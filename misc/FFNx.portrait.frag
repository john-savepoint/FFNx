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

// Character Portrait Fragment Shader
// Composite rendering: dialogue box + portrait + gradient fade + glow + tail

$input v_color0, v_texcoord0, v_position

#include <bgfx/bgfx_shader.sh>

SAMPLER2D(tex_portrait, 0);   // Portrait texture (RGBA)
SAMPLER2D(tex_dialogue, 1);   // Dialogue box background texture (RGBA)
SAMPLER2D(tex_tail, 2);       // Tail/pointer SDF texture (R channel = distance field)

uniform vec4 PortraitParams;
#define fadeWidth       PortraitParams.x  // Gradient fade width (0.0-1.0)
#define fadeDirection   int(PortraitParams.y)  // 0=right, 1=left, 2=down, 3=up
#define glowIntensity   PortraitParams.z  // Edge glow intensity (0.0-1.0)
#define tailRotation    PortraitParams.w  // Tail rotation in radians (not used in shader)

uniform vec4 PortraitColor;  // Portrait tint color (RGBA)
uniform vec4 GlowColor;      // Edge glow color (RGBA)

// Calculate fade factor based on UV and fade direction
float calculateFade(vec2 uv, int direction)
{
    if (direction == 0)  // Fade RIGHT
    {
        // Portrait on left, fades toward right edge
        return smoothstep(1.0 - fadeWidth, 1.0, uv.x);
    }
    else if (direction == 1)  // Fade LEFT
    {
        // Portrait on right, fades toward left edge
        return smoothstep(fadeWidth, 0.0, uv.x);
    }
    else if (direction == 2)  // Fade DOWN
    {
        // Portrait above, fades toward bottom edge
        return smoothstep(1.0 - fadeWidth, 1.0, uv.y);
    }
    else  // Fade UP (direction == 3)
    {
        // Portrait below, fades toward top edge
        return smoothstep(fadeWidth, 0.0, uv.y);
    }
}

void main()
{
    // Initialize with transparent black
    vec4 result = vec4(0.0, 0.0, 0.0, 0.0);

    // Layer 1: Dialogue box background
    vec4 dialogueLayer = texture2D(tex_dialogue, v_texcoord0);
    result = dialogueLayer;

    // Layer 2: Portrait with edge fade
    vec4 portraitLayer = texture2D(tex_portrait, v_texcoord0);

    // Apply gradient fade
    float fadeFactor = 1.0 - calculateFade(v_texcoord0, fadeDirection);
    portraitLayer.a *= fadeFactor;

    // Apply portrait tint color (if specified)
    if (PortraitColor.a > 0.01)
    {
        portraitLayer.rgb = mix(portraitLayer.rgb, PortraitColor.rgb, PortraitColor.a);
    }

    // Composite portrait over dialogue box (alpha blending)
    result.rgb = mix(result.rgb, portraitLayer.rgb, portraitLayer.a);
    result.a = max(result.a, portraitLayer.a);

    // Layer 3: Glow effect on portrait edge
    if (glowIntensity > 0.01)
    {
        // Calculate distance from fade edge (0 at edge, 1 at center/far side)
        float edgeDistance = abs(fadeFactor - 0.5) * 2.0;

        // Glow is strongest at the fade edge
        float glowValue = (1.0 - edgeDistance) * glowIntensity;

        // Apply glow color (additive blend)
        result.rgb = mix(result.rgb, GlowColor.rgb, glowValue * (1.0 - result.a));
        result.a = max(result.a, glowValue * GlowColor.a);
    }

    // Layer 4: Tail/pointer (SDF-based triangle)
    vec4 tailLayer = texture2D(tex_tail, v_texcoord0);

    // Tail SDF: R channel contains distance field
    // Values > 0.5 are inside the triangle, < 0.5 are outside
    if (tailLayer.r > 0.5)
    {
        // Smooth anti-aliased edge
        float tailAlpha = smoothstep(0.45, 0.55, tailLayer.r);

        // Use portrait color for tail
        vec3 tailColor = PortraitColor.rgb;
        if (PortraitColor.a < 0.01)
        {
            // If no tint specified, use white
            tailColor = vec3(1.0, 1.0, 1.0);
        }

        // Composite tail over current result
        result.rgb = mix(result.rgb, tailColor, tailAlpha);
        result.a = max(result.a, tailAlpha);
    }

    // Apply vertex color modulation
    result *= v_color0;

    // Output final composited color
    gl_FragColor = result;
}
