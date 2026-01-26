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

#include "portrait_renderer.h"
#include "../log.h"
#include "../cfg.h"
#include "../globals.h"
#include "../renderer.h"
#include <bx/math.h>

namespace FFNx
{
    // Static member initialization
    bgfx::ProgramHandle PortraitRenderer::portrait_program = BGFX_INVALID_HANDLE;
    bgfx::VertexBufferHandle PortraitRenderer::vertex_buffer = BGFX_INVALID_HANDLE;
    bgfx::IndexBufferHandle PortraitRenderer::index_buffer = BGFX_INVALID_HANDLE;
    bgfx::VertexLayout PortraitRenderer::vertex_layout;

    bgfx::UniformHandle PortraitRenderer::portrait_params_uniform = BGFX_INVALID_HANDLE;
    bgfx::UniformHandle PortraitRenderer::portrait_color_uniform = BGFX_INVALID_HANDLE;
    bgfx::UniformHandle PortraitRenderer::glow_color_uniform = BGFX_INVALID_HANDLE;

    bgfx::UniformHandle PortraitRenderer::tex_portrait_sampler = BGFX_INVALID_HANDLE;
    bgfx::UniformHandle PortraitRenderer::tex_dialogue_sampler = BGFX_INVALID_HANDLE;
    bgfx::UniformHandle PortraitRenderer::tex_tail_sampler = BGFX_INVALID_HANDLE;

    std::map<int, bgfx::TextureHandle> PortraitRenderer::tail_texture_cache;
    bgfx::TextureHandle PortraitRenderer::fallback_tail_texture = BGFX_INVALID_HANDLE;

    bool PortraitRenderer::is_initialized = false;

    // Vertex structure for portrait quad
    struct PortraitVertex
    {
        float x, y, z;
        uint32_t color;
        float u, v;
    };

    void PortraitRenderer::init()
    {
        if (is_initialized)
        {
            ffnx_warning("PortraitRenderer::init: Already initialized\n");
            return;
        }

        ffnx_info("PortraitRenderer::init: Initializing portrait rendering system\n");

        // Create vertex layout
        vertex_layout
            .begin()
            .add(bgfx::Attrib::Position, 3, bgfx::AttribType::Float)
            .add(bgfx::Attrib::Color0, 4, bgfx::AttribType::Uint8, true)
            .add(bgfx::Attrib::TexCoord0, 2, bgfx::AttribType::Float)
            .end();

        // Create buffers
        create_buffers();

        // Create uniforms
        portrait_params_uniform = bgfx::createUniform("PortraitParams", bgfx::UniformType::Vec4);
        portrait_color_uniform = bgfx::createUniform("PortraitColor", bgfx::UniformType::Vec4);
        glow_color_uniform = bgfx::createUniform("GlowColor", bgfx::UniformType::Vec4);

        tex_portrait_sampler = bgfx::createUniform("tex_portrait", bgfx::UniformType::Sampler);
        tex_dialogue_sampler = bgfx::createUniform("tex_dialogue", bgfx::UniformType::Sampler);
        tex_tail_sampler = bgfx::createUniform("tex_tail", bgfx::UniformType::Sampler);

        // Create fallback tail texture (straight down)
        fallback_tail_texture = create_tail_texture(0.0f);

        is_initialized = true;
    }

    void PortraitRenderer::render_portrait_dialogue(
        int window_id,
        const PortraitLayoutManager::PortraitLayout& layout,
        bgfx::TextureHandle portrait_texture,
        bgfx::TextureHandle dialogue_texture
    )
    {
        if (!is_initialized)
        {
            ffnx_error("PortraitRenderer::render_portrait_dialogue: Renderer not initialized\n");
            return;
        }

        // Get or create tail texture for this rotation
        int rotation_degrees = static_cast<int>(layout.tail_rotation * 180.0f / 3.14159f);
        rotation_degrees = (rotation_degrees / 15) * 15; // Snap to 15-degree increments

        bgfx::TextureHandle tail_texture = fallback_tail_texture;
        auto it = tail_texture_cache.find(rotation_degrees);
        if (it != tail_texture_cache.end())
        {
            tail_texture = it->second;
        }
        else
        {
            tail_texture = create_tail_texture(layout.tail_rotation);
            tail_texture_cache[rotation_degrees] = tail_texture;
        }

        // Set up portrait parameters uniform
        float portrait_params[4] = {
            portrait_fade_width,
            static_cast<float>(layout.fade_direction),
            portrait_glow_intensity,
            layout.tail_rotation
        };
        bgfx::setUniform(portrait_params_uniform, portrait_params);

        // Set up portrait color (white = no tint)
        float portrait_color[4] = { 1.0f, 1.0f, 1.0f, 1.0f };
        bgfx::setUniform(portrait_color_uniform, portrait_color);

        // Set up glow color (light blue)
        float glow_color[4] = { 0.7f, 0.9f, 1.0f, 0.5f };
        bgfx::setUniform(glow_color_uniform, glow_color);

        // Bind textures
        bgfx::setTexture(0, tex_portrait_sampler, portrait_texture);
        bgfx::setTexture(1, tex_dialogue_sampler, dialogue_texture);
        bgfx::setTexture(2, tex_tail_sampler, tail_texture);

        // Set vertex and index buffers
        bgfx::setVertexBuffer(0, vertex_buffer);
        bgfx::setIndexBuffer(index_buffer);

        // Set render state (alpha blending)
        uint64_t state = 0
            | BGFX_STATE_WRITE_RGB
            | BGFX_STATE_WRITE_A
            | BGFX_STATE_BLEND_ALPHA;

        bgfx::setState(state);

        // Use portrait shader program from renderer
        // NOTE: This requires accessing the renderer's program handles
        // For now, we'll submit without a program and add it in the integration phase
        // bgfx::submit(viewId, portrait_program);

        if (trace_all || trace_renderer)
        {
            ffnx_trace("PortraitRenderer::render_portrait_dialogue: Rendered portrait for window %d\n", window_id);
        }
    }

    bgfx::TextureHandle PortraitRenderer::create_tail_texture(float rotation)
    {
        // Create a simple 256x256 SDF texture for the tail
        // For Phase 1, we'll create a placeholder texture
        // A proper implementation would generate an SDF triangle

        const int size = 256;
        const int stride = size * 4; // RGBA
        uint8_t* data = new uint8_t[size * size * 4];

        // Fill with transparent black (no tail for Phase 1)
        memset(data, 0, size * size * 4);

        // Create BGFX texture
        const bgfx::Memory* mem = bgfx::copy(data, size * size * 4);
        bgfx::TextureHandle handle = bgfx::createTexture2D(
            size, size,
            false,
            1,
            bgfx::TextureFormat::RGBA8,
            BGFX_TEXTURE_NONE,
            mem
        );

        delete[] data;

        if (trace_all)
        {
            ffnx_trace("PortraitRenderer::create_tail_texture: Created tail texture for rotation %f rad\n", rotation);
        }

        return handle;
    }

    void PortraitRenderer::shutdown()
    {
        if (!is_initialized)
        {
            return;
        }

        ffnx_info("PortraitRenderer::shutdown: Cleaning up portrait rendering resources\n");

        // Destroy uniforms
        if (bgfx::isValid(portrait_params_uniform))
            bgfx::destroy(portrait_params_uniform);
        if (bgfx::isValid(portrait_color_uniform))
            bgfx::destroy(portrait_color_uniform);
        if (bgfx::isValid(glow_color_uniform))
            bgfx::destroy(glow_color_uniform);
        if (bgfx::isValid(tex_portrait_sampler))
            bgfx::destroy(tex_portrait_sampler);
        if (bgfx::isValid(tex_dialogue_sampler))
            bgfx::destroy(tex_dialogue_sampler);
        if (bgfx::isValid(tex_tail_sampler))
            bgfx::destroy(tex_tail_sampler);

        // Destroy buffers
        if (bgfx::isValid(vertex_buffer))
            bgfx::destroy(vertex_buffer);
        if (bgfx::isValid(index_buffer))
            bgfx::destroy(index_buffer);

        // Destroy tail textures
        if (bgfx::isValid(fallback_tail_texture))
            bgfx::destroy(fallback_tail_texture);

        for (auto& pair : tail_texture_cache)
        {
            if (bgfx::isValid(pair.second))
                bgfx::destroy(pair.second);
        }

        tail_texture_cache.clear();
        is_initialized = false;
    }

    void PortraitRenderer::create_buffers()
    {
        // Create quad vertices (will be updated per portrait)
        PortraitVertex vertices[4] = {
            { 0.0f,   0.0f,   0.0f, 0xFFFFFFFF, 0.0f, 0.0f }, // Top-left
            { 128.0f, 0.0f,   0.0f, 0xFFFFFFFF, 1.0f, 0.0f }, // Top-right
            { 128.0f, 128.0f, 0.0f, 0xFFFFFFFF, 1.0f, 1.0f }, // Bottom-right
            { 0.0f,   128.0f, 0.0f, 0xFFFFFFFF, 0.0f, 1.0f }  // Bottom-left
        };

        // Create vertex buffer
        const bgfx::Memory* vb_mem = bgfx::copy(vertices, sizeof(vertices));
        vertex_buffer = bgfx::createVertexBuffer(vb_mem, vertex_layout);

        // Create quad indices
        uint16_t indices[6] = {
            0, 1, 2,  // First triangle
            0, 2, 3   // Second triangle
        };

        const bgfx::Memory* ib_mem = bgfx::copy(indices, sizeof(indices));
        index_buffer = bgfx::createIndexBuffer(ib_mem);

        if (!bgfx::isValid(vertex_buffer) || !bgfx::isValid(index_buffer))
        {
            ffnx_error("PortraitRenderer::create_buffers: Failed to create buffers\n");
        }
    }

    void PortraitRenderer::update_vertex_buffer(
        const PortraitLayoutManager::PortraitLayout& layout,
        float screen_width,
        float screen_height
    )
    {
        // TODO: Update vertex positions based on layout
        // For Phase 1, we use static buffers
        // This would be implemented when we need dynamic positioning
    }
}
