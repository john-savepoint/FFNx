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

#pragma once

#include "portrait_layout.h"
#include <bgfx/bgfx.h>
#include <map>

namespace FFNx
{
    /**
     * @brief Portrait Renderer
     *
     * Handles BGFX rendering of character portraits composited with
     * dialogue boxes using the portrait shader system.
     */
    class PortraitRenderer
    {
    public:
        /**
         * @brief Initialize portrait rendering system
         *
         * Loads shaders, creates vertex/index buffers, and prepares uniforms.
         * Must be called during FFNx initialization.
         */
        static void init();

        /**
         * @brief Render portrait composite for a dialogue box
         *
         * Submits BGFX draw call to render portrait + dialogue box + tail
         * using the multi-layer portrait shader.
         *
         * @param window_id Dialogue window ID (for view ordering)
         * @param layout Portrait layout information
         * @param portrait_texture Character portrait texture handle
         * @param dialogue_texture Dialogue box background texture handle
         */
        static void render_portrait_dialogue(
            int window_id,
            const PortraitLayoutManager::PortraitLayout& layout,
            bgfx::TextureHandle portrait_texture,
            bgfx::TextureHandle dialogue_texture
        );

        /**
         * @brief Create tail/pointer SDF texture
         *
         * Generates a procedural SDF texture for the triangular pointer
         * that connects portrait to dialogue box.
         *
         * @param rotation Tail rotation in radians
         * @return bgfx::TextureHandle Handle to tail SDF texture
         */
        static bgfx::TextureHandle create_tail_texture(float rotation);

        /**
         * @brief Shutdown and cleanup rendering resources
         */
        static void shutdown();

    private:
        /**
         * @brief Load portrait shader program
         *
         * @return true if shader loaded successfully, false otherwise
         */
        static bool load_shader_program();

        /**
         * @brief Create vertex and index buffers for quad rendering
         */
        static void create_buffers();

        /**
         * @brief Update vertex buffer for specific portrait layout
         *
         * @param layout Portrait layout (position, size)
         * @param screen_width Current screen width
         * @param screen_height Current screen height
         */
        static void update_vertex_buffer(
            const PortraitLayoutManager::PortraitLayout& layout,
            float screen_width,
            float screen_height
        );

        // BGFX resources
        static bgfx::ProgramHandle portrait_program;
        static bgfx::VertexBufferHandle vertex_buffer;
        static bgfx::IndexBufferHandle index_buffer;
        static bgfx::VertexLayout vertex_layout;

        // Shader uniforms
        static bgfx::UniformHandle portrait_params_uniform;
        static bgfx::UniformHandle portrait_color_uniform;
        static bgfx::UniformHandle glow_color_uniform;

        // Texture samplers
        static bgfx::UniformHandle tex_portrait_sampler;
        static bgfx::UniformHandle tex_dialogue_sampler;
        static bgfx::UniformHandle tex_tail_sampler;

        // Tail texture cache (rotation angle -> texture handle)
        static std::map<int, bgfx::TextureHandle> tail_texture_cache;

        // Fallback tail texture (straight down)
        static bgfx::TextureHandle fallback_tail_texture;

        // Initialization flag
        static bool is_initialized;
    };
}
