#!/usr/bin/env python3
#
# parse_unreal1_uc.py
# search_path is in format C:\dir

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
	
		
def find_all_files_in(search_path, extension = ".uc"):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			#filepath = dirpath + filename
			if filepath.endswith(extension):
				filename = filename.replace(os.sep, '/')
				filepath = filepath.replace(os.sep, '/')
				paths.append((filename, filepath))
				DPRINT("{0}: {1}".format(extension, filepath))
	return paths
	
VARIABLE_DECLARATIONS = ["var"]

#builtin variable types only
VAR_NUMBER_TYPES = ["bool", "byte", "int", "float"] #default is 0
VAR_STRING_TYPES = ["string", "name"] #default is "" ?
VAR_REFERENCE_TYPES = ["object", "texture", "mesh", "model", "sound", "music", "iterator"] #default is None? todo: check default for 'iterator'

BUILTIN_VAR_TYPES = VAR_NUMBER_TYPES + VAR_STRING_TYPES + VAR_REFERENCE_TYPES

VARIABLE_TYPES = []
VARIABLE_TYPES += ["void"]
VARIABLE_TYPES += VAR_NUMBER_TYPES
VARIABLE_TYPES += VAR_STRING_TYPES
VARIABLE_TYPES += VAR_REFERENCE_TYPES
#VARIABLE_TYPES += ["color", "pointer", "vector", "plane", "rotator"] #these are defined as structs in .uc

VARIABLE_SPECIFIERS = []
VARIABLE_SPECIFIERS += ["const", "editconst", "input", "transient", "native"]
VARIABLE_SPECIFIERS += ["private", "protected", "travel", "skip", "export", "local", "config"]
VARIABLE_SPECIFIERS += ["localized", "globalconfig"]

PARSER_VARTYPE_BUILTIN = "builtin"
PARSER_VARTYPE_ENUM = "enum"
PARSER_VARTYPE_STRUCT = "struct"
PARSER_VARTYPE_CLASS = "class"
PARSER_VARTYPE_CLASSBRACKETED = "class_bracketed" #reference to a class such as 'class<actor>'
PARSER_VARIABLE_TYPES = [PARSER_VARTYPE_BUILTIN, PARSER_VARTYPE_ENUM, PARSER_VARTYPE_STRUCT, PARSER_VARTYPE_CLASS, PARSER_VARTYPE_CLASSBRACKETED]

def get_builtin_var_default(type):
	if type in VAR_NUMBER_TYPES: 
		if type == "bool": return "false"
		if type == "float": return "{:6f}".format(0) #0.000000
		return "0"
	if type in VAR_STRING_TYPES: return ""
	if type in VAR_REFERENCE_TYPES: return "none"
	
	assert False, CURFUNC(CF()) + ": {} is not a builtin type".format(type) 
	return None

class UnrealStruct:
	def __init__(self):
		self.name = None
		self.variables = dict()
		
class UnrealEnum:
	def __init__(self):
		self.name = None
		self.enum_to_int = dict() #self.enum_to_int[enum_choice] = int
		self.int_to_enum = list() #
		
class UnrealVar:
	def __init__(self):
		self.name = None
		self.type = None
		self.length = None			#if this var is an array, the length of the array
		
		self.is_editor_visible = False	#vars with parenthesis (category) are displayed in the editor
		self.editor_category = None		#string containing the text in-between parenthesis
		self.is_editconst = False		#editconst vars are displayed in the editor, but not editable
		
	def is_array(self):
		return self.length != None

#a single preprocessor line
#class UnrealPreprocessorLine:
#	def __init__(self):
#		self.type = None			#the first token, such as '#exec'
#		self.statements = list()	#all following tokens in the preprocessor line without '='
#		self.equals = dict()		#all following tokens in the preprocessor line with '='

class UnrealMesh3d: #mesh_a.3d, mesh_d.3d
	def __init__(self):
		self.unrealpath = None
		self.name = None
		self.origin = (0, 0, 0)
		self.rotation = (0, 0, 0) 	#Preprocessor specifies rotation as bytes, so 255 = 360 degrees.
		self.rotation_degrees = (0, 0, 0)
		self.scale = (1, 1, 1)

class UnrealClass:
	def __init__(self):
		self.name = None		#Name of the class, which is unique across packages
		self.parent = None
		#self.is_pawn = False
		self.inheritance_chain = None
		self.mesh3d = None
		
		self.package = None
		
		#list of lists, the first list corresponds to preprocessor lines and the second to tokens
		self.preprocessor_list_of_lists = list()
		
		self.vars_dict = dict()
		self.struct_dict = dict()
		self.enum_dict = dict()
		
		#defaultproperties is a series of lines in the format 'key=value'
		#defaultproperties_dict[key] = value, where 
		#'key' is a string containing everything to the left of each '=' and 
		#'value' is a string containing everything to the right of each '='
		self.defaultproperties_dict = dict()
		
		self.all_vars_dict = dict()
		
		self.all_editor_vars_dict = dict()

		
		
	def is_a(self, unreal_classname):
		if unreal_classname == self.name:
			return True
	
		return unreal_classname in self.inheritance_chain

	#processes tokens in the format:
	#	'#exec CATEGORY COMMAND var=VALUE var=VALUE ... var=VALUE'
	#and returns a dict containing var_dict[var] = VALUE
	def get_preprocessor_exec(self, category, command):
		for preprocessor_tokens in self.preprocessor_list_of_lists:
			valid0 = preprocessor_tokens[0] == "#exec"
			valid1 = preprocessor_tokens[1] == category
			valid2 = preprocessor_tokens[2] == command
			if valid0 and valid1 and valid2:
				preprocessor_dict = dict()
				for token in preprocessor_tokens[3:]:
					if not '=' in token:
						DPRINT("{}: warning:  #exec {} {} preprocessor_tokens[3:] contains token without '=' for class {}: {}".format(CCF(self, CF()), category, command, self.name, preprocessor_tokens))
					else:
						left, sep, right = token.partition('=')
						var = left
						value = right
						preprocessor_dict[var] = value
				return preprocessor_dict
		return None
		
	def load_staticmesh_data(self):
		mesh_unreal_name = None
		mesh_import_datafile = None
		mesh_import_anivfile = None
		mesh_import = self.get_preprocessor_exec("mesh", "import")
		if mesh_import != None:
			if "mesh" in mesh_import: mesh_unreal_name = mesh_import["mesh"]
			
			#The _d.3d and _a.3d names exported by UnrealEd 2.1 do not match 'datafile' and 'anivfile' in the .uc file.
			#Instead, the .3d files are named after the 'unreal name' given by the 'mesh' keyword.
			#This means that the paths in 'datafile' and 'anivfile' can be ignored.
			if "datafile" in mesh_import: 
				mesh_import_datafile = mesh_import["datafile"] #datatile 'mesh_d.3d', contains the base mesh
				mesh_import_datafile = mesh_import_datafile.replace('\\', '/')
			if "anivfile" in mesh_import: 
				mesh_import_anivfile = mesh_import["anivfile"] #datatile 'mesh_a.3d', contains an animated vertex mesh
				mesh_import_anivfile = mesh_import_anivfile.replace('\\', '/')
		
		#In UE1,
		#roll rotates about the x-axis,
		#pitch rotates about the y-axis, and
		#yaw rotates about the z-axis
		mesh_origin_name = None
		origin_x, origin_y, origin_z, origin_x_roll, origin_y_pitch, origin_z_yaw  = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
		mesh_origin = self.get_preprocessor_exec("mesh", "origin")
		if mesh_origin != None:
			if "mesh" in mesh_origin: mesh_origin_name = mesh_origin["mesh"]
			if "x" in mesh_origin: origin_x = float(mesh_origin["x"])
			if "y" in mesh_origin: origin_y = float(mesh_origin["y"])
			if "z" in mesh_origin: origin_z = float(mesh_origin["z"])
			if "roll" in mesh_origin: origin_x_roll = float(mesh_origin["roll"])
			if "pitch" in mesh_origin: origin_y_pitch = float(mesh_origin["pitch"])
			if "yaw" in mesh_origin: origin_z_yaw = float(mesh_origin["yaw"])
			
		meshmap_scale_name = None
		scale_x, scale_y, scale_z = 1.0, 1.0, 1.0
		meshmap_scale = self.get_preprocessor_exec("meshmap", "scale")
		if meshmap_scale != None:
			if "meshmap" in meshmap_scale: mesh_origin_name = meshmap_scale["meshmap"]
			if "x" in meshmap_scale: scale_x = float(meshmap_scale["x"])
			if "y" in meshmap_scale: scale_y = float(meshmap_scale["y"])
			if "z" in meshmap_scale: scale_z = float(meshmap_scale["z"])
			
		mesh_names_set = set()
		if mesh_unreal_name != None: mesh_names_set.add(mesh_unreal_name)
		if mesh_origin_name != None: mesh_names_set.add(mesh_origin_name)
		if meshmap_scale_name != None: mesh_names_set.add(meshmap_scale_name)
		assert len(mesh_names_set) <= 1, "{}: has more than 1 mesh name: {}".format(CCF(self, CF()), mesh_names_set)
		
		if mesh_unreal_name != None:
			mesh_name = mesh_unreal_name
			
			TO_DEGREES = 180.0 / 128.0
			mesh_unrealpath = "{}.{}".format(self.get_unreal_path(), mesh_name);
			origin = (origin_x, origin_y, origin_z)
			rotation = (origin_x_roll, origin_y_pitch, origin_z_yaw)
			rotation_degrees = (origin_x_roll * TO_DEGREES, origin_y_pitch * TO_DEGREES, origin_z_yaw * TO_DEGREES)
			scale = (scale_x, scale_y, scale_z)
			
			mesh3d = UnrealMesh3d()
			mesh3d.unrealpath = mesh_unrealpath
			mesh3d.name = mesh_name
			mesh3d.origin = origin
			mesh3d.rotation = rotation
			mesh3d.rotation_degrees = rotation_degrees
			mesh3d.scale = scale
			
			self.mesh3d = mesh3d
			return mesh3d
		else:
			self.mesh3d = None
			return None
			
	def get_unreal_path(self):
		assert self.package != None, CCF(self, CF()) + ": self.package == None"
		assert self.name != None, CCF(self, CF()) + ": self.name == None"
		return self.package + "." + self.name
		
class UnrealScriptDefinitions:
	def __init__(self):
		self.class_dict = dict()
		
		self.all_struct_dict = dict()
		self.all_enum_dict = dict()
		
		self.multiple_def_structs = set()
		self.multiple_def_enums = set()
	
	def get_parser_type(self, var_type):
		var_type = var_type.lower()
	
		is_enum = var_type in self.all_enum_dict
		is_struct = var_type in self.all_struct_dict
		is_class = var_type in self.class_dict
		is_class_bracketed = "class" in var_type and "<" in var_type and ">" in var_type
		
		num_definitions = int(is_struct) + int(is_enum) + int(is_class) + int(is_class_bracketed)
		assert num_definitions <= 1, CCF(self, CF()) + ": var_type '{}' has multiple definitions(enum[{}], struct[{}], class[{}], class_bracketed[{}])".format(var_type, is_enum, is_struct, is_class, is_class_bracketed)
		
		if var_type in BUILTIN_VAR_TYPES:
			return PARSER_VARTYPE_BUILTIN
		elif is_enum:
			return PARSER_VARTYPE_ENUM
		elif is_struct:
			return PARSER_VARTYPE_STRUCT
		elif is_class:
			return PARSER_VARTYPE_CLASS
		elif is_class_bracketed:
			return PARSER_VARTYPE_CLASSBRACKETED
			
		assert False, CCF(self, CF()) + ": unsupported var_type '{}'".format(var_type)
		return None
		
	#returns the default value of a variable as a string for the editor or (.t3d) exporter,
	#with all values set to 0 or equivalent
	#format is:
	#	(x=VALUE,y=VALUE,z=VALUE,w=(wx=VALUE,wy=VALUE,wz=VALUE))
	def get_empty_default(self, var_type):
		def default_for_nonstruct(var_type, parser_type):
			if parser_type == PARSER_VARTYPE_BUILTIN:
				return get_builtin_var_default(var_type) #vars are initialized to 0, "", or None
			elif parser_type == PARSER_VARTYPE_ENUM:
				uenum = self.all_enum_dict[var_type]
				return uenum.int_to_enum[0]
			elif parser_type == PARSER_VARTYPE_CLASS:
				return "none"
			elif parser_type == PARSER_VARTYPE_CLASSBRACKETED:
				return "none"
			
			return None
			
		parser_type = self.get_parser_type(var_type)
		if parser_type == PARSER_VARTYPE_STRUCT:
			def expand_struct(ustruct, all_struct_dict, all_enum_dict):
				def structvar_to_default_text(var_name, var_type, parser_type, all_struct_dict, all_enum_dict):
					if parser_type == PARSER_VARTYPE_STRUCT:
						return "{}={}".format(var_name, expand_struct(all_struct_dict[var_type]))
					else:
						return "{}={}".format(var_name, default_for_nonstruct(var_type, parser_type))
						
				num_vars = len(ustruct.variables)
				if num_vars == 0: return "()"
			
				text = "("
				if num_vars == 1:
					ustruct_var = ustruct.variables[0]
					ustruct_var_parser_type = self.get_parser_type(ustruct_var.type)
					text += structvar_to_default_text(ustruct_var.name, ustruct_var.type, ustruct_var_parser_type, all_struct_dict, all_enum_dict)
				else:
					for struct_var_name in ustruct.variables:
						ustruct_var = ustruct.variables[struct_var_name]
						ustruct_var_parser_type = self.get_parser_type(ustruct_var.type)
						text += structvar_to_default_text(ustruct_var.name, ustruct_var.type, ustruct_var_parser_type, all_struct_dict, all_enum_dict) + ","
					text = text[:-1] #remove last ","
				text += ")"
				return text
				
			ustruct = self.all_struct_dict[var_type]
			return expand_struct(ustruct, self.all_struct_dict, self.all_enum_dict)
		
		return default_for_nonstruct(var_type, parser_type)
		
PREPROCESSOR_KEYWORDS = []
#PREPROCESSOR_KEYWORDS += ["#if", "#elif", "#else", "#endif"]
#PREPROCESSOR_KEYWORDS += ["#ifdef", "#ifndef", "#define", "#undef"]
#PREPROCESSOR_KEYWORDS += ["#include"]
PREPROCESSOR_KEYWORDS += ["#exec"]

###
FLOW_CONTROL = ["if", "else", "for", "foreach", "do", "until", "while", "switch", "case", "default", "continue", "goto", "break", "return"]

CONSTANTS = ["True", "False"]

CLASS_DECLARATIONS = ["class", "extends", "expands", "struct", "enum", "replication", "unreliable", "defaultproperties"]

CLASS_SPECIFIERS = []
CLASS_SPECIFIERS += ["abstract", "native", "noexport"]

FUNCTION_DECLARATIONS = ["function", "event", "delegate", "operator", "preoperator", "postoperator", "state"]

FUNCTION_SPECIFIERS = []
FUNCTION_SPECIFIERS += ["static", "singular", "native", "latent", "final", "iterator", "simulated", "exec"]


FUNCTION_ARGUMENT_SPECIFIERS = ["out", "optional"]

KEYWORDS = []
KEYWORDS += FLOW_CONTROL
KEYWORDS += CONSTANTS
KEYWORDS += CLASS_DECLARATIONS
KEYWORDS += CLASS_SPECIFIERS
KEYWORDS += VARIABLE_DECLARATIONS
KEYWORDS += VARIABLE_TYPES
KEYWORDS += VARIABLE_SPECIFIERS
KEYWORDS += FUNCTION_DECLARATIONS
KEYWORDS += FUNCTION_ARGUMENT_SPECIFIERS
###

OPERATORS = []

#from C++, in precedence order (note C++ precedence differs from unrealscript)
#OPERATORS += ["++", "--", "."]
#OPERATORS += ["!", "~"]
#OPERATORS += ["*", "/", "%"]
#OPERATORS += ["+", "-"]
#OPERATORS += ["<<", ">>"]
#OPERATORS += ["<", ">", "<=", ">="]
#OPERATORS += ["==", "!="]
#OPERATORS += ["&"]
#OPERATORS += ["^"]
#OPERATORS += ["|"]
#OPERATORS += ["&&"]
#OPERATORS += ["||"]
#OPERATORS += ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="]
#OPERATORS += [","]
#
#from unrealscript, not sure about precedence
#OPERATORS += ["**"] #float
#OPERATORS += ["$", "@", "$=", "@="] #string

ENCLOSE_OPERATORS = ["(", ")", "[", "]", "{", "}"]
OPERATORS += ENCLOSE_OPERATORS

#parser constants
INQUOTE_TOKEN = "%%q_"
INBRACKET_TOKEN = "%%b_"
NEWLINE_TOKEN = "%%n"

class UCFile:
	def __init__(self):
		self.classname = None
		self.path = None
		self.statements_dict = dict()
		self.inquote_text_dict = dict()
		self.bracket_text_dict = dict()
		self.preprocessor_lines = dict()
		
def parse_unreal_uc(uc_paths):
	unreal_defs = UnrealScriptDefinitions()
	
	#first stage - load .uc files and:
	# - extract text in between quotes \" and \'
	# - extract text in between brackets {}, only the first and last brackets ('depth' == 1)
	# - breakup the text into a series of semicolon separated statements
	uc_files_dict = dict()
	for (name, path) in uc_paths:
		DPRINT("")
		DPRINT(name)
		
		classname = name.replace(".uc", "").lower() #UnrealScript is not case-sensitive

		#By default open() uses locale.getpreferredencoding();
		#Houdini 18.5 on Windows 10 locale.getpreferredencoding() returns 'cp65001', but
		#a standalone Python3 install returns 'cp1252'. Using cp65001 causes the decoding to
		#fail, so explicitly set the codec here.
		CODEC = "cp1252" #windows-1252 'Western Europe'
		
		text = ""
		with open(path, 'rt', encoding=CODEC) as f:
			for line in f:
				text += line
			
		def remove_comments_newlines_and_tabs(text):
			#remove text after // comments; note that single line comments precede multiline comments
			#keepends == True, so we keep the newline chars(/n, /r, ...)
			text_without_comments = ""
			preprocessor_lines = list()
			
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
						
				#remove preprocessor lines
				left_whitespace_removed = comment_removed_line.lstrip(string.whitespace)
				if not left_whitespace_removed.startswith("#"):
					text_without_comments += comment_removed_line
				else:
					preprocessor_lines.append(left_whitespace_removed)
					
			#remove text in between /* */ comments
			REMOVE_MULTILINE_COMMENTS = True
			if REMOVE_MULTILINE_COMMENTS:
				multiline_comment_start_index = text_without_comments.find("/*")
				while multiline_comment_start_index != -1:
					left1, sep1, right1 = text_without_comments.partition("/*")
					left2, sep2, right2 = right1.partition("*/")
					text_without_comments = left1 + right2
					multiline_comment_start_index = text_without_comments.find("/*")
			
			#Current approach removes all newlines and will not work otherwise.
			# #if false all newlines are replaced with " " in next step				
			# INCLUDE_NEWLINE_TOKENS = False
			# if INCLUDE_NEWLINE_TOKENS:
				# #Make sure that the text does not contain NEWLINE_TOKEN before adding it
				# assert text_without_comments.find(NEWLINE_TOKEN) == -1, "error: .fgd contains NEWLINE_TOKEN {}".format(NEWLINE_TOKEN)
				
				# #To make debug print more dense/easier to read we want to remove newlines.
				# #However, newlines might be used for something so replace it with a special token.
				# for char in string.whitespace:
					# text_without_comments = text_without_comments.replace("\n", " {} ".format(NEWLINE_TOKEN))
				
			#replace tabs, newline, return, etc. with " "
			#important: this can only happen after parsing '//' type comments
			for char in string.whitespace:
				text_without_comments = text_without_comments.replace(char, " ")
				
			#	
			return (text_without_comments, preprocessor_lines)
		text, preprocessor_lines = remove_comments_newlines_and_tabs(text)

		#Extract text in between quotes "" or ''
		#Assume that the quotes must be matched; that is \" must end with \" and likewise with \'.
		#Under this assumption, literals such as "string' or 'string" are invalid.
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
			assert not in_quote, "error: missing closing quote for quote_char({}) in {}".format(quote_char, debug_path)
			
			#debug print
			if True:
				DPRINT("removedquotes: " +  text_without_quotes)
				for id in inquote_text_dict:
					DPRINT("{}: {}".format(id, inquote_text_dict[id]))
			
			return (text_without_quotes, inquote_text_dict)
		text, inquote_text_dict = extract_string_literals(text, path)
		
		def pad_operators(text):
			#todo:  include all operators, such as =, <=, +=, ...		
			#pad '{', '}', ... with spaces so that split() will not mix them with text
			PAD_CHARS = "{}[]();,?"
			for char in PAD_CHARS:
				text = text.replace(char, " {} ".format(char))
			return text
		text = pad_operators(text)
		
		#replace sequences of spaces with a single space
		def compact_spaces(text):
			SPACES_4 = "    "
			SPACES_2 = "  "
			while text.find(SPACES_4) != -1:
				text = text.replace(SPACES_4, " ")
			while text.find(SPACES_2) != -1:
				text = text.replace(SPACES_2, " ")
			return text
		text = compact_spaces(text)
		
		#Since we only want to extract configurable properties for classes/entities,
		#it is not necessary to parse text in brackets, except for enum and struct types.
		def extract_bracketed_text(text):
			bracket_text_dict = dict()
			
			text_without_bracket = ""
			
			in_bracket_text = ""
			bracket_depth = 0
			prev_bracket_depth = None
			
			for char in text:
				if char == "{":
					bracket_depth += 1
				if char == "}":
					bracket_depth -= 1
					
				is_exiting_bracket = (bracket_depth == 0 and prev_bracket_depth == 1)
				if is_exiting_bracket:
					dict_id_str = INBRACKET_TOKEN + str( len(bracket_text_dict) )
					bracket_text_dict[dict_id_str] = in_bracket_text
					
					#1: Pad the text as split() uses " " to separate tokens
					#2: Add a semicolon since {} closes the statement
					text_without_bracket += " {} {} ".format(dict_id_str, ";")
					
					in_bracket_text = ""
				elif char != "{" and char != "}":
					if bracket_depth >= 1:
						in_bracket_text += char
					else:
						text_without_bracket += char
				prev_bracket_depth = bracket_depth
				
			return (text_without_bracket, bracket_text_dict)
		text, bracket_text_dict = extract_bracketed_text(text)
		
		#debug print
		if True:
			DPRINT("removedbrackets: " +  text)
			for id in bracket_text_dict:
				DPRINT("{}: {}".format(id, bracket_text_dict[id]))
					
		#DPRINT("pretoken: " +  text)
		#tokens = text.split(sep = " ", maxsplit = -1)
		#DPRINT("tokens: " + str(tokens))
		statements = text.split(sep = ";", maxsplit = -1)
		for s in statements:
			DPRINT("s: " + str(s))
		
		uc_file = UCFile()
		uc_file.classname = classname
		uc_file.path = path
		uc_file.statements = statements
		uc_file.inquote_text_dict = inquote_text_dict
		uc_file.bracket_text_dict = bracket_text_dict
		uc_file.preprocessor_lines = preprocessor_lines
		uc_files_dict[path] = uc_file
		
	#stage 2 - iterate through the .uc files to get all struct, enum, vars
	struct_dict = dict()
	enum_dict = dict()
	for path in uc_files_dict:
		uc = uc_files_dict[path]
		DPRINT("")
		DPRINT("pass 2: {}".format(path))
		uclass = UnrealClass()
		uclass.name = uc.classname
		
		#sets uclass.package from the .uc filesystem path
		#assume that all .uc files are stored in the directory format:
		#	.../PACKAGE_NAME/Classes/CLASS.uc
		EXTRACT_CLASS_PACKAGE = True
		if EXTRACT_CLASS_PACKAGE:
			split_filepath = path.split('/', maxsplit = -1)
			assert len(split_filepath) >= 3, "Failed to get class package, must be in format PACKAGE/Classes/CLASS.uc: {}".format(split_filepath)
			assert split_filepath[-2].lower() == "classes", "Failed to get class package, must be in format PACKAGE/Classes/CLASS.uc: {}".format(split_filepath)
			uclass.package = split_filepath[-3].lower()
			DPRINT("upath: {}".format(uclass.package + "." + uclass.name))
			
		EXTRACT_PREPROCESSOR = True
		if EXTRACT_PREPROCESSOR:
			preprocessor_statements = list()
			for line in uc.preprocessor_lines:
				#assume that single-quote is not supported in UnrealScript preprocessor
				assert '\'' not in line, "\' in class {} (path {})".format(uc.classname, path)
				in_quote = False

				preprocessor_tokens = list()
				token = ""
				for c in line:
					if c in string.whitespace and not in_quote:
						if token != "": #multiple ' ' in succession will append empty strings without this check
							preprocessor_tokens.append(token.lower()) #assume that the preprocessor is not case-sensitive
							token = ""
					elif c == '\"':
						in_quote = not in_quote
						token += c
					else:
						token += c
				
				DPRINT("preprocessor_tokens: {}".format(preprocessor_tokens))
				preprocessor_statements.append(preprocessor_tokens)
				uclass.preprocessor_list_of_lists = preprocessor_statements	
				
		found_class_statement = False
		num_statements = len(uc.statements)
		for statement_index in range(num_statements):
			statement = uc.statements[statement_index]
			
			#Since we add ';' after '}' and split statements by ';',
			#we need to look at the next statement when parsing struct/enum to handle.
			#the case where a list of variables of that struct/enum type is declared.
			next_statement = uc.statements[statement_index+1] if statement_index+1 < num_statements else None
			
			#pad < > so that variable type statements in the form 'class<classname>' are broken into 4 tokens 
			#this will break operatiors such as '<=' or '>=' but since we only want to extract variables it does not matter.
			def pad_operators2(text):
				PAD_CHARS = "<>"
				for char in PAD_CHARS:
					text = text.replace(char, " {} ".format(char))
				return text
			statement = pad_operators2(statement)
			
			#compact spaces
			SPACES_2 = "  "
			while statement.find(SPACES_2) != -1:
				statement = statement.replace(SPACES_2, " ")
				
				
			#UnrealScript is not case-sensitive, so set all tokens to lowercase
			tokens = statement.lower().split(sep = " ", maxsplit = -1)
			DPRINT("statement[{}]: {}".format(statement_index, statement))
			DPRINT("tokens: {}".format(tokens))
			while "" in tokens:
				tokens.remove("")
			
			if next_statement != None:
				while next_statement.find(SPACES_2) != -1:
					next_statement = next_statement.replace(SPACES_2, " ")
				#UnrealScript is not case-sensitive, so set all tokens to lowercase
				next_tokens = next_statement.lower().split(sep = " ", maxsplit = -1)
				while "" in next_tokens:
					next_tokens.remove("")
			else:
				next_tokens = None
			
			#Each class begins with either statement:	
			#	class CLASS_NAME extends PARENT_CLASS CLASS_SPECIFIERS;
			#	class CLASS_NAME expands PARENT_CLASS CLASS_SPECIFIERS
			def extract_class_and_parent_name(tokens):
				classname = None
				parentname = None
				if "class" in tokens:
					classtoken = tokens.index("class")
					classname = tokens[classtoken+1]
					if "extends" in tokens:
						extendstoken = tokens.index("extends")
						parentname = tokens[extendstoken+1]
					if "expands" in tokens:
						expandstoken = tokens.index("expands")
						parentname = tokens[expandstoken+1]
			
				return classname, parentname
				
			#general format for var/struct/enum statement is:
			#	var(EDITOR_CATEGORY) VARIABLE_SPECIFIERS VARIABLE_TYPE VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#if there is 'enum' or 'struct' the format replaces VARIABLE_TYPE:
			#	var(EDITOR_CATEGORY) VARIABLE_SPECIFIERS [enum|struct] [ENUM_NAME|STRUCT_NAME]
			#	{
			#		[ENUM_VALUE, | var VAR_TYPE VAR_NAME;]
			#		[ENUM_VALUE, | var VAR_TYPE VAR_NAME;]
			#		...
			#		[ENUM_VALUE, | var VAR_TYPE VAR_NAME;]
			#	} VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#
			
			#separates into variables a list of tokens in format: VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#returns a list of UnrealVar
			def extract_variable_names_and_lengths(tokens, var_type, is_editor_visible = False, editor_category = None, is_editconst = False):
			
				var_names_and_lengths = list()
			
				num_commas = tokens.count(",")
				num_variables = num_commas + 1
				if num_variables == 1:
					var_name = tokens[0].lower()
				
					is_array = "[" in tokens
					array_length = int(tokens[tokens.index("[")+1]) if is_array else 1
					
					var_names_and_lengths.append((var_name, array_length))
					DPRINT("var: {}{} of type {}".format(var_name, "[" + str(array_length) + "]" if is_array else "", var_type))
				else:
					lowest_comma = tokens.index(",")
					var_name = tokens[0].lower()
				
					is_array = "[" in tokens and tokens.index("[") < lowest_comma
					array_length = int(tokens[tokens.index("[")+1]) if is_array else 1
					
					var_names_and_lengths.append((var_name, array_length))
					DPRINT("multivar: {}{} of type {}".format(var_name, "[" + str(array_length) + "]" if is_array else "", var_type))
					
					remaining_tokens = tokens
					while "," in remaining_tokens:
						lowest_comma = tokens.index(",")
						remaining_tokens = remaining_tokens[lowest_comma+1:]
						current_var_end = remaining_tokens.index(",") if "," in remaining_tokens else len(remaining_tokens)
						current_var_tokens = remaining_tokens[0 : current_var_end]
						if len(current_var_tokens) > 0:
							var_name = current_var_tokens[0].lower()
							is_array = "[" in current_var_tokens
							array_length = int(current_var_tokens[current_var_tokens.index("[")+1]) if is_array else 1
								
							var_names_and_lengths.append((var_name, array_length))
							DPRINT("multivar: {}{} of type {}".format(var_name, "[" + str(array_length) + "]" if is_array else "", var_type))
				
				unreal_vars = list()
				for namelength in var_names_and_lengths:
					name, array_length = namelength
					
					uvar = UnrealVar()
					uvar.name = name.lower()
					uvar.type = var_type.lower()
					uvar.length = array_length
					uvar.is_editor_visible = is_editor_visible
					uvar.editor_category = editor_category
					uvar.is_editconst = is_editconst
					
					unreal_vars.append(uvar)
				return unreal_vars
		
			#expected input is a series of tokens representing a 'var' statement in format:
			#var(EDITOR_CATEGORY) VARIABLE_SPECIFIERS VARIABLE_TYPE VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#returns a list of UnrealVar() in the struct
			def parse_var_statement_in_struct(tokens):
			
				has_parenthesis = "(" in tokens and ")" in tokens
				is_editor_visible = has_parenthesis
				if has_parenthesis:
					open_parenthesis = tokens.index("(")
					close_parenthesis = tokens.index(")")
					has_category = close_parenthesis - open_parenthesis > 1
					category = tokens[open_parenthesis+1] if has_category else None
				else:
					category = None
					
				is_editconst = "editconst" in tokens
				has_specifiers = False
				last_specifier_index = -1
				for i in range(len(tokens)):
					if tokens[i] in VARIABLE_SPECIFIERS:
						last_specifier_index = max(last_specifier_index, i)
						has_specifiers = True
			
				if has_specifiers:
					var_type_index = last_specifier_index + 1
				elif has_parenthesis:
					var_type_index = close_parenthesis + 1
				else:
					var_type_index = tokens.index("var") + 1
				var_type = tokens[var_type_index]
				first_variable_name_index = var_type_index+1
				
				#handle var statements in form 
				#'class<CLASS_NAME>', 'array<CLASS_NAME>', or 'array<class<CLASS_NAME>>'
				#note that 'class' is by itself a valid variable type so we need to check for '<' and '>'
				#the minimum statement is ['class_or_array', '<', 'CLASS_NAME', '>'], so we add 4 to check length
				if (var_type == "class" or var_type == "array") and len(tokens[var_type_index:var_type_index+4]) > 0 and tokens[var_type_index+1] == "<":
					depth = 0
					for t in tokens[var_type_index+1:]:	#var_type_index+0 is 'class' or 'array' and var_type_index+1 is '<'
						var_type += t
						first_variable_name_index += 1
						if t == "<": depth += 1
						if t == ">": depth -= 1
						if depth == 0:
							break
					assert depth == 0, "class or array var statement missing closing bracket '>': {}(var_type_index={})".format(tokens, var_type_index)
				
				unreal_vars = extract_variable_names_and_lengths(tokens[first_variable_name_index:], var_type, is_editor_visible, category, is_editconst)
				
				return unreal_vars
			
			#expected input is a series of tokens representing a 'enum' or 'var+enum' statement in format:
			#	var(EDITOR_CATEGORY) VARIABLE_SPECIFIERS enum ENUM_NAME
			#	{
			#		ENUM_VALUE,
			#		ENUM_VALUE,
			#		...
			#		ENUM_VALUE,
			#	} VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#where 'tokens' contains everything up to the '}' token, and
			#'next_tokens' contains the optional variable list afterwards
			def parse_enum_statement(tokens, next_tokens, bracket_text_dict):
				enum_index = tokens.index("enum")
				enum_name = tokens[enum_index+1].lower()
				
				bracket_token = None
				for t in tokens:
					if t.startswith(INBRACKET_TOKEN):
						bracket_token = t
						break
				if bracket_token != None:
					enum_defs_text = bracket_text_dict[bracket_token]
					enum_defs = enum_defs_text.split(sep = " ", maxsplit = -1)
					while "," in enum_defs:
						enum_defs.remove(",")
					while "" in enum_defs:
						enum_defs.remove("")
					DPRINT("enum {} with options {}".format(enum_name, enum_defs))
				
				enum_uvars = list()
				if next_tokens != None:
					no_keywords_in_next_tokens = True
					for t in next_tokens:
						if t in KEYWORDS:
							no_keywords_in_next_tokens = False
							break
							
					if no_keywords_in_next_tokens and len(next_tokens) > 0:
						var_type = enum_name
						enum_uvars += extract_variable_names_and_lengths(next_tokens, var_type)
				
				uenum = UnrealEnum()
				uenum.name = enum_name
				for enum_def in enum_defs:
					last_index = len(uenum.enum_to_int)
					uenum.enum_to_int[enum_def] = last_index # todo: check if specific values can be assigned to enums as in C/C++
					uenum.int_to_enum.append(enum_def)
				return (uenum, enum_uvars)
				
			#expected input is a series of tokens representing a 'struct' or 'var+struct' statement in format:
			#	var(EDITOR_CATEGORY) VARIABLE_SPECIFIERS struct STRUCT_NAME
			#	{
			#		var VAR_TYPE VAR_NAME;
			#		var VAR_TYPE VAR_NAME;
			#		...
			#		var VAR_TYPE VAR_NAME;
			#	} VAR_NAME[], VAR_NAME[], ..., VAR_NAME[];
			#where 'tokens' contains everything up to the '}' token, and
			#'next_tokens' contains the optional variable list afterwards
			#
			#Declaring a enum inside the struct(in between the outermost brackets) is not implemented.
			def parse_struct_statement(tokens, next_tokens, bracket_text_dict):
				struct_index = tokens.index("struct")
				struct_name = tokens[struct_index+1].lower()
				
				#parse the variables in the struct
				bracket_token = None
				for t in tokens:
					if t.startswith(INBRACKET_TOKEN):
						bracket_token = t
						break
						
				in_struct_uvars = list()
				if bracket_token != None:
					struct_text = bracket_text_dict[bracket_token]
					statements = struct_text.split(sep = ";", maxsplit = -1)
					DPRINT("struct {} with statements {}".format(struct_name, statements))
					for s in statements:
						var_tokens = s.split(sep = " ", maxsplit = -1)
						while "" in var_tokens:
							var_tokens.remove("")
						if len(var_tokens) == 0:
							continue
						
						if "enum" in var_tokens:
							DPRINT("struct parse ignoring nested enum, not implemented: {}".format(var_tokens))
						else:
							in_struct_uvars	+= parse_var_statement_in_struct(var_tokens)
				
				#parse the variable names that are of this struct type
				struct_uvars = list()
				if next_tokens != None:
					no_keywords_in_next_tokens = True
					for t in next_tokens:
						if t in KEYWORDS:
							no_keywords_in_next_tokens = False
							break
									
					if no_keywords_in_next_tokens and len(next_tokens) > 0:
						#DPRINT("struct def has variables: {}".format(struct_name))
						var_type = struct_name
						struct_uvars += extract_variable_names_and_lengths(next_tokens, var_type)
						
				ustruct = UnrealStruct()
				ustruct.name = struct_name
				for uvar in in_struct_uvars:
					ustruct.variables[uvar.name] = uvar
				return (ustruct, struct_uvars)
			
			#
			if not found_class_statement:
				classname, parentname = extract_class_and_parent_name(tokens)
				assert uc.classname == classname, "class file name({}) is not same as classname({})".format(uc.classname, classname)
				found_class_statement = True
				uclass.parent = parentname
		
			has_struct = "struct" in tokens
			has_enum = "enum" in tokens
			has_enum = "enum" in tokens
			if "var" in tokens:
				has_parenthesis = "(" in tokens and ")" in tokens
				is_editor_visible = has_parenthesis
				if has_parenthesis:
					open_parenthesis = tokens.index("(")
					close_parenthesis = tokens.index(")")
					has_category = close_parenthesis - open_parenthesis > 1
					category = tokens[open_parenthesis+1] if has_category else None
				else:
					category = None
					
				is_editconst = "editconst" in tokens
				has_specifiers = False
				last_specifier_index = -1
				for i in range(len(tokens)):
					if tokens[i] in VARIABLE_SPECIFIERS:
						last_specifier_index = max(last_specifier_index, i)
						has_specifiers = True
			
				if not has_struct and not has_enum:
					if has_specifiers:
						var_type_index = last_specifier_index + 1
					elif has_parenthesis:
						var_type_index = close_parenthesis + 1
					else:
						var_type_index = tokens.index("var") + 1
					var_type = tokens[var_type_index]
					first_variable_name_index = var_type_index+1
					
					#handle var statements in form 
					#'class<CLASS_NAME>', 'array<CLASS_NAME>', or 'array<class<CLASS_NAME>>'
					#note that 'class' is by itself a valid variable type so we need to check for '<' and '>'
					#the minimum statement is ['class_or_array', '<', 'CLASS_NAME', '>'], so we add 4 to check length
					if (var_type == "class" or var_type == "array") and len(tokens[var_type_index:var_type_index+4]) > 0 and tokens[var_type_index+1] == "<":
						depth = 0
						for t in tokens[var_type_index+1:]:	#var_type_index+0 is 'class' or 'array' and var_type_index+1 is '<'
							var_type += t
							first_variable_name_index += 1
							if t == "<": depth += 1
							if t == ">": depth -= 1
							if depth == 0:
								break
						assert depth == 0, "class or array var statement missing closing bracket '>': {}(var_type_index={})".format(tokens, var_type_index)
						
					unreal_vars = extract_variable_names_and_lengths(tokens[first_variable_name_index:], var_type, is_editor_visible, category, is_editconst)
					for uvar in unreal_vars:
						uclass.vars_dict[uvar.name] = uvar
				else:
					if has_struct:
						struct_start_index = tokens.index("struct")
						struct_tokens = tokens[struct_start_index:]
						(ustruct, struct_uvars) = parse_struct_statement(struct_tokens, next_tokens, uc.bracket_text_dict)
						
						uclass.struct_dict[ustruct.name] = ustruct
						for uvar in struct_uvars:
							uclass.vars_dict[uvar.name] = uvar
					elif has_enum:
						enum_start_index = tokens.index("enum")
						enum_tokens = tokens[enum_start_index:]
						(uenum, enum_uvars) = parse_enum_statement(enum_tokens, next_tokens, uc.bracket_text_dict)
						
						uclass.enum_dict[uenum.name] = uenum
						for uvar in enum_uvars:
							uclass.vars_dict[uvar.name] = uvar
					else:
						assert False, "var statement has both struct and enum: {}".format(tokens)
			elif has_struct:
				struct_start_index = tokens.index("struct")
				struct_tokens = tokens[struct_start_index:]
				(ustruct, struct_uvars) = parse_struct_statement(struct_tokens, next_tokens, uc.bracket_text_dict)
						
				uclass.struct_dict[ustruct.name] = ustruct
				for uvar in struct_uvars:
					uclass.vars_dict[uvar.name] = uvar
						
			elif has_enum:
				enum_start_index = tokens.index("enum")
				enum_tokens = tokens[enum_start_index:]
				(uenum, enum_uvars) = parse_enum_statement(enum_tokens, next_tokens, uc.bracket_text_dict)
				
				uclass.enum_dict[uenum.name] = uenum
				for uvar in enum_uvars:
					uclass.vars_dict[uvar.name] = uvar
					
			elif "defaultproperties" in tokens:
				#defaultproperties format is:
				#	defaultproperties
				#	{
				#		VAR_NAME=VALUE
				#		VAR_NAME=VALUE
				#		...
				#		VAR_NAME=VALUE
				#	}
				#
				#The straightforward way to parse this is to use = and \n as delimiters, but
				#since we remove newlines in an earlier step it is not feasible. 
				#
				#Additionally, the parsing is complicated by the possibility of parenthesis 
				#in both VAR_NAME and VALUE, and the possibility of '=' token in VALUE.
				#
				#If VAR_NAME refers to an array type, then it might have parenthesis:
				#	{
				#		VAR_NAME(0) = VALUE 
				#		VAR_NAME(1) = VALUE 
				#		...
				#		VAR_NAME(N) = VALUE 
				#	}
				#If VALUE is a vector, then it will have parenthesis and '=': 
				# 		VAR_NAME = (X=0.f, Y=0.f, Z=0.f)
				#
				#Considering these factors, the approach is:
				#	1) find the indices of each '=' that is not in parenthesis as a starting point
				#	2) to get VAR_NAME, search to the left for the first token not in parenthesis
				#	3) to get VALUE, search to the right for the next '=', then,
				#		3a) if there is a '=', search left for the first token not in parenthesis
				#		3b) if there is no '=', for the end of the array
				bracket_token = None
				for t in tokens:
					if t.startswith(INBRACKET_TOKEN):
						bracket_token = t
						break
				if bracket_token != None:
					defprop_text = uc.bracket_text_dict[bracket_token]
					
					def pad_defaultprop(text):
						PAD_CHARS = "{}[]();,="
						for char in PAD_CHARS:
							text = text.replace(char, " {} ".format(char))
						return text
					defprop_text = pad_defaultprop(defprop_text)
					defprop_text = compact_spaces(defprop_text)
					defprop_tokens = defprop_text.split(sep = " ", maxsplit = -1)
					while "" in defprop_tokens:
							defprop_tokens.remove("")
					DPRINT("defprop_tokens: {}".format(defprop_tokens))
					
					#collect the indices of each '=' that is not between parenthesis '(' or ')'
					equals_indicies = list()
					
					parenthesis_depth = 0
					for i in range(len(defprop_tokens)):
						t = defprop_tokens[i]
						if t == "(":
							parenthesis_depth += 1
						if t == ")":
							parenthesis_depth -= 1
							
						if t == "=" and parenthesis_depth == 0:
							equals_indicies.append(i)
					
					#starting from the '=' token, search left for the first token that is not in parenthesis
					def find_defprop_name_start(defprop_tokens, equal_token_index):
						parenthesis_depth = 0
						index = equal_token_index - 1
						while 0 < index:
							t = defprop_tokens[index]
							if t == "(":
								parenthesis_depth += 1
							elif t == ")":
								parenthesis_depth -= 1
							elif parenthesis_depth == 0: #and t != "(" and t != ")":
								return index
							index -= 1
						return 0
						
					#returns the index of the next '=', or the last index of defprop_tokens
					def find_next_equal_token_index(defprop_tokens, equal_token_index):
						index = equal_token_index + 1
						parenthesis_depth = 0
						while index < len(defprop_tokens):
							t = defprop_tokens[index]
							if t == "(":
								parenthesis_depth += 1
							elif t == ")":
								parenthesis_depth -= 1
								
							if parenthesis_depth == 0 and t == '=':
								return index
							
							index += 1
						assert len(defprop_tokens) > 0, "len(defprop_tokens) == 0: {}".format(defprop_tokens)
						return len(defprop_tokens) - 1
						
					def compact_tokens(tokens, inquote_dict):
						merged = ""
						for t in tokens:
							if not t.startswith(INQUOTE_TOKEN):
								merged += t.lower()
							else:
								merged += "'{}'".format(inquote_dict[t])
						return merged
						
					for equals_index in equals_indicies:
						start = find_defprop_name_start(defprop_tokens, equals_index)
						end = find_next_equal_token_index(defprop_tokens, equals_index)
						if end != len(defprop_tokens) - 1:
							#found '=', so the end is the next token to the left not in parenthesis
							end = find_defprop_name_start(defprop_tokens, end)
						else:
							#did not find '=', so the end is the end of the list
							end = len(defprop_tokens)
							
						defprop_name = compact_tokens(defprop_tokens[start:equals_index], uc.inquote_text_dict)
						defprop_value = compact_tokens(defprop_tokens[equals_index+1:end], uc.inquote_text_dict)
						
						DPRINT("defprop: {} = {}".format(defprop_name, defprop_value))
						uclass.defaultproperties_dict[defprop_name] = defprop_value
		unreal_defs.class_dict[uc.classname] = uclass;
	
	#stage 3 - run through the class hierarchy to detect pawns, which are placeable
	uclass_dict = unreal_defs.class_dict
	for classname in uclass_dict:
	
		inheritance_chain = list()
	
		parent = uclass_dict[classname].parent
		while parent in uclass_dict:
			inheritance_chain.append(parent)
			parent = uclass_dict[parent].parent
			
		#is_pawn = "pawn" in inheritance_chain
		#uclass_dict[classname].is_pawn = is_pawn
		uclass_dict[classname].inheritance_chain = inheritance_chain
		
		DPRINT("class {} inherits {} )".format(classname, inheritance_chain))
	
	
	#copy inherited vars from parents
	for classname in uclass_dict:
		uclass_dict[classname].all_vars_dict = copy.deepcopy(uclass_dict[classname].vars_dict)
	
		parent = uclass_dict[classname].parent
		while parent in uclass_dict:
			for var in uclass_dict[parent].vars_dict:
				uclass_dict[classname].all_vars_dict[var] = uclass_dict[parent].vars_dict[var]
		
			parent = uclass_dict[parent].parent
		DPRINT("class {} has {} vars({} +inherited)".format(classname, len(uclass_dict[classname].vars_dict), len(uclass_dict[classname].all_vars_dict)))
		
	#copy editable vars to all_editor_vars_dict
	for classname in uclass_dict:
		for var in uclass_dict[classname].all_vars_dict:
			if uclass_dict[classname].all_vars_dict[var].is_editor_visible and not uclass_dict[classname].all_vars_dict[var].is_editconst:
				uclass_dict[classname].all_editor_vars_dict[var] = uclass_dict[classname].all_vars_dict[var]
		DPRINT("class {} has {} editable vars".format(classname, len(uclass_dict[classname].all_editor_vars_dict)))
	
	#copy inherited defaultproperties from parents
	for classname in uclass_dict:
		parent = uclass_dict[classname].parent
		while parent in uclass_dict:
			parent_defprops = uclass_dict[parent].defaultproperties_dict
			for defprop_name in parent_defprops:
				if defprop_name not in uclass_dict[classname].defaultproperties_dict:
					uclass_dict[classname].defaultproperties_dict[defprop_name] = parent_defprops[defprop_name]
			parent = uclass_dict[parent].parent
	
	#validate defaultproperties_dict
	for classname in uclass_dict:
		uclass = uclass_dict[classname]
		for defprop_name in uclass.defaultproperties_dict:
			if "(" in defprop_name:
				defprop_name = defprop_name[:defprop_name.index("(")]
			assert defprop_name in uclass.all_vars_dict, "class {} has defprop {}, but no var: {}".format(classname, defprop_name, uclass.all_vars_dict)
		
	#load and validate static mesh data, if the class has a .3d mesh
	for classname in uclass_dict:
		uclass_dict[classname].load_staticmesh_data()
		if uclass_dict[classname].mesh3d != None:
			mesh3d = uclass_dict[classname].mesh3d
			DPRINT("{} mesh upath, name: {}, {}".format(uclass_dict[classname].get_unreal_path(), mesh3d.unrealpath, mesh3d.name))
			DPRINT("{} mesh origin, rotation(degrees), scale: {}, {}({}), {}".format(uclass_dict[classname].get_unreal_path(), mesh3d.origin, mesh3d.rotation, mesh3d.rotation_degrees, mesh3d.scale))
			
	#generate global dict for enum and struct
	for classname in uclass_dict:
		uclass = uclass_dict[classname]
		for structname in uclass.struct_dict:
			if structname in unreal_defs.all_struct_dict: 
				DPRINT("warning: multiple definitions for struct {}".format(structname) )
				if structname not in unreal_defs.multiple_def_structs:
					 unreal_defs.multiple_def_structs.add(structname)
			unreal_defs.all_struct_dict[structname] = uclass.struct_dict[structname]
		for enumname in uclass.enum_dict:
			if enumname in unreal_defs.all_enum_dict: 
				DPRINT("warning: multiple definitions for enum {}".format(enumname) )
				if enumname not in unreal_defs.multiple_def_enums:
					 unreal_defs.multiple_def_enums.add(enumname)
			unreal_defs.all_enum_dict[enumname] = uclass.enum_dict[enumname]
			
	if True: #check for name overlaps
		for structname in unreal_defs.all_struct_dict:
			if structname in unreal_defs.all_enum_dict:
				DPRINT("warning: struct {} also defined as enum".format(structname))
		for enumname in unreal_defs.all_enum_dict:
			if enumname in unreal_defs.all_struct_dict:
				DPRINT("warning: enum {} also defined as struvt".format(enumname))
	
	return unreal_defs
	
def parse_uc_in_path(search_path):
	uc_files = find_all_files_in(search_path)
	unreal_defs = parse_unreal_uc(uc_files)
	return unreal_defs
	
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		DPRINT("parse_unreal1_uc.py [search_path]")
		exit()
	
	search_path = sys.argv[1]
	
	unreal_defs = parse_uc_in_path(search_path)
	