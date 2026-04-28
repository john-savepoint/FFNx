# SDF Build Issue Report - For SDF Branch Author

**Date:** 2026-01-28 12:30 JST (Wednesday)
**Session ID:** 827bc3ea-8174-49ca-b9c7-8c8e8809821e
**Reporter:** Title Video Implementation Agent (Opus 4.5)
**Branch:** `feature/sdf-font-shader`
**Commit:** `c92d302` (merge: combine SDF debug overlay + cell-local coords with title video work)

---

## Problem

The build fails with 100+ errors due to undeclared SDF config variables. These variables are referenced in `renderer.cpp` and `sdf_debug.cpp` but are not declared in `cfg.h` or defined in `cfg.cpp`.

## Affected Files

### `src/renderer.cpp` (lines ~2440-2463)
References these undeclared identifiers:
- `sdf_glow_color_g`
- `sdf_glow_color_b`
- `sdf_italic_slant`
- `sdf_skew_x`
- `sdf_skew_y`
- `sdf_anim_speed`
- `sdf_color_cycle_enable`
- `sdf_pulse_enable`
- `sdf_cycle_offset`

### `src/sdf_debug.cpp` (lines ~356-386)
References these undeclared identifiers:
- `sdf_skew_y`
- `sdf_italic_slant`
- `sdf_skew_x`
- `sdf_shadow_offset_x`
- `sdf_shadow_offset_y`
- `sdf_shadow_blur`
- `sdf_outline_width`
- `sdf_inner_outline_width`

## Root Cause

These variables appear to have been added to `renderer.cpp` and `sdf_debug.cpp` during the SDF font implementation but their `extern` declarations in `cfg.h` and definitions in `cfg.cpp` (with TOML config loading via `value_or()`) were not included in the merge commit `c92d302`.

## What I Need

I'm implementing the independent video context for title screen video playback (VideoContext class). My changes to `japanese_text.cpp` compile fine, but the build fails before linking because of these SDF errors. I cannot produce a testable `FFNx.dll` until this is resolved.

## Suggested Fix

Add to `cfg.h`:
```cpp
extern float sdf_italic_slant;
extern float sdf_skew_x;
extern float sdf_skew_y;
extern float sdf_shadow_offset_x;
extern float sdf_shadow_offset_y;
extern float sdf_shadow_blur;
extern float sdf_outline_width;
extern float sdf_inner_outline_width;
extern float sdf_glow_color_g;
extern float sdf_glow_color_b;
extern float sdf_anim_speed;
extern bool sdf_color_cycle_enable;
extern bool sdf_pulse_enable;
extern float sdf_cycle_offset;
```

And corresponding definitions + TOML loading in `cfg.cpp`. The exact default values and types should be determined by the SDF branch author who knows the intended behavior.

## My Changes (Ready to Test Once Build Works)

- Moved title video rendering from `main_menu_draw_everything_maybe_6C0B91_jp()` (GFX init chain, never called per-frame) to `menu_draw_everything_6CC9D3_jp()` (the actual per-frame draw function)
- Gated by `*ff7_externals.engine_game_mode_word_CBF9DC == 20` (title screen mode)
- Uses new `VideoContext` class with independent FFmpeg pipeline
