/****************************************************************************/
//    Copyright (C) 2026 FFNx Project                                       //
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

#pragma once

#include <map>
#include <string>
#include <bgfx/bgfx.h>

namespace FFNx
{
    /**
     * @brief Character Portrait Manager
     *
     * Manages loading, caching, and retrieval of character portrait textures
     * for the dialogue box portrait system.
     *
     * Character IDs:
     *  - 0-8: Main party members (Cloud, Barret, Tifa, Aerith, Red XIII, Yuffie, Cait Sith, Vincent, Cid)
     *  - 100+: NPCs (dynamically assigned based on field entity)
     *
     * Expression IDs:
     *  - 0: default (neutral)
     *  - 1: angry
     *  - 2: happy
     *  - 3: sad
     *  - 4: surprised
     */
    class PortraitManager
    {
    public:
        /**
         * @brief Initialize the portrait manager
         *
         * Must be called during FFNx initialization, before any portraits are requested.
         * Loads configuration and prepares the cache.
         */
        static void init();

        /**
         * @brief Get portrait texture handle for character and expression
         *
         * @param character_id Character ID (0-8 for party, 100+ for NPCs)
         * @param expression Expression ID (0-4)
         * @return bgfx::TextureHandle Handle to portrait texture, or fallback if not found
         */
        static bgfx::TextureHandle get_portrait(int character_id, int expression);

        /**
         * @brief Preload portraits for all main party members
         *
         * Called during field initialization to avoid hitches when portraits
         * first appear. Loads default expressions for all party members.
         */
        static void preload_party_portraits();

        /**
         * @brief Shutdown and cleanup portrait system
         *
         * Frees all cached textures and releases resources.
         */
        static void shutdown();

        /**
         * @brief Check if a specific portrait exists
         *
         * @param character_id Character ID
         * @param expression Expression ID
         * @return true if portrait file exists, false otherwise
         */
        static bool has_portrait(int character_id, int expression);

    private:
        /**
         * @brief Load portrait texture from disk
         *
         * @param character_id Character ID
         * @param expression Expression ID
         * @return bgfx::TextureHandle Loaded texture handle, or invalid handle on failure
         */
        static bgfx::TextureHandle load_portrait_texture(int character_id, int expression);

        /**
         * @brief Get character name string from ID
         *
         * @param character_id Character ID (0-8)
         * @return const char* Character name (lowercase)
         */
        static const char* get_character_name(int character_id);

        /**
         * @brief Get expression name string from ID
         *
         * @param expression Expression ID (0-4)
         * @return const char* Expression name
         */
        static const char* get_expression_name(int expression);

        /**
         * @brief Build file path for portrait texture
         *
         * @param character_id Character ID
         * @param expression Expression ID
         * @param out_path Output buffer for file path (min 512 bytes)
         */
        static void build_portrait_path(int character_id, int expression, char* out_path);

        // Portrait cache: [character_id][expression] -> texture handle
        static std::map<int, std::map<int, bgfx::TextureHandle>> portrait_cache;

        // Fallback portrait for unknown characters
        static bgfx::TextureHandle fallback_portrait;

        // Initialization flag
        static bool is_initialized;
    };
}
