# String Extraction Agent Instructions

**Created:** 2025-12-05 12:35 JST
**Session-ID:** c245e7c0-ec73-4933-b925-5976860e742c

---

## Your Task

You are a sub-agent responsible for extracting strings from ONE FF7 language executable.

### Step 1: Copy the Base Script

Copy `shared/base_extractor.py` to your language directory:
- English agent → `en/extract_en.py`
- Japanese agent → `ja/extract_ja.py`
- Spanish agent → `es/extract_es.py`
- German agent → `de/extract_de.py`
- French agent → `fr/extract_fr.py`

### Step 2: Configure Your Script

Modify these variables at the top of YOUR copy:

```python
LANGUAGE = "XX"  # Your language code

EXE_PATH = "..."  # Full path to executable

DATA_SECTION_OFFSET = 0x...  # From objdump -h output
DATA_SECTION_SIZE = 0x...
DATA_SECTION_VMA = 0x...

KNOWN_STRINGS = [
    # Add 5-10 strings you KNOW exist in this executable
    # Format: ("decoded_text", "hex_bytes_with_spaces")
]
```

### Step 3: Get Section Info

Run `objdump -h /path/to/exe` and find the `.data` section:
- File off = DATA_SECTION_OFFSET
- Size = DATA_SECTION_SIZE
- VMA = DATA_SECTION_VMA

### Step 4: Add Known Strings for Verification

Before running, manually find 5-10 strings using xxd:

```bash
xxd /path/to/exe | grep -i "some pattern"
```

Add these to KNOWN_STRINGS so the script can verify it's working.

**For English, try finding:**
- CONFIG, ITEM, MAGIC, EQUIP, STATUS

**For Japanese, try finding:**
- アイテム (ITEM), まほう (MAGIC), コンフィグ (CONFIG)

**For European languages, try finding:**
- Menu items in that language (look at screenshots if available)

### Step 5: Run and Verify

```bash
cd /path/to/your/language/dir
python3 extract_XX.py
```

Check:
1. `strings_XX.csv` was created
2. `verification_XX.txt` shows passes
3. Spot check passed

### Step 6: Report Back

Your final report should include:
- Total strings found
- Verification results (all passes?)
- Any issues or anomalies
- Sample of interesting findings (menu strings, etc.)

---

## Executable Paths

| Language | Path |
|----------|------|
| English | `/mnt/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII/ff7_en.exe` |
| Japanese | `/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_ja.exe` |
| Spanish | `/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_es.exe` |
| German | `/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_de.exe` |
| French | `/mnt/d/Games/Stand-alone/FINAL FANTASY VII/ff7_fr.exe` |

---

## Section Info Reference

### English (Steam) - ff7_en.exe
```
.data  Size: 0x1E3000  VMA: 0x7BA000  File off: 0x3B8A00
```

### Japanese/European (Original) - ff7_ja/es/de/fr.exe
```
.data  Size: 0x1E4800  VMA: 0x7BB000  File off: 0x3BA000
```
(Verify with objdump - may vary slightly)

---

## Troubleshooting

**No strings found:**
- Check DATA_SECTION_OFFSET is correct
- Verify exe path exists and is readable

**All verification fails:**
- Check KNOWN_STRINGS byte patterns are correct
- FF7 encoding may differ - check decode map

**Spot check fails:**
- File offsets may be wrong - recalculate from objdump

**Decoding looks wrong:**
- European languages may need extended Latin chars in decode map
- Add missing characters to build_english_decode_map()
