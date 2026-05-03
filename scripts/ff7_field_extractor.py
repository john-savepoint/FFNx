#!/usr/bin/env python3
"""
FF7 Field File Extractor and LZS Decompressor

Created: 2025-12-10 14:45 JST
Last Modified: 2025-12-10 15:06 JST
Author: Claude Code
Session-ID: 94f5f148-6c89-4d95-a0b5-104c7ebdd735

Purpose: Extract and decompress FF7 field files from LGP archives to analyze
         Japanese text encoding, specifically to find the heart symbol (♥) encoding.

Context: This script was created during investigation of why heart symbols don't
         render in FFNx when playing with Japanese field text. The hearts display
         correctly in the Japanese eStore version but not in FFNx.

Key Finding: The heart symbol uses byte 0xD9 (217) directly from jafont_1[217],
             NOT the FE D9 sequence (which is a color code for white).

FF7 LZS Compression Format:
- First 4 bytes: uncompressed size (uint32 LE)
- Control bytes: 8 flags per byte, 1=literal, 0=reference
- Reference: 2 bytes encoding (offset, length)
  - Low byte first, then high byte
  - offset = ((high & 0xF0) << 4) | low  (12 bits, 1-4096 range)
  - length = (high & 0x0F) + 3  (4 bits + 3, so 3-18 range)

LGP Archive Format:
- 12 bytes: Magic "SQUARESOFT\0\0"
- 4 bytes: Number of files (uint32 LE)
- TOC entries (27 bytes each):
  - 20 bytes: Filename (null-padded)
  - 4 bytes: Offset (uint32 LE)
  - 1 byte: Unknown
  - 2 bytes: Conflict index

Usage:
    python3 ff7_field_extractor.py

    Extracts and analyzes field files from jfleve.lgp (Japanese field LGP).
"""

import struct
import os
from pathlib import Path


def lzs_decompress(data: bytes) -> bytes:
    """
    Decompress FF7 LZS compressed data.

    Args:
        data: Compressed data with 4-byte size header

    Returns:
        Decompressed data
    """
    if len(data) < 4:
        raise ValueError("Data too short for LZS header")

    # First 4 bytes = uncompressed size
    uncompressed_size = struct.unpack('<I', data[:4])[0]

    if uncompressed_size == 0:
        return b''

    # Output buffer
    output = bytearray()

    # Input position (skip 4-byte header)
    pos = 4

    while len(output) < uncompressed_size and pos < len(data):
        # Read control byte
        if pos >= len(data):
            break
        control = data[pos]
        pos += 1

        # Process 8 bits
        for bit in range(8):
            if len(output) >= uncompressed_size:
                break
            if pos >= len(data):
                break

            if control & (1 << bit):
                # Literal byte
                output.append(data[pos])
                pos += 1
            else:
                # Reference (copy from earlier in output)
                if pos + 1 >= len(data):
                    break

                low = data[pos]
                high = data[pos + 1]
                pos += 2

                # Decode offset and length
                # offset is 12 bits: upper 4 bits of high byte + all 8 bits of low byte
                offset = ((high & 0xF0) << 4) | low
                length = (high & 0x0F) + 3

                # Copy from ring buffer position
                # The offset is relative to a 4096-byte ring buffer
                # Position in output = (current_pos - offset - 1) mod 4096
                # But we simplify: offset from current position
                if offset == 0:
                    offset = 4096

                # Start position to copy from
                copy_pos = len(output) - offset
                if copy_pos < 0:
                    # Pre-fill with zeros if referencing before start
                    for _ in range(length):
                        if len(output) >= uncompressed_size:
                            break
                        if copy_pos < 0:
                            output.append(0)
                        else:
                            output.append(output[copy_pos])
                        copy_pos += 1
                else:
                    # Normal copy
                    for i in range(length):
                        if len(output) >= uncompressed_size:
                            break
                        # Note: copy_pos + i might equal current output length
                        # This is valid - it's a run-length encoding case
                        if copy_pos + i < len(output):
                            output.append(output[copy_pos + i])
                        else:
                            # RLE case - repeat the pattern
                            output.append(output[copy_pos + (i % (len(output) - copy_pos))])

    # Verify size
    if len(output) != uncompressed_size:
        print(f"WARNING: Decompressed size {len(output)} != expected {uncompressed_size}")

    return bytes(output)


def read_lgp_toc(lgp_path: str) -> list:
    """
    Read LGP archive table of contents.

    Returns list of (filename, offset, size) tuples.
    """
    entries = []

    with open(lgp_path, 'rb') as f:
        # Magic: 12 bytes "SQUARESOFT\0\0" or similar
        magic = f.read(12)

        # Number of files
        num_files = struct.unpack('<I', f.read(4))[0]

        # Read TOC entries
        for i in range(num_files):
            # Filename: 20 bytes null-padded
            filename = f.read(20).rstrip(b'\x00').decode('ascii', errors='ignore')
            # Offset: 4 bytes
            offset = struct.unpack('<I', f.read(4))[0]
            # Unknown: 1 byte
            unk = struct.unpack('<B', f.read(1))[0]
            # Conflict index: 2 bytes
            conflict = struct.unpack('<H', f.read(2))[0]

            entries.append({
                'filename': filename,
                'offset': offset,
                'index': i
            })

    return entries


def extract_lgp_file(lgp_path: str, filename: str) -> bytes:
    """
    Extract a single file from an LGP archive.
    """
    entries = read_lgp_toc(lgp_path)

    for entry in entries:
        if entry['filename'].lower() == filename.lower():
            with open(lgp_path, 'rb') as f:
                f.seek(entry['offset'])
                # Entry header: name (20 bytes) + size (4 bytes)
                entry_name = f.read(20).rstrip(b'\x00').decode('ascii', errors='ignore')
                file_size = struct.unpack('<I', f.read(4))[0]
                file_data = f.read(file_size)
                return file_data

    raise ValueError(f"File '{filename}' not found in LGP")


def decompress_field_file(data: bytes) -> bytes:
    """
    Decompress a field file from LGP.

    Field files have a 4-byte header indicating compressed size,
    followed by LZS compressed data.
    """
    # First 4 bytes = LZS uncompressed size (the LZS header)
    # The entire data IS the LZS stream
    return lzs_decompress(data)


def parse_field_sections(data: bytes) -> list:
    """
    Parse the sections of a decompressed field file.

    Structure after decompression:
    - 2 bytes: Padding (0x0000)
    - 4 bytes: Number of sections (usually 9)
    - N*4 bytes: Section offsets (from start of section data)
    - Section data
    """
    if len(data) < 6:
        return []

    # Skip 2-byte padding? Actually let's check
    # The structure varies - let's try to detect it

    # Try reading as section count at different offsets
    for start_offset in [0, 2, 4]:
        if start_offset + 4 > len(data):
            continue

        num_sections = struct.unpack('<I', data[start_offset:start_offset+4])[0]

        if 0 < num_sections <= 12:  # Reasonable section count
            offset_start = start_offset + 4

            if offset_start + num_sections * 4 > len(data):
                continue

            # Read section offsets
            offsets = []
            valid = True
            for i in range(num_sections):
                off = struct.unpack('<I', data[offset_start + i*4:offset_start + i*4 + 4])[0]
                offsets.append(off)

            # Verify offsets are reasonable
            section_data_start = offset_start + num_sections * 4
            max_offset = len(data) - section_data_start

            if all(off <= max_offset + 10000 for off in offsets):  # Allow some slack
                sections = []
                for i, off in enumerate(offsets):
                    # Calculate section size
                    if i + 1 < len(offsets):
                        size = offsets[i + 1] - off
                    else:
                        size = len(data) - section_data_start - off

                    abs_offset = section_data_start + off
                    if abs_offset < len(data):
                        section_data = data[abs_offset:abs_offset + size]
                        sections.append({
                            'index': i,
                            'offset': off,
                            'abs_offset': abs_offset,
                            'size': size,
                            'data': section_data
                        })

                return sections

    return []


def search_pattern_in_data(data: bytes, pattern: bytes, context_bytes: int = 50) -> list:
    """
    Search for a byte pattern and return matches with context.
    """
    matches = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break

        start = max(0, pos - context_bytes)
        end = min(len(data), pos + len(pattern) + context_bytes)

        matches.append({
            'offset': pos,
            'before': data[start:pos],
            'match': data[pos:pos + len(pattern)],
            'after': data[pos + len(pattern):end],
            'full_context': data[start:end]
        })
        pos += 1

    return matches


def main():
    """Main function to extract and analyze field files."""
    import sys

    # Configuration
    lgp_path = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/data/field/jfleve.lgp"

    print("FF7 Field File Extractor")
    print("=" * 60)

    # List available files
    print(f"\nReading LGP: {lgp_path}")
    entries = read_lgp_toc(lgp_path)
    print(f"Found {len(entries)} files")

    # Find files that might contain the dialogue
    # The dialogue is from Jessie on the train - likely tin_1 through tin_4
    train_files = [e for e in entries if 'tin' in e['filename'].lower()]
    print(f"\nTrain-related files:")
    for e in train_files:
        print(f"  {e['filename']}: offset 0x{e['offset']:X}")

    # Extract and decompress tin_1
    target_file = 'tin_1'
    print(f"\nExtracting and decompressing: {target_file}")

    try:
        raw_data = extract_lgp_file(lgp_path, target_file)
        print(f"  Raw size: {len(raw_data)} bytes")

        # Decompress
        decompressed = decompress_field_file(raw_data)
        print(f"  Decompressed size: {len(decompressed)} bytes")

        # Save decompressed file for analysis
        output_dir = Path("/tmp/ff7_field_extract")
        output_dir.mkdir(exist_ok=True)

        raw_path = output_dir / f"{target_file}_raw.dat"
        dec_path = output_dir / f"{target_file}_decompressed.dat"

        with open(raw_path, 'wb') as f:
            f.write(raw_data)
        with open(dec_path, 'wb') as f:
            f.write(decompressed)

        print(f"  Saved raw to: {raw_path}")
        print(f"  Saved decompressed to: {dec_path}")

        # Search for 秘密 pattern (FB 23 FD 3D)
        himitsu = bytes([0xFB, 0x23, 0xFD, 0x3D])
        print(f"\nSearching for 秘密 (FB 23 FD 3D) in decompressed data...")

        matches = search_pattern_in_data(decompressed, himitsu, context_bytes=100)
        print(f"Found {len(matches)} matches")

        for i, m in enumerate(matches):
            print(f"\n--- Match {i+1} at offset 0x{m['offset']:X} ---")
            print(f"Before ({len(m['before'])} bytes):")
            print(f"  {' '.join(f'{b:02X}' for b in m['before'][-30:])}")
            print(f"Match: {' '.join(f'{b:02X}' for b in m['match'])}")
            print(f"After ({len(m['after'])} bytes):")
            print(f"  {' '.join(f'{b:02X}' for b in m['after'][:50])}")

        # Parse sections
        print(f"\nParsing field sections...")
        sections = parse_field_sections(decompressed)
        print(f"Found {len(sections)} sections")

        for sec in sections:
            print(f"  Section {sec['index']}: offset=0x{sec['offset']:X}, size={sec['size']}")

            # Search in each section too
            sec_matches = search_pattern_in_data(sec['data'], himitsu, context_bytes=50)
            if sec_matches:
                print(f"    Contains {len(sec_matches)} 秘密 matches!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
