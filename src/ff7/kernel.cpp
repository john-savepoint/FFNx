/****************************************************************************/
//    Copyright (C) 2009 Aali132                                            //
//    Copyright (C) 2018 quantumpencil                                      //
//    Copyright (C) 2018 Maxime Bacoux                                      //
//    Copyright (C) 2020 myst6re                                            //
//    Copyright (C) 2020 Chris Rizzitello                                   //
//    Copyright (C) 2020 John Pritchard                                     //
//    Copyright (C) 2024 Julian Xhokaxhiu                                   //
//    Copyright (C) 2023 Cosmos                                             //
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

#include "../ff7.h"
#include "../log.h"
#include "../globals.h"

#define FF7_KERNEL_NUM_SECTIONS 27

// KERNEL2
char *kernel2_sections[20];
uint32_t kernel2_section_counter;

void kernel2_reset_counters()
{
	uint32_t i;

	if(trace_all) ffnx_trace("kernel2 reset\n");

	for(i = 0; i < kernel2_section_counter; i++) external_free(kernel2_sections[i]);

	kernel2_section_counter = 0;
}

char *kernel2_add_section(uint32_t size)
{
	char *ret = (char*)external_malloc(size);

	if(trace_all) ffnx_trace("kernel2 add section %i (%i)\n", kernel2_section_counter, size);

	kernel2_sections[kernel2_section_counter++] = ret;

	return ret;
}

char *kernel2_get_text(uint32_t section_base, uint32_t string_id, uint32_t section_offset)
{
	char *section = kernel2_sections[section_base + section_offset];

	if(trace_all) ffnx_trace("kernel2 get text (%i+%i:%i)\n", section_base, section_offset, string_id);

	return &section[((WORD *)section)[string_id]];
}

// ENGINE

void ff7_load_kernel2_wrapper(char *filename)
{
  // DEBUG: Log kernel2 load
  ffnx_info("KERNEL2_LOAD: filename=%s, ff7_language=%s\n", filename, ff7_language.c_str());

  // Language-based kernel loading: try lang-XX path first
  // Supports: en, ja, de, fr, es
  if (ff7_language != "en" || ff7_japanese_edition)
  {
    char lang_filename[260];
    const char* lang_code = ff7_japanese_edition ? "ja" : ff7_language.c_str();

    // Try lang-XX path: data/lang-XX/kernel/kernel2.bin
    _snprintf(lang_filename, sizeof(lang_filename), "%s/data/lang-%s/kernel/kernel2.bin", basedir, lang_code);

    FILE* fd = fopen(lang_filename, "rb");
    if (fd != NULL)
    {
      fclose(fd);
      ffnx_info("KERNEL2_LOAD: Redirecting to %s kernel2: %s\n", lang_code, lang_filename);
      ff7_externals.kernel_load_kernel2(lang_filename);
      return;
    }
    else
    {
      ffnx_warning("KERNEL2_LOAD: %s kernel2 not found at %s, using default\n", lang_code, lang_filename);
    }
  }

  ff7_externals.kernel_load_kernel2(filename);

	char chunk_file[1024]{0};
	uint32_t chunk_size = 0;
	FILE* fd;

	for (int n = 0; n < FF7_KERNEL_NUM_SECTIONS; n++)
	{
		fd = NULL;

		// Language-based: try lang-XX path first
		if (ff7_language != "en" || ff7_japanese_edition)
		{
			const char* lang_code = ff7_japanese_edition ? "ja" : ff7_language.c_str();
			_snprintf(chunk_file, sizeof(chunk_file), "%s/data/lang-%s/kernel/kernel.bin.chunk.%i", basedir, lang_code, n+1);
			fd = fopen(chunk_file, "rb");
			if (fd != NULL)
			{
				ffnx_info("KERNEL_CHUNK: Found %s chunk %i at %s\n", lang_code, n+1, chunk_file);
			}
		}

		// Fallback to direct mode path
		if (fd == NULL)
		{
			_snprintf(chunk_file, sizeof(chunk_file), "%s/%s/kernel/kernel.bin.chunk.%i", basedir, direct_mode_path.c_str(), n+1);
			fd = fopen(chunk_file, "rb");
		}

		if (fd != NULL)
		{
			fseek(fd, 0L, SEEK_END);
			chunk_size = ftell(fd);
			fseek(fd, 0L, SEEK_SET);

			if (0 <= n && n <= 8)
				fread(ff7_externals.kernel_1to9_sections[n], sizeof(byte), chunk_size, fd);
			else
				fread(kernel2_sections[n-9], sizeof(byte), chunk_size, fd);

			ffnx_trace("kernel section %i overridden with %s\n", n+1, chunk_file);
			fclose(fd);
		}
	}
}
