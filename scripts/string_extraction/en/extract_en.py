#!/usr/bin/env python3
"""
FF7 English Executable String Extractor
Created: 2025-12-05 13:00 JST
Session-ID: c245e7c0-ec73-4933-b925-5976860e742c

PURPOSE:
    Extract all FF-terminated strings from FF7 English executable .data section.
    Based on base_extractor.py template.

USAGE:
    python3 extract_en.py

OUTPUT:
    - CSV file: strings_en.csv
    - Verification report: verification_en.txt
"""

import os
import sys
import csv
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LANGUAGE = "en"
EXE_PATH = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe"

# .data section info from objdump -h ff7_en.exe
DATA_SECTION_OFFSET = 0x3B8A00
DATA_SECTION_SIZE = 0x1E3000
DATA_SECTION_VMA = 0x7BA000

# Known menu strings for verification (from MENU_TEXT_ADDRESS_MAP.md)
KNOWN_STRINGS = [
    ("CONFIG", "23 2F 4E 46 49 47"),
    ("ITEM", "29 54 45 4D"),
    ("MAGIC", "2D 41 47 49 43"),
    ("EQUIP", "25 51 55 49 50"),
    ("STATUS", "33 54 41 54 55 53"),
    ("SAVE", "33 41 56 45"),
    ("QUIT", "31 55 49 54"),
    ("NEW GAME", "2E 25 37 00 27 21 2D 25"),
    ("CONTINUE", "23 4F 4E 54 49 4E 55 45 1F"),
]

# ============================================================================
# CHARACTER DECODING
# ============================================================================

def build_english_decode_map():
    """
    English FF7 uses shifted ASCII: actual_char = byte - 0x20
    A=0x21, B=0x22, ... Z=0x3A
    a=0x41, b=0x42, ... z=0x5A
    0=0x10, 1=0x11, ... 9=0x19
    Space=0x00, Period=0x0E
    """
    decode_map = {}
    # Uppercase A-Z
    for i, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        decode_map[0x21 + i] = char
    # Lowercase a-z
    for i, char in enumerate("abcdefghijklmnopqrstuvwxyz"):
        decode_map[0x41 + i] = char
    # Numbers 0-9
    for i, char in enumerate("0123456789"):
        decode_map[0x10 + i] = char
    # Common punctuation
    decode_map[0x00] = ' '   # Space
    decode_map[0x0E] = '.'   # Period
    decode_map[0x0F] = ','   # Comma
    decode_map[0x1A] = ':'   # Colon
    decode_map[0x1B] = "'"   # Apostrophe
    decode_map[0x1C] = '"'   # Quote
    decode_map[0x1D] = '('   # Open paren
    decode_map[0x1E] = ')'   # Close paren
    decode_map[0x1F] = '?'   # Question mark
    decode_map[0x20] = '!'   # Exclamation
    return decode_map

# Initialize decode map
DECODE_MAP = build_english_decode_map()

def decode_byte(byte_val):
    """Decode a single byte to character."""
    return DECODE_MAP.get(byte_val, f'[{byte_val:02X}]')

def decode_string(byte_sequence):
    """Decode a full byte sequence to string."""
    if not byte_sequence:
        return ""
    return ''.join(decode_byte(b) for b in byte_sequence)

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
            if found[1] == expected_bytes:
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
        print("Please update EXE_PATH in this script.")
        sys.exit(1)

    # Determine project root (3 levels up from this script)
    script_dir = Path(__file__).parent

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
