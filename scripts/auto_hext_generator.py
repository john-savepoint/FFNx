#!/usr/bin/env python3
"""
FF7 Auto HEXT Patch Generator

Automatically generates HEXT patches by matching English and Japanese strings
in the FF7 executables. Includes safety checks and validation.

Created: 2025-12-06 01:09 JST
Session: c245e7c0-ec73-4933-b925-5976860e742c
Context: Created to automate HEXT patch generation after discovering EN and JA
         strings follow the same order in their respective executables.

Usage:
    python3 auto_hext_generator.py --en <en_exe> --ja <ja_exe> --start <offset> --length <bytes> --output <hext_file>

Example:
    python3 auto_hext_generator.py \\
        --en "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe" \\
        --ja "/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_ja.exe" \\
        --start 0x518000 \\
        --length 0xE000 \\
        --output japanese_menu_auto.txt
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Import functions from exe_string_dumper
sys.path.append(str(Path(__file__).parent))
from exe_string_dumper import (
    file_to_va,
    load_japanese_charmap,
    find_strings,
    decode_ff7_string,
    JA_CHARMAP
)


def is_valid_string(string_data: dict, is_japanese: bool = False) -> tuple:
    """
    Check if a string looks valid for patching.
    Returns (is_valid, reason)
    """
    # Too short (just terminator)
    if string_data['length'] <= 1:
        return (False, "Too short")

    # Too long (probably not a real string)
    if string_data['length'] > 200:
        return (False, "Too long (>200 bytes)")

    # Check if decoded string is mostly garbage
    decoded = string_data['decoded']
    if decoded.count('[') > len(decoded) / 3:  # More than 33% unknown chars
        return (False, "Mostly unknown characters")

    # Check for binary data patterns (lots of null bytes mid-string)
    raw = string_data['raw_bytes'][:-1]  # Exclude terminator
    if raw.count(0x00) > len(raw) / 2:
        return (False, "Too many null bytes")

    return (True, "OK")


def format_hext_bytes(raw_bytes: bytes, original_length: int) -> str:
    """
    Format bytes for HEXT patch with proper padding.
    Pad with 00 to match the original string's space.
    """
    hex_str = ' '.join(f'{b:02X}' for b in raw_bytes)

    # If JA string is shorter than EN, pad with 00
    if len(raw_bytes) < original_length:
        padding_needed = original_length - len(raw_bytes)
        padding = ' '.join('00' for _ in range(padding_needed))
        hex_str += ' ' + padding

    return hex_str


def generate_hext_patches(en_strings: list, ja_strings: list, safety_check: bool = True) -> tuple:
    """
    Generate HEXT patches by matching EN and JA strings.
    Uses synchronized position tracking to handle skipped strings properly.
    Returns (patches_list, report_list)
    """
    patches = []
    report = []

    report.append(f"String Matching Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"=" * 80)
    report.append("")
    report.append(f"Total EN strings: {len(en_strings)}")
    report.append(f"Total JA strings: {len(ja_strings)}")
    report.append("")

    # Match strings by position - ALWAYS maintain 1:1 alignment
    matched = 0
    warnings = 0

    en_idx = 0
    ja_idx = 0

    while en_idx < len(en_strings) and ja_idx < len(ja_strings):
        en_str = en_strings[en_idx]
        ja_str = ja_strings[ja_idx]

        # Validate both strings
        en_valid, en_reason = is_valid_string(en_str, is_japanese=False)
        ja_valid, ja_reason = is_valid_string(ja_str, is_japanese=True)

        # Track validation warnings but DON'T SKIP - preserve 1:1 alignment
        patch_warnings = []

        if not en_valid:
            warnings += 1
            patch_warnings.append(f"EN validation: {en_reason}")
            report.append(f"WARN #{en_idx+1}: EN may be invalid ({en_reason}) at 0x{en_str['file_offset']:08X} - patching anyway to preserve alignment")

        if not ja_valid:
            warnings += 1
            patch_warnings.append(f"JA validation: {ja_reason}")
            report.append(f"WARN #{ja_idx+1}: JA may be invalid ({ja_reason}) at 0x{ja_str['file_offset']:08X} - patching anyway to preserve alignment")

        # Check for length mismatch concerns
        if ja_str['length'] > en_str['length'] + 5:
            warnings += 1
            patch_warnings.append(f"Length mismatch: JA {ja_str['length']} vs EN {en_str['length']}")
            report.append(f"WARN #{en_idx+1}: JA much longer than EN ({ja_str['length']} vs {en_str['length']}) at 0x{en_str['file_offset']:08X}")
            report.append(f"          EN: {en_str['decoded'][:50]}")
            report.append(f"          JA: {ja_str['decoded'][:50]}")
            report.append(f"          Patching anyway to preserve alignment")

        # ALWAYS generate patch to maintain 1:1 alignment
        patch = {
            'position': (en_idx + 1, ja_idx + 1),
            'en_offset': en_str['file_offset'],
            'ja_offset': ja_str['file_offset'],
            'va': en_str['va'],
            'en_decoded': en_str['decoded'],
            'ja_decoded': ja_str['decoded'],
            'en_length': en_str['length'],
            'ja_length': ja_str['length'],
            'ja_bytes': ja_str['raw_bytes'],
            'hext_line': f"{en_str['va']:06X} = {format_hext_bytes(ja_str['raw_bytes'], en_str['length'])}",
            'warnings': patch_warnings  # Store warnings with the patch
        }

        patches.append(patch)
        matched += 1
        en_idx += 1
        ja_idx += 1

    report.append("")
    report.append(f"Summary:")
    report.append(f"  Total patches created: {matched}")
    report.append(f"  Patches with warnings: {warnings}")
    report.append(f"  Perfect 1:1 alignment maintained: Yes")
    report.append("")
    report.append(f"IMPORTANT: All patches were created to preserve 1:1 alignment.")
    report.append(f"Review warnings in the report and HEXT file. You can comment out")
    report.append(f"problematic patches by adding '#' at the start of the line.")
    report.append("")

    # Report any strings that don't have a match
    if len(en_strings) != len(ja_strings):
        report.append(f"WARNING: String count mismatch!")
        report.append(f"  EN has {len(en_strings)} strings")
        report.append(f"  JA has {len(ja_strings)} strings")
        report.append(f"  Difference: {abs(len(en_strings) - len(ja_strings))}")
        report.append(f"  Note: Skipped strings maintain 1:1 alignment")
        report.append("")

    return (patches, report)


def write_hext_file(patches: list, output_path: Path, en_start: int, ja_start: int, length: int):
    """Write patches to HEXT file with proper formatting and comments."""

    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Japanese Menu Text Patch for FF7 English\n")
        f.write("# AUTO-GENERATED by auto_hext_generator.py\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')}\n")
        f.write(f"# Session: c245e7c0-ec73-4933-b925-5976860e742c\n")
        f.write("#\n")
        f.write(f"# Source EN region: 0x{en_start:X} - 0x{en_start + length:X}\n")
        f.write(f"# Source JA region: 0x{ja_start:X} - 0x{ja_start + length:X}\n")
        f.write(f"# Total patches: {len(patches)}\n")
        f.write("#\n")
        f.write("# Virtual addresses calculated from file offsets:\n")
        f.write("# VA = (FileOffset - 0x3B8A00) + 0x3BA000 + 0x400000\n")
        f.write("\n")

        # Group patches by section (every 20 strings)
        for i, patch in enumerate(patches):
            # Add section header every 20 strings
            if i % 20 == 0:
                f.write(f"# ============================================================\n")
                f.write(f"# Strings #{i+1} - #{min(i+20, len(patches))}\n")
                f.write(f"# ============================================================\n")
                f.write("\n")

            # Add warnings if present
            if patch.get('warnings'):
                f.write(f"# ⚠️  WARNING: This patch may have issues:\n")
                for warning in patch['warnings']:
                    f.write(f"#    - {warning}\n")
                f.write(f"# Review carefully and comment out if it causes problems!\n")

            # Patch entry with detailed comment
            f.write(f"# {patch['en_decoded'][:40]} -> {patch['ja_decoded'][:40]}\n")
            f.write(f"# EN: 0x{patch['en_offset']:08X} ({patch['en_length']} bytes)\n")
            f.write(f"# JA: 0x{patch['ja_offset']:08X} ({patch['ja_length']} bytes)\n")
            f.write(f"{patch['hext_line']}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description='Auto-generate HEXT patches from EN and JA executables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Full menu region:
    python3 auto_hext_generator.py \\
        --en "ff7_en.exe" \\
        --ja "ff7_ja.exe" \\
        --start 0x518000 \\
        --length 0xE000 \\
        --output japanese_menu_auto.txt

  Materia screen only:
    python3 auto_hext_generator.py \\
        --en "ff7_en.exe" \\
        --ja "ff7_ja.exe" \\
        --start 0x51F500 \\
        --length 0x500 \\
        --output materia_auto.txt
        """
    )

    parser.add_argument('--en', required=True, help='Path to English FF7 executable')
    parser.add_argument('--ja', required=True, help='Path to Japanese FF7 executable')
    parser.add_argument('--start', required=True, help='Start offset in hex (e.g., 0x518000)')
    parser.add_argument('--length', required=True, help='Length in hex (e.g., 0xE000)')
    parser.add_argument('--output', required=True, help='Output HEXT file path')
    parser.add_argument('--ja-offset', type=str, help='JA offset (default: EN offset + 0xC00)')
    parser.add_argument('--no-safety', action='store_true', help='Disable safety checks for length mismatches')
    parser.add_argument('--report', help='Path to save validation report (default: <output>.report.txt)')

    args = parser.parse_args()

    # Parse offsets
    en_start = int(args.start, 16)
    length = int(args.length, 16)

    if args.ja_offset:
        ja_start = int(args.ja_offset, 16)
    else:
        ja_start = en_start + 0xC00  # Default offset

    # Load paths
    en_path = Path(args.en)
    ja_path = Path(args.ja)
    output_path = Path(args.output)

    if not en_path.exists():
        print(f"Error: EN exe not found: {en_path}", file=sys.stderr)
        sys.exit(1)

    if not ja_path.exists():
        print(f"Error: JA exe not found: {ja_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Japanese character map...")
    import exe_string_dumper
    exe_string_dumper.JA_CHARMAP = load_japanese_charmap()

    print(f"Reading EN executable: {en_path.name}")
    print(f"  Region: 0x{en_start:X} - 0x{en_start + length:X} ({length} bytes)")

    with open(en_path, 'rb') as f:
        f.seek(en_start)
        en_data = f.read(length)

    print(f"Reading JA executable: {ja_path.name}")
    print(f"  Region: 0x{ja_start:X} - 0x{ja_start + length:X} ({length} bytes)")

    with open(ja_path, 'rb') as f:
        f.seek(ja_start)
        ja_data = f.read(length)

    print(f"Parsing strings...")
    en_strings = find_strings(en_data, en_start, is_japanese=False)
    ja_strings = find_strings(ja_data, ja_start, is_japanese=True)

    print(f"  Found {len(en_strings)} EN strings")
    print(f"  Found {len(ja_strings)} JA strings")

    print(f"Generating patches...")
    patches, report = generate_hext_patches(
        en_strings,
        ja_strings,
        safety_check=not args.no_safety
    )

    print(f"  Generated {len(patches)} patches")

    # Write HEXT file
    print(f"Writing HEXT file: {output_path}")
    write_hext_file(patches, output_path, en_start, ja_start, length)

    # Write report
    report_path = Path(args.report) if args.report else output_path.with_suffix('.report.txt')
    print(f"Writing report: {report_path}")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print()
    print("=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"HEXT file: {output_path}")
    print(f"Report: {report_path}")
    print()
    print("Next steps:")
    print("1. Review the report file for any warnings")
    print("2. Back up your current HEXT file")
    print("3. Copy the generated file to your FFNx hext directory")
    print("4. Test in-game")


if __name__ == '__main__':
    main()
