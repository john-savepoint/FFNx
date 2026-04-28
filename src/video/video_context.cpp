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

// Independent video playback context for FFNx.
// Created 2026-01-28 to allow title screen video to play without
// conflicting with the global FFmpeg pipeline used by game FMVs.
// Each VideoContext instance owns its own AVFormatContext, AVCodecContext,
// SwsContext, decode frame, and BGRA texture ring buffer.

#include "video_context.h"
#include "../globals.h"
#include "../renderer.h"
#include "../gl.h"
#include "../cfg.h"
#include "../log.h"
#include "../ff7/widescreen.h"

extern Renderer newRenderer;
extern Widescreen widescreen;
extern uint32_t game_width;
extern uint32_t game_height;
extern int max_texture_size;

namespace FFNx
{

VideoContext::~VideoContext()
{
    close();
}

bool VideoContext::open(const char* path)
{
    if (!path || strlen(path) == 0) {
        ffnx_warning("VideoContext::open: empty path\n");
        return false;
    }

    // Close any existing context first
    if (format_ctx) {
        close();
    }

    if (trace_all || trace_movies) {
        ffnx_trace("VideoContext::open: %s\n", path);
    }

    // Open container into THIS instance's format_ctx
    if (avformat_open_input(&format_ctx, path, nullptr, nullptr) != 0) {
        ffnx_error("VideoContext::open: couldn't open file: %s\n", path);
        close();
        return false;
    }

    if (avformat_find_stream_info(format_ctx, nullptr) < 0) {
        ffnx_error("VideoContext::open: couldn't find stream info\n");
        close();
        return false;
    }

    // Find video stream
    const AVCodec* codec = nullptr;
    video_stream_index = av_find_best_stream(format_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, &codec, 0);
    if (video_stream_index < 0) {
        ffnx_error("VideoContext::open: no video stream found\n");
        close();
        return false;
    }

    // Allocate and open codec context (instance-owned, not the global)
    codec_ctx = avcodec_alloc_context3(codec);
    if (!codec_ctx) {
        ffnx_error("VideoContext::open: couldn't allocate codec context\n");
        close();
        return false;
    }

    avcodec_parameters_to_context(codec_ctx, format_ctx->streams[video_stream_index]->codecpar);

    if (avcodec_open2(codec_ctx, codec, nullptr) < 0) {
        ffnx_error("VideoContext::open: couldn't open codec\n");
        close();
        return false;
    }

    // Store video metadata
    video_width = codec_ctx->width;
    video_height = codec_ctx->height;
    fps = av_q2d(av_guess_frame_rate(format_ctx, format_ctx->streams[video_stream_index], nullptr));
    duration = (double)format_ctx->duration / (double)AV_TIME_BASE;

    if (video_width > (uint32_t)max_texture_size || video_height > (uint32_t)max_texture_size) {
        ffnx_error("VideoContext::open: dimensions %ux%u exceed max texture size %d\n",
                    video_width, video_height, max_texture_size);
        close();
        return false;
    }

    // Set up sws_scale to convert from source pixel format to BGRA
    sws_ctx = sws_getContext(
        video_width, video_height, codec_ctx->pix_fmt,
        video_width, video_height, AV_PIX_FMT_BGRA,
        SWS_BILINEAR, nullptr, nullptr, nullptr
    );

    if (!sws_ctx) {
        ffnx_error("VideoContext::open: couldn't create sws context\n");
        close();
        return false;
    }

    // Allocate decode frame
    decode_frame = av_frame_alloc();
    if (!decode_frame) {
        ffnx_error("VideoContext::open: couldn't allocate frame\n");
        close();
        return false;
    }

    // Allocate BGRA pixel buffer (reused per-frame)
    bgra_stride = video_width * 4;
    bgra_buffer = (uint8_t*)av_malloc(bgra_stride * video_height);
    if (!bgra_buffer) {
        ffnx_error("VideoContext::open: couldn't allocate BGRA buffer\n");
        close();
        return false;
    }

    // Initialize timing
    QueryPerformanceFrequency((LARGE_INTEGER*)&timer_freq);
    frame_counter = 0;
    start_time = 0;
    finished = false;

    // Zero texture ring buffer
    for (int i = 0; i < BUFFER_SIZE; i++) {
        frame_textures[i] = 0;
    }
    buf_read = 0;
    buf_write = 0;

    ffnx_info("VideoContext::open: loaded %s (%ux%u, %.1f fps, %.1fs)\n",
              path, video_width, video_height, fps, duration);

    return true;
}

void VideoContext::close()
{
    // Free GPU textures
    for (int i = 0; i < BUFFER_SIZE; i++) {
        if (frame_textures[i]) {
            newRenderer.deleteTexture(static_cast<uint16_t>(frame_textures[i]));
            frame_textures[i] = 0;
        }
    }

    // Free BGRA buffer
    if (bgra_buffer) {
        av_free(bgra_buffer);
        bgra_buffer = nullptr;
    }

    // Free FFmpeg resources (order matters: frame, codec, format, sws)
    if (decode_frame) {
        av_frame_free(&decode_frame);
    }
    if (codec_ctx) {
        avcodec_free_context(&codec_ctx);
    }
    if (format_ctx) {
        avformat_close_input(&format_ctx);
    }
    if (sws_ctx) {
        sws_freeContext(sws_ctx);
        sws_ctx = nullptr;
    }

    video_stream_index = -1;
    video_width = 0;
    video_height = 0;
    fps = 0.0;
    duration = 0.0;
    frame_counter = 0;
    start_time = 0;
    finished = false;
    buf_read = 0;
    buf_write = 0;
    bgra_stride = 0;

    if (trace_all || trace_movies) {
        ffnx_trace("VideoContext::close: resources freed\n");
    }
}

bool VideoContext::decodeNextFrame()
{
    if (!format_ctx || finished) return false;

    // Record start time on first frame
    if (frame_counter == 0) {
        QueryPerformanceCounter((LARGE_INTEGER*)&start_time);
    }

    AVPacket packet;
    int ret;

    while ((ret = av_read_frame(format_ctx, &packet)) >= 0) {
        if (packet.stream_index == video_stream_index) {
            ret = avcodec_send_packet(codec_ctx, &packet);
            if (ret < 0) {
                av_packet_unref(&packet);
                break;
            }

            ret = avcodec_receive_frame(codec_ctx, decode_frame);
            if (ret == AVERROR_EOF) {
                av_packet_unref(&packet);
                break;
            }

            if (ret >= 0) {
                // Convert decoded frame to BGRA
                uint8_t* dst_data[1] = { bgra_buffer };
                int dst_linesize[1] = { bgra_stride };
                sws_scale(sws_ctx,
                          decode_frame->data, decode_frame->linesize,
                          0, video_height,
                          dst_data, dst_linesize);

                // Delete old texture at this ring buffer slot
                if (frame_textures[buf_write]) {
                    newRenderer.deleteTexture(static_cast<uint16_t>(frame_textures[buf_write]));
                    frame_textures[buf_write] = 0;
                }

                // Upload BGRA data to a new GPU texture
                // sRGB = true: Video frames are gamma-encoded, let GPU linearize on sampling
                frame_textures[buf_write] = newRenderer.createTexture(
                    bgra_buffer,
                    video_width,
                    video_height,
                    0,
                    RendererTextureType::BGRA,
                    true,   // sRGB - GPU handles gamma conversion automatically
                    true    // copy data
                );

                buf_read = buf_write;
                buf_write = (buf_write + 1) % BUFFER_SIZE;
                frame_counter++;

                av_packet_unref(&packet);
                return true;
            }
        }

        av_packet_unref(&packet);
    }

    // EOF reached
    if (looping) {
        seekToStart();
        // Retry after seeking
        return decodeNextFrame();
    }

    finished = true;
    return false;
}

void VideoContext::render()
{
    if (!format_ctx || frame_textures[buf_read] == 0) return;

    struct game_obj* game_object = common_externals.get_game_object();

    // Save ALL renderer state so UI elements drawn after us are unaffected
    struct driver_state saved_state;
    gl_save_state(&saved_state);

    if (render_target.mode == RenderTarget::FULLSCREEN) {
        // Title video must fill the ENTIRE visible area including widescreen sides.
        //
        // The backendProjMatrix (used for TLVertex) maps:
        //   X: [wide_viewport_x .. wide_viewport_x + wide_viewport_width] -> full screen
        //   Y: [0 .. game_height] -> full screen
        //
        // For 16:9 at 480p: X [-107 .. 747], Y [0 .. 480]
        // For 4:3: X [0 .. 640], Y [0 .. 480]
        //
        // To fill the screen, our quad must span these exact ranges.
        // The video's aspect ratio is preserved by cropping (fill mode).

        float screen_left, screen_right;
        if (widescreen_enabled) {
            screen_left  = (float)wide_viewport_x;                              // -107
            screen_right = (float)(wide_viewport_x + wide_viewport_width);      // 747
        } else {
            screen_left  = 0.0f;
            screen_right = (float)game_width;                                   // 640
        }
        float screen_top    = 0.0f;
        float screen_bottom = (float)game_height;                               // 480

        float screen_w = screen_right - screen_left;
        float screen_h = screen_bottom - screen_top;

        // Scale video to FILL the screen (crop if aspect ratios differ)
        float screen_aspect = screen_w / screen_h;
        float video_aspect  = (float)video_width / (float)video_height;

        float quad_x0, quad_y0, quad_x1, quad_y1;
        float u0 = 0.0f, v0 = 0.0f, u1 = 1.0f, v1 = 1.0f;

        if (video_aspect >= screen_aspect) {
            // Video is wider than screen: fit height, crop sides via UV
            quad_x0 = screen_left;
            quad_x1 = screen_right;
            quad_y0 = screen_top;
            quad_y1 = screen_bottom;
            // Crop the video's horizontal edges via UV coordinates
            float visible_fraction = screen_aspect / video_aspect;
            float umargin = (1.0f - visible_fraction) * 0.5f;
            u0 = umargin;
            u1 = 1.0f - umargin;
        } else {
            // Video is taller than screen: fit width, crop top/bottom via UV
            quad_x0 = screen_left;
            quad_x1 = screen_right;
            quad_y0 = screen_top;
            quad_y1 = screen_bottom;
            float visible_fraction = video_aspect / screen_aspect;
            float vmargin = (1.0f - visible_fraction) * 0.5f;
            v0 = vmargin;
            v1 = 1.0f - vmargin;
        }

        static bool logged_once = false;
        if (!logged_once) {
            ffnx_info("VideoContext::render: screen=[%.0f,%.0f]->[%.0f,%.0f] video=%ux%u uv=[%.3f,%.3f]->[%.3f,%.3f] ws=%d\n",
                      quad_x0, quad_y0, quad_x1, quad_y1,
                      video_width, video_height,
                      u0, v0, u1, v1, widescreen_enabled);
            logged_once = true;
        }

        struct nvertex vertices[] = {
            {quad_x0, quad_y0, 1.0f, 1.0f, 0xffffffff, 0, u0, v0},  // top-left
            {quad_x0, quad_y1, 1.0f, 1.0f, 0xffffffff, 0, u0, v1},  // bottom-left
            {quad_x1, quad_y0, 1.0f, 1.0f, 0xffffffff, 0, u1, v0},  // top-right
            {quad_x1, quad_y1, 1.0f, 1.0f, 0xffffffff, 0, u1, v1},  // bottom-right
        };
        WORD indices[] = { 0, 1, 2, 1, 3, 2 };

        // Bind BGRA texture
        newRenderer.useTexture(static_cast<uint16_t>(frame_textures[buf_read]),
                               RendererTextureSlot::TEX_Y);

        // Set renderer state to match how gl_draw_movie_quad_common works:
        // isMovie(true) tells shader to force alpha=1.0 on the texture color
        // isYUV(false) tells shader to use tex_0 directly as RGB, not do YUV conversion
        // isTLVertex(true) tells vertex shader to use backendProjMatrix
        newRenderer.isMovie(true);
        newRenderer.isYUV(false);
        newRenderer.isTLVertex(true);
        newRenderer.doTextureFiltering(true);

        current_state.texture_filter = true;

        internal_set_renderstate(V_NOCULL, 1, game_object);
        internal_set_renderstate(V_DEPTHTEST, 0, game_object);
        internal_set_renderstate(V_DEPTHMASK, 0, game_object);

        newRenderer.setInterpolationQualifier(RendererInterpolationQualifier::SMOOTH);
        newRenderer.bindVertexBuffer(vertices, 0, 4);
        newRenderer.bindIndexBuffer(indices, 6);
        newRenderer.draw();

    } else {
        // POSITIONED mode (future: character portraits)
        float x0 = render_target.x;
        float y0 = render_target.y;
        float x_end = x0 + render_target.w;
        float y_end = y0 + render_target.h;

        struct nvertex vertices[] = {
            {x0,    y0,    1.0f, 1.0f, 0xffffffff, 0, 0.0f, 0.0f},
            {x0,    y_end, 1.0f, 1.0f, 0xffffffff, 0, 0.0f, 1.0f},
            {x_end, y0,    1.0f, 1.0f, 0xffffffff, 0, 1.0f, 0.0f},
            {x_end, y_end, 1.0f, 1.0f, 0xffffffff, 0, 1.0f, 1.0f},
        };
        WORD indices[] = { 0, 1, 2, 1, 3, 2 };

        newRenderer.useTexture(static_cast<uint16_t>(frame_textures[buf_read]),
                               RendererTextureSlot::TEX_Y);

        newRenderer.isMovie(true);
        newRenderer.isTLVertex(true);
        newRenderer.isYUV(false);
        newRenderer.doTextureFiltering(true);

        current_state.texture_filter = true;
        internal_set_renderstate(V_NOCULL, 1, game_object);
        internal_set_renderstate(V_DEPTHTEST, 0, game_object);
        internal_set_renderstate(V_DEPTHMASK, 0, game_object);

        newRenderer.setInterpolationQualifier(RendererInterpolationQualifier::SMOOTH);
        newRenderer.bindVertexBuffer(vertices, 0, 4);
        newRenderer.bindIndexBuffer(indices, 6);
        newRenderer.draw();
    }

    // Reset movie flags BEFORE restoring state, so the renderer doesn't
    // carry these into subsequent draw calls
    newRenderer.isMovie(false);
    newRenderer.isTLVertex(false);
    newRenderer.isYUV(false);
    newRenderer.doTextureFiltering(false);

    // Restore ALL renderer state (blend mode, depth, texture, viewport, etc.)
    gl_load_state(&saved_state);
}

void VideoContext::seekToStart()
{
    if (!format_ctx) return;

    av_seek_frame(format_ctx, video_stream_index, 0, AVSEEK_FLAG_BACKWARD);
    avcodec_flush_buffers(codec_ctx);

    frame_counter = 0;
    start_time = 0;
    finished = false;

    if (trace_all || trace_movies) {
        ffnx_trace("VideoContext::seekToStart: seeked to beginning\n");
    }
}

} // namespace FFNx
