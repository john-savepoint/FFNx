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
#define pxRange SDFParams.x  // Distance field spread in pixels (default: 4.0)

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

    // Generate smooth anti-aliased alpha
    // Transition happens over ~1 pixel width
    float opacity = clamp(screenPxDistance + 0.5, 0.0, 1.0);

    // DEBUG: Render SDF text in bright red to verify shader is active
    gl_FragColor = vec4(1.0, 0.0, 0.0, opacity);

    // PRODUCTION: Use this instead when testing complete
    // gl_FragColor = vec4(v_color0.rgb, v_color0.a * opacity);
}
