#!/usr/bin/env python3
"""Quick script to find string patterns in FF7 English exe"""

# Read exe data section
with open('/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe', 'rb') as f:
    f.seek(0x3B8A00 + 0x50000)  # Data section offset + 320KB into it
    data = f.read(200000)  # Read 200KB

# Build decode map (ASCII - 0x20)
decode = {}
for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    decode[0x21 + i] = c
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    decode[0x41 + i] = c
decode[0x00] = ' '

# Look for FF-terminated strings
print("Searching for FF-terminated strings...")
print()

i = 0
count = 0
while i < len(data) - 20 and count < 50:
    # Look for FF terminator
    if data[i] == 0xFF:
        i += 1
        continue

    # Scan forward to find FF
    start = i
    while i < len(data) and data[i] != 0xFF:
        i += 1

    if i < len(data) and data[i] == 0xFF:
        length = i - start
        if 3 <= length <= 20:  # Reasonable string length
            raw = data[start:i]
            hex_str = ' '.join(f'{b:02X}' for b in raw)

            # Try to decode
            decoded = ''.join(decode.get(b, f'[{b:02X}]') for b in raw)

            # Only print if mostly decodable
            if decoded.count('[') < len(decoded) * 0.3:
                offset = 0x3B8A00 + 0x50000 + start
                print(f"0x{offset:X}: {hex_str} FF")
                print(f"  Decoded: '{decoded}'")
                print()
                count += 1

    i += 1

print(f"Found {count} candidate strings")
