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

#include "portrait_manager.h"
#include "../log.h"
#include "../cfg.h"
#include "../renderer.h"
#include "../globals.h"
#include <filesystem>

namespace FFNx
{
    // Static member initialization
    std::map<int, std::map<int, bgfx::TextureHandle>> PortraitManager::portrait_cache;
    bgfx::TextureHandle PortraitManager::fallback_portrait = BGFX_INVALID_HANDLE;
    bool PortraitManager::is_initialized = false;

    void PortraitManager::init()
    {
        if (is_initialized)
        {
            ffnx_warning("PortraitManager::init: Already initialized\n");
            return;
        }

        ffnx_info("PortraitManager::init: Initializing character portrait system\n");

        // Clear any existing cache
        portrait_cache.clear();
        fallback_portrait = BGFX_INVALID_HANDLE;

        // Load fallback portrait (generic silhouette)
        char fallback_path[512];
        snprintf(fallback_path, sizeof(fallback_path), "%s/%s/unknown_npc.png",
                 basedir, portrait_texture_path.c_str());

        uint32_t width, height, mipCount;
        fallback_portrait = newRenderer.createTextureHandle(fallback_path, &width, &height, &mipCount, true);

        if (!bgfx::isValid(fallback_portrait))
        {
            ffnx_warning("PortraitManager::init: Failed to load fallback portrait from %s\n", fallback_path);
        }
        else
        {
            ffnx_info("PortraitManager::init: Loaded fallback portrait (%ux%u)\n", width, height);
        }

        is_initialized = true;
    }

    bgfx::TextureHandle PortraitManager::get_portrait(int character_id, int expression)
    {
        if (!is_initialized)
        {
            ffnx_error("PortraitManager::get_portrait: Manager not initialized\n");
            return fallback_portrait;
        }

        // Check cache first
        auto char_it = portrait_cache.find(character_id);
        if (char_it != portrait_cache.end())
        {
            auto expr_it = char_it->second.find(expression);
            if (expr_it != char_it->second.end() && bgfx::isValid(expr_it->second))
            {
                return expr_it->second;
            }
        }

        // Not in cache, try to load
        bgfx::TextureHandle handle = load_portrait_texture(character_id, expression);

        if (bgfx::isValid(handle))
        {
            // Cache the loaded texture
            portrait_cache[character_id][expression] = handle;
            return handle;
        }

        // If default expression failed, return fallback
        if (expression == 0)
        {
            ffnx_warning("PortraitManager::get_portrait: No portrait found for character %d, using fallback\n", character_id);
            return fallback_portrait;
        }

        // Try default expression instead
        ffnx_warning("PortraitManager::get_portrait: Expression %d not found for character %d, falling back to default\n",
                     expression, character_id);
        return get_portrait(character_id, 0);
    }

    void PortraitManager::preload_party_portraits()
    {
        if (!is_initialized)
        {
            ffnx_error("PortraitManager::preload_party_portraits: Manager not initialized\n");
            return;
        }

        ffnx_info("PortraitManager::preload_party_portraits: Preloading party member portraits\n");

        // Preload default expression for all 9 party members
        for (int char_id = 0; char_id <= 8; char_id++)
        {
            bgfx::TextureHandle handle = get_portrait(char_id, 0); // Expression 0 = default
            if (bgfx::isValid(handle))
            {
                ffnx_info("PortraitManager::preload_party_portraits: Loaded portrait for %s\n",
                         get_character_name(char_id));
            }
            else
            {
                ffnx_warning("PortraitManager::preload_party_portraits: Failed to load portrait for %s\n",
                            get_character_name(char_id));
            }
        }
    }

    void PortraitManager::shutdown()
    {
        if (!is_initialized)
        {
            return;
        }

        ffnx_info("PortraitManager::shutdown: Cleaning up portrait system\n");

        // Destroy all cached textures
        for (auto& char_pair : portrait_cache)
        {
            for (auto& expr_pair : char_pair.second)
            {
                if (bgfx::isValid(expr_pair.second))
                {
                    bgfx::destroy(expr_pair.second);
                }
            }
        }

        // Destroy fallback texture
        if (bgfx::isValid(fallback_portrait))
        {
            bgfx::destroy(fallback_portrait);
            fallback_portrait = BGFX_INVALID_HANDLE;
        }

        portrait_cache.clear();
        is_initialized = false;
    }

    bool PortraitManager::has_portrait(int character_id, int expression)
    {
        char path[512];
        build_portrait_path(character_id, expression, path);
        return std::filesystem::exists(path);
    }

    bgfx::TextureHandle PortraitManager::load_portrait_texture(int character_id, int expression)
    {
        char path[512];
        build_portrait_path(character_id, expression, path);

        // Check if file exists
        if (!std::filesystem::exists(path))
        {
            if (trace_all || trace_renderer)
            {
                ffnx_trace("PortraitManager::load_portrait_texture: Portrait not found: %s\n", path);
            }
            return BGFX_INVALID_HANDLE;
        }

        // Load texture using renderer
        uint32_t width, height, mipCount;
        bgfx::TextureHandle handle = newRenderer.createTextureHandle(path, &width, &height, &mipCount, true);

        if (bgfx::isValid(handle))
        {
            ffnx_info("PortraitManager::load_portrait_texture: Loaded %s (%ux%u)\n", path, width, height);
        }
        else
        {
            ffnx_warning("PortraitManager::load_portrait_texture: Failed to load %s\n", path);
        }

        return handle;
    }

    const char* PortraitManager::get_character_name(int character_id)
    {
        static const char* names[] = {
            "cloud",     // 0
            "barret",    // 1
            "tifa",      // 2
            "aerith",    // 3
            "red_xiii",  // 4
            "yuffie",    // 5
            "cait_sith", // 6
            "vincent",   // 7
            "cid"        // 8
        };

        if (character_id >= 0 && character_id <= 8)
        {
            return names[character_id];
        }

        return "unknown";
    }

    const char* PortraitManager::get_expression_name(int expression)
    {
        static const char* expressions[] = {
            "default",   // 0
            "angry",     // 1
            "happy",     // 2
            "sad",       // 3
            "surprised"  // 4
        };

        if (expression >= 0 && expression <= 4)
        {
            return expressions[expression];
        }

        return "default";
    }

    void PortraitManager::build_portrait_path(int character_id, int expression, char* out_path)
    {
        const char* char_name = get_character_name(character_id);
        const char* expr_name = get_expression_name(expression);

        snprintf(out_path, 512, "%s/%s/%s_%s.png",
                 basedir,
                 portrait_texture_path.c_str(),
                 char_name,
                 expr_name);
    }
}
