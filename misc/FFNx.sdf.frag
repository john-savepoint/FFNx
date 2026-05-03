/****************************************************************************/
//    Copyright (C) 2026 John Zealand-Doyle                               //
//    Copyright (C) 2026 Claude Code                                       //
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
//    GNU General Public License for more details                          //
/****************************************************************************/

// SDF (Signed Distance Field) Font Fragment Shader - Enhanced Edition v2.1
// Fixed: Shadow behind text, better blur, per-character cycling, italic/skew

$input v_color0, v_texcoord0

#include <bgfx/bgfx_shader.sh>

SAMPLER2D(tex_0, 0);  // SDF texture (RGB channels contain distance field)

// Core parameters
uniform vec4 SDFParams;
#define pxRange SDFParams.x         // Distance field spread in pixels (default: 4.0)
#define thickness SDFParams.y       // Glyph thickness adjustment (default: 0.5)
#define shadowOffsetX SDFParams.z   // Shadow X offset in pixels
#define shadowOffsetY SDFParams.w   // Shadow Y offset in pixels

// Extended parameters 1
uniform vec4 SDFParams2;
#define shadowBlur SDFParams2.x     // Shadow blur/softness (0.0-10.0)
#define shadowOpacity SDFParams2.y  // Shadow transparency (0.0-1.0)
#define outlineWidth SDFParams2.z   // Outline thickness (0.0-5.0)
#define outlineOpacity SDFParams2.w // Outline opacity (0.0-1.0)

// Extended parameters 2
uniform vec4 SDFParams3;
#define innerOutlineWidth SDFParams3.x    // Inner outline thickness
#define innerOutlineOpacity SDFParams3.y  // Inner outline opacity
#define glowRadius SDFParams3.z           // Glow effect radius
#define glowIntensity SDFParams3.w        // Glow brightness

// Extended parameters 3 (Transform)
uniform vec4 SDFParams4;
#define italicSlant SDFParams4.x    // Italic slant amount (-0.5 to 0.5)
#define skewX SDFParams4.y          // Horizontal skew
#define skewY SDFParams4.z          // Vertical skew
#define unused1 SDFParams4.w        // Reserved

// Color parameters
uniform vec4 SDFTextColor;          // Text fill color override (RGB + enable flag in A)
uniform vec4 SDFShadowColor;        // Shadow color (RGB + unused)
uniform vec4 SDFOutlineColor;       // Outline color (RGB + unused)
uniform vec4 SDFInnerOutlineColor;  // Inner outline color (RGB + unused)
uniform vec4 SDFGlowColor;          // Glow effect color (RGB + unused)

// Animation parameters
uniform vec4 SDFAnimParams;
#define animSpeed SDFAnimParams.x         // Animation speed multiplier
#define animTime SDFAnimParams.y          // Current time for animation
#define colorCycleEnable SDFAnimParams.z  // Enable color cycling (0/1)
#define pulseEnable SDFAnimParams.w       // Enable pulse effect (0/1)

// Animation parameters 2
uniform vec4 SDFAnimParams2;
#define cycleOffset SDFAnimParams2.x      // Per-character color cycle offset
#define unused2 SDFAnimParams2.y
#define unused3 SDFAnimParams2.z
#define unused4 SDFAnimParams2.w

// Compute median of RGB channels
float median(float r, float g, float b) {
    return max(min(r, g), min(max(r, g), b));
}

// HSV to RGB conversion for color cycling
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Smooth step for better anti-aliasing
float smoothDistance(float distance, float width) {
    return smoothstep(-width, width, distance);
}

void main() {
    // Apply italic/skew transformation to UV coordinates
    vec2 uv = v_texcoord0;
    // Negative for correct italic direction, and scale down for subtlety
    uv.x -= uv.y * italicSlant * 0.3;  // Italic slant (negative + scaled)
    uv.x += uv.y * skewX * 0.3;        // Additional horizontal skew (scaled)
    uv.y += uv.x * skewY * 0.3;        // Vertical skew (scaled)

    // Sample the SDF texture with transformed UVs
    vec3 msd = texture2D(tex_0, uv).rgb;

    // Compute signed distance
    float sd = median(msd.r, msd.g, msd.b);
    float screenPxDistance = pxRange * (sd - 0.5);

    // Main text opacity with thickness adjustment
    // CORRECT: ADD thickness to expand, SUBTRACT to shrink
    // thickness range: -1.0 (thin) to +1.0 (bold), 0.0 = normal
    float textOpacity = smoothDistance(screenPxDistance + thickness, 0.5);

    // === GLOW EFFECT (FIXED) ===
    float glowValue = 0.0;
    if (glowRadius > 0.01 && glowIntensity > 0.01) {
        // Distance from edge of glyph
        float distFromEdge = abs(screenPxDistance);
        // Smooth falloff based on glow radius
        glowValue = (1.0 - smoothstep(0.0, glowRadius, distFromEdge)) * glowIntensity;
        // Only show glow where text isn't fully opaque
        glowValue *= (1.0 - textOpacity);
    }

    // === OUTLINE (OUTER) ===
    float outlineValue = 0.0;
    if (outlineWidth > 0.01 && outlineOpacity > 0.01) {
        float outlineDist = screenPxDistance + thickness;  // FIXED: + not -
        float outerEdge = outlineDist - outlineWidth;
        outlineValue = smoothDistance(outlineDist, 0.5) - smoothDistance(outerEdge, 0.5);
        outlineValue *= outlineOpacity;
    }

    // === INNER OUTLINE ===
    float innerOutlineValue = 0.0;
    if (innerOutlineWidth > 0.01 && innerOutlineOpacity > 0.01) {
        float innerDist = screenPxDistance + thickness + innerOutlineWidth;  // FIXED: + not -
        innerOutlineValue = smoothDistance(screenPxDistance + thickness, 0.5) - smoothDistance(innerDist, 0.5);  // FIXED
        innerOutlineValue *= innerOutlineOpacity;
    }

    // === SHADOW (FIXED - MULTI-SAMPLE BLUR) ===
    float shadowValue = 0.0;
    if (shadowOpacity > 0.01 && (abs(shadowOffsetX) > 0.01 || abs(shadowOffsetY) > 0.01)) {
        vec2 texelSize = vec2(1.0 / 1024.0, 1.0 / 1024.0);
        vec2 shadowOffset = vec2(shadowOffsetX, shadowOffsetY) * texelSize;

        if (shadowBlur < 0.1) {
            // Hard shadow - single sample
            vec3 shadowMsd = texture2D(tex_0, uv + shadowOffset).rgb;
            float shadowSd = median(shadowMsd.r, shadowMsd.g, shadowMsd.b);
            float shadowDistance = pxRange * (shadowSd - 0.5);
            shadowValue = smoothDistance(shadowDistance + thickness, 0.5);  // FIXED: + not -
        } else {
            // Soft shadow - multi-sample box blur
            float blurSteps = min(shadowBlur, 8.0);
            int samples = int(blurSteps) + 1;
            float sampleWeight = 1.0 / float(samples * samples);

            for (int y = 0; y < 9; y++) {
                if (y >= samples) break;
                for (int x = 0; x < 9; x++) {
                    if (x >= samples) break;

                    vec2 offset = shadowOffset + vec2(
                        (float(x) - blurSteps * 0.5) * texelSize.x,
                        (float(y) - blurSteps * 0.5) * texelSize.y
                    );

                    vec3 sampleMsd = texture2D(tex_0, uv + offset).rgb;
                    float sampleSd = median(sampleMsd.r, sampleMsd.g, sampleMsd.b);
                    float sampleDist = pxRange * (sampleSd - 0.5);
                    shadowValue += smoothDistance(sampleDist + thickness, 0.5) * sampleWeight;  // FIXED: + not -
                }
            }
        }
        shadowValue *= shadowOpacity;
    }

    // Discard if completely transparent
    if (textOpacity < 0.01 && shadowValue < 0.01 && outlineValue < 0.01 &&
        innerOutlineValue < 0.01 && glowValue < 0.01) {
        discard;
    }

    // === TEXT COLOR ===
    vec3 textColor = v_color0.rgb;

    // Override with custom color if enabled
    if (SDFTextColor.a > 0.5) {
        textColor = SDFTextColor.rgb;
    }

    // Apply color cycling animation with per-character offset
    if (colorCycleEnable > 0.5) {
        // Use UV.x as character position for cycling offset
        float charOffset = uv.x * cycleOffset;
        float hue = fract(animTime * animSpeed + charOffset);
        textColor = hsv2rgb(vec3(hue, 1.0, 1.0));
    }

    // Apply pulse animation to opacity
    float pulseMultiplier = 1.0;
    if (pulseEnable > 0.5) {
        pulseMultiplier = 0.7 + 0.3 * sin(animTime * animSpeed * 6.28318);
    }

    // === COMPOSITE LAYERS (FIXED - PROPER ALPHA BLENDING) ===
    // Layer order: shadow (back) → glow → outline → inner outline → text (front)

    vec4 result = vec4(0.0, 0.0, 0.0, 0.0);

    // Shadow layer (completely behind everything)
    if (shadowValue > 0.0) {
        vec4 shadowLayer = vec4(SDFShadowColor.rgb, shadowValue);
        result = shadowLayer;
    }

    // Glow layer
    if (glowValue > 0.0) {
        vec4 glowLayer = vec4(SDFGlowColor.rgb, glowValue);
        // Alpha blend over shadow
        result.rgb = mix(result.rgb, glowLayer.rgb, glowLayer.a);
        result.a = max(result.a, glowLayer.a);
    }

    // Outline layer
    if (outlineValue > 0.0) {
        vec4 outlineLayer = vec4(SDFOutlineColor.rgb, outlineValue);
        // Alpha blend over previous layers
        result.rgb = mix(result.rgb, outlineLayer.rgb, outlineLayer.a);
        result.a = max(result.a, outlineLayer.a);
    }

    // Inner outline layer
    if (innerOutlineValue > 0.0) {
        vec4 innerLayer = vec4(SDFInnerOutlineColor.rgb, innerOutlineValue);
        result.rgb = mix(result.rgb, innerLayer.rgb, innerLayer.a);
        result.a = max(result.a, innerLayer.a);
    }

    // Text layer (on top of everything)
    if (textOpacity > 0.0) {
        float finalTextAlpha = textOpacity * pulseMultiplier;
        vec4 textLayer = vec4(textColor, finalTextAlpha);
        // Alpha blend text on top
        result.rgb = mix(result.rgb, textLayer.rgb, textLayer.a);
        result.a = max(result.a, textLayer.a);
    }

    gl_FragColor = vec4(result.rgb, result.a * v_color0.a);
}
