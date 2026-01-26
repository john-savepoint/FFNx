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

namespace FFNx
{
    /**
     * @brief Speaker Inference Engine
     *
     * Determines which character is speaking based on dialogue box position,
     * game state, field entity proximity, and manual override configuration.
     */
    class SpeakerInference
    {
    public:
        /**
         * @brief Information about the inferred speaker
         */
        struct SpeakerInfo
        {
            int character_id;       // Character ID (0-8 for party, 100+ for NPCs)
            float screen_x;         // Speaker's screen position X
            float screen_y;         // Speaker's screen position Y
            float confidence;       // Confidence score (0.0-1.0)
        };

        /**
         * @brief Initialize speaker inference system
         *
         * Loads manual override configuration and prepares the system.
         */
        static void init();

        /**
         * @brief Infer speaker from dialogue box and game state
         *
         * @param window_id Dialogue window ID (0-15)
         * @param box_x Dialogue box X position on screen
         * @param box_y Dialogue box Y position on screen
         * @return SpeakerInfo Information about the inferred speaker
         */
        static SpeakerInfo infer_speaker(int window_id, float box_x, float box_y);

        /**
         * @brief Get manual override for specific field and window
         *
         * @param field_id Field ID string (e.g., "mds7st1")
         * @param window_id Dialogue window ID
         * @return int Character ID from override, or -1 if no override exists
         */
        static int get_manual_override(const char* field_id, int window_id);

        /**
         * @brief Load manual override configuration from JSON file
         *
         * @param config_path Path to portrait_overrides.json
         */
        static void load_overrides(const char* config_path);

        /**
         * @brief Shutdown and cleanup speaker inference system
         */
        static void shutdown();

    private:
        /**
         * @brief Find closest field character entity to a screen position
         *
         * @param screen_x Screen X coordinate
         * @param screen_y Screen Y coordinate
         * @return int Character ID of closest entity, or -1 if none found
         */
        static int find_closest_character(float screen_x, float screen_y);

        /**
         * @brief Convert field entity ID to character ID
         *
         * Maps field entity IDs to playable character IDs (0-8) or NPC IDs (100+)
         *
         * @param entity_id Field entity ID
         * @return int Character ID
         */
        static int entity_to_character_id(int entity_id);

        /**
         * @brief Get party leader character ID
         *
         * @return int Character ID of current party leader (fallback option)
         */
        static int get_party_leader();

        // Manual overrides: [field_id][window_id] -> character_id
        static std::map<std::string, std::map<int, int>> manual_overrides;

        // Initialization flag
        static bool is_initialized;
    };
}
