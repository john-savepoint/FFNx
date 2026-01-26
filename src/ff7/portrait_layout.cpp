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

#include "portrait_layout.h"
#include "../log.h"
#include "../cfg.h"
#include <cmath>
#include <algorithm>

namespace FFNx
{
    PortraitLayoutManager::PortraitLayout PortraitLayoutManager::calculate_layout(
        float box_x,
        float box_y,
        float box_width,
        float box_height,
        const SpeakerInference::SpeakerInfo& speaker,
        bool manual_override
    )
    {
        PortraitLayout layout;
        layout.portrait_width = PORTRAIT_DEFAULT_WIDTH;
        layout.portrait_height = PORTRAIT_DEFAULT_HEIGHT;
        layout.auto_positioned = !manual_override;
        layout.confidence = speaker.confidence;

        // Manual override positioning
        if (manual_override && !portrait_auto_placement)
        {
            layout.portrait_x = static_cast<float>(portrait_manual_x);
            layout.portrait_y = static_cast<float>(portrait_manual_y);
            layout.fade_direction = static_cast<FadeDirection>(portrait_manual_fade_direction);
            layout.auto_positioned = false;

            if (trace_all)
            {
                ffnx_trace("PortraitLayoutManager::calculate_layout: Using manual override (%f, %f)\n",
                          layout.portrait_x, layout.portrait_y);
            }
        }
        else
        {
            // Automatic placement based on dialogue box and speaker position
            float box_center_x = box_x + (box_width / 2.0f);
            float box_center_y = box_y + (box_height / 2.0f);

            // Determine which side of the dialogue box to place portrait
            int side = determine_portrait_side(box_x, box_center_x, speaker.screen_x);

            switch (side)
            {
                case 0: // Left of dialogue box
                    layout.portrait_x = box_x - layout.portrait_width - PORTRAIT_MARGIN;
                    layout.portrait_y = box_y + (box_height - layout.portrait_height) / 2.0f;
                    layout.fade_direction = FADE_RIGHT;
                    break;

                case 1: // Right of dialogue box
                    layout.portrait_x = box_x + box_width + PORTRAIT_MARGIN;
                    layout.portrait_y = box_y + (box_height - layout.portrait_height) / 2.0f;
                    layout.fade_direction = FADE_LEFT;
                    break;

                case 2: // Above dialogue box
                    layout.portrait_x = box_center_x - (layout.portrait_width / 2.0f);
                    layout.portrait_y = box_y - layout.portrait_height - PORTRAIT_MARGIN;
                    layout.fade_direction = FADE_DOWN;
                    break;

                case 3: // Below dialogue box
                    layout.portrait_x = box_center_x - (layout.portrait_width / 2.0f);
                    layout.portrait_y = box_y + box_height + PORTRAIT_MARGIN;
                    layout.fade_direction = FADE_UP;
                    break;

                default:
                    // Fallback to left side
                    layout.portrait_x = box_x - layout.portrait_width - PORTRAIT_MARGIN;
                    layout.portrait_y = box_y + (box_height - layout.portrait_height) / 2.0f;
                    layout.fade_direction = FADE_RIGHT;
                    break;
            }
        }

        // Calculate tail/pointer geometry
        calculate_tail_geometry(
            layout.portrait_x, layout.portrait_y,
            layout.portrait_width, layout.portrait_height,
            speaker.screen_x, speaker.screen_y,
            &layout.tail_start_x, &layout.tail_start_y,
            &layout.tail_end_x, &layout.tail_end_y,
            &layout.tail_rotation
        );

        if (trace_all || trace_renderer)
        {
            ffnx_trace("PortraitLayoutManager::calculate_layout: Portrait at (%f, %f), fade %d, confidence %f\n",
                      layout.portrait_x, layout.portrait_y, layout.fade_direction, layout.confidence);
        }

        return layout;
    }

    void PortraitLayoutManager::resolve_multi_box_conflicts(std::vector<PortraitLayout>& layouts)
    {
        if (layouts.size() <= 1)
        {
            return; // No conflicts possible
        }

        // Sort layouts by Y position (top to bottom)
        std::sort(layouts.begin(), layouts.end(),
            [](const PortraitLayout& a, const PortraitLayout& b) {
                return a.portrait_y < b.portrait_y;
            });

        // Iteratively resolve overlaps (max 3 passes)
        const int MAX_ITERATIONS = 3;
        for (int iteration = 0; iteration < MAX_ITERATIONS; iteration++)
        {
            bool had_conflicts = false;

            for (size_t i = 0; i < layouts.size() - 1; i++)
            {
                for (size_t j = i + 1; j < layouts.size(); j++)
                {
                    if (layouts_overlap(layouts[i], layouts[j]))
                    {
                        // Shift lower portrait down by overlap amount + spacing
                        float overlap_y = (layouts[i].portrait_y + layouts[i].portrait_height) -
                                         layouts[j].portrait_y;
                        float shift = overlap_y + PORTRAIT_MARGIN;

                        layouts[j].portrait_y += shift;

                        // Recalculate tail for shifted portrait
                        // (keeping speaker position the same)
                        float speaker_x = layouts[j].tail_end_x;
                        float speaker_y = layouts[j].tail_end_y;

                        calculate_tail_geometry(
                            layouts[j].portrait_x, layouts[j].portrait_y,
                            layouts[j].portrait_width, layouts[j].portrait_height,
                            speaker_x, speaker_y,
                            &layouts[j].tail_start_x, &layouts[j].tail_start_y,
                            &layouts[j].tail_end_x, &layouts[j].tail_end_y,
                            &layouts[j].tail_rotation
                        );

                        had_conflicts = true;

                        if (trace_all)
                        {
                            ffnx_trace("PortraitLayoutManager::resolve_multi_box_conflicts: "
                                      "Shifted portrait %zu down by %f pixels\n", j, shift);
                        }
                    }
                }
            }

            if (!had_conflicts)
            {
                break; // All conflicts resolved
            }
        }
    }

    int PortraitLayoutManager::determine_portrait_side(float box_x, float box_center_x, float speaker_x)
    {
        // Determine horizontal placement based on speaker position relative to dialogue box
        if (speaker_x < box_center_x - 50.0f)
        {
            // Speaker is to the left of box center, place portrait on RIGHT
            return 1;
        }
        else if (speaker_x > box_center_x + 50.0f)
        {
            // Speaker is to the right of box center, place portrait on LEFT
            return 0;
        }
        else
        {
            // Speaker roughly centered, default to left side
            return 0;
        }

        // TODO: Implement above/below placement for extreme Y positions
        // This would check speaker_y vs box_y for vertical placement
    }

    void PortraitLayoutManager::calculate_tail_geometry(
        float portrait_x, float portrait_y,
        float portrait_width, float portrait_height,
        float speaker_x, float speaker_y,
        float* out_start_x, float* out_start_y,
        float* out_end_x, float* out_end_y,
        float* out_rotation
    )
    {
        // Calculate portrait center
        float portrait_center_x = portrait_x + (portrait_width / 2.0f);
        float portrait_center_y = portrait_y + (portrait_height / 2.0f);

        // Calculate angle from portrait center to speaker
        float dx = speaker_x - portrait_center_x;
        float dy = speaker_y - portrait_center_y;
        float angle = std::atan2(dy, dx);

        // Find point on portrait edge closest to speaker
        // (Simple approach: use portrait center for now)
        *out_start_x = portrait_center_x;
        *out_start_y = portrait_center_y;

        // Calculate tail end point (clamped to max tail length)
        float distance = std::sqrt(dx * dx + dy * dy);
        float tail_length = std::min(distance, portrait_tail_length);

        *out_end_x = portrait_center_x + std::cos(angle) * tail_length;
        *out_end_y = portrait_center_y + std::sin(angle) * tail_length;

        *out_rotation = angle;

        if (trace_all)
        {
            ffnx_trace("PortraitLayoutManager::calculate_tail_geometry: "
                      "Tail from (%f, %f) to (%f, %f), angle %f rad\n",
                      *out_start_x, *out_start_y, *out_end_x, *out_end_y, *out_rotation);
        }
    }

    bool PortraitLayoutManager::layouts_overlap(const PortraitLayout& a, const PortraitLayout& b)
    {
        // AABB (axis-aligned bounding box) overlap test
        bool overlap_x = (a.portrait_x < b.portrait_x + b.portrait_width) &&
                        (a.portrait_x + a.portrait_width > b.portrait_x);

        bool overlap_y = (a.portrait_y < b.portrait_y + b.portrait_height) &&
                        (a.portrait_y + a.portrait_height > b.portrait_y);

        return overlap_x && overlap_y;
    }
}
