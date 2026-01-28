/****************************************************************************/
//    Copyright (C) 2026 John Zealand-Doyle                                  //
//                                                                            //
//    This file is part of FFNx                                              //
//                                                                            //
//    FFNx is free software: you can redistribute it and/or modify           //
//    it under the terms of the GNU General Public License as published by   //
//    the Free Software Foundation, either version 3 of the License          //
//                                                                            //
//    FFNx is distributed in the hope that it will be useful,                //
//    but WITHOUT ANY WARRANTY; without even the implied warranty of         //
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          //
//    GNU General Public License for more details.                           //
/****************************************************************************/

#include "title_progress.h"
#include "../log.h"
#include "../cfg.h"
#include "../ff7.h"

namespace FFNx
{
    /**
     * Detect which title video variant to use based on game progress
     */
    TitleVideoVariant detect_title_variant()
    {
        // Get current game mode
        struct game_mode* mode = getmode_cached();

        if (!mode) {
            if (trace_all) {
                ffnx_trace("title_progress: No mode available, using default\n");
            }
            return TITLE_EARLY_GAME;
        }

        // If not in-game or no save data available, use default
        if (mode->driver_mode == MODE_INTRO ||
            mode->driver_mode == MODE_MAIN_MENU ||
            mode->driver_mode == MODE_EXIT) {
            if (trace_all) {
                ffnx_trace("title_progress: Not in-game (mode %d), using default\n",
                    mode->driver_mode);
            }
            return TITLE_EARLY_GAME;
        }

        // Access savemap safely (only available when in-game)
        auto* save = ff7_externals.savemap;
        if (!save) {
            if (trace_all) {
                ffnx_trace("title_progress: No savemap available, using default\n");
            }
            return TITLE_EARLY_GAME;
        }

        // Calculate hours played
        uint32_t hours_played = save->seconds / 3600;

        // Get current location
        WORD location = save->current_location;

        if (trace_all) {
            ffnx_trace("title_progress: Analyzing save - Hours: %u, Location: %u\n",
                hours_played, location);
        }

        // Detection logic based on play time
        // This is a simplified heuristic - could be refined with specific story flags
        // or location checks for more accuracy

        if (hours_played < 5) {
            // Early game - still in Midgar
            if (trace_all || trace_movies) {
                ffnx_info("title_progress: Detected EARLY_GAME (%.1f hours)\n",
                    hours_played);
            }
            return TITLE_EARLY_GAME;
        }
        else if (hours_played < 15) {
            // Mid game - exploring the world
            if (trace_all || trace_movies) {
                ffnx_info("title_progress: Detected WORLD_MAP (%.1f hours)\n",
                    hours_played);
            }
            return TITLE_WORLD_MAP;
        }
        else if (hours_played < 35) {
            // Late game - Meteor crisis
            if (trace_all || trace_movies) {
                ffnx_info("title_progress: Detected METEOR_CRISIS (%.1f hours)\n",
                    hours_played);
            }
            return TITLE_METEOR_CRISIS;
        }
        else {
            // Endgame - approaching final battle
            if (trace_all || trace_movies) {
                ffnx_info("title_progress: Detected FINAL_BATTLE (%.1f hours)\n",
                    hours_played);
            }
            return TITLE_FINAL_BATTLE;
        }
    }

    /**
     * Get video file path for a specific variant
     */
    const char* get_title_video_path(TitleVideoVariant variant)
    {
        switch (variant) {
            case TITLE_EARLY_GAME:
                return title_video_early_game.c_str();

            case TITLE_WORLD_MAP:
                return title_video_world_map.c_str();

            case TITLE_METEOR_CRISIS:
                return title_video_meteor.c_str();

            case TITLE_FINAL_BATTLE:
                return title_video_final.c_str();

            default:
                ffnx_warning("title_progress: Unknown variant %d, using early_game\n",
                    variant);
                return title_video_early_game.c_str();
        }
    }
}
