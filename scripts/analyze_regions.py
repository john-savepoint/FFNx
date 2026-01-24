#!/usr/bin/env python3
"""
FF7 EXE String Region Analyzer

Analyzes all string regions in FF7 executables to understand:
- What types exist in each region
- What the EN and JA content looks like
- Which regions should be skipped and why

Created: 2025-12-08 11:59 JST (Monday)
Session-ID: 0681f78b-0382-45ee-898b-5a32b7ce32d5
Context: Systematic analysis of skip regions for Japanese text patching
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# =============================================================================
# CONSTANTS - From touphScript ff7exe.cpp
# =============================================================================

JA_OFFSET_DELTA = 0xC00

TYPE_NAMES = {
    0: "DEF",        # Standard FF7 encoding with FF terminator
    1: "NOFF_TERM",  # No FF terminator in file
    2: "RGB",        # RGB encoded (ASCII + 0x73)
    3: "UNICODE",    # Windows Unicode strings
    4: "FFPADDED",   # FF7 encoding padded with FF bytes
    5: "ZEROTERM",   # Zero-terminated string
}

# Load arrays from generate_exe_hext.py
def load_arrays():
    """Load EN_OFFSETS, STRING_LENGTHS, STRING_TYPES from generator script."""
    script_path = Path(__file__).parent / "generate_exe_hext.py"
    with open(script_path, 'r') as f:
        content = f.read()

    # Extract arrays by executing the relevant parts
    local_vars = {}

    # Find and execute EN_OFFSETS
    start = content.find("EN_OFFSETS = [")
    end = content.find("]", start) + 1
    exec(content[start:end], {}, local_vars)

    # Find and execute STRING_LENGTHS
    start = content.find("STRING_LENGTHS = [")
    end = content.find("]", start) + 1
    exec(content[start:end], {}, local_vars)

    # Find and execute STRING_TYPES
    start = content.find("STRING_TYPES = [")
    end = content.find("]", start) + 1
    exec(content[start:end], {}, local_vars)

    return local_vars['EN_OFFSETS'], local_vars['STRING_LENGTHS'], local_vars['STRING_TYPES']


def load_charmap(csv_path: Path) -> Dict:
    """Load character map from CSV."""
    charmap = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
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
    return charmap


def decode_ff7_string(data: bytes, charmap: Dict) -> str:
    """Decode FF7-encoded string."""
    result = []
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0xFF:
            break
        if b == 0x00:
            result.append(' ')
            i += 1
        elif b in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) and i + 1 < len(data):
            key = (b, data[i + 1])
            result.append(charmap.get(key, f'[{b:02X}{data[i+1]:02X}]'))
            i += 2
        else:
            result.append(charmap.get(b, f'[{b:02X}]'))
            i += 1
    return ''.join(result)


def decode_ascii(data: bytes) -> str:
    """Decode ASCII/FF7-English string."""
    result = []
    for b in data:
        if b == 0xFF or b == 0x00:
            break
        # FF7 encoding: printable chars are ASCII - 0x20
        if 0x01 <= b <= 0x5F:
            result.append(chr(b + 0x20))
        elif 0x20 <= b <= 0x7E:
            result.append(chr(b))
        else:
            result.append(f'[{b:02X}]')
    return ''.join(result)


def decode_rgb(data: bytes) -> str:
    """Decode RGB-encoded string (ASCII + 0x73)."""
    result = []
    for b in data:
        if b == 0xFF or b == 0x00:
            break
        if 0x93 <= b <= 0xED:
            result.append(chr(b - 0x73))
        elif 0x20 <= b <= 0x7E:
            result.append(chr(b))
        else:
            result.append(f'[{b:02X}]')
    return ''.join(result)


def find_contiguous_ranges(indices: List[int]) -> List[Tuple[int, int]]:
    """Find contiguous ranges in a list of indices."""
    if not indices:
        return []

    ranges = []
    start = indices[0]
    prev = start

    for i in indices[1:]:
        if i != prev + 1:
            ranges.append((start, prev))
            start = i
        prev = i
    ranges.append((start, prev))

    return ranges


def analyze_regions(en_exe_path: str, ja_exe_path: str, charmap_path: str, verbose: bool = False):
    """Analyze all regions and generate comprehensive report."""

    EN_OFFSETS, STRING_LENGTHS, STRING_TYPES = load_arrays()
    charmap = load_charmap(Path(charmap_path))

    total_entries = len(EN_OFFSETS)

    print("=" * 80)
    print("FF7 EXE STRING REGION ANALYSIS")
    print("=" * 80)
    print(f"\nTotal entries: {total_entries}")
    print(f"EN exe: {en_exe_path}")
    print(f"JA exe: {ja_exe_path}")
    print()

    # ==========================================================================
    # PART 1: Type Distribution Overview
    # ==========================================================================
    print("=" * 80)
    print("PART 1: STRING TYPE DISTRIBUTION")
    print("=" * 80)

    type_counts = defaultdict(int)
    type_indices = defaultdict(list)

    for i, stype in enumerate(STRING_TYPES):
        type_counts[stype] += 1
        type_indices[stype].append(i)

    print(f"\n{'Type':<12} {'Count':>6} {'Percentage':>10}  Index Ranges")
    print("-" * 80)

    for type_num in sorted(type_counts.keys()):
        name = TYPE_NAMES[type_num]
        count = type_counts[type_num]
        pct = count / total_entries * 100
        ranges = find_contiguous_ranges(type_indices[type_num])
        range_str = ", ".join(f"{s}-{e}" if s != e else str(s) for s, e in ranges[:5])
        if len(ranges) > 5:
            range_str += f" ... (+{len(ranges)-5} more)"
        print(f"{name:<12} {count:>6} {pct:>9.1f}%  {range_str}")

    # ==========================================================================
    # PART 2: Detailed Region Breakdown
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PART 2: DETAILED REGION BREAKDOWN")
    print("=" * 80)

    # Define logical regions for analysis
    REGIONS = [
        ("Main Menu & UI", 0, 76),
        ("Keyboard Labels", 77, 211),
        ("Config & Status", 212, 460),
        ("Name Entry (UNICODE)", 461, 528),
        ("Battle & Items", 529, 648),
        ("Save Slots (RGB marked)", 649, 657),
        ("Post-Save (RGB)", 658, 686),
        ("Race Ordinals (FFPADDED)", 687, 711),
        ("Chocobo Names (ZEROTERM)", 712, 757),
    ]

    with open(en_exe_path, 'rb') as en_f, open(ja_exe_path, 'rb') as ja_f:
        for region_name, start_idx, end_idx in REGIONS:
            print(f"\n--- {region_name} (indices {start_idx}-{end_idx}) ---")

            # Count types in this region
            region_types = defaultdict(int)
            for i in range(start_idx, min(end_idx + 1, total_entries)):
                region_types[STRING_TYPES[i]] += 1

            print(f"Type breakdown:")
            for type_num, count in sorted(region_types.items()):
                print(f"  {TYPE_NAMES[type_num]}: {count}")

            # Show sample entries
            print(f"\nSample entries:")
            sample_indices = [start_idx, (start_idx + end_idx) // 2, end_idx]
            sample_indices = [i for i in sample_indices if i < total_entries]

            for idx in sample_indices:
                en_offset = EN_OFFSETS[idx]
                ja_offset = en_offset + JA_OFFSET_DELTA
                length = STRING_LENGTHS[idx]
                stype = STRING_TYPES[idx]

                en_f.seek(en_offset)
                en_data = en_f.read(length)

                ja_f.seek(ja_offset)
                ja_data = ja_f.read(length)

                # Decode based on type
                if stype == 2:  # RGB
                    en_text = decode_rgb(en_data)
                    ja_text_as_rgb = decode_rgb(ja_data)
                    ja_text_as_ff7 = decode_ff7_string(ja_data, charmap)
                    print(f"  [{idx}] {TYPE_NAMES[stype]:10} len={length:3}")
                    print(f"       EN bytes: {en_data[:16].hex()}")
                    print(f"       EN as RGB: {repr(en_text[:30])}")
                    print(f"       JA bytes: {ja_data[:16].hex()}")
                    print(f"       JA as RGB: {repr(ja_text_as_rgb[:30])}")
                    print(f"       JA as FF7: {repr(ja_text_as_ff7[:30])}")
                elif stype == 3:  # UNICODE
                    try:
                        en_text = en_data.decode('utf-16-le').rstrip('\x00')
                        ja_text = ja_data.decode('utf-16-le').rstrip('\x00')
                    except:
                        en_text = "[decode error]"
                        ja_text = "[decode error]"
                    print(f"  [{idx}] {TYPE_NAMES[stype]:10} len={length:3}")
                    print(f"       EN: {repr(en_text[:30])}")
                    print(f"       JA: {repr(ja_text[:30])}")
                else:  # DEF, NOFF_TERM, FFPADDED, ZEROTERM
                    en_text = decode_ascii(en_data)
                    ja_text = decode_ff7_string(ja_data, charmap)
                    print(f"  [{idx}] {TYPE_NAMES[stype]:10} len={length:3}")
                    print(f"       EN bytes: {en_data[:16].hex()}")
                    print(f"       EN: {repr(en_text[:30])}")
                    print(f"       JA bytes: {ja_data[:16].hex()}")
                    print(f"       JA: {repr(ja_text[:30])}")

    # ==========================================================================
    # PART 3: Recommended Skip Regions
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PART 3: RECOMMENDED SKIP CONFIGURATION")
    print("=" * 80)

    print("""
Based on analysis, here are the skip region recommendations:

SKIP_REGIONS (do not patch these):
  - range(77, 212)    # Keyboard labels - RGB type, need FFNx fix not HEXT
  - range(461, 529)   # Name entry - UNICODE type, different encoding
  - range(658, 687)   # Post-save - RGB type, produces garbage
  - range(687, 712)   # Race ordinals - FFPADDED type, keep English
  - range(712, 758)   # Chocobo names - ZEROTERM type, keep English

RGB_AS_DEF_REGIONS (copy JA bytes instead of RGB encoding):
  - range(649, 658)   # Save slots - marked RGB but JA has FF7-encoded Japanese

Note: The keyboard region (77-211) is marked as RGB type. These are the key
names like "ESCAPE", "INSERT", "PAGE UP" etc. The EN exe has these in
FF7 encoding (ASCII-0x20), and applying RGB encoding (+0x93) SHOULD map
them to fullwidth English on jafont_1... but the rendering bypasses the
hooked text functions, so HEXT patches don't help.
""")

    # ==========================================================================
    # PART 4: Full Index Listing (optional verbose mode)
    # ==========================================================================
    if verbose:
        print("\n" + "=" * 80)
        print("PART 4: FULL INDEX LISTING")
        print("=" * 80)

        with open(en_exe_path, 'rb') as en_f, open(ja_exe_path, 'rb') as ja_f:
            for idx in range(total_entries):
                en_offset = EN_OFFSETS[idx]
                ja_offset = en_offset + JA_OFFSET_DELTA
                length = STRING_LENGTHS[idx]
                stype = STRING_TYPES[idx]

                en_f.seek(en_offset)
                en_data = en_f.read(min(length, 20))

                ja_f.seek(ja_offset)
                ja_data = ja_f.read(min(length, 20))

                en_text = decode_ascii(en_data)[:20]
                ja_text = decode_ff7_string(ja_data, charmap)[:20]

                print(f"[{idx:3}] {TYPE_NAMES[stype]:10} 0x{en_offset:06X} len={length:3} EN:{repr(en_text):22} JA:{repr(ja_text)}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze FF7 EXE string regions")
    parser.add_argument("en_exe", help="Path to English FF7 executable")
    parser.add_argument("ja_exe", help="Path to Japanese FF7 executable")
    parser.add_argument("--charmap", default=None, help="Path to character map CSV")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show full index listing")

    args = parser.parse_args()

    # Default charmap path
    if args.charmap is None:
        script_dir = Path(__file__).parent.parent
        args.charmap = script_dir / "docs" / "character_maps" / "ff7_complete_mapping_compact.csv"

    analyze_regions(args.en_exe, args.ja_exe, args.charmap, args.verbose)


if __name__ == "__main__":
    main()
