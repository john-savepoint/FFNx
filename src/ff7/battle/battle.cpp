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

#include "../../globals.h"
#include "../../log.h"
#include "../../achievement.h"

#include "defs.h"

namespace ff7::battle
{
	void magic_thread_start(void (*func)())
	{
		ff7_externals.destroy_magic_effects();

		/*
		* Original function creates a separate thread but the code is not thread
		* safe in any way! Luckily modern PCs are fast enough to load magic
		* effects synchronously.
		*/
		func();
	}

	void load_battle_stage(int param_1, int battle_location_id, int **param_3){
		((void(*)(int, int, int **)) ff7_externals.load_battle_stage)(param_1, battle_location_id, param_3);

		g_FF7SteamAchievements->initCharStatsBeforeBattle(ff7_externals.savemap->chars);
		g_FF7SteamAchievements->unlockBattleSquareAchievement(battle_location_id);
	}

	void battle_sub_5C7F94(int param_1, int param_2){
		((void(*)(int, int)) ff7_externals.battle_sub_5C7F94)(param_1, param_2);

		if (trace_all || trace_achievement)
			ffnx_trace("%s - trying to unlock achievement for gil\n", __func__);
		g_FF7SteamAchievements->unlockGilAchievement(ff7_externals.savemap->gil);
	}

	void display_battle_action_text_sub_6D71FA(short command_id, short action_id){
		ff7_externals.battle_actor_data->formation_entry = 1;
		ff7_externals.battle_actor_data->command_index = command_id;
		ff7_externals.battle_actor_data->action_index = action_id;

		g_FF7SteamAchievements->unlockFirstLimitBreakAchievement(command_id, action_id);
	}

	int load_scene_bin_chunk(char *filename, int offset, int size, char **out_buffer, void (*callback)(void))
	{
		char lang_filename[1024]{0};
		char chunk_file[1024]{0};
		uint32_t chunk_size = 0;
		FILE* fd = NULL;
		int ret;

		// Language-aware scene.bin loading
		// CRITICAL: Only Japanese scene.bin is structurally compatible with the US executable.
		// German, French, and Spanish scene.bin have different block structures due to
		// longer text causing different GZIP compression ratios, resulting in different
		// scenes-per-block distribution. Using them causes wrong battle encounters.
		//
		// Block structure (scenes per block):
		//   EN/JA: [12, 6, 7, 8, 6, 6, 8, 8, 12, 8] - Compatible
		//   DE/FR/ES: [11, 7, 7, 8, 6, 6, 7, 7, 13, 8] - INCOMPATIBLE
		//
		// Solution: Always use English scene.bin structure for DE/FR/ES.
		// Enemy names will be injected via memory patching in a future update.

		// Determine which scene.bin to use based on structural compatibility
		const char* scene_lang = "en";  // Default to English (safe)
		bool use_lang_scene = false;

		if (ff7_japanese_edition || ff7_language == "ja")
		{
			// Japanese scene.bin has same block structure as English - safe to use
			scene_lang = "ja";
			use_lang_scene = true;
		}
		else if (ff7_language == "en" || ff7_language.empty())
		{
			// English or no language set - use default path
			use_lang_scene = false;
		}
		else
		{
			// DE/FR/ES - these have incompatible block structures!
			// Use English scene.bin to ensure correct battle encounters.
			// TODO: Implement enemy name injection from external text files
			if (trace_all || trace_files)
				ffnx_trace("load_scene_bin_chunk: Language '%s' has incompatible scene.bin structure, using English\n", ff7_language.c_str());
			use_lang_scene = false;
		}

		if (use_lang_scene)
		{
			// Try language-specific scene.bin (only for Japanese)
			_snprintf(lang_filename, sizeof(lang_filename), "%s/data/lang-%s/battle/scene.bin", basedir, scene_lang);

			if ((fd = fopen(lang_filename, "rb")) != NULL)
			{
				fclose(fd);
				if (trace_all || trace_files)
					ffnx_trace("load_scene_bin_chunk: Using %s scene.bin: %s\n", scene_lang, lang_filename);
				ret = ff7_externals.engine_load_bin_file_sub_419210(lang_filename, offset, size, out_buffer, callback);
			}
			else
			{
				if (trace_all || trace_files)
					ffnx_trace("load_scene_bin_chunk: %s scene.bin not found at %s, using default\n", scene_lang, lang_filename);
				ret = ff7_externals.engine_load_bin_file_sub_419210(filename, offset, size, out_buffer, callback);
			}
		}
		else
		{
			// Use default English scene.bin
			ret = ff7_externals.engine_load_bin_file_sub_419210(filename, offset, size, out_buffer, callback);
		}

		// Check for language-specific chunk overrides
		// Note: For DE/FR/ES, we still allow chunk overrides from their lang directories
		// in case modders provide properly structured chunks
		if (!ff7_language.empty())
		{
			const char* chunk_lang = ff7_japanese_edition ? "ja" : ff7_language.c_str();
			_snprintf(chunk_file, sizeof(chunk_file), "%s/data/lang-%s/battle/scene.bin.chunk.%i", basedir, chunk_lang, (offset >> 13) + 1);
			fd = fopen(chunk_file, "rb");
			if (fd != NULL && (trace_all || trace_files))
				ffnx_trace("load_scene_bin_chunk: Found %s chunk %i\n", chunk_lang, (offset >> 13) + 1);
		}

		// Fall back to direct mode chunk overrides
		if (fd == NULL)
		{
			_snprintf(chunk_file, sizeof(chunk_file), "%s/%s/battle/scene.bin.chunk.%i", basedir, direct_mode_path.c_str(), (offset >> 13) + 1);
			fd = fopen(chunk_file, "rb");
		}

		if (fd != NULL)
		{
			fseek(fd, 0L, SEEK_END);
			chunk_size = ftell(fd);
			fseek(fd, 0L, SEEK_SET);
			fread(*out_buffer, sizeof(byte), chunk_size, fd);

			ffnx_trace("scene section %i overridden with %s\n", (offset >> 13) + 1, chunk_file);
			fclose(fd);
		}

		return ret;
	}
}
