#!/usr/bin/env python3
"""
FF7 Scene.bin Text Extractor
============================
Created: 2025-12-26 16:20 JST
Session: 2e703ab4-4b5e-4772-8894-ba089b4f437c
Author: Claude Code

Extracts enemy names and attack names from FF7 scene.bin files for all languages.
Outputs binary .dat files for use with FFNx text injection system.

Scene.bin Structure:
- 256 GZIP-compressed scenes in ~33 8KB blocks
- Each scene is 7808 bytes uncompressed (EN) or smaller (JA)
- Enemy names at: 0x0298, 0x0350, 0x0408 (first 32 bytes of each enemy data)
- Attack names at: 0x0880 (32 × 32 bytes)
- Japanese uses 16-byte names instead of 32

Usage:
    python extract_scene_text.py [scene.bin path] [output.dat] [--japanese]
    python extract_scene_text.py --all  # Extract all languages to default paths
"""

import struct
import gzip
import os
import sys
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, asdict
from io import BytesIO

# Constants
BLOCK_SIZE = 0x2000  # 8192 bytes
MAX_SCENES = 256
SCENE_SIZE_EN = 7808  # English/Western scene size
SCENE_SIZE_JA = 7808  # Japanese (same total, different field sizes)

# Offsets for English/Western (32-byte names)
ENEMY_DATA_OFFSETS_EN = [0x0298, 0x0350, 0x0408]  # 3 enemies per scene
ENEMY_NAME_SIZE_EN = 32
ATTACK_NAMES_OFFSET_EN = 0x0880
ATTACK_NAME_SIZE_EN = 32
ATTACK_COUNT = 32

# Offsets for Japanese (16-byte names)
ENEMY_NAME_SIZE_JA = 16
ATTACK_NAME_SIZE_JA = 16
# Japanese offsets are different due to smaller name fields
# Enemy data structure is: name (16) + other_data (184-32+16 = 168)
# Need to recalculate offsets for Japanese...
# Actually, the total enemy data size changes, so all offsets shift
# From the docs: "In the japanese scene.bin, ennemies names and attacks names have a size of 16 bytes, instead of 32 bytes."


@dataclass
class EnemyText:
    """Text data for a single enemy"""
    name: bytes  # Raw FF7 encoded bytes
    name_str: str  # Decoded for display


@dataclass
class SceneText:
    """Text data for a single scene"""
    scene_id: int
    enemies: List[EnemyText]  # 3 enemies max
    attack_names: List[bytes]  # 32 attacks max


def decode_ff7_text(data: bytes) -> str:
    """
    Decode FF7 text bytes to readable string.
    FF7 PC uses a simple encoding: byte + 0x20 = ASCII character.
    0x00 = space, 0xFF = string terminator.
    """
    result = []
    for byte in data:
        if byte == 0xFF:  # String terminator
            break
        elif byte == 0x00:
            result.append(' ')
        elif 0x01 <= byte <= 0xFE:
            # FF7 encoding: add 0x20 to get ASCII
            ascii_val = byte + 0x20
            if 0x20 <= ascii_val <= 0x7E:
                result.append(chr(ascii_val))
            else:
                # Extended character - show hex
                result.append(f'[{byte:02X}]')
        else:
            result.append(f'[{byte:02X}]')
    return ''.join(result).strip()


def read_scene_bin_scenes(filepath: str, is_japanese: bool = False) -> List[bytes]:
    """
    Read and decompress all scenes from a scene.bin file.
    Returns list of decompressed scene data.
    """
    scenes = []

    with open(filepath, 'rb') as f:
        file_data = f.read()

    file_size = len(file_data)
    num_blocks = (file_size + BLOCK_SIZE - 1) // BLOCK_SIZE

    scene_count = 0

    for block_idx in range(num_blocks):
        block_offset = block_idx * BLOCK_SIZE

        if block_offset >= file_size:
            break

        # Read block header (up to 16 pointers)
        pointers = []
        for i in range(16):
            ptr_offset = block_offset + (i * 4)
            if ptr_offset + 4 > file_size:
                break
            ptr = struct.unpack_from('<I', file_data, ptr_offset)[0]
            if ptr == 0xFFFFFFFF:
                break
            pointers.append(ptr * 4)  # Multiply by 4 to get actual offset

        # Extract and decompress each scene in this block
        for i, ptr in enumerate(pointers):
            abs_offset = block_offset + ptr

            # Determine end of this scene's data
            if i + 1 < len(pointers):
                next_ptr = pointers[i + 1]
                end_offset = block_offset + next_ptr
            else:
                end_offset = block_offset + BLOCK_SIZE

            if abs_offset >= file_size:
                continue

            end_offset = min(end_offset, file_size)
            compressed_data = file_data[abs_offset:end_offset]

            # Strip trailing 0xFF padding
            while compressed_data and compressed_data[-1] == 0xFF:
                compressed_data = compressed_data[:-1]

            if not compressed_data:
                continue

            try:
                # Decompress GZIP data
                decompressed = gzip.decompress(compressed_data)
                scenes.append(decompressed)
                scene_count += 1

                if scene_count >= MAX_SCENES:
                    return scenes

            except Exception as e:
                print(f"Warning: Failed to decompress scene {scene_count} in block {block_idx}: {e}")
                scenes.append(b'')  # Empty placeholder
                scene_count += 1

    return scenes


def extract_scene_text(scene_data: bytes, scene_id: int, is_japanese: bool = False) -> Optional[SceneText]:
    """
    Extract enemy names and attack names from a decompressed scene.
    """
    if not scene_data or len(scene_data) < 0x0C80:
        return None

    name_size = ENEMY_NAME_SIZE_JA if is_japanese else ENEMY_NAME_SIZE_EN
    attack_name_size = ATTACK_NAME_SIZE_JA if is_japanese else ATTACK_NAME_SIZE_EN

    # For Japanese, offsets are different due to smaller name fields
    # The enemy data blocks are smaller, so everything shifts
    if is_japanese:
        # Japanese enemy data is 168 bytes (184 - 16 saved from name)
        enemy_data_size = 184 - 16  # 168 bytes
        enemy_offsets = [
            0x0298,  # Enemy 1 (same start)
            0x0298 + 168,  # Enemy 2
            0x0298 + 168 * 2,  # Enemy 3
        ]
        # Attack names offset shifts too
        # Original: 0x0880
        # Shift: 3 enemies × 16 bytes saved = 48 bytes
        # But also attack data and attack IDs might shift...
        # Actually need to recalculate based on actual Japanese format
        # For now, let's try the standard offsets and see
        attack_names_offset = 0x0880 - 48  # Rough estimate
    else:
        enemy_offsets = ENEMY_DATA_OFFSETS_EN
        attack_names_offset = ATTACK_NAMES_OFFSET_EN

    enemies = []
    for i, offset in enumerate(enemy_offsets):
        if offset + name_size > len(scene_data):
            break
        name_bytes = scene_data[offset:offset + name_size]
        enemies.append(EnemyText(
            name=name_bytes,
            name_str=decode_ff7_text(name_bytes)
        ))

    # Extract attack names
    attack_names = []
    for i in range(ATTACK_COUNT):
        offset = attack_names_offset + (i * attack_name_size)
        if offset + attack_name_size > len(scene_data):
            break
        attack_names.append(scene_data[offset:offset + attack_name_size])

    return SceneText(
        scene_id=scene_id,
        enemies=enemies,
        attack_names=attack_names
    )


def extract_all_text(scene_bin_path: str, is_japanese: bool = False) -> List[SceneText]:
    """
    Extract all text from a scene.bin file.
    """
    print(f"Reading: {scene_bin_path}")
    scenes = read_scene_bin_scenes(scene_bin_path, is_japanese)
    print(f"Decompressed {len(scenes)} scenes")

    results = []
    for i, scene_data in enumerate(scenes):
        text = extract_scene_text(scene_data, i, is_japanese)
        if text:
            results.append(text)

    print(f"Extracted text from {len(results)} scenes")
    return results


def write_dat_file(texts: List[SceneText], output_path: str, is_japanese: bool = False):
    """
    Write extracted text to binary .dat file for FFNx.

    Format:
    - Header: "ET01" (4 bytes) + version (2 bytes) + flags (2 bytes) + scene_count (4 bytes)
    - For each scene:
      - Enemy 1 name (32 bytes, padded with 0xFF)
      - Enemy 2 name (32 bytes)
      - Enemy 3 name (32 bytes)
      - Attack names (32 × 32 bytes)
    """
    name_size = 16 if is_japanese else 32

    with open(output_path, 'wb') as f:
        # Write header
        f.write(b'ET01')  # Magic
        f.write(struct.pack('<H', 1))  # Version
        f.write(struct.pack('<H', 1 if is_japanese else 0))  # Flags (1 = Japanese)
        f.write(struct.pack('<I', len(texts)))  # Scene count

        # Write each scene's text
        for text in texts:
            # Write enemy names (always 3 slots, padded)
            for i in range(3):
                if i < len(text.enemies):
                    name = text.enemies[i].name[:name_size]
                else:
                    name = b''
                # Pad to fixed size
                name = name.ljust(name_size, b'\xff')
                f.write(name)

            # Write attack names (always 32 slots)
            for i in range(ATTACK_COUNT):
                if i < len(text.attack_names):
                    name = text.attack_names[i][:name_size]
                else:
                    name = b''
                name = name.ljust(name_size, b'\xff')
                f.write(name)

    print(f"Wrote: {output_path}")


def write_json_file(texts: List[SceneText], output_path: str):
    """
    Write extracted text to JSON file for debugging/inspection.
    """
    data = {
        'version': 1,
        'scene_count': len(texts),
        'scenes': []
    }

    for text in texts:
        scene_data = {
            'scene_id': text.scene_id,
            'enemies': [
                {
                    'name_hex': e.name.hex(),
                    'name_decoded': e.name_str
                }
                for e in text.enemies
            ],
            'attacks': [
                {
                    'name_hex': a.hex(),
                    'name_decoded': decode_ff7_text(a)
                }
                for a in text.attack_names
                if a and a[0] != 0xFF  # Skip empty attacks
            ]
        }
        data['scenes'].append(scene_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote: {output_path}")


def extract_all_languages():
    """
    Extract text from all language versions of scene.bin.
    """
    # Define paths
    steam_base = "/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/data"
    output_base = "/home/johnzealanddoyle/projects/ff7OG_japanese/data/scene_text"

    # Create output directory
    os.makedirs(output_base, exist_ok=True)

    languages = [
        ('en', f"{steam_base}/lang-en/battle/scene.bin", False),
        ('de', f"{steam_base}/lang-de/battle/scene.bin", False),
        ('fr', f"{steam_base}/lang-fr/battle/scene.bin", False),
        ('es', f"{steam_base}/lang-es/battle/scene.bin", False),
        ('ja', f"{steam_base}/lang-ja/battle/scene.bin", True),
    ]

    for lang_code, scene_path, is_japanese in languages:
        print(f"\n=== Extracting {lang_code.upper()} ===")

        if not os.path.exists(scene_path):
            print(f"Scene.bin not found: {scene_path}")
            continue

        try:
            texts = extract_all_text(scene_path, is_japanese)

            # Write binary .dat file
            dat_path = os.path.join(output_base, f"enemy_text_{lang_code}.dat")
            write_dat_file(texts, dat_path, is_japanese)

            # Write JSON for inspection
            json_path = os.path.join(output_base, f"enemy_text_{lang_code}.json")
            write_json_file(texts, json_path)

        except Exception as e:
            print(f"Error extracting {lang_code}: {e}")
            import traceback
            traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_scene_text.py --all")
        print("  python extract_scene_text.py <scene.bin> <output.dat> [--japanese]")
        sys.exit(1)

    if sys.argv[1] == '--all':
        extract_all_languages()
    else:
        scene_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else 'enemy_text.dat'
        is_japanese = '--japanese' in sys.argv or '-j' in sys.argv

        texts = extract_all_text(scene_path, is_japanese)
        write_dat_file(texts, output_path, is_japanese)

        # Also write JSON
        json_path = output_path.replace('.dat', '.json')
        write_json_file(texts, json_path)


if __name__ == '__main__':
    main()
