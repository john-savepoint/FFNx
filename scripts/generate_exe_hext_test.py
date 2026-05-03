#!/usr/bin/env python3
"""
FF7 HEXT Generator - TEST VERSION with keyboard byte experiments

This version applies various test transformations to keyboard bytes to help
identify patterns in the rendering behavior.

Created: 2025-12-08 14:05 JST (Monday)
Session-ID: 0681f78b-0382-45ee-898b-5a32b7ce32d5
"""

import sys
import argparse
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum

# Import the base arrays from the main script
sys.path.insert(0, str(Path(__file__).parent))
from generate_exe_hext import (
    EN_OFFSETS, STRING_LENGTHS, STRING_TYPES, StringType,
    JA_OFFSET_DELTA, SKIP_REGIONS, RGB_SKIP_REGIONS,
    FF7CharacterEncoder, file_offset_to_va, decode_english
)

# Test modes for keyboard region
TEST_MODES = {
    "ja_copy": "Copy JA bytes directly (current behavior)",
    "en_copy": "Copy EN bytes directly (original English)",
    "en_rgb": "Apply RGB encoding (+0x93) to EN bytes",
    "zeros": "All zeros (should show spaces)",
    "sequential": "Sequential bytes 0x00-0xFF to see pattern",
    "ff7_ja": "Use FF7 Japanese encoding for test text",
    "offset_minus": "JA bytes minus 0x20 (shift down)",
    "offset_plus": "JA bytes plus 0x20 (shift up)",
}


def encode_rgb(data: bytes) -> bytes:
    """Apply RGB encoding: FF7_byte + 0x93 to map to fullwidth positions."""
    result = bytearray()
    for byte in data:
        if byte == 0x00:
            result.append(0x00)
        elif byte == 0xFF:
            result.append(0xFF)
        elif 0x21 <= byte <= 0x3A:
            result.append(byte + 0x93)
        elif 0x41 <= byte <= 0x5A:
            result.append(byte - 0x20 + 0x93)
        elif 0x01 <= byte <= 0x5F:
            result.append(byte + 0x93)
        else:
            result.append(byte)
    return bytes(result)


def apply_test_mode(en_bytes: bytes, ja_bytes: bytes, mode: str, index: int) -> Tuple[bytes, str]:
    """Apply test transformation to keyboard bytes."""

    if mode == "ja_copy":
        return ja_bytes, "JA bytes copied"

    elif mode == "en_copy":
        return en_bytes, "EN bytes copied"

    elif mode == "en_rgb":
        return encode_rgb(en_bytes), "EN+RGB encoded"

    elif mode == "zeros":
        return bytes([0x00] * len(en_bytes)), "All zeros"

    elif mode == "sequential":
        # Use index to create sequential test values
        start = (index - 77) * 4  # Offset by keyboard start index
        result = bytearray()
        for i in range(len(en_bytes)):
            if i < len(en_bytes) - 2:  # Leave room for terminator
                result.append((start + i) % 256)
            else:
                result.append(0xFF if en_bytes[i] == 0xFF else 0x00)
        return bytes(result), f"Sequential from {start}"

    elif mode == "ff7_ja":
        # Write "テスト" (test) in FF7 Japanese encoding
        # テ=0x64, ス=0x59, ト=0x66 on jafont_1
        test_bytes = bytearray([0x64, 0x59, 0x66, 0xFF])
        # Pad to match length
        while len(test_bytes) < len(en_bytes):
            test_bytes.append(0x00)
        return bytes(test_bytes[:len(en_bytes)]), "FF7-JA: テスト"

    elif mode == "offset_minus":
        result = bytearray()
        for b in ja_bytes:
            if b == 0x00 or b == 0xFF:
                result.append(b)
            elif b >= 0x20:
                result.append(b - 0x20)
            else:
                result.append(b)
        return bytes(result), "JA-0x20"

    elif mode == "offset_plus":
        result = bytearray()
        for b in ja_bytes:
            if b == 0x00 or b == 0xFF:
                result.append(b)
            elif b <= 0xDF:
                result.append(b + 0x20)
            else:
                result.append(b)
        return bytes(result), "JA+0x20"

    else:
        return ja_bytes, "Unknown mode, using JA"


@dataclass
class PatchEntry:
    index: int
    en_offset: int
    ja_offset: int
    en_text: str
    ja_text: str
    length: int
    string_type: StringType
    patch_bytes: bytes
    test_note: str = ""


def generate_test_hext(en_exe: Path, ja_exe: Path, output: Path,
                       encoder: FF7CharacterEncoder, session_id: str,
                       keyboard_mode: str) -> None:
    """Generate HEXT patch file with test keyboard transformations."""

    patches: List[PatchEntry] = []

    # RGB regions that should copy JA bytes (save slots)
    RGB_COPY_JA_REGIONS = set(range(649, 658))

    with open(en_exe, 'rb') as en_f, open(ja_exe, 'rb') as ja_f:
        for i, (en_offset, length, stype) in enumerate(zip(EN_OFFSETS, STRING_LENGTHS, STRING_TYPES)):
            # Skip problematic regions (but NOT keyboard - we're testing those)
            if i in SKIP_REGIONS:
                continue

            if i in RGB_SKIP_REGIONS:
                continue

            if length <= 1:
                continue

            ja_offset = en_offset + JA_OFFSET_DELTA

            en_f.seek(en_offset)
            en_bytes = en_f.read(length)

            ja_f.seek(ja_offset)
            ja_bytes = ja_f.read(length)

            # Determine patch bytes based on region
            test_note = ""

            if 77 <= i <= 211:
                # KEYBOARD REGION - apply test mode
                patch_bytes, test_note = apply_test_mode(en_bytes, ja_bytes, keyboard_mode, i)
                en_text = decode_english(en_bytes)
                ja_text = f"[TEST:{test_note}]"

            elif stype == StringType.RGB:
                if i in RGB_COPY_JA_REGIONS:
                    en_text = decode_english(en_bytes)
                    ja_text = encoder.decode_string(ja_bytes)
                    patch_bytes = ja_bytes
                else:
                    en_text = decode_english(en_bytes)
                    patch_bytes = encode_rgb(en_bytes)
                    ja_text = f"[RGB:{en_text}]"

            elif stype == StringType.UNICODE:
                try:
                    en_text = en_bytes.decode('utf-16-le').rstrip('\x00')
                    ja_text = ja_bytes.decode('utf-16-le').rstrip('\x00')
                    patch_bytes = ja_bytes
                except:
                    en_text = "[UNICODE]"
                    ja_text = "[UNICODE]"
                    patch_bytes = ja_bytes

            else:
                en_text = decode_english(en_bytes)
                ja_text = encoder.decode_string(ja_bytes)
                patch_bytes = ja_bytes

            if not en_text.strip() and not ja_text.strip():
                continue

            # For keyboard test region, always include even if bytes match
            if patch_bytes == en_bytes and not (77 <= i <= 211):
                continue

            patches.append(PatchEntry(
                index=i,
                en_offset=en_offset,
                ja_offset=ja_offset,
                en_text=en_text,
                ja_text=ja_text,
                length=length,
                string_type=StringType(stype),
                patch_bytes=patch_bytes,
                test_note=test_note
            ))

    # Write HEXT file
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S JST")

    with open(output, 'w', encoding='utf-8') as f:
        f.write("# Japanese Menu Text Patch for FF7 English\n")
        f.write("# TEST VERSION - Keyboard experiments\n")
        f.write(f"# Generated: {timestamp}\n")
        f.write(f"# Session: {session_id}\n")
        f.write(f"# Keyboard Mode: {keyboard_mode} - {TEST_MODES.get(keyboard_mode, 'Unknown')}\n")
        f.write("#\n")
        f.write(f"# Source EN exe: {en_exe.name}\n")
        f.write(f"# Source JA exe: {ja_exe.name}\n")
        f.write(f"# Total patches: {len(patches)}\n")
        f.write("#\n")
        f.write("# VA = (FileOffset - 0x3B8A00) + 0x3BA000 + 0x400000\n")
        f.write("\n")

        for patch in patches:
            va = file_offset_to_va(patch.en_offset)
            byte_str = ' '.join(f'{b:02X}' for b in patch.patch_bytes)

            # Truncate display text
            en_disp = patch.en_text[:20].replace('\n', ' ')
            ja_disp = patch.ja_text[:30].replace('\n', ' ')

            f.write(f"# {en_disp} -> {ja_disp}\n")
            if patch.test_note:
                f.write(f"# TEST: {patch.test_note}\n")
            f.write(f"# EN: 0x{patch.en_offset:08X} ({patch.length} bytes)\n")
            f.write(f"# JA: 0x{patch.ja_offset:08X}\n")
            f.write(f"{va:X} = {byte_str}\n\n")

    print(f"Generated {len(patches)} patches to {output}")
    print(f"Keyboard mode: {keyboard_mode} - {TEST_MODES.get(keyboard_mode, 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Generate test HEXT with keyboard experiments")
    parser.add_argument("en_exe", help="Path to English FF7 executable")
    parser.add_argument("ja_exe", help="Path to Japanese FF7 executable")
    parser.add_argument("-o", "--output", required=True, help="Output HEXT file path")
    parser.add_argument("--session", default="test", help="Session ID for tracking")
    parser.add_argument("--mode", choices=list(TEST_MODES.keys()), default="ja_copy",
                        help="Test mode for keyboard region")
    parser.add_argument("--list-modes", action="store_true", help="List available test modes")

    args = parser.parse_args()

    if args.list_modes:
        print("Available test modes for keyboard region:")
        for mode, desc in TEST_MODES.items():
            print(f"  {mode:15} - {desc}")
        return

    script_dir = Path(__file__).parent.parent
    charmap_path = script_dir / "docs" / "character_maps" / "ff7_complete_mapping_compact.csv"
    encoder = FF7CharacterEncoder(charmap_path)

    generate_test_hext(
        Path(args.en_exe),
        Path(args.ja_exe),
        Path(args.output),
        encoder,
        args.session,
        args.mode
    )


if __name__ == "__main__":
    main()
