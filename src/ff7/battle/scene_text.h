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
//    Multi-Language Scene Text System
//    =================================
//    Created: 2025-12-26 19:30 JST
//    Updated: 2025-12-28 12:25 JST - Simplified API
//    Session: 2e703ab4-4b5e-4772-8894-ba089b4f437c
//    Author: Claude Code
//
//    Provides runtime enemy/attack name injection for multi-language support.
//    Called from load_scene_bin_chunk in battle.cpp after scene data is loaded.
//
/****************************************************************************/

#pragma once

#include <string>
#include <cstdint>

namespace ff7::battle
{
    // Constants matching extract_scene_text.py
    constexpr int SCENE_COUNT = 256;
    constexpr int ENEMY_COUNT = 3;
    constexpr int ATTACK_COUNT = 32;
    constexpr int NAME_SIZE_EN = 32;
    constexpr int NAME_SIZE_JA = 16;

    // .dat file header
    struct SceneTextHeader
    {
        char magic[4];      // "ET01"
        uint16_t version;   // 1
        uint16_t flags;     // 1 = Japanese (16-byte names)
        uint32_t scene_count;
    };

    // Scene text data for one scene (using 32-byte names for EN/DE/FR/ES)
    struct SceneTextData
    {
        char enemy_names[ENEMY_COUNT][NAME_SIZE_EN];
        char attack_names[ATTACK_COUNT][NAME_SIZE_EN];
    };

    // Japanese scene text (16-byte names)
    struct SceneTextDataJA
    {
        char enemy_names[ENEMY_COUNT][NAME_SIZE_JA];
        char attack_names[ATTACK_COUNT][NAME_SIZE_JA];
    };

    // Language text database
    struct LanguageTextData
    {
        bool loaded;
        bool is_japanese;
        SceneTextData scenes[SCENE_COUNT];
    };

    // Initialize scene text system - call at startup
    void init_scene_text();

    // Load text data for a specific language
    bool load_language_text(const std::string& lang_code);

    // Get enemy name for current scene/enemy index
    // Returns pointer to localized name, or nullptr if using default
    const char* get_localized_enemy_name(int scene_id, int enemy_index);

    // Get attack name for current scene/attack index
    const char* get_localized_attack_name(int scene_id, int attack_index);

    // Check if scene text injection is needed for current language
    bool needs_text_injection();

    // Performs the actual injection into the scene buffer
    // Called from load_scene_bin_chunk in battle.cpp
    void inject_scene_text();
}
