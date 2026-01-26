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

#include "speaker_inference.h"
#include "../log.h"
#include "../cfg.h"
#include "../globals.h"
#include "../ff7.h"
#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace FFNx
{
    // Static member initialization
    std::map<std::string, std::map<int, int>> SpeakerInference::manual_overrides;
    bool SpeakerInference::is_initialized = false;

    void SpeakerInference::init()
    {
        if (is_initialized)
        {
            ffnx_warning("SpeakerInference::init: Already initialized\n");
            return;
        }

        ffnx_info("SpeakerInference::init: Initializing speaker inference system\n");

        manual_overrides.clear();

        // Load manual overrides if config file exists
        char config_path[512];
        snprintf(config_path, sizeof(config_path), "%s/%s",
                 basedir, portrait_override_config.c_str());

        if (std::filesystem::exists(config_path))
        {
            load_overrides(config_path);
        }
        else
        {
            ffnx_info("SpeakerInference::init: No override config found at %s (this is normal)\n", config_path);
        }

        is_initialized = true;
    }

    SpeakerInference::SpeakerInfo SpeakerInference::infer_speaker(int window_id, float box_x, float box_y)
    {
        SpeakerInfo info;
        info.character_id = -1;
        info.screen_x = box_x;
        info.screen_y = box_y;
        info.confidence = 0.0f;

        if (!is_initialized)
        {
            ffnx_error("SpeakerInference::infer_speaker: System not initialized\n");
            return info;
        }

        // Priority 1: Check manual override
        // TODO: Get current field ID from game state
        // For now, we'll skip this and implement it when we have field ID access
        // int manual_id = get_manual_override(current_field_id, window_id);
        // if (manual_id >= 0) { ... }

        // Priority 2: Check field entity association
        if (ff7_externals.field_text_box_window_entity_id_CC0960 != nullptr)
        {
            int entity_id = ff7_externals.field_text_box_window_entity_id_CC0960[window_id];
            if (entity_id >= 0 && entity_id < 256)
            {
                info.character_id = entity_to_character_id(entity_id);
                info.confidence = 0.8f; // High confidence from entity association

                if (trace_all)
                {
                    ffnx_trace("SpeakerInference::infer_speaker: Entity %d -> Character %d\n",
                              entity_id, info.character_id);
                }

                return info;
            }
        }

        // Priority 3: Fallback to party leader
        info.character_id = get_party_leader();
        info.confidence = 0.3f; // Low confidence fallback

        if (trace_all)
        {
            ffnx_warning("SpeakerInference::infer_speaker: No entity found, using party leader %d\n",
                        info.character_id);
        }

        return info;
    }

    int SpeakerInference::get_manual_override(const char* field_id, int window_id)
    {
        auto field_it = manual_overrides.find(field_id);
        if (field_it != manual_overrides.end())
        {
            auto window_it = field_it->second.find(window_id);
            if (window_it != field_it->second.end())
            {
                return window_it->second;
            }
        }
        return -1;
    }

    void SpeakerInference::load_overrides(const char* config_path)
    {
        try
        {
            std::ifstream file(config_path);
            if (!file.is_open())
            {
                ffnx_warning("SpeakerInference::load_overrides: Could not open %s\n", config_path);
                return;
            }

            json config = json::parse(file);

            if (config.contains("fields") && config["fields"].is_object())
            {
                for (auto& [field_id, field_data] : config["fields"].items())
                {
                    if (field_data.contains("boxes") && field_data["boxes"].is_array())
                    {
                        for (auto& box : field_data["boxes"])
                        {
                            if (box.contains("window_id") && box.contains("character_id"))
                            {
                                int window_id = box["window_id"].get<int>();
                                int character_id = box["character_id"].get<int>();
                                manual_overrides[field_id][window_id] = character_id;

                                ffnx_info("SpeakerInference::load_overrides: %s window %d -> character %d\n",
                                         field_id.c_str(), window_id, character_id);
                            }
                        }
                    }
                }
            }

            ffnx_info("SpeakerInference::load_overrides: Loaded %zu field overrides\n", manual_overrides.size());
        }
        catch (const std::exception& e)
        {
            ffnx_error("SpeakerInference::load_overrides: JSON parse error: %s\n", e.what());
        }
    }

    void SpeakerInference::shutdown()
    {
        if (!is_initialized)
        {
            return;
        }

        ffnx_info("SpeakerInference::shutdown: Cleaning up speaker inference system\n");
        manual_overrides.clear();
        is_initialized = false;
    }

    int SpeakerInference::find_closest_character(float screen_x, float screen_y)
    {
        // TODO: Implement field entity proximity detection
        // This would require access to field entity screen positions
        // For Phase 1, we'll rely on entity ID association instead
        return -1;
    }

    int SpeakerInference::entity_to_character_id(int entity_id)
    {
        // Entity ID to character ID mapping
        // In FF7, entity IDs 0-8 typically correspond to party members
        // This is a simplified mapping that works for most cases

        // For field entities, we need to check if they're party members
        // Party member entity IDs map directly to character IDs in most fields
        if (entity_id >= 0 && entity_id <= 8)
        {
            return entity_id;
        }

        // For NPC entities, we assign IDs starting from 100
        // In a full implementation, this would map to specific NPC portraits
        return 100 + (entity_id % 100);
    }

    int SpeakerInference::get_party_leader()
    {
        // Get first party member (leader)
        if (ff7_externals.savemap != nullptr && ff7_externals.savemap->party_members[0] < 9)
        {
            return ff7_externals.savemap->party_members[0];
        }

        // Default to Cloud if we can't determine party leader
        return 0;
    }
}
