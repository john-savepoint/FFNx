#!/usr/bin/env python3
"""
FF7 Executable String Dumper

This script reads a section of the FF7 executable and displays all strings
with their EXACT byte positions, making it easy to identify the correct
addresses for HEXT patches.

Created: 2025-12-05 21:50 JST
Session: c245e7c0-ec73-4933-b925-5976860e742c
Context: Created to solve repeated offset calculation errors when creating
         HEXT patches. The issue was assuming strings start at xxd line
         addresses instead of counting to the actual first byte.

Usage:
    python3 exe_string_dumper.py <exe_path> <start_offset> <length> [--ja <ja_exe_path>]

Examples:
    # Dump Materia screen region from EN exe
    python3 exe_string_dumper.py "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe" 0x51F500 0x500

    # Compare with JA exe (adds 0xC00 offset automatically)
    python3 exe_string_dumper.py "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe" 0x51F500 0x500 --ja "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_ja.exe"
"""

import sys
import argparse
from pathlib import Path


def file_to_va(file_offset: int) -> int:
    """Convert file offset to Virtual Address for FF7 menu strings."""
    return (file_offset - 0x3B8A00) + 0x3BA000 + 0x400000


def load_japanese_charmap(csv_path: str = None) -> dict:
    """Load the Japanese character map from CSV."""
    if csv_path is None:
        # Default path relative to script
        script_dir = Path(__file__).parent.parent
        csv_path = script_dir / "docs" / "character_maps" / "ff7_complete_mapping_compact.csv"

    charmap = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            import csv
            reader = csv.DictReader(f)
            for row in reader:
                texture = row['texture']
                index = int(row['index'])
                char = row['character']

                if texture == 'jafont_1':
                    charmap[index] = char
                elif texture == 'jafont_2':
                    charmap[(0xFA, index)] = char
                elif texture == 'jafont_3':
                    charmap[(0xFB, index)] = char
                elif texture == 'jafont_4':
                    charmap[(0xFC, index)] = char
                elif texture == 'jafont_5':
                    charmap[(0xFD, index)] = char
                elif texture == 'jafont_6':
                    charmap[(0xFE, index)] = char
    except FileNotFoundError:
        pass  # Will use fallback decoding

    return charmap


# Global charmap - loaded once
JA_CHARMAP = {}


def decode_ff7_english_char(byte: int) -> str:
    """
    Decode a single FF7 ENGLISH character byte.

    FF7 English encoding is ASCII - 0x20:
    - 0x21 = A (ASCII 0x41 - 0x20)
    - 0x22 = B (ASCII 0x42 - 0x20)
    - etc.
    """
    # Space
    if byte == 0x00:
        return ' '
    # Terminator
    if byte == 0xFF:
        return ''

    # Convert FF7 encoding to ASCII by adding 0x20
    ascii_val = byte + 0x20

    # If it's a printable ASCII character, return it
    if 0x20 <= ascii_val <= 0x7E:
        return chr(ascii_val)

    # Special cases that don't follow the +0x20 rule
    if byte == 0x1F:
        return '?'
    if byte == 0x0E:
        return '.'
    if byte == 0x01:
        return '!'

    # Unknown - show hex
    return f'[{byte:02X}]'


def decode_ff7_japanese_char(byte: int, next_byte: int = None) -> tuple:
    """
    Decode FF7 JAPANESE character byte(s).
    Returns (decoded_char, bytes_consumed)
    """
    global JA_CHARMAP

    # Two-byte sequences (FA-FE prefix)
    if byte in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) and next_byte is not None:
        key = (byte, next_byte)
        if key in JA_CHARMAP:
            return (JA_CHARMAP[key], 2)
        else:
            prefix_names = {0xFA: '2', 0xFB: '3', 0xFC: '4', 0xFD: '5', 0xFE: '6'}
            return (f'[jf{prefix_names[byte]}:{next_byte:02X}]', 2)

    # Single byte from jafont_1
    if byte in JA_CHARMAP:
        return (JA_CHARMAP[byte], 1)

    # Space
    if byte == 0x00:
        return (' ', 1)

    # Terminator
    if byte == 0xFF:
        return ('', 1)

    # Unknown
    return (f'[{byte:02X}]', 1)


def decode_ff7_string(data: bytes, is_japanese: bool = False) -> str:
    """Decode FF7 encoded string to readable form."""
    result = []
    i = 0

    while i < len(data):
        byte = data[i]
        if byte == 0xFF:
            break

        if is_japanese:
            next_byte = data[i + 1] if i + 1 < len(data) else None
            char, consumed = decode_ff7_japanese_char(byte, next_byte)
            result.append(char)
            i += consumed
        else:
            result.append(decode_ff7_english_char(byte))
            i += 1

    return ''.join(result)


def find_strings(data: bytes, base_offset: int, is_japanese: bool = False) -> list:
    """
    Find all strings in the data section.
    Returns list of (file_offset, va, raw_bytes, decoded_string, length)
    """
    strings = []
    i = 0

    while i < len(data):
        # Skip null bytes to find string start
        if data[i] == 0x00:
            i += 1
            continue

        # Found start of potential string
        string_start = i
        file_offset = base_offset + string_start

        # Find the end (0xFF terminator)
        j = i
        while j < len(data) and data[j] != 0xFF:
            j += 1

        if j < len(data) and data[j] == 0xFF:
            # Found a valid string
            string_bytes = data[string_start:j+1]  # Include terminator

            # Only include if it looks like a real string (not just random bytes)
            if len(string_bytes) >= 2:  # At least 1 char + terminator
                va = file_to_va(file_offset)
                decoded = decode_ff7_string(string_bytes, is_japanese=is_japanese)
                strings.append({
                    'file_offset': file_offset,
                    'va': va,
                    'raw_bytes': string_bytes,
                    'decoded': decoded,
                    'length': len(string_bytes)
                })

            i = j + 1
        else:
            i += 1

    return strings


def format_bytes(data: bytes, max_display: int = 24) -> str:
    """Format bytes for display."""
    hex_str = ' '.join(f'{b:02X}' for b in data[:max_display])
    if len(data) > max_display:
        hex_str += ' ...'
    return hex_str


def main():
    global JA_CHARMAP

    # Load Japanese character map for JA decoding (do this first, before any use)
    JA_CHARMAP = load_japanese_charmap()

    parser = argparse.ArgumentParser(
        description='Dump FF7 executable strings with exact byte positions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Materia screen (EN):
    python3 exe_string_dumper.py "ff7_en.exe" 0x51F500 0x500

  Status screen (EN):
    python3 exe_string_dumper.py "ff7_en.exe" 0x51F200 0x200

  Config screen (EN):
    python3 exe_string_dumper.py "ff7_en.exe" 0x5188A0 0x800

  With Japanese comparison:
    python3 exe_string_dumper.py "ff7_en.exe" 0x51F500 0x500 --ja "ff7_ja.exe"
        """
    )
    parser.add_argument('exe_path', help='Path to FF7 executable')
    parser.add_argument('start_offset', help='Start offset in hex (e.g., 0x51F500)')
    parser.add_argument('length', help='Number of bytes to read in hex (e.g., 0x500)')
    parser.add_argument('--ja', dest='ja_exe_path', help='Path to Japanese exe for comparison')
    parser.add_argument('--raw', action='store_true', help='Show raw hex dump as well')

    args = parser.parse_args()

    # Parse hex values
    start_offset = int(args.start_offset, 16)
    length = int(args.length, 16)

    # Read EN executable
    exe_path = Path(args.exe_path)
    if not exe_path.exists():
        print(f"Error: File not found: {exe_path}", file=sys.stderr)
        sys.exit(1)

    with open(exe_path, 'rb') as f:
        f.seek(start_offset)
        data = f.read(length)

    print("=" * 80)
    print(f"FF7 String Dump (ENGLISH): {exe_path.name}")
    print(f"Region: File 0x{start_offset:X} - 0x{start_offset + length:X}")
    print(f"        VA   0x{file_to_va(start_offset):X} - 0x{file_to_va(start_offset + length):X}")
    print("=" * 80)
    print()

    # Find and display strings (English decoding)
    strings = find_strings(data, start_offset, is_japanese=False)

    print(f"Found {len(strings)} strings:\n")
    print(f"{'File Offset':<14} {'VA':<12} {'Len':<5} {'Decoded':<30} Bytes")
    print("-" * 100)

    for s in strings:
        decoded_display = s['decoded'][:28] + '..' if len(s['decoded']) > 30 else s['decoded']
        print(f"0x{s['file_offset']:08X}   0x{s['va']:06X}   {s['length']:<5} {decoded_display:<30} {format_bytes(s['raw_bytes'])}")

    # If JA exe provided, show comparison
    if args.ja_exe_path:
        ja_path = Path(args.ja_exe_path)
        if ja_path.exists():
            ja_offset = start_offset + 0xC00  # JA is typically 0xC00 ahead

            print()
            print("=" * 80)
            print(f"FF7 String Dump (JAPANESE): {ja_path.name}")
            print(f"Region: File 0x{ja_offset:X} - 0x{ja_offset + length:X} (EN offset + 0xC00)")
            print("=" * 80)
            print()

            with open(ja_path, 'rb') as f:
                f.seek(ja_offset)
                ja_data = f.read(length)

            ja_strings = find_strings(ja_data, ja_offset, is_japanese=True)

            print(f"Found {len(ja_strings)} strings:\n")
            print(f"{'JA File Offset':<14} {'Len':<5} {'Decoded':<30} Bytes (for HEXT patch)")
            print("-" * 100)

            for s in ja_strings:
                decoded_display = s['decoded'][:28] + '..' if len(s['decoded']) > 30 else s['decoded']
                print(f"0x{s['file_offset']:08X}       {s['length']:<5} {decoded_display:<30} {format_bytes(s['raw_bytes'])}")

    # Raw hex dump if requested
    if args.raw:
        print()
        print("=" * 80)
        print("Raw Hex Dump (with FF7 English decoding)")
        print("=" * 80)
        for i in range(0, len(data), 16):
            addr = start_offset + i
            hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
            # Use FF7 English decoding instead of ASCII
            ff7_part = ''.join(decode_ff7_english_char(b) if b != 0xFF else '.' for b in data[i:i+16])
            print(f"{addr:08X}: {hex_part:<48} {ff7_part}")


if __name__ == '__main__':
    main()
