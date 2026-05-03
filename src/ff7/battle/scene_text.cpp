/****************************************************************************/
//    Copyright (C) 2024 FFNx Team                                          //
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
//
//    Multi-Language Scene Text Implementation
//    =========================================
//    Created: 2025-12-26 19:35 JST
//    Updated: 2025-12-28 20:25 JST - FIXED: Correct RAM addresses from Cheat Engine discovery
//    Session: 2e703ab4-4b5e-4772-8894-ba089b4f437c
//    Author: Claude Code
//
//    Strategy: Inject directly to the RAM addresses where enemy names are stored.
//    Addresses discovered via Cheat Engine memory search during live gameplay:
//    - Enemy 1: 0x9A8E9C
//    - Enemy 2: 0x9A8F54
//    - Enemy 3: 0x9A900C
//    Spacing: 184 bytes (0xB8) - full enemy record size, not 32-byte name size.
//
/****************************************************************************/

#include "scene_text.h"
#include "../../globals.h"
#include "../../log.h"
#include <cstdio>
#include <cstring>

namespace ff7::battle
{
    // Static storage for loaded text data
    static LanguageTextData g_language_text = { false, false, {} };
    static bool g_initialized = false;

    // Enemy name RAM addresses - discovered via Cheat Engine (2025-12-28)
    // Verified: manual edits at these addresses change displayed names in-game
    constexpr uint32_t ENEMY_NAME_ADDR_1 = 0x9A8E9C;  // Enemy 1 name
    constexpr uint32_t ENEMY_NAME_ADDR_2 = 0x9A8F54;  // Enemy 2 name (Guard Hound confirmed)
    constexpr uint32_t ENEMY_NAME_ADDR_3 = 0x9A900C;  // Enemy 3 name
    constexpr uint32_t ENEMY_RECORD_SIZE = 184;       // 0xB8 bytes between enemy records

    // Attack name addresses - TODO: Need Cheat Engine verification
    // These are ESTIMATED based on scene file structure, may need adjustment
    constexpr uint32_t ATTACK_NAMES_BASE = 0x9A9234;  // Estimated: after 3 enemy records
    // Note: Attack names in file are at offset 0x0880, but RAM layout differs

    void init_scene_text()
    {
        ffnx_info("[MLANG-INIT] init_scene_text called: ff7_language='%s', g_initialized=%d\n",
            ff7_language.c_str(), g_initialized);

        if (g_initialized)
            return;

        g_initialized = true;
        memset(&g_language_text, 0, sizeof(g_language_text));

        bool needs_inject = needs_text_injection();
        ffnx_info("[MLANG-INIT] needs_text_injection() = %d\n", needs_inject);

        // Only load text data if we need injection (DE/FR/ES using English scene.bin)
        if (needs_inject)
        {
            ffnx_info("[MLANG-INIT] Attempting to load text for language '%s'\n", ff7_language.c_str());
            if (!ff7_language.empty())
            {
                bool loaded = load_language_text(ff7_language);
                ffnx_info("[MLANG-INIT] load_language_text returned: %d\n", loaded);
                if (loaded)
                {
                    ffnx_info("[MLANG-INIT] SUCCESS: Loaded %s language text for injection\n", ff7_language.c_str());
                }
                else
                {
                    ffnx_warning("[MLANG-INIT] FAILED: Could not load %s language text\n", ff7_language.c_str());
                }
            }
        }
        else
        {
            if (trace_all || trace_files)
                ffnx_trace("Scene text: Injection not needed for language '%s'\n", ff7_language.c_str());
        }
    }

    bool needs_text_injection()
    {
        // Text injection is needed for DE/FR/ES because they use English scene.bin
        // (their native scene.bin has incompatible block structure)
        if (ff7_language == "de" || ff7_language == "fr" || ff7_language == "es")
            return true;
        return false;
    }

    bool load_language_text(const std::string& lang_code)
    {
        char filepath[1024];

        // Try multiple possible locations for the .dat file
        const char* paths[] = {
            "%s/data/lang-%s/battle/enemy_text_%s.dat",
            "%s/mods/language/enemy_text_%s.dat",
            "%s/enemy_text_%s.dat"
        };

        FILE* fd = nullptr;

        // Try language-specific path first
        _snprintf(filepath, sizeof(filepath), paths[0], basedir, lang_code.c_str(), lang_code.c_str());
        fd = fopen(filepath, "rb");

        if (!fd)
        {
            // Try mods folder
            _snprintf(filepath, sizeof(filepath), paths[1], basedir, lang_code.c_str());
            fd = fopen(filepath, "rb");
        }

        if (!fd)
        {
            // Try basedir directly
            _snprintf(filepath, sizeof(filepath), paths[2], basedir, lang_code.c_str());
            fd = fopen(filepath, "rb");
        }

        if (!fd)
        {
            ffnx_warning("Scene text: Could not find enemy_text_%s.dat in any location\n", lang_code.c_str());
            return false;
        }

        if (trace_all || trace_files)
            ffnx_trace("Scene text: Loading from %s\n", filepath);

        // Read and validate header
        SceneTextHeader header;
        if (fread(&header, sizeof(header), 1, fd) != 1)
        {
            ffnx_error("Scene text: Failed to read header\n");
            fclose(fd);
            return false;
        }

        // Validate magic
        if (memcmp(header.magic, "ET01", 4) != 0)
        {
            ffnx_error("Scene text: Invalid magic (expected ET01)\n");
            fclose(fd);
            return false;
        }

        // Validate version
        if (header.version != 1)
        {
            ffnx_error("Scene text: Unsupported version %d\n", header.version);
            fclose(fd);
            return false;
        }

        // Check if Japanese format
        g_language_text.is_japanese = (header.flags & 1) != 0;

        if (header.scene_count != SCENE_COUNT)
        {
            ffnx_warning("Scene text: Expected %d scenes, got %d\n", SCENE_COUNT, header.scene_count);
        }

        // Read scene data
        int scenes_to_read = (header.scene_count < SCENE_COUNT) ? header.scene_count : SCENE_COUNT;

        if (g_language_text.is_japanese)
        {
            // Japanese uses 16-byte names, need to convert to 32-byte format
            SceneTextDataJA temp_scene;
            for (int i = 0; i < scenes_to_read; i++)
            {
                if (fread(&temp_scene, sizeof(temp_scene), 1, fd) != 1)
                {
                    ffnx_error("Scene text: Failed to read scene %d\n", i);
                    fclose(fd);
                    return false;
                }

                // Convert 16-byte to 32-byte format (pad with 0xFF)
                for (int j = 0; j < ENEMY_COUNT; j++)
                {
                    memcpy(g_language_text.scenes[i].enemy_names[j], temp_scene.enemy_names[j], NAME_SIZE_JA);
                    memset(g_language_text.scenes[i].enemy_names[j] + NAME_SIZE_JA, 0xFF, NAME_SIZE_EN - NAME_SIZE_JA);
                }
                for (int j = 0; j < ATTACK_COUNT; j++)
                {
                    memcpy(g_language_text.scenes[i].attack_names[j], temp_scene.attack_names[j], NAME_SIZE_JA);
                    memset(g_language_text.scenes[i].attack_names[j] + NAME_SIZE_JA, 0xFF, NAME_SIZE_EN - NAME_SIZE_JA);
                }
            }
        }
        else
        {
            // Western languages use 32-byte names directly
            for (int i = 0; i < scenes_to_read; i++)
            {
                if (fread(&g_language_text.scenes[i], sizeof(SceneTextData), 1, fd) != 1)
                {
                    ffnx_error("Scene text: Failed to read scene %d\n", i);
                    fclose(fd);
                    return false;
                }
            }
        }

        fclose(fd);
        g_language_text.loaded = true;

        ffnx_info("Scene text: Successfully loaded %d scenes from %s\n", scenes_to_read, filepath);
        return true;
    }

    const char* get_localized_enemy_name(int scene_id, int enemy_index)
    {
        if (!g_language_text.loaded)
            return nullptr;

        if (scene_id < 0 || scene_id >= SCENE_COUNT)
            return nullptr;

        if (enemy_index < 0 || enemy_index >= ENEMY_COUNT)
            return nullptr;

        return g_language_text.scenes[scene_id].enemy_names[enemy_index];
    }

    const char* get_localized_attack_name(int scene_id, int attack_index)
    {
        if (!g_language_text.loaded)
            return nullptr;

        if (scene_id < 0 || scene_id >= SCENE_COUNT)
            return nullptr;

        if (attack_index < 0 || attack_index >= ATTACK_COUNT)
            return nullptr;

        return g_language_text.scenes[scene_id].attack_names[attack_index];
    }

    // Called from battle.cpp -> load_scene_bin_chunk
    // Injects localized enemy names directly to the RAM addresses where the game reads them.
    // These addresses were discovered via Cheat Engine and verified by manual memory edits.
    void inject_scene_text()
    {
        if (!g_language_text.loaded || !needs_text_injection())
        {
            return;
        }

        // Get current battle formation ID
        uint16_t formation_id = ff7_externals.modules_global_object->battle_id;

        // Convert formation ID to scene ID (4 formations per scene)
        uint16_t scene_id = formation_id / 4;

        if (scene_id >= SCENE_COUNT)
        {
            ffnx_warning("[MLANG-BATTLE] Invalid scene_id %d (from formation %d)\n", scene_id, formation_id);
            return;
        }

        // Calculate expected block for this scene (for debugging)
        // EN/JA: scene 11 -> block 0 (12 scenes per block)
        // DE/FR/ES: scene 11 -> block 1 (11 scenes per block)
        int expected_block_en = scene_id / 12;
        int expected_block_de = scene_id / 11;

        // [MLANG-BATTLE] prefix for battle/scene ID logging
        ffnx_info("[MLANG-BATTLE] Battle started: formation_id=%d, scene_id=%d, expected_block_EN=%d, expected_block_DE=%d\n",
            formation_id, scene_id, expected_block_en, expected_block_de);

        // Enemy name RAM addresses - verified via Cheat Engine
        // These are DIRECT memory addresses, not offsets from a buffer
        const uint32_t enemy_name_addrs[ENEMY_COUNT] = {
            ENEMY_NAME_ADDR_1,  // 0x9A8E9C - Enemy 1
            ENEMY_NAME_ADDR_2,  // 0x9A8F54 - Enemy 2
            ENEMY_NAME_ADDR_3   // 0x9A900C - Enemy 3
        };

        // Inject enemy names directly to RAM
        for (int i = 0; i < ENEMY_COUNT; i++)
        {
            const char* localized_name = get_localized_enemy_name(scene_id, i);

            // Only overwrite if we have a valid name (not null, not starting with 0xFF)
            if (localized_name && localized_name[0] != (char)0xFF)
            {
                char* dest = (char*)enemy_name_addrs[i];
                memcpy(dest, localized_name, NAME_SIZE_EN);

                if (trace_all || trace_battle_text)
                {
                    ffnx_trace("Scene text: Injected enemy %d name at 0x%08X\n", i, enemy_name_addrs[i]);
                }
            }
        }

        // Attack names - using estimated address (may need Cheat Engine verification)
        // TODO: If attack names don't work, use Cheat Engine to find correct addresses
        for (int i = 0; i < ATTACK_COUNT; i++)
        {
            const char* localized_attack = get_localized_attack_name(scene_id, i);

            if (localized_attack && localized_attack[0] != (char)0xFF)
            {
                char* dest = (char*)(ATTACK_NAMES_BASE + (i * NAME_SIZE_EN));
                memcpy(dest, localized_attack, NAME_SIZE_EN);
            }
        }

        ffnx_info("[MLANG-INJECT] Injection complete for scene %d\n", scene_id);
    }
}
