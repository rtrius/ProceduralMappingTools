#!/usr/bin/env python3
#	node               : 	pmt::pmt_t3d_import
#	houdini_module_name: 	pmt_t3d_import

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

class ImportActorT3d:
	def __init__(self):
		self.keyvalues = None	#dict()
		self.brushes = list()	#ImportBrushT3d
	def has_brushes(self):
		return len(self.brushes) > 0
		
class ImportBrushT3d:
	def __init__(self):
		self.keyvalues = None	#dict()
		self.polygons = list()	#ImportPolyT3d
		
class ImportPolyT3d:
	def __init__(self):
		self.origin = None
		self.normal = None
		self.textureu = None
		self.texturev = None
		self.pan = None
		self.vertices = list()
		self.keyvalues = None	#dict
		
def parse_t3d(t3d_path):
			
	#Assume that the quotes must be matched; that is \" must end with \" and likewise with \'.
	#Under this assumption, literals such as "string' or 'string" are invalid.
	INQUOTE_TOKEN = "%%q_"
	def extract_string_literals(text, debug_path = None):
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
		assert not in_quote, "error: missing closing quote for quote_char({}): [{}]".format(quote_char, debug_path, text)
			
		return (text_without_quotes, inquote_text_dict)
	
	with open(t3d_path, 'rt', encoding=TEXT_CODEC) as t3d_file:
		text = ""
		for line in t3d_file:
			text += line.lstrip()
			
	(text_without_quotes, inquote_text_dict) = extract_string_literals(text, t3d_path)
	lines = text_without_quotes.split("\n", maxsplit = -1)
	while "" in lines:
		lines.remove("")
	num_lines = len(lines)
	
	for i in range(num_lines):
		lines[i] = lines[i].lower()
	
	assert lines[0].startswith("begin map"), "t3d does not start with 'begin map': {}".format(lines[0].lower())
	assert lines[-1].startswith("end map"), "t3d does not end with 'end map': {}".format(lines[-1].lower())
	
	def find_line_index_that_startswith(lines, start_index, end_statement = "end map"):
		num_lines = len(lines)
		while start_index < num_lines:
			if lines[start_index].startswith(end_statement):
				return start_index
			start_index += 1
			
		return None
	def get_begin_statement_keyvalues(begin_line):
		kv_dict = dict()
	
		begin_line_tokens = begin_line.rstrip().split(sep = " ", maxsplit = -1)
		begin_line_tokens = begin_line_tokens[2:]
		for t in begin_line_tokens:
			t = t.lower()
			if "=" in t:
				left, sep, right = t.partition("=")
				kv_dict[left] = right
				DPRINT("beginkv {}={}".format(left, right))
		return kv_dict
		
	def parse_brush(lines, brush_start, inquote_text_dict):
		brush_end = find_line_index_that_startswith(lines, brush_start, end_statement = "end brush")
		
		brush_first_line = lines[brush_start]
		brush_kv_dict = get_begin_statement_keyvalues(brush_first_line)
		polygons = list()
		
		polylist_start = find_line_index_that_startswith(lines, brush_start, end_statement = "begin polylist")
		polylist_end = find_line_index_that_startswith(lines, brush_start, end_statement = "end polylist")
		
		num_lines = len(lines)
		brush_line_index = polylist_start + 1
		while brush_line_index < polylist_end:
			brush_line = lines[brush_line_index]
		
			if brush_line.startswith("begin polygon"):
				poly_kv = get_begin_statement_keyvalues(brush_line)
				
				poly_start = brush_line_index
				poly_end = find_line_index_that_startswith(lines, brush_line_index, end_statement = "end polygon")
				
				poly_lines = lines[poly_start+1:poly_end]
				assert "begin polygon" not in poly_lines[0]
				assert "end polygon" not in poly_lines[-1]
				
				poly = ImportPolyT3d()
				poly.keyvalues = poly_kv
				for poly_line in poly_lines:
					def float3_to_tokens(line, remove = "origin"):
						return line[len(remove):].lstrip().split(",", maxsplit=-1)
						
					if poly_line.startswith("origin"):
						floatstr = float3_to_tokens(poly_line, "origin")
						DPRINT("origin: {}".format(floatstr))
						poly.origin = floatstr
					elif poly_line.startswith("normal"):
						floatstr = float3_to_tokens(poly_line, "normal")
						DPRINT("normal: {}".format(floatstr))
						poly.normal = floatstr
					elif poly_line.startswith("textureu"):
						floatstr = float3_to_tokens(poly_line, "textureu")
						DPRINT("textureu: {}".format(floatstr))
						poly.textureu = floatstr
					elif poly_line.startswith("texturev"):
						floatstr = float3_to_tokens(poly_line, "texturev")
						DPRINT("texturev: {}".format(floatstr))
						poly.texturev = floatstr
					elif poly_line.startswith("vertex"):
						floatstr = float3_to_tokens(poly_line, "vertex")
						DPRINT("vertex: {}".format(floatstr))
						poly.vertices.append(floatstr)
					elif poly_line.startswith("pan"):
						pan_line = poly_line[len("pan"):].lstrip()
						uline, sep, vline = pan_line.partition(" ")
						assert uline.startswith("u=")
						assert vline.startswith("v=")
						pan_u = uline[2:]
						pan_v = vline[2:]
						DPRINT("pan_u,v: {}".format((pan_u, pan_v)))
						poly.pan = (pan_u, pan_v)
					else:
						assert False, "unsupported line in 'begin polygon': {}".format(poly_line)
						
				polygons.append(poly)
				
				brush_line_index = poly_end
			brush_line_index += 1
		
		brush = ImportBrushT3d()
		brush.keyvalues = brush_kv_dict
		brush.polygons = polygons
		return (brush, brush_end)
		
	def parse_actor(lines, actor_start, inquote_text_dict):
		actor_end = find_line_index_that_startswith(lines, actor_start, end_statement = "end actor")
		
		actor_first_line = lines[actor_start]
		actor_kv_dict = get_begin_statement_keyvalues(actor_first_line)
		brushes = list()
		
		num_lines = len(lines)
		actor_line_index = actor_start + 1
		while actor_line_index < actor_end:
			actor_line = lines[actor_line_index]
		
			if actor_line.startswith("begin brush"):
				(brush, actor_line_index) = parse_brush(lines, actor_line_index, inquote_text_dict)
				brushes.append(brush)
			elif "=" in actor_line:
				left, sep, right = actor_line.rstrip().partition("=")
				key = left.lower()
				value = right
				if INQUOTE_TOKEN in value:
					vtokens = value.split(" ", maxsplit = -1)
					while "" in vtokens:
						vtokens.remove("")
						
					num_rtokens = len(vtokens)
					assert num_rtokens <= 2, "actorkv unsupported: {} (vtokens={})".format(actor_line, vtokens)
				
					if num_rtokens == 1 and vtokens[0].startswith(INQUOTE_TOKEN):
						type_string = "string"
						value_string = inquote_text_dict[vtokens[0]]
						kv_string = value_string
						DPRINT("actorkv {}='{}'".format(left, value_string))
					elif num_rtokens == 2 and vtokens[1].startswith(INQUOTE_TOKEN):
						type_string = vtokens[0]
						value_string = inquote_text_dict[vtokens[1]]
						kv_string = "{}'{}'".format(type_string, value_string)
						DPRINT("actorkv {}={}'{}'".format(left, type_string, value_string))
					
					actor_kv_dict[key] = kv_string
					
				else:
					DPRINT("actorkv {}={}".format(key, value))
					actor_kv_dict[key] = value
			actor_line_index += 1
			
		actor = ImportActorT3d()
		actor.keyvalues = actor_kv_dict
		actor.brushes = brushes
		return (actor, actor_end)
	
	actors = list()
	
	line_index = 1
	while line_index < num_lines-1:
		line = lines[line_index]

		if line.startswith("begin actor"):
			(actor, line_index) = parse_actor(lines, line_index, inquote_text_dict)
			actors.append(actor)
	
		line_index += 1
	
	return actors


U1_TO_DEGREES = 360.0 / 65536.0
			
PMT_T3D_ENTITY_RESTRICTED_KEYVALUES = ["class", "name", "location", "rotation"]  #pmt_common.py

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
	
def add_imported_actor(hou_geometry, actor, brush_index):
	if not IN_HOUDINI:
		return
		
	is_brush_actor = actor.has_brushes()
	
	#world_group = find_or_create_pointgroup(hou_geometry, "t3d_world")
	pointentity_group = find_or_create_pointgroup(hou_geometry, "t3d_pointentity")
	brush_group = find_or_create_pointgroup(hou_geometry, "t3d_brush")
	
	if not is_brush_actor:
		point_class_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_t3d_entity_class", "")
		point_kv_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_t3d_entity_keyvalues", dict())
		rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_t3d_rotation_euler", hou.Vector3((0,0,0)))
		has_rotation_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Point, "pmt_has_euler_rotation", 1)
		
		position = hou.Vector3((0,0,0))
		if "location" in actor.keyvalues:
			locstr = actor.keyvalues["location"].lower()
			locstr = locstr.replace("(", "") 
			locstr = locstr.replace(")", "") 
			loc = locstr.split(",", maxsplit = -1)
			while "" in loc:
				loc.remove("")
			for coord in loc:
				val = float(coord[2:])
				if coord.startswith("x="):
					position[0] = val
				elif coord.startswith("y="):
					position[1] = val
				elif coord.startswith("z="):
					position[2] = val
					
			
		rotation = hou.Vector3((0,0,0))		
		if "rotation" in actor.keyvalues:
			rotstr = actor.keyvalues["rotation"].lower()
			rotstr = rotstr.replace("(", "") 
			rotstr = rotstr.replace(")", "") 
			rot = rotstr.split(",", maxsplit = -1)
			while "" in rot:
				rot.remove("")
			for coord in rot:
				P = "pitch=" 	
				Y = "yaw="		
				R = "roll="		
				if coord.startswith(P):
					val = coord[len(P):]
					rotation[1] = float(val) * U1_TO_DEGREES	#pitch y-axis
				elif coord.startswith(Y):
					val = coord[len(Y):]
					rotation[2] = float(val) * U1_TO_DEGREES	#yaw z-axis
				elif coord.startswith(R):
					val = coord[len(R):]
					rotation[0] = float(val) * U1_TO_DEGREES	#roll x-axis
					
		new_point = hou_geometry.createPoint()
		new_point.setPosition(position)
		new_point.setAttribValue(rotation_attrib, rotation)
		new_point.setAttribValue(has_rotation_attrib, 1)
		#newpt_kv = dictAttribValue(point_kv_attrib)
		#for key in actor.keyvalues:
		#	if key in PMT_T3D_ENTITY_RESTRICTED_KEYVALUES:
		#		continue
		#	newpt_kv[key] = actor.keyvalues
		#	
		#new_point.setAttribValue(point_kv_attrib, newpt_kv)
		
		if "class" in actor.keyvalues:
			new_point.setAttribValue(point_class_attrib, actor.keyvalues["class"])
			del actor.keyvalues["class"]
			
		for remove_key in PMT_T3D_ENTITY_RESTRICTED_KEYVALUES:
			if remove_key in actor.keyvalues:
				del actor.keyvalues[remove_key]
		new_point.setAttribValue(point_kv_attrib, actor.keyvalues)
		
		pointentity_group.add(new_point)
		
	else:
		#pmt_t3d_texture_size
		#pmt_t3d_texture_path
		prim_material_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_material", "")
		
		prim_uv_u_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_uv_u_axis", hou.Vector3((0,0,0)))
		prim_uv_v_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_uv_v_axis", hou.Vector3((0,0,0)))
		prim_uv_scale_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_uv_scale", hou.Vector2((0,0)))
		prim_uv_offset_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_uv_offset", hou.Vector2((0,0)))
		
		uclassname = None
		if "class" in actor.keyvalues:
			prim_class_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_entity_class", "")
			prim_kv_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "pmt_t3d_entity_keyvalues", dict())
			uclassname = actor.keyvalues["class"]
			del actor.keyvalues["class"]
			
		for remove_key in PMT_T3D_ENTITY_RESTRICTED_KEYVALUES:
			if remove_key in actor.keyvalues:
				del actor.keyvalues[remove_key]
		
		
		#for merging vertices shared between prims
		brush_index_attrib = find_or_create_attrib(hou_geometry, hou.attribType.Prim, "t3d_import_brush_index", -1)
		
		for brush in actor.brushes:
			#for key in brush.keyvalues:
			
			
			brush_index += 1	
			for poly in brush.polygons:
				material = "engine.defaulttexture"
				if "texture" in poly.keyvalues:
					material = poly.keyvalues["texture"]
					
				#origin = hou.Vector3((float(poly.origin[0]), float(poly.origin[1]), float(poly.origin[2])))
				#normal = hou.Vector3((float(poly.normal[0]), float(poly.normal[1]), float(poly.normal[2])))
				textureu = hou.Vector3((float(poly.textureu[0]), float(poly.textureu[1]), float(poly.textureu[2])))
				texturev = hou.Vector3((float(poly.texturev[0]), float(poly.texturev[1]), float(poly.texturev[2])))
				scaleu = textureu.length()
				scalev = texturev.length()
				scale = hou.Vector2((scaleu, scalev))
				textureu = textureu.normalized()
				texturev = texturev.normalized()
				pan = hou.Vector2(float(poly.pan[0]), float(poly.pan[1]))
				
				#pmt_* uv attribs use .vmf convention, so convert from .t3d to .vmf
				if True:
					scale[0] = 1.0 / scale[0]
					scale[1] = 1.0 / scale[1]
				
				new_poly = hou_geometry.createPolygon()
				new_poly.setAttribValue(brush_index_attrib, brush_index)
				
				new_poly.setAttribValue(prim_material_attrib, material)
				new_poly.setAttribValue(prim_uv_u_attrib, textureu)
				new_poly.setAttribValue(prim_uv_v_attrib, texturev)
				new_poly.setAttribValue(prim_uv_scale_attrib, scale)
				new_poly.setAttribValue(prim_uv_offset_attrib, pan)
				
				if uclassname != None:
					new_poly.setAttribValue(prim_class_attrib, uclassname)
					new_poly.setAttribValue(prim_kv_attrib, actor.keyvalues)
					
				for vertex in reversed(poly.vertices):
					x, y, z = float(vertex[0]), float(vertex[1]), float(vertex[2])
					pos = hou.Vector3((x,y,z))
					new_point = hou_geometry.createPoint()
					new_point.setPosition(pos)
					brush_group.add(new_point)
		
					new_poly.addVertex(new_point)
					if "texture" in poly.keyvalues:
						new_poly.setAttribValue(prim_material_attrib, poly.keyvalues["texture"])
	return brush_index
	
	
def import_actors(hou_geometry, actors):
	#skip the first brush, which is the 'active brush' that does not contribute to world geometry
	is_first_brush = True
		
	#track a global brush index so that vertices shared by brushes can be merged
	brush_index = 0
		
	for a in actors:
		if is_first_brush and "class" in a.keyvalues and a.keyvalues["class"] == "brush":
			is_first_brush = False
			continue
		brush_index = add_imported_actor(hou_geometry, a, brush_index)

if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("pmt_prefab_unreal1_t3d.py [path_to.t3d]")
		exit()
	
	t3d_path = sys.argv[1]
	
	actors = parse_t3d(t3d_path)
else:
	import hou
	node = hou.pwd()
	IS_PYTHON_NODE = node != None and "python" in node.type().nameWithCategory().lower() #'Sop/python' in Houdini 18.5
	if IS_PYTHON_NODE:
		t3d_path = "C:/pmt/exports/out.t3d"
		
		geo = node.geometry()
		actors = parse_t3d(t3d_path)
		import_actors(geo, actors)