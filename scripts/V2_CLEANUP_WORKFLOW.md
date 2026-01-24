# FF7 Documentation V2 Cleanup Workflow

**Created**: 2025-12-02 01:12 JST
**Session**: 887a1b3f-e34c-44f4-8434-e7e55610b603

---

## Overview

This workflow creates cleaned "V2" versions of all 37 FF7 game engine documentation files using:
- **Opus model** for highest quality cleanup
- **GNU Parallel** for simultaneous processing (5-6 docs at a time)
- **Claude Code headless mode** (`-p`) for automation

## Standardization Complete ✅

**Waves 1-8 processed**: 36 of 37 documents standardized
**Missing document**: FF7_Battle_Damage_Formulas.md (processing now)

**Results:**
- Wave 1: 5 docs ✅
- Wave 2: 4 docs ✅ (1 pending)
- Wave 3: 5 docs ✅
- Wave 4: 5 docs ✅
- Wave 5: 5 docs ✅
- Wave 6: 5 docs ✅
- Wave 7: 5 docs ✅
- Wave 8: 2 docs ✅

---

## V2 Cleanup Objectives

### 1. Fix Corrupted Characters
- Replace `ï¿½` (U+FFFD replacement character)
- Fix UTF-8 encoding errors
- Restore special characters lost in conversion

### 2. Fix LaTeX Rendering Issues
**Problem**: Markdown patterns incorrectly interpreted as LaTeX math

```markdown
# BEFORE (renders as math):
**Header** \[at offset 0x00000000\]

# AFTER (renders correctly):
**Header** [at offset 0x00000000]
```

### 3. GitHub Markdown Enhancements

**Alerts** (for important callouts):
```markdown
> [!NOTE]
> Useful information that users should know

> [!WARNING]
> Urgent information that requires immediate attention

> [!IMPORTANT]
> Key information users need to know to achieve their goal
```

**Color Specifications** (for tables/diagrams):
```markdown
`#FF0000` - Red (warnings, errors)
`#00FF00` - Green (success, valid)
`#0088FF` - Blue (information)
`#FFD700` - Gold (highlights)
```

**Task Lists** (for checklists):
```markdown
- [ ] Incomplete task
- [x] Completed task
```

**Better Code Blocks** (always specify language):
```c
// C code with syntax highlighting
typedef struct {
    uint8_t value;
} Example;
```

**Better Tables** (use column alignment):
```markdown
| Register | Address | Description |
|:---------|:-------:|:------------|
| PSR      | 0x0000  | Status Reg  |
```

---

## Parallel Processing Script

**Location**: `scripts/cleanup_v2_parallel.sh`

### Usage

```bash
# Process all documents with 5 parallel jobs (default)
./scripts/cleanup_v2_parallel.sh

# Process with 6 parallel jobs
./scripts/cleanup_v2_parallel.sh 6

# Monitor progress (shows progress bar)
# GNU Parallel will display real-time progress
```

### How It Works

1. **Reads all files** from `docs/reference/game_engine/final/`
2. **Launches parallel Claude Code instances** (5-6 at a time)
3. **Each instance**:
   - Uses `claude -p` (headless mode)
   - Specifies `--model opus` for highest quality
   - Loads comprehensive cleanup prompt
   - Reads source document
   - Applies all fixes
   - Writes to `final v2/` directory
4. **Progress tracking** via GNU Parallel's `--bar` flag

### Estimated Time

- **Per document**: 1-3 minutes (Opus processing time)
- **Total with 5 parallel jobs**: ~15-25 minutes
- **Total with 6 parallel jobs**: ~12-20 minutes

---

## Cleanup Prompt Details

The script uses a comprehensive system prompt that instructs Opus to:

### Critical Fixes
1. **Character Encoding**: Replace ï¿½ with correct characters
2. **LaTeX Math**: Fix `\[` `\]` patterns being interpreted as math
3. **Tables**: Ensure proper column alignment
4. **Code Blocks**: Add language tags
5. **Images**: Add descriptive alt text
6. **Links**: Fix broken cross-references

### Enhancements
1. **Alerts**: Use `> [!NOTE]`, `> [!WARNING]`, `> [!IMPORTANT]`
2. **Colors**: Specify colors in tables for clarity
3. **Task Lists**: Convert checklists to `- [ ]` format
4. **Table Alignment**: Use `:---`, `:---:`, `---:` for alignment
5. **Emojis**: Add sparingly for emphasis (only where appropriate)

### Preservation Rules
- ❌ **Do NOT** modify technical content (addresses, values, formulas)
- ❌ **Do NOT** change code examples (except language tags)
- ❌ **Do NOT** alter YAML frontmatter structure
- ❌ **Do NOT** change HTML metadata blocks
- ❌ **Do NOT** remove any information
- ✅ **Do** preserve 100% technical accuracy

---

## Output Structure

### Final V2 Directory

```
docs/reference/game_engine/final v2/
├── FF7_Battle_Battle_Animation_PC.md
├── FF7_Battle_Battle_Field.md
├── FF7_Battle_Battle_Mechanics.md
├── ... (all 37 documents)
└── PSX_TIM_format.md
```

### Each Document Structure

```markdown
---
[YAML frontmatter - unchanged]
---

<!--
[HTML metadata block - unchanged]
-->

# Document Title

[Enhanced content with:]
- Fixed character encoding
- Corrected LaTeX rendering
- GitHub markdown features
- Improved formatting
- All technical content preserved
```

---

## Quality Verification

After parallel processing completes, verify:

### 1. Character Encoding Check
```bash
# Search for remaining corrupted characters
grep -r "ï¿½" "docs/reference/game_engine/final v2/"
# Should return: no results

# Check for common encoding issues
grep -r "Ã" "docs/reference/game_engine/final v2/" | head -20
```

### 2. LaTeX Rendering Check
```bash
# Find patterns that might render as LaTeX
grep -r '\\\[' "docs/reference/game_engine/final v2/" | head -20
# Review each match - only actual math should have \[
```

### 3. Document Count
```bash
ls -1 "docs/reference/game_engine/final v2/"/*.md | wc -l
# Expected: 37
```

### 4. Spot Check Quality
```bash
# Compare before/after for a complex document
diff "docs/reference/game_engine/final/FF7_Savemap.md" \
     "docs/reference/game_engine/final v2/FF7_Savemap.md"
```

---

## Commit Strategy

### Commit 1: Standardized Documents
```bash
git add docs/reference/game_engine/final/
git commit -m "docs: complete standardization of 37 FF7 game engine documents

- Wave 1-8 processed with comprehensive standardization
- Added YAML frontmatter with LLM routing metadata
- Fixed heading hierarchy issues
- Converted wiki-style links to markdown
- Standardized image paths
- Added agent summaries for index generation

Total: 37 documents standardized
Session: 887a1b3f-e34c-44f4-8434-e7e55610b603

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Commit 2: V2 Cleaned Documents
```bash
git add "docs/reference/game_engine/final v2/"
git commit -m "docs: create v2 cleaned versions with Opus (character encoding + formatting)

Fixes:
- Replaced all ï¿½ corrupted characters
- Fixed LaTeX math rendering issues (\[ patterns)
- Enhanced with GitHub markdown features (alerts, colors, task lists)
- Improved table formatting and alignment
- Added code block language tags
- Fixed broken links and images

Processing:
- Opus model for highest quality
- GNU Parallel (5-6 docs at a time)
- Total processing time: ~15-25 minutes

Total: 37 documents cleaned
Session: 887a1b3f-e34c-44f4-8434-e7e55610b603

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Troubleshooting

### GNU Parallel Not Found
```bash
brew install parallel
```

### Script Permission Denied
```bash
chmod +x scripts/cleanup_v2_parallel.sh
```

### Opus Model Rate Limiting
If you hit rate limits, reduce parallel jobs:
```bash
./scripts/cleanup_v2_parallel.sh 3  # Use 3 instead of 5
```

### Cleanup Failed for Specific Document
Re-run manually:
```bash
claude -p "Clean document: docs/reference/game_engine/final/FF7_Savemap.md

Output to: docs/reference/game_engine/final v2/FF7_Savemap.md

[Full cleanup prompt here]" \
  --model opus \
  --output-format json \
  --allowedTools "Read,Write,Edit" \
  --permission-mode acceptEdits
```

---

## Next Steps After V2 Completion

1. **Verify Quality**: Run all verification checks above
2. **Spot Check**: Manually review 3-5 documents for quality
3. **Generate Backlinks**: Update cross-references in frontmatter
4. **Create Complete Index**: Generate `FF7_COMPLETE_INDEX.md`
5. **Update Master TOC**: Update main `FF7.md` with links to final v2
6. **Commit**: Create final commit with v2 cleaned documents

---

## Summary

**Standardization Phase** (Complete):
- 37 documents with YAML frontmatter, LLM metadata, fixed hierarchy
- Output: `docs/reference/game_engine/final/`

**V2 Cleanup Phase** (Ready to Execute):
- Character encoding fixes + GitHub markdown enhancements
- Opus model + GNU Parallel for quality + speed
- Output: `docs/reference/game_engine/final v2/`

**Total Documents**: 37
**Processing Method**: Automated with checkpoints
**Quality Level**: Opus-reviewed for accuracy
