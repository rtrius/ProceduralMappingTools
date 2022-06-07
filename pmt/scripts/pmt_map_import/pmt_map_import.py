#!/usr/bin/env python3
#	node               : 	pmt::pmt_map_import
#	houdini_module_name: 	pmt_map_import

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

#.map format(idTech4) is a series of 'entity' statements, that encloses:
#	A) a series of key-value pairs, and/or
#	B) a series of primitives that are either brushes or patches
#Typically 'entity 0' is worldspawn, and has the key-value pair:
#		"classname" "worldspawn"

#Rough example:
#
#Version 2
#	//entity 0
#	{
#		"key" "value"
#		"key" "value"
#		...
#		"key" "value"
#		//primitive 0
#		{
#			brushDef3|patchDef2|patchDef3
#			{
#				...
#			}
#		}
#		//primitive 1
#		{
#			...
#		}
#		//primitive 2
#		{
#			...
#		}
#		...
#	}
#	//entity 1
#	{
#		...
#	}
#	//entity 2
#	{
#		...
#	}
#	...
#	

PRIMITIVE_TYPES = ["brushdef3", "patchdef2", "patchdef3"]

class ImportMapBrushPlane:
	def __init__(self):
		self.normal = None
		self.distance = None	#plane constant
		self.uv_row0 = None
		self.uv_row1 = None
		self.material = None
		
class ImportMapBrush:
	def __init__(self):
		self.planes = list()
		
class ImportMapPatchdef2:
	def __init__(self):
		self.width = None
		self.height = None
		self.material = None
		self.vertices = list()
		
class ImportMapPatchdef3(ImportMapPatchdef2):
	def __init__(self):
		super().__init__()
		self.width_subdivisions = None
		self.height_subdivisions = None

class ImportMapEntity:
	def __init__(self):
		keyvalues = dict()
		brushes = list()
		patchdef2s = list()
		patchdef3s = list()

def parse_map(map_path):
	with open(map_path, 'rt', encoding=TEXT_CODEC) as map_file:
		text = ""
		for line in map_file:
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
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, map_path)
	
	def simplify_whitespace(text):
		for char in string.whitespace:
			text = text.replace(char, " ")
		return text
	text_without_quotes = simplify_whitespace(text_without_quotes)
	
	def pad_operators(text):
		#pad '{', '}', ... with spaces so that split() will not mix them with text
		PAD_CHARS = "{}()"
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
	entities = list()
	
	assert tokens[0].lower() == "version"
	assert tokens[1] == "2"
	
	num_tokens = len(tokens)
	token_index = 2
	while token_index < num_tokens:
		t = tokens[token_index]
		#t_quote = tokens_with_quotes[token_index]
		
		if t == "{":
			entity_opening = token_index
			
			bracket_depth = 1
			entity_closing = token_index + 1
			while entity_closing < num_tokens:
				t2 = tokens[entity_closing]
				if t2 == "{": bracket_depth += 1
				if t2 == "}": bracket_depth -= 1
				if bracket_depth == 0: break
				
				entity_closing += 1
			assert bracket_depth == 0, "error: no closing bracket in .map"
			
			def parse_entity(tokens, tokens_with_quotes, entity_opening, entity_closing):
				
				entity_kv = dict()
				ent_brushes = list()
				ent_patch2s = list()
				ent_patch3s = list()
				DPRINT("ent tokens: {}".format(tokens[entity_opening:entity_closing+1]))
				#num_tokens2 = len(tokens)
				token_index2 = entity_opening + 1
				while token_index2 < entity_closing:
					if tokens_with_quotes[token_index2].startswith(INQUOTE_TOKEN):
						t2_lower = tokens[token_index2].lower()
						t2_next = tokens[token_index2 + 1]
						entity_kv[t2_lower] = t2_next
						DPRINT("addkv: {}={}".format(t2_lower, t2_next)) 
						token_index2 += 1
					elif t == "{":
						opening_index3 = token_index2
						primitive_type = tokens[opening_index3 + 1].lower()
						assert primitive_type in PRIMITIVE_TYPES, "primitive_type: '{}' is not in PRIMITIVE_TYPES token_index2={}".format(primitive_type, token_index2)
						assert tokens[opening_index3 + 2] == "{", "No 2nd opening bracket for primitive_type '{}' token_index2={}".format(primitive_type, token_index2)
						
						if primitive_type not in entity_kv:
							entity_kv[primitive_type] = list()
						
						num_closing_brackets = 0
						closing_index3 = opening_index3
						while closing_index3 < entity_closing and num_closing_brackets < 2:
							if tokens[closing_index3] == "}": num_closing_brackets += 1
							if num_closing_brackets < 2: closing_index3 += 1
						assert num_closing_brackets == 2
						assert tokens[closing_index3] == "}"
						
						num_prim_tokens = (closing_index3 - opening_index3) + 1
						
						#DPRINT("num_prim_tokens={} for primitive_type={}".format(num_prim_tokens, primitive_type))
						DPRINT("prim tokens: {}".format(tokens[opening_index3:closing_index3+1]))
						if primitive_type == "brushdef3":
							#A brushdef3 has 5 tokens and 22 tokens for each plane:
							#{
							#	brushdef3
							#	{
							#		( x y z d ) ( ( a b c ) ( d e f ) ) TEXTURE_PATH 0 0 0
							#		( x y z d ) ( ( a b c ) ( d e f ) ) TEXTURE_PATH 0 0 0
							#		...
							#		( x y z d ) ( ( a b c ) ( d e f ) ) TEXTURE_PATH 0 0 0
							#	}
							#}
							brush = ImportMapBrush()
							assert (num_prim_tokens - 5) % 22 == 0, "num_prim_tokens: {}".format(num_prim_tokens)
							num_planes = (num_prim_tokens - 5) // 22
							for plane_index in range(num_planes):
								pl = opening_index3 + 3 + plane_index * 22 #first plane index
								assert tokens[pl + 0] == "("
								x = tokens[pl + 1]
								y = tokens[pl + 2]
								z = tokens[pl + 3]
								d = tokens[pl + 4]
								assert tokens[pl + 5] == ")"
								assert tokens[pl + 6] == "("
								assert tokens[pl + 7] == "("
								u0 = tokens[pl + 8]
								u1 = tokens[pl + 9]
								u2 = tokens[pl + 10]
								assert tokens[pl + 11] == ")"
								assert tokens[pl + 12] == "("
								v0 = tokens[pl + 13]
								v1 = tokens[pl + 14]
								v2 = tokens[pl + 15]
								assert tokens[pl + 16] == ")"
								assert tokens[pl + 17] == ")"
								material_path = tokens[pl + 18]
								DPRINT("brushdef3 side: {}".format((x,y,z,d, u0,u1,u2, v0,v1,v2, material_path)))
								
								side = ImportMapBrushPlane()
								side.normal = (float(x), float(y), float(z))
								side.distance = float(d)
								side.uv_row0 = (float(u0), float(u1), float(u2))
								side.uv_row1 = (float(v0), float(v1), float(v2))
								side.material = material_path
								brush.planes.append(side)
							ent_brushes.append(brush)
							
						elif primitive_type == "patchdef2" or primitive_type == "patchdef3":
							#patchDef2 has:
							#	5 tokens for the keyword + brackets
							#	10 tokens for the patch params, and outer parenthesis '(' ')'
							#	2 parenthesis '(' ')' tokens for each width + 7 tokens for each vertex
							#{
							#	patchDef2
							#	{
							#		MATERIAL_PATH
							#		( WIDTH HEIGHT 0 0 0 )
							#		(
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		...
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		)
							#	}
							#}
							#
							#patchDef3 is same as patchDef2, except additional parameters (WIDTH_SUBDIVISIONS, HEIGHT_SUBDIVISIONS)
							#patchDef3 has:
							#	5 tokens for the keyword + brackets
							#	12 tokens for the patch params, and outer parenthesis '(' ')'
							#	2 parenthesis '(' ')' tokens for each width + 7 tokens for each vertex
							#{
							#	patchDef3
							#	{
							#		MATERIAL_PATH
							#		( WIDTH HEIGHT WIDTH_SUBDIVISIONS HEIGHT_SUBDIVISIONS 0 0 0 )
							#		(
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		...
							#		( ( x y z u v ) ( x y z u v ) ( x y z u v ) )
							#		)
							#	}
							#}
							#
							#patchDef2/patchDef3
							# -- -- --> height
							# |
							# |
							# v
							# width
							if primitive_type == "patchdef2":
								patch = ImportMapPatchdef2()
							else: #patchdef3
								patch = ImportMapPatchdef3()
							
							texpath_index = opening_index3 + 3
							assert tokens_with_quotes[texpath_index].startswith(INQUOTE_TOKEN)
							material_path = tokens[texpath_index]
							assert tokens[texpath_index + 1] == "("
							width = tokens[texpath_index + 2]
							height = tokens[texpath_index + 3]
							patch.width = int(width)
							patch.height = int(height)
							patch.material = material_path
							
							if primitive_type == "patchdef3":
								width_subdiv = tokens[texpath_index + 4]
								height_subdiv = tokens[texpath_index + 5]
								patch.width_subdivisions = int(width_subdiv)
								patch.height_subdivisions = int(height_subdivisions)
							
							if primitive_type == "patchdef2":
								assert tokens[texpath_index + 4] == "0"
								assert tokens[texpath_index + 5] == "0"
								assert tokens[texpath_index + 6] == "0"
								assert tokens[texpath_index + 7] == ")"
								assert tokens[texpath_index + 8] == "("
								texpath_offset_to_1st_vertex = 11
							else: #patchdef3
								assert tokens[texpath_index + 6] == "0"
								assert tokens[texpath_index + 7] == "0"
								assert tokens[texpath_index + 8] == "0"
								assert tokens[texpath_index + 9] == ")"
								assert tokens[texpath_index + 10] == "("
								texpath_offset_to_1st_vertex = 13
							
							TOKENS_PER_VERTEX = 7
							width_i = int(width)
							height_i = int(height)
							first_vertex_x = texpath_index + texpath_offset_to_1st_vertex #token index of position 'x' of first vertex
							
							tokens_per_width = (height_i * TOKENS_PER_VERTEX) + 2
							
							for w in range(width_i):
								first_x_of_line = first_vertex_x + w * tokens_per_width
								for h in range(height_i):
									x_of_vertex = first_x_of_line + h * TOKENS_PER_VERTEX
									assert tokens[x_of_vertex - 1] == "("
									x = tokens[x_of_vertex]
									y = tokens[x_of_vertex + 1]
									z = tokens[x_of_vertex + 2]
									u = tokens[x_of_vertex + 3]
									v = tokens[x_of_vertex + 4]
									assert tokens[x_of_vertex + 5] == ")"
									DPRINT("{} vtx: {}".format(primitive_type, (x,y,z,u,v)))
									vertex = (float(x), float(y), float(z), float(u), float(v))
									patch.vertices.append(vertex)
									
							if primitive_type == "patchdef2":
								ent_patch2s.append(patch)
							else: #patchdef3
								ent_patch3s.append(patch)
						token_index2 = closing_index3
					else:
						assert False, "unexpected token: {} (token_index2={})".format(tokens[token_index2], token_index2)
						
					token_index2 += 1
					
					
				entity = ImportMapEntity()
				entity.keyvalues = entity_kv
				entity.brushes = ent_brushes
				entity.patchdef2s = ent_patch2s
				entity.patchdef3s = ent_patch3s
				return entity
			entity = parse_entity(tokens, tokens_with_quotes, entity_opening, entity_closing)
			entities.append(entity)
			
			DPRINT("add entity: {}".format(entity.keyvalues))
			token_index = entity_closing
			
		token_index += 1
	return entities
		
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
	
PMT_MAP_ENTITY_RESTRICTED_KEYVALUES = ["classname", "name", "origin", "rotation"]

def import_map(hou_geometry, entities):
	if not IN_HOUDINI:
		return	

	point_class_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_entity_class", "")
	point_kv_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_entity_keyvalues", dict())
	rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_rotation_euler", hou.Vector3((0,0,0)))
	has_rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_has_euler_rotation", 1)
		
	material_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_material", "")
	uv_scale_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_uv_scale", hou.Vector2((1,1)))
	uv_offset_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_uv_offset", hou.Vector2((0,0)))
	uv_rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_map_uv_rotation_degrees", 0.0)
	
	brush_index_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "map_import_brush_index", -1)
	normal_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "N", hou.Vector3((0,0,0)))
	
	patch_material_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_map_material", "")
	patch_width_subdivs_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_map_patchdef3_width_subdivs", -1)
	patch_height_subdivs_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_map_patchdef3_height_subdivs", -1)
	
	world_group = find_or_create_pointgroup(hou_geometry, "map_world")
	pointentity_group = find_or_create_pointgroup(hou_geometry, "map_pointentity")
	brushentity_group = find_or_create_pointgroup(hou_geometry, "map_brushentity")
	
	brush_index = 0
	for e in entities:
		is_world = e.keyvalues["classname"] == "worldspawn"
	
		has_brushes = len(e.brushes) != 0
		has_patches = len(e.patchdef2s) != 0 or len(e.patchdef3s) != 0
		
		has_origin = "origin" in e.keyvalues
		if has_origin:
			origin_tokens = e.keyvalues["origin"].split(" ", maxsplit = -1)
			while "" in origin_tokens: origin_tokens.remove("")
			origin_tuple = (float(origin_tokens[0]), float(origin_tokens[1]), float(origin_tokens[2]))
			origin = hou.Vector3(origin_tuple)
		
		if not is_world and not has_brushes and not has_patches: 
			#point entity
			
			classname = e.keyvalues["classname"]
			
			if "name" in e.keyvalues:
				del e.keyvalues["name"]
			if "origin" in e.keyvalues:
				del e.keyvalues["origin"]
			if "rotation" in e.keyvalues:
				#todo: convert matrix3 to euler
				del e.keyvalues["rotation"]
				
			for remove_key in PMT_MAP_ENTITY_RESTRICTED_KEYVALUES:
				if remove_key in e.keyvalues:
					del e.keyvalues[remove_key]
			
			new_point = hou_geometry.createPoint()
			new_point.setPosition(-origin)
			new_point.setAttribValue(point_class_attrib, classname)
			new_point.setAttribValue(point_kv_attrib, e.keyvalues)
			new_point.setAttribValue(brush_index_attrib, -1)
			pointentity_group.add(new_point)
		else:
			if has_brushes:
				for brush in e.brushes:
				
					for plane in brush.planes:
						N = hou.Vector3(plane.normal)
						plane_constant = plane.distance
						
						clip_pos = N * plane_constant
						if has_origin:
							clip_pos -= origin
						
						#plane.uv_row0
						#plane.uv_row1
						offset = hou.Vector2(plane.uv_row0[2], plane.uv_row1[2])
						
						#todo: convert 'texture_matrix' to scale, rotation
						scale = hou.Vector2(1.0, 1.0)
						rotation = 0.0
						
						clip_point = hou_geometry.createPoint()
						clip_point.setPosition(clip_pos)
						clip_point.setAttribValue(normal_attrib, N)
						clip_point.setAttribValue(material_attrib, plane.material)
						clip_point.setAttribValue(uv_scale_attrib, scale)
						clip_point.setAttribValue(uv_offset_attrib, offset)
						clip_point.setAttribValue(uv_rotation_attrib, rotation)
						
						clip_point.setAttribValue(brush_index_attrib, brush_index)
						if is_world:
							world_group.add(clip_point)
						else:
							brushentity_group.add(clip_point)
					brush_index += 1
					
			if has_patches:
				def make_patch(hou_geo, patchdef, is_patchdef3 = False):
					patch = hou_geo.createBezierSurface(width, height, is_closed_in_u=False, is_closed_in_v=False)
					patch.setAttribValue(patch_material_attrib, patchdef.material)
					if is_patchdef3:
						patch.setAttribValue(patch_width_subdivs_attrib, patchdef.width_subdiv)
						patch.setAttribValue(patch_height_subdivs_attrib, patchdef.height_subdiv)
						
					for w in range(width):
						for h in range(height):
							vertex_index = w * height + h
							vertex_position = patchdef.vertices[vertex_index]
						
							p = patch.vertex(w, h).point()
							p.setPosition(vertex_position)
							if is_world:
								world_group.add(p)
							else:
								brushentity_group.add(p)
					return patch		
					
				for patch2 in e.patchdef2s:
					make_patch(hou_geometry, patch2, is_patchdef3 = False)
					
				for patch3 in e.patchdef3s:
					make_patch(hou_geometry, patch3, is_patchdef3 = True)
					
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("pmt_prefab_idtech4_map.py [path_to.map]")
		exit()
	
	map_path = sys.argv[1]
	
	map_data = parse_map(map_path)
else:
	import hou
	node = hou.pwd()
	IS_PYTHON_NODE = node != None and "python" in node.type().nameWithCategory().lower() #'Sop/python' in Houdini 18.5
	if IS_PYTHON_NODE:
		geo = node.geometry()
		
		map_path = "C:/pmt/exports/out.map"
		entity_list = parse_map(map_path)
		import_map(geo, entity_list)