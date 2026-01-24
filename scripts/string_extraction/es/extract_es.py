#!/usr/bin/env python3
"""
FF7 Spanish Executable String Extractor
Created: 2025-12-05 13:15 JST
Session-ID: c245e7c0-ec73-4933-b925-5976860e742c

PURPOSE:
    Extract all FF-terminated strings from FF7 Spanish executable .data section.

LANGUAGE: Spanish (European)
EXECUTABLE: ff7_es.exe

ENCODING:
    Spanish version uses shifted ASCII like English (byte - 0x20)
    May include extended Latin characters: á, é, í, ó, ú, ñ, ü, ¿, ¡
"""

import os
import sys
import csv
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LANGUAGE = "es"
EXE_PATH = "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_es.exe"

# .data section info from objdump -h ff7_es.exe
# Idx Name          Size      VMA       LMA       File off  Algn
#   2 .data         001e4800  007bb000  007bb000  003ba000  2**2
DATA_SECTION_OFFSET = 0x3BA000
DATA_SECTION_SIZE = 0x1E4800
DATA_SECTION_VMA = 0x7BB000

# Known strings for verification (to be populated after first extraction)
KNOWN_STRINGS = [
    # Will populate after examining extracted strings
]

# ============================================================================
# CHARACTER DECODING
# ============================================================================

def build_spanish_decode_map():
    """
    Spanish FF7 uses shifted ASCII like English: actual_char = byte - 0x20
    Plus extended Latin characters for Spanish-specific letters.
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
    decode_map[0x3B] = '['   # Open bracket (guess)
    decode_map[0x3C] = ']'   # Close bracket (guess)
    decode_map[0x3D] = '-'   # Hyphen (guess)
    decode_map[0x3E] = '/'   # Slash (guess)

    # Spanish extended characters (will discover actual byte values during extraction)
    # These are placeholders - actual byte values may differ
    # á, é, í, ó, ú, ñ, ü, ¿, ¡

    return decode_map

DECODE_MAP = build_spanish_decode_map()

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
    Analyze strings to find Spanish extended characters.
    Report undecoded bytes that might be á, é, í, ó, ú, ñ, ü, ¿, ¡
    """
    report_lines = ["", "=" * 60, "EXTENDED CHARACTER ANALYSIS", "=" * 60, ""]

    # Find all undecoded bytes
    undecoded_bytes = {}
    for file_offset, raw_bytes, decoded in strings:
        for i, char in enumerate(decoded):
            if char.startswith('[') and char.endswith(']'):
                byte_val = raw_bytes[i]
                if byte_val not in undecoded_bytes:
                    undecoded_bytes[byte_val] = []
                # Store context (5 chars before and after)
                context_start = max(0, i - 5)
                context_end = min(len(decoded), i + 6)
                context = decoded[context_start:context_end]
                undecoded_bytes[byte_val].append(context)

    # Report frequent undecoded bytes with context
    if undecoded_bytes:
        report_lines.append("Undecoded bytes found (possible Spanish extended chars):")
        report_lines.append("")
        for byte_val in sorted(undecoded_bytes.keys()):
            contexts = undecoded_bytes[byte_val]
            report_lines.append(f"Byte 0x{byte_val:02X} ({len(contexts)} occurrences):")
            # Show up to 5 examples
            for context in contexts[:5]:
                report_lines.append(f"  Context: ...{context}...")
            if len(contexts) > 5:
                report_lines.append(f"  ... and {len(contexts) - 5} more")
            report_lines.append("")
    else:
        report_lines.append("No undecoded bytes found - all characters decoded successfully!")

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

def write_sample_strings(strings, output_path, num_samples=50):
    """Write sample strings for manual inspection."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("SAMPLE EXTRACTED STRINGS (First 50)\n")
        f.write("=" * 60 + "\n\n")

        for i, (file_offset, raw_bytes, decoded) in enumerate(strings[:num_samples]):
            f.write(f"String {i+1}:\n")
            f.write(f"  Offset: 0x{file_offset:X}\n")
            f.write(f"  Bytes:  {' '.join(f'{b:02X}' for b in raw_bytes)}\n")
            f.write(f"  Text:   {decoded}\n")
            f.write("\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Validate configuration
    if not os.path.exists(EXE_PATH):
        print(f"ERROR: EXE file not found: {EXE_PATH}")
        sys.exit(1)

    # Determine script directory
    script_dir = Path(__file__).parent

    print(f"Extracting strings from Spanish FF7 executable...")
    print(f"  File: {EXE_PATH}")
    print(f"  Data section: 0x{DATA_SECTION_OFFSET:X} - 0x{DATA_SECTION_OFFSET + DATA_SECTION_SIZE:X}")
    print(f"  Data section size: {DATA_SECTION_SIZE / 1024 / 1024:.2f} MB")

    # Extract strings
    strings = extract_strings(EXE_PATH, DATA_SECTION_OFFSET, DATA_SECTION_SIZE)
    print(f"  Found {len(strings)} strings")

    # Output paths
    csv_path = script_dir / f"strings_{LANGUAGE}.csv"
    report_path = script_dir / f"verification_{LANGUAGE}.txt"
    sample_path = script_dir / f"sample_strings_{LANGUAGE}.txt"

    # Write CSV
    write_csv(strings, csv_path, LANGUAGE)
    print(f"  Wrote {csv_path}")

    # Write sample strings
    write_sample_strings(strings, sample_path)
    print(f"  Wrote {sample_path}")

    # Verification
    full_report = []

    # Known string verification (if any)
    if KNOWN_STRINGS:
        passed, failed, report = verify_extraction(strings, KNOWN_STRINGS)
        full_report.append(report)
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

    # Summary
    print("\n" + "=" * 60)
    print(f"EXTRACTION COMPLETE: Spanish")
    print(f"  Total strings: {len(strings)}")
    print(f"  Output: {csv_path}")
    print(f"  Report: {report_path}")
    print(f"  Samples: {sample_path}")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review sample_strings_es.txt to identify Spanish menu strings")
    print("2. Add verified strings to KNOWN_STRINGS for future validation")
    print("3. Check verification_es.txt for extended character analysis")

if __name__ == "__main__":
    main()
