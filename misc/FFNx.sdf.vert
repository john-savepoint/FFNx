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

// SDF (Signed Distance Field) Font Vertex Shader
// Provides standard vertex transformation for SDF text rendering

$input a_position, a_color0, a_texcoord0
$output v_color0, v_texcoord0

#include <bgfx/bgfx_shader.sh>

void main() {
    // Standard vertex transformation
    gl_Position = mul(u_modelViewProj, a_position);

    // Pass through color and texture coordinates
    v_color0 = a_color0;
    v_texcoord0 = a_texcoord0;
}
