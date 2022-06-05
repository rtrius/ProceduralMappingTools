#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_sounddb_idtech4_sndshd
#	script_section_name: 	pmt_sounddb_idtech4_sndshd.py
# Parses .sndshd files to extract .wav/.ogg sound paths.

import os
import sys
import string
	
#By default open() uses locale.getpreferredencoding();
#Houdini 18.5 on Windows 10 locale.getpreferredencoding() returns 'cp65001', but
#a standalone Python3 install returns 'cp1252'. Using cp65001 causes the decoding to
#fail, so explicitly set the codec here.
TEXT_CODEC = "cp1252" #windows-1252 'Western Europe'

IN_HOUDINI = 'hou' in sys.modules
def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
def find_all_files_in(search_path, extension):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			#filepath = dirpath + filename
			if filepath.endswith(extension):
				paths.append((filename, filepath))
				DPRINT("{0}: {1}".format(extension, filepath))
	return paths

###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules from a module inside pmt__global_config.
###Only modules starting with "pmt_common" should be accessed from inside pmt::pmt__global_config.
import sys
IN_HOUDINI = 'hou' in sys.modules
if IN_HOUDINI:
	import hou
	PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt_common = PMT__G_CFG.pmt_common
	pmt_common_texture = PMT__G_CFG.pmt_common_texture
###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__

class SoundShader:
	def __init__(self):
		self.name = None
		self.path = None 		#editor_displayfolder + name if editor_displayfolder exists in params
		self.tags = list()
		self.params = dict()
		self.sounds = list()	#list of paths to .wav/.ogg sounds
		
#Parses a single .sndshd file, which references multiple sounds
def parse_soundshader(sndshd_path):		
	def remove_comments_newlines_and_tabs(text):
		#remove text after // comments; note that single line comments precede multiline comments
		#keepends == True, so we keep the newline chars(/n, /r, ...)
		text_without_comments = ""
		
		for line in text.splitlines(keepends = True):
			if len(line) == 0: continue

			if "\"" not in line and "\'" not in line:
				left, sep, right = line.partition("//")
				comment_removed_line = left
			else: #ignore // if it is in a quote
				if "//" in line:
					#find the lowest // that is not in a quote and remove all text afterwards
					splitline = line.split("//", maxsplit = -1)
					if len(splitline) > 0:
						num_single_quote = splitline[0].count("\'")
						num_double_quote = splitline[0].count("\"")
						comment_removed_line = splitline[0]
						
						for i in range(1, len(splitline)):
							in_quote = num_single_quote % 2 != 0 or num_double_quote % 2 != 0
							if in_quote:
								comment_removed_line += "//" + splitline[i] 
								num_single_quote += splitline[i].count("\'")
								num_double_quote += splitline[i].count("\"")
							else:
								break #if we are not in a quote, all remaining text is removed
								
				else:
					comment_removed_line = line
				
			text_without_comments += comment_removed_line
			
		#remove text in between /* */ comments
		REMOVE_MULTILINE_COMMENTS = True
		if REMOVE_MULTILINE_COMMENTS:
			multiline_comment_start_index = text_without_comments.find("/*")
			while multiline_comment_start_index != -1:
				left1, sep1, right1 = text_without_comments.partition("/*")
				left2, sep2, right2 = right1.partition("*/")
				text_without_comments = left1 + right2
				multiline_comment_start_index = text_without_comments.find("/*")
		
		#replace tabs, newline, return, etc. with " "
		#important: this can only happen after parsing '//' type comments
		for char in string.whitespace:
			text_without_comments = text_without_comments.replace(char, " ")
			
		#	
		return text_without_comments
		
	#Extract text in between quotes "" or ''
	#Assume that the quotes must be matched; that is \" must end with \" and likewise with \'.
	#Under this assumption, literals such as "string' or 'string" are invalid.
	INQUOTE_TOKEN = "%%q_"
	def extract_string_literals(text, debug_path):
		assert text.find(INQUOTE_TOKEN) == -1, "error: .uc contains INQUOTE_TOKEN {}".format(INQUOTE_TOKEN)
		
		inquote_text_dict = dict()
		
		in_quote = False
		quote_char = None
		
		text_without_quotes = ""
		inquote_buffer = ""
		for char in text:
			if char == "\"" or char == "\'" and not in_quote:
				quote_char = char
				
			if char == quote_char:
				if not in_quote: #opening quote
					inquote_buffer = ""
				else: #closing quote
					dict_id_str = INQUOTE_TOKEN + str( len(inquote_text_dict) )
					inquote_text_dict[dict_id_str] = inquote_buffer
					text_without_quotes += " {} ".format(dict_id_str)
					#DPRINT("inquote: {}: {}".format(dict_id_str, inquote_buffer))
				in_quote = not in_quote
			else:
				if in_quote:
					inquote_buffer += char
				else:
					text_without_quotes += char
		assert not in_quote, "error: missing closing quote for quote_char({}) in {}: [{}]".format(quote_char, debug_path, text)
			
		return (text_without_quotes, inquote_text_dict)
		
	def pad_operators(text):
		#pad '{', '}', ... with spaces so that split() will not mix them with text
		PAD_CHARS = "{}"
		for char in PAD_CHARS:
			text = text.replace(char, " {} ".format(char))
		return text
	
	#replace sequences of spaces with a single space
	def compact_spaces(text):
		SPACES_4 = "    "
		SPACES_2 = "  "
		while text.find(SPACES_4) != -1:
			text = text.replace(SPACES_4, " ")
		while text.find(SPACES_2) != -1:
			text = text.replace(SPACES_2, " ")
		return text
		
	with open(sndshd_path, 'rt', encoding=TEXT_CODEC) as sndshd_file:
		text = ""
		for line in sndshd_file:
			text += line
		
		
	#list of tuple containing:
	#(soundshader_name, sounds, tags, params)
	#sounds is a line that ends with .wav or .ogg
	#tags is a single token statement
	#params is a double token statement
	TAG_NAMES = ["no_dups", "no_efx", "unclamped", "no_occlusion", "looping", "omnidirectional", "private", "global"]
	PARAM_NAMES = ["mindistance", "maxdistance", "volume", "editor_displayfolder", "description", "shakes", "leadin"]
	
	
	text = remove_comments_newlines_and_tabs(text)
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, sndshd_path)

	text_without_quotes = pad_operators(text_without_quotes)
	text_without_quotes = compact_spaces(text_without_quotes)	
	tokens_with_quotes = text_without_quotes.split(sep = " ", maxsplit = -1)
	
	tokens = list()
	for token in tokens_with_quotes:
		if token.startswith(INQUOTE_TOKEN):
			tokens.append(inquote_text_dict[token])
		else:
			tokens.append(token)				
			
	while "" in tokens:
		tokens.remove("")
	DPRINT("tokens: {}".format(tokens))	
	
	current_soundshader_name = None
	current_tags = list()
	current_params = dict()
	current_sounds = list()
	
	token_index = 0
	num_tokens = len(tokens)
	indentation_level = 0
	
	soundshaders = list()
	while token_index < num_tokens:
		token = tokens[token_index]
		tokenlo = token.lower()
		#print("token_index: {}".format(token_index))
		#print("num_tokens: {}".format(num_tokens))
		if token == "{":
			indentation_level += 1
			#print("indentation_level+: {}".format(indentation_level))
			assert indentation_level <= 1, "indentation_level > 2 in {}".format(sndshd_path)
		elif token == "}":
			indentation_level -= 1
			#print("indentation_level-: {}".format(indentation_level))
			assert indentation_level >= 0, "indentation_level < 0 in {}".format(sndshd_path)
			
			if indentation_level == 0 and current_soundshader_name != None:
				sndshd = SoundShader()
				sndshd.name = current_soundshader_name
				if "editor_displayfolder" in current_params:
					folder = current_params["editor_displayfolder"]
					if not folder.endswith("/"):
						folder += "/"
					sndshd.path = folder + current_soundshader_name
				sndshd.tags = current_tags
				sndshd.params = current_params
				sndshd.sounds = current_sounds
			
				soundshaders.append(sndshd)
			
				DPRINT("soundshader: {}".format(sndshd.name))
				current_soundshader_name = None
				current_tags = list()
				current_params = dict()
				current_sounds = list()
		else:
			if indentation_level == 0:
				current_soundshader_name = token
			else: #indentation_level == 1:
				is_tag = tokenlo in TAG_NAMES
				is_param = tokenlo in PARAM_NAMES
				is_sound = tokenlo.endswith(".wav") or tokenlo.endswith(".ogg")
				
				#assert is_tag or is_param or is_sound, "unknown token: [{}] (is_tag={} is_param={} is_sound={}) in {}".format(token, is_tag, is_param, is_sound, sndshd_path)
				if not is_tag and not is_param and not is_sound:
					DPRINT("warning: ignoring unknown token: [{}] (is_tag={} is_param={} is_sound={}) in {}".format(token, is_tag, is_param, is_sound, sndshd_path))
				
				if is_tag:
					current_tags.append(tokenlo)
				if is_param:
					assert token_index+1 < num_tokens, "found param token but no value specified: [{}] in {}".format(token, sndshd_path)
					current_params[tokenlo] = tokens[token_index+1].lower()
					token_index += 1
				if is_sound:
					current_sounds.append(tokenlo)
		token_index += 1
				
	assert indentation_level == 0, "No closing bracket in {} (indentation_level=={})".format(sndshd_path, indentation_level)
	
	return soundshaders
	
class MapSounddb:
	def __init__(self):
		self.sndshd_dict = dict()
	
		#sndshd_to_sound[sndshd_name] = list()
		#where list contains sound_path(s) that are referenced by the soundshader
		self.sndshd_to_sounds = dict()
		
		#sound_to_sndshd[sound_path] = list()
		#where list contains soundshader(s) that reference the sound_path
		self.sound_to_sndshds = dict()
		
		#list of relative paths to .wav/.ogg
		self.fs_sounds_list = list()
		
	#returns .wav/.ogg paths that are referenced by the soundshader
	def get_sound_of_sndshd(self, sndshd_name):
		sndshd_name = sndshd_name.lower()
		#if sndshd_name not in self.sndshd_to_sounds:
		#	print("MapSounddb::get_sound_of_sndshd() no sndshd_name in dict {}".format(sndshd_name))
		#	return None
		return self.sndshd_to_sounds[sndshd_name]
		
	#returns soundshaders that reference the .wav/.ogg at sound_path
	def get_sndshd_using_sound(self, sound_path):
		sound_path = sound_path.lower()
		#if sound_path not in self.sound_to_sndshds:
		#	print("MapSounddb::get_sndshd_using_sound() no sound_path in dict {}".format(sound_path))
		#	return None
		return self.sound_to_sndshds[sound_path]

		
#Converts between idtech4 and filesystem paths:
#filesystem: C:/pmt_resources/textures/map/textures/folder/texture.png
#   idtech4: /textures/folder/texture
def convert_fs_to_idtech4_path(fs_path, map_textures_path, extension = ".png"):
	idtech4_path = fs_path[len(map_textures_path):-len(extension)]
	return idtech4_path
def convert_idtech4_path_to_fs(idtech4_path, map_textures_path, extension = ".png"):
	if not map_textures_path.endswith('/'):
		map_textures_path += '/'
	return map_textures_path + idtech4_path + extension
	
def parse_sndshd_files(map_sounds_path):
	#
	all_soundshaders = list()
	
	sndshd_files = find_all_files_in(map_sounds_path, ".sndshd")
	for (filename, filepath) in sndshd_files:
		soundshaders = parse_soundshader(filepath)
		all_soundshaders += soundshaders
		
	#
	sndshd_dict = dict()
	for sndshd in all_soundshaders:
		sndshd_dict[sndshd.name] = sndshd
		
	#
	sndshd_to_sounds = dict()
	for sndshd in all_soundshaders:
		assert sndshd.name not in sndshd_to_sounds, "duplicate soundshader name: {}".format(sndshd.name)
		sndshd_to_sounds[sndshd.name] = sndshd.sounds
	
	#'reverse' sndshd_to_sounds;
	#since sndshd_to_sounds should already be lowercase,
	#we do not call lower() here
	sound_to_sndshds = dict()	
	
	for sndshd_name in sndshd_to_sounds:
		sounds = sndshd_to_sounds[sndshd_name]
		for sound_path in sounds:
			if sound_path not in sound_to_sndshds:
				sound_to_sndshds[sound_path] = list()
			sound_to_sndshds[sound_path].append(sndshd_name)
	
	#
	for sndshd_name in sndshd_to_sounds:
		sounds = sndshd_to_sounds[sndshd_name]
		DPRINT("sndshd: {}".format(sndshd_name))
		for sound_path in sounds:
			DPRINT("-> {}".format(sound_path))
			
	for sound_path in sound_to_sndshds:
		soundshaders = sound_to_sndshds[sound_path]
		DPRINT("sound_path: {}".format(sound_path))
		for sndshd_name in soundshaders:
			DPRINT("-> {}".format(sndshd_name))
	
	#
	map_sounds = MapSounddb()
	map_sounds.sndshd_dict = sndshd_dict
	map_sounds.sndshd_to_sounds = sndshd_to_sounds
	map_sounds.sound_to_sndshds = sound_to_sndshds
	
	#
	if True:
		wav_files = find_all_files_in(map_sounds_path, ".wav")
		ogg_files = find_all_files_in(map_sounds_path, ".ogg")
		all_sounds = list()
		map_sounds_path2 = map_sounds_path.replace(os.sep, "/")
		for (filename, filepath) in (wav_files + ogg_files):
			rel_path = filepath.replace(os.sep , "/").replace(map_sounds_path2, "")
			DPRINT("fs_sound: {}".format(rel_path))
			all_sounds.append(rel_path)
		map_sounds.fs_sounds_list = all_sounds
	
	#
	return map_sounds
	
if __name__ == "__main__" and not IN_HOUDINI:
	num_argv = len(sys.argv)
	if not num_argv == 2:
		print("pmt_sounddb_idtech4_sndshd.py [map_sound_path]")
		exit()
		
	map_sounds_path = sys.argv[1]
	
	
	DPRINT("map_sounds_path: ".format(map_sounds_path))
	map_sounddb = parse_sndshd_files(map_sounds_path)
