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
//    GNU General Public License for more details.                          //
/****************************************************************************/

// SDF (Signed Distance Field) Font Fragment Shader
// Provides resolution-independent, sharp text rendering

$input v_color0, v_texcoord0

#include <bgfx/bgfx_shader.sh>

SAMPLER2D(tex_0, 0);  // SDF texture (RGB channels contain distance field)

uniform vec4 SDFParams;
#define pxRange SDFParams.x         // Distance field spread in pixels (default: 4.0)
#define thickness SDFParams.y       // Glyph thickness adjustment (default: 0.5)
#define shadowOffset SDFParams.z    // Shadow offset in pixels (default: 1.0)
#define shadowOpacity SDFParams.w   // Shadow transparency (default: 0.5)

// Compute median of RGB channels
// This preserves sharp corners better than single-channel SDF
float median(float r, float g, float b) {
    return max(min(r, g), min(max(r, g), b));
}

void main() {
    // Sample the SDF texture
    vec3 msd = texture2D(tex_0, v_texcoord0).rgb;

    // Compute signed distance
    // msd contains distance values in [0, 1] range
    // 0.5 = exactly on edge, >0.5 = inside glyph, <0.5 = outside
    float sd = median(msd.r, msd.g, msd.b);

    // Convert distance to screen-space pixels
    // pxRange defines how many pixels the distance field covers
    float screenPxDistance = pxRange * (sd - 0.5);

    // Generate smooth anti-aliased alpha with thickness adjustment
    // thickness controls how bold the text appears (0.5 = normal, higher = bolder)
    float opacity = clamp(screenPxDistance + thickness, 0.0, 1.0);

    // Sample SDF offset for drop shadow (configurable offset)
    vec2 shadowOffsetVec = vec2(shadowOffset, shadowOffset) / vec2(1024.0, 1024.0);
    vec3 shadowMsd = texture2D(tex_0, v_texcoord0 + shadowOffsetVec).rgb;
    float shadowSd = median(shadowMsd.r, shadowMsd.g, shadowMsd.b);
    float shadowDistance = pxRange * (shadowSd - 0.5);
    float shadowOpacity = clamp(shadowDistance + 0.5, 0.0, 1.0);

    // Discard if neither text nor shadow is visible
    if (opacity < 0.01 && shadowOpacity < 0.01) {
        discard;
    }

    // Composite: shadow (dark) behind text (colored)
    vec3 shadowColor = vec3(0.0, 0.0, 0.0);  // Black shadow
    vec3 finalColor = mix(shadowColor, v_color0.rgb, opacity);
    float finalAlpha = max(opacity, shadowOpacity * shadowOpacity);  // Use config shadow opacity

    gl_FragColor = vec4(finalColor, v_color0.a * finalAlpha);
}
