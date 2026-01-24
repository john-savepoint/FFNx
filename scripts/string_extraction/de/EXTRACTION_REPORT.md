# German FF7 String Extraction - Final Report

**Date:** 2025-12-05 19:45 JST
**Executable:** ff7_de.exe
**Location:** /mnt/d/Games/Stand-alone/FINAL FANTASY VII/

## Data Section Information

From `objdump -h`:
- **File Offset:** 0x3B9A00
- **Size:** 0x1E3C00 (1,973,248 bytes)
- **VMA:** 0x7BA000

## Extraction Results

**Total Strings Extracted:** 39,197

**Output Files:**
- `strings_de.csv` (all extracted strings)
- `verification_de.txt` (verification report)

## Encoding Verification

German FF7 uses shifted ASCII encoding (identical to English):
- **Uppercase A-Z:** 0x21-0x3A
- **Lowercase a-z:** 0x41-0x5A
- **Numbers 0-9:** 0x10-0x19
- **Space:** 0x00
- **Period:** 0x0E
- **Terminator:** 0xFF

## Verified Menu Strings

| String      | Offset     | Byte Pattern                          |
|-------------|------------|---------------------------------------|
| Materia     | 0x590C83   | `2D 41 54 45 52 49 41 FF`            |
| Limit       | 0x590CD2   | `2C 49 4D 49 54 FF`                  |
| Konfig      | 0x590CE6   | `2B 4F 4E 46 49 47 FF`               |
| Speichern   | 0x590D0C   | `33 50 45 49 43 48 45 52 4E FF`      |
| Tauschen    | 0x5973FF   | `34 41 55 53 43 48 45 4E FF`         |

## Sample Game Strings

### Element/Status Names (found @ 0x596xxx)
- **Hitze** (Fire/Heat)
- **Gewitter** (Thunder)
- **Erde** (Earth)
- **Gift** (Poison)
- **Schwerkraft** (Gravity)
- **Wasser** (Water)
- **Wind** (Wind)
- **Heilig** (Holy)
- **Tod** (Death)
- **Gefahr** (Danger)
- **Schlaf** (Sleep)
- **Trauer** (Sadness)
- **Zorn** (Fury)
- **Psycho** (Confusion)
- **Schweigen** (Silence)
- **Hast** (Haste)
- **Gemach** (Slow)
- **Stop** (Stop)
- **Frosch** (Frog)

### Item Names
- **Wertvolle Uhr** (Precious Watch)
- **Antarkt. Wind** (Antarctic Wind)
- **Gegenangriff** (Counterattack)

### Character Names
- **HELENE** (Aerith's German name)

## Extended Characters

Analysis found many undecoded byte values (0x01-0xFE) with high occurrence:
- **0xFE:** 14,976 occurrences
- **0xFD:** 11,858 occurrences
- **0xFC:** 7,826 occurrences
- **0xFB:** 5,167 occurrences

These are likely:
- Control codes for text formatting
- Extended character mappings (German umlauts: ä, ö, ü, ß, Ä, Ö, Ü)
- Special game symbols

**Recommendation:**
To identify German umlaut mappings, manually search in-game strings for words known to contain umlauts and cross-reference with byte values.

## Verification Status

- ✅ **Spot Check:** PASSED (5/5 random strings verified in binary)
- ✅ **Encoding:** Confirmed shifted ASCII
- ✅ **Menu Strings:** 5 verified German menu terms found
- ✅ **Game Content:** Element names, item names, character names confirmed

## Next Steps

1. Add German umlaut character mappings when identified
2. Update `KNOWN_STRINGS` in `extract_de.py` with verified menu terms
3. Cross-reference with English extraction for address mapping
4. Identify control codes used for formatting/colors

---

**Script:** `/home/johnzealanddoyle/projects/ff7OG_japanese/scripts/string_extraction/de/extract_de.py`
