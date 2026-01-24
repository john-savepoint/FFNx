#!/bin/bash
#
# Check V2 Cleanup Status - Resume Helper
#

PROJECT_ROOT="/Volumes/DevSSD/01_Development/Projects/experiments/ff70G-japanese-mod"
SOURCE_DIR="$PROJECT_ROOT/docs/reference/game_engine/final"
OUTPUT_DIR="$PROJECT_ROOT/docs/reference/game_engine/final v2"

echo "════════════════════════════════════════════════════════════════════"
echo "  V2 Cleanup Status"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Count source and output files
source_count=$(cd "$SOURCE_DIR" && ls -1 *.md 2>/dev/null | wc -l | tr -d ' ')
output_count=$(cd "$OUTPUT_DIR" && ls -1 *.md 2>/dev/null | wc -l | tr -d ' ')
remaining=$((source_count - output_count))

echo "Total documents: $source_count"
echo "Completed: $output_count"
echo "Remaining: $remaining"
echo ""

if [ $remaining -gt 0 ]; then
    echo "Documents still to process:"
    cd "$SOURCE_DIR"
    for file in *.md; do
        if [ ! -f "$OUTPUT_DIR/$file" ]; then
            echo "  - $file"
        fi
    done
    echo ""
    echo "To resume: ./scripts/cleanup_v2_parallel.sh 6"
else
    echo "✓ All documents completed!"
fi
