/****************************************************************************/
//    Copyright (C) 2009 Aali132                                            //
//    Copyright (C) 2018 quantumpencil                                      //
//    Copyright (C) 2018 Maxime Bacoux                                      //
//    Copyright (C) 2020 myst6re                                            //
//    Copyright (C) 2020 Chris Rizzitello                                   //
//    Copyright (C) 2020 John Pritchard                                     //
//    Copyright (C) 2024 Julian Xhokaxhiu                                   //
//    Copyright (C) 2023 Tang-Tang Zhou                                     //
//    Copyright (C) 2024 John Zealand-Doyle                                 //
//                                                                          //
//    This file is part of FFNx                                             //
//                                                                          //
//    FFNx is free software: you can redistribute it and/or modify          //
//    it under the terms of the GNU General Public License as published by  //
//    the Free Software Foundation, either version 3 of the License         //
//                                                                          //
//    FFNx is distributed in the hope that it will be useful,               //
//    but WITHOUT ANY WARRANTY; without even the implied warranty of        //
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         //
//    GNU General Public License for more details.                          //
/****************************************************************************/

// Japanese Naming Screen Implementation
// Replaces the disabled English keyboard input with a 3-page Japanese character selector
// Pages: Hiragana, Katakana, Eisuu (alphanumeric)
//
// INJECTION APPROACH (2025-12-13):
// Instead of fighting vanilla's save logic, we inject directly into vanilla's buffers:
// - Write Japanese characters to vanilla's temp buffer at 0xDD45F0
// - Sync cursor position with vanilla's cursor at 0xDD4614
// - Blank out English character grid at 0x921D70
// This way, when vanilla confirms, it copies OUR Japanese data to savemap.

#include "../ff7.h"
#include "../log.h"
#include "../gamepad.h"
#include "defs.h"
#include <cstring>

// ============================================================================
// ENUMS AND CONSTANTS
// ============================================================================

enum NamingScreenPage {
    PAGE_HIRAGANA = 0,
    PAGE_KATAKANA = 1,
    PAGE_EISUU = 2
};

enum SidebarAction {
    SIDEBAR_HIRAGANA = 0,
    SIDEBAR_KATAKANA = 1,
    SIDEBAR_EISUU = 2,
    SIDEBAR_SPACE = 3,
    SIDEBAR_DELETE = 4,
    SIDEBAR_CONFIRM = 5,
    SIDEBAR_DEFAULT = 6
};

// Grid layout constants
// Values calibrated from cursor position screenshots (2025-12-13)
// Hand cursor at (0,0) appears around screen position (330, 345)
// 10 columns span about 400px horizontally
// 9 rows span about 290px vertically
const int GRID_BASE_X = 118;    // Where first column character renders
const int GRID_BASE_Y = 172;    // Where first row character renders
const int CELL_WIDTH = 40;      // Horizontal spacing between columns
const int CELL_HEIGHT = 33;     // Vertical spacing between rows
const int GRID_COLS = 10;
const int GRID_ROWS_KANA = 9;
const int GRID_ROWS_EISUU = 5;

// Sidebar constants - page indicator labels (ひらがな/カタカナ/えいすう)
// From markup: need to shift left and down from current position
const int SIDEBAR_X = 505;      // Adjusted left
const int SIDEBAR_Y = 172;      // Aligned with grid top
const int SIDEBAR_ITEM_HEIGHT = 33;  // Match grid row height
const int SIDEBAR_ITEMS = 7;

// Name buffer constants
const int NAME_MAX_CHARS = 9;
const float NAMING_SCREEN_Z = 0.0f;

// ============================================================================
// VANILLA MEMORY ADDRESSES (Found via Cheat Engine 2025-12-13)
// ============================================================================

// Vanilla's temp name buffer - where characters are stored during input
// 9 bytes for characters + 0xFF terminator
uint8_t* const VANILLA_NAME_BUFFER = (uint8_t*)0x00DD45F0;

// Vanilla's cursor position - current character index (0-9) in the name
// 0x00DD4614 was wrong - the actual buffer cursor is at 0x00DD46F0
int* const VANILLA_NAME_CURSOR_POS = (int*)0x00DD46F0;

// Vanilla's grid cursor positions
int* const VANILLA_GRID_CURSOR_X = (int*)0x00DD4538;
int* const VANILLA_GRID_CURSOR_Y = (int*)0x00DD453C;

// English character grid in memory - we blank this so vanilla input does nothing useful
// This is the A-Z, 0-9 grid that gets rendered and selected from
uint8_t* const ENGLISH_GRID_ADDRESS = (uint8_t*)0x00921D70;
const int ENGLISH_GRID_SIZE = 90; // Approximate size of the grid data

// Flag indicating if cursor is in grid (0) or sidebar (1)
// Found via Cheat Engine - alternates between 0/1 when moving between grid and sidebar
int* const VANILLA_IN_SIDEBAR_FLAG = (int*)0x00921ED4;

// Input timing
const uint32_t INPUT_INITIAL_DELAY = 15;
const uint32_t INPUT_REPEAT_RATE = 4;

// ============================================================================
// STATE STRUCTURE
// ============================================================================

struct NamingScreenState {
    NamingScreenPage current_page;
    int cursor_x;
    int cursor_y;
    int sidebar_cursor;
    bool in_sidebar;

    int name_cursor_pos;
    uint8_t name_buffer[12];
    int character_index;

    bool is_active;
    bool confirm_pressed;
    bool cancel_pressed;
    bool l1_pressed;
    bool r1_pressed;

    uint32_t last_input_frame;
    uint32_t frame_counter;
};

static NamingScreenState g_naming_state = {0};

// Global flag for other modules to check if naming screen is active
bool g_jp_naming_screen_active = false;

// Flag to indicate we're currently drawing our own characters (not to be filtered)
bool g_jp_naming_screen_drawing = false;

// Force-overwrite counter - when > 0, we re-apply our Japanese name to savemap each frame
// This counters the game's attempt to overwrite with its empty temp buffer
int g_jp_naming_force_overwrite_frames = 0;

// Saved name buffer for force-overwrite (copy of what we want to persist)
static uint8_t g_saved_name_buffer[12] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static int g_saved_character_index = 0;

// Track previous state for passive injection (detect when vanilla adds/deletes a character)
static int g_prev_name_pos = -1;
static int g_prev_grid_x = 0;
static int g_prev_grid_y = 0;
static int g_prev_in_sidebar = 0;

// Track if Cancel was pressed while in grid - used to undo vanilla's sidebar snap
// We need to keep trying for a few frames because vanilla's state change may be delayed
static int g_cancel_undo_frames = 0;
static const int CANCEL_UNDO_MAX_FRAMES = 3;  // Try for up to 3 frames

// Original function pointer for post-hook pattern
typedef void (*menu_sub_718DBE_func)();
static menu_sub_718DBE_func g_original_menu_sub_718DBE = nullptr;

// ============================================================================
// CHARACTER TABLES (jafont_1 indices)
// ============================================================================

// Hiragana table (9x10 grid)
static const uint8_t HIRAGANA_TABLE[9][10] = {
    // Row 0: あ行 + small あ行
    {0x6B, 0x6D, 0x69, 0x6F, 0x71, 0xA5, 0xA7, 0xA9, 0xAB, 0xAD},
    // Row 1: か行 + が行
    {0x4B, 0x4D, 0x4F, 0x51, 0x53, 0x0B, 0x0D, 0x0F, 0x11, 0x13},
    // Row 2: さ行 + ざ行
    {0x55, 0x57, 0x59, 0x5B, 0x5D, 0x15, 0x17, 0x19, 0x1B, 0x1D},
    // Row 3: た行 + だ行
    {0x5F, 0x61, 0x63, 0x65, 0x67, 0x1F, 0x21, 0x23, 0x25, 0x27},
    // Row 4: な行 + special
    {0x73, 0x75, 0x77, 0x79, 0x7B, 0x9D, 0x3F, 0x3F, 0x3F, 0xD1},
    // Row 5: は行 + ば行
    {0x41, 0x43, 0x45, 0x47, 0x49, 0x01, 0x03, 0x05, 0x07, 0x09},
    // Row 6: ま行 + ぱ行
    {0x7D, 0x7F, 0x81, 0x83, 0x85, 0x2A, 0x2C, 0x2E, 0x30, 0x32},
    // Row 7: や行 + small や行 + っ
    {0x87, 0x89, 0x8B, 0x9F, 0xA1, 0xA3, 0x3F, 0x3F, 0x3D, 0x3E},
    // Row 8: ら行 + わ行
    {0x8D, 0x8F, 0x91, 0x93, 0x95, 0x97, 0x9B, 0x99, 0xAE, 0xAF}
};

// Katakana table (9x10 grid)
static const uint8_t KATAKANA_TABLE[9][10] = {
    // Row 0: ア行 + small ア行
    {0x6A, 0x6C, 0x68, 0x6E, 0x70, 0xA4, 0xA6, 0xA8, 0xAA, 0xAC},
    // Row 1: カ行 + ガ行
    {0x4A, 0x4C, 0x4E, 0x50, 0x52, 0x0A, 0x0C, 0x0E, 0x10, 0x12},
    // Row 2: サ行 + ザ行
    {0x54, 0x56, 0x58, 0x5A, 0x5C, 0x14, 0x16, 0x18, 0x1A, 0x1C},
    // Row 3: タ行 + ダ行
    {0x5E, 0x60, 0x62, 0x64, 0x66, 0x1E, 0x20, 0x22, 0x24, 0x26},
    // Row 4: ナ行 + brackets
    {0x72, 0x74, 0x76, 0x78, 0x7A, 0xD7, 0xD8, 0xDF, 0xE0, 0xD0},
    // Row 5: ハ行 + バ行
    {0x40, 0x42, 0x44, 0x46, 0x48, 0x00, 0x02, 0x04, 0x06, 0x08},
    // Row 6: マ行 + パ行
    {0x7C, 0x7E, 0x80, 0x82, 0x84, 0x29, 0x2B, 0x2D, 0x2F, 0x31},
    // Row 7: special
    {0x86, 0x88, 0x8A, 0x9E, 0xA0, 0xA2, 0x9C, 0x3F, 0xCE, 0xD2},
    // Row 8: ヤ行 + ワ行
    {0x8C, 0x8E, 0x90, 0x92, 0x94, 0x96, 0x9A, 0x98, 0xD5, 0xD4}
};

// Eisuu (alphanumeric) table (5x10 grid)
// Matches Japanese AF3DN.P at offset 0x4116C exactly
static const uint8_t EISUU_TABLE[5][10] = {
    // Row 0: A-J (fullwidth)
    {0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD},
    // Row 1: K-T (fullwidth)
    {0xBE, 0xBF, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7},
    // Row 2: U-Z, space, ！, 「, 」
    {0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0x3F, 0xB2, 0xDB, 0xDC},
    // Row 3: 0-9 (fullwidth)
    {0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C},
    // Row 4: symbols (？, ／, space, space, ・, space, space, ー, ～, XIII)
    // Note: 0xE6 is the special XIII character (Roman numeral 13) used in Red XIII's name
    {0xCF, 0xD3, 0x3F, 0x3F, 0xD6, 0x3F, 0x3F, 0xD9, 0xDA, 0xE6}
};

// Sidebar labels (jafont_1 indices, 0xFF terminated)
static const uint8_t SIDEBAR_HIRAGANA_LABEL[] = {0x43, 0x87, 0x0B, 0x73, 0xFF};
static const uint8_t SIDEBAR_KATAKANA_LABEL[] = {0x4A, 0x5E, 0x4A, 0x72, 0xFF};
static const uint8_t SIDEBAR_EISUU_LABEL[] = {0x6F, 0x6D, 0x59, 0x69, 0xFF};
static const uint8_t SIDEBAR_SPACE_LABEL[] = {0x58, 0x2F, 0xD0, 0x58, 0xFF};
static const uint8_t SIDEBAR_DELETE_LABEL[] = {0x55, 0x4F, 0x17, 0xA3, 0xFF};
static const uint8_t SIDEBAR_CONFIRM_LABEL[] = {0x51, 0x9D, 0x65, 0x6D, 0xFF};
static const uint8_t SIDEBAR_DEFAULT_LABEL[] = {0x24, 0x44, 0xAC, 0x8A, 0x66, 0xFF};

static const uint8_t* SIDEBAR_LABELS[7] = {
    SIDEBAR_HIRAGANA_LABEL,
    SIDEBAR_KATAKANA_LABEL,
    SIDEBAR_EISUU_LABEL,
    SIDEBAR_SPACE_LABEL,
    SIDEBAR_DELETE_LABEL,
    SIDEBAR_CONFIRM_LABEL,
    SIDEBAR_DEFAULT_LABEL
};

// ============================================================================
// FORWARD DECLARATIONS
// ============================================================================

static void naming_screen_init(int character_index);
static void naming_screen_process_input();
static void naming_screen_draw();
static int naming_screen_get_max_rows();
static void naming_screen_write_table_to_grid();
static uint8_t naming_screen_get_char_at_cursor();

// ============================================================================
// INITIALIZATION
// ============================================================================

static void naming_screen_init(int character_index)
{
    g_naming_state.current_page = PAGE_HIRAGANA;
    g_naming_state.cursor_x = 0;
    g_naming_state.cursor_y = 0;
    // sidebar_cursor and in_sidebar are no longer used - vanilla handles sidebar
    g_naming_state.sidebar_cursor = 0;
    g_naming_state.in_sidebar = false;

    // Sync our cursor position with vanilla's cursor
    g_naming_state.name_cursor_pos = *VANILLA_NAME_CURSOR_POS;
    if (g_naming_state.name_cursor_pos < 0) g_naming_state.name_cursor_pos = 0;
    if (g_naming_state.name_cursor_pos > NAME_MAX_CHARS) g_naming_state.name_cursor_pos = NAME_MAX_CHARS;

    // Copy vanilla's current buffer to our buffer (in case there's a default name)
    memcpy(g_naming_state.name_buffer, VANILLA_NAME_BUFFER, NAME_MAX_CHARS);
    // Fill rest with 0xFF
    for (int i = NAME_MAX_CHARS; i < 12; i++) {
        g_naming_state.name_buffer[i] = 0xFF;
    }

    g_naming_state.character_index = character_index;

    g_naming_state.is_active = true;
    g_naming_state.confirm_pressed = false;
    g_naming_state.cancel_pressed = false;
    g_naming_state.l1_pressed = false;
    g_naming_state.r1_pressed = false;

    g_naming_state.last_input_frame = 0;
    g_naming_state.frame_counter = 0;

    g_jp_naming_screen_active = true;

    // Write the initial page's table to vanilla's grid memory
    // This replaces the English A-Z grid with Japanese characters at 0x921D70
    // Vanilla's rendering loop will now display our Japanese characters
    naming_screen_write_table_to_grid();

    // Reset passive injection tracking variables
    g_prev_name_pos = *VANILLA_NAME_CURSOR_POS;
    g_prev_grid_x = *VANILLA_GRID_CURSOR_X;
    g_prev_grid_y = *VANILLA_GRID_CURSOR_Y;
    g_prev_in_sidebar = *VANILLA_IN_SIDEBAR_FLAG;
    g_cancel_undo_frames = 0;

    ffnx_info("naming_screen_init: character_index=%d, vanilla_name_pos=%d, grid=(%d,%d)\n",
        character_index, *VANILLA_NAME_CURSOR_POS, *VANILLA_GRID_CURSOR_X, *VANILLA_GRID_CURSOR_Y);
    ffnx_info("naming_screen_init: Vanilla buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
        VANILLA_NAME_BUFFER[0], VANILLA_NAME_BUFFER[1], VANILLA_NAME_BUFFER[2],
        VANILLA_NAME_BUFFER[3], VANILLA_NAME_BUFFER[4], VANILLA_NAME_BUFFER[5],
        VANILLA_NAME_BUFFER[6], VANILLA_NAME_BUFFER[7], VANILLA_NAME_BUFFER[8]);
}

// ============================================================================
// INPUT HANDLING
// ============================================================================

static bool naming_screen_check_button_edge(bool button_state, bool* was_pressed)
{
    bool pressed_now = button_state;
    bool result = pressed_now && !(*was_pressed);
    *was_pressed = pressed_now;
    return result;
}

static bool naming_screen_should_process_dpad()
{
    uint32_t frame = g_naming_state.frame_counter;
    uint32_t last = g_naming_state.last_input_frame;

    if (last == 0) {
        g_naming_state.last_input_frame = frame;
        return true;
    }

    uint32_t elapsed = frame - last;
    if (elapsed >= INPUT_INITIAL_DELAY) {
        if ((elapsed - INPUT_INITIAL_DELAY) % INPUT_REPEAT_RATE == 0) {
            return true;
        }
    }
    return false;
}

static void naming_screen_handle_dpad(int dx, int dy)
{
    // SIMPLIFIED NAVIGATION (2025-12-13):
    // - We only navigate the character grid
    // - No sidebar navigation (vanilla handles sidebar via its own cursor)
    // - No wrap-around (cursor stops at edges, matching vanilla behavior)
    // - Vanilla cursor controls actual selection, we just overlay Japanese chars

    int max_rows = naming_screen_get_max_rows();

    if (dx != 0) {
        g_naming_state.cursor_x += dx;
        // Clamp to grid bounds - NO wrap-around, NO sidebar entry
        if (g_naming_state.cursor_x < 0) {
            g_naming_state.cursor_x = 0;
        }
        if (g_naming_state.cursor_x >= GRID_COLS) {
            g_naming_state.cursor_x = GRID_COLS - 1;
        }
    }

    if (dy != 0) {
        g_naming_state.cursor_y += dy;
        // Clamp to grid bounds - NO wrap-around
        if (g_naming_state.cursor_y < 0) {
            g_naming_state.cursor_y = 0;
        }
        if (g_naming_state.cursor_y >= max_rows) {
            g_naming_state.cursor_y = max_rows - 1;
        }
    }
}

// Write the current page's character table to vanilla's grid memory at 0x921D70
// This makes vanilla's rendering show our Japanese characters
static void naming_screen_write_table_to_grid()
{
    const uint8_t* src_table = nullptr;
    int table_size = 0;

    switch (g_naming_state.current_page) {
        case PAGE_HIRAGANA:
            src_table = &HIRAGANA_TABLE[0][0];
            table_size = GRID_ROWS_KANA * GRID_COLS; // 9 * 10 = 90 bytes
            break;
        case PAGE_KATAKANA:
            src_table = &KATAKANA_TABLE[0][0];
            table_size = GRID_ROWS_KANA * GRID_COLS; // 9 * 10 = 90 bytes
            break;
        case PAGE_EISUU:
            src_table = &EISUU_TABLE[0][0];
            table_size = GRID_ROWS_EISUU * GRID_COLS; // 5 * 10 = 50 bytes
            // Fill remaining 40 bytes with 0x3F (ideographic space) for rows 6-9
            memcpy(ENGLISH_GRID_ADDRESS, src_table, table_size);
            memset(ENGLISH_GRID_ADDRESS + table_size, 0x3F, 90 - table_size);
            ffnx_info("naming_screen_write_table_to_grid: Wrote EISUU table (%d bytes) + padding to 0x%08X\n",
                table_size, (uint32_t)ENGLISH_GRID_ADDRESS);
            return;
    }

    if (src_table != nullptr) {
        memcpy(ENGLISH_GRID_ADDRESS, src_table, table_size);
        ffnx_info("naming_screen_write_table_to_grid: Wrote %s table (%d bytes) to 0x%08X\n",
            g_naming_state.current_page == PAGE_HIRAGANA ? "Hiragana" : "Katakana",
            table_size, (uint32_t)ENGLISH_GRID_ADDRESS);
    }
}

static void naming_screen_switch_page(int direction)
{
    int page = (int)g_naming_state.current_page + direction;
    if (page < 0) page = 2;
    if (page > 2) page = 0;
    g_naming_state.current_page = (NamingScreenPage)page;

    // Clamp cursor if switching to/from eisuu
    int max_rows = naming_screen_get_max_rows();
    if (g_naming_state.cursor_y >= max_rows) {
        g_naming_state.cursor_y = max_rows - 1;
    }

    // Write the new page's table to vanilla's grid memory
    naming_screen_write_table_to_grid();

    if (trace_all)
        ffnx_trace("naming_screen_switch_page: new page=%d\n", page);
}

static void naming_screen_add_character(uint8_t char_code)
{
    if (g_naming_state.name_cursor_pos >= NAME_MAX_CHARS) return;

    // Write to OUR buffer
    g_naming_state.name_buffer[g_naming_state.name_cursor_pos] = char_code;

    // INJECTION: Also write to VANILLA's buffer so it gets saved properly
    VANILLA_NAME_BUFFER[g_naming_state.name_cursor_pos] = char_code;

    g_naming_state.name_cursor_pos++;

    // INJECTION: Sync vanilla's cursor position with ours
    *VANILLA_NAME_CURSOR_POS = g_naming_state.name_cursor_pos;

    if (trace_all)
        ffnx_trace("naming_screen_add_character: char=0x%02X pos=%d (synced to vanilla)\n",
            char_code, g_naming_state.name_cursor_pos);
}

static void naming_screen_delete_character()
{
    if (g_naming_state.name_cursor_pos > 0) {
        g_naming_state.name_cursor_pos--;

        // Clear in OUR buffer
        g_naming_state.name_buffer[g_naming_state.name_cursor_pos] = 0xFF;

        // INJECTION: Also clear in VANILLA's buffer
        VANILLA_NAME_BUFFER[g_naming_state.name_cursor_pos] = 0xFF;

        // INJECTION: Sync vanilla's cursor position with ours
        *VANILLA_NAME_CURSOR_POS = g_naming_state.name_cursor_pos;

        if (trace_all)
            ffnx_trace("naming_screen_delete_character: pos=%d (synced to vanilla)\n",
                g_naming_state.name_cursor_pos);
    }
}

static void naming_screen_add_space()
{
    naming_screen_add_character(0x3F);
}

static void naming_screen_confirm_name()
{
    // With the INJECTION approach, vanilla will copy VANILLA_NAME_BUFFER to savemap
    // We just need to ensure vanilla's buffer has our Japanese data (which it should)
    // and then let vanilla's confirm logic do the actual save

    ffnx_info("naming_screen_confirm_name: Confirming for character %d\n", g_naming_state.character_index);
    ffnx_info("naming_screen_confirm_name: Our buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
        g_naming_state.name_buffer[0], g_naming_state.name_buffer[1], g_naming_state.name_buffer[2],
        g_naming_state.name_buffer[3], g_naming_state.name_buffer[4], g_naming_state.name_buffer[5],
        g_naming_state.name_buffer[6], g_naming_state.name_buffer[7], g_naming_state.name_buffer[8]);
    ffnx_info("naming_screen_confirm_name: Vanilla buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
        VANILLA_NAME_BUFFER[0], VANILLA_NAME_BUFFER[1], VANILLA_NAME_BUFFER[2],
        VANILLA_NAME_BUFFER[3], VANILLA_NAME_BUFFER[4], VANILLA_NAME_BUFFER[5],
        VANILLA_NAME_BUFFER[6], VANILLA_NAME_BUFFER[7], VANILLA_NAME_BUFFER[8]);
    ffnx_info("naming_screen_confirm_name: Vanilla cursor pos: %d\n", *VANILLA_NAME_CURSOR_POS);

    // Ensure vanilla's buffer matches ours (should already be synced, but be safe)
    memcpy(VANILLA_NAME_BUFFER, g_naming_state.name_buffer, NAME_MAX_CHARS);
    *VANILLA_NAME_CURSOR_POS = g_naming_state.name_cursor_pos;

    g_naming_state.is_active = false;
    g_jp_naming_screen_active = false;

    // Note: We're NOT writing to savemap ourselves anymore.
    // We return 1 from the keyboard hook, which tells vanilla to finish.
    // Vanilla will then copy VANILLA_NAME_BUFFER (which has our Japanese chars) to savemap.
}

static void naming_screen_set_default_name()
{
    // TODO: Load default name for character
    // For now, just clear both buffers
    memset(g_naming_state.name_buffer, 0xFF, sizeof(g_naming_state.name_buffer));
    g_naming_state.name_cursor_pos = 0;

    // INJECTION: Also clear vanilla's buffer and reset cursor
    memset(VANILLA_NAME_BUFFER, 0xFF, NAME_MAX_CHARS);
    *VANILLA_NAME_CURSOR_POS = 0;

    if (trace_all)
        ffnx_trace("naming_screen_set_default_name: reset to default (synced to vanilla)\n");
}

static void naming_screen_execute_sidebar_action()
{
    switch (g_naming_state.sidebar_cursor) {
        case SIDEBAR_HIRAGANA:
            g_naming_state.current_page = PAGE_HIRAGANA;
            // Don't reset cursor position - just switch page and exit sidebar
            g_naming_state.in_sidebar = false;
            // Clamp Y if switching from eisuu (5 rows) to kana (9 rows) - no issue
            // But clamp if switching TO eisuu would be needed (handled in switch_page)
            break;
        case SIDEBAR_KATAKANA:
            g_naming_state.current_page = PAGE_KATAKANA;
            g_naming_state.in_sidebar = false;
            break;
        case SIDEBAR_EISUU:
            g_naming_state.current_page = PAGE_EISUU;
            g_naming_state.in_sidebar = false;
            // Clamp cursor if coming from kana page with row > 4
            if (g_naming_state.cursor_y >= GRID_ROWS_EISUU) {
                g_naming_state.cursor_y = GRID_ROWS_EISUU - 1;
            }
            break;
        case SIDEBAR_SPACE:
            naming_screen_add_space();
            break;
        case SIDEBAR_DELETE:
            naming_screen_delete_character();
            break;
        case SIDEBAR_CONFIRM:
            naming_screen_confirm_name();
            break;
        case SIDEBAR_DEFAULT:
            naming_screen_set_default_name();
            break;
    }
}

static void naming_screen_handle_confirm()
{
    // SIMPLIFIED (2025-12-13): No sidebar handling - vanilla does that
    // We only handle grid character selection

    uint8_t char_code = naming_screen_get_char_at_cursor();
    ffnx_trace("naming_screen_handle_confirm: Grid select char=0x%02X at (%d,%d)\n",
        char_code, g_naming_state.cursor_x, g_naming_state.cursor_y);

    // Don't add empty cells from the grid (0x3F is ideographic space used as placeholder)
    if (char_code != 0x3F) {
        naming_screen_add_character(char_code);
    }
}

static void naming_screen_handle_cancel()
{
    naming_screen_delete_character();
}

static void naming_screen_process_input()
{
    g_naming_state.frame_counter++;

    // TRACE: Monitor entire buffer for any 0x00 writes (Space character)
    static uint8_t trace_prev_buf[9] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
    for (int i = 0; i < 9; i++) {
        if (VANILLA_NAME_BUFFER[i] != trace_prev_buf[i]) {
            ffnx_info("TRACE: Buffer[%d] changed from 0x%02X to 0x%02X (frame %d)\n",
                i, trace_prev_buf[i], VANILLA_NAME_BUFFER[i], g_naming_state.frame_counter);
            trace_prev_buf[i] = VANILLA_NAME_BUFFER[i];
        }
    }

    // NOTE: 0x00 = バ (ba) which is a VALID character in jafont_1
    // We only replace 0x00 with 0x3F (space) when it's a sidebar Space action
    // NOT for grid selections of バ

    // PASSIVE INJECTION APPROACH (2025-12-13):
    // - Read vanilla's grid cursor position (X/Y) every frame
    // - Sync our grid position with vanilla's
    // - Only handle L1/R1 for page switching (vanilla doesn't use these)
    // - Let vanilla handle ALL other buttons (confirm, cancel, d-pad)
    // - Detect when vanilla adds a character and overwrite with Japanese

    // Read vanilla's current state
    int vanilla_x = *VANILLA_GRID_CURSOR_X;
    int vanilla_y = *VANILLA_GRID_CURSOR_Y;
    int vanilla_name_pos = *VANILLA_NAME_CURSOR_POS;

    // Clamp grid position to valid range for our grid
    if (vanilla_x < 0) vanilla_x = 0;
    if (vanilla_x >= GRID_COLS) vanilla_x = GRID_COLS - 1;
    if (vanilla_y < 0) vanilla_y = 0;

    int max_rows = naming_screen_get_max_rows();
    if (vanilla_y >= max_rows) vanilla_y = max_rows - 1;

    // Update our state to match vanilla's grid cursor
    g_naming_state.cursor_x = vanilla_x;
    g_naming_state.cursor_y = vanilla_y;
    g_naming_state.name_cursor_pos = vanilla_name_pos;

    // Handle input
    ff7_gamepad_status* pad = ff7_externals.gamepad_status;
    if (pad != nullptr) {
        // L1/R1 for page switching - vanilla doesn't use these
        if (naming_screen_check_button_edge(pad->button5 != 0, &g_naming_state.l1_pressed)) {
            naming_screen_switch_page(-1);
        }
        if (naming_screen_check_button_edge(pad->button6 != 0, &g_naming_state.r1_pressed)) {
            naming_screen_switch_page(1);
        }

        // Detect Cancel button press while in grid - we'll undo vanilla's sidebar snap later
        if (naming_screen_check_button_edge(pad->button2 != 0, &g_naming_state.cancel_pressed)) {
            if (g_prev_in_sidebar == 0) {
                // Cancel was pressed while cursor was in grid
                // Start the undo timer
                g_cancel_undo_frames = CANCEL_UNDO_MAX_FRAMES;
                ffnx_info("naming_screen: Cancel pressed while in grid - will undo sidebar snap for %d frames\n", g_cancel_undo_frames);
            }
        }
    }

    // PASSIVE CANCEL HANDLING: Detect and undo vanilla's sidebar snap
    // When Cancel is pressed in grid, vanilla:
    // 1. Deletes a character (decreases name_pos) - this is what we want
    // 2. Snaps cursor to sidebar - this is what we DON'T want
    // We let vanilla do both, then force cursor back to grid for several frames
    int current_in_sidebar = *VANILLA_IN_SIDEBAR_FLAG;
    if (g_cancel_undo_frames > 0) {
        if (current_in_sidebar != 0) {
            // Vanilla put us in sidebar - force back to grid
            *VANILLA_IN_SIDEBAR_FLAG = 0;
            ffnx_info("naming_screen: Forcing cursor back to grid (frames left: %d)\n", g_cancel_undo_frames);
        }
        g_cancel_undo_frames--;
    }

    // DISABLED (2025-12-17): Passive injection overwrite no longer needed.
    // We now write Japanese tables directly to 0x921D70 via naming_screen_write_table_to_grid().
    // Vanilla renders directly from that address, so no buffer overwrite is required.
    // The Space character fix is also handled by HEXT patch 71905E = 3F.
    /*
    // Detect when vanilla added a character (buffer position increased)
    // Then overwrite what vanilla wrote with our Japanese character
    // BUT only if cursor was in the grid, not in sidebar
    //
    // SPECIAL CASE: At position 8 (9th character), vanilla doesn't increment position
    // but still writes a character. We detect this by checking if the buffer changed.
    bool char_added_normally = (g_prev_name_pos >= 0 && vanilla_name_pos > g_prev_name_pos);
    bool char_added_at_pos8 = false;

    // Check for position 8 special case - vanilla wrote but didn't increment
    // This applies to BOTH grid and sidebar actions at position 8
    static uint8_t prev_char_at_8 = 0xFF;
    static bool confirm_was_pressed = false;

    // Track confirm button state
    ff7_gamepad_status* pad_check = ff7_externals.gamepad_status;
    bool confirm_pressed_now = (pad_check != nullptr && pad_check->button3 != 0);
    bool confirm_just_pressed = confirm_pressed_now && !confirm_was_pressed;
    confirm_was_pressed = confirm_pressed_now;

    // Detect position 8 writes for BOTH grid and sidebar actions
    // We need to detect both, then handle them differently below
    if (g_prev_name_pos == 8 && vanilla_name_pos == 8) {
        uint8_t curr_char_at_8 = VANILLA_NAME_BUFFER[8];
        // Trigger if buffer changed (any action - grid or sidebar)
        if (curr_char_at_8 != prev_char_at_8) {
            char_added_at_pos8 = true;
            ffnx_info("naming_screen: Pos8 action - buffer changed from 0x%02X to 0x%02X, prev_sidebar=%d\n",
                prev_char_at_8, curr_char_at_8, g_prev_in_sidebar);
        }
        prev_char_at_8 = curr_char_at_8;
    } else {
        // Reset tracking when not at position 8
        prev_char_at_8 = (vanilla_name_pos >= 8) ? VANILLA_NAME_BUFFER[8] : 0xFF;
    }

    if (char_added_normally || char_added_at_pos8) {
        // Vanilla just added a character at position (vanilla_name_pos - 1)
        int write_pos = g_prev_name_pos;  // Position where vanilla wrote

        ffnx_info("naming_screen: Char added - prev_in_sidebar=%d, prev_grid=(%d,%d), write_pos=%d, new_pos=%d\n",
            g_prev_in_sidebar, g_prev_grid_x, g_prev_grid_y, write_pos, vanilla_name_pos);

        // Check if this was a sidebar action
        // Use g_prev_in_sidebar for both normal and pos8 cases - it was captured last frame
        int sidebar_check = g_prev_in_sidebar;
        if (sidebar_check != 0 && write_pos >= 0 && write_pos < NAME_MAX_CHARS) {
            // Sidebar action - vanilla wrote something
            uint8_t written_char = VANILLA_NAME_BUFFER[write_pos];
            ffnx_info("naming_screen: Sidebar action wrote 0x%02X at pos %d (sidebar_check=%d)\n", written_char, write_pos, sidebar_check);

            // Fix Space: vanilla writes 0x00 which renders as バ in jafont_1
            // Replace with 0x3F (ideographic space)
            if (written_char == 0x00) {
                VANILLA_NAME_BUFFER[write_pos] = 0x3F;
                ffnx_info("naming_screen: Fixed Space - replaced 0x00 with 0x3F\n");
            }
        }
        // Only overwrite with Japanese if cursor WAS in the character grid (g_prev_in_sidebar == 0)
        else if (g_prev_in_sidebar == 0 && write_pos >= 0 && write_pos < NAME_MAX_CHARS) {
            // Get Japanese character based on grid position WHEN confirm was pressed
            int grid_x = g_prev_grid_x;
            int grid_y = g_prev_grid_y;

            ffnx_info("naming_screen: Grid action - attempting overwrite at pos %d, grid=(%d,%d), page=%d\n",
                write_pos, grid_x, grid_y, (int)g_naming_state.current_page);

            // Bounds check Y
            if (grid_y < 0) grid_y = 0;

            uint8_t jp_char = 0xFF;
            switch (g_naming_state.current_page) {
                case PAGE_HIRAGANA:
                    if (grid_y < GRID_ROWS_KANA)
                        jp_char = HIRAGANA_TABLE[grid_y][grid_x];
                    break;
                case PAGE_KATAKANA:
                    if (grid_y < GRID_ROWS_KANA)
                        jp_char = KATAKANA_TABLE[grid_y][grid_x];
                    break;
                case PAGE_EISUU:
                    if (grid_y < GRID_ROWS_EISUU)
                        jp_char = EISUU_TABLE[grid_y][grid_x];
                    break;
            }

            ffnx_info("naming_screen: Grid lookup result: jp_char=0x%02X\n", jp_char);

            // Overwrite vanilla's character with our Japanese character
            // Note: 0x3F is ideographic space - we should overwrite it too since the grid is blanked with 0x3F
            if (jp_char != 0xFF) {
                VANILLA_NAME_BUFFER[write_pos] = jp_char;
                ffnx_info("naming_screen: Overwrote pos %d with char 0x%02X (grid %d,%d)\n",
                    write_pos, jp_char, grid_x, grid_y);
            } else {
                ffnx_info("naming_screen: NOT overwriting - jp_char is 0xFF\n");
            }
        } else {
            ffnx_info("naming_screen: Skipped overwrite - prev_in_sidebar=%d, write_pos=%d, NAME_MAX_CHARS=%d\n",
                g_prev_in_sidebar, write_pos, NAME_MAX_CHARS);
        }
    }
    */

    // Update tracking for next frame (still needed for page indicator display logic)
    g_prev_name_pos = vanilla_name_pos;
    g_prev_grid_x = vanilla_x;
    g_prev_grid_y = vanilla_y;
    g_prev_in_sidebar = *VANILLA_IN_SIDEBAR_FLAG;
}

// ============================================================================
// RENDERING
// ============================================================================

static int naming_screen_get_max_rows()
{
    return (g_naming_state.current_page == PAGE_EISUU) ? GRID_ROWS_EISUU : GRID_ROWS_KANA;
}

static uint8_t naming_screen_get_char_at_cursor()
{
    int row = g_naming_state.cursor_y;
    int col = g_naming_state.cursor_x;

    switch (g_naming_state.current_page) {
        case PAGE_HIRAGANA:
            return HIRAGANA_TABLE[row][col];
        case PAGE_KATAKANA:
            return KATAKANA_TABLE[row][col];
        case PAGE_EISUU:
            return EISUU_TABLE[row][col];
    }
    return 0x3F;
}

static void naming_screen_draw_string(int x, int y, const uint8_t* str, int color)
{
    int pos_x = x;
    while (*str != 0xFF && *str != 0x00) {
        pos_x = common_submit_draw_char_from_buffer_6F564E_jp(pos_x, y, color, *str, NAMING_SCREEN_Z);
        str++;
    }
}

static void naming_screen_draw_character_grid()
{
    const uint8_t (*table)[10];
    int max_rows;

    switch (g_naming_state.current_page) {
        case PAGE_HIRAGANA:
            table = HIRAGANA_TABLE;
            max_rows = GRID_ROWS_KANA;
            break;
        case PAGE_KATAKANA:
            table = KATAKANA_TABLE;
            max_rows = GRID_ROWS_KANA;
            break;
        case PAGE_EISUU:
            table = EISUU_TABLE;
            max_rows = GRID_ROWS_EISUU;
            break;
        default:
            return;
    }

    for (int row = 0; row < max_rows; row++) {
        for (int col = 0; col < GRID_COLS; col++) {
            uint8_t char_code = table[row][col];

            // Skip empty cells
            if (char_code == 0x3F) continue;

            int x = GRID_BASE_X + (col * CELL_WIDTH);
            int y = GRID_BASE_Y + (row * CELL_HEIGHT);

            // Highlight current cursor position
            int color = 0; // Gray/White
            if (!g_naming_state.in_sidebar && row == g_naming_state.cursor_y && col == g_naming_state.cursor_x) {
                color = 5; // Yellow for selected
            }

            common_submit_draw_char_from_buffer_6F564E_jp(x, y, color, char_code, NAMING_SCREEN_Z);
        }
    }
}

static void naming_screen_draw_sidebar()
{
    for (int i = 0; i < SIDEBAR_ITEMS; i++) {
        int x = SIDEBAR_X;
        int y = SIDEBAR_Y + (i * SIDEBAR_ITEM_HEIGHT);

        int color = 0; // Default: Gray/White

        // Highlight logic:
        // - Yellow (5) = currently selected item when cursor is in sidebar
        // - Cyan (6) = current page indicator (top 3 items only)
        // - Gray (0) = everything else

        if (g_naming_state.in_sidebar && i == g_naming_state.sidebar_cursor) {
            color = 5; // Yellow for selected cursor position
        }
        else if (i < 3 && i == (int)g_naming_state.current_page) {
            color = 6; // Cyan for current page indicator
        }

        naming_screen_draw_string(x, y, SIDEBAR_LABELS[i], color);
    }
}

static void naming_screen_draw_name_preview()
{
    int x = 240;
    int y = 130;

    for (int i = 0; i < NAME_MAX_CHARS; i++) {
        uint8_t char_code = g_naming_state.name_buffer[i];

        if (char_code == 0xFF || char_code == 0x00) {
            // Draw underscore placeholder
            common_submit_draw_char_from_buffer_6F564E_jp(x, y, 0, 0x3E, NAMING_SCREEN_Z); // Use minus as placeholder
        } else {
            common_submit_draw_char_from_buffer_6F564E_jp(x, y, 0, char_code, NAMING_SCREEN_Z);
        }
        x += 24;
    }
}

static void naming_screen_draw_page_indicator()
{
    // Draw only the page labels (ひらがな/カタカナ/えいすう) so user knows which page they're on
    // Vanilla sidebar handles Space/Delete/Select/Default
    for (int i = 0; i < 3; i++) {
        int x = SIDEBAR_X;
        int y = SIDEBAR_Y + (i * SIDEBAR_ITEM_HEIGHT);

        // Highlight current page in cyan (6), others in gray (0)
        int color = (i == (int)g_naming_state.current_page) ? 6 : 0;

        naming_screen_draw_string(x, y, SIDEBAR_LABELS[i], color);
    }
}

static void naming_screen_draw()
{
    // Set flag so our draws don't get filtered (kept for safety, though filter is removed)
    g_jp_naming_screen_drawing = true;

    // DISABLED (2025-12-17): Character grid rendering no longer needed.
    // Vanilla now renders directly from 0x921D70 where we write Japanese tables.
    // naming_screen_draw_character_grid();

    // TEMPORARILY RE-ENABLED for debugging - vanilla patches not working yet
    // HEXT patches at 719227=07 and 719237=30 should make vanilla render 7 sidebar items
    // but labels aren't appearing. Using FFNx overlay until we fix vanilla rendering.
    naming_screen_draw_page_indicator();

    // REMOVED: Full sidebar (vanilla handles all 7 items now)
    // REMOVED: Name preview (vanilla handles it)

    g_jp_naming_screen_drawing = false;
}

// ============================================================================
// FORCE-OVERWRITE TICK (Called from main loop)
// ============================================================================

// This function should be called every frame from a main loop hook (e.g., common_flip hook)
// It re-applies our Japanese name to the savemap to counter the game's overwrite
// NOTE (2025-12-13): DISABLED - With injection approach, this is no longer needed.
// Kept for potential future experimentation.
void ff7_naming_screen_force_overwrite_tick()
{
    // DISABLED - injection approach writes directly to vanilla's buffer
    // so vanilla's own save logic preserves our Japanese characters
    /*
    if (g_jp_naming_force_overwrite_frames > 0) {
        g_jp_naming_force_overwrite_frames--;

        if (ff7_externals.savemap != nullptr && g_saved_character_index >= 0 && g_saved_character_index < 9) {
            savemap_char* char_data = &ff7_externals.savemap->chars[g_saved_character_index];
            memcpy(char_data->name, g_saved_name_buffer, 12);

            if (g_jp_naming_force_overwrite_frames % 5 == 0) {
                ffnx_trace("ff7_naming_screen_force_overwrite_tick: Re-applying name, %d frames left\n",
                    g_jp_naming_force_overwrite_frames);
            }
        }
    }
    */
}

// ============================================================================
// INITIALIZATION (Called once at startup)
// ============================================================================

void ff7_naming_screen_init_hook()
{
    // Save the original function pointer before it gets replaced
    g_original_menu_sub_718DBE = (menu_sub_718DBE_func)ff7_externals.menu_sub_718DBE;
    ffnx_info("ff7_naming_screen_init_hook: Saved original menu_sub_718DBE at 0x%08X\n",
        (uint32_t)g_original_menu_sub_718DBE);
}

// ============================================================================
// KEYBOARD INPUT HOOK (Replaces keyboard_name_input)
// ============================================================================

// This runs each frame WHILE the vanilla naming loop is active
// INJECTION APPROACH:
// 1. Collect Japanese character input and write to VANILLA's buffer
// 2. Render our Japanese grid overlay (vanilla's English grid is blanked)
// 3. When user confirms, vanilla copies its buffer (with our Japanese chars) to savemap
// Returns: 0 = continue, 1 = finish (when user confirms)
int ff7_naming_keyboard_input_jp()
{
    static bool initialized = false;
    static int log_counter = 0;

    // Initialize on first call
    if (!initialized) {
        int character_index = 0;
        naming_screen_init(character_index);
        initialized = true;
        log_counter = 0;
        g_jp_naming_screen_active = true;
        ffnx_info("ff7_naming_keyboard_input_jp: Initialized for character %d (INJECTION MODE)\n", character_index);
    }

    log_counter++;

    // Log every 60 frames
    if (log_counter % 60 == 0) {
        ffnx_trace("ff7_naming_keyboard_input_jp: frame=%d, cursor=(%d,%d), in_sidebar=%d, name_pos=%d\n",
            log_counter, g_naming_state.cursor_x, g_naming_state.cursor_y,
            g_naming_state.in_sidebar ? 1 : 0, g_naming_state.name_cursor_pos);
        ffnx_trace("ff7_naming_keyboard_input_jp: vanilla_buffer=%02X %02X %02X %02X, vanilla_cursor=%d\n",
            VANILLA_NAME_BUFFER[0], VANILLA_NAME_BUFFER[1], VANILLA_NAME_BUFFER[2], VANILLA_NAME_BUFFER[3],
            *VANILLA_NAME_CURSOR_POS);
    }

    // Process our Japanese input (writes to both our buffer AND vanilla's buffer)
    naming_screen_process_input();

    // Render our Japanese grid (overlay on the vanilla screen)
    naming_screen_draw();

    // Check if user confirmed via our Japanese system
    if (!g_naming_state.is_active) {
        // User pressed confirm in our system
        ffnx_info("ff7_naming_keyboard_input_jp: User confirmed! (INJECTION MODE)\n");
        ffnx_info("ff7_naming_keyboard_input_jp: Our buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
            g_naming_state.name_buffer[0], g_naming_state.name_buffer[1], g_naming_state.name_buffer[2],
            g_naming_state.name_buffer[3], g_naming_state.name_buffer[4], g_naming_state.name_buffer[5],
            g_naming_state.name_buffer[6], g_naming_state.name_buffer[7], g_naming_state.name_buffer[8]);
        ffnx_info("ff7_naming_keyboard_input_jp: Vanilla buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
            VANILLA_NAME_BUFFER[0], VANILLA_NAME_BUFFER[1], VANILLA_NAME_BUFFER[2],
            VANILLA_NAME_BUFFER[3], VANILLA_NAME_BUFFER[4], VANILLA_NAME_BUFFER[5],
            VANILLA_NAME_BUFFER[6], VANILLA_NAME_BUFFER[7], VANILLA_NAME_BUFFER[8]);

        // With injection approach, vanilla will now copy VANILLA_NAME_BUFFER to savemap
        // We don't need to do anything else - the Japanese chars are already in vanilla's buffer!

        // Reset state for next time
        initialized = false;
        g_jp_naming_screen_active = false;

        // Reset page to Hiragana and write to grid memory BEFORE returning
        // This ensures the next naming screen entry shows Hiragana immediately,
        // even before our init runs (vanilla renders first frame before calling us)
        g_naming_state.current_page = PAGE_HIRAGANA;
        naming_screen_write_table_to_grid();
        ffnx_info("ff7_naming_keyboard_input_jp: Reset grid to Hiragana for next entry\n");

        return 1; // Tell vanilla to finish - it will save our Japanese name!
    }

    return 0; // Continue - vanilla will keep calling us
}

// ============================================================================
// MAIN ENTRY POINT (Post-Hook Pattern for menu_sub_718DBE)
// ============================================================================

// This function replaces menu_sub_718DBE using the POST-HOOK pattern:
// 1. Call the original vanilla function (which calls our hooked keyboard_name_input)
// 2. While vanilla runs, our keyboard hook collects Japanese input each frame
// 3. When user confirms, our keyboard hook returns 1, vanilla finishes
// 4. Vanilla writes its (empty/garbage) buffer to savemap
// 5. AFTER vanilla returns, we overwrite savemap with our Japanese buffer
void ff7_naming_screen_jp()
{
    ffnx_info("ff7_naming_screen_jp: POST-HOOK - Entering wrapper\n");

    // Get character index (TODO: get from game state)
    int character_index = 0;

    // Step 1: Call the ORIGINAL vanilla function
    // This runs the naming screen loop. It will call our hooked keyboard_name_input
    // each frame, which collects Japanese input. When user confirms, our hook returns 1.
    // Vanilla then writes its buffer to savemap and returns here.
    if (g_original_menu_sub_718DBE != nullptr) {
        ffnx_info("ff7_naming_screen_jp: Calling original menu_sub_718DBE...\n");
        g_original_menu_sub_718DBE();
        ffnx_info("ff7_naming_screen_jp: Original function returned\n");
    } else {
        ffnx_error("ff7_naming_screen_jp: Original function pointer is NULL!\n");
        return;
    }

    // Step 2: POST-HOOK - Overwrite savemap with our Japanese name
    // The vanilla function just finished and wrote garbage to savemap.
    // Our Japanese buffer was collected by ff7_naming_keyboard_input_jp.
    ffnx_info("ff7_naming_screen_jp: POST-HOOK - Overwriting with Japanese name\n");
    ffnx_info("ff7_naming_screen_jp: Japanese buffer: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
        g_naming_state.name_buffer[0], g_naming_state.name_buffer[1], g_naming_state.name_buffer[2],
        g_naming_state.name_buffer[3], g_naming_state.name_buffer[4], g_naming_state.name_buffer[5],
        g_naming_state.name_buffer[6], g_naming_state.name_buffer[7], g_naming_state.name_buffer[8]);

    if (ff7_externals.savemap != nullptr && character_index >= 0 && character_index < 9) {
        savemap_char* char_data = &ff7_externals.savemap->chars[character_index];

        // Log what the vanilla function wrote (for debugging)
        ffnx_info("ff7_naming_screen_jp: Vanilla wrote: %02X %02X %02X %02X %02X %02X %02X %02X %02X\n",
            (uint8_t)char_data->name[0], (uint8_t)char_data->name[1], (uint8_t)char_data->name[2],
            (uint8_t)char_data->name[3], (uint8_t)char_data->name[4], (uint8_t)char_data->name[5],
            (uint8_t)char_data->name[6], (uint8_t)char_data->name[7], (uint8_t)char_data->name[8]);

        // Overwrite with our Japanese name
        memcpy(char_data->name, g_naming_state.name_buffer, 12);
        ffnx_info("ff7_naming_screen_jp: Japanese name written to savemap!\n");
    }

    g_jp_naming_screen_active = false;
    ffnx_info("ff7_naming_screen_jp: POST-HOOK - Complete\n");
}
