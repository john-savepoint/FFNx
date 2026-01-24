#!/usr/bin/env python3
"""
FF7 Executable Full Analyzer

This script performs a comprehensive analysis of FF7 executables to:
1. Dump ALL text strings (both FF7-encoded and ASCII/Shift-JIS)
2. Analyze PE sections to understand size differences
3. Compare EN vs JA executables

Created: 2025-12-06 16:15 JST
Session: 0681f78b-0382-45ee-898b-5a32b7ce32d5
Context: Investigating why ff7_ja.exe (24MB) is ~4x larger than ff7_en.exe (6.4MB)

Usage:
    python3 exe_full_analyzer.py <exe_path> [--compare <other_exe>] [--strings-only] [--sections-only]

Examples:
    # Full analysis of Japanese exe
    python3 exe_full_analyzer.py "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_ja.exe"

    # Compare both executables
    python3 exe_full_analyzer.py "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe" --compare "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_ja.exe"
"""

import sys
import argparse
import struct
from pathlib import Path
from collections import defaultdict


def parse_pe_header(data: bytes) -> dict:
    """Parse PE header to get section information."""
    # Check DOS header
    if data[:2] != b'MZ':
        return None

    # Get PE header offset from DOS header at offset 0x3C
    pe_offset = struct.unpack('<I', data[0x3C:0x40])[0]

    # Check PE signature
    if data[pe_offset:pe_offset+4] != b'PE\x00\x00':
        return None

    # COFF header starts after PE signature
    coff_offset = pe_offset + 4

    # Parse COFF header
    machine = struct.unpack('<H', data[coff_offset:coff_offset+2])[0]
    num_sections = struct.unpack('<H', data[coff_offset+2:coff_offset+4])[0]
    timestamp = struct.unpack('<I', data[coff_offset+4:coff_offset+8])[0]
    optional_header_size = struct.unpack('<H', data[coff_offset+16:coff_offset+18])[0]

    # Optional header
    optional_offset = coff_offset + 20
    magic = struct.unpack('<H', data[optional_offset:optional_offset+2])[0]

    # Section table starts after optional header
    section_table_offset = optional_offset + optional_header_size

    sections = []
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)

        name = data[section_offset:section_offset+8].rstrip(b'\x00').decode('ascii', errors='replace')
        virtual_size = struct.unpack('<I', data[section_offset+8:section_offset+12])[0]
        virtual_addr = struct.unpack('<I', data[section_offset+12:section_offset+16])[0]
        raw_size = struct.unpack('<I', data[section_offset+16:section_offset+20])[0]
        raw_offset = struct.unpack('<I', data[section_offset+20:section_offset+24])[0]
        characteristics = struct.unpack('<I', data[section_offset+36:section_offset+40])[0]

        sections.append({
            'name': name,
            'virtual_size': virtual_size,
            'virtual_addr': virtual_addr,
            'raw_size': raw_size,
            'raw_offset': raw_offset,
            'characteristics': characteristics
        })

    return {
        'pe_offset': pe_offset,
        'machine': machine,
        'num_sections': num_sections,
        'timestamp': timestamp,
        'optional_header_size': optional_header_size,
        'magic': magic,
        'sections': sections
    }


def find_all_strings(data: bytes, min_length: int = 4) -> dict:
    """
    Find all strings in the executable.
    Returns categorized strings by type.
    """
    strings = {
        'ff7_encoded': [],      # FF7 custom encoding (0x00-0xFE, terminated by 0xFF)
        'ascii': [],            # Standard ASCII/Latin-1
        'shift_jis': [],        # Japanese Shift-JIS
        'unicode': [],          # UTF-16 LE
    }

    # Find FF7-encoded strings (terminated by 0xFF)
    i = 0
    while i < len(data) - min_length:
        # Look for FF7 string pattern
        if data[i] != 0x00 and data[i] != 0xFF:
            # Potential string start
            j = i
            valid_ff7 = True

            while j < len(data) and data[j] != 0xFF:
                # FF7 encoding uses 0x00-0xFE range
                # Valid printable chars roughly in 0x01-0x5F range for English
                # Japanese uses multi-byte with 0xFA-0xFE prefixes
                if data[j] > 0xFE:
                    valid_ff7 = False
                    break
                j += 1

            if valid_ff7 and j < len(data) and data[j] == 0xFF:
                length = j - i + 1
                if length >= min_length:
                    strings['ff7_encoded'].append({
                        'offset': i,
                        'length': length,
                        'data': data[i:j+1]
                    })
                i = j + 1
                continue
        i += 1

    # Find ASCII strings (printable characters terminated by null)
    i = 0
    while i < len(data) - min_length:
        if 0x20 <= data[i] <= 0x7E:  # Printable ASCII
            j = i
            while j < len(data) and 0x20 <= data[j] <= 0x7E:
                j += 1

            # Check for null terminator
            if j < len(data) and data[j] == 0x00:
                length = j - i
                if length >= min_length:
                    try:
                        text = data[i:j].decode('ascii')
                        strings['ascii'].append({
                            'offset': i,
                            'length': length,
                            'text': text
                        })
                    except:
                        pass
                i = j + 1
                continue
        i += 1

    # Find Shift-JIS strings
    i = 0
    while i < len(data) - min_length:
        # Shift-JIS first byte ranges: 0x81-0x9F, 0xE0-0xEF (double-byte)
        # or 0x20-0x7E, 0xA1-0xDF (single-byte)
        if (0x81 <= data[i] <= 0x9F) or (0xE0 <= data[i] <= 0xEF):
            j = i
            valid_sjis = True

            while j < len(data) - 1:
                b = data[j]
                if b == 0x00:
                    break
                elif (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF):
                    # Double-byte character
                    j += 2
                elif (0x20 <= b <= 0x7E) or (0xA1 <= b <= 0xDF):
                    # Single-byte character
                    j += 1
                else:
                    valid_sjis = False
                    break

            if valid_sjis and j > i + min_length:
                try:
                    text = data[i:j].decode('shift_jis')
                    if len(text) >= min_length // 2:
                        strings['shift_jis'].append({
                            'offset': i,
                            'length': j - i,
                            'text': text
                        })
                except:
                    pass
            i = j if j > i else i + 1
        else:
            i += 1

    # Find UTF-16 LE strings
    i = 0
    while i < len(data) - (min_length * 2):
        # Look for pattern of ASCII char + 0x00 (UTF-16 LE)
        if 0x20 <= data[i] <= 0x7E and i + 1 < len(data) and data[i+1] == 0x00:
            j = i
            valid_utf16 = True

            while j < len(data) - 1:
                if data[j] == 0x00 and data[j+1] == 0x00:
                    break
                if not (0x20 <= data[j] <= 0x7E or (0x00 <= data[j] <= 0xFF and data[j+1] == 0x00)):
                    valid_utf16 = False
                    break
                j += 2

            if valid_utf16 and (j - i) >= min_length * 2:
                try:
                    text = data[i:j].decode('utf-16-le')
                    if len(text) >= min_length:
                        strings['unicode'].append({
                            'offset': i,
                            'length': j - i,
                            'text': text
                        })
                except:
                    pass
            i = j if j > i else i + 2
        else:
            i += 1

    return strings


def decode_ff7_english_char(byte: int) -> str:
    """Decode FF7 English character."""
    if byte == 0x00:
        return ' '
    if byte == 0xFF:
        return ''

    ascii_val = byte + 0x20
    if 0x20 <= ascii_val <= 0x7E:
        return chr(ascii_val)

    special = {0x1F: '?', 0x0E: '.', 0x01: '!'}
    if byte in special:
        return special[byte]

    return f'[{byte:02X}]'


def decode_ff7_string(data: bytes) -> str:
    """Decode FF7-encoded string."""
    result = []
    for b in data:
        if b == 0xFF:
            break
        result.append(decode_ff7_english_char(b))
    return ''.join(result)


def analyze_data_patterns(data: bytes, section_name: str) -> dict:
    """Analyze what kind of data is in a section."""
    analysis = {
        'null_bytes': 0,
        'ff_bytes': 0,
        'high_entropy_blocks': 0,
        'low_entropy_blocks': 0,
        'potential_images': 0,
        'potential_code': 0,
    }

    block_size = 4096
    for i in range(0, len(data), block_size):
        block = data[i:i+block_size]
        if len(block) < block_size:
            continue

        # Count byte frequencies
        freq = defaultdict(int)
        for b in block:
            freq[b] += 1

        # Check for patterns
        null_ratio = freq[0] / len(block)
        ff_ratio = freq[0xFF] / len(block)

        if null_ratio > 0.5:
            analysis['null_bytes'] += len(block)
        if ff_ratio > 0.3:
            analysis['ff_bytes'] += len(block)

        # Entropy estimation
        unique_bytes = len(freq)
        if unique_bytes > 200:
            analysis['high_entropy_blocks'] += 1
        elif unique_bytes < 50:
            analysis['low_entropy_blocks'] += 1

        # Image patterns (look for texture headers, bitmap patterns)
        if block[:4] in (b'DDS ', b'BM', b'\x89PNG'):
            analysis['potential_images'] += 1

        # Code patterns (look for common x86 opcodes)
        code_opcodes = [0x55, 0x8B, 0x89, 0xE8, 0xC3, 0x90]
        code_count = sum(freq[op] for op in code_opcodes)
        if code_count > len(block) * 0.1:
            analysis['potential_code'] += 1

    return analysis


def format_size(size: int) -> str:
    """Format byte size for display."""
    if size >= 1024 * 1024:
        return f"{size / (1024*1024):.2f} MB"
    elif size >= 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size} bytes"


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive FF7 executable analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('exe_path', help='Path to FF7 executable')
    parser.add_argument('--compare', dest='compare_path', help='Path to second exe for comparison')
    parser.add_argument('--strings-only', action='store_true', help='Only dump strings')
    parser.add_argument('--sections-only', action='store_true', help='Only show PE sections')
    parser.add_argument('--min-length', type=int, default=4, help='Minimum string length (default: 4)')
    parser.add_argument('--output', '-o', help='Output file for strings')

    args = parser.parse_args()

    exe_path = Path(args.exe_path)
    if not exe_path.exists():
        print(f"Error: File not found: {exe_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {exe_path.name}...")
    with open(exe_path, 'rb') as f:
        data = f.read()

    file_size = len(data)
    print(f"File size: {format_size(file_size)}")
    print()

    # Parse PE header
    pe_info = parse_pe_header(data)

    if pe_info:
        print("=" * 80)
        print("PE SECTION ANALYSIS")
        print("=" * 80)
        print()
        print(f"{'Section':<10} {'Virtual Size':<15} {'Raw Size':<15} {'Raw Offset':<12} {'Characteristics'}")
        print("-" * 80)

        total_raw = 0
        for section in pe_info['sections']:
            char_str = ""
            chars = section['characteristics']
            if chars & 0x20000000:
                char_str += "EXEC "
            if chars & 0x40000000:
                char_str += "READ "
            if chars & 0x80000000:
                char_str += "WRITE "
            if chars & 0x00000020:
                char_str += "CODE "
            if chars & 0x00000040:
                char_str += "IDATA "
            if chars & 0x00000080:
                char_str += "UDATA "

            print(f"{section['name']:<10} {format_size(section['virtual_size']):<15} {format_size(section['raw_size']):<15} 0x{section['raw_offset']:08X}   {char_str}")
            total_raw += section['raw_size']

        print("-" * 80)
        print(f"{'TOTAL':<10} {'':<15} {format_size(total_raw):<15}")
        print()

        # Analyze each section
        print("=" * 80)
        print("SECTION CONTENT ANALYSIS")
        print("=" * 80)
        print()

        for section in pe_info['sections']:
            start = section['raw_offset']
            size = section['raw_size']
            section_data = data[start:start+size]

            analysis = analyze_data_patterns(section_data, section['name'])

            print(f"Section: {section['name']}")
            print(f"  Size: {format_size(size)}")
            print(f"  Null bytes: {format_size(analysis['null_bytes'])} ({100*analysis['null_bytes']/size:.1f}%)" if size > 0 else "")
            print(f"  High-entropy blocks: {analysis['high_entropy_blocks']}")
            print(f"  Low-entropy blocks: {analysis['low_entropy_blocks']}")
            print(f"  Potential code blocks: {analysis['potential_code']}")
            print(f"  Potential image blocks: {analysis['potential_images']}")
            print()

    if args.sections_only:
        return

    # Find all strings
    print("=" * 80)
    print("STRING ANALYSIS")
    print("=" * 80)
    print()
    print("Scanning for strings (this may take a moment)...")

    strings = find_all_strings(data, min_length=args.min_length)

    print()
    print("String counts by type:")
    print(f"  FF7-encoded strings: {len(strings['ff7_encoded'])}")
    print(f"  ASCII strings: {len(strings['ascii'])}")
    print(f"  Shift-JIS strings: {len(strings['shift_jis'])}")
    print(f"  Unicode (UTF-16) strings: {len(strings['unicode'])}")
    print()

    # Output strings
    output = sys.stdout
    if args.output:
        output = open(args.output, 'w', encoding='utf-8')

    # FF7-encoded strings
    if strings['ff7_encoded']:
        print("=" * 80, file=output)
        print("FF7-ENCODED STRINGS", file=output)
        print("=" * 80, file=output)
        print(file=output)
        print(f"{'Offset':<12} {'Length':<8} {'Decoded':<50} Raw Hex", file=output)
        print("-" * 100, file=output)

        for s in strings['ff7_encoded'][:500]:  # Limit output
            decoded = decode_ff7_string(s['data'])
            decoded_display = decoded[:48] + '..' if len(decoded) > 50 else decoded
            hex_display = ' '.join(f'{b:02X}' for b in s['data'][:16])
            if len(s['data']) > 16:
                hex_display += ' ...'
            print(f"0x{s['offset']:08X}   {s['length']:<8} {decoded_display:<50} {hex_display}", file=output)

        if len(strings['ff7_encoded']) > 500:
            print(f"\n... and {len(strings['ff7_encoded']) - 500} more FF7-encoded strings", file=output)
        print(file=output)

    # ASCII strings
    if strings['ascii']:
        print("=" * 80, file=output)
        print("ASCII STRINGS", file=output)
        print("=" * 80, file=output)
        print(file=output)
        print(f"{'Offset':<12} {'Length':<8} Text", file=output)
        print("-" * 80, file=output)

        for s in strings['ascii'][:500]:
            text_display = s['text'][:70] + '..' if len(s['text']) > 70 else s['text']
            print(f"0x{s['offset']:08X}   {s['length']:<8} {text_display}", file=output)

        if len(strings['ascii']) > 500:
            print(f"\n... and {len(strings['ascii']) - 500} more ASCII strings", file=output)
        print(file=output)

    # Shift-JIS strings
    if strings['shift_jis']:
        print("=" * 80, file=output)
        print("SHIFT-JIS STRINGS (Japanese)", file=output)
        print("=" * 80, file=output)
        print(file=output)
        print(f"{'Offset':<12} {'Length':<8} Text", file=output)
        print("-" * 80, file=output)

        for s in strings['shift_jis'][:500]:
            text_display = s['text'][:50] + '..' if len(s['text']) > 50 else s['text']
            print(f"0x{s['offset']:08X}   {s['length']:<8} {text_display}", file=output)

        if len(strings['shift_jis']) > 500:
            print(f"\n... and {len(strings['shift_jis']) - 500} more Shift-JIS strings", file=output)
        print(file=output)

    # Unicode strings
    if strings['unicode']:
        print("=" * 80, file=output)
        print("UNICODE (UTF-16) STRINGS", file=output)
        print("=" * 80, file=output)
        print(file=output)
        print(f"{'Offset':<12} {'Length':<8} Text", file=output)
        print("-" * 80, file=output)

        for s in strings['unicode'][:200]:
            text_display = s['text'][:60] + '..' if len(s['text']) > 60 else s['text']
            print(f"0x{s['offset']:08X}   {s['length']:<8} {text_display}", file=output)

        if len(strings['unicode']) > 200:
            print(f"\n... and {len(strings['unicode']) - 200} more Unicode strings", file=output)

    if args.output:
        output.close()
        print(f"\nStrings written to: {args.output}")

    # Comparison mode
    if args.compare_path:
        compare_path = Path(args.compare_path)
        if compare_path.exists():
            print()
            print("=" * 80)
            print(f"COMPARISON WITH {compare_path.name}")
            print("=" * 80)
            print()

            with open(compare_path, 'rb') as f:
                compare_data = f.read()

            compare_size = len(compare_data)
            size_diff = compare_size - file_size

            print(f"{exe_path.name}: {format_size(file_size)}")
            print(f"{compare_path.name}: {format_size(compare_size)}")
            print(f"Difference: {format_size(abs(size_diff))} ({'larger' if size_diff > 0 else 'smaller'})")
            print()

            compare_pe = parse_pe_header(compare_data)
            if compare_pe and pe_info:
                print("Section size comparison:")
                print(f"{'Section':<10} {exe_path.name:<15} {compare_path.name:<15} Difference")
                print("-" * 60)

                sections1 = {s['name']: s for s in pe_info['sections']}
                sections2 = {s['name']: s for s in compare_pe['sections']}

                all_sections = set(sections1.keys()) | set(sections2.keys())

                for name in sorted(all_sections):
                    size1 = sections1.get(name, {}).get('raw_size', 0)
                    size2 = sections2.get(name, {}).get('raw_size', 0)
                    diff = size2 - size1
                    diff_str = f"+{format_size(diff)}" if diff > 0 else f"-{format_size(abs(diff))}" if diff < 0 else "same"
                    print(f"{name:<10} {format_size(size1):<15} {format_size(size2):<15} {diff_str}")


if __name__ == '__main__':
    main()
