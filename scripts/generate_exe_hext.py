#!/usr/bin/env python3
"""
FF7 Japanese Menu HEXT Generator

Generates HEXT patches to replace English exe strings with Japanese equivalents.
Uses the offset table from touphScript ff7exe.cpp to ensure correct memory locations.

Created: 2025-12-06 19:35 JST
Session: 0681f78b-0382-45ee-898b-5a32b7ce32d5
Context: Automates creation of HEXT patches for Japanese menu text in FF7 English exe.
         Reads Japanese text from ff7_ja.exe and generates patches targeting ff7_en.exe.

Usage:
    python3 generate_exe_hext.py ff7_en.exe ff7_ja.exe -o japanese_menu.txt

Output Format:
    # Comment with EN -> JA text
    # EN offset, JA offset info
    XXXXXX = AA BB CC DD FF 00 00
"""

import sys
import argparse
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum


# =============================================================================
# CONSTANTS - From touphScript ff7exe.cpp
# =============================================================================

JA_OFFSET_DELTA = 0xC00  # Japanese exe strings are 0xC00 bytes ahead

class StringType(IntEnum):
    DEF = 0        # Standard FF7 encoding with FF terminator
    NOFF_TERM = 1  # No FF terminator in file
    RGB = 2        # RGB encoded (ASCII + 0x73)
    UNICODE = 3    # Windows Unicode strings
    FFPADDED = 4   # FF7 encoding padded with FF bytes
    ZEROTERM = 5   # Zero-terminated string

# English offsets from touphScript ff7exe.cpp
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
# SKIP REGIONS CONFIGURATION
#
# These regions are skipped because:
# - They contain English text that should stay English (keyboard labels, jockey names)
# - They use different encoding (UNICODE for name entry)
# - They affect layout/rendering control data beyond just text
# - They produce garbage when patched
#
# Note: RGB encoding (+0x93) is still available for keyboard labels, but those
# regions bypass the hooked text renderer, so HEXT patches don't help there.
# The keyboard issue needs a different solution (likely FFNx code changes).
# =============================================================================

# Primary skip regions - these work correctly when skipped
SKIP_REGIONS = set()
SKIP_REGIONS.update(range(461, 529))   # Name entry characters (UNICODE type) - indices 461-528
# SKIP_REGIONS.update(range(77, 212))  # INCLUDED NOW - Keyboard key names (RGB type)
SKIP_REGIONS.update(range(687, 712))   # Race ordinals and related (FFPADDED type)
SKIP_REGIONS.update(range(712, 758))   # Chocobo jockey names (ZEROTERM type)

# RGB regions that should COPY JA BYTES (not apply RGB encoding to EN bytes)
# Save slots 3-10: JA has FF7-encoded Japanese (セーブ３-１０)
# Note: Index 657 is "Level" (レベル), NOT a save slot
RGB_COPY_JA_REGIONS = set(range(649, 657))  # Save slots 3-10 only (indices 649-656)

# Save slots need spacing added to align with cursor (EN exe has trailing spaces, JA doesn't)
# Save 1-2 (DEF type, indices 647-648) and Save 3-10 (RGB type, indices 649-656)
# Note: Index 657 is "Level" (レベル), NOT a save slot!
SAVE_SLOT_REGION = set(range(647, 657))  # Indices 647-656 (Save 1-10 only)

# Keyboard region needs special handling: JA bytes + 0x20
# The game/FFNx applies -0x20 to keyboard bytes before font lookup,
# so we must add +0x20 to compensate
# Note: Indices 212-213 (BUTTON 9, BUTTON 10) are marked DEF but use same rendering path
KEYBOARD_REGION = set(range(77, 214))  # Keyboard labels (indices 77-213, including BUTTON 9/10)

# Legacy alias for backwards compatibility
RGB_AS_DEF_REGIONS = RGB_COPY_JA_REGIONS

# RGB regions to skip entirely (EN and JA are identical - timing/score formats)
# Start at 658, NOT 657 - index 657 (Level/レベル) needs +0x20 offset like keyboard
RGB_SKIP_REGIONS = set(range(658, 687))    # Post-save: "00'00\"000", "SURF", etc.

# Level label (index 657) needs keyboard offset because it uses same rendering path
LEVEL_INDEX = 657

# Shop menu "Buy Sell Exit" needs extra spacing (index 572)
# EN has: Buy[3sp]Sell[5sp]Exit  JA has: かう[1sp]うる[1sp]でる
# Adding more ideographic spaces to match EN alignment
SHOP_MENU_INDEX = 572

# Item/Materia menu column header needs spacing (index 578)
# EN has: Item[6sp]Materia  JA has: アイテム[1sp]マテリア
# Adding more ideographic spaces to match EN column alignment
ITEM_MATERIA_INDEX = 578


# =============================================================================
# CHARACTER ENCODING
# =============================================================================

class FF7CharacterEncoder:
    """Handles encoding/decoding of FF7 Japanese text."""

    def __init__(self, charmap_path: Optional[Path] = None):
        self.charmap: Dict = {}

        if charmap_path is None:
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
                elif texture == 'jafont_2':
                    self.charmap[(0xFA, index)] = char
                elif texture == 'jafont_3':
                    self.charmap[(0xFB, index)] = char
                elif texture == 'jafont_4':
                    self.charmap[(0xFC, index)] = char
                elif texture == 'jafont_5':
                    self.charmap[(0xFD, index)] = char
                elif texture == 'jafont_6':
                    self.charmap[(0xFE, index)] = char

    def decode_char(self, byte: int, next_byte: Optional[int] = None) -> Tuple[str, int]:
        """Decode FF7 Japanese character byte(s)."""
        if byte in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) and next_byte is not None:
            key = (byte, next_byte)
            if key in self.charmap:
                return (self.charmap[key], 2)
            else:
                return (f'[{byte:02X}{next_byte:02X}]', 2)

        if byte in self.charmap:
            return (self.charmap[byte], 1)

        if byte == 0x00:
            return (' ', 1)
        if byte == 0xFF:
            return ('', 1)

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


def encode_rgb(data: bytes) -> bytes:
    """
    Encode FF7-encoded bytes using RGB encoding.

    The EN exe stores keyboard labels in FF7 encoding (ASCII - 0x20).
    To display them correctly on jafont_1, we need to convert them to
    positions where fullwidth English letters are located.

    The formula is: RGB_byte = FF7_byte + 0x93
    Which is equivalent to: (ASCII - 0x20) + 0x93 = ASCII + 0x73

    This maps FF7-encoded letters to fullwidth positions on jafont_1:
    - FF7 'E' (0x25) + 0x93 = 0xB8 -> position 184 = 'Ｅ'
    - FF7 'e' (0x45) + 0x93 = 0xD8 -> but we want uppercase, so we use 0xB8

    For uppercase mapping:
    - FF7 uppercase letters are 0x21-0x3A (A=0x21, Z=0x3A)
    - FF7 lowercase letters are 0x41-0x5A (a=0x41, z=0x5A)
    - Fullwidth A-Z are at positions 180-205 (0xB4-0xCD)

    So: uppercase FF7 byte + 0x93 = correct position
    And: lowercase FF7 byte + 0x73 = also maps to uppercase position (convenient!)
    """
    result = bytearray()
    for byte in data:
        if byte == 0x00:
            # Null/space - keep as is (FF7 uses 0x00 for space)
            result.append(0x00)
        elif byte == 0xFF:
            # Terminator - keep as is
            result.append(0xFF)
        elif 0x21 <= byte <= 0x3A:
            # FF7 uppercase A-Z (0x21-0x3A) -> add 0x93 to get fullwidth
            result.append(byte + 0x93)
        elif 0x41 <= byte <= 0x5A:
            # FF7 lowercase a-z (0x41-0x5A) -> subtract 0x20 first to get uppercase, then add 0x93
            # This makes lowercase display as uppercase fullwidth
            result.append(byte - 0x20 + 0x93)
        elif 0x01 <= byte <= 0x5F:
            # Other FF7 printable characters - add 0x93
            result.append(byte + 0x93)
        else:
            # Other bytes (control codes, etc.) - keep as is
            result.append(byte)
    return bytes(result)


def apply_keyboard_offset(data: bytes) -> bytes:
    """Apply +0x20 offset to keyboard bytes to compensate for game's -0x20 transformation.

    The game/FFNx applies -0x20 to keyboard label bytes before font lookup,
    so we add +0x20 to the JA bytes to compensate.
    """
    result = bytearray()
    for byte in data:
        if byte == 0x00 or byte == 0xFF:
            # Terminators/spaces - keep as is
            result.append(byte)
        elif byte <= 0xDF:
            # Add 0x20, but don't overflow past 0xFF
            result.append(byte + 0x20)
        else:
            # Already high values - keep as is to avoid overflow
            result.append(byte)
    return bytes(result)


def add_save_slot_spacing(data: bytes, target_length: int) -> bytes:
    """Add trailing spaces to save slot text to align with cursor.

    Testing position 63 (0x3F) which is ideographic space (　, U+3000) on jafont_1.
    Position 217 (0xD9) was found to be zero-width/non-rendering.
    """
    JAFONT1_SPACE = 0x3F  # Position 63 = ideographic space (　)

    result = bytearray()

    # Find where the text ends (0xFF terminator)
    for b in data:
        if b == 0xFF:
            break
        result.append(b)

    text_len = len(result)

    # Calculate how many spaces we can add while still fitting terminator
    available_space = target_length - text_len - 1  # -1 for terminator

    # Add up to 2 spaces, but only if there's room
    # 2 spaces provides better alignment than 3 for Japanese text width
    spaces_to_add = min(2, available_space)
    for _ in range(spaces_to_add):
        result.append(JAFONT1_SPACE)

    # Add terminator
    result.append(0xFF)

    # Pad rest with 0x00 (these are after terminator, won't render)
    while len(result) < target_length:
        result.append(0x00)

    return bytes(result[:target_length])


def fix_shop_menu_spacing(data: bytes, target_length: int) -> bytes:
    """Fix spacing for shop menu 'Buy Sell Exit' / 'かう うる でる'.

    EN has: Buy[3sp]Sell[5sp]Exit (20 bytes)
    JA has: かう[1sp]うる[1sp]でる (9 bytes including terminator)

    We need to add more ideographic spaces (0x3F) to align with EN.
    Target: かう[2sp]うる[3sp]でる
    """
    JAFONT1_SPACE = 0x3F

    # Manually construct: かう + 2 spaces + うる + 3 spaces + でる + terminator
    # か=0x4B, う=0x69, る=0x8B, で=0x25
    result = bytearray([
        0x4B, 0x69,                     # かう
        JAFONT1_SPACE, JAFONT1_SPACE,   # 2 spaces
        0x69, 0x8B,                     # うる
        JAFONT1_SPACE, JAFONT1_SPACE, JAFONT1_SPACE,  # 3 spaces
        0x25, 0x8B,                     # でる
        0xFF                            # terminator
    ])

    # Pad to target length
    while len(result) < target_length:
        result.append(0x00)

    return bytes(result[:target_length])


def fix_item_materia_spacing(data: bytes, target_length: int) -> bytes:
    """Fix spacing for Item/Materia column header.

    EN has: Item[6sp]Materia (17 chars + terminator = 20 bytes)
    JA has: アイテム[1sp]マテリア (9 bytes + terminator)

    We need to add more ideographic spaces (0x3F) to align columns.
    Target: アイテム[4sp]マテリア (EN has 6 spaces, ~4 JA spaces equivalent)

    JA bytes from exe: 6a 6c 64 80 3f 7c 64 88 6a ff
    ア=0x6A, イ=0x6C, テ=0x64, ム=0x80, マ=0x7C, テ=0x64, リ=0x88, ア=0x6A
    """
    JAFONT1_SPACE = 0x3F

    # Manually construct: アイテム + 4 spaces + マテリア + terminator
    result = bytearray([
        0x6A, 0x6C, 0x64, 0x80,         # アイテム
        JAFONT1_SPACE, JAFONT1_SPACE,   # 4 spaces (EN has 6, ~67% = 4)
        JAFONT1_SPACE, JAFONT1_SPACE,
        0x7C, 0x64, 0x88, 0x6A,         # マテリア
        0xFF                            # terminator
    ])

    # Pad to target length
    while len(result) < target_length:
        result.append(0x00)

    return bytes(result[:target_length])


def decode_rgb_as_ascii(data: bytes) -> str:
    """Decode RGB-encoded bytes back to ASCII for display purposes."""
    result = []
    for byte in data:
        if byte == 0xFF:
            break
        if byte == 0x00:
            result.append(' ')
        elif 0x93 <= byte <= 0xF1:  # RGB range (0x20+0x73 to 0x7E+0x73)
            result.append(chr(byte - 0x73))
        else:
            result.append(f'[{byte:02X}]')
    return ''.join(result)


def file_offset_to_va(file_offset: int) -> int:
    """Convert file offset to Virtual Address for HEXT."""
    return (file_offset - 0x3B8A00) + 0x3BA000 + 0x400000


# =============================================================================
# HEXT GENERATION
# =============================================================================

@dataclass
class PatchEntry:
    """Represents a single HEXT patch entry."""
    index: int
    en_offset: int
    ja_offset: int
    en_text: str
    ja_text: str
    length: int
    string_type: StringType
    ja_bytes: bytes


def generate_hext(en_exe: Path, ja_exe: Path, output: Path, encoder: FF7CharacterEncoder, session_id: str) -> None:
    """Generate HEXT patch file."""
    patches: List[PatchEntry] = []

    with open(en_exe, 'rb') as en_f, open(ja_exe, 'rb') as ja_f:
        for i, (en_offset, length, stype) in enumerate(zip(EN_OFFSETS, STRING_LENGTHS, STRING_TYPES)):
            # Skip problematic regions
            if i in SKIP_REGIONS:
                continue

            # Skip RGB regions that produce garbage
            if i in RGB_SKIP_REGIONS:
                continue

            # Skip single-byte entries
            if length <= 1:
                continue

            ja_offset = en_offset + JA_OFFSET_DELTA

            # Read both
            en_f.seek(en_offset)
            en_bytes = en_f.read(length)

            ja_f.seek(ja_offset)
            ja_bytes = ja_f.read(length)

            # Decode for display and determine patch bytes
            # SIMPLIFIED: RGB type = encode EN bytes, everything else = copy JA bytes

            if stype == StringType.RGB:
                # Keyboard region: JA bytes + 0x20 to compensate for game's -0x20 transformation
                if i in KEYBOARD_REGION:
                    en_text = decode_english(en_bytes)
                    patch_bytes = apply_keyboard_offset(ja_bytes)
                    # Decode the original JA RGB bytes to show what text it represents
                    rgb_decoded = ''.join(chr(b - 0x73) if 0x93 <= b <= 0xED else ('?' if b not in (0x00, 0xFF) else '') for b in ja_bytes)
                    ja_text = f"[KB:{rgb_decoded.strip()}]"
                # Level label (index 657): copy JA bytes directly (menu path, no -0x20 transformation)
                elif i == LEVEL_INDEX:
                    en_text = decode_english(en_bytes)
                    patch_bytes = ja_bytes  # Direct copy, no offset needed
                    ja_text = "レベル"
                # Save slots: copy JA bytes with spacing for cursor alignment
                # Uses 0xD9 (position 217) as space character on jafont_1
                elif i in RGB_COPY_JA_REGIONS:
                    en_text = decode_english(en_bytes)
                    ja_text = encoder.decode_string(ja_bytes)
                    patch_bytes = add_save_slot_spacing(ja_bytes, length)
                else:
                    # Other RGB regions: apply RGB encoding to EN bytes
                    en_text = decode_english(en_bytes)
                    patch_bytes = encode_rgb(en_bytes)
                    ja_text = f"[RGB:{en_text}]"
            elif stype == StringType.UNICODE:
                try:
                    en_text = en_bytes.decode('utf-16-le').rstrip('\x00')
                    ja_text = ja_bytes.decode('utf-16-le').rstrip('\x00')
                    patch_bytes = ja_bytes
                except:
                    en_text = f"[UNICODE]"
                    ja_text = f"[UNICODE]"
                    patch_bytes = ja_bytes
            else:
                # DEF, NOFF_TERM, FFPADDED, ZEROTERM - copy JA bytes
                en_text = decode_english(en_bytes)
                ja_text = encoder.decode_string(ja_bytes)
                # Check if this DEF entry is in keyboard region (BUTTON 9/10 are DEF but need offset)
                if i in KEYBOARD_REGION:
                    patch_bytes = apply_keyboard_offset(ja_bytes)
                    rgb_decoded = ''.join(chr(b - 0x73) if 0x93 <= b <= 0xED else ('?' if b not in (0x00, 0xFF) else '') for b in ja_bytes)
                    ja_text = f"[KB:{rgb_decoded.strip()}]"
                # Check if this DEF entry is a save slot (Save 1-2 are DEF type)
                elif i in SAVE_SLOT_REGION:
                    patch_bytes = add_save_slot_spacing(ja_bytes, length)
                # Shop menu "Buy Sell Exit" needs extra spacing
                elif i == SHOP_MENU_INDEX:
                    patch_bytes = fix_shop_menu_spacing(ja_bytes, length)
                    ja_text = "かう　　うる　　　でる"
                # Item/Materia column header needs extra spacing
                elif i == ITEM_MATERIA_INDEX:
                    patch_bytes = fix_item_materia_spacing(ja_bytes, length)
                    ja_text = "アイテム　　　　マテリア"
                else:
                    patch_bytes = ja_bytes

            # Skip if both are empty or identical
            if not en_text.strip() and not ja_text.strip():
                continue

            # Skip if patch bytes are identical to EN bytes (no change needed)
            if patch_bytes == en_bytes:
                continue

            patches.append(PatchEntry(
                index=i,
                en_offset=en_offset,
                ja_offset=ja_offset,
                en_text=en_text,
                ja_text=ja_text,
                length=length,
                string_type=StringType(stype),
                ja_bytes=patch_bytes  # Use patch_bytes instead of ja_bytes
            ))

    # Write HEXT file
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S JST")

    with open(output, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Japanese Menu Text Patch for FF7 English\n")
        f.write("# AUTO-GENERATED by generate_exe_hext.py\n")
        f.write(f"# Generated: {timestamp}\n")
        f.write(f"# Session: {session_id}\n")
        f.write("#\n")
        f.write(f"# Source EN exe: {en_exe.name}\n")
        f.write(f"# Source JA exe: {ja_exe.name}\n")
        f.write(f"# Total patches: {len(patches)}\n")
        f.write("#\n")
        f.write("# Virtual addresses calculated from file offsets:\n")
        f.write("# VA = (FileOffset - 0x3B8A00) + 0x3BA000 + 0x400000\n")
        f.write("#\n")
        f.write("# Offset table from touphScript ff7exe.cpp\n")
        f.write("# JA offset = EN offset + 0xC00\n")
        f.write("\n")

        # Group patches by section (every 20)
        section_size = 20
        for section_start in range(0, len(patches), section_size):
            section_end = min(section_start + section_size, len(patches))
            f.write(f"# {'=' * 60}\n")
            f.write(f"# Strings #{section_start + 1} - #{section_end}\n")
            f.write(f"# {'=' * 60}\n\n")

            for patch in patches[section_start:section_end]:
                va = file_offset_to_va(patch.en_offset)
                va_hex = f"{va:06X}"

                # Format bytes as hex string
                bytes_hex = ' '.join(f'{b:02X}' for b in patch.ja_bytes)

                # Truncate text for display
                en_display = patch.en_text[:25] + "..." if len(patch.en_text) > 25 else patch.en_text
                ja_display = patch.ja_text[:25] + "..." if len(patch.ja_text) > 25 else patch.ja_text

                f.write(f"# {en_display} -> {ja_display}\n")
                f.write(f"# EN: 0x{patch.en_offset:08X} ({patch.length} bytes)\n")
                f.write(f"# JA: 0x{patch.ja_offset:08X}\n")
                f.write(f"{va_hex} = {bytes_hex}\n\n")

    print(f"Generated {len(patches)} patches to {output}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate HEXT patches for Japanese menu text',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('en_exe', type=Path, help='Path to ff7_en.exe')
    parser.add_argument('ja_exe', type=Path, help='Path to ff7_ja.exe')
    parser.add_argument('-o', '--output', type=Path, required=True, help='Output HEXT file')
    parser.add_argument('--session', type=str, default='unknown', help='Session ID for header')

    args = parser.parse_args()

    if not args.en_exe.exists():
        print(f"Error: {args.en_exe} not found", file=sys.stderr)
        sys.exit(1)
    if not args.ja_exe.exists():
        print(f"Error: {args.ja_exe} not found", file=sys.stderr)
        sys.exit(1)

    encoder = FF7CharacterEncoder()
    generate_hext(args.en_exe, args.ja_exe, args.output, encoder, args.session)


if __name__ == '__main__':
    main()
