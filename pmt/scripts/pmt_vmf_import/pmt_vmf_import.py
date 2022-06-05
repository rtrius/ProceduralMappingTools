#!/usr/bin/env python3
#	node               : 	pmt::pmt_vmf_import
#	houdini_module_name: 	pmt_vmf_import

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

EDITOR_KEYWORDS = ["versioninfo", "visgroups", "viewsettings", "editor", "cameras", "cordons", "group", "hidden"]
BSP_KEYWORDS =  ["world", "solid", "side"]
ENTITY_KEYWORDS = ["entity", "connections"]
DISPLACEMENT_MAP_KEYWORDS = ["dispinfo", "normals", "distances", "offsets", "offset_normals", "alphas", "triangle_tags"]

VMF_KEYWORDS = EDITOR_KEYWORDS + BSP_KEYWORDS + ENTITY_KEYWORDS + DISPLACEMENT_MAP_KEYWORDS

def parse_vmf(vmf_path):
	with open(vmf_path, 'rt', encoding=TEXT_CODEC) as vmf_file:
		text = ""
		for line in vmf_file:
			if line.lstrip().startswith("//"):
				left, sep, right = line.partition("//")
				text += left
			else:
				text += line
			
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
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, vmf_path)
	
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
	vmf_dict = dict()
	
	#
	num_tokens = len(tokens)
	token_index = 0
	while token_index < num_tokens:
		t = tokens[token_index]
		
		if t == "{":
			opening_index = token_index
			vmf_keyword = tokens[opening_index - 1].lower()
			
			DPRINT("vmf_keyword: {}".format(vmf_keyword))
			
			def extract_tokens_in_brackets(vmf_keyword, tokens, tokens_with_quotes, opening_index, global_bracket_depth):
				assert global_bracket_depth <= 3, "expected max bracket_depth == 3, is {} (vmf_keyword={}, tokens={})".format(global_bracket_depth, vmf_keyword, tokens) 
			
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
					
					#Assuming that there are 2 types of tokens in .vmf files:
					#	- If the token is not encapsulated by quotes, then it should be in VMF_KEYWORDS,
					#	and should be followed by a opening '{' and closing '}' brace.
					#	- If the token is in quotes, then it is a key-value pair in the format:
					#		"a" "b"
					#if t2lo in VMF_KEYWORDS:
					if not t2quote.startswith(INQUOTE_TOKEN):
						assert t2lo in VMF_KEYWORDS, "unexpected token '{}' not in VMF_KEYWORDS (token={}) (tokens={})".format(vmf_keyword, tokens)
						if t2lo not in kv_dict:
							kv_dict[t2lo] = list()
							
						(closing_index2, kv_dict2) = extract_tokens_in_brackets(t2lo, in_bracket_tokens, in_bracket_tokens_quotes, token_index2+1, global_bracket_depth+1)
						kv_dict[t2lo].append(kv_dict2)
						token_index2 = closing_index2
					else:
						t2next = in_bracket_tokens[token_index2+1]
						token_index2 += 1
						kv_dict[t2] = t2next
						
					token_index2 += 1
				
				
				return (closing_index, kv_dict)
				
			(closing_index, kv_dict) = extract_tokens_in_brackets(vmf_keyword, tokens, tokens_with_quotes, opening_index, 1)
			DPRINT("tokens: {}".format(tokens[opening_index:closing_index+1]))
			DPRINT("kv_dict: {}".format(kv_dict))
			DPRINT("")
			
			if vmf_keyword not in vmf_dict:
				vmf_dict[vmf_keyword] = list()
			vmf_dict[vmf_keyword].append(kv_dict)
			
			token_index = closing_index
			
		token_index += 1
		
	if "world" in vmf_dict:
		assert len(vmf_dict["world"]) == 1, "error: .vmf file has multiple world(s)"
		world_kv = vmf_dict["world"][0]
	
		if "solid" in world_kv:
			solids_list = world_kv["solid"]
			num_solids = len(solids_list)
			DPRINT("num_solids: {}".format(num_solids))
			for solid_kv_dict in solids_list:
				if "side" in solid_kv_dict:
					sides_list = solid_kv_dict["side"]
					num_sides = len(sides_list)
					DPRINT("num_sides: {}".format(num_sides))
					for side_kv_dict in sides_list:
						DPRINT("side: {}".format(side_kv_dict))
						
		
	#	
	return vmf_dict
	
def find_or_create_attrib(hou_geometry, hou_attrib_type, attrib_name, default_value):
	if hou_attrib_type == hou.attribType.Point:
		attrib = hou_geometry.findPointAttrib(attrib_name)
	elif hou_attrib_type == hou.attribType.Prim:
		attrib = hou_geometry.findPrimAttrib(attrib_name)
	if attrib == None:
		attrib = hou_geometry.addAttrib(hou_attrib_type, attrib_name, default_value)
	return attrib
	
def find_or_create_pointgroup(hou_geometry, point_group_name):
	point_group = hou_geometry.findPointGroup(point_group_name)
	if point_group == None:
		point_group = hou_geometry.createPointGroup(point_group_name)
	
	return point_group
	
PMT_VMF_ENTITY_RESTRICTED_KEYVALUES = ["id", "origin", "angles"]
	
def import_vmf(hou_geometry, vmf_dict):
	if not IN_HOUDINI:
		return
	
	def parse_side(side_kv_dict):
		plane_str = side_kv_dict["plane"]
		uaxis_str = side_kv_dict["uaxis"]
		vaxis_str = side_kv_dict["vaxis"]
		material = side_kv_dict["material"]
		lightmapscale = int(side_kv_dict["lightmapscale"])
		
		plane = plane_str.replace("(", "").replace(")", "").split(" ", maxsplit = -1)
		while "" in plane:
			plane.remove("")
		v0 = hou.Vector3(float(plane[0]), float(plane[1]), float(plane[2]))
		v1 = hou.Vector3(float(plane[3]), float(plane[4]), float(plane[5]))
		v2 = hou.Vector3(float(plane[6]), float(plane[7]), float(plane[8]))
			
		uaxis_tokens = uaxis_str.replace("[", "").replace("]", "").split(" ", maxsplit = -1)
		while "" in uaxis_tokens:
			uaxis_tokens.remove("")
		uaxis = hou.Vector3(float(uaxis_tokens[0]), float(uaxis_tokens[1]), float(uaxis_tokens[2]))
		uoffset = float(uaxis_tokens[3])
		uscale = float(uaxis_tokens[4])
		
		vaxis_tokens = vaxis_str.replace("[", "").replace("]", "").split(" ", maxsplit = -1)
		while "" in vaxis_tokens:
			vaxis_tokens.remove("")
		vaxis = hou.Vector3(float(vaxis_tokens[0]), float(vaxis_tokens[1]), float(vaxis_tokens[2]))
		voffset = float(vaxis_tokens[3])
		vscale = float(vaxis_tokens[4])
		
		scale = hou.Vector2((uscale, vscale))
		offset = hou.Vector2((uoffset, voffset))
			
		return (v0, v1, v2, uaxis, vaxis, scale, offset, material)
		
	point_class_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_vmf_entity_class", "")
	point_kv_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_vmf_entity_keyvalues", dict())
	rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_vmf_rotation_euler", hou.Vector3((0,0,0)))
	has_rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_has_euler_rotation", 1)
		
	prim_material_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_vmf_material", "")
	prim_uv_u_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_vmf_uv_u_axis", hou.Vector3((0,0,0)))
	prim_uv_v_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_vmf_uv_v_axis", hou.Vector3((0,0,0)))
	prim_uv_scale_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_vmf_uv_scale", hou.Vector2((0,0)))
	prim_uv_offset_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_vmf_uv_offset", hou.Vector2((0,0)))
	
	brush_index_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "vmf_import_brush_index", -1)
	
	world_group = find_or_create_pointgroup(hou_geometry, "vmf_world")
	pointentity_group = find_or_create_pointgroup(hou_geometry, "vmf_pointentity")
	brushentity_group = find_or_create_pointgroup(hou_geometry, "vmf_brushentity")
	
	brush_index = 0
	if "world" in vmf_dict:
		assert len(vmf_dict["world"]) == 1, "error: .vmf file has multiple world(s)"
		world_kv = vmf_dict["world"][0]
	
		if "solid" in world_kv:
			solids_list = world_kv["solid"]
			for solid_kv_dict in solids_list:
				if "side" not in solid_kv_dict:
					continue 
					
				sides_list = solid_kv_dict["side"]
				for side_kv_dict in sides_list:
					(v0, v1, v2, uaxis, vaxis, scale, offset, material) = parse_side(side_kv_dict)
					
					new_poly = hou_geometry.createPolygon()
					new_poly.setAttribValue(brush_index_attrib, brush_index)
					new_poly.setAttribValue(prim_material_attrib, material)
					new_poly.setAttribValue(prim_uv_u_attrib, uaxis)
					new_poly.setAttribValue(prim_uv_v_attrib, vaxis)
					new_poly.setAttribValue(prim_uv_scale_attrib, scale)
					new_poly.setAttribValue(prim_uv_offset_attrib, offset)
					
					#todo: process other entity attribs
					
					for v in [v0, v1, v2]:
						new_point = hou_geometry.createPoint()
						new_point.setPosition(v)
						world_group.add(new_point)
						new_poly.addVertex(new_point)
				brush_index += 1
				
	if "entity" in vmf_dict:
		entity_list = vmf_dict["entity"]
		for entity_kv_dict in entity_list:
					
			if "solid" in entity_kv_dict:
				entity_brushes = entity_kv_dict["solid"]
				for solid_kv_dict in entity_brushes:
					if "side" not in solid_kv_dict:
						continue 
						
					sides_list = solid_kv_dict["side"]
					for side_kv_dict in sides_list:
						(v0, v1, v2, uaxis, vaxis, scale, offset, material) = parse_side(side_kv_dict)
						
						new_poly = hou_geometry.createPolygon()
						new_poly.setAttribValue(brush_index_attrib, brush_index)
						new_poly.setAttribValue(prim_material_attrib, material)
						new_poly.setAttribValue(prim_uv_u_attrib, uaxis)
						new_poly.setAttribValue(prim_uv_v_attrib, vaxis)
						new_poly.setAttribValue(prim_uv_scale_attrib, scale)
						new_poly.setAttribValue(prim_uv_offset_attrib, offset)
						
						for v in [v0, v1, v2]:
							new_point = hou_geometry.createPoint()
							new_point.setPosition(v)
							brushentity_group.add(new_point)
							new_poly.addVertex(new_point)
					brush_index += 1
					
			else:
				def str_to_vector3(string):
					coords = string.split(" ", maxsplit = -1)
					return hou.Vector3( (float(coords[0]), float(coords[1]), float(coords[2])) )
			
				new_point = hou_geometry.createPoint()
				if "classname" in entity_kv_dict:
					classname = entity_kv_dict["classname"]
					new_point.setAttribValue(point_class_attrib, classname)
					del entity_kv_dict["classname"]
					
				if "origin" in entity_kv_dict:
					origin = str_to_vector3(entity_kv_dict["origin"])
					new_point.setPosition(origin)
					del entity_kv_dict["origin"]
					
				if "angles" in entity_kv_dict:
					#angles is ordered as y, z, x, whereas pmt_vmf_rotation_euler is x, y, z
					angles_tokens = entity_kv_dict["angles"].split(" ", maxsplit = -1)
					angles = hou.Vector3( (float(angles_tokens[2]), float(angles_tokens[0]), float(angles_tokens[1])) )
					
					new_point.setAttribValue(rotation_attrib, angles)
					new_point.setAttribValue(has_rotation_attrib, 1)
					del entity_kv_dict["angles"]
				
				for remove_key in PMT_VMF_ENTITY_RESTRICTED_KEYVALUES:
					if remove_key in entity_kv_dict:
						del entity_kv_dict[remove_key]
						
				array_keys = list()
				for key in entity_kv_dict:
					if type(entity_kv_dict[key]) == type(list()):
						array_keys.append(key)
						
				for remove_key in array_keys:
					del entity_kv_dict[remove_key]
						
				new_point.setAttribValue(point_kv_attrib, entity_kv_dict)
				pointentity_group.add(new_point)
				
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("pmt_prefab_source1_vmf.py [path_to.vmf]")
		exit()
	
	vmf_path = sys.argv[1]
	
	vmf_dict = parse_vmf(vmf_path)
	
else:
	import hou
	node = hou.pwd()
	IS_PYTHON_NODE = node != None and "python" in node.type().nameWithCategory().lower() #'Sop/python' in Houdini 18.5
	if IS_PYTHON_NODE:
		geo = node.geometry()
		
		vmf_path = "C:/pmt_resources/exports/out.vmf"
		vmf_dict = parse_vmf(vmf_path)
		import_vmf(geo, vmf_dict)