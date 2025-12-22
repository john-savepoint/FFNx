/****************************************************************************/
//    Copyright (C) 2009 Aali132                                            //
//    Copyright (C) 2018 quantumpencil                                      //
//    Copyright (C) 2018 Maxime Bacoux                                      //
//    Copyright (C) 2020 myst6re                                            //
//    Copyright (C) 2020 Chris Rizzitello                                   //
//    Copyright (C) 2020 John Pritchard                                     //
//    Copyright (C) 2024 Julian Xhokaxhiu                                   //
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

#include <string.h>
#include <sys/stat.h>
#include <io.h>

#include "../ff7.h"
#include "../log.h"
#include "../redirect.h"
#include "../globals.h"

// Helper function to replace a substring in a path
// Returns true if replacement was made
static bool replace_lgp_name(char* path, size_t path_size, const char* search, const char* replace)
{
	char* pos = strstr(path, search);
	if(pos == NULL) return false;

	size_t search_len = strlen(search);
	size_t replace_len = strlen(replace);
	size_t suffix_len = strlen(pos + search_len);

	// Check if we have enough space
	if((pos - path) + replace_len + suffix_len >= path_size) return false;

	// Move the suffix to make room for the replacement
	memmove(pos + replace_len, pos + search_len, suffix_len + 1);
	// Copy the replacement
	memcpy(pos, replace, replace_len);

	return true;
}

// Language-based LGP file routing
// Routes game requests to language-specific LGP files based on ff7_language setting
// Supports: en (English), ja (Japanese), de (German), fr (French), es (Spanish)
static void apply_language_routing(char* modified_filename, size_t size)
{
	const char* lang = ff7_language.c_str();
	bool is_ja = (ff7_language == "ja" || ff7_japanese_edition);
	bool is_de = (ff7_language == "de");
	bool is_fr = (ff7_language == "fr");
	bool is_es = (ff7_language == "es");
	// en is default - no routing needed for most files

	// ============================================================
	// FIELD DIALOGUE (data/field/)
	// Pattern: flevel.lgp -> [prefix]flevel.lgp or flevel_en.lgp
	// ============================================================
	if(strstr(modified_filename, "flevel.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(ff7_language == "en") new_lgp = "flevel_en.lgp";
		else if(is_ja) new_lgp = "jfleve.lgp";
		else if(is_de) new_lgp = "gflevel.lgp";
		else if(is_fr) new_lgp = "fflevel.lgp";
		else if(is_es) new_lgp = "sflevel.lgp";

		if(new_lgp && replace_lgp_name(modified_filename, size, "flevel.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [field]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// MENU SYSTEM (data/menu/)
	// Pattern: menu_us.lgp -> menu_[lang].lgp
	// Codes: us=EN, ja=JA, gm=DE, fr=FR, sp=ES
	// ============================================================
	else if(strstr(modified_filename, "menu_us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_ja) new_lgp = "menu_ja.lgp";
		else if(is_de) new_lgp = "menu_gm.lgp";
		else if(is_fr) new_lgp = "menu_fr.lgp";
		else if(is_es) new_lgp = "menu_sp.lgp";
		// en: keep menu_us.lgp

		if(new_lgp && replace_lgp_name(modified_filename, size, "menu_us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [menu]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// CD DATA (data/cd/)
	// Pattern: cr_us.lgp, disc_us.lgp -> [name]_[lang].lgp
	// Codes: us=EN, gm=DE, fr=FR, sp=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "cr_us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "cr_gm.lgp";
		else if(is_fr) new_lgp = "cr_fr.lgp";
		else if(is_es) new_lgp = "cr_sp.lgp";
		// ja/en: keep cr_us.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "cr_us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [cd/cr]: %s (lang=%s)\n", modified_filename, lang);
		}
	}
	else if(strstr(modified_filename, "disc_us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "disc_gm.lgp";
		else if(is_fr) new_lgp = "disc_fr.lgp";
		else if(is_es) new_lgp = "disc_sp.lgp";
		// ja/en: keep disc_us.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "disc_us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [cd/disc]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// WORLD MAP (data/wm/)
	// Pattern: world_us.lgp -> world_[lang].lgp
	// Codes: us=EN, gm=DE, fr=FR, sp=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "world_us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "world_gm.lgp";
		else if(is_fr) new_lgp = "world_fr.lgp";
		else if(is_es) new_lgp = "world_sp.lgp";
		// ja/en: keep world_us.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "world_us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [world]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// MINIGAMES - CHOCOBO (data/minigame/)
	// Pattern: chocobo.lgp -> [prefix]chocobo.lgp
	// Prefixes: (none)=EN, f=FR, g=DE, s=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "chocobo.lgp") != NULL && strstr(modified_filename, "fchocobo") == NULL
		&& strstr(modified_filename, "gchocobo") == NULL && strstr(modified_filename, "schocobo") == NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "gchocobo.lgp";
		else if(is_fr) new_lgp = "fchocobo.lgp";
		else if(is_es) new_lgp = "schocobo.lgp";
		// ja/en: keep chocobo.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "chocobo.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [chocobo]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// MINIGAMES - SUBMARINE (data/minigame/)
	// Pattern: sub.lgp -> [prefix]sub.lgp
	// Prefixes: (none)=EN, f=FR, g=DE, s=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "sub.lgp") != NULL && strstr(modified_filename, "fsub") == NULL
		&& strstr(modified_filename, "gsub") == NULL && strstr(modified_filename, "ssub") == NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "gsub.lgp";
		else if(is_fr) new_lgp = "fsub.lgp";
		else if(is_es) new_lgp = "ssub.lgp";
		// ja/en: keep sub.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "sub.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [sub]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// MINIGAMES - HIGHWIND (data/minigame/)
	// Pattern: high-us.lgp -> high-[lang].lgp
	// Codes: us=EN, ge=DE, fr=FR, sp=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "high-us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "high-ge.lgp";
		else if(is_fr) new_lgp = "high-fr.lgp";
		else if(is_es) new_lgp = "high-sp.lgp";
		// ja/en: keep high-us.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "high-us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [high]: %s (lang=%s)\n", modified_filename, lang);
		}
	}

	// ============================================================
	// MINIGAMES - SNOWBOARD (data/minigame/)
	// Pattern: snowboard-us.lgp -> snowboard-[lang].lgp
	// Codes: us=EN, ge=DE, fr=FR, sp=ES (NO Japanese variant)
	// ============================================================
	else if(strstr(modified_filename, "snowboard-us.lgp") != NULL)
	{
		const char* new_lgp = NULL;
		if(is_de) new_lgp = "snowboard-ge.lgp";
		else if(is_fr) new_lgp = "snowboard-fr.lgp";
		else if(is_es) new_lgp = "snowboard-sp.lgp";
		// ja/en: keep snowboard-us.lgp (no Japanese variant)

		if(new_lgp && replace_lgp_name(modified_filename, size, "snowboard-us.lgp", new_lgp))
		{
			if(trace_all || trace_files) ffnx_trace("Language routing [snowboard]: %s (lang=%s)\n", modified_filename, lang);
		}
	}
}

FILE *open_lgp_file(char *filename, uint32_t mode)
{
	char _filename[260]{ 0 };
	if(trace_all || trace_files) ffnx_trace("opening lgp file %s\n", filename);

	char modified_filename[260]{ 0 };
	strcpy(modified_filename, filename);

	// Apply language-based routing for all LGP files
	apply_language_routing(modified_filename, sizeof(modified_filename));

	int redirect_status = attempt_redirection(modified_filename, _filename, sizeof(_filename));

	if (redirect_status == -1)
	{
		strcpy(_filename, modified_filename);
	}

	return fopen(_filename, "rb");
}

void close_lgp_file(FILE *fd)
{
	if(!fd) return;

	if(trace_all || trace_files) ffnx_trace("closing lgp file\n");

	fclose(fd);
}

// LGP names used for modpath lookup
char lgp_names[18][256] = {
	"char",
	"flevel",
	"battle",
	"magic",
	"menu",
	"world",
	"condor",
	"chocobo",
	"high",
	"coaster",
	"snowboard",
	"midi",
	"",
	"",
	"moviecam",
	"cr",
	"disc",
	"sub",
};

struct lgp_file
{
	uint32_t is_lgp_offset;
	union
	{
		uint32_t offset;
		FILE *fd;
	};
	uint32_t resolved_conflict;
};

#define NUM_LGP_FILES 64

struct lgp_file *lgp_files[NUM_LGP_FILES];
uint32_t lgp_files_index = 0;

struct lgp_file *last;

char lgp_current_dir[256];

uint32_t use_files_array = true;

int lgp_lookup_value(unsigned char c)
{
	c = tolower(c);

	if(c == '.') return -1;

	if(c < 'a' && c >= '0' && c <= '9') c += 'a' - '0';

	if(c == '_') c = 'k';
	if(c == '-') c = 'l';

	return c - 'a';
}

uint32_t lgp_chdir(char *path)
{
	uint32_t len = strlen(path);

	while(path[0] == '/' || path[0] == '\\') path++;

	memcpy(lgp_current_dir, path, len + 1);

	while(lgp_current_dir[len - 1] == '/' || lgp_current_dir[len - 1] == '\\') len--;
	lgp_current_dir[len] = 0;

	return true;
}

// original LGP open file logic, unchanged except for the LGP Tools safety net
uint32_t original_lgp_open_file(char *filename, uint32_t lgp_num, struct lgp_file *ret)
{
	uint32_t lookup_value1 = lgp_lookup_value(filename[0]);
	uint32_t lookup_value2 = lgp_lookup_value(filename[1]) + 1;
	struct lookup_table_entry *lookup_table = ff7_externals.lgp_lookup_tables[lgp_num];
	uint32_t toc_offset = lookup_table[lookup_value1 * 30 + lookup_value2].toc_offset;
	uint32_t i;

	// did we find anything in the lookup table?
	if(toc_offset)
	{
		uint32_t num_files = lookup_table[lookup_value1 * 30 + lookup_value2].num_files;

		// look for our file
		for(i = 0; i < num_files; i++)
		{
			struct lgp_toc_entry *toc_entry = &ff7_externals.lgp_tocs[lgp_num * 2][toc_offset + i - 1];

			if(!_stricmp(toc_entry->name, filename))
			{
				if(!toc_entry->conflict)
				{
					// this is the only file with this name, we're done here
					ret->is_lgp_offset = true;
					ret->offset = toc_entry->offset;
					return true;
				}
				else
				{
					struct conflict_list *conflict = &ff7_externals.lgp_folders[lgp_num].conflicts[toc_entry->conflict - 1];
					struct conflict_entry *conflict_entries = conflict->conflict_entries;
					uint32_t num_conflicts = conflict->num_conflicts;

					// there are multiple files with this name, look for our
					// current directory in the conflict table
					for(i = 0; i < num_conflicts; i++)
					{
						if(!_stricmp(conflict_entries[i].name, lgp_current_dir))
						{
							struct lgp_toc_entry *toc_entry = &ff7_externals.lgp_tocs[lgp_num * 2][conflict_entries[i].toc_index];

							// file name and directory matches, this is our file
							ret->is_lgp_offset = true;
							ret->offset = toc_entry->offset;
							ret->resolved_conflict = true;
							return true;
						}
					}

					break;
				}
			}
		}
	}

	// one last chance, the lookup table might have been broken by LGP Tools,
	// search through the entire archive
	for(i = 0; i < ((uint32_t *)ff7_externals.lgp_tocs)[lgp_num * 2 + 1]; i++)
	{
		struct lgp_toc_entry *toc_entry = &ff7_externals.lgp_tocs[lgp_num * 2][i];

		if(!_stricmp(toc_entry->name, filename))
		{
			ffnx_glitch("broken LGP file (%s), don't use LGP Tools!\n", lgp_names[lgp_num]);

			if(!toc_entry->conflict)
			{
				ret->is_lgp_offset = true;
				ret->offset = toc_entry->offset;
				return true;
			}
		}
	}

	return false;
}

// new LGP open file logic with modpath and direct mode support
struct lgp_file *lgp_open_file(char *filename, uint32_t lgp_num)
{
	struct lgp_file *ret = (lgp_file*)external_calloc(sizeof(*ret), 1);
	char tmp[512 + sizeof(basedir)];
	char _fname[_MAX_FNAME];
	char *fname = _fname;
	char ext[_MAX_EXT];
	char name[_MAX_FNAME + _MAX_EXT];

	_splitpath(filename, 0, 0, fname, ext);

	if(!direct_mode_path.empty())
	{
		_snprintf(tmp, sizeof(tmp), "%s/%s/%s/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
		ret->fd = fopen(tmp, "rb");

		if(!ret->fd)
		{
			_snprintf(tmp, sizeof(tmp), "%s/%s/%s.lgp/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
			ret->fd = fopen(tmp, "rb");
		}

		// Try to load special language named lgp files
		if(!ret->fd)
		{
			switch (lgp_num) {
				case 4: // menu
					// For Japanese edition, try menu_ja.lgp first
					if(ff7_japanese_edition)
					{
						_snprintf(tmp, sizeof(tmp), "%s/%s/%s_ja.lgp/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
						ret->fd = fopen(tmp, "rb");
						if(ret->fd && (trace_all || trace_direct)) ffnx_trace("lgp_open_file: using Japanese menu LGP: %s\n", tmp);
					}
					if(!ret->fd)
					{
						_snprintf(tmp, sizeof(tmp), "%s/%s/%s_us.lgp/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
					}
					break;
				case 5: // world
				case 15: // cr
				case 16: // disc
					_snprintf(tmp, sizeof(tmp), "%s/%s/%s_us.lgp/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
					break;
				case 8: // high
				case 10: // snowboard
					_snprintf(tmp, sizeof(tmp), "%s/%s/%s-us.lgp/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], fname, ext);
					break;
			}
			if(!ret->fd) ret->fd = fopen(tmp, "rb");
		}

		if(!ret->fd)
		{
			_snprintf(tmp, sizeof(tmp), "%s/%s/%s/%s/%s%s", basedir, direct_mode_path.c_str(), lgp_names[lgp_num], lgp_current_dir, fname, ext);
			ret->fd = fopen(tmp, "rb");
			if(ret->fd) ret->resolved_conflict = true;
		}

		if(ret->fd && (trace_all || trace_direct)) ffnx_trace("lgp_open_file: %i, %s (%s) [%s] = 0x%x\n", lgp_num, filename, lgp_current_dir, tmp, ret);
	}

	if(!ret->fd)
	{
		sprintf(name, "%s%s", fname, ext);

		if(!original_lgp_open_file(name, lgp_num, ret))
		{
			if(!direct_mode_path.empty()) ffnx_error("failed to find file %s; tried %s/%s/%s, %s/%s/%s/%s, %s/%s (LGP) (path: %s)\n", filename, direct_mode_path.c_str(), lgp_names[lgp_num], name, direct_mode_path.c_str(), lgp_names[lgp_num], lgp_current_dir, name, lgp_names[lgp_num], name, lgp_current_dir);
			else ffnx_error("failed to find file %s/%s (LGP) (path: %s)\n", lgp_names[lgp_num], name, lgp_current_dir);
			external_free(ret);
			return 0;
		}

		if(trace_all || trace_direct) ffnx_trace("lgp_open_file: %i, %s (%s) [ORIGINAL] = 0x%x\n", lgp_num, filename, lgp_current_dir, ret);
	}

	last = ret;

	if(use_files_array && !ret->is_lgp_offset)
	{
		if(lgp_files[lgp_files_index])
		{
			fclose(lgp_files[lgp_files_index]->fd);
			external_free(lgp_files[lgp_files_index]);
		}

		lgp_files[lgp_files_index] = ret;
		lgp_files_index = (lgp_files_index + 1) % NUM_LGP_FILES;
	}

	return ret;
}

/*
 * Direct LGP file access routines are used all over the place despite the nice
 * generic file interface found below in this file. Therefore we must implement
 * these in a way that works with the original code.
 */

// seek to given offset in LGP file
uint32_t lgp_seek_file(uint32_t offset, uint32_t lgp_num)
{
	if(!ff7_externals.lgp_fds[lgp_num]) return false;

	fseek(ff7_externals.lgp_fds[lgp_num], offset, SEEK_SET);

	return true;
}

// read straight from LGP file
uint32_t lgp_read(uint32_t lgp_num, char *dest, uint32_t size)
{
	if(!ff7_externals.lgp_fds[lgp_num]) return 0;

	if(last->is_lgp_offset) return fread(dest, 1, size, ff7_externals.lgp_fds[lgp_num]);

	return fread(dest, 1, size, last->fd);
}

// read from LGP file by LGP file descriptor
uint32_t lgp_read_file(struct lgp_file *file, uint32_t lgp_num, char *dest, uint32_t size)
{
	if(!ff7_externals.lgp_fds[lgp_num]) return 0;

	if(file->is_lgp_offset)
	{
		lgp_seek_file(file->offset + 24, lgp_num);
		return fread(dest, 1, size, ff7_externals.lgp_fds[lgp_num]);
	}

	return fread(dest, 1, size, file->fd);
}

// retrieve the size of a file within the LGP archive
uint32_t lgp_get_filesize(struct lgp_file *file, uint32_t lgp_num)
{
	if(file->is_lgp_offset)
	{
		uint32_t size;

		lgp_seek_file(file->offset + 20, lgp_num);
		fread(&size, 4, 1, ff7_externals.lgp_fds[lgp_num]);
		return size;
	}
	else
	{
		struct stat s;

		fstat(_fileno(file->fd), &s);

		return s.st_size;
	}
}

// close a file handle
void close_file(struct ff7_file *file)
{
	if(!file) return;

	if(file->fd)
	{
		if(!file->fd->is_lgp_offset && file->fd->fd) fclose(file->fd->fd);
		external_free(file->fd);
	}

	external_free(file->name);
	external_free(file);
}

// open file handle, target could be a file within an LGP archive or a regular
// file on disk
struct ff7_file *open_file(struct file_context *file_context, char *filename)
{
	char mangled_name[200];
	struct ff7_file *ret = (ff7_file*)external_calloc(sizeof(*ret), 1);
	char _filename[260]{ 0 };
	int redirect_status = 0;

	if (!ret) return 0;

	if(trace_all || trace_files)
	{
		if(file_context->use_lgp) ffnx_trace("open %s (LGP:%s)\n", filename, lgp_names[file_context->lgp_num]);
		else ffnx_trace("open %s (mode %i)\n", filename, file_context->mode);
	}

	if (!file_context->use_lgp)
	{
		// File was not found, but was required
		if (redirect_path_with_override(filename, _filename, sizeof(_filename)) == 1)
		{
			strcpy(_filename, filename);

			goto error;
		}
	}
	else
		// LGP files can be loaded safely from data, as Steam/eStore does not override them
		strcpy(_filename, filename);

	ret->name = (char*)external_malloc(strlen(_filename) + 1);
	strcpy(ret->name, _filename);
	memcpy(&ret->context, file_context, sizeof(*file_context));

	// file name mangler used mainly by battle module to convert PSX file names
	// to LGP-friendly PC names
	if(file_context->name_mangler)
	{
		file_context->name_mangler(_filename, mangled_name);
		strcpy(_filename, mangled_name);

		if(trace_all || trace_files) ffnx_trace("mangled name: %s\n", mangled_name);
	}

	if(file_context->use_lgp)
	{
		use_files_array = false;
		ret->fd = lgp_open_file(_filename, ret->context.lgp_num);
		use_files_array = true;
		if(!ret->fd)
		{
			if(file_context->name_mangler) ffnx_error("offset error: %s %s\n", _filename, mangled_name);
			else ffnx_error("offset error: %s\n", _filename);
			goto error;
		}

		if(!lgp_seek_file(ret->fd->offset + 24, ret->context.lgp_num))
		{
			ffnx_error("seek error: %s\n", _filename);
			goto error;
		}
	}
	else
	{
		ret->fd = (lgp_file*)external_calloc(sizeof(*ret->fd), 1);

		if(ret->context.mode == FF7_FMODE_READ) ret->fd->fd = fopen(_filename, "rb");
		else if(ret->context.mode == FF7_FMODE_READ_TEXT) ret->fd->fd = fopen(_filename, "r");
		else if(ret->context.mode == FF7_FMODE_WRITE) ret->fd->fd = fopen(_filename, "wb");
		else if(ret->context.mode == FF7_FMODE_CREATE) ret->fd->fd = fopen(_filename, "w+b");
		else ret->fd->fd = fopen(_filename, "r+b");

		if(!ret->fd->fd) goto error;
	}

	return ret;

error:
	// it's normal for save files to be missing, anything else is probably
	// going to cause trouble
	if(file_context->use_lgp || _stricmp(&_filename[strlen(_filename) - 4], ".ff7")) ffnx_error("could not open file %s\n", _filename);
	close_file(ret);
	return 0;
}

// read from file handle, returns how many bytes were actually read
uint32_t __read_file(uint32_t count, void *buffer, struct ff7_file *file)
{
	uint32_t ret = 0;

	if(!file || !count) return false;

	if(trace_all || trace_files) ffnx_trace("reading %i bytes from %s (ALT)\n", count, file->name);

	if(file->context.use_lgp) return lgp_read(file->context.lgp_num, (char*)buffer, count);

	ret = fread(buffer, 1, count, file->fd->fd);

	if(ferror(file->fd->fd))
	{
		ffnx_error("could not read from file %s (%i)\n", file->name, ret);
		return -1;
	}

	return ret;
}

// read from file handle, returns true if the read succeeds
uint32_t read_file(uint32_t count, void *buffer, struct ff7_file *file)
{
	uint32_t ret = 0;

	if(!file || !count) return false;

	if(trace_all || trace_files) ffnx_trace("reading %i bytes from %s\n", count, file->name);

	if(file->context.use_lgp) return lgp_read(file->context.lgp_num, (char*)buffer, count);

	ret = fread(buffer, 1, count, file->fd->fd);

	if(ret != count)
	{
		ffnx_error("could not read from file %s (%i)\n", file->name, ret);
		return false;
	}

	return true;
}

// read directly from a file descriptor returned by the open_file function
uint32_t __read(FILE *file, char *buffer, uint32_t count)
{
	return fread(buffer, 1, count, file);
}

// write to file handle, returns true if the write succeeds
uint32_t write_file(uint32_t count, void *buffer, struct ff7_file *file)
{
	uint32_t ret = 0;
	void *tmp = 0;

	if(!file || !count) return false;

	if(file->context.use_lgp) return false;

	if(trace_all || trace_files) ffnx_trace("writing %i bytes to %s\n", count, file->name);

	// hack to emulate win95 style writes, a NULL buffer means we should write
	// all zeroes
	if(!buffer)
	{
		tmp = driver_calloc(count, 1);
		buffer = tmp;
	}

	ret = fwrite(buffer, 1, count, file->fd->fd);

	if(tmp) driver_free(tmp);

	if(ret != count)
	{
		ffnx_error("could not write to file %s\n", file->name);
		return false;
	}

	return true;
}

// retrieve the size of a file from file handle
uint32_t get_filesize(struct ff7_file *file)
{
	if(!file) return 0;

	if(trace_all || trace_files) ffnx_trace("get_filesize %s\n", file->name);

	if(file->context.use_lgp) return lgp_get_filesize(file->fd, file->context.lgp_num);
	else
	{
		struct stat s;
		fstat(_fileno(file->fd->fd), &s);

		return s.st_size;
	}
}

// retrieve the current seek position from file handle
uint32_t tell_file(struct ff7_file *file)
{
	if(!file) return 0;

	if(trace_all || trace_files) ffnx_trace("tell %s\n", file->name);

	if(file->context.use_lgp) return 0;

	return ftell(file->fd->fd);
}

// seek to position in file
void seek_file(struct ff7_file *file, uint32_t offset)
{
	if(!file) return;

	if(trace_all || trace_files) ffnx_trace("seek %s to %i\n", file->name, offset);

	// it's not possible to seek within LGP archives
	if(file->context.use_lgp) return;

	if(fseek(file->fd->fd, offset, SEEK_SET)) ffnx_error("could not seek file %s\n", file->name);
}

// construct modpath name from file context, file handle and filename
char *make_pc_name(struct file_context *file_context, struct ff7_file *file, char *filename)
{
	uint32_t i, len;
	char *backslash;
	char* ret = (char*)external_malloc(1024);

	if(file_context->use_lgp)
	{
		if(file->fd->resolved_conflict) len = _snprintf(ret, 1024, "%s/%s/%s", lgp_names[file_context->lgp_num], lgp_current_dir, filename);
		else len = _snprintf(ret, 1024, "%s/%s", lgp_names[file_context->lgp_num], filename);
	}
	else len = _snprintf(ret, 1024, "%s", filename);

	for(i = 0; i < len; i++)
	{
		if(ret[i] == '.')
		{
			if(!_stricmp(&ret[i], ".tex")) ret[i] = 0;
			else if(!_stricmp(&ret[i], ".p")) ret[i] = 0;
			else ret[i] = '_';
		}
	}

	while(backslash = strchr(ret, '\\')) *backslash = '/';

	return ret;
}

/*###########################################################
	FF7 CHUNKED FIELD FILES
###########################################################*/

#define FF7_FIELD_NUM_SECTIONS 9
#define FF7_FIELD_OFFSET 0x2A

struct {
	uint32_t size = 0;
	byte* data;
} ff7_field_file_chunked[FF7_FIELD_NUM_SECTIONS];

int ff7_read_field_file(char* path)
{
	char filepath[256];

	if ( *ff7_externals.field_CFF268 ) return 1;

  _splitpath(path, NULL, NULL, filepath, NULL);

  lgp_file* lgp_file = lgp_open_file(filepath, 1);
  if ( !lgp_file ) return 0;

  uint32_t size = lgp_get_filesize(lgp_file, 1);
  char* dest = (char*)driver_malloc(size);
  char* original_field_data = (char*)driver_malloc(*ff7_externals.known_field_buffer_size);
	if ( !ff7_externals.field_file_buffer ) return 0;

  lgp_read_file(lgp_file, 1, dest, size);
  ff7_externals.lzss_decode(dest, original_field_data);
	if ( dest )
  {
    driver_free(dest);
    dest = 0;
  }

	// Attempt to override part of the current field file with chunk files
	char chunk_file[1024]{0};
	uint32_t data_ptr = 0, data_len = 0, next_data_ptr = 0;
	FILE* fd;

	for (int n = 0; n < FF7_FIELD_NUM_SECTIONS; n++)
	{
		_snprintf(chunk_file, sizeof(chunk_file), "%s/%s/%s.lgp/%s.chunk.%i", basedir, direct_mode_path.c_str(), lgp_names[1], filepath, n+1);

		if ((fd = fopen(chunk_file, "rb")) != NULL)
		{
			fseek(fd, 0L, SEEK_END);
			ff7_field_file_chunked[n].size = ftell(fd);
			ff7_field_file_chunked[n].data = new byte[ff7_field_file_chunked[n].size];

			fseek(fd, 0L, SEEK_SET);
			fread(ff7_field_file_chunked[n].data, sizeof(byte), ff7_field_file_chunked[n].size, fd);

			fclose(fd);
		}
		else
		{
			data_ptr = *(uint32_t*)(original_field_data + 0x6 + 0x4 * n);

			// if this isn't the last section
			if (n < (FF7_FIELD_NUM_SECTIONS-1))
			{
				next_data_ptr = *(uint32_t*)(original_field_data + 0x6 + 0x4 * (n + 1));

				// the lgp might be lying about the length of the section! recalculate it.
				data_len = next_data_ptr - data_ptr - 0x4;
			}
			else
			{
				//there is no section after, so we use known_field_buffer_size.
				data_len = *ff7_externals.known_field_buffer_size - data_ptr - 0x4;
			}

			ff7_field_file_chunked[n].size = data_len;
			ff7_field_file_chunked[n].data = new byte[ff7_field_file_chunked[n].size];

			memcpy(ff7_field_file_chunked[n].data, original_field_data + data_ptr + 0x4, ff7_field_file_chunked[n].size);
		}
	}

	// Allocate the new field file
	driver_free(original_field_data);
	*ff7_externals.field_file_buffer = (char*)external_malloc(*ff7_externals.known_field_buffer_size);

	// Build the new field file
	*(short*)(*ff7_externals.field_file_buffer) = 0x0; // 0x0
	*(int*)(*ff7_externals.field_file_buffer + 0x2) = FF7_FIELD_NUM_SECTIONS; // 0x2
	uint32_t offset = FF7_FIELD_OFFSET;
	for (int n = 0; n < FF7_FIELD_NUM_SECTIONS; n++)
	{
		// Pointer to data section
		ff7_externals.field_file_section_ptrs[n] = offset;
		*(int*)(*ff7_externals.field_file_buffer + 0x6 + (0x4 * n)) = ff7_externals.field_file_section_ptrs[n];

		// Length of data section
		*(int*)(*ff7_externals.field_file_buffer + offset) = ff7_field_file_chunked[n].size;

		// The data
		offset += 0x4;
		memcpy(*ff7_externals.field_file_buffer + offset, ff7_field_file_chunked[n].data, ff7_field_file_chunked[n].size);
		offset += ff7_field_file_chunked[n].size;

		// Cleanup
		delete ff7_field_file_chunked[n].data;
	}

  return 1;
}
