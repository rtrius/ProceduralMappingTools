#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	parse_source1_fgd
#	script_section_name: 	PythonModule_parse_source1_fgd
#
# search_path is in format C:\dir
#
#

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
	
def find_all_files_in(search_path, extension = ".fgd"):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			if not dirpath.endswith(os.sep) and not dirpath.endswith('/'):
				filepath = dirpath + os.sep + filename
			else:
				filepath = dirpath + filename
			
			if filepath.endswith(extension):
				paths.append((filename, filepath))
				DPRINT("{0}: {1}".format(extension, filepath))
	return paths
	
#input_or_output name(argument_type) : description
class EInputOutput:
	def __init__(self):
		self.name = ""
		self.in_or_out = None #string that is "input" or "output"
		self.argument_type = None
		self.description = None
	def __str__(self):
		return self.name
	
class EPropertyFlag:
	def __init__(self):
		self.bit = None				#string: a 32-bit unsigned int in (1, 2, ..., 4294967296), which represents the bit of this flag
		self.description = None
		self.default = None			#string: 0 or 1
		
class EPropertyChoice:
	def __init__(self):
		self.value = None
		self.description = None
	def __repr__(self):
		return "({}, {})".format(self.value, self.description)
		
#name(type) : short_description : default : long_description
class EProperty:
	def __init__(self):
		self.name = ""
		self.type = None
		
		#default_value is usually a string; 
		#if self.type is "choices", then this is an index(int) into choices_list
		#if self.type is "flags", then this is a string containing the int32 value of all flags enabled
		self.default_value = ""		
		
		self.short_description = ""
		self.long_description = ""
		
		self.choices_list = None #EPropertyChoice
		self.flags_dict = None #EPropertyFlag, keys are power of 2 ints as string: flags_dict["524288"]; note that iterating 'for f in self.flags_dict:' is not in order
	
	def get_flags_default_value(self):
		assert self.type == "flags"
		assert self.flags_dict != None
	
		default_int32 = 0
		for flagstr in self.flags_dict:
			flag = self.flags_dict[flagstr]
					
			bit_index = int(flag.bit).bit_length() - 1
			if int(flag.default) == 1:
				default_int32 |= 1 << bit_index
		return str(default_int32)

	def get_flags_descriptions(self):
		assert self.type == "flags"
		assert self.flags_dict != None
		
		flags_descriptions_list = list()
		for i in range(32):
			flags_descriptions_list.append("")
				
		for flagstr in self.flags_dict:
			flag = self.flags_dict[flagstr]
			bit_index = int(flag.bit).bit_length() - 1
			flags_descriptions_list[bit_index] = flag.description
		return flags_descriptions_list
	
	def get_default_value_str(self):
		if self.type == "flags": 
			return self.get_flags_default_value()
		if self.type == "choices":
			choices_index = self.default_value
			assert choices_index < len(self.choices_list), CCF(self, CF()) + ": invalid default_value({}) for choices {}".format(choices_index, self.choices_list)
			
			return self.choices_list[choices_index].value
			
		return self.default_value
class Entity:
	def __init__(self):
	
		self.classtype = ""
		self.classname = ""
		self.description = ""
		
		self.component_list_of_lists = list() 	#a component 'base(a, b, c)' is parsed into the list [base, a, b, c]
		self.input_output_dict = dict()
		self.property_dict = dict()
		
		#list of classname(s) of parent entities, not ordered
		self.parent_list = None
		
		self.class_hierarchy = None #class_hierarchy[0] is classname, and is followed by immediate parents
		
		#i/o and props, including inherited ones
		self.all_input_output_dict = dict()
		self.all_property_dict = dict()
		
	def is_placeable(self):
		#todo: some classes such as 'light' are @baseclass and also placeable
		#need to determine the actual factors used to decide which entities can be placed in the editor
		return self.classtype.lower() != "@baseclass"
		
	def has_model(self):
		has_model_prop = "model" in self.all_property_dict
		
		has_studio_component = False
		for component_list in self.component_list_of_lists:
			if component_list[0] == "studio":
				has_studio_component = True
				break
				
		return has_model_prop or has_studio_component
		
	def get_default_model(self):
		if "model" in self.all_property_dict:
			modelprop = self.all_property_dict["model"]
			if modelprop.type == "studio":
				return modelprop.default_value
			elif modelprop.type == "choices": #if type is choices, default_value is an int
				choices_index = modelprop.default_value
				return modelprop.choices_list[choices_index].value
			
		for component_list in self.component_list_of_lists:
			if component_list[0] == "studio":
				return component_list[1]
				
		assert False, CCF(self, CF()) + ": no default model found for class {}".format(self.classname)
	#def __str__(self):
	#	return "{} {} {}".format(self.name self.input_output_dict, self.property_dict)
def parse_source1_fgd(fgd_paths):

	INCLUDE_NEWLINES = True

	#load .fgd files and create a series of tokens for each file
	fgd_tokens_dict = dict()
	inquote_text_dict = dict()
	
	INQUOTE_TOKEN = "%%q_"
	NEWLINE_TOKEN = "%%n"
	inquote_token_index = 0
	for (name, filepath) in fgd_paths:
		DPRINT("parsing: {}".format(filepath))
		
		#By default open() uses locale.getpreferredencoding();
		#Houdini 18.5 on Windows 10 locale.getpreferredencoding() returns 'cp65001', but
		#a standalone Python3 install returns 'cp1252'. Using cp65001 causes the decoding to
		#fail, so explicitly set the codec here.
		CODEC = "cp1252" #windows-1252 'Western Europe'
		with open(filepath, 'rt', encoding=CODEC) as f:
			text = ""
			for line in f:
				text += line
			
			#remove text after // comments; note that single line comments precede multiline comments
			#keepends == True, so we keep the newline chars(/n, /r, ...) 
			text_without_comments = ""
			for line in text.splitlines(keepends = True):
				if len(line) == 0: continue

				left, sep, right = line.partition("//")
				text_without_comments += left
			
			#	todo:  check whether .fgd supports multiline comments
			#remove text in between /* */ comments
			REMOVE_MULTILINE_COMMENTS = False
			if REMOVE_MULTILINE_COMMENTS:
				multiline_comment_start_index = text_without_comments.find("/*")
				while multiline_comment_start_index != -1:
					left1, sep1, right1 = text_without_comments.partition("/*")
					left2, sep2, right2 = right1.partition("*/")
					text_without_comments = left1 + right2
					multiline_comment_start_index = text_without_comments.find("/*")
			
			#DPRINT("commentsremoved: " +  text_without_comments)
			
			if INCLUDE_NEWLINES:
				#Make sure that the text does not contain NEWLINE_TOKEN before adding it
				assert text_without_comments.find(NEWLINE_TOKEN) == -1, "error: .fgd contains NEWLINE_TOKEN {}".format(NEWLINE_TOKEN)
				
				#To make debug print more dense/easier to read we want to remove newlines.
				#However, newlines might be used to indicate the end of entity properties so
				#replace it with a special token.
				for char in string.whitespace:
					text_without_comments = text_without_comments.replace("\n", " {} ".format(NEWLINE_TOKEN))
			
			#replace tabs, return, etc. with " "
			#important: this can only happen after parsing '//' type comments
			for char in string.whitespace:
				text_without_comments = text_without_comments.replace(char, " ")
			
			#DPRINT("removedwhitespace: " +  text_without_comments)
			
			#extract text in between quotes
			assert text_without_comments.find(INQUOTE_TOKEN) == -1, "error: .fgd contains INQUOTE_TOKEN {}".format(INQUOTE_TOKEN)
			
			in_quote = False
			text_without_quotes = ""
			inquote_buffer = ""
			for char in text_without_comments:
				if char == "\"":
					if not in_quote: #opening quote
						inquote_buffer = ""
					else: #closing quote
						dict_id_str = INQUOTE_TOKEN + str(inquote_token_index)
						inquote_token_index += 1
						inquote_text_dict[dict_id_str] = inquote_buffer
						text_without_quotes += " {} ".format(dict_id_str)
					in_quote = not in_quote
				else:
					if in_quote:
						inquote_buffer += char
					else:
						text_without_quotes += char
			assert not in_quote, "error: missing closing quote"
			
			#DPRINT("removedquotes: " +  text_without_quotes)
			#for id in inquote_text_dict:
			#	DPRINT("{}: {}".format(id, inquote_text_dict[id]))
			
			#pad '{', '}', ... with spaces so that split() will not mix them with text
			PAD_CHARS = "{}[]():=,+"
			for char in PAD_CHARS:
				text_without_quotes = text_without_quotes.replace(char, " {} ".format(char))
			
			#replace sequences of spaces with a single space
			SPACES_4 = "    "
			SPACES_2 = "  "
			while text_without_quotes.find(SPACES_4) != -1:
				text_without_quotes = text_without_quotes.replace(SPACES_4, " ")
			while text_without_quotes.find(SPACES_2) != -1:
				text_without_quotes = text_without_quotes.replace(SPACES_2, " ")
			
			#DPRINT("pretoken: " +  text_without_quotes)
			tokens = text_without_quotes.split(sep = " ", maxsplit = -1)
			DPRINT("tokens: " + str(tokens))
			
			fgd_tokens_dict[filepath] = tokens
			
	#validate brackets
	def validate_bracket_depth(tokens, open_bracket = "{", close_bracket = "}", min_depth = 0, max_depth = 128):
		bracket_depth = 0
		
		min_depth_in_range = True
		max_depth_in_range = True
		
		for t in tokens:
			if t == open_bracket: bracket_depth += 1
			if t == close_bracket: bracket_depth -= 1
			if bracket_depth < min_depth: min_depth_in_range = False
			if bracket_depth > max_depth: max_depth_in_range = False
			
		all_brackets_closed = (bracket_depth == 0)	
		
		assert min_depth_in_range, "bracket min_depth {} exceeded ('{}' '{}')".format(min_depth, open_bracket, close_bracket)
		assert max_depth_in_range, "bracket max_depth {} exceeded ('{}' '{}')".format(max_depth, open_bracket, close_bracket)
		assert all_brackets_closed,  "no closing bracket ('{}' '{}')".format(open_bracket, close_bracket)
		
		return all_brackets_closed and min_depth_in_range and max_depth_in_range
		
	for filepath in fgd_tokens_dict:
		tokens = fgd_tokens_dict[filepath]
		#FGD does not contain {} brackets
		assert validate_bracket_depth(tokens, "{", "}", 0, 0), "bracket validation failed in {}".format(filepath)
		assert validate_bracket_depth(tokens, "(", ")", 0, 1), "bracket validation failed in {}".format(filepath)
		assert validate_bracket_depth(tokens, "[", "]", 0, 2), "bracket validation failed in {}".format(filepath)
	
	#
	TOKEN_IGNORED = ["@mapsize", "@include"]
	
	TOKEN_OPERATORS = list()
	TOKEN_OPERATORS += ["(", ")", "{", "}", "[", "]", "+", ":", "=", ","]
	
	#class definition format:
	#	@CLASSTYPE COMPONENT_LIST = CLASS_NAME : CLASS_DESCRIPTION [ ENTITY_PROPERTIES_LIST ]
	TOKEN_CLASS_DEFINITIONS = list()
	TOKEN_CLASS_DEFINITIONS += ["@pointclass", "@npcclass", "@solidclass", "@keyframeclass", "@moveclass"]
	TOKEN_CLASS_DEFINITIONS += ["@filterclass", "@baseclass"]
	
	#'components' in COMPONENT_LIST above, format is:
	#	COMPONENT_NAME(ARGUMENTS)
	TOKEN_CLASS_COMPONENTS = list()
	TOKEN_CLASS_COMPONENTS += ["base", "color", "iconsprite", "sidelist", "sphere", "studioprop"]
	TOKEN_CLASS_COMPONENTS += ["studio", "lightprop", "line", "cylinder", "lightcone"]
	TOKEN_CLASS_COMPONENTS += ["frustum", "halfgridsnap", "wirebox", "size", "origin"]
	TOKEN_CLASS_COMPONENTS += ["vecline", "axis", "decal", "overlay", "overlay_transition"]
	TOKEN_CLASS_COMPONENTS += ["sweptplayerhull", "instance"]
	
	#input/output entity properties, format is:
	#	input INPUT_NAME(TYPE) : DESCRIPTION
	#	output OUTPUT_NAME(TYPE) : DESCRIPTION
	TOKEN_IO_DEFINITIONS = list()
	TOKEN_IO_DEFINITIONS += ["input", "output"]
	
	TOKEN_ENTITY_PROP_TYPE = list()
	#entity properties
	TOKEN_ENTITY_PROP_TYPE += ["void"]
	TOKEN_ENTITY_PROP_TYPE += ["string", "integer", "float", "choices", "flags"]
	#entity properties ui
	TOKEN_ENTITY_PROP_TYPE += ["axis", "angle", "color255", "color1", "filterclass", "decal", "material", "node_dest", "npcclass"]
	TOKEN_ENTITY_PROP_TYPE += ["origin", "pointentityclass", "scene", "sidelist", "sound", "sprite", "studio"]
	TOKEN_ENTITY_PROP_TYPE += ["target_destination", "target_name_or_class", "target_source", "vecline", "vector"]
	
	#display unparsed tokens for debugging
	DETECT_UNPARSED_TOKENS = False
	if DETECT_UNPARSED_TOKENS:
		TOKENLIST = list()
		TOKENLIST += TOKEN_IGNORED
		TOKENLIST += TOKEN_OPERATORS
		TOKENLIST += TOKEN_CLASS_COMPONENTS
		TOKENLIST += TOKEN_CLASS_DEFINITIONS
		TOKENLIST += TOKEN_IO_DEFINITIONS
		TOKENLIST += TOKEN_ENTITY_PROP_TYPE
		
		unparsed_tokens = list()
		for filepath in fgd_tokens_dict:
			tokens = fgd_tokens_dict[filepath]
			for t in tokens:
				if t.lower() in TOKENLIST or t.startswith(INQUOTE_TOKEN) or t.startswith(NEWLINE_TOKEN):
					pass
				else:
					unparsed_tokens.append(t)
		DPRINT("unparsed_tokens: {}".format(unparsed_tokens))
	
	if INCLUDE_NEWLINES:
		#debug
		if False:
			for filepath in fgd_tokens_dict:
				tokens = fgd_tokens_dict[filepath]
				DPRINT("tokens with duplicate newlines({}): {}".format(filepath, tokens))
			
		#pre-pass to remove duplicate NEWLINE_TOKEN(s) from token list
		for filepath in fgd_tokens_dict:
			tokens_no_duplicate_newlines = list()
			
			tokens = fgd_tokens_dict[filepath]
			num_tokens = len(tokens)
			token_index = 0
			while token_index < num_tokens:
				t = tokens[token_index]
				if t == NEWLINE_TOKEN:
					while token_index + 1 < num_tokens and tokens[token_index + 1] == NEWLINE_TOKEN:
						token_index += 1
				tokens_no_duplicate_newlines.append(t)
				token_index += 1
				
			fgd_tokens_dict[filepath] = tokens_no_duplicate_newlines
			
		#debug
		if True:
			for filepath in fgd_tokens_dict:
				tokens = fgd_tokens_dict[filepath]
				DPRINT("tokens no duplicate newlines({}): {}".format(filepath, tokens))
			
	#pre-pass to remove '+' operators from token list
	for filepath in fgd_tokens_dict:
		tokens_no_concatenate_op = list()
		
		tokens = fgd_tokens_dict[filepath]
		num_tokens = len(tokens)
		token_index = 0
		while token_index < num_tokens:
			t = tokens[token_index].lower()
			if t == "+":
				concat_index = token_index
				assert concat_index != 0, "error: first token is '+'"
				assert concat_index != num_tokens-1, "error: last token is '+'"
				assert tokens[concat_index+1] != "+", "error: 2 '+' tokens in succession"
				
				if not INCLUDE_NEWLINES:
					#find min/max range of successive tokens
					# TEXT + TEXT + ... + TEXT
					min_merge_index = concat_index - 1 #-1 for the leftmost text token
					max_merge_index = concat_index + 1 #+1 for the rightmost text token
					
					cursor = concat_index + 2
					while cursor < num_tokens and tokens[cursor] == "+":
						max_merge_index = cursor
						cursor += 2
					
					#if max_merge_index != concat_index + 1, then the body of the above while loop
					#executed and max_merge_index points at '+' instead of text. 
					#Add 1 so it points at the last text token.
					if max_merge_index != concat_index + 1:
						max_merge_index + 1
				else:
					#find the min index of tokens associated with this "+"
					min_merge_index = concat_index - 1
					while min_merge_index > 0:
						min_token = tokens[min_merge_index]
						if min_token == NEWLINE_TOKEN:
							min_merge_index -= 1
						elif min_token == "+":
							min_merge_index -= 1
						elif min_token.startswith(INQUOTE_TOKEN):
							prev_index = min_merge_index - 1
							if prev_index < 0:
								#no more tokens, so we found min_merge_index
								break
								
							prev_token = tokens[prev_index]
							if prev_token == NEWLINE_TOKEN:
								min_merge_index = prev_index
								continue
							elif prev_token == "+":
								min_merge_index = prev_index
								continue
							elif prev_token.startswith(INQUOTE_TOKEN):
								#there are 2 tokens in succession that start with INQUOTE_TOKEN with no NEWLINE_TOKEN or "+" in between
								break
							else:
								#concatenation operator only associates with INQUOTE_TOKEN(s), newlines and "+",
								#so we found min_merge_index if prev_token is none of these
								break
						else:
							#concatenation operator only associates with INQUOTE_TOKEN(s), newlines and "+",
							#so we found min_merge_index if min_token is none of these
							
							#in this branch min_merge_index points at a token that is not "\n", "+", or a INQUOTE_TOKEN,
							#so add 1 so that it points at the last token that is "\n", "+", or a INQUOTE_TOKEN
							min_merge_index += 1
							break
							
					#find the max index of tokens associated with this "+"
					max_merge_index = concat_index + 1
					while max_merge_index < num_tokens:
						max_token = tokens[max_merge_index]
						if max_token == NEWLINE_TOKEN:
							max_merge_index += 1
						elif max_token == "+":
							max_merge_index += 1
						elif max_token.startswith(INQUOTE_TOKEN):
							next_index = max_merge_index + 1
							if next_index >= num_tokens:
								#no more tokens, so we found max_merge_index
								break
								
							next_token = tokens[next_index]
							if next_token == NEWLINE_TOKEN:
								max_merge_index = next_index
								continue
							elif next_token == "+":
								max_merge_index = next_index
								continue
							elif next_token.startswith(INQUOTE_TOKEN):
								#there are 2 tokens in succession that start with INQUOTE_TOKEN with no NEWLINE_TOKEN or "+" in between
								break
							else:
								#concatenation operator only associates with INQUOTE_TOKEN(s), newlines and "+",
								#so we found max_merge_index if prev_token is none of these
								break
						else:
							#concatenation operator only associates with INQUOTE_TOKEN(s), newlines and "+",
							#so we found max_merge_index if max_token is none of these
							
							#in this branch max_merge_index points at a token that is not "\n", "+", or a INQUOTE_TOKEN,
							#so subtract 1 so that it points at the last token that is "\n", "+", or a INQUOTE_TOKEN
							max_merge_index -= 1
							break
					
					
					#keep a single newline if there are newlines in [min_merge_index, max_merge_index]
					contains_newline = False
					for i in range(min_merge_index, max_merge_index + 1, 1):
						if tokens[i] == NEWLINE_TOKEN:
							contains_newline = True
							break
						
				#merge tokens from min_merge_index to max_merge_index
				merged_text_id = ""
				merged_text_inquote = ""
				for i in range(min_merge_index, max_merge_index + 1, 1):
					if tokens[i] != "+" and tokens[i] != NEWLINE_TOKEN:
						inquote_token = tokens[i]
						assert inquote_token.startswith(INQUOTE_TOKEN), "token {} does not start with {}".format(i, INQUOTE_TOKEN)
						merged_text_id += inquote_token
						merged_text_inquote += " " + inquote_text_dict[inquote_token]
				merged_text_inquote = merged_text_inquote[1:] #remove 1st char, which is a " "
				
				assert merged_text_id not in inquote_text_dict, "inquote_text_dict contains {}".format(merged_text_id)
				inquote_text_dict[merged_text_id] = merged_text_inquote
				#DPRINT("added merged_text_id '{}': {}".format(merged_text_id, merged_text_inquote))
				
				tokens_no_concatenate_op.append(merged_text_id)
				
				if INCLUDE_NEWLINES and contains_newline:
					tokens_no_concatenate_op.append(NEWLINE_TOKEN)
				
				token_index = max_merge_index + 1
			else:
				tokens_no_concatenate_op.append(tokens[token_index])
				token_index += 1
		fgd_tokens_dict[filepath] = tokens_no_concatenate_op
		
	#main entity parsing pass
	IGNORED_TOKENS = set([NEWLINE_TOKEN])
	#get_token returns the offset that is [offset] tokens from [base_index], excluding tokens in ignored_tokens
	def get_offset_excluding_tokens(tokens, base_index, offset, ignored_tokens = IGNORED_TOKENS):
		num_tokens = len(tokens)
		actual_offset = 0
		
		if offset < 0:
			while offset < 0:
				if base_index + actual_offset < 0:
					return None
				if tokens[base_index + actual_offset - 1] not in ignored_tokens:
					offset += 1
				actual_offset -= 1
		elif offset > 0:
			while offset > 0:
				if base_index + actual_offset >= num_tokens:
					return None
				if tokens[base_index + actual_offset + 1] not in ignored_tokens:
					offset -= 1
				actual_offset += 1
				
		return actual_offset
		
	#get_token returns the token that is [offset] tokens from [base_index], excluding tokens in ignored_tokens
	def get_token(tokens, base_index, offset, ignored_tokens = IGNORED_TOKENS):
		actual_offset = get_offset_excluding_tokens(tokens, base_index, offset, ignored_tokens)
		if actual_offset != None:
			return tokens[base_index + actual_offset]
		else:
			return None
	
	def debug_print_tokens(tokens, base_index, radius = 3):
		min_index = base_index - radius
		max_index = base_index + 1
		min_index = max(0, min_index)
		max_index = min(len(tokens)-1, max_index)
		
		for i in range(min_index, max_index+1):
			DPRINT("tokens[{}]: {}".format(i, tokens[i]))
	
	entity_dict = dict()
	for filepath in fgd_tokens_dict:
		tokens = fgd_tokens_dict[filepath]
		num_tokens = len(tokens)
		token_index = 0
		while token_index < num_tokens:
			t = tokens[token_index].lower()
			
			if t in TOKEN_CLASS_DEFINITIONS:
				#find token indices of start, '=', first '[' and last ']' which closes the entity definition
				first_index = token_index
				
				#'=' denotes the end of the entity component list, and is followed by the entity name
				equal_index = token_index
				while equal_index < num_tokens and tokens[equal_index] != '=':
					equal_index += 1
				assert equal_index < num_tokens, "error, last token is '='"
				
				#first '[', which begins the list of entity properties
				first_bracket_index = token_index
				while first_bracket_index < num_tokens and tokens[first_bracket_index] != '[':
					first_bracket_index += 1
				assert equal_index < num_tokens, "error, last token is '['"
				
				#last ']', which ends the list of entity properties and closes the definition
				last_bracket_index = first_bracket_index + 1
				bracket_depth = 1
				while last_bracket_index < num_tokens:
					if tokens[last_bracket_index] == '[': bracket_depth += 1
					if tokens[last_bracket_index] == ']': bracket_depth -= 1
					if bracket_depth == 0:
						break
					last_bracket_index += 1
				assert last_bracket_index < num_tokens, "error, could not find closing bracket token is ']'"
				
				#Collect the tokens for this entity definition only.
				#Additionally, dereference the quotes for the main processing step;
				#a non-dereferenced copy is retained to resolve ambiguity in processing 'choices'.
				entdef_tokens = list()
				entdef_tokens_no_dereference = list()
				for i in range(first_index, last_bracket_index+1):
					entdef_tokens_no_dereference.append(tokens[i])
					if not tokens[i].startswith(INQUOTE_TOKEN):
						entdef_tokens.append(tokens[i])
					else:
						entdef_tokens.append(inquote_text_dict[tokens[i]])
				
				DPRINT("entdef({} tokens): {}".format(len(entdef_tokens), entdef_tokens))
				
				#convert global indices, which reference tokens[],
				#into local indices that reference entdef_tokens[]
				global_last_bracket_index = last_bracket_index #store to increment the outer while loop
			
				last_bracket_index -= first_index
				first_bracket_index -= first_index
				equal_index -= first_index
				first_index = 0
				assert last_bracket_index+1 == len(entdef_tokens), "last_bracket_index+1 is {}, but len(entdef_tokens) is {}".format(last_bracket_index+1, len(entdef_tokens))
					
				e_tokens = entdef_tokens
				e_tokens_no_dereference = entdef_tokens_no_dereference
				
				#
				classtype = get_token(e_tokens, first_index, 0)
				classname = get_token(e_tokens, equal_index, 1).lower()
				description = get_token(e_tokens, equal_index, 3) if get_token(e_tokens, equal_index, 2) == ":" else ""
				
				entity = Entity()
				entity.classtype = classtype
				entity.classname = classname
				entity.description = description
				
				#get the list of components
				#DPRINT("register equal_index, first_index: {}, {} class {}".format(equal_index, first_index, classname))
				component_list_of_lists = None
				if equal_index - first_index > 1:
					first_component = first_index + 1
					last_component = equal_index - 1
					
					component_list_of_lists = list()
					
					#base(a, b, c) is parsed into the list [base, a, b, c]
					component_list = list()
					for i in range(first_component, last_component+1):
						t = e_tokens[i]
						if t == "(" or t == "," or t == NEWLINE_TOKEN:
							pass
						elif t == ")":
							component_list_of_lists.append(component_list)
							component_list = list()
						else:
							component_list.append(t)
						#DPRINT("t: {}".format(t))
						
					#case where all tokens in range [first_index, equal_index] are newlines
					if len(component_list_of_lists) == 0:
						component_list_of_lists = None
				
				if component_list_of_lists != None:
					for component_list in component_list_of_lists:
						DPRINT("component_list: {}".format(component_list))
						entity.component_list_of_lists.append( copy.deepcopy(component_list) )
						
				#get the entity properties
				#check if there are any tokens between the first '[' and last ']'
				#if so, then there are entity properties to parse
				if last_bracket_index - first_bracket_index > 2:
					first_prop = first_bracket_index + get_offset_excluding_tokens(e_tokens, first_bracket_index, 1)
					last_prop = last_bracket_index + get_offset_excluding_tokens(e_tokens, last_bracket_index, -1)
					assert first_prop != None, "first_prop is None: {}".format(entdef_tokens)
					assert last_prop != None, "last_prop is None: {}".format(entdef_tokens)
					#DPRINT("firstlast bracket: {}, {}".format(first_bracket_index, last_bracket_index))
					#DPRINT("firstlast prop: {}, {}".format(first_prop, last_prop))
					
					prop_index = first_prop
					while prop_index <= last_prop:
						t = e_tokens[prop_index].lower()
						#DPRINT("prop_index: {}, t = {}".format(prop_index, t))
						if t in TOKEN_IO_DEFINITIONS:
							#format is:
							#io name(argument_type) : description
							#'io' 'name' '(' 'argument_type' ')' ':' 'description'
							in_or_out = get_token(e_tokens, prop_index, 0)
							name = get_token(e_tokens, prop_index, 1)
							assert get_token(e_tokens, prop_index, 2) == "(", "index 2 (from prop_index {}) is '{}' not '(' {}: ".format(prop_index, get_token(e_tokens, prop_index, 2), entdef_tokens)
							argument_type = get_token(e_tokens, prop_index, 3).lower()
							assert get_token(e_tokens, prop_index, 4) == ")", "index 4 (from prop_index {}) is '{}' not ')' {}: ".format(prop_index, get_token(e_tokens, prop_index, 4), entdef_tokens)
							
							if get_token(e_tokens, prop_index, 5) == ":":
								description = get_token(e_tokens, prop_index, 6)
								offset = 7
							else:
								description = None
								offset = 5
							
							io_prop = EInputOutput()
							io_prop.name = name
							io_prop.in_or_out = in_or_out
							io_prop.argument_type = argument_type
							io_prop.description = description
							
							if name in entity.input_output_dict:
								DPRINT("warning: entity {} contains multiple io {}".format(classname, name))
							entity.input_output_dict[name] = io_prop
							
							DPRINT("register io {} to class {}".format(io_prop, classname))
							actual_offset = get_offset_excluding_tokens(e_tokens, prop_index, offset)
							assert actual_offset != None
							
							prop_index += actual_offset
						elif t in TOKEN_ENTITY_PROP_TYPE:
							#some property names are same as type name, such as
							#origin(origin) : "" : : ""
							#to handle such cases, check for parenthesis
							prev_token = get_token(e_tokens, prop_index, -1)
							next_token = get_token(e_tokens, prop_index, 1)
							any_is_none = prev_token == None or next_token == None
							if any_is_none or not (prev_token == '(' and next_token == ')'):
								prop_index += 1
								continue
								
							#if t is in TOKEN_ENTITY_PROP_TYPE then prop_index points to 'type', which is
							#at the 3nd token(with index 2); subtract 2 so it points to the beginning
							prop_index += get_offset_excluding_tokens(e_tokens, prop_index, -2)
						
							name = get_token(e_tokens, prop_index, 0)
							assert get_token(e_tokens, prop_index, 1) == "(", "index 1 (from prop_index {}) is '{}' not '(': {}".format(prop_index, get_token(e_tokens, prop_index, 1), entdef_tokens)
							type = get_token(e_tokens, prop_index, 2).lower()
							assert get_token(e_tokens, prop_index, 3) == ")", "index 3 (from prop_index {}) is '{}' not ')': {}".format(prop_index, get_token(e_tokens, prop_index, 3), entdef_tokens)
							
							CHOICE_FLAG_NONPROP_TOKENS = [":", NEWLINE_TOKEN]
							
							#format is:
							#name(type) : short_description : default : long_description
							#'name' '(' 'type' ')' ':' 'short_description' ':' 'default' ':' 'long_description'
							
							#Count the number of ':' tokens before newline token, there can be 0 to 3. 
							colon_indices = list()
							next_newline_index = prop_index
							while next_newline_index < len(e_tokens) and e_tokens[next_newline_index] != NEWLINE_TOKEN:
								if e_tokens[next_newline_index] == ":":
									colon_indices.append(next_newline_index)
								next_newline_index += 1
						
							num_colons = len(colon_indices)
							default_value = None
							short_description = None
							long_description = None
									
							default_value_token_index = None
									
							if num_colons > 0:
								colon0_index = colon_indices[0]
								if e_tokens[colon0_index+1] not in CHOICE_FLAG_NONPROP_TOKENS:
									short_description = e_tokens[colon0_index+1]
							if num_colons > 1:
								colon1_index = colon_indices[1]
								if e_tokens[colon1_index+1] not in CHOICE_FLAG_NONPROP_TOKENS:
									default_value_token_index = colon1_index+1
									default_value = e_tokens[default_value_token_index]
							if num_colons > 2:
								colon2_index = colon_indices[2]
								if e_tokens[colon2_index+2] not in CHOICE_FLAG_NONPROP_TOKENS:
									long_description = e_tokens[colon2_index+2]
							
							if type != "choices" and type != "flags":
								next_prop_index = next_newline_index + 1
							else:
								nearest_equal_index = prop_index
								while nearest_equal_index < len(e_tokens) and e_tokens[nearest_equal_index] != "=":
									nearest_equal_index += 1
								assert e_tokens[nearest_equal_index] == "=", "choices/flags prop '{}' does not have a '=' ".format(name)
								
								nearest_open = nearest_equal_index
								while nearest_open < len(e_tokens) and e_tokens[nearest_open] != "[":
									nearest_open += 1
								assert e_tokens[nearest_open] == "[", "choices/flags prop '{}' does not have a '[' ".format(name)
								
								nearest_close = nearest_equal_index
								while nearest_close < len(e_tokens) and e_tokens[nearest_close] != "]":
									nearest_close += 1
								assert e_tokens[nearest_close] == "]", "choices/flags prop '{}' does not have a ']' ".format(name)
								
								#if the next token after "[", excluding newlines is not "]" then there are choices/flags
								tokens_in_brackets = get_token(e_tokens, nearest_open, 1) != "]"
								if tokens_in_brackets:
									#flags/choices extends the basic prop format with '= []'
									if type == "choices":
										#format of 'choices' is:
										#name(type) : short_description : default : long_description = 
										#[
										#	value : description
										#	value : description
										#	...
										#	value : description
										#]
										choices = list()
										
										choice_index = nearest_open + get_offset_excluding_tokens(e_tokens, nearest_open, 1)
										while choice_index < nearest_close:
											next_newline = choice_index
											while next_newline < len(e_tokens) and e_tokens[next_newline] != NEWLINE_TOKEN:
												next_newline += 1
											
											colon_indices_choice = list()
											for i in range(choice_index, next_newline):
												if e_tokens[i] == ":":
													colon_indices_choice.append(i)
											
											choice = EPropertyChoice()
											choice.value = e_tokens[choice_index]
											assert e_tokens[choice_index] not in ["[", "]"] + CHOICE_FLAG_NONPROP_TOKENS, "e_tokens[choice_index] (index {}): {}".format(choice_index, e_tokens[choice_index])
											
											num_colons = len(colon_indices_choice)
											if num_colons > 0:
												colon0_token = get_token(e_tokens, colon_indices_choice[0], 1)
												if colon0_token not in CHOICE_FLAG_NONPROP_TOKENS:
													choice.description = colon0_token
												
											DPRINT("choice: {} {}".format(choice.value, choice.description))
											choices.append(choice)
											
											choice_index = next_newline + get_offset_excluding_tokens(e_tokens, next_newline, 1)
											
										#update default_value for this [choice]  -- the issue is that [default]
										#can be ambiguous since it can refer to a [value] or [description] or can be an index:
										#	name(choices) : short_description : "0" : long_description = 
										#	[
										#		"0" : description
										#		value : "0"
										#	]
										if default_value != None:
											def default_value_to_choice_index(default_value, choices_name, choices):
												num_matches = 0
												num_choices = len(choices)
												
												default_choice_index = None
												for choice_index in range(num_choices):
													c = choices[choice_index]
													is_default_choice = default_value == c.value
													is_default_description = default_value == c.description
													if c.value == c.description:
														if is_default_choice or is_default_description:
															num_matches += 1
															default_choice_index = choice_index
													else:
														if is_default_choice:
															num_matches += 1
															default_choice_index = choice_index
														if is_default_description:
															num_matches += 1
															default_choice_index = choice_index
												assert num_matches <= 1, "ambiguous default ({}) for choices named {} ({})".format(default_value, choices_name, choices)
												return default_choice_index
												
											assert default_value_token_index != None
											defvalue_token_dereferenced = e_tokens[default_value_token_index]
											defvalue_token_not_dereferenced = e_tokens_no_dereference[default_value_token_index]
											if defvalue_token_not_dereferenced.startswith(INQUOTE_TOKEN):
												#the default value is in quotes, and is not an index,
												#find the index and convert it to int so it is not ambiguous
												default_choice_index = default_value_to_choice_index(default_value, name, choices)
												assert default_choice_index != None, "could not find default_choice_index for default value [{}] and choices named, {}({})".format(default_value, name, choices)
												default_value = default_choice_index
											else:
												#default_value is not in quotes, it might be an index; 
												default_choice_index = default_value_to_choice_index(default_value, name, choices)
												if default_choice_index == None:
													#default_value does not match any choices, so it is an index
													default_value = int(default_value)
													assert default_value < len(choices), "default value out of bounds [{}] for choices named {}({})".format(default_value, name, choices)
												else:
													#default value matches either a 'value' or 'description', 
													#assume that the default refers to this choice
													#this branch is taken in cases such as:
													#
													#	name(choices) : short_description : 0 : long_description = 
													#	[
													#		2 : "a"
													#		"b" : 0
													#	]
													#in this case default_choice_index == 1, which refers to the choice with "b"
													default_value = default_choice_index
												
									elif type == "flags":
										#format of 'flags' is:
										#name(type) : short_description : default : long_description = 
										#[
										#	bit : description : default
										#	bit : description : default
										#	...
										#	bit : description : default
										#]
										flags = dict()
										
										flag_index = nearest_open + get_offset_excluding_tokens(e_tokens, nearest_open, 1)
										while flag_index < nearest_close:
											next_newline = flag_index
											while next_newline < len(e_tokens) and e_tokens[next_newline] != NEWLINE_TOKEN:
												next_newline += 1
										
											colon_indices_flag = list()
											for i in range(flag_index, next_newline):
												if e_tokens[i] == ":":
													colon_indices_flag.append(i)
												
											flag = EPropertyFlag()
											flag.default = 0 #default is off if there is no default specified	
											flag.bit = e_tokens[flag_index]
											assert e_tokens[flag_index] not in ["[", "]"] + CHOICE_FLAG_NONPROP_TOKENS, "e_tokens[flag_index] (index {}): {}".format(flag_index, e_tokens[flag_index])
											
											num_colons = len(colon_indices_flag)
											if num_colons > 0:
												colon0_token = get_token(e_tokens, colon_indices_flag[0], 1)
												if colon0_token not in CHOICE_FLAG_NONPROP_TOKENS:
													flag.description = colon0_token
											if num_colons > 1:
												colon1_token = get_token(e_tokens, colon_indices_flag[1], 1)
												if colon1_token not in CHOICE_FLAG_NONPROP_TOKENS:
													flag.default = colon1_token
											
											DPRINT("flag: {} {} {}".format(flag.bit, flag.description, flag.default))
											flags[flag.bit] = flag
											
											flag_index = next_newline + get_offset_excluding_tokens(e_tokens, next_newline, 1)
											
								next_prop_index = nearest_close + 1
							
							ent_prop = EProperty()
							ent_prop.name = name
							ent_prop.type = type
							if default_value != None: ent_prop.default_value = default_value
							if short_description != None: ent_prop.short_description = short_description
							if long_description != None: ent_prop.long_description = long_description
							if type == "choices":
								ent_prop.choices_list = choices
							elif type == "flags":
								ent_prop.flags_dict = flags
							
							if name in entity.property_dict:
								DPRINT("warning: entity {} contains multiple properties {}".format(classname, name))
							entity.property_dict[name] = ent_prop
							DPRINT("register prop({}) {} to class {}".format(ent_prop.type, ent_prop, classname))
							
							prop_index = next_prop_index
						else:
							prop_index += 1
				#
				if classname not in entity_dict:
					entity_dict[classname] = entity
				else:
					DPRINT("warning: entity {} is defined multiple times".format(name))
					
				#debug print
				DPRINT("class: {}({}) of type {} with components {}".format(classname, description, classtype, component_list_of_lists))
				DPRINT("io {}".format(entity.input_output_dict))
				DPRINT("props {}".format(entity.property_dict))
				
				#
				token_index = global_last_bracket_index + 1
			else:
				token_index += 1
	
	#post-parsing pass to find props inherited from parent entities
	for classname in entity_dict:
		ent = entity_dict[classname]
		
		parent_entities = None
		for component_list in ent.component_list_of_lists:
			if component_list[0] == "base":
				parent_entities = component_list[1:]
				break
		
		#all keys in entity_dict should be lowercase, set parents lowercase as well
		if parent_entities != None:
			for i in range(len(parent_entities)):
				parent_entities[i] = parent_entities[i].lower()
		
		entity_dict[classname].parent_list = parent_entities
		DPRINT("ent: {} immediate parents: {}".format(classname, parent_entities))
	
	#Not sure how .fgd handles inheritance:
	#can entity A be a child of entity B, while B is a child of A?
	#Current approach is to merge all props/io and assume that they are the same.
	for classname in entity_dict:
		classes_to_inherit_from = list()
		classes_to_inherit_from.append(classname)
		
		classes_to_check = set()
		classes_to_check.add(classname)
		previously_seen_classes = set()
		previously_seen_classes.add(classname)
		while len(classes_to_check) != 0:
			check_class = classes_to_check.pop()
			if entity_dict[check_class].parent_list == None:
				continue
			
			for parentclass in entity_dict[check_class].parent_list:
				if parentclass not in previously_seen_classes:
					classes_to_check.add(parentclass)
					previously_seen_classes.add(parentclass)
					
					classes_to_inherit_from.append(parentclass)
		
		entity_dict[classname].class_hierarchy = classes_to_inherit_from
		DPRINT("ent: {} class_hierarchy: {}".format(classname, classes_to_inherit_from))
		
		for c in classes_to_inherit_from:
			for io_name in entity_dict[c].input_output_dict:
				io = entity_dict[c].input_output_dict[io_name]
				if io_name not in entity_dict[classname].all_input_output_dict:
					entity_dict[classname].all_input_output_dict[io_name] = io
				else:
					io2 = entity_dict[classname].all_input_output_dict[io_name]
					if io.argument_type != io2.argument_type:
						DPRINT("warning: multiple io ('{}') with different type ('{}', '{}') in entity ('{}')".format(io_name, io2.argument_type, io.argument_type, classname))
					
			for prop_name in entity_dict[c].property_dict:
				prop = entity_dict[c].property_dict[prop_name]
				if prop_name not in entity_dict[classname].all_property_dict:
					entity_dict[classname].all_property_dict[prop_name] = prop
				else:
					prop2 = entity_dict[classname].all_property_dict[prop_name]
					if prop.type != prop2.type:
						DPRINT("warning: multiple prop ('{}') with different type ('{}', '{}') in entity ('{}')".format(prop_name, prop2.type, prop.type, classname))
		
		#Inherit flags from parents
		#since we check property_dict and not all_property_dict we do not need to move this to a separate loop
		SPAWNFLAGS = "spawnflags"
		if SPAWNFLAGS in entity_dict[classname].all_property_dict:
			flags_prop = entity_dict[classname].all_property_dict[SPAWNFLAGS]
		
			for c in classes_to_inherit_from:
				if c == classname:
					continue
					
				if SPAWNFLAGS in entity_dict[c].property_dict:
					inherit_flags = entity_dict[c].property_dict[SPAWNFLAGS].flags_dict
					for key in inherit_flags:
						if key not in flags_prop.flags_dict:
							flags_prop.flags_dict[key] = inherit_flags[key]
			
			flags_prop.default_value = flags_prop.get_flags_default_value() 
			entity_dict[classname].all_property_dict[SPAWNFLAGS] = flags_prop
		#DPRINT("ent: {} all io: {}".format(classname, entity_dict[classname].all_input_output_dict))				
		DPRINT("ent: {} all prop: {}".format(classname, entity_dict[classname].all_property_dict))				
			
	return entity_dict
	
def parse_fgds_in_path(search_path):
	fgd_files = find_all_files_in(search_path)
	entity_dict = parse_source1_fgd(fgd_files)
	return entity_dict
	
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("parse_source1_fgd.py [search_path]")
		exit()
	
	search_path = sys.argv[1]
	
	entity_dict = parse_fgds_in_path(search_path)
	
