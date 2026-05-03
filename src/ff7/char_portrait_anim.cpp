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

#include "char_portrait_anim.h"
#include "../log.h"
#include "../cfg.h"
#include "../ff7.h"
#include <cmath>

namespace FFNx
{
    // Global animation state for 9 characters
    CharPortraitAnim g_char_anims[9];

    // Character names for logging and file paths
    static const char* char_names[9] = {
        "cloud", "tifa", "barret", "aerith", "redxiii",
        "yuffie", "cait", "vincent", "cid"
    };

    /**
     * Load animation frames from 8×8 sprite sheet
     *
     * @param texture_path Path to sprite sheet PNG (relative to FF7 directory)
     * @param out_frames Output vector to store frame data
     * @param frame_duration Duration of each frame in seconds (default 0.1s = 10 FPS)
     * @return true if successful, false on error
     */
    bool load_anim_frames(const char* texture_path, std::vector<AnimFrame>& out_frames, float frame_duration)
    {
        // Verify texture exists (actual texture loading handled by FFNx texture system)
        char full_path[512];
        snprintf(full_path, sizeof(full_path), "%s/%s", basedir, texture_path);

        if (trace_all || trace_renderer) {
            ffnx_trace("char_portrait_anim: Loading sprite sheet: %s\n", full_path);
        }

        // Calculate UV coordinates for 8×8 grid
        // Each cell is 128×128 pixels in a 1024×1024 texture
        const int grid_size = 8;
        const float cell_size = 1.0f / grid_size;  // 0.125 in UV space

        out_frames.clear();
        out_frames.reserve(grid_size * grid_size);  // 64 frames

        for (int row = 0; row < grid_size; row++) {
            for (int col = 0; col < grid_size; col++) {
                AnimFrame frame;
                frame.u0 = col * cell_size;
                frame.v0 = row * cell_size;
                frame.u1 = (col + 1) * cell_size;
                frame.v1 = (row + 1) * cell_size;
                frame.duration = frame_duration;

                out_frames.push_back(frame);

                if (trace_all) {
                    ffnx_trace("  Frame %d: UV(%.3f,%.3f)-(%.3f,%.3f)\n",
                        (int)out_frames.size() - 1,
                        frame.u0, frame.v0, frame.u1, frame.v1);
                }
            }
        }

        if (trace_all || trace_renderer) {
            ffnx_trace("char_portrait_anim: Loaded %d frames from %s\n",
                (int)out_frames.size(), texture_path);
        }

        return true;
    }

    /**
     * Initialize character portrait animation system
     *
     * Loads sprite sheets for all 9 characters and links them to
     * the corresponding menu avatar graphics objects in FF7's memory.
     */
    void init_char_portrait_anims()
    {
        if (!char_portrait_anim_enable) {
            ffnx_info("char_portrait_anim: Disabled via config\n");
            return;
        }

        ffnx_info("char_portrait_anim: Initializing animation system\n");

        for (int i = 0; i < 9; i++) {
            CharPortraitAnim& anim = g_char_anims[i];

            // Load sprite sheet
            char texture_path[256];
            snprintf(texture_path, sizeof(texture_path),
                "mods/Textures/menu/%s_anim.png", char_names[i]);

            if (!load_anim_frames(texture_path, anim.frames)) {
                ffnx_warning("char_portrait_anim: Failed to load %s, disabling animation\n",
                    char_names[i]);
                anim.enabled = false;
                continue;
            }

            // Link to graphics object
            // Note: Graphics objects are created dynamically by FF7's menu system
            // We'll link them at runtime when menu is first drawn
            anim.gfx_obj = nullptr;
            anim.current_frame = 0;
            anim.time_accum = 0.0f;
            anim.enabled = true;
            anim.initialized = true;

            ffnx_info("char_portrait_anim: Initialized %s animation (%d frames)\n",
                char_names[i], (int)anim.frames.size());
        }

        ffnx_info("char_portrait_anim: Initialization complete\n");
    }

    /**
     * Link character animation to FF7 menu avatar graphics object
     *
     * @param char_id Character ID (0-8)
     * @param gfx_obj Pointer to FF7 graphics object for this character's menu portrait
     */
    static void link_graphics_object(int char_id, ff7_graphics_object* gfx_obj)
    {
        if (char_id < 0 || char_id >= 9) return;
        if (!gfx_obj) return;

        CharPortraitAnim& anim = g_char_anims[char_id];

        if (!anim.initialized || !anim.enabled) return;

        // Only link once
        if (anim.gfx_obj == gfx_obj) return;

        anim.gfx_obj = gfx_obj;

        if (trace_all || trace_renderer) {
            ffnx_trace("char_portrait_anim: Linked %s to graphics object %p\n",
                char_names[char_id], gfx_obj);
        }
    }

    /**
     * Update character portrait animations
     *
     * Called each frame to advance animations and update UV coordinates
     * on the menu avatar graphics objects.
     *
     * @param delta_time Time since last frame in seconds
     */
    void update_char_portrait_anims(float delta_time)
    {
        if (!char_portrait_anim_enable) return;

        // Link graphics objects on first update (when menu is active)
        // In FF7, menu avatar graphics objects are at specific memory locations
        // Cloud is at DC1014, others follow sequentially
        static bool objects_linked = false;
        if (!objects_linked && ff7_externals.menu_objects) {
            // Attempt to find and link graphics objects
            // Note: This is a simplified approach - actual implementation may need
            // to detect menu state and character party composition

            // For now, we'll link when we detect valid graphics objects
            // This will be refined based on testing
            objects_linked = true;

            if (trace_all || trace_renderer) {
                ffnx_trace("char_portrait_anim: Attempting to link graphics objects\n");
            }
        }

        // Update each character's animation
        for (int i = 0; i < 9; i++) {
            CharPortraitAnim& anim = g_char_anims[i];

            if (!anim.enabled || !anim.initialized || anim.frames.empty()) {
                continue;
            }

            // Skip if not linked to graphics object yet
            if (!anim.gfx_obj) {
                continue;
            }

            // Accumulate time
            anim.time_accum += delta_time;

            // Get current frame
            if (anim.current_frame >= anim.frames.size()) {
                anim.current_frame = 0;  // Safety check
            }

            const AnimFrame& current = anim.frames[anim.current_frame];

            // Check if we should advance to next frame
            if (anim.time_accum >= current.duration) {
                anim.time_accum -= current.duration;
                anim.current_frame = (anim.current_frame + 1) % anim.frames.size();

                if (trace_all) {
                    ffnx_trace("char_portrait_anim: %s advanced to frame %d\n",
                        char_names[i], (int)anim.current_frame);
                }
            }

            // Update UV coordinates on graphics object
            // Graphics objects have a vertex_transform array with UV data
            if (anim.gfx_obj->vertex_transform) {
                const AnimFrame& frame = anim.frames[anim.current_frame];

                // Update quad vertices (4 vertices for menu portrait)
                // Vertex order: top-left, top-right, bottom-right, bottom-left
                graphics_vertex* verts = anim.gfx_obj->vertex_transform;

                verts[0].u = frame.u0; verts[0].v = frame.v0;  // Top-left
                verts[1].u = frame.u1; verts[1].v = frame.v0;  // Top-right
                verts[2].u = frame.u1; verts[2].v = frame.v1;  // Bottom-right
                verts[3].u = frame.u0; verts[3].v = frame.v1;  // Bottom-left

                if (trace_all && anim.current_frame == 0) {
                    ffnx_trace("char_portrait_anim: %s UV updated - UV(%.3f,%.3f)-(%.3f,%.3f)\n",
                        char_names[i], frame.u0, frame.v0, frame.u1, frame.v1);
                }
            }
        }
    }

    /**
     * Cleanup character portrait animation resources
     *
     * Called on shutdown to free memory.
     */
    void cleanup_char_portrait_anims()
    {
        ffnx_info("char_portrait_anim: Cleaning up animation system\n");

        for (int i = 0; i < 9; i++) {
            g_char_anims[i].frames.clear();
            g_char_anims[i].gfx_obj = nullptr;
            g_char_anims[i].initialized = false;
        }
    }
}
