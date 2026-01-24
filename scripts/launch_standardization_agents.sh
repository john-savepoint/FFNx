#!/bin/bash
#
# FF7 Documentation Standardization - Agent Launcher
#
# Launches Claude Code agents in headless mode to standardize all 37 FF7 documentation files.
# Uses wave-based execution with checkpoints for quality control.
#
# Created: 2025-12-01 21:20 JST
# Session: 887a1b3f-e34c-44f4-8434-e7e55610b603
#
# Usage:
#   ./launch_standardization_agents.sh [wave_number]
#
#   wave_number: 1-8 (or 'all' to run all waves)
#   If not specified, runs Wave 1 only
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="/Volumes/DevSSD/01_Development/Projects/experiments/ff70G-japanese-mod"
SOURCE_DIR="$PROJECT_ROOT/docs/reference/game_engine/markdown/merged_with_pdf_content"
OUTPUT_DIR="$PROJECT_ROOT/docs/reference/game_engine/final"
CONTEXT_DIR="$PROJECT_ROOT/.claude/data/ff7-docs-context"
TEMP_DIR="$PROJECT_ROOT/.claude/tmp/agent-prompts"
SUMMARIES_FILE="$CONTEXT_DIR/agent_summaries.json"

# Wave configuration (5 documents per wave)
WAVE_SIZE=5
SKIP_CHECKPOINTS=false

# Parse arguments
WAVE_NUMBER="1"
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-checkpoints|--auto)
            SKIP_CHECKPOINTS=true
            shift
            ;;
        [1-8]|all)
            WAVE_NUMBER="$1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" >&2
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# ============================================================================
# Validation
# ============================================================================

validate_environment() {
    log_info "Validating environment..."

    # Check Claude Code is available
    if ! command -v claude &> /dev/null; then
        log_error "Claude Code CLI not found. Please install Claude Code."
        exit 1
    fi

    # Check context files exist
    if [ ! -f "$CONTEXT_DIR/headings_index.json" ]; then
        log_error "Context files not found. Run extract_doc_context.py first."
        exit 1
    fi

    # Check source directory
    if [ ! -d "$SOURCE_DIR" ]; then
        log_error "Source directory not found: $SOURCE_DIR"
        exit 1
    fi

    # Create output and temp directories
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$TEMP_DIR"

    # Initialize summaries file if it doesn't exist
    if [ ! -f "$SUMMARIES_FILE" ]; then
        echo "{}" > "$SUMMARIES_FILE"
    fi

    log_success "Environment validated"
}

# ============================================================================
# Get document list for wave
# ============================================================================

get_wave_documents() {
    local wave=$1
    local all_docs

    # Get all markdown files (excluding special files)
    all_docs=$(cd "$SOURCE_DIR" && ls -1 *.md | grep -v -E '(repomix-markdown-only|README|FF7_GameEngine_MERGED)' | sort)

    # Calculate start and end indices for this wave
    local start_idx=$(( (wave - 1) * WAVE_SIZE ))
    local end_idx=$(( start_idx + WAVE_SIZE ))

    # Extract docs for this wave
    echo "$all_docs" | sed -n "$((start_idx + 1)),$((end_idx))p"
}

# ============================================================================
# Generate comprehensive agent prompt
# ============================================================================

generate_agent_prompt() {
    local filename=$1
    local module=$2
    local prompt_file="$TEMP_DIR/${filename%.md}_prompt.txt"

    log_info "Generating prompt for $filename..."

    # Read context data
    local headings_json=$(cat "$CONTEXT_DIR/headings_index.json")
    local categories_json=$(cat "$CONTEXT_DIR/document_categories.json")
    local images_json=$(cat "$CONTEXT_DIR/image_inventory.json")

    # Create the comprehensive prompt
    cat > "$prompt_file" <<'PROMPT_END'
# FF7 Documentation Standardization Agent - Comprehensive Instructions

You are a technical documentation standardization specialist transforming Final Fantasy VII game engine documentation for modern GitHub rendering and LLM navigation.

---

## PROJECT CONTEXT

### Why This Matters
This documentation represents years of reverse-engineering work by the FF7 modding community. It needs to be:
1. **GitHub-friendly**: Standard markdown that renders correctly without special tools
2. **LLM-navigable**: Structured metadata so LLMs can route to relevant sections
3. **Human-readable**: Clean hierarchy and cross-references
4. **Historically preserved**: All original metadata and merge history retained

### Current Problems
- 4 different metadata formats (inconsistent)
- 15+ files skip heading levels (H1→H4 instead of H1→H2→H3→H4)
- Wiki-style links don't work on GitHub
- Image paths use 3 different formats
- No LLM-specific context for routing

### Your Mission
Transform ONE document to meet all standardization requirements while preserving 100% technical accuracy.

---

## INPUT DOCUMENT

**File**: FILENAME_PLACEHOLDER
**Source**: `SOURCE_DIR_PLACEHOLDER/FILENAME_PLACEHOLDER`
**Module**: MODULE_PLACEHOLDER

---

## TRANSFORMATION REQUIREMENTS

### ✅ REQUIREMENT 1: Add YAML Frontmatter

Place at the very top of the document:

```yaml
---
title: "[Exact H1 title from document]"
module: "MODULE_PLACEHOLDER"
created: "[YYYY-MM-DD HH:MM JST from existing metadata, or use current date]"
modified: "2025-12-01 21:20 JST"
session_id: "887a1b3f-e34c-44f4-8434-e7e55610b603"
author: "Generated by Claude Code Documentation Standardization Agent"
status: "Complete"

# LLM-specific metadata (CRITICAL for routing)
llm_summary: "[1-2 sentences: What this covers + when LLM should read this]"
llm_tags: ["tag1", "tag2", "tag3"]  # 3-6 tags, lowercase-hyphenated
llm_primary_topics: ["Topic 1", "Topic 2", "Topic 3"]  # 3-5 concrete topics
llm_related_docs: ["file1.md", "file2.md"]  # Related documents

# Backlinks (leave empty - populated in pass 2)
referenced_by: []
---
```

**LLM Summary Guidelines**:
- Sentence 1: What technical content this document covers
- Sentence 2: When would an LLM need to consult this?
- Example: "Specifies PSX TIM texture format including color modes and CLUT structure. LLMs should read this when analyzing texture loading code or debugging color rendering issues."

**LLM Tags**: lowercase, hyphen-separated: `["psx", "texture", "tim-format", "color-depth"]`
**LLM Topics**: Concrete nouns: `["TIM file structure", "CLUT color tables", "Texture memory layout"]`

---

### ✅ REQUIREMENT 2: Add HTML Comment Metadata Block

Place immediately after YAML frontmatter (before H1 title):

```html
<!--
STANDARDIZATION METADATA
Original: [original filename]
Source: merged_with_pdf_content/FILENAME_PLACEHOLDER
Standardized: 2025-12-01 21:20 JST
Session-ID: 887a1b3f-e34c-44f4-8434-e7e55610b603
Agent: FF7 Documentation Standardization Agent v1.0

Previous Merge Metadata:
[Preserve entire existing HTML comment block content here]
[If no previous metadata: "None - original documentation"]

Standardization Changes Applied:
- [List ALL changes made - be specific]
- Example: "Added YAML frontmatter with LLM routing metadata"
- Example: "Fixed heading hierarchy: H1→H4 corrected to H1→H2→H3→H4"
- Example: "Converted 5 wiki-style links to standard markdown"
- Example: "Standardized 2 image paths to ../images/ format"

LLM CONTEXT BLOCK (Read this first for routing decisions):
[2-3 sentence prose summary for LLM readers explaining what this document covers,
key technical concepts, relevant use cases, and cross-references to related docs]
-->
```

---

### ✅ REQUIREMENT 3: Fix Heading Hierarchy

**Rule**: Strict H1→H2→H3→H4 progression (NO SKIPS)

```markdown
# Document Title (H1) - Exactly ONE per document
## Major Section (H2)
### Subsection (H3)
#### Detail (H4)
##### Fine Detail (H5) - Only for docs >3000 lines
```

**Common Fix Pattern**:
```markdown
❌ BEFORE (skips H2, H3):
# FF7 LZSS Format
#### Compression Algorithm

✅ AFTER (correct):
# FF7 LZSS Format
## Format Specification
### Compression Algorithm
```

**Special Cases**:
- Remove bold from H1: `# **Title**` → `# Title`
- Insert parent headings semantically (don't just write "Sections")
- Document all changes in metadata block

---

### ✅ REQUIREMENT 4: Convert Links to Hybrid Format

**Quick References** (wikilinks):
```markdown
See [[Memory Management]] for details.
The [[Kernel]] module handles this.
```

**Cross-Document Links** (standard markdown):
```markdown
For memory allocation, see [Memory Management](FF7_Kernel_Memory_management.md#ram-management).

Related documentation:
- [Field Module](FF7_Field_Module.md) - Field-specific memory
- [Battle Module](FF7_Battle_Battle_Mechanics.md) - Battle constraints
```

**Converting Wiki-Style Links**:
```markdown
❌ [text](FF7/Kernel/Overview#anchor "title"){.wikilink}
✅ [text](FF7_Kernel_Overview.md#anchor)

Pattern: Replace / with _, remove special chars, append .md
```

**External Links** (preserve unchanged):
```markdown
[Qhimm Forums](https://forums.qhimm.com/)
```

---

### ✅ REQUIREMENT 5: Standardize Image Paths

**Standard Format** (use for ALL images):
```markdown
![Descriptive alt text](../images/filename.png)
```

**Rules**:
- Path is always `../images/` (relative to final/ directory)
- Alt text is required and descriptive (5-15 words)
- Verify filename exists in image inventory
- ✅ "Engine architecture showing six interconnected modules"
- ❌ "" (empty - never acceptable)

---

### ✅ REQUIREMENT 6: Quality Checks

**Code Blocks Must Have Language Tags**:
```markdown
❌ ```
typedef struct { ... }
```

✅ ```c
typedef struct { ... }
```
```

**Common languages**: `c`, `cpp`, `python`, `bash`, `json`, `yaml`, `text`

**Other Checks**:
- Prefer Markdown tables over HTML `<table>` when possible
- Preserve complex HTML tables if needed
- Fix known typos flagged in metadata
- Ensure all headings can be linked with standard anchors

---

## COMPLETE HEADING REFERENCE (All 37 Documents)

**Use this to write accurate cross-references:**

HEADINGS_JSON_PLACEHOLDER

---

## OUTPUT REQUIREMENTS

### 1. Transformed Document File

**Write to**: `OUTPUT_DIR_PLACEHOLDER/FILENAME_PLACEHOLDER`

**Structure**:
```
[YAML frontmatter]
---

[HTML comment metadata block]

# [Document Title - H1]

[Document content with all transformations applied]
```

**Preservation Rules**:
- Preserve ALL technical content (no deletion)
- Preserve author's voice and phrasing
- Preserve code blocks, tables, lists exactly
- Only modify: metadata, headings, links, images

### 2. Agent Summary Report

**Print this JSON to stdout** (I will collect it):

```json
{
  "filename": "FILENAME_PLACEHOLDER",
  "module": "MODULE_PLACEHOLDER",
  "line_count": 0,
  "original_line_count": 0,
  "llm_summary": "[Your LLM summary from frontmatter]",
  "primary_topics": ["topic1", "topic2", "topic3"],
  "heading_changes": "[Description of ALL heading modifications]",
  "outbound_links": [
    {
      "target": "filename.md",
      "anchor": "section-name",
      "text": "link text",
      "line_number": 0
    }
  ],
  "images_count": 0,
  "images_updated": ["../images/file1.png"],
  "wiki_links_converted": 0,
  "tables_count": 0,
  "code_blocks_count": 0,
  "issues_found": [],
  "processing_notes": "[Free-form notes about transformation]"
}
```

---

## FINAL CHECKLIST

Before completing, verify:

- [ ] YAML frontmatter complete with all required fields
- [ ] HTML metadata block preserves original + documents changes
- [ ] LLM summary is 1-2 sentences, concrete and actionable
- [ ] Heading hierarchy is H1→H2→H3→H4 (no skips)
- [ ] All cross-document links use standard markdown
- [ ] All images use `../images/` path with descriptive alt text
- [ ] All code blocks have language tags
- [ ] All technical content preserved exactly
- [ ] Agent summary report JSON is complete

---

**Your task**: Transform FILENAME_PLACEHOLDER following ALL requirements above. Preserve 100% technical accuracy while standardizing format for GitHub and LLM navigation.

PROMPT_END

    # Replace simple placeholders
    sed -i '' "s|FILENAME_PLACEHOLDER|$filename|g" "$prompt_file"
    sed -i '' "s|MODULE_PLACEHOLDER|$module|g" "$prompt_file"
    sed -i '' "s|SOURCE_DIR_PLACEHOLDER|$SOURCE_DIR|g" "$prompt_file"
    sed -i '' "s|OUTPUT_DIR_PLACEHOLDER|$OUTPUT_DIR|g" "$prompt_file"

    # Replace HEADINGS_JSON_PLACEHOLDER with actual JSON using Python
    # (sed can't handle multi-line replacements easily)
    python3 - <<EOF
import json
import sys

# Read the prompt file
with open("$prompt_file", "r") as f:
    content = f.read()

# Read and format the headings JSON
with open("$CONTEXT_DIR/headings_index.json", "r") as f:
    headings = json.load(f)

# Format JSON with indentation
headings_formatted = json.dumps(headings, indent=2, ensure_ascii=False)
# Indent all lines by 4 spaces
headings_formatted = '\n'.join('    ' + line for line in headings_formatted.split('\n'))

# Replace placeholder
content = content.replace("HEADINGS_JSON_PLACEHOLDER", headings_formatted)

# Write back
with open("$prompt_file", "w") as f:
    f.write(content)
EOF

    echo "$prompt_file"
}

# ============================================================================
# Launch agent for single document
# ============================================================================

launch_agent() {
    local filename=$1
    local module=$2
    local prompt_file=$3

    log_info "Launching agent for $filename (module: $module)..."

    # Create output file path
    local output_file="$OUTPUT_DIR/$filename"
    local json_output_file="$TEMP_DIR/${filename%.md}_output.json"

    # Launch Claude Code in headless mode
    # CRITICAL: Redirect stdin to /dev/null to prevent claude from consuming
    # the while loop's input (which would cause only 1 doc to be processed)
    if claude -p "Transform $filename according to the comprehensive instructions provided." \
        --system-prompt-file "$prompt_file" \
        --output-format json \
        --model opus \
        --allowedTools "Read,Write,Edit,Grep,Glob" \
        --permission-mode acceptEdits \
        < /dev/null \
        > "$json_output_file" 2>&1; then

        log_success "Agent completed successfully for $filename"

        # Extract summary from agent response
        # The agent should have printed JSON summary to its final output
        local summary=$(cat "$json_output_file" | jq -r '.result' 2>/dev/null || echo "{}")

        # Verify output file was created
        if [ -f "$output_file" ]; then
            log_success "Output file created: $output_file"
            local line_count=$(wc -l < "$output_file")
            log_info "  Lines: $line_count"
        else
            log_warning "Output file not found: $output_file"
        fi

        # Add summary to collection
        add_to_summaries "$filename" "$summary"

        return 0
    else
        log_error "Agent failed for $filename"
        log_error "See output: $json_output_file"
        return 1
    fi
}

# ============================================================================
# Add summary to collection
# ============================================================================

add_to_summaries() {
    local filename=$1
    local summary=$2

    # Read current summaries
    local current=$(cat "$SUMMARIES_FILE")

    # Add new summary (using jq to merge)
    echo "$current" | jq --arg key "$filename" --argjson value "$summary" \
        '. + {($key): $value}' > "$SUMMARIES_FILE.tmp"

    mv "$SUMMARIES_FILE.tmp" "$SUMMARIES_FILE"
}

# ============================================================================
# Process wave
# ============================================================================

process_wave() {
    local wave=$1

    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  WAVE $wave - Processing Documents"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""

    # Get documents for this wave
    local docs=$(get_wave_documents "$wave")
    local doc_count=$(echo "$docs" | wc -l | tr -d ' ')

    if [ -z "$docs" ]; then
        log_warning "No documents found for wave $wave"
        return 0
    fi

    log_info "Processing $doc_count documents in wave $wave"
    echo ""

    local success_count=0
    local fail_count=0

    # Read categories JSON once
    local categories_json=$(cat "$CONTEXT_DIR/document_categories.json")

    # Process each document
    while IFS= read -r filename; do
        if [ -z "$filename" ]; then
            continue
        fi

        echo ""
        echo "────────────────────────────────────────────────────────────────"
        log_info "Document: $filename"
        echo "────────────────────────────────────────────────────────────────"

        # Get module for this document
        local module=$(echo "$categories_json" | jq -r --arg key "$filename" '.[$key]')

        # Generate prompt
        local prompt_file=$(generate_agent_prompt "$filename" "$module")

        # Launch agent
        if launch_agent "$filename" "$module" "$prompt_file"; then
            ((success_count++))
        else
            ((fail_count++))
        fi

        # Brief pause between agents
        sleep 2
    done <<< "$docs"

    # Wave summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  WAVE $wave - COMPLETE"
    echo "════════════════════════════════════════════════════════════════════"
    log_success "Successful: $success_count documents"
    if [ $fail_count -gt 0 ]; then
        log_error "Failed: $fail_count documents"
    fi
    echo ""

    # Checkpoint prompt - return 0 to continue, 1 to stop
    if [ "$SKIP_CHECKPOINTS" = true ]; then
        # Auto-continue mode - no prompts
        if [ $fail_count -gt 0 ]; then
            log_warning "Failures detected, but auto-continuing (--skip-checkpoints mode)"
        else
            log_success "Wave $wave completed successfully! Auto-continuing to next wave..."
        fi
        sleep 1
        return 0
    fi

    # Manual checkpoint mode
    if [ $fail_count -gt 0 ]; then
        log_warning "Failures detected. Review outputs before continuing."
        read -p "Continue to next wave? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Stopping at checkpoint."
            return 1
        fi
    else
        log_success "Wave $wave completed successfully!"
        if [ "$wave" -lt 8 ]; then
            read -p "Continue to wave $((wave + 1))? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Stopping at checkpoint."
                return 1
            fi
        fi
    fi

    return 0
}

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  FF7 Documentation Standardization - Agent Launcher"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""

    validate_environment

    # Determine waves to process
    if [ "$WAVE_NUMBER" = "all" ]; then
        log_info "Processing ALL waves (1-8)"
        for wave in {1..8}; do
            if ! process_wave "$wave"; then
                log_info "Stopping at user request."
                break
            fi
        done
    else
        if [[ ! "$WAVE_NUMBER" =~ ^[1-8]$ ]]; then
            log_error "Invalid wave number. Must be 1-8 or 'all'"
            exit 1
        fi

        # Process starting wave, then continue to subsequent waves if user wants
        current_wave="$WAVE_NUMBER"
        while [ "$current_wave" -le 8 ]; do
            if ! process_wave "$current_wave"; then
                log_info "Stopping at user request."
                break
            fi
            ((current_wave++))
        done
    fi

    # Final summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  STANDARDIZATION COMPLETE"
    echo "════════════════════════════════════════════════════════════════════"
    log_success "All agent summaries saved to: $SUMMARIES_FILE"
    log_success "Transformed documents in: $OUTPUT_DIR"
    echo ""
}

main "$@"
