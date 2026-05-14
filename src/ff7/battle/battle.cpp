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
#include "../../patch.h"

#include "defs.h"
#include "scene_text.h"

namespace ff7::battle
{
	// Store original function pointer before replacement (set in ff7_opengl.cpp)
	uint32_t g_original_display_battle_action_text = 0;

	// ============================================================================
	// Scene.bin block divisor patch for multi-language support
	// ============================================================================
	//
	// PROBLEM:
	// German/French/Spanish scene.bin files have 11 scenes per block (block 0)
	// English/Japanese scene.bin files have 12 scenes per block
	// The FF7 executable hardcodes division by 12 using magic number optimization
	//
	// SOLUTION:
	// Patch BOTH the division AND the modulo calculations:
	// 1. The magic number 0x2AAAAAAB at 0x7B29BB handles scene_id / 12 (block number)
	// 2. The literal 0x0C at 0x7B29D0 handles scene_id % 12 (scene within block)
	// 3. The CMP ESI, 0x0B at 0x7B29B6 is a check for small scene IDs
	//
	// ADDRESSES (based on disassembly analysis):
	// 0x7B2990: Function start (PUSH EBX; PUSH ESI; PUSH EDI)
	// 0x7B29AF: MOV ESI, [EDI+0x10]  ; Load scene_id
	// 0x7B29B6: CMP ESI, 0x0B        ; Compare with 11
	// 0x7B29B9: JLE +0x3E            ; Skip division if scene_id <= 11
	// 0x7B29BB: MOV EAX, 0x2AAAAAAB  ; Magic number for / 12
	// 0x7B29C0: IMUL ESI             ; Multiply
	// 0x7B29C2: SAR EDX, 1           ; Arithmetic shift right 1
	// 0x7B29D0: MOV ESI, 0x0C        ; Literal 12 for modulo
	// 0x7B29D5: IDIV ESI             ; Divide for modulo
	//
	// For DE/FR/ES, we need to change:
	// - The magic number and shift for /11 instead of /12
	// - The literal from 0x0C to 0x0B for %11
	// - Possibly the CMP at 0x7B29B6
	// ============================================================================

	// CORRECTED ADDRESSES (file offset to runtime: +0xC00 due to PE section alignment)
	// File offset 0x3B29BC -> Runtime 0x7B35BC
	constexpr uint32_t SCENE_BLOCK_DIVISOR_ADDR = 0x7B35D0;  // The literal 12 for MOD (BE 0C at file 0x3B29CF+1)
	constexpr uint32_t SCENE_BLOCK_CMP_ADDR = 0x7B35B8;      // The 0x0B in CMP ESI, 0x0B (83 FE 0B at file 0x3B29B6+2)
	constexpr uint32_t SCENE_MAGIC_NUMBER_ADDR = 0x7B35BC;   // Start of magic number (0x2AAAAAAB at file 0x3B29BC)
	constexpr uint32_t SCENE_SAR_SHIFT_ADDR = 0x7B35C3;      // SAR EDX, 1 instruction (not used currently)

	constexpr uint8_t BLOCK_DIVISOR_EN = 12;  // English/Japanese
	constexpr uint8_t BLOCK_DIVISOR_DE = 11;  // German/French/Spanish

	// Magic number for division by 11 is 0x2E8BA2E9
	// However, division by 11 also requires SAR EDX, 1 (same as /12)
	// So we can just replace the magic number

	void patch_scene_block_divisor()
	{
		// NOTE: With the flevel.lgp fix (all languages use English flevel),
		// we no longer need to patch the divisor for DE/FR/ES.
		// All languages now use English scene.bin structure (12 scenes per block).
		// Keeping this function for future use if native scene.bin support is needed.
		bool use_de_divisor = false;  // Disabled: English flevel + English scene structure
		uint8_t divisor = use_de_divisor ? BLOCK_DIVISOR_DE : BLOCK_DIVISOR_EN;

		// ========================================
		// PATCH 1: The literal for MOD operation
		// ========================================
		// At 0x7B29D0: BE 0C 00 00 00 (MOV ESI, 0x0C)
		// Change to:   BE 0B 00 00 00 (MOV ESI, 0x0B) for DE/FR/ES
		uint8_t original_mod = *(uint8_t*)SCENE_BLOCK_DIVISOR_ADDR;
		patch_code_byte(SCENE_BLOCK_DIVISOR_ADDR, divisor);
		uint8_t patched_mod = *(uint8_t*)SCENE_BLOCK_DIVISOR_ADDR;

		ffnx_info("[MLANG-PATCH1] MOD divisor: addr=0x%08X, original=%d, patched=%d\n",
			SCENE_BLOCK_DIVISOR_ADDR, original_mod, patched_mod);

		// ========================================
		// PATCH 2: The CMP threshold
		// ========================================
		// At 0x7B29B6: 83 FE 0B (CMP ESI, 0x0B)
		// This is the check "if scene_id <= 11, skip the complex division"
		// For DE/FR/ES, change to CMP ESI, 0x0A (if scene_id <= 10, skip)
		uint8_t cmp_value = use_de_divisor ? 0x0A : 0x0B;
		uint8_t original_cmp = *(uint8_t*)SCENE_BLOCK_CMP_ADDR;
		patch_code_byte(SCENE_BLOCK_CMP_ADDR, cmp_value);
		uint8_t patched_cmp = *(uint8_t*)SCENE_BLOCK_CMP_ADDR;

		ffnx_info("[MLANG-PATCH2] CMP threshold: addr=0x%08X, original=0x%02X, patched=0x%02X\n",
			SCENE_BLOCK_CMP_ADDR, original_cmp, patched_cmp);

		// ========================================
		// PATCH 3: The magic number for DIV
		// ========================================
		// At 0x7B29BC: AB AA AA 2A (0x2AAAAAAB in little-endian) for /12
		// For /11: E9 A2 8B 2E (0x2E8BA2E9 in little-endian)
		//
		// Division by 11: (n * 0x2E8BA2E9) >> 33 (same shift as /12)
		// Division by 12: (n * 0x2AAAAAAB) >> 33
		//
		// After IMUL, high 32 bits in EDX, then SAR EDX, 1 gives >> 33 total

		if (use_de_divisor)
		{
			// Patch magic number for division by 11
			// 0x2E8BA2E9 in little-endian: E9 A2 8B 2E
			uint8_t magic_11[] = {0xE9, 0xA2, 0x8B, 0x2E};

			uint32_t original_magic = *(uint32_t*)SCENE_MAGIC_NUMBER_ADDR;

			patch_code_byte(SCENE_MAGIC_NUMBER_ADDR + 0, magic_11[0]);
			patch_code_byte(SCENE_MAGIC_NUMBER_ADDR + 1, magic_11[1]);
			patch_code_byte(SCENE_MAGIC_NUMBER_ADDR + 2, magic_11[2]);
			patch_code_byte(SCENE_MAGIC_NUMBER_ADDR + 3, magic_11[3]);

			uint32_t patched_magic = *(uint32_t*)SCENE_MAGIC_NUMBER_ADDR;

			ffnx_info("[MLANG-PATCH3] DIV magic number: addr=0x%08X, original=0x%08X, patched=0x%08X\n",
				SCENE_MAGIC_NUMBER_ADDR, original_magic, patched_magic);
		}
		else
		{
			ffnx_info("[MLANG-PATCH3] DIV magic number: no change needed for EN/JA\n");
		}

		// ========================================
		// Summary log
		// ========================================
		ffnx_info("[MLANG-DIV] Scene block patches complete: lang=%s, using_divisor=%d\n",
			ff7_language.c_str(), divisor);
	}

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

		// Multi-language: Inject enemy names EARLY, before any rendering starts
		// This avoids race conditions with the text renderer
		check_and_inject_enemy_names();
	}

	void battle_sub_5C7F94(int param_1, int param_2){
		((void(*)(int, int)) ff7_externals.battle_sub_5C7F94)(param_1, param_2);

		if (trace_all || trace_achievement)
			ffnx_trace("%s - trying to unlock achievement for gil\n", __func__);
		g_FF7SteamAchievements->unlockGilAchievement(ff7_externals.savemap->gil);
	}

	void display_battle_action_text_sub_6D71FA(short command_id, short action_id){
		// Call the STORED original function (not ff7_externals which is now patched)
		if (g_original_display_battle_action_text) {
			((void(*)(short, short))g_original_display_battle_action_text)(command_id, action_id);
		}

		// Then do achievement tracking
		g_FF7SteamAchievements->unlockAchievementByBattleCommandAndAction(command_id, action_id);
	}

	int load_scene_bin_chunk(char *filename, int offset, int size, char **out_buffer, void (*callback)(void))
	{
		char lang_filename[1024]{0};
		char chunk_file[1024]{0};
		uint32_t chunk_size = 0;
		FILE* fd = NULL;
		int ret;

		// Calculate block and scene info for debugging
		// Block = offset / 0x2000 (8KB blocks)
		// Scene offset within block can help identify which scene
		int block_num = offset >> 13;  // offset / 8192

		// Unique searchable prefix: [MLANG-SCENE]
		ffnx_info("[MLANG-SCENE] load_scene_bin_chunk called: offset=0x%08X, block=%d, size=%d, lang=%s\n",
			offset, block_num, size, ff7_language.c_str());

		// Language-aware scene.bin loading
		//
		// STRATEGY: Use English scene.bin for DE/FR/ES since we're using English flevel.lgp
		// which has English-compatible encounter mappings (12 scenes per block).
		// Only Japanese uses its own scene.bin (jfleve.lgp has compatible mappings).
		//
		// Enemy names/attack names in German can be injected at display time.
		const char* scene_lang = NULL;
		bool use_lang_scene = false;

		if (ff7_japanese_edition || ff7_language == "ja")
		{
			// Japanese has its own compatible structure
			scene_lang = "ja";
			use_lang_scene = true;
		}
		else if (ff7_language == "en")
		{
			// English uses lang-en scene.bin
			scene_lang = "en";
			use_lang_scene = true;
		}
		// DE/FR/ES: use default English scene.bin (no lang-specific override)

		if (use_lang_scene && scene_lang)
		{
			// Try language-specific scene.bin
			_snprintf(lang_filename, sizeof(lang_filename), "%s/data/lang-%s/battle/scene.bin", basedir, scene_lang);

			if ((fd = fopen(lang_filename, "rb")) != NULL)
			{
				fclose(fd);
				// [MLANG-FILE] prefix for file routing decisions
				ffnx_info("[MLANG-FILE] Using lang scene.bin: lang=%s, path=%s\n", scene_lang, lang_filename);
				ret = ff7_externals.engine_load_bin_file_sub_419210(lang_filename, offset, size, out_buffer, callback);
			}
			else
			{
				ffnx_info("[MLANG-FILE] Lang scene.bin NOT FOUND: lang=%s, path=%s, falling back to default\n", scene_lang, lang_filename);
				ret = ff7_externals.engine_load_bin_file_sub_419210(filename, offset, size, out_buffer, callback);
			}
		}
		else
		{
			// DE/FR/ES: Use default English scene.bin for correct block structure
			ffnx_info("[MLANG-FILE] Using DEFAULT (English) scene.bin for %s: path=%s\n", ff7_language.c_str(), filename);
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

		// NOTE: Buffer injection doesn't work here because *out_buffer contains
		// COMPRESSED data. The decompression happens inside engine_load_bin_file_sub_419210.
		// We need to find a hook point AFTER decompression.

		return ret;
	}

	// ============================================================================
	// Enemy name injection for multi-language support (Western editions)
	// ============================================================================
	// Strategy: Hook the scene bin loading, then inject DIRECTLY to the RAM
	// addresses where enemy names end up. These addresses were verified via
	// Cheat Engine - manual edits at these addresses change displayed names.
	//
	// The game's copy chain is:
	// 1. Scene data loaded from file
	// 2. 0x005C8037 copies to 0x9A8E9C/9A8F54/9A900C (enemy record buffer)
	// 3. 0x00419A60 copies for display
	//
	// We inject AFTER step 2 by hooking a function that runs during battle.
	// ============================================================================

	// Direct RAM addresses for enemy names (verified via Cheat Engine)
	constexpr uint32_t ENEMY_RAM_ADDR_1 = 0x9A8E9C;
	constexpr uint32_t ENEMY_RAM_ADDR_2 = 0x9A8F54;
	constexpr uint32_t ENEMY_RAM_ADDR_3 = 0x9A900C;

	// Track if we've injected for current battle
	static uint16_t last_injected_formation = 0xFFFF;

	// Called when battle menu opens - inject enemy names once
	//
	// CRITICAL: The enemy record at 0x9A8E9C is 184 bytes:
	//   Offset 0x00-0x1F (0-31): Enemy Name (32 bytes, FF7 encoding, 0xFF terminated)
	//   Offset 0x20 (32): Level - DO NOT OVERWRITE!
	//   Offset 0x21+: Speed, Luck, Evade, Strength, Defense, Magic, etc.
	//
	// We must write AT MOST 31 bytes of name + 0xFF terminator at byte 31.
	// Writing to byte 32 corrupts Level and causes crash during damage calculation.
	void check_and_inject_enemy_names()
	{
		if (!needs_text_injection())
			return;

		uint16_t formation_id = ff7_externals.modules_global_object->battle_id;

		// Only inject once per battle
		if (formation_id == last_injected_formation)
			return;

		last_injected_formation = formation_id;
		uint16_t scene_id = formation_id / 4;

		ffnx_info("[MLANG-INJECT] Injecting: formation=%d, scene=%d\n", formation_id, scene_id);

		if (scene_id >= 256)
		{
			ffnx_warning("[MLANG-INJECT] Scene ID %d out of bounds\n", scene_id);
			return;
		}

		const uint32_t enemy_addrs[3] = { ENEMY_RAM_ADDR_1, ENEMY_RAM_ADDR_2, ENEMY_RAM_ADDR_3 };

		for (int i = 0; i < 3; i++)
		{
			char* dest = (char*)enemy_addrs[i];

			// Get the localized name for this enemy slot
			const char* localized_name = get_localized_enemy_name(scene_id, i);
			if (localized_name && localized_name[0] != '\0')
			{
				// Calculate safe length - max 31 chars, stop at 0x00 or 0xFF terminator
				size_t name_len = 0;
				while (name_len < 31 && localized_name[name_len] != '\0' && (unsigned char)localized_name[name_len] != 0xFF)
					name_len++;

				// Copy the name
				memcpy(dest, localized_name, name_len);

				// Pad remaining bytes with 0xFF (FF7 text terminator)
				for (size_t j = name_len; j < 32; j++)
					dest[j] = (char)0xFF;

				ffnx_info("[MLANG-INJECT] Enemy %d @ 0x%08X: wrote '%s' (%zu bytes)\n",
					i, enemy_addrs[i], localized_name, name_len);
			}
			else
			{
				ffnx_info("[MLANG-INJECT] Enemy %d @ 0x%08X: no localized name for scene %d slot %d\n",
					i, enemy_addrs[i], scene_id, i);
			}
		}

		ffnx_info("[MLANG-INJECT] Done\n");
	}

	// Reset injection tracking when leaving battle
	void reset_enemy_name_injection()
	{
		last_injected_formation = 0xFFFF;
	}

	// Install the hook (called from ff7_opengl.cpp)
	void install_enemy_name_hook()
	{
		if (!ff7_japanese_edition && needs_text_injection())
		{
			ffnx_info("[MLANG-HOOK] Enemy name injection enabled for %s (direct RAM method)\n", ff7_language.c_str());
		}
		else
		{
			ffnx_info("[MLANG-HOOK] Enemy name injection not needed for %s\n", ff7_language.c_str());
		}
	}

}
