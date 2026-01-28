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

#include <stdint.h>

// Forward declarations for FFmpeg types (actual includes in .cpp via globals.h)
struct AVFormatContext;
struct AVCodecContext;
struct AVFrame;
struct SwsContext;

namespace FFNx
{
    /**
     * Self-contained video playback context.
     *
     * Each instance owns its own FFmpeg state (AVFormatContext, AVCodecContext,
     * SwsContext, AVFrame) and GPU texture ring buffer. Decodes to BGRA for
     * simplicity -- no YUV shader plumbing needed.
     *
     * This class exists to allow independent video playback that does NOT
     * conflict with the global FFmpeg pipeline used by game FMVs (opening.avi, etc.).
     */
    class VideoContext {
    private:
        // Per-instance FFmpeg state (NOT the globals in movies.cpp)
        AVFormatContext* format_ctx = nullptr;
        AVCodecContext*  codec_ctx  = nullptr;
        AVFrame*         decode_frame = nullptr;
        SwsContext*      sws_ctx    = nullptr;
        int video_stream_index = -1;

        // Per-instance texture ring buffer (BGRA textures)
        static constexpr int BUFFER_SIZE = 4;
        uint32_t frame_textures[BUFFER_SIZE] = {0};
        uint32_t buf_read = 0;
        uint32_t buf_write = 0;

        // Per-instance video metadata and timing
        uint32_t video_width = 0;
        uint32_t video_height = 0;
        double fps = 0.0;
        double duration = 0.0;
        int64_t timer_freq = 0;
        int64_t start_time = 0;
        uint32_t frame_counter = 0;
        bool finished = false;

        // BGRA pixel buffer (reused across frames to avoid per-frame allocation)
        uint8_t* bgra_buffer = nullptr;
        int bgra_stride = 0;

    public:
        VideoContext() = default;
        ~VideoContext();

        // Non-copyable (owns FFmpeg resources)
        VideoContext(const VideoContext&) = delete;
        VideoContext& operator=(const VideoContext&) = delete;

        /**
         * Open a video file into this instance's own FFmpeg contexts.
         * @param path Filesystem path to the video file
         * @return true if opened successfully
         */
        bool open(const char* path);

        /**
         * Close and free all FFmpeg resources and GPU textures.
         */
        void close();

        /**
         * Decode the next frame and upload it to a GPU texture.
         * @return true if a frame was decoded, false at EOF
         */
        bool decodeNextFrame();

        /**
         * Render the current frame as a fullscreen quad.
         * Saves and restores renderer state so UI elements drawn
         * after this call are not contaminated.
         */
        void render();

        /**
         * Seek back to the start of the video (for looping).
         */
        void seekToStart();

        bool isOpen() const { return format_ctx != nullptr; }
        bool isFinished() const { return finished; }
        uint32_t getWidth() const { return video_width; }
        uint32_t getHeight() const { return video_height; }
        double getFps() const { return fps; }

        // Render target configuration
        struct RenderTarget {
            enum Mode { FULLSCREEN, POSITIONED };
            Mode mode = FULLSCREEN;
            float x = 0.0f;
            float y = 0.0f;
            float w = 128.0f;
            float h = 128.0f;
        } render_target;

        bool looping = false;
    };
}
