#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_sounddb_source1
#	script_section_name: 	pmt_sounddb_source1.py


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

#Converts between source and filesystem paths:
#filesystem: C:/pmt_resources/textures/vmf/materials/folder/texture.png
#    source: folder/texture
def convert_fs_to_source_path(fs_path, vmf_textures_path, extension = ".png"):
	source_path = fs_path[len(vmf_textures_path):-len(extension)]
	while source_path.startswith("/"):
		source_path = source_path[1:]
	return source_path
def convert_source_path_to_fs(source_path, vmf_textures_path, extension = ".png"):
	if not vmf_textures_path.endswith('/'):
		vmf_textures_path += '/'
	return vmf_textures_path + source_path + extension

# class VmfSound:
	# def __init__(self):
		# self.name = None
		# self.keyvalues = None
		
class VmfSoundDb:

	#single line statements in format:
	#	"key" "value"
	KEYVALUE_TOKENS = ["channel", "volume", "pitch", "soundlevel", "dsp", "dsp_volume", 
	"wave", "attenuation", "time", "position", "positionoverride", "name", "soundmixer",
	"suppress_on_restore"]
	
	#multiline statement in format:
	#	"bracket"
	#	{
	#		"key" "value"
	#		"key" "value"
	#		...
	#		"key" "value"
	#	}
	#BRACKET_TOKENS = ["rndwave"]
	#BRACKET_TOKENS = ["playrandom", "playlooping", "playsoundscape"]
	BRACKET_TOKENS = ["rndwave", "playrandom", "playlooping", "playsoundscape"]
	
	def __init__(self):
		#Both all_soundscripts and all_soundscapes are multi-level dict():
		#	self.all_soundscripts[SOUND_NAME] contains the key-value dict for SOUND_NAME,
		#for example, if SOUND_NAME has 'volume' specified, we access it with:
		#	self.all_soundscripts[SOUND_NAME]['volume']
		#the 'volume' key contains the volume as a string
		#
		#1) if the key is in KEYVALUE_TOKENS, the value of the key is stored as a string
		#	1b) An exception is if the key is "wave", in which case the key is a list of strings.
		#	This is since a "rndwave" statement can contain multiple "wave" statements.
		#2) if the key is in BRACKET_TOKENS, the value of the key is a list(), for which each element is a dict().
		#The key is a list, as there can be multiple "playrandom", "playlooping", and "playsoundscape" statements in a soundscape.
		
		self.all_soundscripts = None
		self.all_soundscapes = None
		
		#list of relative paths to .wav
		self.fs_sounds_list = list()
	
	def get_all_sounds(self, sound_name):
		def find_waves(kv_dict, soundscapes = None):
			result_list = list()
			for key in kv_dict:
				if key == "wave":
					result_list += kv_dict["wave"]
				elif key in VmfSoundDb.BRACKET_TOKENS: 
					assert type(kv_dict[key]) == type(list())
					if key == "playsoundscape" and soundscapes != None:
						for sub_kv_dict in kv_dict["playsoundscape"]:
							if "name" in sub_kv_dict:
								soundscape_name = sub_kv_dict["name"]
								if soundscape_name in soundscapes:
									result_list += find_waves(soundscapes[soundscape_name], soundscapes)
					else:
						for sub_kv_dict in kv_dict[key]:
							result_list += find_waves(sub_kv_dict)
				
			#DPRINT("result_list: {}".format(result_list))		
			return result_list
					
			
		is_soundscript = sound_name in self.all_soundscripts
		is_soundscape = sound_name in self.all_soundscapes
		assert not (is_soundscript and is_soundscape), "error: {} is both a soundscript and soundscape".format(sound_name)
			
		if is_soundscript:
			sound_paths = find_waves(self.all_soundscripts[sound_name], self.all_soundscapes)
			return sound_paths
			
		if is_soundscape:
			sound_paths = find_waves(self.all_soundscapes[sound_name], self.all_soundscapes)
			return sound_paths
			
		DPRINT("{} is not a soundscript or soundscape".format(sound_name))
		return None
	
def parse_soundscript(soundscript_path):
	with open(soundscript_path, 'rt', encoding=TEXT_CODEC) as soundscript_file:
		text = ""
		for line in soundscript_file:
			left, sep, right = line.partition("//")
			text += left
			
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
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, soundscript_path)
	
	def simplify_whitespace(text):
		for char in string.whitespace:
			text = text.replace(char, " ")
		return text
	text_without_quotes = simplify_whitespace(text_without_quotes)
	
	def pad_operators(text):
		#pad '{', '}', ... with spaces so that split() will not mix them with text
		PAD_CHARS = "{}"
		for char in PAD_CHARS:
			text = text.replace(char, " {} ".format(char))
		return text
	text_without_quotes = pad_operators(text_without_quotes)
	
	#replace sequences of spaces with a single space
	def compact_spaces(text):
		SPACES_4 = "    "
		SPACES_2 = "  "
		while text.find(SPACES_4) != -1:
			text = text.replace(SPACES_4, " ")
		while text.find(SPACES_2) != -1:
			text = text.replace(SPACES_2, " ")
		return text
	text_without_quotes = compact_spaces(text_without_quotes)
	
	#
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
	
	sound_dict = dict()
	
	#
	num_tokens = len(tokens)
	token_index = 0
	while token_index < num_tokens:
		t = tokens[token_index]
		
		if t == "{":
			opening_index = token_index
			sound_name = tokens[opening_index - 1].lower()
			
			#DPRINT("sound({})[{}:{}]: {}".format(sound_name, opening_index, closing_index, tokens[opening_index:closing_index+1]))	
			DPRINT("sound: {}".format(sound_name))
			
			def extract_tokens_in_brackets(sound_name, tokens, opening_index, global_bracket_depth):
				assert global_bracket_depth <= 3, "expected max bracket_depth == 3, is {} (sound_name={}, tokens={})".format(global_bracket_depth,  sound_name, tokens) 
			
				DEBUG_SPACING = ""
				for i in range(global_bracket_depth):
					DEBUG_SPACING += "  "
			
				assert tokens[opening_index] == "{"
				closing_index = opening_index+1
				bracket_depth = 1
				
				#find closing_index
				while closing_index < num_tokens:
					t2 = tokens[closing_index]
					if t2 == "{": bracket_depth += 1
					if t2 == "}": bracket_depth -= 1
					
					if bracket_depth == 0:
						break
				
					closing_index += 1
				
				assert tokens[closing_index] == "}"
				in_bracket_tokens = tokens[opening_index:closing_index+1]
				assert in_bracket_tokens[0] == "{", "in_bracket_tokens: {}".format(in_bracket_tokens)
				assert in_bracket_tokens[-1] == "}", "in_bracket_tokens: {}".format(in_bracket_tokens)
				
				kv_dict = dict()
				
				token_index2 = 0
				num_tokens2 = len(in_bracket_tokens)
				while token_index2 < num_tokens2:
					#skip first/last brackets
					if token_index2 == 0 or token_index2 == num_tokens2 - 1:
						token_index2 += 1
						continue
				
					t2 = in_bracket_tokens[token_index2]
					t2lo = t2.lower()
					if t2lo in VmfSoundDb.KEYVALUE_TOKENS:
						next_token = in_bracket_tokens[token_index2+1]
						token_index2 += 1
						DPRINT("{}kv: {} = {}".format(DEBUG_SPACING, t2lo, next_token))
						if t2lo != "wave":
							kv_dict[t2lo] = next_token
						else:
							assert t2lo == "wave"
							if "wave" not in kv_dict:
								kv_dict["wave"] = list()
							kv_dict["wave"].append(next_token)
							
					elif t2lo in VmfSoundDb.BRACKET_TOKENS:
						assert in_bracket_tokens[token_index2+1] == "{", "Expected opening_bracket at index {} (is '{}'): {}".format(token_index2+1, in_bracket_tokens[token_index2+1], in_bracket_tokens)
						DPRINT("{}bracket: {}".format(DEBUG_SPACING, in_bracket_tokens[token_index2]))
						(closing_index2, kv_dict2) = extract_tokens_in_brackets(sound_name, in_bracket_tokens, token_index2+1, global_bracket_depth+1)
						
						if t2lo not in kv_dict:
							kv_dict[t2lo] = list()
							
						kv_dict[t2lo].append(kv_dict2)
						
						token_index2 = closing_index2
					else:
						assert False, "unexpected token: {} (index={} tokens={})".format(t2, token_index2, in_bracket_tokens)
					token_index2 += 1
				
				
				return (closing_index, kv_dict)
				
			(closing_index, kv_dict) = extract_tokens_in_brackets(sound_name, tokens, opening_index, 1)
			DPRINT("sound tokens: {}".format(tokens[opening_index:closing_index+1]))
			DPRINT("sound kv_dict: {}".format(kv_dict))
			DPRINT("")
			
			sound_dict[sound_name] = kv_dict
			
			token_index = closing_index
			
		token_index += 1
		
	#4. parse in between brackets(depth >= 1)
	return sound_dict
	
def parse_manifest(manifest_path):
	soundscript_paths = list()
	with open(manifest_path, 'rt', encoding=TEXT_CODEC) as manifest_file:
		for line in manifest_file:
			#ignored commented lines // 
			left, sep, right = line.partition("//")
			
			#search for lines in format:
			#	"file"				"scripts/path_to_soundscript.txt"
			#	"precache_file"		"scripts/path_to_soundscript.txt"
			if left.count("\"") == 4:
				first = left.find("\"")
				second = left.find("\"", first+1)
				third = left.find("\"", second+1)
				fourth = left.find("\"", third+1)
				
				file = left[first+1:second]
				path = left[third+1:fourth]
				
				FILE_TYPES = ["file", "precache_file"]
				assert file.lower() in FILE_TYPES, "unexpected file type: '{}' in manifest '{}'".format(file, manifest_path)
		
				DPRINT("soundscript: {} ({})".format(path, file))
				soundscript_paths.append(path)
		
	return soundscript_paths
	
def parse_vmf_sounds(vmf_game_path):
	#
	if "\\" in vmf_game_path:
		vmf_game_path = vmf_game_path.replace("\\", "/")
	if not vmf_game_path.endswith("/"):
		vmf_game_path += "/"
	
	game_sounds_manifest = vmf_game_path + "scripts/game_sounds_manifest.txt"
	soundscapes_manifest = vmf_game_path + "scripts/soundscapes_manifest.txt"
		
	soundscript_paths = parse_manifest(game_sounds_manifest)
	soundscape_paths = parse_manifest(soundscapes_manifest)
	
	all_soundscripts = dict()
	all_soundscapes = dict()
	
	for path in soundscript_paths:
		fullpath = vmf_game_path + path
		if os.path.isfile(fullpath):
			sound_dict = parse_soundscript(fullpath)
			for sound_name in sound_dict:
				all_soundscripts[sound_name] = sound_dict[sound_name]
		else:
			DPRINT("({}) {} is not a file; ignoring ".format(game_sounds_manifest, fullpath))
			
	for path in soundscape_paths:
		fullpath = vmf_game_path + path
		if os.path.isfile(fullpath):
			sound_dict = parse_soundscript(fullpath)
			for sound_name in sound_dict:
				all_soundscapes[sound_name] = sound_dict[sound_name]
		else:
			DPRINT("({}) {} is not a file; ignoring ".format(soundscapes_manifest, fullpath))
	
	#
	vmf_sounddb = VmfSoundDb()
	vmf_sounddb.all_soundscripts = all_soundscripts
	vmf_sounddb.all_soundscapes = all_soundscapes
	
	#
	DPRINT("found {} soundscripts".format(len(all_soundscripts)))
	DPRINT("found {} soundscapes".format(len(all_soundscapes)))
	
	#
	for sound_name in vmf_sounddb.all_soundscripts:
		sound_paths = vmf_sounddb.get_all_sounds(sound_name)
		DPRINT("")
		DPRINT("soundscript: {}".format(sound_name))
		for path in sound_paths:
			DPRINT("-> {}".format(path))
			
	for sound_name in vmf_sounddb.all_soundscapes:
		sound_paths = vmf_sounddb.get_all_sounds(sound_name)
		DPRINT("")
		DPRINT("soundscape: {}".format(sound_name))
		for path in sound_paths:
			DPRINT("-> {}".format(path))
	
	#
	if True:
		wav_files = find_all_files_in(vmf_game_path, ".wav")
		all_sounds = list()
		vmf_game_path2 = vmf_game_path.replace(os.sep, "/")
		for (filename, filepath) in wav_files:
			rel_path = filepath.replace(os.sep, "/").replace(vmf_game_path2, "")
			DPRINT("wav: {}".format(rel_path))
			all_sounds.append(rel_path)
		vmf_sounddb.fs_sounds_list = all_sounds
	
	
	return vmf_sounddb
	
if __name__ == "__main__" and not IN_HOUDINI:
	num_argv = len(sys.argv)
	if not num_argv == 2:
		DPRINT("pmt_sounddb_source1.py [vmf_sounds_path]")
		exit()
		
	vmf_sounds_path = sys.argv[1]
	
	DPRINT("vmf_sounds_path: ".format(vmf_sounds_path))
	vmf_sounddb = parse_vmf_sounds(vmf_sounds_path)
	
