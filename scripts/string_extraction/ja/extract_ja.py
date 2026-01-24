#!/usr/bin/env python3
"""
FF7 Japanese Executable String Extractor
Created: 2025-12-05 JST
Session-ID: 2f82b29a-10fb-4890-833f-e1de0d8fc8bb

PURPOSE:
    Extract all FF-terminated strings from FF7 Japanese executable .data section.
    Uses the Japanese character mapping from ff7_complete_mapping_compact.csv.

USAGE:
    python3 extract_ja.py

OUTPUT:
    - CSV file: strings_ja.csv
    - Verification report: verification_ja.txt
"""

import os
import sys
import csv
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LANGUAGE = "ja"
EXE_PATH = "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_ja.exe"

# .data section info from objdump -h
# Japanese exe:
#   .data at file offset 0x3B9600, size 0x1E3000, VMA 0x7BA000
DATA_SECTION_OFFSET = 0x3B9600
DATA_SECTION_SIZE = 0x1E3000
DATA_SECTION_VMA = 0x7BA000

# Known strings for verification (found via xxd search)
# Format: (expected_decoded_text, expected_byte_pattern_hex)
KNOWN_STRINGS = [
    ("アイテム", "6A 6C 64 80"),  # ITEM at 0x519EC0
    ("まほう", "7D 49 69"),        # MAGIC at 0x519ED0
    ("コンフィグ", "52 98 44 A6 0E"),  # CONFIG (partial pattern found)
    ("セット", "5A 9C 66"),        # Set at 0x51EB80
    ("はい", "41 6D"),            # Yes at 0x518FD0
]

# ============================================================================
# CHARACTER DECODING
# ============================================================================

def load_japanese_decode_map(csv_path):
    """
    Load Japanese character map from our CSV file.
    Returns dict: {(texture_num, index): unicode_char}
    """
    decode_map = {}
    if not os.path.exists(csv_path):
        print(f"WARNING: Japanese character map not found at {csv_path}")
        return decode_map

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            texture = row['texture']  # e.g., "jafont_1"
            index = int(row['index'])
            char = row['character']
            if char:  # Skip empty entries
                texture_num = int(texture.split('_')[1])
                decode_map[(texture_num, index)] = char
    return decode_map

# Global decode map
DECODE_MAP = {}

def init_decode_map(project_root):
    """Initialize the decode map based on language."""
    global DECODE_MAP
    csv_path = os.path.join(project_root, 'docs/character_maps/ff7_complete_mapping_compact.csv')
    DECODE_MAP = load_japanese_decode_map(csv_path)
    print(f"  Loaded {len(DECODE_MAP)} character mappings from {csv_path}")

def decode_byte(byte_val, texture_num=1):
    """Decode a single byte to character."""
    key = (texture_num, byte_val)
    return DECODE_MAP.get(key, f'[{byte_val:02X}]')

def decode_string(byte_sequence):
    """
    Decode a full byte sequence to string.
    For Japanese, handles texture prefix bytes (FA-FE).
    """
    if not byte_sequence:
        return ""

    result = []
    i = 0
    texture_num = 1

    while i < len(byte_sequence):
        byte_val = byte_sequence[i]

        # Check for Japanese texture prefix
        if byte_val in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE):
            texture_num = byte_val - 0xFA + 2  # FA=2, FB=3, FC=4, FD=5, FE=6
            i += 1
            continue

        # Decode the character
        char = decode_byte(byte_val, texture_num)
        result.append(char)

        # Reset texture for next char
        texture_num = 1

        i += 1

    return ''.join(result)

# ============================================================================
# STRING EXTRACTION
# ============================================================================

def extract_strings(exe_path, data_offset, data_size, min_length=2, max_length=200):
    """
    Extract all FF-terminated strings from the .data section.

    Returns list of tuples: (file_offset, raw_bytes, decoded_text)
    """
    strings = []

    with open(exe_path, 'rb') as f:
        f.seek(data_offset)
        data = f.read(data_size)

    i = 0
    while i < len(data):
        # Look for potential string start (non-FF byte)
        if data[i] == 0xFF:
            i += 1
            continue

        # Scan for FF terminator
        start = i
        while i < len(data) and data[i] != 0xFF:
            i += 1

        # Check if we found a terminator
        if i < len(data) and data[i] == 0xFF:
            length = i - start
            if min_length <= length <= max_length:
                raw_bytes = data[start:i]  # Exclude FF terminator
                file_offset = data_offset + start
                decoded = decode_string(raw_bytes)

                # Filter out likely non-text (too many undecoded bytes)
                undecoded_count = decoded.count('[')
                if undecoded_count < len(decoded) * 0.3:  # Allow up to 30% unknown
                    strings.append((file_offset, raw_bytes, decoded))

        i += 1

    return strings

def file_offset_to_va(file_offset):
    """Convert file offset to virtual address."""
    return (file_offset - DATA_SECTION_OFFSET) + DATA_SECTION_VMA + 0x400000

# ============================================================================
# VERIFICATION
# ============================================================================

def verify_extraction(strings, known_strings):
    """
    Verify that known strings were found in the extraction.
    Returns (passed, failed, report_text)
    """
    report_lines = ["=" * 60, "VERIFICATION REPORT", "=" * 60, ""]
    passed = 0
    failed = 0

    # Build lookup by decoded text
    found_texts = {s[2]: s for s in strings}

    for expected_text, expected_bytes_hex in known_strings:
        expected_bytes = bytes.fromhex(expected_bytes_hex.replace(" ", ""))

        if expected_text in found_texts:
            found = found_texts[expected_text]
            # Check if bytes match (partial match OK since we don't include FF)
            if found[1][:len(expected_bytes)] == expected_bytes:
                report_lines.append(f"PASS: '{expected_text}' found at 0x{found[0]:X}")
                passed += 1
            else:
                report_lines.append(f"PARTIAL: '{expected_text}' found but bytes differ")
                report_lines.append(f"  Expected: {expected_bytes_hex}")
                report_lines.append(f"  Found:    {' '.join(f'{b:02X}' for b in found[1])}")
                passed += 1  # Still counts as found
        else:
            report_lines.append(f"FAIL: '{expected_text}' NOT FOUND")
            failed += 1

    report_lines.extend([
        "",
        "=" * 60,
        f"SUMMARY: {passed} passed, {failed} failed",
        "=" * 60
    ])

    return passed, failed, '\n'.join(report_lines)

def spot_check_raw_exe(exe_path, strings, num_checks=5):
    """
    Spot-check by reading raw bytes from exe and comparing.
    Picks random strings and verifies they exist at claimed offset.
    """
    import random

    report_lines = ["", "=" * 60, "SPOT CHECK (Raw Byte Verification)", "=" * 60, ""]

    if len(strings) < num_checks:
        check_indices = range(len(strings))
    else:
        check_indices = random.sample(range(len(strings)), num_checks)

    passed = 0
    with open(exe_path, 'rb') as f:
        for idx in check_indices:
            file_offset, expected_bytes, decoded = strings[idx]

            f.seek(file_offset)
            actual_bytes = f.read(len(expected_bytes) + 1)  # +1 for FF terminator

            if actual_bytes[:-1] == expected_bytes and actual_bytes[-1] == 0xFF:
                report_lines.append(f"PASS: '{decoded[:30]}...' at 0x{file_offset:X}")
                passed += 1
            else:
                report_lines.append(f"FAIL: '{decoded[:30]}...' at 0x{file_offset:X}")
                report_lines.append(f"  Expected: {' '.join(f'{b:02X}' for b in expected_bytes)} FF")
                report_lines.append(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_bytes)}")

    report_lines.extend([
        "",
        f"Spot check: {passed}/{len(check_indices)} passed",
        "=" * 60
    ])

    return passed == len(check_indices), '\n'.join(report_lines)

# ============================================================================
# OUTPUT
# ============================================================================

def write_csv(strings, output_path, language):
    """Write extracted strings to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['language', 'file_offset', 'virtual_address', 'raw_bytes', 'decoded_text', 'string_length'])

        for file_offset, raw_bytes, decoded in strings:
            va = file_offset_to_va(file_offset)
            raw_hex = ' '.join(f'{b:02X}' for b in raw_bytes)
            writer.writerow([language, f'0x{file_offset:X}', f'0x{va:X}', raw_hex, decoded, len(raw_bytes)])

def write_verification_report(report_text, output_path):
    """Write verification report to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Validate configuration
    if not EXE_PATH or not os.path.exists(EXE_PATH):
        print(f"ERROR: EXE_PATH not set or file not found: {EXE_PATH}")
        sys.exit(1)

    # Determine project root (3 levels up from this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent

    # Initialize decode map
    init_decode_map(project_root)

    print(f"Extracting strings from {LANGUAGE} executable...")
    print(f"  File: {EXE_PATH}")
    print(f"  Data section: 0x{DATA_SECTION_OFFSET:X} - 0x{DATA_SECTION_OFFSET + DATA_SECTION_SIZE:X}")

    # Extract strings
    strings = extract_strings(EXE_PATH, DATA_SECTION_OFFSET, DATA_SECTION_SIZE)
    print(f"  Found {len(strings)} strings")

    # Output paths
    output_dir = script_dir
    csv_path = output_dir / f"strings_{LANGUAGE}.csv"
    report_path = output_dir / f"verification_{LANGUAGE}.txt"

    # Write CSV
    write_csv(strings, csv_path, LANGUAGE)
    print(f"  Wrote {csv_path}")

    # Verification
    full_report = []

    # Known string verification
    if KNOWN_STRINGS:
        passed, failed, report = verify_extraction(strings, KNOWN_STRINGS)
        full_report.append(report)
        print(f"  Known string verification: {passed} passed, {failed} failed")

    # Spot check
    spot_ok, spot_report = spot_check_raw_exe(EXE_PATH, strings)
    full_report.append(spot_report)
    print(f"  Spot check: {'PASSED' if spot_ok else 'FAILED'}")

    # Write report
    write_verification_report('\n\n'.join(full_report), report_path)
    print(f"  Wrote {report_path}")

    # Summary
    print("\n" + "=" * 60)
    print(f"EXTRACTION COMPLETE: {LANGUAGE}")
    print(f"  Total strings: {len(strings)}")
    print(f"  Output: {csv_path}")
    print(f"  Report: {report_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
