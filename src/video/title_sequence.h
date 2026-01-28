/****************************************************************************/
//    Copyright (C) 2026 John Zealand-Doyle                                  //
//                                                                            //
//    This file is part of FFNx                                              //
//                                                                            //
//    FFNx is free software: you can redistribute it and/or modify           //
//    it under the terms of the GNU General Public License as published by   //
//    the Free Software Foundation, either version 3 of the License          //
//                                                                            //
//    FFNx is distributed in the hope that it will be useful,               //
//    but WITHOUT ANY WARRANTY; without even the implied warranty of         //
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          //
//    GNU General Public License for more details.                           //
/****************************************************************************/

#pragma once

#include <vector>
#include <string>
#include "../renderer.h"

namespace FFNx
{
    /**
     * Image sequence player for title screen animation
     * Loads a sequence of PNG/JPG files and cycles through them
     */
    class TitleSequencePlayer
    {
    private:
        std::vector<uint32_t> frame_textures;  // Loaded frame texture handles
        size_t current_frame = 0;
        float time_accumulator = 0.0f;
        float frame_duration = 1.0f / 30.0f;  // 30 FPS default
        bool is_active = false;
        bool is_looping = true;

    public:
        /**
         * Load image sequence from directory
         * @param path Directory containing numbered frames (e.g., "textures/title/frame_001.png")
         * @param fps Playback frame rate
         */
        bool load(const char* directory, float fps = 30.0f);

        /**
         * Update animation state
         */
        void update(float delta_time);

        /**
         * Render current frame to screen
         */
        void render();

        /**
         * Stop playback and free resources
         */
        void stop();

        /**
         * Check if sequence is currently active
         */
        bool isActive() const { return is_active; }
    };

    // Global title sequence player instance
    extern TitleSequencePlayer g_title_sequence;
}
