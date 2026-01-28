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

// Title screen video player using independent VideoContext.
// Rewritten 2026-01-28 to use VideoContext instead of global FFmpeg functions.
// This prevents the crash-on-New-Game bug where title video and game FMVs
// shared the same global AVFormatContext/AVCodecContext state.

#include "title_video.h"
#include "../log.h"
#include "../cfg.h"

namespace FFNx
{
    // Global title video player instance
    TitleVideoPlayer g_title_video;

    bool TitleVideoPlayer::load(const char* path, bool loop)
    {
        if (!path || strlen(path) == 0) {
            ffnx_warning("title_video: Empty path provided\n");
            return false;
        }

        // Stop any currently playing video
        if (is_active) {
            stop();
        }

        if (trace_all || trace_movies) {
            ffnx_trace("title_video: Loading video: %s (loop=%d)\n", path, loop);
        }

        // Open video via our own independent VideoContext (NOT the global pipeline)
        if (!video_ctx.open(path)) {
            ffnx_error("title_video: Failed to load video: %s\n", path);
            return false;
        }

        video_ctx.looping = loop;
        video_ctx.render_target.mode = VideoContext::RenderTarget::FULLSCREEN;

        current_path = path;
        is_active = true;

        // Initialize timing for frame-rate control
        QueryPerformanceFrequency((LARGE_INTEGER*)&timer_freq);
        last_decode_time = 0;

        // Decode the first frame immediately so we have something to render
        video_ctx.decodeNextFrame();

        ffnx_info("title_video: Video loaded successfully: %s\n", path);
        return true;
    }

    void TitleVideoPlayer::update()
    {
        if (!is_active) return;

        // FPS-based timing: only decode when enough time has elapsed
        double video_fps = video_ctx.getFps();
        if (video_fps <= 0.0) video_fps = 24.0;

        int64_t now;
        QueryPerformanceCounter((LARGE_INTEGER*)&now);

        if (last_decode_time == 0) {
            last_decode_time = now;
        }

        double elapsed_ms = (double)(now - last_decode_time) * 1000.0 / (double)timer_freq;
        double frame_interval_ms = 1000.0 / video_fps;

        if (elapsed_ms >= frame_interval_ms) {
            video_ctx.decodeNextFrame();
            last_decode_time = now;
        }

        if (video_ctx.isFinished() && !video_ctx.looping) {
            if (trace_all || trace_movies) {
                ffnx_trace("title_video: Video finished: %s\n", current_path.c_str());
            }
        }
    }

    void TitleVideoPlayer::render()
    {
        if (!is_active) return;

        video_ctx.render();
    }

    void TitleVideoPlayer::stop()
    {
        if (!is_active) return;

        if (trace_all || trace_movies) {
            ffnx_trace("title_video: Stopping video: %s\n", current_path.c_str());
        }

        video_ctx.close();

        is_active = false;
        current_path.clear();
        last_decode_time = 0;
    }
}
