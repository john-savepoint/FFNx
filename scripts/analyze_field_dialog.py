#!/usr/bin/env python3
"""
Analyze FF7 field file dialog structure to understand color codes and animations.
"""
import struct
import sys

def analyze_lgp(lgp_path, field_name="md1stin"):
    """Extract and analyze a field file from the LGP archive."""

    with open(lgp_path, "rb") as f:
        # Read LGP header
        magic = f.read(12)
        print(f"LGP Magic: {magic}")

        num_files = struct.unpack("<I", f.read(4))[0]
        print(f"Number of files: {num_files}")

        # Read TOC
        toc = []
        for _ in range(num_files):
            name_bytes = f.read(20)
            name = name_bytes.rstrip(b"\x00").decode("ascii", errors="replace")
            offset = struct.unpack("<I", f.read(4))[0]
            f.read(3)  # unknown
            toc.append((name, offset))

        # Find target field
        for name, offset in toc:
            if name == field_name:
                print(f"\nFound field '{name}' at offset 0x{offset:X}")

                f.seek(offset)

                # Read field file header (blank LZSS header on PC)
                field_header = f.read(4)
                print(f"Field header: {field_header.hex()}")

                # Read section offsets
                num_sections = struct.unpack("<I", f.read(4))[0]
                print(f"Number of sections: {num_sections}")

                section_offsets = []
                for i in range(num_sections):
                    sec_offset = struct.unpack("<I", f.read(4))[0]
                    section_offsets.append(sec_offset)
                    print(f"  Section {i}: offset 0x{sec_offset:X}")

                # Calculate section sizes
                base_offset = f.tell()

                # Read Section 0 (Script/Dialog)
                f.seek(offset + section_offsets[0])

                # Read a chunk of section 0
                section0_data = f.read(8000)

                print(f"\n=== Section 0 (Script/Dialog) Analysis ===")
                print(f"First 100 bytes: {section0_data[:100].hex()}")

                # Look for color codes
                print(f"\n--- Color Control Codes (D0-D7) ---")
                color_names = {
                    0xD0: "GRAY",
                    0xD1: "BLUE",
                    0xD2: "RED",
                    0xD3: "PURPLE",
                    0xD4: "GREEN",
                    0xD5: "CYAN",
                    0xD6: "YELLOW",
                    0xD7: "WHITE"
                }

                found_colors = {}
                for i, b in enumerate(section0_data):
                    if 0xD0 <= b <= 0xD7:
                        if b not in found_colors:
                            found_colors[b] = []
                        found_colors[b].append(i)

                for code, positions in sorted(found_colors.items()):
                    print(f"  0x{code:02X} ({color_names[code]}): {len(positions)} occurrences")
                    # Show first few with context
                    for pos in positions[:3]:
                        start = max(0, pos-5)
                        end = min(len(section0_data), pos+15)
                        context = section0_data[start:end]
                        print(f"    +{pos}: {context.hex()}")

                # Look for window opcodes
                print(f"\n--- Window Opcodes (50-57) ---")
                opcode_names = {
                    0x50: "WINDOW (init)",
                    0x51: "WMOVE (move)",
                    0x52: "WMODE (mode)",
                    0x53: "unknown",
                    0x54: "WCLSE (close)",
                    0x55: "unknown",
                    0x56: "unknown",
                    0x57: "SWCOL (set color)"
                }

                found_opcodes = {}
                for i, b in enumerate(section0_data):
                    if 0x50 <= b <= 0x57:
                        if b not in found_opcodes:
                            found_opcodes[b] = []
                        found_opcodes[b].append(i)

                for code, positions in sorted(found_opcodes.items()):
                    print(f"  0x{code:02X} ({opcode_names[code]}): {len(positions)} occurrences")

                return

        print(f"Field '{field_name}' not found!")

if __name__ == "__main__":
    lgp_path = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/data/field/flevel.lgp"
    field = sys.argv[1] if len(sys.argv) > 1 else "md1stin"
    analyze_lgp(lgp_path, field)
