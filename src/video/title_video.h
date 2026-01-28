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

#include "video_context.h"
#include <string>

namespace FFNx
{
    /**
     * Title screen video player using an independent VideoContext.
     *
     * Owns its own FFmpeg pipeline via VideoContext, so the title video
     * does NOT share state with the global movie pipeline (opening.avi etc.).
     * This prevents the crash-on-New-Game bug where stopping the title video
     * would corrupt the global FFmpeg state needed by game FMVs.
     */
    class TitleVideoPlayer {
    private:
        VideoContext video_ctx;
        bool is_active = false;
        std::string current_path;

        // FPS timing: only decode a new frame when enough time has passed
        int64_t timer_freq = 0;
        int64_t last_decode_time = 0;

    public:
        /**
         * Load and start playing a video.
         * @param path Path to video file (relative to FF7 directory)
         * @param loop Whether to loop the video indefinitely
         * @return true if video loaded successfully
         */
        bool load(const char* path, bool loop = true);

        /**
         * Update video playback (decode next frame if timing allows).
         */
        void update();

        /**
         * Render current video frame to screen as a fullscreen quad.
         * Saves/restores renderer state so UI elements render correctly on top.
         */
        void render();

        /**
         * Stop video playback and free all resources.
         */
        void stop();

        bool isActive() const { return is_active; }
        const char* getCurrentPath() const { return current_path.c_str(); }
    };

    // Global title video player instance
    extern TitleVideoPlayer g_title_video;
}
