#!/usr/bin/env python3
"""
FF7 French Executable String Extractor
Created: 2025-12-05 13:45 JST
Session-ID: c245e7c0-ec73-4933-b925-5976860e742c

PURPOSE:
    Extract all FF-terminated strings from FF7 French executable .data section.
    French version uses similar encoding to English (shifted ASCII).

CONFIGURATION:
    - French executable: ff7_fr.exe
    - Data section: 0x3B9E00 (file), 0x7BA000 (VMA), size 0x1E4C00
    - Character encoding: Shifted ASCII + extended Latin characters

OUTPUT:
    - CSV file: strings_fr.csv
    - Verification report: verification_fr.txt
"""

import os
import sys
import csv
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LANGUAGE = "fr"
EXE_PATH = "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_fr.exe"

# .data section info from objdump
DATA_SECTION_OFFSET = 0x3B9E00
DATA_SECTION_SIZE = 0x1E4C00
DATA_SECTION_VMA = 0x7BA000

# Known French strings for verification
KNOWN_STRINGS = [
    ("Config", "23 4F 4E 46 49 47"),
    ("Magie", "2D 41 47 49 45"),
    ("Equiper", "25 51 55 49 50 45 52"),
    ("Quitter", "31 55 49 54 54 45 52"),
    ("Élément", "25 6C 6E 6D 65 6E 74"),  # é=0x6E
    ("Maître", "2D 61 74 74 72 65"),     # î=0x74
]

# ============================================================================
# CHARACTER DECODING
# ============================================================================

def build_french_decode_map():
    """
    French FF7 likely uses shifted ASCII similar to English.
    A=0x21, B=0x22, ... Z=0x3A
    a=0x41, b=0x42, ... z=0x5A
    0=0x10, 1=0x11, ... 9=0x19
    Space=0x00, Period=0x0E

    Extended Latin characters (é, è, ê, ë, à, â, ù, û, ô, î, ï, ç, œ, æ)
    will be identified during extraction and added to the map.
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

    # Common punctuation (from English mapping)
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
    decode_map[0x3B] = '-'   # Hyphen (common in French)
    decode_map[0x3C] = '/'   # Slash

    # Extended Latin characters for French (discovered during extraction)
    decode_map[0x07] = "'"   # Apostrophe (d'espace, m'a, l'air)
    decode_map[0x0D] = "-"   # Hyphen (Contre-attaque, Non-valide, Quasi-mort, Toi-même)
    decode_map[0x6D] = "ç"   # c cedilla (ça)
    decode_map[0x6E] = "é"   # e acute (précieuse, équipement, Phénix, désactivée, Stéréo, Élément, Dextérité)
    decode_map[0x6F] = "è"   # e grave (Après, Barrière, Protège)
    decode_map[0x70] = "ê"   # e circumflex (Fenêtre, Arrêter, Toi-même)
    decode_map[0x74] = "î"   # i circumflex (Maître)
    decode_map[0x79] = "ô"   # o circumflex (hôtelier)
    # Will discover more as needed: ë, à, â, ù, û, ï, œ, æ

    return decode_map

DECODE_MAP = build_french_decode_map()

def decode_byte(byte_val):
    """Decode a single byte to character."""
    return DECODE_MAP.get(byte_val, f'[{byte_val:02X}]')

def decode_string(byte_sequence):
    """Decode a full byte sequence to string."""
    if not byte_sequence:
        return ""

    result = []
    for byte_val in byte_sequence:
        result.append(decode_byte(byte_val))

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
# ANALYSIS
# ============================================================================

def analyze_extended_characters(strings):
    """
    Identify undecoded bytes that might be French extended characters.
    Returns dict of {byte_value: frequency}
    """
    undecoded_bytes = {}

    for file_offset, raw_bytes, decoded in strings:
        # Find [XX] patterns in decoded string
        i = 0
        byte_idx = 0
        while i < len(decoded):
            if decoded[i] == '[' and i + 3 < len(decoded) and decoded[i+3] == ']':
                byte_hex = decoded[i+1:i+3]
                try:
                    byte_val = int(byte_hex, 16)
                    undecoded_bytes[byte_val] = undecoded_bytes.get(byte_val, 0) + 1
                except ValueError:
                    pass
                i += 4
            else:
                i += 1

    return undecoded_bytes

# ============================================================================
# VERIFICATION
# ============================================================================

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

def write_extended_char_analysis(undecoded_bytes, output_path):
    """Write analysis of undecoded bytes (potential extended characters)."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("EXTENDED CHARACTER ANALYSIS\n")
        f.write("=" * 60 + "\n\n")
        f.write("Undecoded byte values and their frequencies:\n")
        f.write("These may represent French extended characters (é, è, ç, etc.)\n\n")

        # Sort by frequency (most common first)
        sorted_bytes = sorted(undecoded_bytes.items(), key=lambda x: x[1], reverse=True)

        f.write("Byte    Frequency\n")
        f.write("-" * 20 + "\n")
        for byte_val, freq in sorted_bytes:
            f.write(f"0x{byte_val:02X}    {freq}\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Validate configuration
    if not os.path.exists(EXE_PATH):
        print(f"ERROR: Executable not found: {EXE_PATH}")
        sys.exit(1)

    print(f"Extracting strings from French executable...")
    print(f"  File: {EXE_PATH}")
    print(f"  Data section: 0x{DATA_SECTION_OFFSET:X} - 0x{DATA_SECTION_OFFSET + DATA_SECTION_SIZE:X}")

    # Extract strings
    strings = extract_strings(EXE_PATH, DATA_SECTION_OFFSET, DATA_SECTION_SIZE)
    print(f"  Found {len(strings)} strings")

    # Analyze extended characters
    undecoded_bytes = analyze_extended_characters(strings)
    print(f"  Found {len(undecoded_bytes)} undecoded byte values (potential extended chars)")

    # Output paths
    script_dir = Path(__file__).parent
    csv_path = script_dir / "strings_fr.csv"
    report_path = script_dir / "verification_fr.txt"
    extended_path = script_dir / "extended_chars_fr.txt"

    # Write CSV
    write_csv(strings, csv_path, LANGUAGE)
    print(f"  Wrote {csv_path}")

    # Verification
    full_report = []

    # Spot check
    spot_ok, spot_report = spot_check_raw_exe(EXE_PATH, strings)
    full_report.append(spot_report)
    print(f"  Spot check: {'PASSED' if spot_ok else 'FAILED'}")

    # Write reports
    write_verification_report('\n\n'.join(full_report), report_path)
    print(f"  Wrote {report_path}")

    write_extended_char_analysis(undecoded_bytes, extended_path)
    print(f"  Wrote {extended_path}")

    # Find sample menu strings
    print("\n" + "=" * 60)
    print("SAMPLE EXTRACTED STRINGS (first 20 with good decoding)")
    print("=" * 60)

    good_strings = [s for s in strings if '[' not in s[2]][:20]
    for file_offset, raw_bytes, decoded in good_strings:
        print(f"0x{file_offset:X}: {decoded}")

    # Summary
    print("\n" + "=" * 60)
    print(f"EXTRACTION COMPLETE: French")
    print(f"  Total strings: {len(strings)}")
    print(f"  Output: {csv_path}")
    print(f"  Report: {report_path}")
    print(f"  Extended char analysis: {extended_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
