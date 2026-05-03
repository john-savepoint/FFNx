#!/usr/bin/env python3
"""
FF7 EXE Spacing Analysis

Analyzes spacing patterns in EN vs JA executables to identify entries
that may need additional spacing for proper alignment.

Created: 2025-12-08 15:40 JST (Monday)
Session-ID: 0681f78b-0382-45ee-898b-5a32b7ce32d5
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from generate_exe_hext import (
    EN_OFFSETS, STRING_LENGTHS, STRING_TYPES, StringType,
    JA_OFFSET_DELTA, SKIP_REGIONS, RGB_SKIP_REGIONS, KEYBOARD_REGION
)


def count_spaces(data: bytes, space_byte: int = 0x00) -> dict:
    """Count spaces in different positions within the data."""
    result = {
        'leading': 0,
        'trailing': 0,
        'internal': 0,
        'total': 0,
        'sequences': []  # List of (position, count) for space sequences
    }

    # Find terminator position
    term_pos = len(data)
    for i, b in enumerate(data):
        if b == 0xFF:
            term_pos = i
            break

    # Only analyze up to terminator
    data = data[:term_pos]
    if not data:
        return result

    # Count leading spaces
    for b in data:
        if b == space_byte:
            result['leading'] += 1
        else:
            break

    # Count trailing spaces
    for b in reversed(data):
        if b == space_byte:
            result['trailing'] += 1
        else:
            break

    # Count all spaces and find sequences
    in_sequence = False
    seq_start = 0
    seq_count = 0

    for i, b in enumerate(data):
        if b == space_byte:
            result['total'] += 1
            if not in_sequence:
                in_sequence = True
                seq_start = i
                seq_count = 1
            else:
                seq_count += 1
        else:
            if in_sequence:
                result['sequences'].append((seq_start, seq_count))
                in_sequence = False
                seq_count = 0

    if in_sequence:
        result['sequences'].append((seq_start, seq_count))

    # Internal = total - leading - trailing
    result['internal'] = result['total'] - result['leading'] - result['trailing']

    return result


def decode_en_text(data: bytes) -> str:
    """Decode EN FF7 text."""
    result = []
    for b in data:
        if b == 0xFF:
            break
        if b == 0x00:
            result.append(' ')
        elif 0x21 <= b <= 0x5A:
            result.append(chr(b + 0x20))
        elif 0x01 <= b <= 0x20:
            result.append(chr(b + 0x20))
        else:
            result.append(f'[{b:02X}]')
    return ''.join(result)


def main():
    en_exe_path = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe"
    ja_exe_path = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_ja.exe"

    print("=" * 80)
    print("FF7 SPACING ANALYSIS")
    print("=" * 80)
    print()
    print("Analyzing entries where EN has significant spacing that JA might lack...")
    print()

    entries_with_spacing = []

    with open(en_exe_path, 'rb') as en_f, open(ja_exe_path, 'rb') as ja_f:
        for i, (en_offset, length, stype) in enumerate(zip(EN_OFFSETS, STRING_LENGTHS, STRING_TYPES)):
            # Skip problematic regions
            if i in SKIP_REGIONS or i in RGB_SKIP_REGIONS or i in KEYBOARD_REGION:
                continue

            if length <= 1:
                continue

            ja_offset = en_offset + JA_OFFSET_DELTA

            en_f.seek(en_offset)
            en_data = en_f.read(length)

            ja_f.seek(ja_offset)
            ja_data = ja_f.read(length)

            # Count spaces in EN (0x00 = space in FF7 encoding)
            en_spaces = count_spaces(en_data, 0x00)

            # Count spaces in JA (0x3F = ideographic space on jafont_1)
            ja_spaces = count_spaces(ja_data, 0x3F)

            # Flag entries where EN has internal spacing (multiple words)
            if en_spaces['internal'] >= 2 or len(en_spaces['sequences']) >= 2:
                en_text = decode_en_text(en_data)

                entries_with_spacing.append({
                    'index': i,
                    'type': StringType(stype).name,
                    'en_text': en_text,
                    'en_spaces': en_spaces,
                    'ja_spaces': ja_spaces,
                    'en_data': en_data,
                    'ja_data': ja_data,
                })

    # Sort by total EN spaces (descending)
    entries_with_spacing.sort(key=lambda x: x['en_spaces']['total'], reverse=True)

    print(f"Found {len(entries_with_spacing)} entries with significant internal spacing")
    print()
    print("=" * 80)
    print("ENTRIES WITH INTERNAL SPACING (potential alignment issues)")
    print("=" * 80)
    print()

    for entry in entries_with_spacing[:50]:  # Show top 50
        print(f"[{entry['index']:3d}] {entry['type']}")
        print(f"  EN: {repr(entry['en_text'][:50])}")
        print(f"  EN spaces: total={entry['en_spaces']['total']}, "
              f"internal={entry['en_spaces']['internal']}, "
              f"trailing={entry['en_spaces']['trailing']}")
        print(f"  EN sequences: {entry['en_spaces']['sequences']}")
        print(f"  JA spaces (0x3F): total={entry['ja_spaces']['total']}")
        print()

    # Summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    # Group by space patterns
    multi_word = [e for e in entries_with_spacing if len(e['en_spaces']['sequences']) >= 2]
    trailing_only = [e for e in entries_with_spacing if e['en_spaces']['trailing'] >= 2 and e['en_spaces']['internal'] == 0]

    print(f"Multi-word entries (multiple space sequences): {len(multi_word)}")
    print(f"Trailing-space-only entries: {len(trailing_only)}")
    print()

    # Show ratio analysis
    print("=" * 80)
    print("SPACE RATIO ANALYSIS (EN spaces vs JA spaces)")
    print("=" * 80)
    print()

    for entry in entries_with_spacing[:20]:
        en_total = entry['en_spaces']['total']
        ja_total = entry['ja_spaces']['total']
        if en_total > 0:
            ratio = ja_total / en_total if en_total > 0 else 0
            suggested_ja = round(en_total * 0.67)  # ~2/3 ratio based on observation
            print(f"[{entry['index']:3d}] EN:{en_total:2d} JA:{ja_total:2d} "
                  f"ratio:{ratio:.2f} suggested_ja:{suggested_ja} "
                  f"| {entry['en_text'][:30]}")


if __name__ == "__main__":
    main()
