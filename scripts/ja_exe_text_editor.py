#!/usr/bin/env python3
"""
FF7 Japanese Executable Text Editor

A comprehensive tool for dumping and editing text strings in the Japanese
version of Final Fantasy VII's executable (ff7_ja.exe). Supports both reading
(dump) and writing (encode) operations.

Created: 2025-12-06 17:30 JST
Session: 0681f78b-0382-45ee-898b-5a32b7ce32d5
Context: Evolved from exe_string_dumper.py to provide full text editing
         capability for the Japanese exe, similar to what touphScript does
         for the English exe. The Japanese exe has a 0xC00 offset from
         English offsets due to additional PE sections in the Steam version.

Based on: exe_string_dumper.py (c245e7c0-ec73-4933-b925-5976860e742c)
Reference: touphScript ff7exe.cpp for offset table structure

Key Differences from English exe:
    - All offsets are shifted by +0xC00 (3072 bytes)
    - Uses multi-byte Japanese encoding (FA-FE prefixes for jafont_2-6)
    - Single-byte characters from jafont_1 texture

Usage:
    # Dump all exe strings to a text file
    python3 ja_exe_text_editor.py dump ff7_ja.exe --output ja_exe_strings.txt

    # Encode modified text back into exe
    python3 ja_exe_text_editor.py encode ff7_ja.exe ja_exe_strings.txt

    # Dump specific region (for investigation)
    python3 ja_exe_text_editor.py region ff7_ja.exe 0x518F70 0x500

    # Compare EN and JA strings at equivalent offsets
    python3 ja_exe_text_editor.py compare ff7_en.exe ff7_ja.exe
"""

import sys
import argparse
import csv
import shutil
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import IntEnum


# =============================================================================
# CONSTANTS - Offset table derived from touphScript ff7exe.cpp + 0xC00
# =============================================================================

# The offset between English and Japanese exe string locations
JA_OFFSET_DELTA = 0xC00  # 3072 bytes

# String types (from touphScript)
class StringType(IntEnum):
    DEF = 0        # Standard FF7 encoding with FF terminator
    NOFF_TERM = 1  # No FF terminator in file
    RGB = 2        # RGB encoded (add 0x73 to each byte)
    UNICODE = 3    # Windows Unicode strings
    FFPADDED = 4   # FF7 encoding padded with FF bytes
    ZEROTERM = 5   # Zero-terminated string

# English offsets from touphScript - we add JA_OFFSET_DELTA for Japanese
EN_OFFSETS = [
    0x518370, 0x51838E, 0x5183AC, 0x5183D0, 0x5183D4, 0x5188A8, 0x5188D8,
    0x518908, 0x518938, 0x518968, 0x518998, 0x5189C8, 0x5189F8, 0x518A28,
    0x518A58, 0x518A88, 0x518AB8, 0x518C08, 0x518C38, 0x518C68, 0x518C98,
    0x518CC8, 0x518CF8, 0x518D28, 0x518D58, 0x518D88, 0x518DE8, 0x518E18,
    0x518ED8, 0x518F08, 0x518F38, 0x518F68, 0x518FC8, 0x519238, 0x51923E,
    0x519244, 0x519288, 0x5192A1, 0x5192C0, 0x5192D4, 0x5192E8, 0x5192FC,
    0x519310, 0x519324, 0x519338, 0x51934C, 0x519360, 0x519374, 0x519388,
    0x51939C, 0x5193D8, 0x5193EC, 0x519400, 0x519414, 0x519428, 0x519450,
    0x519464, 0x519478, 0x5196B0, 0x5196E2, 0x519714, 0x519746, 0x519778,
    0x5197AA, 0x5197DC, 0x51980E, 0x519840, 0x519872, 0x5198A4, 0x5198D6,
    0x519908, 0x51993A, 0x51996C, 0x51999E, 0x5199D0, 0x519A02, 0x519A34,
    0x519FE0, 0x519FE8, 0x519FEC, 0x519FF0, 0x519FF4, 0x519FF8, 0x519FFC,
    0x51A000, 0x51A004, 0x51A008, 0x51A00C, 0x51A010, 0x51A018, 0x51A020,
    0x51A02C, 0x51A030, 0x51A034, 0x51A038, 0x51A03C, 0x51A040, 0x51A044,
    0x51A048, 0x51A04C, 0x51A050, 0x51A054, 0x51A058, 0x51A068, 0x51A078,
    0x51A080, 0x51A090, 0x51A094, 0x51A098, 0x51A09C, 0x51A0A0, 0x51A0A4,
    0x51A0A8, 0x51A0AC, 0x51A0B0, 0x51A0B4, 0x51A0C0, 0x51A0CC, 0x51A0D4,
    0x51A0E0, 0x51A0EC, 0x51A0F0, 0x51A0F4, 0x51A0F8, 0x51A0FC, 0x51A100,
    0x51A104, 0x51A108, 0x51A110, 0x51A118, 0x51A120, 0x51A12C, 0x51A138,
    0x51A144, 0x51A14C, 0x51A158, 0x51A15C, 0x51A160, 0x51A164, 0x51A168,
    0x51A16C, 0x51A170, 0x51A174, 0x51A178, 0x51A17C, 0x51A180, 0x51A188,
    0x51A190, 0x51A198, 0x51A1A0, 0x51A1A8, 0x51A1B4, 0x51A1BC, 0x51A1C4,
    0x51A1CC, 0x51A1D0, 0x51A1D8, 0x51A1E0, 0x51A1E8, 0x51A1F0, 0x51A210,
    0x51A214, 0x51A270, 0x51A274, 0x51A278, 0x51A2C4, 0x51A30C, 0x51A31C,
    0x51A330, 0x51A3AC, 0x51A3CC, 0x51A3D8, 0x51A3DC, 0x51A3E4, 0x51A3F0,
    0x51A3F8, 0x51A400, 0x51A404, 0x51A430, 0x51A43C, 0x51A4F4, 0x51A508,
    0x51A518, 0x51A520, 0x51A59C, 0x51A5A4, 0x51A5A8, 0x51A5B8, 0x51A5C8,
    0x51A5D8, 0x51A5DC, 0x51A5E4, 0x51A5F0, 0x51A5F8, 0x51A638, 0x51A644,
    0x51A650, 0x51A660, 0x51A66C, 0x51A678, 0x51A68C, 0x51A690, 0x51A698,
    0x51A6A0, 0x51A6C8, 0x51A6D4, 0x51A6E0, 0x51A6EC, 0x51A6F8, 0x51A704,
    0x51A710, 0x51A71C, 0x51A728, 0x51A734, 0x51D1E0, 0x51D23C, 0x51D246,
    0x51D250, 0x51D25A, 0x51D264, 0x51D26E, 0x51D278, 0x51D282, 0x51D28C,
    0x51D2B4, 0x51D2BE, 0x51D2DC, 0x51D2F0, 0x51D30E, 0x51D318, 0x51D322,
    0x51D32C, 0x51D3A0, 0x51D3BC, 0x51D3C0, 0x51D3C8, 0x51D588, 0x51D598,
    0x51D5B0, 0x51D5C6, 0x51D5DC, 0x51D608, 0x51D628, 0x51D648, 0x51D668,
    0x51D688, 0x51D6A8, 0x51D6C8, 0x51D6E8, 0x51D708, 0x51D728, 0x51D748,
    0x51D768, 0x51D788, 0x51D7A8, 0x51D7C8, 0x51D7E8, 0x51D808, 0x51D828,
    0x51D848, 0x51D868, 0x51D888, 0x51D8A8, 0x51D8C8, 0x51D8E8, 0x51D908,
    0x51D928, 0x51D94A, 0x51D96C, 0x51DAE0, 0x51DB40, 0x51DB66, 0x51DB8C,
    0x51DBB2, 0x51DBD8, 0x51DBFE, 0x51DE22, 0x51DE38, 0x51DE4E, 0x51DED8,
    0x51DEFC, 0x51DF20, 0x51DF44, 0x51DF68, 0x51DF8C, 0x51DFB0, 0x51DFD4,
    0x51DFF8, 0x51E01C, 0x51E040, 0x51E064, 0x51E088, 0x51E0AC, 0x51EF40,
    0x51EF4A, 0x51EF54, 0x51EF5E, 0x51EF68, 0x51EF72, 0x51EF7C, 0x51EF86,
    0x51EF90, 0x51EFA0, 0x51EFB4, 0x51EFC8, 0x51EFDC, 0x51EFF0, 0x51F004,
    0x51F018, 0x51F02C, 0x51F040, 0x51F054, 0x51F068, 0x51F07C, 0x51F090,
    0x51F0A4, 0x51F0B8, 0x51F0CC, 0x51F0E0, 0x51F0F4, 0x51F108, 0x51F130,
    0x51F144, 0x51F158, 0x51F16C, 0x51F180, 0x51F194, 0x51F1A8, 0x51F1C0,
    0x51F1CF, 0x51F1DE, 0x51F1ED, 0x51F1FC, 0x51F20B, 0x51F21A, 0x51F256,
    0x51F265, 0x51F274, 0x51F283, 0x51F292, 0x51F2A1, 0x51F2B0, 0x51F2BF,
    0x51F2CE, 0x51F2DD, 0x51F2EC, 0x51F2FB, 0x51F30A, 0x51F319, 0x51F328,
    0x51F337, 0x51F346, 0x51F3A8, 0x51F3B4, 0x51F3C0, 0x51F420, 0x51F42C,
    0x51F438, 0x51F444, 0x51F450, 0x51F45C, 0x51F468, 0x51F474, 0x51F480,
    0x51F48C, 0x51F498, 0x51F4A4, 0x51F4B0, 0x51F518, 0x51F53C, 0x51F560,
    0x51F584, 0x51F5A8, 0x51F5BC, 0x51F5D0, 0x51F5E4, 0x51F5F8, 0x51F60C,
    0x51F634, 0x51F648, 0x51F65C, 0x51F670, 0x51F684, 0x51F698, 0x51F6AC,
    0x51F6D4, 0x51F6E8, 0x51F6FC, 0x51F710, 0x51F724, 0x51F738, 0x51F74C,
    0x51F760, 0x51F774, 0x51F788, 0x51F79C, 0x51F7B0, 0x51F7C4, 0x51F7D8,
    0x51F7EC, 0x51F800, 0x51F814, 0x51F828, 0x51F83C, 0x51F850, 0x51F864,
    0x51F878, 0x51F88C, 0x51F8A0, 0x51F9E8, 0x51F9FC, 0x51FA10, 0x51FA24,
    0x51FA38, 0x51FA4C, 0x51FA60, 0x51FA74, 0x51FA9C, 0x51FAB0, 0x51FAC4,
    0x51FAD8, 0x51FAEC, 0x51FB68, 0x51FB74, 0x51FB80, 0x51FB8C, 0x51FB98,
    0x51FBA4, 0x51FBB0, 0x51FBBC, 0x51FBC8, 0x51FBD4, 0x51FBE0, 0x51FBF0,
    0x51FC12, 0x51FC34, 0x51FC56, 0x51FC78, 0x51FC9A, 0x51FCBC, 0x51FCDE,
    0x51FD00, 0x51FD22, 0x51FD44, 0x51FD66, 0x51FD88, 0x51FDAA, 0x51FDCC,
    0x51FDEE, 0x51FE10, 0x51FE32, 0x51FE54, 0x51FE76, 0x51FE98, 0x51FEBA,
    0x51FEDC, 0x51FEFE, 0x51FF20, 0x5206B8, 0x5206C4, 0x5206D0, 0x5206DC,
    0x5206E8, 0x5206F4, 0x520700, 0x52070C, 0x520718, 0x520724, 0x520748,
    0x520750, 0x520758, 0x520760, 0x520768, 0x520770, 0x520771, 0x520772,
    0x520773, 0x520774, 0x520775, 0x520776, 0x520777, 0x520778, 0x520779,
    0x52077A, 0x52077B, 0x52077C, 0x52077D, 0x52077E, 0x52077F, 0x520780,
    0x520781, 0x520782, 0x520783, 0x520784, 0x520785, 0x520786, 0x520787,
    0x520788, 0x520789, 0x52078A, 0x52078B, 0x52078C, 0x52078D, 0x52078E,
    0x52078F, 0x520790, 0x520791, 0x520792, 0x520793, 0x520794, 0x520795,
    0x520796, 0x520797, 0x520798, 0x520799, 0x52079A, 0x52079B, 0x52079C,
    0x52079D, 0x52079E, 0x52079F, 0x5207A0, 0x5207A1, 0x5207A2, 0x5207A3,
    0x5207A4, 0x5207A5, 0x5207A6, 0x5207A7, 0x5207A8, 0x5207A9, 0x5207AC,
    0x5207AD, 0x5207AE, 0x5207AF, 0x5207B0, 0x5207B1, 0x5207B2, 0x5207B3,
    0x5207B4, 0x5207B5, 0x5213D8, 0x5213EC, 0x52143C, 0x521450, 0x521464,
    0x5214DC, 0x5214F0, 0x521504, 0x521518, 0x52152C, 0x521540, 0x521554,
    0x521568, 0x52157C, 0x521590, 0x5215A4, 0x5215B8, 0x5215CC, 0x5215E0,
    0x5215F4, 0x521608, 0x52161C, 0x521630, 0x521644, 0x521658, 0x52166C,
    0x521680, 0x521694, 0x5216A8, 0x5216F8, 0x5216FA, 0x521700, 0x521714,
    0x521728, 0x52173C, 0x521750, 0x521764, 0x521778, 0x52178C, 0x5217A0,
    0x5217B4, 0x52196A, 0x521980, 0x521996, 0x5219AC, 0x5219DC, 0x5219F0,
    0x521A04, 0x521A18, 0x521A2C, 0x521A40, 0x521A54, 0x521A68, 0x521A80,
    0x521AAE, 0x521ADC, 0x521B0A, 0x521B38, 0x524160, 0x524184, 0x5241A8,
    0x524238, 0x52425C, 0x524280, 0x5242A4, 0x5242C8, 0x524310, 0x524334,
    0x524358, 0x52437C, 0x5243A0, 0x5243C4, 0x5243E8, 0x52440C, 0x524430,
    0x524454, 0x524478, 0x52449C, 0x5244C0, 0x5244E4, 0x524508, 0x52452C,
    0x524550, 0x524574, 0x524598, 0x5245BC, 0x5245E0, 0x524604, 0x524628,
    0x52464C, 0x524698, 0x524728, 0x524758, 0x524788, 0x5247B8, 0x5247E8,
    0x524818, 0x524848, 0x524878, 0x5248A8, 0x5248D8, 0x524908, 0x524998,
    0x5249C8, 0x524AB8, 0x524AE8, 0x524B18, 0x524B24, 0x524B30, 0x524B3C,
    0x524B48, 0x524B54, 0x524B60, 0x524B6C, 0x524B78, 0x524B84, 0x524BF0,
    0x5552C0, 0x5552D0, 0x555410, 0x555420, 0x555430, 0x5557A0, 0x5557B0,
    0x5557BC, 0x5557C4, 0x5557CC, 0x5557D4, 0x5557E0, 0x5557E8, 0x5557F0,
    0x5557F8, 0x555800, 0x555804, 0x55580C, 0x555814, 0x55581C, 0x555824,
    0x55582C, 0x555838, 0x555848, 0x555854, 0x55585C, 0x555864, 0x55586C,
    0x555874, 0x555880, 0x55588C, 0x555898, 0x5558A0, 0x5558AC, 0x5558B4,
    0x5558BC, 0x5558C4, 0x5558CC, 0x57B2A8, 0x57B3D0, 0x57B3E0, 0x57B3F0,
    0x57B400, 0x57B410, 0x57B420, 0x57B430, 0x57B440, 0x57B450, 0x57B460,
    0x57B470, 0x57B480, 0x57B490, 0x57B4A0, 0x57B4B0, 0x57B4C0, 0x57B4D0,
    0x57B4E0, 0x57B4F0, 0x57B500, 0x57B510, 0x57B520, 0x57B530, 0x57B540,
    0x57B658, 0x57B65F, 0x57B666, 0x57B66D, 0x57B674, 0x57B67B, 0x57B682,
    0x57B689, 0x57B690, 0x57B697, 0x57B69E, 0x57B6A5, 0x57B6AC, 0x57B6B3,
    0x57B6BA, 0x57B6C1, 0x57B6C8, 0x57B6CF, 0x57B6D6, 0x57B6DD, 0x57B6E4,
    0x57B6EB, 0x57B6F2, 0x57B6F9, 0x57B700, 0x57B707, 0x57B70E, 0x57B715,
    0x57B71C, 0x57B723, 0x57B72A, 0x57B731, 0x57B738, 0x57B73F, 0x57B746,
    0x57B74D, 0x57B754, 0x57B75B, 0x57B762, 0x57B769, 0x57B770, 0x57B777,
    0x57B77E, 0x57B785, 0x57B78C, 0x57B793
]

# String lengths (from touphScript)
STRING_LENGTHS = [
    30, 30, 30, 4, 4, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48,
    48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 6, 6, 6, 25, 25,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50,
    50, 50, 50, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 8, 8, 12, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 16, 16, 8, 16, 4, 4, 4, 4, 4, 4, 4, 4, 4, 12, 12, 8, 12,
    12, 4, 4, 4, 4, 4, 4, 4, 8, 8, 8, 12, 12, 12, 8, 12, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 8, 8, 8, 8, 8, 12, 8, 8, 8, 4, 8, 8, 8, 8, 8, 4, 4, 4, 4, 4, 8,
    8, 12, 4, 16, 12, 4, 8, 12, 8, 8, 4, 12, 12, 16, 12, 8, 8, 12, 8, 4, 8,
    8, 8, 4, 8, 12, 8, 8, 12, 12, 8, 12, 12, 12, 4, 8, 8, 8, 12, 12, 12, 12,
    12, 12, 12, 12, 12, 12, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 11,
    10, 10, 10, 10, 10, 10, 28, 4, 8, 16, 16, 24, 22, 22, 22, 32, 32, 32, 32,
    32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32,
    32, 32, 32, 34, 34, 34, 8, 38, 38, 38, 38, 38, 38, 22, 22, 22, 36, 36,
    36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 10, 10, 10, 10, 10, 10,
    10, 10, 10, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 12,
    12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 36, 36, 36,
    36, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 12, 12, 12, 12,
    12, 12, 12, 12, 12, 12, 12, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34,
    34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 12, 12, 12, 12,
    12, 12, 12, 12, 12, 12, 8, 8, 8, 8, 8, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    2, 2, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 22, 22, 22, 22, 20, 20, 20,
    20, 20, 20, 20, 20, 46, 46, 46, 46, 46, 36, 36, 36, 36, 36, 36, 36, 36,
    36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
    36, 36, 36, 36, 36, 36, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48,
    48, 48, 48, 48, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 8, 16, 16, 16,
    16, 16, 8, 12, 8, 8, 8, 12, 8, 8, 8, 8, 4, 8, 8, 8, 8, 8, 12, 8, 12, 8,
    8, 8, 8, 12, 12, 12, 8, 8, 8, 8, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16,
    16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7
]

# String types (from touphScript)
STRING_TYPES = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5
]


# =============================================================================
# CHARACTER ENCODING
# =============================================================================

class FF7CharacterEncoder:
    """Handles encoding/decoding of FF7 Japanese text."""

    def __init__(self, charmap_path: Optional[Path] = None):
        self.charmap: Dict = {}
        self.reverse_charmap: Dict[str, bytes] = {}

        if charmap_path is None:
            # Default path relative to script
            script_dir = Path(__file__).parent.parent
            charmap_path = script_dir / "docs" / "character_maps" / "ff7_complete_mapping_compact.csv"

        self._load_charmap(charmap_path)

    def _load_charmap(self, csv_path: Path) -> None:
        """Load character map from CSV."""
        if not csv_path.exists():
            print(f"Warning: Character map not found at {csv_path}", file=sys.stderr)
            return

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                texture = row['texture']
                index = int(row['index'])
                char = row['character']

                if texture == 'jafont_1':
                    self.charmap[index] = char
                    self.reverse_charmap[char] = bytes([index])
                elif texture == 'jafont_2':
                    self.charmap[(0xFA, index)] = char
                    self.reverse_charmap[char] = bytes([0xFA, index])
                elif texture == 'jafont_3':
                    self.charmap[(0xFB, index)] = char
                    self.reverse_charmap[char] = bytes([0xFB, index])
                elif texture == 'jafont_4':
                    self.charmap[(0xFC, index)] = char
                    self.reverse_charmap[char] = bytes([0xFC, index])
                elif texture == 'jafont_5':
                    self.charmap[(0xFD, index)] = char
                    self.reverse_charmap[char] = bytes([0xFD, index])
                elif texture == 'jafont_6':
                    self.charmap[(0xFE, index)] = char
                    self.reverse_charmap[char] = bytes([0xFE, index])

    def decode_char(self, byte: int, next_byte: Optional[int] = None) -> Tuple[str, int]:
        """
        Decode FF7 Japanese character byte(s).
        Returns (decoded_char, bytes_consumed)
        """
        # Two-byte sequences (FA-FE prefix)
        if byte in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) and next_byte is not None:
            key = (byte, next_byte)
            if key in self.charmap:
                return (self.charmap[key], 2)
            else:
                prefix_names = {0xFA: '2', 0xFB: '3', 0xFC: '4', 0xFD: '5', 0xFE: '6'}
                return (f'[jf{prefix_names[byte]}:{next_byte:02X}]', 2)

        # Single byte from jafont_1
        if byte in self.charmap:
            return (self.charmap[byte], 1)

        # Space
        if byte == 0x00:
            return (' ', 1)

        # Terminator
        if byte == 0xFF:
            return ('', 1)

        # Unknown
        return (f'[{byte:02X}]', 1)

    def decode_string(self, data: bytes) -> str:
        """Decode FF7 encoded bytes to string."""
        result = []
        i = 0

        while i < len(data):
            byte = data[i]
            if byte == 0xFF:
                break

            next_byte = data[i + 1] if i + 1 < len(data) else None
            char, consumed = self.decode_char(byte, next_byte)
            result.append(char)
            i += consumed

        return ''.join(result)

    def encode_string(self, text: str) -> bytes:
        """Encode string to FF7 bytes."""
        result = bytearray()

        for char in text:
            if char == ' ':
                result.append(0x00)
            elif char in self.reverse_charmap:
                result.extend(self.reverse_charmap[char])
            else:
                # Unknown character - skip with warning
                print(f"Warning: Unknown character '{char}' (U+{ord(char):04X})", file=sys.stderr)

        result.append(0xFF)  # Terminator
        return bytes(result)


# =============================================================================
# MAIN OPERATIONS
# =============================================================================

@dataclass
class StringEntry:
    """Represents a single string entry in the exe."""
    index: int
    en_offset: int
    ja_offset: int
    length: int
    string_type: StringType
    raw_bytes: bytes
    decoded: str


def dump_strings(exe_path: Path, output_path: Optional[Path], encoder: FF7CharacterEncoder) -> List[StringEntry]:
    """Dump all strings from the Japanese exe."""
    entries = []

    with open(exe_path, 'rb') as f:
        for i, (en_offset, length, stype) in enumerate(zip(EN_OFFSETS, STRING_LENGTHS, STRING_TYPES)):
            ja_offset = en_offset + JA_OFFSET_DELTA

            f.seek(ja_offset)
            raw_bytes = f.read(length)

            # Decode based on type
            if stype == StringType.UNICODE:
                # Windows Unicode - decode as UTF-16
                try:
                    decoded = raw_bytes.decode('utf-16-le').rstrip('\x00')
                except:
                    decoded = f"[UNICODE:{raw_bytes.hex()}]"
            elif stype == StringType.RGB:
                # RGB encoded - subtract 0x73 (only for valid bytes, clamp to 0)
                decoded_bytes = bytes(
                    max(0, b - 0x73) if b != 0xFF else 0xFF for b in raw_bytes
                )
                decoded = encoder.decode_string(decoded_bytes)
            else:
                # Standard FF7 encoding
                decoded = encoder.decode_string(raw_bytes)

            entry = StringEntry(
                index=i,
                en_offset=en_offset,
                ja_offset=ja_offset,
                length=length,
                string_type=StringType(stype),
                raw_bytes=raw_bytes,
                decoded=decoded
            )
            entries.append(entry)

    # Write to file if output specified
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# FF7 Japanese Executable Text Dump\n")
            f.write(f"# Generated from: {exe_path.name}\n")
            f.write(f"# Total strings: {len(entries)}\n")
            f.write("#\n")
            f.write("# Format: INDEX|JA_OFFSET|TYPE|TEXT\n")
            f.write("# Edit the TEXT portion only. Do not change INDEX, OFFSET, or TYPE.\n")
            f.write("# Lines starting with # are comments and will be ignored.\n")
            f.write("#" + "=" * 79 + "\n\n")

            for entry in entries:
                f.write(f"{entry.index:04d}|0x{entry.ja_offset:08X}|{entry.string_type.name}|{entry.decoded}\n")

        print(f"Dumped {len(entries)} strings to {output_path}")

    return entries


def encode_strings(exe_path: Path, text_path: Path, encoder: FF7CharacterEncoder) -> None:
    """Encode modified text back into the exe."""
    # Parse the text file
    modified = {}
    with open(text_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('#') or not line.strip():
                continue

            parts = line.split('|', 3)
            if len(parts) != 4:
                continue

            index = int(parts[0])
            text = parts[3]
            modified[index] = text

    # Create backup
    backup_path = exe_path.with_suffix('.exe.bak')
    if not backup_path.exists():
        shutil.copy2(exe_path, backup_path)
        print(f"Created backup: {backup_path}")

    # Write modifications
    changes = 0
    with open(exe_path, 'r+b') as f:
        for index, text in modified.items():
            if index >= len(EN_OFFSETS):
                print(f"Warning: Index {index} out of range", file=sys.stderr)
                continue

            en_offset = EN_OFFSETS[index]
            ja_offset = en_offset + JA_OFFSET_DELTA
            length = STRING_LENGTHS[index]
            stype = STRING_TYPES[index]

            # Encode the string
            if stype == StringType.UNICODE:
                encoded = text.encode('utf-16-le')
                encoded = encoded[:length]
                encoded = encoded.ljust(length, b'\x00')
            elif stype == StringType.RGB:
                # RGB encoding - add 0x73
                temp = encoder.encode_string(text)
                encoded = bytes(b + 0x73 if b != 0xFF else 0xFF for b in temp)
                encoded = encoded[:length]
            else:
                encoded = encoder.encode_string(text)
                # Handle padding based on type
                if stype == StringType.FFPADDED:
                    encoded = encoded[:length].ljust(length, b'\xFF')
                elif stype == StringType.ZEROTERM:
                    encoded = encoded[:-1]  # Remove FF terminator
                    encoded = encoded[:length].ljust(length, b'\x00')
                elif stype == StringType.NOFF_TERM:
                    encoded = encoded[:-1]  # Remove FF terminator
                    encoded = encoded[:length].ljust(length, b'\x00')
                else:
                    encoded = encoded[:length].ljust(length, b'\x00')

            if len(encoded) > length:
                print(f"Warning: String {index} too long ({len(encoded)} > {length})", file=sys.stderr)
                encoded = encoded[:length]

            f.seek(ja_offset)
            f.write(encoded)
            changes += 1

    print(f"Encoded {changes} strings into {exe_path}")


def dump_region(exe_path: Path, start_offset: int, length: int, encoder: FF7CharacterEncoder) -> None:
    """Dump a specific region of the exe for investigation."""
    with open(exe_path, 'rb') as f:
        f.seek(start_offset)
        data = f.read(length)

    print("=" * 80)
    print(f"FF7 Region Dump: {exe_path.name}")
    print(f"Region: 0x{start_offset:08X} - 0x{start_offset + length:08X}")
    print("=" * 80)
    print()

    # Find strings in the region
    strings = []
    i = 0
    while i < len(data):
        if data[i] == 0x00:
            i += 1
            continue

        # Find string end
        j = i
        while j < len(data) and data[j] != 0xFF:
            j += 1

        if j < len(data) and data[j] == 0xFF:
            string_bytes = data[i:j+1]
            if len(string_bytes) >= 2:
                file_offset = start_offset + i
                decoded = encoder.decode_string(string_bytes)
                strings.append((file_offset, string_bytes, decoded))
            i = j + 1
        else:
            i += 1

    print(f"Found {len(strings)} strings:\n")
    print(f"{'Offset':<14} {'Len':<5} {'Decoded':<40} Bytes")
    print("-" * 100)

    for offset, raw, decoded in strings:
        decoded_display = decoded[:38] + '..' if len(decoded) > 40 else decoded
        hex_str = ' '.join(f'{b:02X}' for b in raw[:20])
        if len(raw) > 20:
            hex_str += ' ...'
        print(f"0x{offset:08X}   {len(raw):<5} {decoded_display:<40} {hex_str}")


def compare_exes(en_path: Path, ja_path: Path, encoder: FF7CharacterEncoder) -> None:
    """Compare strings between EN and JA executables."""
    print("=" * 100)
    print("FF7 EN/JA String Comparison")
    print("=" * 100)
    print()

    with open(en_path, 'rb') as en_f, open(ja_path, 'rb') as ja_f:
        print(f"{'Idx':<5} {'EN Offset':<12} {'JA Offset':<12} {'EN Text':<30} {'JA Text':<30}")
        print("-" * 100)

        for i, (en_offset, length, stype) in enumerate(zip(EN_OFFSETS[:50], STRING_LENGTHS[:50], STRING_TYPES[:50])):
            ja_offset = en_offset + JA_OFFSET_DELTA

            en_f.seek(en_offset)
            en_bytes = en_f.read(length)

            ja_f.seek(ja_offset)
            ja_bytes = ja_f.read(length)

            # Decode EN (different encoding)
            en_decoded = decode_english(en_bytes)

            # Decode JA
            ja_decoded = encoder.decode_string(ja_bytes)

            en_display = en_decoded[:28] + '..' if len(en_decoded) > 30 else en_decoded
            ja_display = ja_decoded[:28] + '..' if len(ja_decoded) > 30 else ja_decoded

            print(f"{i:<5} 0x{en_offset:08X}   0x{ja_offset:08X}   {en_display:<30} {ja_display:<30}")


def decode_english(data: bytes) -> str:
    """Decode English FF7 string."""
    result = []
    for byte in data:
        if byte == 0xFF:
            break
        if byte == 0x00:
            result.append(' ')
        elif 0x01 <= byte <= 0x5F:
            result.append(chr(byte + 0x20))
        else:
            result.append(f'[{byte:02X}]')
    return ''.join(result)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='FF7 Japanese Executable Text Editor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Dump all strings:
    python3 ja_exe_text_editor.py dump ff7_ja.exe -o ja_strings.txt

  Encode modified strings back:
    python3 ja_exe_text_editor.py encode ff7_ja.exe ja_strings.txt

  Dump specific region:
    python3 ja_exe_text_editor.py region ff7_ja.exe 0x518F70 0x500

  Compare EN and JA:
    python3 ja_exe_text_editor.py compare ff7_en.exe ff7_ja.exe
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Dump all exe strings')
    dump_parser.add_argument('exe_path', type=Path, help='Path to ff7_ja.exe')
    dump_parser.add_argument('-o', '--output', type=Path, help='Output text file')

    # Encode command
    encode_parser = subparsers.add_parser('encode', help='Encode strings back into exe')
    encode_parser.add_argument('exe_path', type=Path, help='Path to ff7_ja.exe')
    encode_parser.add_argument('text_path', type=Path, help='Modified text file')

    # Region command
    region_parser = subparsers.add_parser('region', help='Dump specific memory region')
    region_parser.add_argument('exe_path', type=Path, help='Path to exe')
    region_parser.add_argument('start_offset', help='Start offset (hex, e.g., 0x518F70)')
    region_parser.add_argument('length', help='Length in bytes (hex, e.g., 0x500)')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare EN and JA strings')
    compare_parser.add_argument('en_exe', type=Path, help='Path to ff7_en.exe')
    compare_parser.add_argument('ja_exe', type=Path, help='Path to ff7_ja.exe')

    args = parser.parse_args()

    # Initialize encoder
    encoder = FF7CharacterEncoder()

    if args.command == 'dump':
        if not args.exe_path.exists():
            print(f"Error: File not found: {args.exe_path}", file=sys.stderr)
            sys.exit(1)
        dump_strings(args.exe_path, args.output, encoder)

    elif args.command == 'encode':
        if not args.exe_path.exists():
            print(f"Error: File not found: {args.exe_path}", file=sys.stderr)
            sys.exit(1)
        if not args.text_path.exists():
            print(f"Error: File not found: {args.text_path}", file=sys.stderr)
            sys.exit(1)
        encode_strings(args.exe_path, args.text_path, encoder)

    elif args.command == 'region':
        if not args.exe_path.exists():
            print(f"Error: File not found: {args.exe_path}", file=sys.stderr)
            sys.exit(1)
        start = int(args.start_offset, 16)
        length = int(args.length, 16)
        dump_region(args.exe_path, start, length, encoder)

    elif args.command == 'compare':
        if not args.en_exe.exists():
            print(f"Error: File not found: {args.en_exe}", file=sys.stderr)
            sys.exit(1)
        if not args.ja_exe.exists():
            print(f"Error: File not found: {args.ja_exe}", file=sys.stderr)
            sys.exit(1)
        compare_exes(args.en_exe, args.ja_exe, encoder)


if __name__ == '__main__':
    main()
