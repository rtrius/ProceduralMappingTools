#!/usr/bin/env python3
# vmf_mapspecific_prop_material_convert.py
# Converts materials so they can be used with models;
# in general, this means converting .vmt materials from "LightmappedGeneric" to "VertexLitGeneric".
#
# For setup run 'vmf_mapspecific_prop_material_convert.py -d'.
# This script should be run from 'C:/pmt_resources/scripts/setup/';
# the current working directory must be 'C:/pmt_resources/scripts/setup/'.
#
# Running this script will duplicate .vmt files and place them in search_path/_msp/.
# By default the path will be C:/pmt_resources/materials/vmf/materials/_msp/. The '_msp'
# folder must be copied to the Source project directory afterwards, if map-specific props are used.

DEFAULT_SEARCH_PATH = "../../materials/vmf/materials"

import sys
import os
import string
import copy

IN_HOUDINI = 'hou' in sys.modules

def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
import inspect
CF = inspect.currentframe
def CURFUNC(inspect_currentframe): #return the name of the 'current function':  CURFUNC(CF())
	return inspect_currentframe.f_code.co_name
def CCF(self, inspect_currentframe, sep = "::", suffix = "()"): #return the name the the 'current class function': CCF(self, CF())
	return type(self).__qualname__ + sep + inspect_currentframe.f_code.co_name +  suffix
	
#By default open() uses locale.getpreferredencoding();
#Houdini 18.5 on Windows 10 locale.getpreferredencoding() returns 'cp65001', but
#a standalone Python3 install returns 'cp1252'. Using cp65001 causes the decoding to
#fail, so explicitly set the codec here.
TEXT_CODEC = "cp1252" #windows-1252 'Western Europe'

def parse_vmt(vmt_path):
	with open(vmt_path, 'rt', encoding=TEXT_CODEC) as vmt_file:
		text = ""
		for line in vmt_file:
			text += line
				
		def remove_comments(text):
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
			return text_without_comments
		text = remove_comments(text)
	
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
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, vmt_path)
	
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
	
	while "" in tokens_with_quotes:
		tokens_with_quotes.remove("")
		
	tokens = list()
	for token in tokens_with_quotes:
		if token.startswith(INQUOTE_TOKEN):
			tokens.append(inquote_text_dict[token])
		else:
			tokens.append(token)	
			
	DPRINT("tokens: {}".format(tokens))	
	
	
	#
	VALIDATE_BRACKETS = True
	if VALIDATE_BRACKETS:
		num_open = 0
		num_close = 0
		for t in tokens:
			if t == "{":
				num_open += 1
			elif t == "}":
				num_close += 1
		if num_open != num_close:
			error = "{} is missing opening or closing brackets({} open, {} close)".format(vmt_path, num_open, num_close)
			print(error)
			return None
		
	#
	num_tokens = len(tokens)
	token_index = 0
	while token_index < num_tokens:
		t = tokens[token_index]
		
		if t == "{":
			opening_index = token_index
			shader = tokens[opening_index - 1].lower()
			
			DPRINT("shader: {}".format(shader))
			
			def extract_tokens_in_brackets(shader, tokens, tokens_with_quotes, opening_index, global_bracket_depth):
				assert global_bracket_depth <= 4, "expected max bracket_depth == 4, is {} (shader={}, tokens={})".format(global_bracket_depth, shader, tokens) 
			
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
				in_bracket_tokens_quotes = tokens_with_quotes[opening_index:closing_index+1]
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
					t2quote = in_bracket_tokens_quotes[token_index2]
					t2lo = t2.lower()
					
					#Assuming that there are 2 types of tokens in .vmt files:
					#	- If the token is followed by an opening '{' brace,  then there should be a closing '}' brace and we create a dict().
					#	- otherwise, then it is a key-value pair in the format:
					#		"a" "b"
					if in_bracket_tokens[token_index2+1] == "{":
						if t2lo not in kv_dict:
							kv_dict[t2lo] = dict()
							
						(closing_index2, kv_dict2) = extract_tokens_in_brackets(t2lo, in_bracket_tokens, in_bracket_tokens_quotes, token_index2+1, global_bracket_depth+1)
						kv_dict[t2lo] = kv_dict2
						token_index2 = closing_index2
					else:
						t2next = in_bracket_tokens[token_index2+1]
						token_index2 += 1
						#kv_dict[t2] = t2next
						kv_dict[t2lo] = t2next.lower()
						
					token_index2 += 1
				
				
				return (closing_index, kv_dict)
				
			(closing_index, vmt_dict2) = extract_tokens_in_brackets(shader, tokens, tokens_with_quotes, opening_index, 1)
			DPRINT("tokens: {}".format(tokens[opening_index:closing_index+1]))
			
			vmt_dict = dict()
			vmt_dict[shader] = vmt_dict2
			DPRINT("vmt_dict: {}".format(vmt_dict))
			DPRINT("")
			
			token_index = closing_index
			
		token_index += 1
		
	#	
	return vmt_dict
	
				
def find_all_files_in(search_path, extension):
	path_list = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			
			if not filepath.endswith(extension):
				continue
			
			print(extension + ": " + filepath.replace(search_path, ""))
			path_list.append(filepath)
	return path_list

def tabs(num_tabs):
	s = ""
	for i in range(num_tabs):
		s += "\t"
	return s

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("vmf_mapspecific_prop_material_convert.py [search_path] -- converts suitable materials in search_path for models")
		print("vmf_mapspecific_prop_material_convert.py -d -- converts suitable materials in {} for models".format(DEFAULT_SEARCH_PATH))
		exit()
	else:
		search_path = sys.argv[1]
		if search_path == "-d":
			cwd = os.getcwd()
			(cwd, first_folder) = os.path.split(cwd)
			(cwd, second_folder) = os.path.split(cwd)
			if first_folder.lower() != "setup" or second_folder.lower() != "scripts":
				print("When using -d, this script must be run from /pmt_resources/scripts/setup/.")
				exit()
			search_path = DEFAULT_SEARCH_PATH
		
		
	if not search_path.endswith("materials"):
		print("vmf_mapspecific_prop_material_convert.py [search_path]")
		print("[search_path] must end with 'materials' (lowercase)")
		exit()
		
	fail_conversions = list()
		
	vmt_paths = find_all_files_in(search_path, ".vmt")
	
	path_and_dict = list()
	for path in vmt_paths:
		if "/_msp/" in path.replace("\\", "/"):
			continue
	
		print("convert: " + path)
		vmt_dict = parse_vmt(path)
		if vmt_dict == None:
			fail_conversions.append(path)
		else:
			assert len(vmt_dict) == 1, "each material should have only 1 top-level shader name"
			top_level_shader = list(vmt_dict.keys())[0]
			
			#duplicating all materials causes hammer to crash,
			#a possible reason might be that some materials can only be defined once?
			SUPPORTED_SHADERS = ["vertexlitgeneric", "lightmappedgeneric", "unlitgeneric", "worldvertextransition", "spritecard"]
			if top_level_shader in SUPPORTED_SHADERS:
				path_and_dict.append( (path, vmt_dict) )
			
	for path in fail_conversions:
		print("failed to parse: " + path)
	
	PRINT_SHADER_TYPES = True
	if PRINT_SHADER_TYPES:
		shader_counts = dict()
		for (path, vmt_dict) in path_and_dict:
			for key in vmt_dict: #top-level shader name
				if key not in shader_counts:
					shader_counts[key] = 0
				shader_counts[key] += 1
		print("shader_types:")
		
		shaders = list()
		for s in shader_counts:
			shaders.append((shader_counts[s], s))
		shaders.sort()
		for (count, shadername) in shaders:
			print("{}({} instances)".format(shadername, count))

	CONVERT_MATERIALS = True
	if CONVERT_MATERIALS:
		for i in range(len(path_and_dict)):
			(path, vmt_dict) = path_and_dict[i]
			keys = vmt_dict.keys()
			assert len(vmt_dict) == 1, "each material should have only 1 top-level shader name"
			top_level_shader = list(keys)[0]
			
			print("converting: {}".format(path))
			print("from: {}".format(vmt_dict))
			
			#replaces(renames) each key in a dict that starts with 'old' with 'new'
			def rename_shaders(material_dict, old, new):
				for key in list(material_dict.keys()):
					if key.startswith(old):
						value = material_dict[key]
						newkey = new + key[len(old):]
						del material_dict[key]
						material_dict[newkey] = value
				for key in material_dict:
					if type(material_dict[key]) == type(dict()):
						material_dict[key] = rename_shaders(material_dict[key], old, new)
				return material_dict
			
			def delete_keys(material_dict, key_list):
				for key in list(material_dict.keys()):
					if key in key_list:
						del material_dict[key]
				for key in material_dict:
					if type(material_dict[key]) == type(dict()):
						material_dict[key] = delete_keys(material_dict[key], key_list)
				return material_dict
				
			
			def convert_lightmappedgeneric(material_dict):
				return rename_shaders(material_dict, "lightmappedgeneric", "vertexlitgeneric")
			def convert_unlitgeneric(material_dict):
				if "$model" not in material_dict["unlitgeneric"]:
					material_dict["unlitgeneric"]["$model"] = "1"
				return material_dict
			def convert_worldvertextransition(material_dict):
				for key in list(material_dict["worldvertextransition"].keys()):
					if key not in ["$basetexture", "$surfaceprop"]:
						del material_dict["worldvertextransition"][key]
				material_dict = rename_shaders(material_dict, "worldvertextransition", "vertexlitgeneric")
				return material_dict
			def convert_spritecard(material_dict):
				return rename_shaders(material_dict, "spritecard", "vertexlitgeneric")
			switch = dict()
			switch["lightmappedgeneric"] = convert_lightmappedgeneric
			switch["unlitgeneric"] = convert_unlitgeneric
			switch["worldvertextransition"] = convert_worldvertextransition
			switch["spritecard"] = convert_spritecard
			
			if top_level_shader in switch:
				vmt_dict = switch[top_level_shader](vmt_dict)
			
			REMOVED_KEYS = ["$basetexture2",
			"$basetexturetransform2",
			"$blendmodulatetexture",
			"$bumpmap2",
			"$decal",
			"$detail",
			"$reflectivity"
			"$seamless_scale", 
			"$ssbump",
			"$surfaceprop2"]
			vmt_dict = delete_keys(vmt_dict, REMOVED_KEYS)
			print("to: {}".format(vmt_dict))
			
			path_and_dict[i] = (path, vmt_dict)
			
	WRITE_MATERIALS = True
	if WRITE_MATERIALS:
		output_path = search_path.replace("\\", "/") + "/_msp/"
		print("output_path: " + output_path)
		if not os.path.exists(output_path):
			os.mkdir(output_path)
			
		for (path, vmt_dict) in path_and_dict:
			material_name = path[len(search_path)+1:].replace("\\", "_").replace("/", "_")
			new_vmt_path = output_path + material_name
			print("writing new vmt: " + new_vmt_path)
			print("vmt_dict: {}".format(vmt_dict))
			with open(new_vmt_path, 'wt') as f:
				def write_converted_material(file, material_dict, depth = 0):
					for key in material_dict:
						if type(material_dict[key]) == type(dict()):
							file.write(tabs(depth) + "\"{}\"\n".format(key))
							file.write(tabs(depth) + "{\n")
							write_converted_material(file, material_dict[key], depth + 1)
							file.write(tabs(depth) + "}\n")
						else:
							file.write(tabs(depth) + "\"{}\" \"{}\"\n".format(key, material_dict[key]))
				write_converted_material(f, vmt_dict)