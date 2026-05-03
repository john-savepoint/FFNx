/****************************************************************************/
//    Copyright (C) 2025 John Zealand-Doyle                                //
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

#include "sdf_debug.h"
#include "cfg.h"
#include "common.h"

#include <imgui.h>

void sdf_debug(bool* isOpen)
{
    if (!ImGui::Begin("SDF Font Laboratory", isOpen, ImGuiWindowFlags_::ImGuiWindowFlags_None))
    {
        ImGui::End();
        return;
    }

    ImGui::Text("Real-time SDF Font Styling & Effects Laboratory");
    ImGui::Separator();

    // Enable/disable checkbox
    ImGui::Checkbox("Enable SDF Fonts", &enable_sdf_fonts);
    ImGui::Spacing();

    // === TABS FOR ORGANIZATION ===
    if (ImGui::BeginTabBar("SDFTabs"))
    {
        // === BASIC TAB ===
        if (ImGui::BeginTabItem("Basic"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Core Text Parameters");
            ImGui::Separator();

            ImGui::DragFloat("Pixel Range", &sdf_pixel_range, 0.1f, 0.5f, 10.0f, "%.1f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Distance field spread\nHigher = smoother but blurrier\nRecommended: 3.0-5.0");

            ImGui::DragFloat("Thickness", &sdf_thickness, 0.05f, -1.0f, 1.0f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Glyph weight adjustment\n0.0 = normal\nPositive = bolder\nNegative = thinner");

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Text("Quick Presets");

            if (ImGui::Button("Thin", ImVec2(70, 0)))
                sdf_thickness = -0.3f;
            ImGui::SameLine();
            if (ImGui::Button("Normal", ImVec2(70, 0)))
                sdf_thickness = 0.0f;
            ImGui::SameLine();
            if (ImGui::Button("Bold", ImVec2(70, 0)))
                sdf_thickness = 0.3f;

            ImGui::Spacing();
            if (ImGui::Button("Reset Basic", ImVec2(120, 0)))
            {
                sdf_pixel_range = 4.0f;
                sdf_thickness = 0.0f;
            }

            ImGui::EndTabItem();
        }

        // === SHADOW TAB ===
        if (ImGui::BeginTabItem("Shadow"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Shadow Effects");
            ImGui::Separator();

            ImGui::DragFloat("Shadow X Offset", &sdf_shadow_offset_x, 0.1f, -10.0f, 10.0f, "%.1f px");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Horizontal shadow displacement\nNegative = left, Positive = right");

            ImGui::DragFloat("Shadow Y Offset", &sdf_shadow_offset_y, 0.1f, -10.0f, 10.0f, "%.1f px");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Vertical shadow displacement\nNegative = up, Positive = down");

            ImGui::DragFloat("Shadow Blur", &sdf_shadow_blur, 0.1f, 0.0f, 5.0f, "%.1f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Shadow softness\n0 = hard edge, higher = softer");

            ImGui::DragFloat("Shadow Opacity", &sdf_shadow_opacity, 0.05f, 0.0f, 1.0f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Shadow transparency\n0 = invisible, 1 = opaque");

            ImGui::Spacing();
            ImGui::ColorEdit3("Shadow Color", &sdf_shadow_color_r);

            ImGui::Spacing();
            if (ImGui::Button("Reset Shadow", ImVec2(120, 0)))
            {
                sdf_shadow_offset_x = 1.0f;
                sdf_shadow_offset_y = 1.0f;
                sdf_shadow_blur = 0.0f;
                sdf_shadow_opacity = 0.5f;
                sdf_shadow_color_r = 0.0f;
                sdf_shadow_color_g = 0.0f;
                sdf_shadow_color_b = 0.0f;
            }

            ImGui::EndTabItem();
        }

        // === OUTLINE TAB ===
        if (ImGui::BeginTabItem("Outline"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Outline/Border Effects");
            ImGui::Separator();

            ImGui::Text("Outer Outline");
            ImGui::DragFloat("Outline Width", &sdf_outline_width, 0.1f, 0.0f, 5.0f, "%.1f px");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Outer border thickness\n0 = no outline");

            ImGui::DragFloat("Outline Opacity", &sdf_outline_opacity, 0.05f, 0.0f, 1.0f, "%.2f");
            ImGui::ColorEdit3("Outline Color", &sdf_outline_color_r);

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Text("Inner Outline");

            ImGui::DragFloat("Inner Width", &sdf_inner_outline_width, 0.1f, 0.0f, 5.0f, "%.1f px");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Inner border thickness\nCreates border-within-border effect");

            ImGui::DragFloat("Inner Opacity", &sdf_inner_outline_opacity, 0.05f, 0.0f, 1.0f, "%.2f");
            ImGui::ColorEdit3("Inner Color", &sdf_inner_outline_color_r);

            ImGui::Spacing();
            if (ImGui::Button("Reset Outlines", ImVec2(120, 0)))
            {
                sdf_outline_width = 0.0f;
                sdf_outline_opacity = 1.0f;
                sdf_outline_color_r = 1.0f;
                sdf_outline_color_g = 1.0f;
                sdf_outline_color_b = 1.0f;
                sdf_inner_outline_width = 0.0f;
                sdf_inner_outline_opacity = 1.0f;
                sdf_inner_outline_color_r = 0.5f;
                sdf_inner_outline_color_g = 0.5f;
                sdf_inner_outline_color_b = 0.5f;
            }

            ImGui::EndTabItem();
        }

        // === COLOR TAB ===
        if (ImGui::BeginTabItem("Color"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Text Color Customization");
            ImGui::Separator();

            ImGui::Checkbox("Override Text Color", &sdf_text_color_enable);
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Enable custom text color\nWhen off, uses game's original colors");

            if (sdf_text_color_enable)
            {
                ImGui::ColorEdit3("Text Color", &sdf_text_color_r);
            }

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Quick Color Presets");
            ImGui::Spacing();

            if (ImGui::Button("White", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 1.0f; sdf_text_color_g = 1.0f; sdf_text_color_b = 1.0f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Red", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 1.0f; sdf_text_color_g = 0.0f; sdf_text_color_b = 0.0f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Green", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 0.0f; sdf_text_color_g = 1.0f; sdf_text_color_b = 0.0f;
            }

            if (ImGui::Button("Blue", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 0.0f; sdf_text_color_g = 0.5f; sdf_text_color_b = 1.0f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Yellow", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 1.0f; sdf_text_color_g = 1.0f; sdf_text_color_b = 0.0f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Purple", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 0.8f; sdf_text_color_g = 0.2f; sdf_text_color_b = 1.0f;
            }

            if (ImGui::Button("Orange", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 1.0f; sdf_text_color_g = 0.6f; sdf_text_color_b = 0.0f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Pink", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 1.0f; sdf_text_color_g = 0.4f; sdf_text_color_b = 0.7f;
            }
            ImGui::SameLine();
            if (ImGui::Button("Cyan", ImVec2(80, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 0.0f; sdf_text_color_g = 1.0f; sdf_text_color_b = 1.0f;
            }

            ImGui::EndTabItem();
        }

        // === GLOW TAB ===
        if (ImGui::BeginTabItem("Glow"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Glow/Halo Effect");
            ImGui::Separator();

            ImGui::DragFloat("Glow Radius", &sdf_glow_radius, 0.1f, 0.0f, 5.0f, "%.1f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Glow spread distance\n0 = no glow");

            ImGui::DragFloat("Glow Intensity", &sdf_glow_intensity, 0.05f, 0.0f, 2.0f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Glow brightness\n0 = off, higher = brighter");

            ImGui::ColorEdit3("Glow Color", &sdf_glow_color_r);

            ImGui::Spacing();
            ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.4f, 1.0f), "Try: Radius 2.0, Intensity 1.0, Yellow Color");

            ImGui::Spacing();
            if (ImGui::Button("Reset Glow", ImVec2(120, 0)))
            {
                sdf_glow_radius = 0.0f;
                sdf_glow_intensity = 0.0f;
                sdf_glow_color_r = 1.0f;
                sdf_glow_color_g = 1.0f;
                sdf_glow_color_b = 0.0f;
            }

            ImGui::EndTabItem();
        }

        // === ANIMATION TAB ===
        if (ImGui::BeginTabItem("Animation"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Dynamic Effects & Animation");
            ImGui::Separator();

            ImGui::Checkbox("Rainbow Color Cycle", &sdf_color_cycle_enable);
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Animated rainbow text!\nCycles through all hues continuously");

            if (sdf_color_cycle_enable)
            {
                ImGui::Indent();
                ImGui::DragFloat("Cycle Speed", &sdf_anim_speed, 0.1f, 0.1f, 5.0f, "%.1f");
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Animation speed\n1.0 = normal, higher = faster");

                ImGui::DragFloat("Per-Char Offset", &sdf_cycle_offset, 1.0f, 0.0f, 50.0f, "%.1f");
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Color offset between characters\n0 = all same color\n10+ = each char different color");
                ImGui::Unindent();
            }

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Spacing();

            ImGui::Checkbox("Pulse Effect", &sdf_pulse_enable);
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Text breathes/pulses in and out");

            ImGui::Spacing();
            ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.4f, 1.0f), "Warning: Animations may be distracting!");

            ImGui::Spacing();
            if (ImGui::Button("Disable All", ImVec2(120, 0)))
            {
                sdf_color_cycle_enable = false;
                sdf_pulse_enable = false;
                sdf_anim_speed = 1.0f;
            }

            ImGui::EndTabItem();
        }

        // === TRANSFORM TAB ===
        if (ImGui::BeginTabItem("Transform"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Text Transformation");
            ImGui::Separator();

            ImGui::DragFloat("Italic Slant", &sdf_italic_slant, 0.01f, -0.5f, 0.5f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Italic/slant effect\nNegative = left lean\nPositive = right lean (italic)\n0.15 = typical italic");

            ImGui::DragFloat("Horizontal Skew", &sdf_skew_x, 0.01f, -0.5f, 0.5f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Skew text horizontally");

            ImGui::DragFloat("Vertical Skew", &sdf_skew_y, 0.01f, -0.5f, 0.5f, "%.2f");
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Skew text vertically");

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Text("Quick Presets");

            if (ImGui::Button("Normal", ImVec2(100, 0)))
            {
                sdf_italic_slant = 0.0f;
                sdf_skew_x = 0.0f;
                sdf_skew_y = 0.0f;
            }

            if (ImGui::Button("Italic", ImVec2(100, 0)))
            {
                sdf_italic_slant = 0.15f;
                sdf_skew_x = 0.0f;
                sdf_skew_y = 0.0f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Classic italic slant");

            if (ImGui::Button("Heavy Italic", ImVec2(100, 0)))
            {
                sdf_italic_slant = 0.3f;
                sdf_skew_x = 0.0f;
                sdf_skew_y = 0.0f;
            }

            ImGui::Spacing();
            if (ImGui::Button("Reset Transform", ImVec2(120, 0)))
            {
                sdf_italic_slant = 0.0f;
                sdf_skew_x = 0.0f;
                sdf_skew_y = 0.0f;
            }

            ImGui::EndTabItem();
        }

        // === PRESETS TAB ===
        if (ImGui::BeginTabItem("Presets"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Quick Style Presets");
            ImGui::Separator();
            ImGui::Spacing();

            if (ImGui::Button("Classic (Default)", ImVec2(200, 0)))
            {
                sdf_pixel_range = 4.0f;
                sdf_thickness = 0.5f;
                sdf_shadow_offset_x = 1.0f;
                sdf_shadow_offset_y = 1.0f;
                sdf_shadow_blur = 0.0f;
                sdf_shadow_opacity = 0.5f;
                sdf_outline_width = 0.0f;
                sdf_inner_outline_width = 0.0f;
                sdf_glow_radius = 0.0f;
                sdf_text_color_enable = false;
                sdf_color_cycle_enable = false;
                sdf_pulse_enable = false;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Clean, readable text with subtle shadow");

            if (ImGui::Button("Bold with Black Outline", ImVec2(200, 0)))
            {
                sdf_thickness = 0.7f;
                sdf_outline_width = 0.8f;
                sdf_outline_opacity = 1.0f;
                sdf_outline_color_r = 0.0f;
                sdf_outline_color_g = 0.0f;
                sdf_outline_color_b = 0.0f;
                sdf_shadow_offset_x = 1.5f;
                sdf_shadow_offset_y = 1.5f;
                sdf_shadow_opacity = 0.7f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Strong contrast for readability");

            if (ImGui::Button("Soft Glow (Fantasy Style)", ImVec2(200, 0))
)
            {
                sdf_glow_radius = 2.5f;
                sdf_glow_intensity = 1.2f;
                sdf_glow_color_r = 0.5f;
                sdf_glow_color_g = 0.8f;
                sdf_glow_color_b = 1.0f;
                sdf_shadow_opacity = 0.3f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Ethereal glowing text");

            if (ImGui::Button("Double Outline (Retro)", ImVec2(200, 0)))
            {
                sdf_thickness = 0.6f;
                sdf_outline_width = 1.2f;
                sdf_outline_opacity = 1.0f;
                sdf_outline_color_r = 0.0f;
                sdf_outline_color_g = 0.0f;
                sdf_outline_color_b = 0.0f;
                sdf_inner_outline_width = 0.5f;
                sdf_inner_outline_opacity = 1.0f;
                sdf_inner_outline_color_r = 1.0f;
                sdf_inner_outline_color_g = 0.8f;
                sdf_inner_outline_color_b = 0.0f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Classic arcade-style borders");

            if (ImGui::Button("RAINBOW RAVE!", ImVec2(200, 0)))
            {
                sdf_color_cycle_enable = true;
                sdf_anim_speed = 2.0f;
                sdf_glow_radius = 3.0f;
                sdf_glow_intensity = 1.5f;
                sdf_glow_color_r = 1.0f;
                sdf_glow_color_g = 1.0f;
                sdf_glow_color_b = 1.0f;
                sdf_pulse_enable = true;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Maximum chaos! (Not recommended for gameplay)");

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f), "Extreme Presets (Use with caution!)");

            if (ImGui::Button("Ultra Thicc", ImVec2(200, 0)))
            {
                sdf_thickness = 1.5f;
                sdf_outline_width = 2.0f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Extremely bold text");

            if (ImGui::Button("Ghost Mode", ImVec2(200, 0)))
            {
                sdf_text_color_enable = true;
                sdf_text_color_r = 0.5f;
                sdf_text_color_g = 0.5f;
                sdf_text_color_b = 0.5f;
                sdf_glow_radius = 4.0f;
                sdf_glow_intensity = 2.0f;
                sdf_glow_color_r = 0.3f;
                sdf_glow_color_g = 0.9f;
                sdf_glow_color_b = 0.3f;
                sdf_shadow_opacity = 0.0f;
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Spooky translucent text");

            ImGui::EndTabItem();
        }

        // === EXPORT TAB ===
        if (ImGui::BeginTabItem("Export"))
        {
            ImGui::TextColored(ImVec4(0.4f, 0.8f, 1.0f, 1.0f), "Save Configuration");
            ImGui::Separator();
            ImGui::Spacing();

            if (ImGui::Button("Show Config Values", ImVec2(200, 0)))
            {
                ImGui::OpenPopup("Config Export");
            }

            if (ImGui::BeginPopup("Config Export"))
            {
                ImGui::Text("Copy these values to FFNx.toml:");
                ImGui::Separator();
                ImGui::Text("# Basic");
                ImGui::Text("sdf_pixel_range = %.1f", sdf_pixel_range);
                ImGui::Text("sdf_thickness = %.2f", sdf_thickness);
                ImGui::Text("# Shadow");
                ImGui::Text("sdf_shadow_offset_x = %.1f", sdf_shadow_offset_x);
                ImGui::Text("sdf_shadow_offset_y = %.1f", sdf_shadow_offset_y);
                ImGui::Text("sdf_shadow_blur = %.1f", sdf_shadow_blur);
                ImGui::Text("sdf_shadow_opacity = %.2f", sdf_shadow_opacity);
                ImGui::Text("sdf_shadow_color_r = %.2f", sdf_shadow_color_r);
                ImGui::Text("sdf_shadow_color_g = %.2f", sdf_shadow_color_g);
                ImGui::Text("sdf_shadow_color_b = %.2f", sdf_shadow_color_b);
                ImGui::Text("# Outline");
                ImGui::Text("sdf_outline_width = %.1f", sdf_outline_width);
                ImGui::Text("sdf_outline_opacity = %.2f", sdf_outline_opacity);
                ImGui::Text("sdf_outline_color_r = %.2f", sdf_outline_color_r);
                ImGui::Text("sdf_outline_color_g = %.2f", sdf_outline_color_g);
                ImGui::Text("sdf_outline_color_b = %.2f", sdf_outline_color_b);
                ImGui::Text("# Inner Outline");
                ImGui::Text("sdf_inner_outline_width = %.1f", sdf_inner_outline_width);
                ImGui::Text("sdf_inner_outline_opacity = %.2f", sdf_inner_outline_opacity);
                ImGui::Text("sdf_inner_outline_color_r = %.2f", sdf_inner_outline_color_r);
                ImGui::Text("sdf_inner_outline_color_g = %.2f", sdf_inner_outline_color_g);
                ImGui::Text("sdf_inner_outline_color_b = %.2f", sdf_inner_outline_color_b);
                ImGui::Text("# Glow");
                ImGui::Text("sdf_glow_radius = %.1f", sdf_glow_radius);
                ImGui::Text("sdf_glow_intensity = %.2f", sdf_glow_intensity);
                ImGui::Text("sdf_glow_color_r = %.2f", sdf_glow_color_r);
                ImGui::Text("sdf_glow_color_g = %.2f", sdf_glow_color_g);
                ImGui::Text("sdf_glow_color_b = %.2f", sdf_glow_color_b);
                ImGui::Text("# Text Color");
                ImGui::Text("sdf_text_color_enable = %s", sdf_text_color_enable ? "true" : "false");
                ImGui::Text("sdf_text_color_r = %.2f", sdf_text_color_r);
                ImGui::Text("sdf_text_color_g = %.2f", sdf_text_color_g);
                ImGui::Text("sdf_text_color_b = %.2f", sdf_text_color_b);
                ImGui::Text("# Animation");
                ImGui::Text("sdf_anim_speed = %.1f", sdf_anim_speed);
                ImGui::Text("sdf_color_cycle_enable = %s", sdf_color_cycle_enable ? "true" : "false");
                ImGui::Text("sdf_pulse_enable = %s", sdf_pulse_enable ? "true" : "false");
                ImGui::EndPopup();
            }

            ImGui::Spacing();
            ImGui::TextWrapped("Tip: Changes apply immediately. Copy the values above to FFNx.toml to make them permanent.");

            ImGui::EndTabItem();
        }

        ImGui::EndTabBar();
    }

    ImGui::End();
}
