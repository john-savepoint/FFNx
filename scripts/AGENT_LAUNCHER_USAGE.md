# FF7 Documentation Standardization - Agent Launcher Usage Guide

**Created**: 2025-12-01 21:25 JST
**Session**: 887a1b3f-e34c-44f4-8434-e7e55610b603

---

## Overview

The `launch_standardization_agents.sh` script automates the standardization of all 37 FF7 game engine documentation files using Claude Code's headless mode. It processes documents in waves of 5, with checkpoints between each wave for quality review.

## Prerequisites

1. **Claude Code CLI** installed and available in PATH
2. **Context data** generated (run `extract_doc_context.py` first)
3. **Bash 4.0+** with standard Unix utilities (`jq`, `sed`, `python3`)

## Quick Start

### 1. Run Pre-Processing (First Time Only)

```bash
# Extract context data from all documentation
python3 scripts/extract_doc_context.py \
  --source docs/reference/game_engine/markdown/merged_with_pdf_content \
  --output .claude/data/ff7-docs-context \
  --images docs/reference/game_engine/images
```

**Output**: Creates JSON files in `.claude/data/ff7-docs-context/`:
- `headings_index.json` - All H1-H4 headings from 37 documents
- `links_index.json` - All forward links
- `document_categories.json` - Module assignments
- `image_inventory.json` - Image validation data

### 2. Run Wave 1 (Recommended First Run)

```bash
# Process first 5 documents (Wave 1)
./scripts/launch_standardization_agents.sh 1
```

**What happens**:
1. Validates environment and context data
2. Generates comprehensive prompts for 5 documents
3. Launches Claude Code agents in headless mode (Opus model)
4. Collects agent summary reports
5. Prompts for checkpoint review before continuing

### 3. Review Wave 1 Output

Check the transformed documents in `docs/reference/game_engine/final/`:

```bash
# List generated files
ls -lh docs/reference/game_engine/final/

# Spot-check one file
head -100 docs/reference/game_engine/final/FF7_History.md

# Verify YAML frontmatter parsed correctly
python3 -c "import yaml; print(yaml.safe_load(open('docs/reference/game_engine/final/FF7_History.md').read().split('---')[1]))"
```

### 4. Continue Remaining Waves

If Wave 1 looks good, continue with subsequent waves:

```bash
# Wave 2 (documents 6-10)
./scripts/launch_standardization_agents.sh 2

# Wave 3 (documents 11-15)
./scripts/launch_standardization_agents.sh 3

# ... and so on through Wave 8
```

**Or run all waves automatically**:

```bash
# Process all 37 documents across 8 waves
# (Still prompts at checkpoints if errors occur)
./scripts/launch_standardization_agents.sh all
```

---

## Usage Options

### Basic Syntax

```bash
./launch_standardization_agents.sh [wave_number]
```

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `1-8` | Process specific wave (5 docs each) | `./launch_standardization_agents.sh 3` |
| `all` | Process all waves sequentially | `./launch_standardization_agents.sh all` |
| *(empty)* | Defaults to Wave 1 | `./launch_standardization_agents.sh` |

### Wave Breakdown

| Wave | Documents | Files |
|------|-----------|-------|
| 1 | 1-5 | FF7.md, FF7_Battle_Battle_Animation_PC.md, FF7_Battle_Battle_Field.md, FF7_Battle_Battle_Mechanics.md, FF7_Battle_Battle_Scenes.md |
| 2 | 6-10 | FF7_Battle_Battle_Scenes_Battle_Script.md, FF7_Battle_Damage_Formulas.md, FF7_Chocobo_Breeding.md, FF7_Engine_basics.md, FF7_Field_Module.md |
| 3 | 11-15 | FF7_History.md, FF7_Item_Materia_Reference.md, FF7_Kernel.md, FF7_Kernel_Kernelbin.md, FF7_Kernel_Low_level_libraries.md |
| 4 | 16-20 | FF7_Kernel_Memory_management.md, FF7_Kernel_Overview.md, FF7_LGP_format.md, FF7_LZSS_format.md, FF7_Menu_Module.md |
| 5 | 21-25 | FF7_PSX_Sound.md, FF7_PSX_Sound_AKAO_frames.md, FF7_PSX_Sound_INSTRxALL.md, FF7_PSX_Sound_INSTRxDAT.md, FF7_PSX_Sound_Overview.md |
| 6 | 26-30 | FF7_Playstation_Battle_Model_Format.md, FF7_Savemap.md, FF7_TEX_format.md, FF7_Technical.md, FF7_Technical_Customising.md |
| 7 | 31-35 | FF7_Technical_Source.md, FF7_WorldMap_Module.md, FF7_WorldMap_Module_Script.md, FF7_World_Map_BSZ.md, FF7_World_Map_Encounters.md |
| 8 | 36-37 | FF7_World_Map_TXZ.md, PSX_TIM_format.md |

---

## Script Behavior

### Automatic Actions

1. **Environment Validation**
   - Checks Claude Code CLI is available
   - Verifies context data exists
   - Creates output directories

2. **Prompt Generation**
   - Loads headings, categories, images from JSON
   - Generates comprehensive 600+ line prompt for each document
   - Embeds full heading reference from all 37 documents
   - Saves prompts to `.claude/tmp/agent-prompts/`

3. **Agent Execution**
   - Launches Claude Code in headless mode (`claude -p`)
   - Uses Opus model for highest accuracy
   - Allowed tools: Read, Write, Edit, Grep, Glob
   - Auto-accepts edits (`--permission-mode acceptEdits`)

4. **Output Collection**
   - Writes transformed documents to `final/`
   - Saves agent JSON responses to `.claude/tmp/agent-prompts/`
   - Appends summaries to `agent_summaries.json`

### Checkpoints

After each wave completes, the script:
- Shows success/failure count
- **If failures occurred**: Prompts whether to continue
- **If all succeeded**: Prompts to continue to next wave
- Allows you to stop and review before proceeding

**Example**:
```
════════════════════════════════════════════════════════════════════
  WAVE 1 - COMPLETE
════════════════════════════════════════════════════════════════════
✓ Successful: 5 documents
✓ Wave 1 completed successfully!
Continue to wave 2? (y/n)
```

### Error Handling

If an agent fails:
1. Error is logged to console
2. JSON output saved to `.claude/tmp/agent-prompts/<file>_output.json`
3. Wave summary shows failure count
4. Checkpoint prompts for review before continuing

---

## Output Files

### Transformed Documents

**Location**: `docs/reference/game_engine/final/`

**Structure** (each file):
```markdown
---
[YAML frontmatter with LLM metadata]
---

<!--
[HTML comment metadata block]
-->

# Document Title

[Standardized content]
```

### Agent Summaries

**Location**: `.claude/data/ff7-docs-context/agent_summaries.json`

**Format**:
```json
{
  "FF7_History.md": {
    "filename": "FF7_History.md",
    "module": "Historical",
    "line_count": 95,
    "llm_summary": "...",
    "primary_topics": ["...", "..."],
    "heading_changes": "...",
    "outbound_links": [...],
    "images_count": 0,
    "wiki_links_converted": 5,
    "issues_found": [],
    "processing_notes": "..."
  },
  "FF7_Engine_basics.md": {
    ...
  }
}
```

**Use this for**:
- Generating `FF7_COMPLETE_INDEX.md`
- Building backlinks
- Quality validation
- Statistics

### Temporary Files

**Location**: `.claude/tmp/agent-prompts/`

Contains:
- `<filename>_prompt.txt` - Generated comprehensive prompts
- `<filename>_output.json` - Raw Claude Code JSON responses

**Can be deleted after successful run** (or kept for debugging).

---

## Validation & QA

### After Each Wave

1. **Check file count**:
   ```bash
   ls docs/reference/game_engine/final/ | wc -l
   # Should match expected count for completed waves
   ```

2. **Validate YAML**:
   ```bash
   # Check all YAML frontmatter parses correctly
   for f in docs/reference/game_engine/final/*.md; do
       python3 -c "import yaml; yaml.safe_load(open('$f').read().split('---')[1])" || echo "YAML error: $f"
   done
   ```

3. **Spot-check quality**:
   ```bash
   # View one simple doc
   less docs/reference/game_engine/final/FF7_History.md

   # View one complex doc
   less docs/reference/game_engine/final/FF7_Savemap.md
   ```

4. **Check for heading skips**:
   ```bash
   # This should find no results (all heading hierarchies fixed)
   grep -n "^#\s" docs/reference/game_engine/final/*.md | grep -E "^.*:#### " | head -20
   ```

5. **Verify images**:
   ```bash
   # Extract all image references
   grep -oh '!\[.*\](../images/[^)]+)' docs/reference/game_engine/final/*.md | sort -u

   # Verify they all exist
   for img in $(grep -oh '../images/[^)]+' docs/reference/game_engine/final/*.md | sort -u); do
       [ -f "docs/reference/game_engine/$img" ] || echo "Missing: $img"
   done
   ```

---

## Troubleshooting

### "Claude Code CLI not found"

**Solution**: Install Claude Code or ensure it's in your PATH:
```bash
which claude
# Should show path to claude binary
```

### "Context files not found"

**Solution**: Run the pre-processing script first:
```bash
python3 scripts/extract_doc_context.py \
  --source docs/reference/game_engine/markdown/merged_with_pdf_content \
  --output .claude/data/ff7-docs-context \
  --images docs/reference/game_engine/images
```

### Agent Fails with Permission Error

**Check**: Verify output directory is writable:
```bash
ls -ld docs/reference/game_engine/final
# Should show: drwxr-xr-x
```

### Agent Produces Malformed Output

**Check**:
1. View the agent's JSON output: `.claude/tmp/agent-prompts/<file>_output.json`
2. Check for errors in the response
3. Re-run just that document:
   ```bash
   # Find which wave contains the problematic document
   # Re-run that wave
   ./scripts/launch_standardization_agents.sh <wave_number>
   ```

### JSON Parsing Errors in Summaries

**Check**: Ensure `jq` is installed:
```bash
which jq
# Install if missing: brew install jq
```

---

## Advanced Usage

### Custom Wave Size

Edit the script and change:
```bash
WAVE_SIZE=5  # Change to 10 for larger waves
```

### Run Single Document Manually

```bash
# Generate prompt for one file
filename="FF7_History.md"
module="Historical"

# Create prompt file
# (Simplified - use script's generate_agent_prompt function)

# Run agent
claude -p "Transform $filename" \
  --system-prompt-file prompt.txt \
  --output-format json \
  --model opus \
  --allowedTools "Read,Write,Edit,Grep,Glob" \
  --permission-mode acceptEdits
```

### Dry Run (Generate Prompts Only)

Comment out the `claude` invocation and just generate prompts:
```bash
# In launch_agent function, comment out claude command
# This will generate all prompts without executing
```

---

## Estimated Runtime

**Per document**:
- Prompt generation: ~1-2 seconds
- Agent execution: ~1-3 minutes (varies by document size)
- Total: ~2-4 minutes per document

**Per wave** (5 documents):
- ~10-20 minutes

**All 8 waves** (37 documents):
- ~2-4 hours (with checkpoints)

---

## Next Steps After Completion

Once all 37 documents are standardized:

1. **Generate backlinks**:
   ```bash
   python3 scripts/generate_backlinks.py \
     --summaries .claude/data/ff7-docs-context/agent_summaries.json \
     --target docs/reference/game_engine/final
   ```

2. **Generate complete index**:
   ```bash
   python3 scripts/generate_complete_index.py \
     --summaries .claude/data/ff7-docs-context/agent_summaries.json \
     --headings .claude/data/ff7-docs-context/headings_index.json \
     --output docs/reference/game_engine/final/FF7_COMPLETE_INDEX.md
   ```

3. **Update master TOC**:
   ```bash
   python3 scripts/update_master_toc.py \
     --source docs/reference/game_engine/markdown/merged_with_pdf_content/FF7.md \
     --output docs/reference/game_engine/final/FF7.md
   ```

4. **Final validation**:
   ```bash
   python3 scripts/validate_final_docs.py \
     --docs docs/reference/game_engine/final \
     --images docs/reference/game_engine/images
   ```

---

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review script output and error messages
3. Inspect `.claude/tmp/agent-prompts/<file>_output.json` for agent responses
4. Check logs in `.claude/logs/` if available

**Script location**: `scripts/launch_standardization_agents.sh`
**Context data**: `.claude/data/ff7-docs-context/`
**Output**: `docs/reference/game_engine/final/`
