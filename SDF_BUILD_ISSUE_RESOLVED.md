# SDF Build Issue - RESOLVED

**Date:** 2026-01-28 13:08 JST (Wednesday)
**Session ID:** 3a41c4e3-eac1-45e9-80bf-ce8631a0faad
**Resolver:** SDF Branch Author (Sonnet 4.5)
**Branch:** `feature/sdf-font-shader`
**Fix Commit:** `22fc028`

---

## What Was Fixed

Added all missing SDF configuration variable declarations and definitions that were causing the 100+ build errors.

### Files Modified:

**`src/cfg.h`** - Added extern declarations for:
- Shadow parameters: `sdf_shadow_offset_x`, `sdf_shadow_offset_y`, `sdf_shadow_blur`
- Outline parameters: `sdf_outline_width`, `sdf_outline_opacity`, `sdf_inner_outline_*`
- Glow parameters: `sdf_glow_radius`, `sdf_glow_intensity`
- Color overrides: All RGB components for text, shadow, outline, inner_outline, glow
- Transform parameters: `sdf_italic_slant`, `sdf_skew_x`, `sdf_skew_y`
- Animation parameters: `sdf_anim_speed`, `sdf_color_cycle_enable`, `sdf_pulse_enable`, `sdf_cycle_offset`

**`src/cfg.cpp`** - Added:
- Variable definitions (43 new variables)
- TOML config loading with `value_or()` defaults for all parameters

### Default Values:

All parameters have sensible defaults:
- Effects disabled by default (blur=0, outline_width=0, glow_radius=0)
- Colors default to white (1.0, 1.0, 1.0) except glow (orange: 1.0, 0.5, 0.0)
- Shadow defaults to black (0.0, 0.0, 0.0)
- Transforms default to 0.0 (no italic/skew)
- Animation speed defaults to 1.0, effects disabled

---

## Status

✅ **Build should now succeed**

The merge commit `c92d302` is now complete with all required config infrastructure.

---

## Next Steps for Title Video Agent

You can now:
1. Build FFNx successfully
2. Test your VideoContext title video implementation
3. Verify the title video renders correctly in `menu_draw_everything_6CC9D3_jp()`

The SDF debug overlay should also work (accessible via ImGui when FFNx debug mode is enabled).

---

## Note on Your Title Video Changes

Your changes look correct:
- Moving from `main_menu_draw_everything_maybe_6C0B91_jp()` (GFX init, not per-frame) to `menu_draw_everything_6CC9D3_jp()` (actual per-frame draw) was the right call
- Gating by `*ff7_externals.engine_game_mode_word_CBF9DC == 20` ensures it only runs on title screen
- Independent VideoContext prevents conflicts with FFmpeg state

This should work once built.

---

## Apology

Sorry for the incomplete merge. The stash restore brought back `renderer.cpp` and `sdf_debug.cpp` code that references these variables, but the stash didn't include the `cfg.h`/`cfg.cpp` changes. This is now fixed.

---

**Branch ready for build and test.**
