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

#include "title_sequence.h"
#include "../log.h"
#include "../cfg.h"
#include "../renderer.h"
#include "../saveload.h"
#include "../gl.h"
#include <filesystem>

namespace fs = std::filesystem;

namespace FFNx
{
    // Global instance
    TitleSequencePlayer g_title_sequence;

    bool TitleSequencePlayer::load(const char* directory, float fps)
    {
        if (!directory || strlen(directory) == 0) {
            ffnx_warning("title_sequence: Empty directory provided\n");
            return false;
        }

        // Free any existing frames
        stop();

        frame_duration = 1.0f / fps;

        if (trace_all || trace_movies) {
            ffnx_trace("title_sequence: Loading frames from %s at %.1f FPS\n", directory, fps);
        }

        // Find all PNG files in directory (sorted by name)
        std::vector<std::string> frame_paths;
        try {
            for (const auto& entry : fs::directory_iterator(directory)) {
                if (entry.is_regular_file()) {
                    std::string ext = entry.path().extension().string();
                    if (ext == ".png" || ext == ".PNG") {
                        frame_paths.push_back(entry.path().string());
                    }
                }
            }
        } catch (const std::exception& e) {
            ffnx_error("title_sequence: Failed to read directory %s: %s\n", directory, e.what());
            return false;
        }

        if (frame_paths.empty()) {
            ffnx_warning("title_sequence: No PNG files found in %s\n", directory);
            return false;
        }

        // Sort paths to ensure correct order
        std::sort(frame_paths.begin(), frame_paths.end());

        // Load each frame as a texture using FFNx renderer
        for (const auto& path : frame_paths) {
            char path_buf[512];
            strncpy(path_buf, path.c_str(), sizeof(path_buf) - 1);
            path_buf[sizeof(path_buf) - 1] = '\0';

            normalize_path(path_buf);

            if (trace_all || trace_movies) {
                ffnx_trace("title_sequence: Loading frame: %s\n", path_buf);
            }

            uint32_t width = 0, height = 0;
            uint32_t tex = newRenderer.createTextureLibPng(path_buf, &width, &height, true);

            if (tex && tex != UINT16_MAX) {
                frame_textures.push_back(tex);
                if (trace_all || trace_movies) {
                    ffnx_trace("title_sequence: Frame loaded OK: %ux%u, tex=%u\n", width, height, tex);
                }
            } else {
                ffnx_warning("title_sequence: Failed to load frame: %s (tex=%u)\n", path.c_str(), tex);
            }
        }

        if (frame_textures.empty()) {
            ffnx_error("title_sequence: No frames loaded successfully\n");
            return false;
        }

        is_active = true;
        current_frame = 0;
        time_accumulator = 0.0f;

        ffnx_info("title_sequence: Loaded %zu frames from %s\n", frame_textures.size(), directory);
        return true;
    }

    void TitleSequencePlayer::update(float delta_time)
    {
        if (!is_active || frame_textures.empty()) return;

        time_accumulator += delta_time;

        // Advance frame if enough time has passed
        while (time_accumulator >= frame_duration) {
            time_accumulator -= frame_duration;
            current_frame++;

            if (current_frame >= frame_textures.size()) {
                if (is_looping) {
                    current_frame = 0;
                } else {
                    current_frame = frame_textures.size() - 1;
                    is_active = false;
                }
            }
        }
    }

    void TitleSequencePlayer::render()
    {
        if (!is_active || frame_textures.empty() || current_frame >= frame_textures.size()) return;

        uint32_t current_tex = frame_textures[current_frame];
        if (!current_tex) return;

        // Render fullscreen using single texture (not YUV like movies)
        newRenderer.useTexture(current_tex);
        newRenderer.isMovie(true);  // Use movie rendering mode for fullscreen

        // Draw fullscreen quad at game resolution (640x480 for FF7)
        gl_draw_movie_quad(640, 480);

        newRenderer.isMovie(false);
    }

    void TitleSequencePlayer::stop()
    {
        if (!is_active && frame_textures.empty()) return;

        if (trace_all || trace_movies) {
            ffnx_trace("title_sequence: Stopping sequence (%zu frames loaded)\n", frame_textures.size());
        }

        // Free all loaded textures
        for (uint32_t tex : frame_textures) {
            if (tex) {
                newRenderer.deleteTexture(tex);
            }
        }

        frame_textures.clear();
        is_active = false;
        current_frame = 0;
        time_accumulator = 0.0f;
    }
}
