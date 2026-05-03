# FF7 Japanese Text Rendering Fixes

**Created:** 2025-12-10 20:03 JST
**Last Modified:** 2025-12-10 20:03 JST
**Version:** 1.0.0
**Author:** John Zealand-Doyle
**Session-ID:** 0681f78b-0382-45ee-898b-5a32b7ce32d5

## Overview

This document describes fixes implemented to make FFNx's Japanese text rendering match the original Japanese PC release of Final Fantasy VII. Two issues were identified and resolved:

1. **Heart Symbol (❤) not rendering** - The heart character at position 217 (byte `0xD9`) was invisible
2. **Rainbow animation stopping prematurely** - Animated text would stop cycling colors mid-sentence

---

## Issue 1: Heart Symbol Not Rendering

### Symptoms

- In dialogue like `秘密❤　楽しみに待ってね❤`, the heart symbols were invisible
- A space appeared where the heart should be (indicating the character was being processed but not displayed)

### Root Cause Analysis

The heart character is encoded as direct byte `0xD9` (decimal 217) from jafont_1. Investigation revealed two problems:

1. **Width data was zero:** `charWidthData[0][217]` was set to `0`, making the character invisible
2. **Texture not loading from mod path:** FFNx's texture override system (`mods/Textures/menu/`) was not being used for jafont textures

### Technical Details

#### Heart Character Encoding

```
Field text byte sequence for "秘密❤":
FE DB FB 23 FD 3D D9 FE DB ...
      │       │   │
      │       │   └── D9 = Heart (jafont_1 position 217)
      │       └────── FD 3D = 密 (jafont_4)
      └────────────── FB 23 = 秘 (jafont_2)
```

**Important:** `FE D9` is a color code (white/reset). Plain `D9` without prefix is the heart character.

#### Texture Loading Path

jafont textures are loaded via `engine_load_graphics_object_6710AC` which reads from:
- **Direct path:** `direct/menu/jafont_X.tex` (TEX format files)
- **NOT** from `mods/Textures/menu/jafont_X.png` (the mod path texture override)

The TEX format has specific requirements:
- Header must match original format (see TEX Format section below)
- **Pixel data must be stored top-down** (row 0 = top of image)

#### Image2TEX Tool Issue

The Image2TEX tool stores pixels in BMP order (bottom-up), but FF7 expects top-down order. This causes:
- Characters appear upside down
- Characters appear at wrong positions
- Misaligned rendering

### Solution

#### Fix 1: Character Width

In `src/ff7/japanese_text.cpp`, line 336, change `charWidthData[0][217]` from `0` to `27`:

```cpp
// Line 336 - position 217 is the 10th value (index 9) in this row
28, 27, 27, 29, 30, 12, 25, 22, 11, 27, 27, 23, 23, 23, 12, 22,
//                                  ^^
//                                  Changed from 0 to 27
```

#### Fix 2: TEX File Preparation

When converting PNG to TEX for jafont textures:

1. **Vertically flip the image before conversion**, OR
2. **Post-process the TEX file** to flip pixel data

Python script to verify/fix TEX orientation:

```python
import struct

def flip_tex_pixels(filepath):
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())

    # Read dimensions from header
    width = struct.unpack_from('<I', data, 0x3C)[0]
    height = struct.unpack_from('<I', data, 0x40)[0]
    bpp = struct.unpack_from('<I', data, 0x68)[0]

    header_size = 0xEC
    row_size = width * bpp

    # Extract pixel data
    pixel_data = data[header_size:]

    # Flip rows
    flipped = bytearray()
    for row in range(height - 1, -1, -1):
        start = row * row_size
        flipped.extend(pixel_data[start:start + row_size])

    # Write back
    data[header_size:] = flipped

    with open(filepath, 'wb') as f:
        f.write(data)
```

---

## Issue 2: Rainbow Animation Stopping Prematurely

### Symptoms

- Text like `秘密❤　楽しみに待ってね❤` should have full rainbow animation
- Only `秘密❤` was animating; `楽しみに待ってね❤` was static white
- Original Japanese game showed full animation for both parts

### Root Cause Analysis

The control code `FE DB` toggles rainbow animation. The field data contains:

```
FE DB (ON) → 秘密 → D9 (heart) → FE DB → 楽しみに待ってね → D9 (heart) → FE DB (OFF)
```

FFNx implemented `FE DB` as a **toggle** (XOR operation):
```cpp
(*ff7_externals.word_DC3CC4) ^= 1u;  // Toggle: 0→1, 1→0
```

This meant the second `FE DB` turned rainbow **OFF**, leaving the rest of the text unanimated.

However, the **original Japanese game** treats `FE DB` as "turn ON" only - it doesn't toggle off mid-text.

### Solution

In `src/ff7/japanese_text.cpp`, line 586, change from XOR toggle to direct assignment:

```cpp
// BEFORE (toggle behavior - INCORRECT):
if ( *buffer_text == 0xDBu )
{
    // 0xDB: Toggle rainbow/cycle effect
    (*ff7_externals.word_DC3CC4) ^= 1u;
    ++buffer_text;
    continue;
}

// AFTER (set ON only - CORRECT for original JP behavior):
if ( *buffer_text == 0xDBu )
{
    // 0xDB: Turn ON rainbow/cycle effect (original JP behavior: does not toggle off mid-text)
    (*ff7_externals.word_DC3CC4) = 1;
    ++buffer_text;
    continue;
}
```

### Verification

Compare behavior against original Japanese PC release:
1. Load mds7_w2 field (Sector 7 area)
2. Trigger the dialogue containing `秘密❤　楽しみに待ってね❤`
3. Entire colored section should animate with rainbow cycling

---

## TEX Format Reference

The FF7 PC TEX format header (0xEC bytes):

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0x00 | 4 | Version | Must be 1 |
| 0x3C | 4 | Width | Image width in pixels |
| 0x40 | 4 | Height | Image height in pixels |
| 0x4C | 4 | PaletteFlag | 0=no palette, 1=paletted |
| 0x64 | 4 | BitsPerPixel | Usually 32 for jafont |
| 0x68 | 4 | BytesPerPixel | Usually 4 for jafont |
| 0xEC+ | - | Pixel Data | BGRA format, **top-down order** |

Key differences from Image2TEX output:
- `MinimumBitsPerColor` (0x14): Original=32, Image2TEX=8
- `MinimumBitsPerPixel` (0x24): Original=8, Image2TEX=32
- **Pixel order**: Original=top-down, Image2TEX=bottom-up (BMP order)

---

## File Locations

### Source Files Modified
- `src/ff7/japanese_text.cpp` - Character width data and rainbow toggle logic

### Game Data Files
- `direct/menu/jafont_1.tex` through `jafont_6.tex` - Japanese font textures
- `data/field/jfleve.lgp` - Japanese field dialogue (contains rainbow control codes)

### Tools
- Image2TEX - Converts images to TEX format (requires pixel flip for correct orientation)

---

## Issue 3: Button Placeholder Text

**Status:** Implemented - button labels now render correctly

### Symptoms

- Field dialogue shows button labels like `【Cキー】` in the original Japanese game
- FFNx showed garbage characters or missing text where button labels should appear
- Example dialogue: `「キャンセルボタン【Cキー】を押しながら...`

### Root Cause Analysis

Button labels in field dialogue are **dynamic placeholders**, not literal text. The encoding uses:

```
FD F0 - FD FF = Button placeholder codes
```

Where:
- `FD F0` = OK/Confirm button (決定 / Circle / Enter)
- `FD F1` = Cancel button (キャンセル / Cross / C key)
- `FD F2` = Menu button (メニュー / Triangle / V key)
- `FD F3` = Switch/Assist button (Square / X key)
- `FD F4` through `FD F9` = Shoulder/Select/Start buttons
- `FD FA` through `FD FF` = Directional/other buttons

Example field text encoding:

```
D7 FD F1 D8
│   │    │
│   │    └── D8 = 】 (right bracket)
│   └────── FD F1 = Button placeholder (Cancel)
└────────── D7 = 【 (left bracket)
```

FFNx was treating `FD F0-FF` as jafont_5 characters (indices 240-255), which are empty/undefined, causing garbage display.

### Solution

The implementation consists of three parts:

#### 1. Button Label Data Definitions

At the top of `src/ff7/japanese_text.cpp`, button labels are defined as jafont_1 byte sequences:

```cpp
// Button label byte sequences (jafont_1 indices)
static const unsigned char BUTTON_LABEL_CANCEL[] = { 0xB6, 0x4C, 0xD0 };  // Ｃキー
static const unsigned char BUTTON_LABEL_SWITCH[] = { 0xCB, 0x4C, 0xD0 };  // Ｘキー
static const unsigned char BUTTON_LABEL_MENU[] = { 0xC9, 0x4C, 0xD0 };    // Ｖキー
static const unsigned char BUTTON_LABEL_PAGEUP[] = { 0xC3, 0xBA, 0xC8, 0xC3 };  // ＰＧＵＰ
static const unsigned char BUTTON_LABEL_PAGEDN[] = { 0xC3, 0xBA, 0xB7, 0xC1 };  // ＰＧＤＮ
static const unsigned char BUTTON_LABEL_ASSIST[] = { 0xCD, 0x4C, 0xD0 };  // Ｚキー

// Mapping table (F0-FF)
static const ButtonLabelData buttonLabels[16] = {
    { nullptr, 0 },                              // F0 - OK/Confirm
    { BUTTON_LABEL_CANCEL, 3 },                  // F1 - Cancel
    { BUTTON_LABEL_MENU, 3 },                    // F2 - Menu
    { BUTTON_LABEL_SWITCH, 3 },                  // F3 - Switch
    { BUTTON_LABEL_PAGEUP, 4 },                  // F4 - Page Up
    { BUTTON_LABEL_PAGEDN, 4 },                  // F5 - Page Down
    { BUTTON_LABEL_ASSIST, 3 },                  // F6 - Assist
    // ... remaining entries
};
```

#### 2. Placeholder Detection

In the `case 0xFDu:` handler, detect button placeholders and set up label injection:

```cpp
case 0xFDu:
  // ...
  if ( *buffer_text >= 0xF0u )
  {
    unsigned char placeholderCode = *buffer_text - 0xF0;
    // Set up button label buffer for injection
    if (placeholderCode < 16 && buttonLabels[placeholderCode].bytes != nullptr)
    {
      buttonLabelBuffer = buttonLabels[placeholderCode].bytes;
      buttonLabelIndex = 0;
      buttonLabelLength = buttonLabels[placeholderCode].length;
    }
    // ...
  }
```

#### 3. Character Injection Loop

At the start of each rendering iteration, check if we're rendering from the button label buffer:

```cpp
for ( i = 0; i < 1024 && ...; ++i )
{
  bool renderingFromButtonLabel = false;
  if (buttonLabelBuffer != nullptr && buttonLabelIndex < buttonLabelLength)
  {
    unsigned char effectiveChar = buttonLabelBuffer[buttonLabelIndex++];
    renderingFromButtonLabel = true;

    // Set up rendering for this character
    graphics_object = ff7_externals.menu_jafont_1_graphics_object;
    offset_u_in_byte = 32 * (effectiveChar % 16);
    graphics_object_v_in_byte = 32 * (effectiveChar / 16);
    // ...
    goto RENDER_BUTTON_LABEL_CHAR;
  }
  // Normal text processing...
}
```

### Button Placeholder Mapping

| Code | Function | Default Key | Label |
|------|----------|-------------|-------|
| FD F0 | OK/Confirm | Enter | (not implemented) |
| FD F1 | Cancel | C | Ｃキー |
| FD F2 | Menu | V | Ｖキー |
| FD F3 | Switch | X | Ｘキー |
| FD F4 | Page Up | PgUp | ＰＧＵＰ |
| FD F5 | Page Down | PgDn | ＰＧＤＮ |
| FD F6 | Assist | Z | Ｚキー |
| FD F7-FF | Various | - | (not implemented) |

### Field Files with Button Placeholders

Found in all tutorial/instruction dialogues:
- `smkin_4` - Barret's running tutorial
- `mds7_*` - Sector 7 areas
- Many other field files (~8000+ total occurrences across all placeholder codes)

---

## Testing Checklist

- [ ] Heart symbol renders in dialogue
- [ ] Heart has correct width/spacing
- [ ] Rainbow animation starts at `FE DB` code
- [ ] Rainbow animation continues through entire animated section
- [ ] Rainbow animation matches original Japanese game behavior
- [ ] Button placeholders show correct key labels (Ｃキー, Ｖキー, etc.)
- [ ] Button labels appear at correct position with proper spacing
- [ ] No regression in other Japanese text rendering

---

## References

- [Qhimm Wiki - FF7 TEX Format](http://wiki.qhimm.com/FF7/TEX_format)
- Original Japanese PC release (D:\Games\Stand-alone\FINAL FANTASY VII)
- Field file mds7_w2 for rainbow text testing
