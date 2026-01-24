#!/bin/bash
#
# FF7 Documentation V2 Cleanup - Parallel Processing with Opus
#
# Fixes corrupted characters, formatting errors, and enhances markdown using GNU Parallel
#
# Created: 2025-12-02 01:10 JST
# Session: 887a1b3f-e34c-44f4-8434-e7e55610b603
#
# Usage:
#   ./cleanup_v2_parallel.sh [jobs]
#
#   jobs: Number of parallel jobs (default: 5)
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="/Volumes/DevSSD/01_Development/Projects/experiments/ff70G-japanese-mod"
SOURCE_DIR="$PROJECT_ROOT/docs/reference/game_engine/final"
OUTPUT_DIR="$PROJECT_ROOT/docs/reference/game_engine/final v2"
PARALLEL_JOBS="${1:-5}"

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

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# ============================================================================
# Cleanup single document
# ============================================================================

cleanup_document() {
    local filename=$1
    local source_file="$SOURCE_DIR/$filename"
    local output_file="$OUTPUT_DIR/$filename"
    local temp_log="/tmp/cleanup_${filename%.md}.log"

    # RESUME SAFETY: Skip if already processed
    if [ -f "$output_file" ]; then
        local line_count=$(wc -l < "$output_file" | tr -d ' ')
        if [ "$line_count" -gt 10 ]; then
            log_info "$filename - already cleaned (skipping)"
            return 0
        else
            log_info "$filename - incomplete output detected, re-processing..."
        fi
    fi

    log_info "Cleaning $filename..."

    # Verify source file exists
    if [ ! -f "$source_file" ]; then
        log_error "$filename - source file not found"
        return 1
    fi

    # Create comprehensive cleanup prompt
    local cleanup_prompt="# Document Cleanup Task

You are a technical documentation cleanup specialist. Your task is to fix formatting and character encoding issues in this FF7 game engine documentation file while preserving all technical content.

## Critical Fixes Required

### 1. Corrupted Character Encoding
- Replace all \`ï¿½\` (replacement character U+FFFD) with correct characters
- Fix UTF-8 encoding errors
- Restore special characters that got corrupted during conversion

### 2. LaTeX Math Rendering Issues
Fix cases where markdown is being incorrectly interpreted as LaTeX:
- \`**Header** [at offset 0x00000000]\` - This should NOT render as math
- Remove backslash escapes that trigger math mode: \`\\[\` should be \`[\`
- Check all \`[...]\` patterns - only actual math expressions should use LaTeX

### 3. GitHub Markdown Enhancements
Use GitHub-flavored markdown features to improve readability:

**Alerts** (for important notes):
\`\`\`markdown
> [!NOTE]
> Useful information

> [!WARNING]
> Critical information

> [!IMPORTANT]
> Key information
\`\`\`

**Color in Tables** (for register/memory docs):
\`\`\`markdown
\`#FF0000\` - Red for warnings
\`#00FF00\` - Green for success
\`#0088FF\` - Blue for info
\`\`\`

**Task Lists** (for checklists):
\`\`\`markdown
- [ ] Incomplete task
- [x] Complete task
\`\`\`

**Better Code Blocks** (specify language):
\`\`\`c
// Always specify language
typedef struct { ... }
\`\`\`

**Better Tables** (use alignment):
\`\`\`markdown
| Left | Center | Right |
|:-----|:------:|------:|
| L    |   C    |     R |
\`\`\`

### 4. Formatting Improvements
- Fix broken tables (ensure proper column alignment)
- Fix inconsistent heading hierarchy
- Improve code block language tags
- Add descriptive alt text to images
- Fix broken links

## What NOT to Change
- ❌ Do NOT modify technical content (addresses, values, formulas)
- ❌ Do NOT change code examples (except language tags)
- ❌ Do NOT alter YAML frontmatter structure
- ❌ Do NOT change HTML metadata blocks
- ❌ Do NOT remove any information

## Output Requirements
- Write the cleaned document to the specified output path
- Preserve exact same filename
- Maintain all frontmatter and metadata
- Keep all technical accuracy

Read the source document, apply all fixes, and write the cleaned version."

    # Run Claude Code with Opus model in headless mode
    # Redirect output to temp log for debugging if needed
    if timeout 600 claude -p "Clean document: $source_file

Output to: $output_file

$cleanup_prompt" \
        --model opus \
        --output-format json \
        --allowedTools "Read,Write,Edit" \
        --permission-mode acceptEdits \
        < /dev/null \
        > "$temp_log" 2>&1; then

        # Verify output file was actually created
        if [ -f "$output_file" ]; then
            local line_count=$(wc -l < "$output_file" | tr -d ' ')
            if [ "$line_count" -gt 10 ]; then
                log_success "$filename cleaned ($line_count lines)"
                rm -f "$temp_log"  # Clean up temp log on success
                return 0
            else
                log_error "$filename - output too short ($line_count lines)"
                return 1
            fi
        else
            log_error "$filename - output file not created"
            return 1
        fi
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_error "$filename - timed out (>10 minutes)"
        else
            log_error "$filename - agent failed (exit code: $exit_code)"
        fi
        return 1
    fi
}

export -f cleanup_document
export -f log_info
export -f log_success
export -f log_error
export SOURCE_DIR OUTPUT_DIR RED GREEN YELLOW BLUE NC

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  FF7 Documentation V2 Cleanup - Parallel Processing"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""

    # Validate source directory
    if [ ! -d "$SOURCE_DIR" ]; then
        log_error "Source directory not found: $SOURCE_DIR"
        exit 1
    fi

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Get all markdown files
    local files
    files=$(cd "$SOURCE_DIR" && ls -1 *.md 2>/dev/null || true)

    if [ -z "$files" ]; then
        log_error "No markdown files found in $SOURCE_DIR"
        exit 1
    fi

    local file_count
    file_count=$(echo "$files" | wc -l | tr -d ' ')

    log_info "Found $file_count documents to clean"
    log_info "Using $PARALLEL_JOBS parallel jobs with Opus model"
    echo ""

    # Check if GNU Parallel is installed
    if ! command -v parallel &> /dev/null; then
        log_error "GNU Parallel not found. Install with: brew install parallel"
        exit 1
    fi

    # Process files in parallel (continue on error with --halt never)
    echo "$files" | parallel -j "$PARALLEL_JOBS" --halt never --bar cleanup_document {}

    # Count results
    local output_count=$(ls -1 "$OUTPUT_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    local failed_count=$((file_count - output_count))

    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  CLEANUP COMPLETE"
    echo "════════════════════════════════════════════════════════════════════"
    log_success "Successfully cleaned: $output_count of $file_count documents"
    if [ $failed_count -gt 0 ]; then
        log_error "Failed to clean: $failed_count documents"
        log_info "Check temp logs in /tmp/cleanup_*.log for details"
    fi
    log_success "Cleaned documents saved to: $OUTPUT_DIR"
    echo ""

    # Exit with error if any failures
    if [ $failed_count -gt 0 ]; then
        exit 1
    fi
}

main "$@"
