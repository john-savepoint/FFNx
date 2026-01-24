#!/usr/bin/env python3
"""
FF7 Documentation Context Extraction Script

Extracts comprehensive context from all FF7 game engine documentation files to provide
shared knowledge for standardization agents.

Outputs:
  - headings_index.json: All H1-H4 headings by document
  - links_index.json: All forward links (wiki-style and standard markdown)
  - document_categories.json: Module assignment for each document
  - image_inventory.json: All image references with validation

Created: 2025-12-01 21:00 JST
Session: 887a1b3f-e34c-44f4-8434-e7e55610b603
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def extract_headings(content: str, filename: str) -> Dict[str, List[str]]:
    """
    Extract H1-H4 headings from markdown content.

    Returns dict with keys: h1, h2, h3, h4
    Each value is a list of heading texts (without # markers)
    """
    headings = {
        'h1': [],
        'h2': [],
        'h3': [],
        'h4': []
    }

    for line in content.split('\n'):
        line = line.strip()

        # Match heading levels (H1-H4 only)
        if line.startswith('# ') and not line.startswith('## '):
            # H1
            text = line[2:].strip()
            # Remove bold formatting if present: **Text** → Text
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            headings['h1'].append(text)
        elif line.startswith('## ') and not line.startswith('### '):
            # H2
            text = line[3:].strip()
            headings['h2'].append(text)
        elif line.startswith('### ') and not line.startswith('#### '):
            # H3
            text = line[4:].strip()
            headings['h3'].append(text)
        elif line.startswith('#### ') and not line.startswith('##### '):
            # H4
            text = line[5:].strip()
            headings['h4'].append(text)

    return headings


def extract_links(content: str, filename: str) -> List[Dict]:
    """
    Extract all forward links (both wiki-style and standard markdown).

    Returns list of link dictionaries with:
      - type: "wiki" | "standard" | "external"
      - target: filename or URL
      - anchor: section anchor (if present)
      - text: link text
      - line_number: approximate line number
    """
    links = []
    line_num = 0

    for line in content.split('\n'):
        line_num += 1

        # Pattern 1: Wiki-style links
        # [BIN Archives](FF7/Kernel/Low_level_libraries#BIN-GZIP "title"){.wikilink}
        wiki_pattern = r'\[([^\]]+)\]\(([^)]+?)\s*(?:"[^"]*")?\)\{\.wikilink\}'
        for match in re.finditer(wiki_pattern, line):
            link_text = match.group(1)
            link_path = match.group(2)

            # Parse path and anchor
            if '#' in link_path:
                path, anchor = link_path.split('#', 1)
            else:
                path, anchor = link_path, None

            # Convert wiki path to filename
            # FF7/Kernel/Overview → FF7_Kernel_Overview.md
            target = path.replace('/', '_') + '.md' if not path.startswith('http') else path

            links.append({
                'type': 'wiki',
                'target': target,
                'anchor': anchor,
                'text': link_text,
                'line_number': line_num,
                'original_path': link_path
            })

        # Pattern 2: Standard markdown links
        # [Memory Management](FF7_Kernel_Memory_management.md#ram-management)
        # [External link](https://example.com)
        std_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(std_pattern, line):
            link_text = match.group(1)
            link_target = match.group(2)

            # Skip if already matched as wiki link
            if '{.wikilink}' in line[match.end():match.end()+20]:
                continue

            # Determine if external or internal
            if link_target.startswith('http://') or link_target.startswith('https://'):
                link_type = 'external'
                anchor = None
            else:
                link_type = 'standard'
                # Parse anchor
                if '#' in link_target:
                    link_target, anchor = link_target.split('#', 1)
                else:
                    anchor = None

            if link_type != 'external':  # Only track internal links
                links.append({
                    'type': link_type,
                    'target': link_target,
                    'anchor': anchor,
                    'text': link_text,
                    'line_number': line_num
                })

    return links


def categorize_document(filename: str) -> str:
    """
    Assign module category based on filename pattern.

    Returns: "Kernel" | "Battle" | "Field" | "World Map" | "Menu" |
             "Sound" | "Reference" | "Format Spec" | "Historical" | "Container"
    """
    fn = filename.lower()

    # Historical
    if 'history' in fn:
        return 'Historical'

    # Kernel module
    if 'kernel' in fn:
        return 'Kernel'

    # Battle module
    if 'battle' in fn:
        return 'Battle'

    # Field module
    if 'field' in fn:
        return 'Field'

    # World Map module
    if 'world' in fn or 'worldmap' in fn:
        return 'World Map'

    # Menu module
    if 'menu' in fn:
        return 'Menu'

    # Sound module
    if 'sound' in fn or 'akao' in fn or 'instr' in fn:
        return 'Sound'

    # Format specifications
    if any(fmt in fn for fmt in ['_format', 'tim', 'tex', 'lgp', 'lzss']):
        return 'Format Spec'

    # Reference/Technical
    if any(word in fn for word in ['technical', 'item', 'materia', 'savemap', 'chocobo']):
        return 'Reference'

    # Engine basics
    if 'engine' in fn:
        return 'Overview'

    # Container files (TOC only)
    if fn in ['ff7.md', 'readme.md', 'ff7_psx_sound.md']:
        return 'Container'

    # Default
    return 'Reference'


def extract_images(content: str, filename: str) -> List[Dict]:
    """
    Extract all image references with their paths.

    Returns list of image dictionaries with:
      - alt_text: image alt text
      - path: image path (as written in markdown)
      - filename: just the image filename
      - line_number: approximate line number
    """
    images = []
    line_num = 0

    for line in content.split('\n'):
        line_num += 1

        # Pattern: ![alt text](path/to/image.png)
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(img_pattern, line):
            alt_text = match.group(1)
            img_path = match.group(2)

            # Extract just the filename
            img_filename = os.path.basename(img_path)

            images.append({
                'alt_text': alt_text,
                'path': img_path,
                'filename': img_filename,
                'line_number': line_num
            })

    return images


def validate_images(all_images: Dict[str, List[Dict]], images_dir: Path) -> Dict:
    """
    Validate that all referenced images exist in the images directory.

    Returns validation report with exists/missing status for each unique image.
    """
    # Collect all unique image filenames
    unique_images = set()
    for doc_images in all_images.values():
        for img in doc_images:
            unique_images.add(img['filename'])

    # Check existence
    validation = {}
    for img_filename in sorted(unique_images):
        img_path = images_dir / img_filename
        validation[img_filename] = {
            'exists': img_path.exists(),
            'path': str(img_path),
            'referenced_by': []
        }

    # Add reference information
    for doc_filename, doc_images in all_images.items():
        for img in doc_images:
            validation[img['filename']]['referenced_by'].append({
                'document': doc_filename,
                'line_number': img['line_number'],
                'current_path': img['path']
            })

    return validation


def process_documents(source_dir: Path, images_dir: Path) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Process all markdown files and extract context data.

    Returns: (headings_index, links_index, categories, image_inventory)
    """
    headings_index = {}
    links_index = {}
    categories = {}
    all_images = {}

    # Get all .md files
    md_files = list(source_dir.glob('*.md'))

    # Exclude special files
    exclude = {'repomix-markdown-only.md', 'README.md', 'FF7_GameEngine_MERGED.md'}
    md_files = [f for f in md_files if f.name not in exclude]

    print(f"Processing {len(md_files)} markdown files...")

    for md_file in sorted(md_files):
        filename = md_file.name
        print(f"  • {filename}")

        # Read content
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"    ⚠️  Error reading {filename}: {e}")
            continue

        # Extract data
        headings_index[filename] = extract_headings(content, filename)
        links_index[filename] = extract_links(content, filename)
        categories[filename] = categorize_document(filename)
        all_images[filename] = extract_images(content, filename)

    # Validate images
    image_inventory = validate_images(all_images, images_dir)

    return headings_index, links_index, categories, image_inventory


def generate_summary_stats(headings_index: Dict, links_index: Dict,
                          categories: Dict, image_inventory: Dict) -> Dict:
    """Generate summary statistics for reporting."""

    total_docs = len(headings_index)
    total_headings = sum(
        len(h['h1']) + len(h['h2']) + len(h['h3']) + len(h['h4'])
        for h in headings_index.values()
    )
    total_links = sum(len(links) for links in links_index.values())
    total_images = len(image_inventory)
    images_missing = sum(1 for img in image_inventory.values() if not img['exists'])

    # Category distribution
    category_counts = defaultdict(int)
    for cat in categories.values():
        category_counts[cat] += 1

    return {
        'documents_processed': total_docs,
        'total_headings': total_headings,
        'total_links': total_links,
        'total_unique_images': total_images,
        'images_missing': images_missing,
        'category_distribution': dict(category_counts)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Extract context from FF7 documentation for standardization agents'
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Source directory containing markdown files'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for context JSON files'
    )
    parser.add_argument(
        '--images',
        default=None,
        help='Images directory for validation (default: source/../images)'
    )

    args = parser.parse_args()

    # Convert to Path objects
    source_dir = Path(args.source)
    output_dir = Path(args.output)

    if args.images:
        images_dir = Path(args.images)
    else:
        images_dir = source_dir.parent / 'images'

    # Validate directories
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1

    if not images_dir.exists():
        print(f"⚠️  Images directory not found: {images_dir}")
        print(f"   Image validation will show all as missing.")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("FF7 Documentation Context Extraction")
    print("="*60)
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print(f"Images: {images_dir}")
    print()

    # Process documents
    headings_index, links_index, categories, image_inventory = process_documents(
        source_dir, images_dir
    )

    # Generate stats
    stats = generate_summary_stats(headings_index, links_index, categories, image_inventory)

    # Write output files
    print("\nWriting output files...")

    output_files = {
        'headings_index.json': headings_index,
        'links_index.json': links_index,
        'document_categories.json': categories,
        'image_inventory.json': image_inventory,
        'extraction_stats.json': stats
    }

    for filename, data in output_files.items():
        output_path = output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ {filename}")

    # Print summary
    print("\n" + "="*60)
    print("Extraction Summary")
    print("="*60)
    print(f"Documents processed: {stats['documents_processed']}")
    print(f"Total headings extracted: {stats['total_headings']}")
    print(f"Total links extracted: {stats['total_links']}")
    print(f"Unique images found: {stats['total_unique_images']}")
    if stats['images_missing'] > 0:
        print(f"⚠️  Images missing: {stats['images_missing']}")
    else:
        print(f"✓ All images validated")

    print("\nCategory distribution:")
    for cat, count in sorted(stats['category_distribution'].items()):
        print(f"  {cat:15s}: {count:2d} documents")

    print("\n✅ Context extraction complete!")
    print(f"\nOutput files written to: {output_dir}")

    return 0


if __name__ == '__main__':
    exit(main())
