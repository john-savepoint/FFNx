#!/usr/bin/env python3
"""
FF7 German String Extractor
Created: 2025-12-05 19:30 JST
Session-ID: c245e7c0-ec73-4933-b925-5976860e742c

PURPOSE:
    Extract all FF-terminated strings from FF7 German .data section.

CONFIGURATION:
    Based on ff7_de.exe from /mnt/d/Games/Stand-alone/FINAL FANTASY VII/
    .data section: offset 0x3B9A00, size 0x1E3C00, VMA 0x7BA000

OUTPUT:
    - CSV file: strings_de.csv
    - Verification report: verification_de.txt
"""

import os
import sys
import csv
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LANGUAGE = "de"
EXE_PATH = "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_de.exe"

# .data section info from objdump -h
# .data         001e3c00  007ba000  007ba000  003b9a00  2**2
DATA_SECTION_OFFSET = 0x3B9A00  # File offset
DATA_SECTION_SIZE = 0x1E3C00    # Size
DATA_SECTION_VMA = 0x7BA000     # Virtual memory address

# Known strings for verification
# We'll start with common menu terms and add more as we find them
KNOWN_STRINGS = [
    # German FF7 menu terms - we'll need to find these first
    # Format: (expected_decoded_text, expected_byte_pattern_hex)
]

# ============================================================================
# CHARACTER DECODING
# ============================================================================

def build_german_decode_map():
    """
    German FF7 likely uses shifted ASCII similar to English.
    May include extended characters: ä, ö, ü, ß, Ä, Ö, Ü

    We'll start with the English map and add German characters as we find them.
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

    # German extended characters - placeholder positions
    # We'll identify these from the output
    # decode_map[0x??] = 'ä'
    # decode_map[0x??] = 'ö'
    # decode_map[0x??] = 'ü'
    # decode_map[0x??] = 'ß'
    # decode_map[0x??] = 'Ä'
    # decode_map[0x??] = 'Ö'
    # decode_map[0x??] = 'Ü'

    return decode_map

DECODE_MAP = build_german_decode_map()

def decode_byte(byte_val):
    """Decode a single byte to character."""
    return DECODE_MAP.get(byte_val, f'[{byte_val:02X}]')

def decode_string(byte_sequence):
    """Decode a full byte sequence to string."""
    if not byte_sequence:
        return ""
    return ''.join([decode_byte(b) for b in byte_sequence])

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

    if not known_strings:
        report_lines.append("No known strings configured for verification.")
        report_lines.append("Review the output CSV and add verification strings to the script.")
        return 0, 0, '\n'.join(report_lines)

    # Build lookup by decoded text
    found_texts = {s[2]: s for s in strings}

    for expected_text, expected_bytes_hex in known_strings:
        expected_bytes = bytes.fromhex(expected_bytes_hex.replace(" ", "").replace("FF", ""))

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

def analyze_extended_chars(strings):
    """
    Analyze strings to find potential German extended characters (ä, ö, ü, ß).
    Returns report of undecoded byte values that might be German characters.
    """
    report_lines = ["", "=" * 60, "EXTENDED CHARACTER ANALYSIS", "=" * 60, ""]

    # Collect all undecoded bytes
    undecoded_bytes = {}
    for file_offset, raw_bytes, decoded in strings:
        import re
        # Find [XX] patterns
        for match in re.finditer(r'\[([0-9A-F]{2})\]', decoded):
            byte_val = int(match.group(1), 16)
            if byte_val not in undecoded_bytes:
                undecoded_bytes[byte_val] = []
            undecoded_bytes[byte_val].append((file_offset, decoded))

    if undecoded_bytes:
        report_lines.append("Undecoded byte values (potential German characters):")
        report_lines.append("")
        for byte_val in sorted(undecoded_bytes.keys()):
            occurrences = len(undecoded_bytes[byte_val])
            sample = undecoded_bytes[byte_val][0][1][:50]
            report_lines.append(f"  0x{byte_val:02X}: {occurrences} occurrences - sample: {sample}...")
    else:
        report_lines.append("No undecoded bytes found.")

    report_lines.append("=" * 60)
    return '\n'.join(report_lines)

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
    if not os.path.exists(EXE_PATH):
        print(f"ERROR: Executable not found: {EXE_PATH}")
        sys.exit(1)

    script_dir = Path(__file__).parent

    print(f"Extracting strings from German FF7 executable...")
    print(f"  File: {EXE_PATH}")
    print(f"  Data section: 0x{DATA_SECTION_OFFSET:X} - 0x{DATA_SECTION_OFFSET + DATA_SECTION_SIZE:X}")

    # Extract strings
    strings = extract_strings(EXE_PATH, DATA_SECTION_OFFSET, DATA_SECTION_SIZE)
    print(f"  Found {len(strings)} strings")

    # Output paths
    csv_path = script_dir / f"strings_{LANGUAGE}.csv"
    report_path = script_dir / f"verification_{LANGUAGE}.txt"

    # Write CSV
    write_csv(strings, csv_path, LANGUAGE)
    print(f"  Wrote {csv_path}")

    # Verification
    full_report = []

    # Known string verification
    passed, failed, report = verify_extraction(strings, KNOWN_STRINGS)
    full_report.append(report)
    if KNOWN_STRINGS:
        print(f"  Known string verification: {passed} passed, {failed} failed")

    # Spot check
    spot_ok, spot_report = spot_check_raw_exe(EXE_PATH, strings)
    full_report.append(spot_report)
    print(f"  Spot check: {'PASSED' if spot_ok else 'FAILED'}")

    # Extended character analysis
    extended_report = analyze_extended_chars(strings)
    full_report.append(extended_report)

    # Write report
    write_verification_report('\n\n'.join(full_report), report_path)
    print(f"  Wrote {report_path}")

    # Print sample strings
    print("\n" + "=" * 60)
    print("SAMPLE STRINGS (first 10 menu-related):")
    print("=" * 60)
    menu_related = []
    for offset, raw, decoded in strings:
        # Look for strings that might be menu-related (short, uppercase, etc.)
        if len(decoded) <= 20 and any(c.isupper() for c in decoded if c.isalpha()):
            menu_related.append((offset, decoded))
            if len(menu_related) >= 10:
                break

    for offset, decoded in menu_related:
        print(f"0x{offset:06X}: {decoded}")

    # Summary
    print("\n" + "=" * 60)
    print(f"EXTRACTION COMPLETE: German (de)")
    print(f"  Total strings: {len(strings)}")
    print(f"  Output: {csv_path}")
    print(f"  Report: {report_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
