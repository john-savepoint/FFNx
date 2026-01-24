#!/usr/bin/env python3
"""
Generate Backlinks and FF7_COMPLETE_INDEX.md

Reads first 100 lines of all V2 markdown files to:
1. Extract YAML frontmatter
2. Build backlinks map (reverse of llm_related_docs)
3. Update referenced_by fields in all documents
4. Generate FF7_COMPLETE_INDEX.md (LLM-optimized master index)

Created: 2025-12-02 15:57 JST
Session: 887a1b3f-e34c-44f4-8434-e7e55610b603
"""

import os
import re
import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

# Directories
V2_DIR = Path("/Volumes/DevSSD/01_Development/Projects/experiments/ff70G-japanese-mod/docs/reference/game_engine/final v2")
OUTPUT_INDEX = V2_DIR / "FF7_COMPLETE_INDEX.md"

def extract_frontmatter(file_path: Path, max_lines: int = 100) -> Dict:
    """Extract YAML frontmatter from first N lines of markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = ''.join(f.readline() for _ in range(max_lines))

        # Extract YAML frontmatter between --- markers
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL | re.MULTILINE)
        if not match:
            print(f"⚠️  No frontmatter found in {file_path.name}")
            return {}

        frontmatter_text = match.group(1)
        frontmatter = yaml.safe_load(frontmatter_text)

        # Add filename for reference
        frontmatter['_filename'] = file_path.name

        return frontmatter
    except Exception as e:
        print(f"❌ Error reading {file_path.name}: {e}")
        return {}

def build_backlinks_map(all_frontmatter: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build backlinks map: for each document, track which other documents reference it.

    Returns: {filename: {set of filenames that reference it}}
    """
    backlinks = defaultdict(set)

    for fm in all_frontmatter:
        source_file = fm.get('_filename')
        if not source_file:
            continue

        # Get documents this file references
        related_docs = fm.get('llm_related_docs', [])
        if not related_docs:
            continue

        # Add backlink: for each referenced doc, record that source_file references it
        for target_doc in related_docs:
            # Handle both absolute and relative paths
            if isinstance(target_doc, str):
                target_filename = os.path.basename(target_doc)
                backlinks[target_filename].add(source_file)

    # Convert sets to sorted lists for deterministic output
    return {k: sorted(list(v)) for k, v in backlinks.items()}

def update_frontmatter_backlinks(file_path: Path, backlinks: List[str]) -> bool:
    """Update referenced_by field in YAML frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find and replace referenced_by field
        # Pattern: referenced_by: [] or referenced_by: [...] (with any content)
        pattern = r'(referenced_by:\s*)\[.*?\]'

        # Format backlinks as YAML array
        if backlinks:
            backlinks_yaml = '[' + ', '.join(f'"{doc}"' for doc in backlinks) + ']'
        else:
            backlinks_yaml = '[]'

        replacement = f'referenced_by: {backlinks_yaml}'

        # Replace in content
        new_content = re.sub(pattern, replacement, content, count=1)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"❌ Error updating {file_path.name}: {e}")
        return False

def generate_llm_index(all_frontmatter: List[Dict], backlinks_map: Dict[str, Set[str]]) -> str:
    """Generate FF7_COMPLETE_INDEX.md with LLM-optimized structure."""

    # Group documents by module
    by_module = defaultdict(list)
    for fm in all_frontmatter:
        module = fm.get('module', 'Unknown')
        by_module[module].append(fm)

    # Sort modules
    module_order = ['History', 'Engine', 'Kernel', 'Menu', 'Field', 'Battle', 'World Map', 'Technical', 'Format', 'Other']
    sorted_modules = []
    for module in module_order:
        if module in by_module:
            sorted_modules.append((module, by_module[module]))

    # Add any remaining modules
    for module in sorted(by_module.keys()):
        if module not in module_order:
            sorted_modules.append((module, by_module[module]))

    # Build index content
    index = []
    index.append("---")
    index.append("title: \"FF7 Complete Documentation Index (LLM-Optimized)\"")
    index.append("type: \"master_index\"")
    index.append("created: \"2025-12-02 15:57 JST\"")
    index.append("session_id: \"887a1b3f-e34c-44f4-8434-e7e55610b603\"")
    index.append("llm_summary: \"Master index of all FF7 game engine documentation. LLMs should read this first to understand available documentation and navigate to specific topics.\"")
    index.append("llm_tags: [\"index\", \"master\", \"navigation\", \"llm-routing\"]")
    index.append("---\n")

    index.append("# FF7 Complete Documentation Index\n")
    index.append("> [!NOTE]")
    index.append("> **For LLMs**: This is the master index of all FF7 game engine documentation. Use this to:")
    index.append("> - Understand the complete documentation structure")
    index.append("> - Find documents by topic, module, or keyword")
    index.append("> - Navigate to specific technical areas")
    index.append("> - Understand relationships between documents\n")

    # Statistics
    total_docs = len(all_frontmatter)
    total_tags = sum(len(fm.get('llm_tags', [])) for fm in all_frontmatter)
    total_backlinks = sum(len(links) for links in backlinks_map.values())

    index.append("## Documentation Statistics\n")
    index.append(f"- **Total Documents**: {total_docs}")
    index.append(f"- **Total Modules**: {len(sorted_modules)}")
    index.append(f"- **Total LLM Tags**: {total_tags}")
    index.append(f"- **Total Cross-references**: {total_backlinks}\n")

    # Table of Contents by Module
    index.append("## Table of Contents by Module\n")
    for module, docs in sorted_modules:
        index.append(f"- [{module}](#{module.lower().replace(' ', '-')})")
    index.append("")

    # Detailed module sections
    for module, docs in sorted_modules:
        index.append(f"## {module}\n")

        # Sort documents by title
        docs_sorted = sorted(docs, key=lambda x: x.get('title', ''))

        for fm in docs_sorted:
            filename = fm.get('_filename', '')
            title = fm.get('title', filename)
            summary = fm.get('llm_summary', 'No summary available')
            tags = fm.get('llm_tags', [])
            topics = fm.get('llm_primary_topics', [])
            related = fm.get('llm_related_docs', [])
            referenced_by = backlinks_map.get(filename, [])

            index.append(f"### [{title}]({filename})\n")
            index.append(f"**Summary**: {summary}\n")

            if tags:
                index.append(f"**Tags**: {', '.join(f'`{tag}`' for tag in tags)}\n")

            if topics:
                index.append(f"**Primary Topics**:")
                for topic in topics:
                    index.append(f"- {topic}")
                index.append("")

            if related:
                index.append(f"**Related Documents**:")
                for doc in related:
                    doc_name = os.path.basename(doc) if isinstance(doc, str) else doc
                    index.append(f"- [{doc_name}]({doc_name})")
                index.append("")

            if referenced_by:
                index.append(f"**Referenced By**: {len(referenced_by)} document(s)")
                for doc in referenced_by[:5]:  # Show first 5
                    index.append(f"- [{doc}]({doc})")
                if len(referenced_by) > 5:
                    index.append(f"- *...and {len(referenced_by) - 5} more*")
                index.append("")

            index.append("---\n")

    # Tag index
    index.append("## Tag Index\n")
    index.append("> [!NOTE]")
    index.append("> **For LLMs**: Use this tag index to find documents by keyword or topic.\n")

    # Build tag -> documents map
    tag_map = defaultdict(list)
    for fm in all_frontmatter:
        filename = fm.get('_filename', '')
        title = fm.get('title', filename)
        tags = fm.get('llm_tags', [])
        for tag in tags:
            tag_map[tag].append((filename, title))

    # Sort tags alphabetically
    for tag in sorted(tag_map.keys()):
        docs = tag_map[tag]
        index.append(f"### `{tag}` ({len(docs)} documents)\n")
        for filename, title in sorted(docs, key=lambda x: x[1]):
            index.append(f"- [{title}]({filename})")
        index.append("")

    return '\n'.join(index)

def main():
    print("════════════════════════════════════════════════════════════════════")
    print("  FF7 Documentation - Generate Backlinks and Index")
    print("════════════════════════════════════════════════════════════════════\n")

    # Step 1: Read frontmatter from all V2 documents
    print("📖 Reading frontmatter from all V2 documents...\n")

    markdown_files = sorted(V2_DIR.glob("*.md"))
    markdown_files = [f for f in markdown_files if f.name != "FF7_COMPLETE_INDEX.md"]  # Skip existing index

    all_frontmatter = []
    for md_file in markdown_files:
        print(f"  Reading: {md_file.name}")
        fm = extract_frontmatter(md_file, max_lines=100)
        if fm:
            all_frontmatter.append(fm)

    print(f"\n✅ Read frontmatter from {len(all_frontmatter)} documents\n")

    # Step 2: Build backlinks map
    print("🔗 Building backlinks map...\n")
    backlinks_map = build_backlinks_map(all_frontmatter)

    total_backlinks = sum(len(v) for v in backlinks_map.values())
    print(f"✅ Generated {total_backlinks} backlinks across {len(backlinks_map)} documents\n")

    # Show some examples
    print("📊 Example backlinks:")
    for filename, backlinks in list(backlinks_map.items())[:5]:
        print(f"  {filename} ← referenced by {len(backlinks)} doc(s)")
    print("")

    # Step 3: Update referenced_by fields
    print("📝 Updating referenced_by fields in all documents...\n")

    updated_count = 0
    for md_file in markdown_files:
        backlinks = backlinks_map.get(md_file.name, [])
        if update_frontmatter_backlinks(md_file, backlinks):
            updated_count += 1
            if backlinks:
                print(f"  ✓ {md_file.name} - {len(backlinks)} backlink(s)")

    print(f"\n✅ Updated {updated_count} documents\n")

    # Step 4: Generate LLM-optimized index
    print("📋 Generating FF7_COMPLETE_INDEX.md...\n")

    index_content = generate_llm_index(all_frontmatter, backlinks_map)

    with open(OUTPUT_INDEX, 'w', encoding='utf-8') as f:
        f.write(index_content)

    print(f"✅ Generated: {OUTPUT_INDEX}\n")

    # Summary
    print("════════════════════════════════════════════════════════════════════")
    print("  COMPLETE")
    print("════════════════════════════════════════════════════════════════════")
    print(f"✅ Processed: {len(all_frontmatter)} documents")
    print(f"✅ Generated: {total_backlinks} backlinks")
    print(f"✅ Updated: {updated_count} frontmatter blocks")
    print(f"✅ Created: FF7_COMPLETE_INDEX.md")
    print("")

if __name__ == "__main__":
    main()
