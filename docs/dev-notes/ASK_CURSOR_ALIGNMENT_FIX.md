# ASK Dialogue Cursor Alignment Fix - Developer Journey

**Created:** 2025-12-11 17:33 JST (Thursday)
**Author:** John Zealand-Doyle + Claude Code
**Session-ID:** 0681f78b-0382-45ee-898b-5a32b7ce32d5

---

## Executive Summary

Fixed the ASK dialogue cursor (finger pointer) misalignment when using custom 26px Japanese line height instead of vanilla 32px. The cursor drifted further down with each row - by row 8+, it was completely outside the dialogue box.

**Solution:** Direct memory patch at `0x63138A` changing `shl eax, 4` (multiply by 16) to `imul eax, eax, 13` (multiply by 13).

---

## The Problem

When Japanese text rendering was changed from 32px to 26px line height for better text density:
- Text rendered correctly at 26px spacing
- The ASK dialogue cursor (selection finger) still used 32px spacing internally
- Result: Cursor drifted 6px per row relative to text
- By row 8, cursor was ~48px off - completely outside the dialogue

**Visual:** Cursor points at wrong option, gets worse as you scroll down.

---

## Initial Assumptions (All Wrong)

### Assumption 1: Cursor uses `field_submit_draw_arrow`
We believed the ASK cursor used the same rendering path as the field pointer (hand over Cloud's head):
```
field_draw_pointer_hand -> field_submit_draw_pointer_hand -> field_submit_draw_arrow
```

**Reality:** The ASK cursor uses a completely different code path. It's a sprite blit from WINDOW.BIN, not a polygon through the arrow system.

### Assumption 2: Address `0x631D10` is DrawWindowCursor
Documentation suggested this address for the cursor drawing function.

**Reality:** This address contains garbage in the Steam version - different build/version. Scanning it found only calls to `sub_6CB9B8` (text buffer function).

### Assumption 3: We could find cursor code by scanning for multiply-by-32
We searched the text box code area (`0x6E7000-0x6F0000`) for `shl reg, 5` or `imul reg, 32`.

**Reality:** The cursor Y calculation was in a completely different area (`0x631xxx`) and used multiply-by-16, not 32 (internal coordinates get scaled).

---

## Tools Used

### 1. FFNx Logging (Primary Tool)
Added custom scanning code to FFNx to:
- Dump all function calls in specific ranges
- Find all callers to specific functions
- Search for memory address references
- Locate multiply instructions

**Pros:** Full control, persistent across runs, comprehensive output
**Cons:** Requires rebuild for each change, tedious iteration

### 2. Cheat Engine (Breakthrough Tool)
Used to find memory addresses that change when cursor moves:
1. "Unknown initial value" scan
2. Move cursor down -> "Increased value" scan
3. Move cursor up -> "Decreased value" scan
4. Narrowed to 4 addresses

**Key Finding:** Address `0xCFF5DE` (value 118) changes with cursor movement.

**Pros:** Fast memory searching, real-time value monitoring
**Cons:** Debugger feature crashed the game (DRM issues)

### 3. x32dbg (Attempted, Limited Success)
Tried to set hardware write breakpoints on the addresses found.

**Issues:**
- Steam DRM blocked direct execution
- Required Steamless to unpack exe
- Hardware breakpoints didn't trigger reliably
- Many false exceptions cluttered debugging

### 4. Steamless
Used to strip Steam DRM from `ff7_en.exe` to enable debugging.
- Creates `ff7_en.exe.unpacked.exe`
- Game runs but some features (like Steam overlay) don't work

### 5. IDA Pro (Attempted, Abandoned)
Tried for static analysis and debugging.

**Issues:**
- Constant exception popups (50+)
- "Don't display again" checkbox didn't persist
- Made debugging impractical

---

## The Journey (Chronological)

### Phase 1: Wrong Hook Point
**Hours 1-2**

Implemented context-aware cursor detection in `ff7_field_submit_draw_cursor`:
- Check if cursor Y is inside text box window bounds
- If yes -> ASK cursor -> apply correction
- If no -> field pointer -> no correction

**Result:** CURSOR_HOOK traces showed the function was called, but only for the field pointer. Zero calls during ASK dialogue. The ASK cursor doesn't use this code path at all.

### Phase 2: Comprehensive Code Scanning
**Hour 3**

User frustrated: *"I'm sick of these fucking surgical things. I would much prefer if you just looked fucking everywhere and logged every fucking call"*

Implemented full code segment scan (`0x401000-0x700000`) for:
- All calls to `field_submit_draw_arrow`
- All calls to `field_submit_draw_pointer_hand`
- All calls to `field_draw_pointer_hand`

**Result:** Only found calls for gateway arrows and field pointer. Confirmed ASK cursor uses different path.

### Phase 3: External AI Consultation
**Hour 4**

Consulted external AI for hook suggestions. Tried multiple offsets:
- `0x39F` - Crashed (stack cleanup instruction)
- `0x3A2` - Wrong function (text boxes)
- `0x3AA` - Crashed (mov/push instruction)
- `0x631D10` - Wrong function (text buffer)

All failed. The documented addresses were for a different game version.

### Phase 4: Memory-Based Approach
**Hour 5**

Switched strategy: Instead of finding code, find the memory that stores cursor position.

**Cheat Engine Process:**
1. Start at ASK dialogue, cursor on first option
2. Unknown initial value scan
3. Move cursor down -> Increased value
4. Repeat until 4 addresses remain:
   - `0xCC14FD` (value 7)
   - `0xCFF5DE` (value 118) <-- This one!
   - `0x382F6DC` (value 7)
   - `0x7A3F9998` (value 7)

### Phase 5: Finding the Write Location
**Hour 6**

Added FFNx scan to find code that references address `0xCFF5DE`:

```cpp
uint32_t targets[] = {0xCC14FD, 0xCFF5DE, 0x0382F6DC, 0x7A3F9998};
for (uint32_t addr = 0x401000; addr < 0x750000; addr++) {
    uint32_t val = *(uint32_t*)addr;
    for (int t = 0; t < 4; t++) {
        if (val == targets[t]) {
            ffnx_info("REF 0x%08X at code 0x%08X\n", val, addr);
        }
    }
}
```

**Result:**
```
REF 0x00CFF5DE at code 0x0063139F [bytes: 89 81 8B 15 D8 F9]
```

Code at `0x63139F` writes to the cursor position!

### Phase 6: Analyzing the Instruction
**Hour 6 continued**

Dumped bytes around `0x63139F`:

```
0x631388: 0F BF 02 C1 E0 04 83 C0 06 8B 4D 08...
```

Decoded:
- `0F BF 02` = movsx eax, word ptr [edx]
- `C1 E0 04` = **shl eax, 4** (multiply by 16)
- `83 C0 06` = add eax, 6

The cursor Y is calculated as: `(row * 16) + 6` at internal resolution.

Since vanilla uses 32px and internal is half (16px), for 26px we need 13px: `26 / 2 = 13`

### Phase 7: The Fix
**Final Solution**

Patch at `0x63138A`:
- **Before:** `C1 E0 04` (shl eax, 4 = multiply by 16)
- **After:** `6B C0 0D` (imul eax, eax, 13)

```cpp
if (ff7_japanese_edition)
{
    unsigned char* patch_addr = (unsigned char*)0x63138A;

    DWORD old_protect;
    VirtualProtect(patch_addr, 3, PAGE_EXECUTE_READWRITE, &old_protect);
    patch_addr[0] = 0x6B;  // imul
    patch_addr[1] = 0xC0;  // eax, eax
    patch_addr[2] = 0x0D;  // 13
    VirtualProtect(patch_addr, 3, old_protect, &old_protect);
}
```

---

## Key Technical Details

### Memory Layout
- `0xCFF5B8` = `text_box_window_data_array` base
- `0xCFF5DE` = `text_box_window_data_array[0]` + 0x26 = cursor Y position
- Text box struct size = 0x30 (48 bytes)

### Coordinate System
- Internal resolution: 320x240 (half of 640x480)
- Vanilla line height: 32px display = 16px internal
- Custom line height: 26px display = 13px internal

### The Function at 0x631300+
This function handles ASK dialogue cursor positioning:
- Reads current option index
- Multiplies by line height (was 16, now 13)
- Adds base offset (6)
- Writes to cursor Y position in text box struct

---

## Files Modified

### `/mnt/c/FFNx/src/ff7/field/field.cpp`
Added memory patch in `ff7_field_init()`:
```cpp
// Patch cursor Y calculation at 0x63138A
if (ff7_japanese_edition)
{
    unsigned char* patch_addr = (unsigned char*)0x63138A;
    DWORD old_protect;
    VirtualProtect(patch_addr, 3, PAGE_EXECUTE_READWRITE, &old_protect);
    patch_addr[0] = 0x6B;  // imul
    patch_addr[1] = 0xC0;  // eax, eax
    patch_addr[2] = 0x0D;  // 13
    VirtualProtect(patch_addr, 3, old_protect, &old_protect);
}
```

---

## Lessons Learned

### 1. Don't Trust Documentation Addresses
Different game versions (PSX, PC 1998, Steam) have different addresses. Always verify dynamically.

### 2. Memory Scanning > Code Tracing
When you can't find code that modifies something, find the memory it modifies, then trace back to the code.

### 3. Cheat Engine is Underrated for Reverse Engineering
The "find what writes to this address" feature is powerful (when it doesn't crash).

### 4. The Obvious Path Isn't Always Right
The cursor LOOKS like it should use the arrow rendering system. It doesn't. It's a sprite blit from a completely different code path.

### 5. Scaling Matters
What looks like "multiply by 32" at display resolution might be "multiply by 16" internally. Always consider coordinate system scaling.

---

## Future Considerations

### If Line Height Changes Again
The patch value (13) is hardcoded for 26px line height. If line height becomes configurable:
```cpp
int internal_line_height = custom_line_height / 2;
patch_addr[2] = (unsigned char)internal_line_height;
```

### Other Cursors
This fix only affects ASK dialogue cursor. Other cursors (menus, battle) may need separate investigation if they show similar issues.

### There's a Second shl at 0x631441
There's another `shl eax, 4` at `0x631441` in the same function. This might be for a different code path (scrolling?). Monitor if issues appear.

---

## Debugging Commands for Future Reference

### Filter FFNx Log
```bash
grep -v "bindVertexBuffer\|XYZW\|BGRA" FFNx.log > filtered.log
```

### Search for Memory References in FFNx
```cpp
for (uint32_t addr = 0x401000; addr < 0x750000; addr++) {
    if (*(uint32_t*)addr == TARGET_ADDRESS) {
        ffnx_info("Found at 0x%08X\n", addr);
    }
}
```

### Cheat Engine Scan Process
1. Unknown initial value
2. Increase/decrease value based on cursor movement
3. Narrow down to <10 addresses
4. "Find what writes to this address"

---

## Total Time Spent

~6 hours of debugging across multiple sessions.

**Breakdown:**
- 2 hours: Wrong assumptions about arrow rendering path
- 1 hour: External AI consultation and failed hook attempts
- 1 hour: Tool setup (Cheat Engine, x32dbg, Steamless, IDA)
- 1 hour: Memory scanning and reference hunting
- 1 hour: Code analysis and patch implementation

---

## Acknowledgments

User's persistence through frustration led to the breakthrough. The switch from "find the code" to "find the memory" was the key insight.

Sometimes the best debugging tool is pure stubbornness.
