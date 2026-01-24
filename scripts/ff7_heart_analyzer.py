#!/usr/bin/env python3
"""
FF7 Heart Symbol Analyzer

Created: 2025-12-10 15:06 JST
Author: Claude Code
Session-ID: 94f5f148-6c89-4d95-a0b5-104c7ebdd735

Purpose: Analyze the heart symbol (♥) encoding in FF7 Japanese field text
         and verify texture/width data readiness.

Context: Investigation into why heart symbols display in Japanese eStore version
         but not in FFNx. This script provides verification and analysis tools.

Key Discovery:
    - Heart (♥) = DIRECT BYTE 0xD9 (217)
    - NO PREFIX - rendered from jafont_1[217]
    - NOT FE D9 (that's a color code for white)

The Fix Required:
    In FFNx's japanese_text.cpp, line 336:
    charWidthData[0][217] must be changed from 0 to ~15

    BEFORE: 28, 27, 27, 29, 30, 12, 25, 22, 11, 0, 27, 23, 23, 23, 12, 22,
    AFTER:  28, 27, 27, 29, 30, 12, 25, 22, 11, 15, 27, 23, 23, 23, 12, 22,
                                                ^^

Usage:
    python3 ff7_heart_analyzer.py [--verify-texture] [--analyze-field FILE]
"""

import struct
import csv
import sys
from pathlib import Path

# Import from sibling module
try:
    from ff7_field_extractor import (
        lzs_decompress, read_lgp_toc, extract_lgp_file,
        decompress_field_file, search_pattern_in_data
    )
except ImportError:
    # Fallback: define minimal versions if import fails
    def lzs_decompress(data):
        if len(data) < 4:
            return data
        uncompressed_size = struct.unpack('<I', data[:4])[0]
        if uncompressed_size == 0 or uncompressed_size > 10000000:
            return data[4:]
        output = bytearray()
        pos = 4
        while len(output) < uncompressed_size and pos < len(data):
            control = data[pos]
            pos += 1
            for bit in range(8):
                if len(output) >= uncompressed_size or pos >= len(data):
                    break
                if control & (1 << bit):
                    output.append(data[pos])
                    pos += 1
                else:
                    if pos + 1 >= len(data):
                        break
                    ref1, ref2 = data[pos], data[pos + 1]
                    pos += 2
                    offset = ((ref2 & 0xF0) << 4) | ref1
                    length = (ref2 & 0x0F) + 3
                    if offset == 0:
                        offset = 4096
                    src_pos = len(output) - offset
                    for i in range(length):
                        if len(output) >= uncompressed_size:
                            break
                        if src_pos + i >= 0 and src_pos + i < len(output):
                            output.append(output[src_pos + i])
                        else:
                            output.append(0)
        return bytes(output)


# Configuration paths
LGP_PATH = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/data/field/jfleve.lgp"
CHARMAP_PATH = "/home/johnzealanddoyle/projects/ff7OG_japanese/docs/character_maps/ff7_complete_mapping_compact.csv"
JAFONT1_PATH = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/mods/Textures/menu/jafont_1.png"


def load_character_map(csv_path: str) -> dict:
    """Load FF7 character mapping from CSV."""
    char_map = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            texture = row['texture']
            index = int(row['index'])
            char = row['character']

            if texture == 'jafont_1':
                char_map[index] = (char, 'jafont_1', 'direct')
            elif texture == 'jafont_2':
                char_map[(0xFA, index)] = (char, 'jafont_2', 'FA')
            elif texture == 'jafont_3':
                char_map[(0xFB, index)] = (char, 'jafont_3', 'FB')
            elif texture == 'jafont_4':
                char_map[(0xFC, index)] = (char, 'jafont_4', 'FC')
            elif texture == 'jafont_5':
                char_map[(0xFD, index)] = (char, 'jafont_5', 'FD')
            elif texture == 'jafont_6':
                char_map[(0xFE, index)] = (char, 'jafont_6', 'FE')

    return char_map


def decode_field_text(data: bytes, char_map: dict, start_pos: int, max_bytes: int = 100) -> str:
    """Decode FF7 field text bytes to readable string."""
    decoded = []
    pos = start_pos
    end_pos = min(start_pos + max_bytes, len(data))

    while pos < end_pos:
        byte = data[pos]

        # End of string
        if byte == 0xFF:
            decoded.append('[END]')
            break
        # Newline
        elif byte == 0xE7:
            decoded.append('\\n')
            pos += 1
            continue
        # Page break
        elif byte == 0xE8:
            decoded.append('[PAGE]')
            pos += 1
            continue
        # Control codes
        elif byte < 0x20:
            decoded.append(f'[{byte:02X}]')
            pos += 1
            continue

        # Multi-byte sequences (FA-FE prefixes)
        if byte >= 0xFA and byte <= 0xFE and pos + 1 < len(data):
            next_byte = data[pos + 1]
            key = (byte, next_byte)

            # Color codes under FE
            if byte == 0xFE:
                if 0xD2 <= next_byte <= 0xD9:
                    colors = ['gray', 'blue', 'red', 'purple', 'green', 'yellow', 'cyan', 'white']
                    decoded.append(f'[COLOR:{colors[next_byte-0xD2]}]')
                    pos += 2
                    continue
                elif next_byte == 0xDA:
                    decoded.append('[BLINK]')
                    pos += 2
                    continue
                elif next_byte == 0xDB:
                    decoded.append('[RAINBOW]')
                    pos += 2
                    continue

            if key in char_map:
                char, texture, prefix = char_map[key]
                decoded.append(char)
            else:
                decoded.append(f'[{byte:02X}{next_byte:02X}]')
            pos += 2
            continue

        # Direct byte from jafont_1
        if byte in char_map:
            char, texture, _ = char_map[byte]
            decoded.append(char)
        else:
            # Position 217 (0xD9) = Heart!
            if byte == 0xD9:
                decoded.append('♥')  # Heart!
            else:
                decoded.append(f'[{byte:02X}]')
        pos += 1

    return ''.join(decoded)


def analyze_heart_occurrences(lgp_path: str, char_map: dict):
    """Find and analyze all heart occurrences in field files."""
    print("=" * 70)
    print("HEART SYMBOL ANALYSIS")
    print("=" * 70)

    # Search pattern: 秘密 (often followed by heart)
    himitsu = bytes([0xFB, 0x23, 0xFD, 0x3D])

    # Key field file with Jessie's dialogue
    target_file = 'mds7_w2'

    with open(lgp_path, 'rb') as f:
        magic = f.read(12)
        num_files = struct.unpack('<I', f.read(4))[0]

        for i in range(num_files):
            fname = f.read(20).rstrip(b'\x00').decode('ascii', errors='ignore')
            offset = struct.unpack('<I', f.read(4))[0]
            f.read(3)

            if fname.lower() == target_file:
                f.seek(offset)
                f.read(20)
                file_size = struct.unpack('<I', f.read(4))[0]
                raw_data = f.read(file_size)
                break

    print(f"\nAnalyzing: {target_file}")
    print(f"Raw size: {len(raw_data)} bytes")

    # Decompress
    decompressed = lzs_decompress(raw_data)
    print(f"Decompressed size: {len(decompressed)} bytes")

    # Find 秘密 occurrences
    pos = 0
    occurrences = []
    while True:
        pos = decompressed.find(himitsu, pos)
        if pos == -1:
            break
        occurrences.append(pos)
        pos += 1

    print(f"\nFound {len(occurrences)} occurrences of 秘密")

    # Analyze each
    for i, occ_pos in enumerate(occurrences[:5]):  # First 5
        print(f"\n{'='*50}")
        print(f"Occurrence {i+1} at offset 0x{occ_pos:X}")
        print(f"{'='*50}")

        # Bytes after 秘密
        after_pos = occ_pos + 4
        after_bytes = decompressed[after_pos:after_pos+20]
        print(f"\nRaw bytes after 秘密:")
        print(f"  {' '.join(f'{b:02X}' for b in after_bytes)}")
        print(f"  First byte: 0x{after_bytes[0]:02X} = {after_bytes[0]}")

        if after_bytes[0] == 0xD9:
            print(f"  *** THIS IS THE HEART! (0xD9 = 217) ***")

        # Decode surrounding text
        start = max(0, occ_pos - 20)
        decoded = decode_field_text(decompressed, char_map, start, 80)
        print(f"\nDecoded text:")
        print(f"  {decoded}")


def verify_texture(jafont_path: str):
    """Verify heart glyph exists in jafont_1 texture."""
    print("\n" + "=" * 70)
    print("TEXTURE VERIFICATION")
    print("=" * 70)

    try:
        from PIL import Image

        img = Image.open(jafont_path)
        print(f"\nTexture: {jafont_path}")
        print(f"Size: {img.size}")
        print(f"Mode: {img.mode}")

        # Check position 217
        pos = 217
        row, col = pos // 16, pos % 16
        x, y = col * 64, row * 64  # Assuming 64x64 cells in high-res

        # Count non-transparent pixels
        if img.mode == 'RGBA':
            count = sum(1 for i in range(64) for j in range(64)
                       if x + i < img.width and y + j < img.height
                       and img.getpixel((x + i, y + j))[3] > 0)
        else:
            # For non-RGBA, count non-black pixels
            count = sum(1 for i in range(64) for j in range(64)
                       if x + i < img.width and y + j < img.height
                       and sum(img.getpixel((x + i, y + j))[:3]) > 0)

        coverage = count / (64*64) * 100

        print(f"\nPosition 217 (row {row}, col {col}):")
        print(f"  Cell coordinates: ({x}, {y})")
        print(f"  Non-transparent pixels: {count}")
        print(f"  Coverage: {coverage:.1f}%")

        if count > 0:
            print(f"  Status: ✓ Heart glyph IS present in texture")
        else:
            print(f"  Status: ✗ Position is EMPTY!")

    except ImportError:
        print("PIL not available - skipping texture verification")
    except FileNotFoundError:
        print(f"Texture not found: {jafont_path}")
    except Exception as e:
        print(f"Error: {e}")


def print_summary():
    """Print summary of findings."""
    print("\n" + "=" * 70)
    print("HEART SYMBOL ENCODING DISCOVERY - SUMMARY")
    print("=" * 70)

    print("""
## CONFIRMED FINDINGS

### Heart Encoding in Japanese Field Text:
   - Heart (♥) = DIRECT BYTE 0xD9 (217)
   - NO PREFIX - rendered from jafont_1[217]
   - NOT FE D9 (that's a color code for white)

### Example from mds7_w2 (Jessie's dialogue):
   Offset 0x903C: FE DB FB 23 FD 3D D9 FE DB 3F ...

   Decoded:
   - FE DB = Rainbow toggle ON
   - FB 23 = 秘 (jafont_3[35])
   - FD 3D = 密 (jafont_5[61])
   - D9    = ♥ (jafont_1[217]) <-- HEART!
   - FE DB = Rainbow toggle OFF
   - 3F    = Space

### Why Hearts Don't Display in FFNx:
   1. jafont_1[217] texture: NOW has heart glyph (we added it)
   2. FFNx charWidthData[0][217] = 0 (INVISIBLE!)
   3. Width of 0 means character renders with zero width

### The Fix Required:
   File: /mnt/c/FFNx/src/ff7/japanese_text.cpp
   Line: 336

   BEFORE: 28, 27, 27, 29, 30, 12, 25, 22, 11, 0, 27, 23, 23, 23, 12, 22,
   AFTER:  28, 27, 27, 29, 30, 12, 25, 22, 11, 15, 27, 23, 23, 23, 12, 22,
                                               ^^
   Change position 217's width from 0 to 15.
""")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='FF7 Heart Symbol Analyzer')
    parser.add_argument('--verify-texture', action='store_true',
                       help='Verify heart glyph in jafont_1 texture')
    parser.add_argument('--analyze-field', type=str, default='mds7_w2',
                       help='Field file to analyze (default: mds7_w2)')
    parser.add_argument('--summary', action='store_true',
                       help='Print summary only')
    args = parser.parse_args()

    if args.summary:
        print_summary()
        return

    # Load character map
    print("Loading character map...")
    try:
        char_map = load_character_map(CHARMAP_PATH)
        print(f"Loaded {len(char_map)} character mappings")
    except FileNotFoundError:
        print(f"Character map not found: {CHARMAP_PATH}")
        char_map = {}

    # Analyze heart occurrences
    try:
        analyze_heart_occurrences(LGP_PATH, char_map)
    except FileNotFoundError:
        print(f"LGP not found: {LGP_PATH}")

    # Verify texture if requested
    if args.verify_texture:
        verify_texture(JAFONT1_PATH)

    # Always print summary
    print_summary()


if __name__ == '__main__':
    main()
