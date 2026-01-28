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

#pragma once

#include "../common.h"
#include "../ff7_data.h"

namespace FFNx
{
    /**
     * Title screen video variants based on game progress
     */
    enum TitleVideoVariant {
        TITLE_EARLY_GAME,      // Midgar (before leaving)
        TITLE_WORLD_MAP,       // After Midgar escape
        TITLE_METEOR_CRISIS,   // After Meteor summoned
        TITLE_FINAL_BATTLE     // Near endgame
    };

    /**
     * Detect which title video variant to use based on game progress
     *
     * Analyzes save data (play time, location, story flags) to determine
     * which stage of the game the player is in.
     *
     * @return TitleVideoVariant enum indicating current game stage
     */
    TitleVideoVariant detect_title_variant();

    /**
     * Get video file path for a specific variant
     *
     * @param variant The title video variant
     * @return Path to video file (from config)
     */
    const char* get_title_video_path(TitleVideoVariant variant);
}
