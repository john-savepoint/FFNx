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
#include <vector>

namespace FFNx
{
    // Single frame in animation sequence
    struct AnimFrame {
        float u0, v0, u1, v1;  // UV rectangle for this frame in sprite sheet
        float duration;         // Time to display this frame (seconds)
    };

    // Character portrait animation state
    struct CharPortraitAnim {
        ff7_graphics_object* gfx_obj;        // Points to menu avatar graphics object
        std::vector<AnimFrame> frames;        // 64 frames from 8×8 sprite sheet
        float time_accum = 0.0f;              // Accumulated time for current frame
        size_t current_frame = 0;             // Current frame index (0-63)
        bool enabled = true;                  // Animation enabled flag
        bool initialized = false;             // Initialization state
    };

    // Global animation state for all 9 characters
    // Order: Cloud=0, Tifa=1, Barret=2, Aerith=3, RedXIII=4, Yuffie=5, Cait=6, Vincent=7, Cid=8
    extern CharPortraitAnim g_char_anims[9];

    // Initialize animation system (loads sprite sheets, links graphics objects)
    void init_char_portrait_anims();

    // Update all animations (called each frame with delta time)
    void update_char_portrait_anims(float delta_time);

    // Cleanup animation resources
    void cleanup_char_portrait_anims();

    // Load frames from 8×8 sprite sheet
    bool load_anim_frames(const char* texture_path, std::vector<AnimFrame>& out_frames, float frame_duration = 0.1f);
}
