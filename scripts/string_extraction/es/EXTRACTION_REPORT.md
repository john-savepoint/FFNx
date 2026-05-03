# Spanish FF7 String Extraction Report
**Date:** 2025-12-05 13:30 JST
**Session:** c245e7c0-ec73-4933-b925-5976860e742c
**Language:** Spanish (es)
**Executable:** ff7_es.exe

## Extraction Summary

- **Total strings extracted:** 39,157
- **Data section offset:** 0x3BA000
- **Data section size:** 0x1E4800 (1.89 MB)
- **Data section VMA:** 0x7BB000
- **Spot check:** PASSED (5/5)

## Encoding

Spanish FF7 uses **shifted ASCII encoding** (same as English):
- Character encoding: `byte_value + 0x20 = ASCII`
- Uppercase A-Z: bytes 0x21-0x3A
- Lowercase a-z: bytes 0x41-0x5A
- Numbers 0-9: bytes 0x10-0x19
- Space: 0x00

## Verified Menu Strings

| Spanish Text | Offset | Virtual Address | Bytes | Translation |
|--------------|--------|-----------------|-------|-------------|
| Elemento | 0x591590 | 0xD92590 | 25 4C 45 4D 45 4E 54 4F | Element/Item |
| Magia | 0x591599 | 0xD92599 | 2D 41 47 49 41 | Magic |
| Equipo | 0x5915C0 | 0xD925C0 | 25 51 55 49 50 4F | Equipment |
| Config | 0x59160F | 0xD9260F | 23 4F 4E 46 49 47 | Config |
| Guardar | 0x591634 | 0xD92634 | 27 55 41 52 44 41 52 | Save |
| Salir | 0x59164C | 0xD9264C | 33 41 4C 49 52 | Exit |
| Seleccionar | 0x5912AF | 0xD922AF | 33 45 4C 45 43 43 49 4F 4E 41 52 | Select |
| Cancelar | 0x5912FC | 0xD922FC | 23 41 4E 43 45 4C 41 52 | Cancel |
| Ayuda | 0x591380 | 0xD92380 | 21 59 55 44 41 | Help |
| Pausa | 0x59148E | 0xD9248E | 30 41 55 53 41 | Pause |

## Sample Item Names

| Spanish Text | Bytes |
|--------------|-------|
| Contraataque | 23 4F 4E 54 52 41 41 54 41 51 55 45 |
| Reloj precioso | 32 45 4C 4F 4A 00 50 52 45 43 49 4F 53 4F |
| Cascabel | 23 41 53 43 41 42 45 4C |
| Elixir | 25 4C 49 58 49 52 |
| Megaelixir | 2D 45 47 41 45 4C 49 58 49 52 |
| Hiper | 28 49 50 45 52 |

## Extended Characters

Spanish-specific characters identified:
- **0x77 = ó** - Confirmed in "bot[77]n" → "botón" (button)
- **0x7C = ú** - Confirmed in "Men[7C]" → "Menú" (menu) and "m[7C]sica" → "música" (music)
- **0xB2, 0xB3** - UI markers for button indicators in instructions (e.g., "[B2]START[B3]")

**Still to identify:**
- á (a with accent)
- é (e with accent)
- í (i with accent)
- ñ (n with tilde)
- ü (u with diaeresis)
- ¿ (inverted question mark)
- ¡ (inverted exclamation mark)

## Next Steps

1. Identify byte mappings for Spanish extended characters:
   - á, é, í, ó, ú, ñ, ü, ¿, ¡
2. Update decode map with extended character mappings
3. Add verified strings to KNOWN_STRINGS for regression testing
4. Cross-reference with English extraction to identify common patterns

## Files Generated

- `strings_es.csv` - Full extraction (39,157 strings)
- `verification_es.txt` - Verification and spot check report
- `sample_strings_es.txt` - First 50 strings for manual review
- `extract_es.py` - Extraction script (configured for Spanish exe)
