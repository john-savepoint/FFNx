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

// Character Portrait Vertex Shader
// Handles portrait + dialogue box composite rendering with gradient fade

$input a_position, a_color0, a_texcoord0
$output v_color0, v_texcoord0, v_position

#include <bgfx/bgfx_shader.sh>

void main()
{
    // Transform vertex position
    gl_Position = mul(u_modelViewProj, vec4(a_position.xyz, 1.0));

    // Pass through color and texture coordinates
    v_color0 = a_color0;
    v_texcoord0 = a_texcoord0;

    // Pass through position for spatial effects in fragment shader
    v_position = a_position.xy;
}
