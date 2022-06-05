#!/usr/bin/env python3
#
# parse_idtech4_def.py
# search_path is in format C:\dir
#
# a simple parser to extract props from entitydef in .def files

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

def find_all_files_in(search_path, extension = ".def"):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			#filepath = dirpath + filename
			if filepath.endswith(extension):
				paths.append((filename, filepath))
				DPRINT("{0}: {1}".format(extension, filepath))
	return paths

class EntityProp():
	def __init__(self):
		self.key = ""
		self.value = None
		
		self.editor_tag = None
		self.editor_description = None
		
class EntityDef:
	def __init__(self):
		self.source_file_path = ""
	
		self.name = ""
		self.property_dict = dict()
		self.editor_tags_dict = dict()
		
		#list of class names of parent entities, inheritance_chain[0] is the immediate parent
		#assume no support for multiple inheritance
		self.inheritance_chain = None
		self.inherited_property_dict = dict()
		
		self.all_property_dict = dict()
		self.all_property_dict_editor = dict() #contains all properties with editor_tags assigned
		
def parse_idtech4_def(def_paths):
	#load .def files and create a series of tokens for each file
	def_tokens_dict = dict()
	for (name, filepath) in def_paths:
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
				
			#remove text in between /* */ comments
			multiline_comment_start_index = text_without_comments.find("/*")
			while multiline_comment_start_index != -1:
				left1, sep1, right1 = text_without_comments.partition("/*")
				left2, sep2, right2 = right1.partition("*/")
				text_without_comments = left1 + right2
				multiline_comment_start_index = text_without_comments.find("/*")
			
			#DPRINT("commentsremoved: " +  text_without_comments)
			
			#replace tabs, return, etc. with " "
			#important: this can only happen after parsing '//' type comments
			for char in string.whitespace:
				text_without_comments = text_without_comments.replace(char, " ")
			
			#pad '{' and '}' with spaces so that split() will not mix brackets with text
			text_without_comments = text_without_comments.replace("{", " { ")
			text_without_comments = text_without_comments.replace("}", " } ")
			
			#replace sequences of spaces with a single space
			SPACES_4 = "    "
			SPACES_2 = "  "
			while text_without_comments.find(SPACES_4) != -1:
				text_without_comments = text_without_comments.replace(SPACES_4, " ")
			while text_without_comments.find(SPACES_2) != -1:
				text_without_comments = text_without_comments.replace(SPACES_2, " ")
			
			DPRINT("pretoken: " +  text_without_comments)
			tokens = text_without_comments.split(sep = " ", maxsplit = -1)
			DPRINT("tokens: " + str(tokens))
			
			def_tokens_dict[filepath] = tokens
	
	#first pass parsing of tokens
	entitydef_dict = dict()
	for filepath in def_tokens_dict:
		tokens = def_tokens_dict[filepath]
		num_tokens = len(tokens)
		
		#
		validate_bracket_depth = 0
		for i in range(num_tokens):
			if tokens[i] == "{":
				validate_bracket_depth += 1
			if tokens[i] == "}":
				validate_bracket_depth -= 1
				
		assert validate_bracket_depth == 0, "no closing bracket for {} (bracket_depth == {})".format(filepath, validate_bracket_depth)
		
		#
		token_index = 0
		while token_index < num_tokens:
			if tokens[token_index].lower() == "entitydef":
				is_in_entitydef = True
				entity_name = tokens[token_index+1]
				open_bracket = tokens[token_index+2]
				assert open_bracket == "{", "syntax error - no opening bracket for entityDef {} in {}".format(entity_name, filepath)
				
				#find the token index of closing bracket so we know the range to search for key-value pairs
				closing_bracket_index = -1
				for i in range(token_index, num_tokens, 1):
					if tokens[i] == "}":
						closing_bracket_index = i
						break
				assert closing_bracket_index != -1, "could not find closing bracket in {}".format(filepath)
						
				if entity_name not in entitydef_dict:
					new_def = EntityDef()
					new_def.source_file_path = filepath
					new_def.name = entity_name
					DPRINT("entity: {}".format(entity_name))
					
					first_property_index = token_index + 3
					last_property_index = closing_bracket_index - 1
					
					#using split() to produce tokens in the previous step separates text between \",
					#so we need to recombine it
					recombined_token_string = tokens[first_property_index]
					for i in range(first_property_index + 1, last_property_index + 1, 1):
						recombined_token_string += " " + tokens[i]
					
					#we want to split() the string into key-value pairs using " " as a separator, but
					#do not want to split along spaces between quotes. To resolve this, temporarly replace
					#spaces in quotes with \t
					in_quote = False
					property_string = ""
					for i in range(len(recombined_token_string)):
						char = recombined_token_string[i]
						if char == "\"":
							in_quote = not in_quote
							
						if in_quote and char == " ":
							property_string += "\t"
						else:
							property_string += char
							
					key_value_pairs_with_tabs = property_string.split(sep = " ", maxsplit = -1)	
					key_value_pairs = list()
					for token in key_value_pairs_with_tabs:
						key_value_pairs.append(token.replace("\t", " "))
				
					#populate the key-value pair dict for this entity
					#lines are in the format
					#	key_or_editor value_or_description
					#	or
					#	"key_or_editor" "value_or_description"
					num_properties_x2 = len(key_value_pairs)
					assert num_properties_x2 % 2 == 0, "entityDef {} in {} has a unpaired key-value pair {}".format(entity_name, filepath, key_value_pairs)
					for i in range(0, num_properties_x2, 2):
						key_or_editor = key_value_pairs[i]
						value_or_description = key_value_pairs[i+1]
						if key_or_editor.startswith("\""): key_or_editor = key_or_editor[1:]
						if key_or_editor.endswith("\""): key_or_editor = key_or_editor[:-1]
						if value_or_description.startswith("\""): value_or_description = value_or_description[1:]
						if value_or_description.endswith("\""): value_or_description = value_or_description[:-1]
						
						key_or_editor = key_or_editor.lower()
						
						#editor_ keywords without numbers, possibly incomplete
						EDITOR_SINGLE = ['editor_alert_factor', 'editor_alert_max', 'editor_angle', 'editor_argString', 'editor_bool', 'editor_caption', 'editor_cmdName', 'editor_color', 'editor_combatnode', 'editor_combination', 'editor_displayfolder', 'editor_dur', 'editor_float', 'editor_gui', 'editor_head', 'editor_int', 'editor_light', 'editor_material', 'editor_maxs', 'editor_mins', 'editor_model', 'editor_mover', 'editor_ragdoll', 'editor_readable', 'editor_rotatable', 'editor_sentence', 'editor_setkeyvalue', 'editor_showangle', 'editor_skin', 'editor_snd', 'editor_string', 'editor_transparent', 'editor_var', 'editor_vector', 'editor_vocal_set', 'editor_waitUntilFinishedAllowed']
						#editor_ keywords with numbers (format editor_KEYWORD#), possibly incomplete,
						#example:  'editor_usage1', 'editor_usage2', ...
						EDITOR_MULTI = ['editor_argDesc', 'editor_argOptional', 'editor_argRequired', 'editor_argTitle', 'editor_argType', 'editor_copy', 'editor_usage']
							
						#Lines in this format are used to create actual key-value pairs:
						#	"key" "value"
						#	key value
						#
						#Lines beginning with 'editor_' are used to assign a description to the key,
						#and to tag it as a certain type in the editor:
						#	"editor_KEYWORD key"  "value"
						#	"editor_KEYWORD key X"  "value"		#regex: editor_([aA-zZ]|[0-9])*[ ]([aA-zZ]|[0-9]|_)*[ ]
						#and others are:
						#	"editor_KEYWORD" "value"
						#
						#The order of these lines is not specified, so we need to check the property_dict if the key already exists.
						#
						#todo: in some cases value == ? such as:
						#	"editor_mins" "?"
						#	"editor_maxs" "?"
						if key_or_editor.startswith("editor_"):
							#editor_KEYWORD case:
							#	"editor_KEYWORD key"  "value"
							#	"editor_KEYWORD key X"  "value"		#regex: editor_([aA-zZ]|[0-9])*[ ]([aA-zZ]|[0-9]|_)*[ ]
							#and others are:
							#	"editor_KEYWORD" "value"
							num_spaces = key_or_editor.count(" ")
							if num_spaces == 0: #"editor_KEYWORD" "value"
								#this case is possibly used to tag the entity and not for actual key-value pairs
								editor = key_or_editor
								new_def.editor_tags_dict[editor] = value_or_description
								DPRINT("assign entity '{}' editor_tag '{}' with value: {}".format(entity_name, editor, value_or_description))
							elif num_spaces == 1: #"editor_KEYWORD key"  "value"
								firstspace = key_or_editor.index(" ")
								key = key_or_editor[firstspace+1:]
								editor_tag = key_or_editor[:firstspace]
								editor_description = value_or_description
								if key not in new_def.property_dict:
									new_def.property_dict[key] = EntityProp()
									new_def.property_dict[key].key = key
								new_def.property_dict[key].editor_tag = editor_tag
								new_def.property_dict[key].editor_description = editor_description
							elif num_spaces == 2: #"editor_KEYWORD key X"  "value"
								#very rare case, so ignore it; ~3 of ~5600 cases of lines with editor_KEYWORD
								DPRINT("in entity {} ignoring editor_* tag({}) with value: {}".format(entity_name, key_or_editor, value_or_description))
							else:
								assert False, "entity {}  has unsupported editor_*: {} [}".format(entity_name, key_or_editor, value_or_description)
						else:
							#Key-value case:
							#	"key" "value"
							#	key value
							key = key_or_editor
							value = value_or_description
							if key not in new_def.property_dict:
								new_def.property_dict[key] = EntityProp()
								new_def.property_dict[key].key = key
							new_def.property_dict[key].value = value
						
					entitydef_dict[entity_name] = new_def
				else:
					prevdef_path = entitydef_dict[entity_name].source_file_path
					DPRINT("warning: entityDef {} defined 2+ times in {} and {}".format(entity_name, filepath, prevdef_path))
				
				token_index = closing_bracket_index + 1
			else:
				DPRINT("ignoring token: {}".format(tokens[token_index]))
				token_index += 1
				
	#second pass find parents of each class so we can copy inherited properties
	def generate_inheritance_chain(entitydef_dict):
		INHERIT = "inherit"
	
		for entity_name in entitydef_dict:
			#DPRINT("{}: {}".format(entity_name, entitydef_dict[entity_name].property_dict))
		
			parent_chain = list()
			current = entity_name
			while current in entitydef_dict and INHERIT in entitydef_dict[current].property_dict:
				parent_name = entitydef_dict[current].property_dict[INHERIT].value
				if parent_name != None:
					parent_chain.append(parent_name)
				current = parent_name
				
			entitydef_dict[entity_name].inheritance_chain = parent_chain
			DPRINT("class {} inherits: {}".format(entity_name, parent_chain))
		
		return entitydef_dict
	entitydef_dict = generate_inheritance_chain(entitydef_dict)
	
	#third pass populates EntityDef.inherited_property_dict
	def copy_inherited_props(entitydef_dict):
		#traverse the class hierarchy to copy parent props
		for entity in entitydef_dict:
			for parent in entitydef_dict[entity].inheritance_chain:
				for prop in entitydef_dict[parent].property_dict:
					inherited_prop = entitydef_dict[parent].property_dict[prop]
					
					has_prop = prop in entitydef_dict[entity].property_dict
					if not has_prop and prop not in entitydef_dict[entity].inherited_property_dict:
						entitydef_dict[entity].inherited_property_dict[prop] = inherited_prop
		
		#populate the merged property_dict
		for entity in entitydef_dict:
			entitydef_dict[entity].all_property_dict = copy.deepcopy(entitydef_dict[entity].property_dict)
			for prop in entitydef_dict[entity].inherited_property_dict:
				inherited_prop = entitydef_dict[entity].inherited_property_dict[prop]
				if prop not in entitydef_dict[entity].all_property_dict:
					entitydef_dict[entity].all_property_dict[prop] = inherited_prop
						
		return entitydef_dict
	entitydef_dict = copy_inherited_props(entitydef_dict)
	
	#populate EntityDef.all_property_dict_editor
	def copy_editor_props(entitydef_dict):
		for entity in entitydef_dict:
			for propname in entitydef_dict[entity].all_property_dict:
				prop = entitydef_dict[entity].all_property_dict[propname]
				if prop.editor_tag != None:
					entitydef_dict[entity].all_property_dict_editor[propname] = prop
		return entitydef_dict
	entitydef_dict = copy_editor_props(entitydef_dict)
	
	return entitydef_dict
	
def parse_def_in_path(search_path):
	def_files = find_all_files_in(search_path)
	entitydef_dict = parse_idtech4_def(def_files)
	return entitydef_dict
	
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		DPRINT("parse_idtech4_def.py [search_path]")
		exit()
	
	search_path = sys.argv[1]
	
	entitydef_dict = parse_def_in_path(search_path)
	
