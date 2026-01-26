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

#include "speaker_inference.h"
#include <vector>

namespace FFNx
{
    /**
     * @brief Portrait Layout Manager
     *
     * Calculates portrait position, tail direction, and fade orientation
     * based on dialogue box position and speaker location.
     */
    class PortraitLayoutManager
    {
    public:
        /**
         * @brief Fade direction for portrait gradient
         */
        enum FadeDirection
        {
            FADE_RIGHT = 0,  // Portrait fades toward right (portrait on left of box)
            FADE_LEFT = 1,   // Portrait fades toward left (portrait on right of box)
            FADE_DOWN = 2,   // Portrait fades downward (portrait above box)
            FADE_UP = 3      // Portrait fades upward (portrait below box)
        };

        /**
         * @brief Calculated layout for portrait and dialogue box
         */
        struct PortraitLayout
        {
            // Portrait position
            float portrait_x;
            float portrait_y;
            float portrait_width;
            float portrait_height;

            // Tail/pointer geometry
            float tail_start_x;  // Portrait-side tail point
            float tail_start_y;
            float tail_end_x;    // Speaker-side tail point
            float tail_end_y;
            float tail_rotation; // Radians

            // Fade direction
            FadeDirection fade_direction;

            // Placement metadata
            bool auto_positioned;  // True if auto-calculated, false if manual override
            float confidence;      // How good is this layout (0.0-1.0)
        };

        /**
         * @brief Calculate optimal portrait layout for dialogue box
         *
         * @param box_x Dialogue box X position
         * @param box_y Dialogue box Y position
         * @param box_width Dialogue box width
         * @param box_height Dialogue box height
         * @param speaker Speaker information from inference engine
         * @param manual_override True to use manual positioning from config
         * @return PortraitLayout Calculated layout
         */
        static PortraitLayout calculate_layout(
            float box_x,
            float box_y,
            float box_width,
            float box_height,
            const SpeakerInference::SpeakerInfo& speaker,
            bool manual_override = false
        );

        /**
         * @brief Resolve conflicts between multiple portrait layouts
         *
         * Adjusts portrait positions to prevent overlaps when multiple
         * dialogue boxes are visible simultaneously.
         *
         * @param layouts Vector of layouts to resolve (modified in-place)
         */
        static void resolve_multi_box_conflicts(std::vector<PortraitLayout>& layouts);

    private:
        /**
         * @brief Determine which side of dialogue box to place portrait
         *
         * @param box_x Dialogue box X
         * @param box_center_x Dialogue box center X
         * @param speaker_x Speaker screen X
         * @return int 0=left, 1=right, 2=above, 3=below
         */
        static int determine_portrait_side(float box_x, float box_center_x, float speaker_x);

        /**
         * @brief Calculate tail vertices for pointer triangle
         *
         * @param portrait_x Portrait X
         * @param portrait_y Portrait Y
         * @param portrait_width Portrait width
         * @param portrait_height Portrait height
         * @param speaker_x Speaker screen X
         * @param speaker_y Speaker screen Y
         * @param out_start_x Output: tail start X (portrait edge)
         * @param out_start_y Output: tail start Y
         * @param out_end_x Output: tail end X (speaker position)
         * @param out_end_y Output: tail end Y
         * @param out_rotation Output: tail rotation in radians
         */
        static void calculate_tail_geometry(
            float portrait_x, float portrait_y,
            float portrait_width, float portrait_height,
            float speaker_x, float speaker_y,
            float* out_start_x, float* out_start_y,
            float* out_end_x, float* out_end_y,
            float* out_rotation
        );

        /**
         * @brief Check if two portrait layouts overlap
         *
         * @param a First layout
         * @param b Second layout
         * @return true if layouts overlap, false otherwise
         */
        static bool layouts_overlap(const PortraitLayout& a, const PortraitLayout& b);

        // Constants for layout calculation
        static constexpr float PORTRAIT_DEFAULT_WIDTH = 128.0f;
        static constexpr float PORTRAIT_DEFAULT_HEIGHT = 128.0f;
        static constexpr float PORTRAIT_MARGIN = 16.0f;  // Gap between portrait and dialogue box
        static constexpr float TAIL_MAX_LENGTH = 100.0f; // Maximum tail length (from config)
    };
}
