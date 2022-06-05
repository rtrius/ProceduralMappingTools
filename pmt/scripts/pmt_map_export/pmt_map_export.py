#!/usr/bin/env python3
#	node               : 	pmt::pmt_map_export
#	script_section_name: 	pmt_map_export.py

###__pmt::pmt__globalconfig__COMMON_SECTION__
if True:
	import hou
	PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt__global_config = PMT__G_CFG.pmt__global_config
	pmt_common = PMT__G_CFG.pmt_common
	pmt_material_select = PMT__G_CFG.pmt_material_select
	pmt_parse_source1_fgd = PMT__G_CFG.pmt_parse_source1_fgd
###__pmt::pmt__globalconfig__COMMON_SECTION__

###pmt exporters COMMON_SECTION
if True:
	LINS = pmt_common.LINS
	LINE = pmt_common.LINE
###pmt exporters COMMON_SECTION

import sys
import os
import math
import random
import importlib

import inspect
CF = inspect.currentframe
def CURFUNC(inspect_currentframe): #return the name of the 'current function':  CURFUNC(CF())
	return inspect_currentframe.f_code.co_name
def CCF(self, inspect_currentframe, sep = "::", suffix = "()"): #return the name the the 'current class function': CCF(self, CF())
	return type(self).__qualname__ + sep + inspect_currentframe.f_code.co_name +  suffix
	
#A plane defined by normal and distance
class Side:
	def __init__(self):
		self.primidx = None #Houdini prim index, for debugging
		self.normal = (0.0, 0.0, 0.0)
		self.distance = 0.0
		self.material_str = None
		self.uv_data = None
		self.texture_size = None
		
		self.vertices = None
		

#A convex solid defined by the intersections of multiple halfspaces(planes)
class BrushDef3:
	def __init__(self):
		self.sides = list()
		
		self.bsp_island = None 	#bsp_island is an int shared by all prims of a single brush
		
		#self.origin = None	#Only used for detail brushes
		self.entity_island = None 	#entity_island is an int indicating which entity the brush is assigned to  
		self.entity_class = None	#string 
		self.entity_keyvalues_dict = None
		
#An entity composed of multiple solid brushes.
#We assume that all keyvalues of the solids are the same, 
#so we can get the keyvalues by looking at entity_keyvalues_list of solids[0].
class BrushEntity:
	def __init__(self):
		self.origin = None
		self.brushes = list()
		
#// primitive N
#{
#patchDef2
#{
#"TEXTURE_PATH"
#( width height 0 0 0 )
#(
#( ( 128 0 -64 0 0 ) ( 128 0 0 0 -4 ) ( 128 0 64 0 -8 ) )
#( ( 192 0 -64 4 0 ) ( 192 0 0 4 -4 ) ( 192 0 64 4 -8 ) )
#( ( 256 0 -64 8 0 ) ( 256 0 0 8 -4 ) ( 256 0 64 8 -8 ) )
#)
#}
#}
#patchDef2
# -- -- --> height
# |
# |
# v
# width
#
# (x y z u v)
#
#
#patchDef3
#
#Same as patchdef2, except width/height subdivisions 
#corresponds to 'Fixed Subdivisions' in patch inspector
#
#// primitive N
#{
#patchDef3
#{
#"TEXTURE_PATH"
#( width height width_subdivisions height_subdivisions 0 0 0 )
#(
#( ( 128 0 -64 0 0 ) ( 128 0 0 0 -4 ) ( 128 0 64 0 -8 ) )
#( ( 192 0 -64 4 0 ) ( 192 0 0 4 -4 ) ( 192 0 64 4 -8 ) )
#( ( 256 0 -64 8 0 ) ( 256 0 0 8 -4 ) ( 256 0 64 8 -8 ) )
#)
#}
#}
class PatchDef:
	def __init__(self):
		self.width = 0
		self.height = 0
		self.vertices = list()			#Each element is 5 tuple (x,y,z,u,v)
		self.material_str = None
		
		self.width_subdivisions = None #4
		self.height_subdivisions = None #4
		
		self.entity_class = None	#string 
		self.entity_keyvalues_dict = None
	
	#Inverts direction of patch normal
	def reverse(self):
		width_list = list()
		for width_index in range(self.width):
			height_start = width_index * self.height
			
			height_list = list()
			for height_index in range(self.height):
				height_list.append(self.vertices[height_start + height_index])
			
			width_list.append(height_list)
		width_list.reverse()
		
		self.vertices = list()	
		for width_index in range(self.width):
			self.vertices += width_list[width_index]
			
	def is_patchdef3(self):
		return self.width_subdivisions != None and self.height_subdivisions != None
	def is_patch_entity(self):
		return self.entity_class != None and self.entity_keyvalues_dict != None
		
TAB = "\t"
NEWLINE = "\n"

#Returns string in format:	[\t + \t + ... + \t] + string + \n
def LINS(num_tabs, string):
	out = ""
	for i in range(num_tabs):
		out += TAB
	out += string + NEWLINE
	return out
	
#Returns string in format:	[\t + \t + ... + \t] + "key" + " " + "value" + \n
def LINE(num_tabs, key, value):
	out = ""
	for i in range(num_tabs):
		out += TAB
	out += "\"" + key + "\" \"" + value + "\"" + NEWLINE
	return out
	
#converts float -> int -> string
def FloatStr(float_value):
	#return str( int( round(float_value) ) )
	return str( int(float_value) )
	
#converts float -> string
def FloatUVStr(float_value):
	return '{0:0=.16f}'.format(float_value)
	#return str(float_value)

def PlaneStr(n, distance, material = "textures/common/clip", uv_data = None, texture_size = None, primidx = -1, bsp_island = -1):

	#0.0078125 == 1/128
	scale = (0.0078125, 0.0078125)
	offset = (0.0, 0.0)
	rotation_radians = 0.0
	if texture_size == None:
		texture_size = (128, 128)
	
	if uv_data != None:
		if texture_size == None:
			assert False, "map export_polygon(): error - side has uv_data but not texture_size"
		scale = uv_data.map_uv_scale
		offset = uv_data.map_uv_offset
		rotation_degrees = uv_data.map_uv_rotation_degrees
		rotation_radians = math.radians(rotation_degrees)
	
	assert scale[0] != 0.0, "scale[0] is 0"
	assert scale[1] != 0.0, "scale[1] is 0"
		
	TEXTURE_SIZE_EPSILON = 1.0
	assert texture_size[0] >= TEXTURE_SIZE_EPSILON, "texture_size[0] < {} (material={}, texture_size={}, primidx={}, bsp_island={})".format(material, texture_size, TEXTURE_SIZE_EPSILON, primidx, bsp_island)
	assert texture_size[1] >= TEXTURE_SIZE_EPSILON, "texture_size[1] < {} (material={}, texture_size={}, primidx={}, bsp_island={})".format(material, texture_size, TEXTURE_SIZE_EPSILON, primidx, bsp_island)
	
	u_scale = scale[0]
	v_scale = scale[1]
	u_offset = offset[0]
	v_offset = offset[1]
	
	#Convert scale and offset from VMF convention to MAP convention
	#see also: pmt::pmt_map_uv_load
	if True:
		#map_scale = 1.0 / vmf_scale
		u_scale = 1.0 / u_scale
		v_scale = 1.0 / v_scale
		
		u_scale /= texture_size[0]
		v_scale /= texture_size[1]
		
		#map uv_offset is [0, 1], vmf is in pixels
		u_offset /= texture_size[0]
		v_offset /= texture_size[1]

	#a = ([u_scale * math.cos(radians), -v_scale * math.sin(radians), u_offset],
	#     [u_scale * math.sin(radians), v_scale * math.cos(radians), v_offset],
	#     [0.0, 0.0, 1.0])
	#A = hou.Matrix3(a)
	a_row0 = (u_scale * math.cos(rotation_radians), -v_scale * math.sin(rotation_radians), u_offset)
	a_row1 = (u_scale * math.sin(rotation_radians), v_scale * math.cos(rotation_radians), v_offset)
	#a_row2 = (0.0, 0.0, 1.0)
			
	u_str = "( {0} {1} {2} )".format( FloatUVStr(a_row0[0]), FloatUVStr(a_row0[1]), FloatUVStr(a_row0[2]) )
	v_str = "( {0} {1} {2} )".format( FloatUVStr(a_row1[0]), FloatUVStr(a_row1[1]), FloatUVStr(a_row1[2]) )

	plane_str = ""
	plane_str += "({0} {1} {2} {3})".format( FloatUVStr(n[0]), FloatUVStr(n[1]), FloatUVStr(n[2]), FloatUVStr(distance) )
	plane_str += " ( {0} {1} ) \"{2}\" 0 0 0".format(u_str, v_str, material) + NEWLINE
	return plane_str
	
def Matrix3Str(rotation = [1,0,0, 0,1,0, 0,0,1]):
	MATRIX_SIZE = len(rotation)
	rotation_str = ""
	for i in range(MATRIX_SIZE):
		rotation_str += "{0}".format(FloatUVStr(rotation[i]))
		if i < MATRIX_SIZE - 1:
			rotation_str += " "
	return rotation_str
	
class MapExport:
	def __init__(self):
		self.primitive_id = 0
		self.entity_id = 1		#worldspawn == id 0
	
	def get_primitive_id(self):
		id_out = self.primitive_id
		self.primitive_id += 1
		return str(id_out)
	def get_entity_id(self):
		id_out = self.entity_id
		self.entity_id += 1
		return str(id_out)

	#Call before any other functions
	def export_map_start(self, levelprops_class, levelprops_kv):
		out = ""
		out += LINS(0, "Version 2")
		out += LINS(0, "// entity 0")
		out += LINS(0, "{")
		if levelprops_class != None and levelprops_kv != None:
			out += LINE(0, "classname", levelprops_class)
			for key in levelprops_kv:
				value = levelprops_kv[key]
				out += LINE(0, key, value)
		else:
			out += LINE(0, "classname", "worldspawn")
			out += LINE(0, "editor_drLastCameraPos", "-300 0 0")
			out += LINE(0, "editor_drLastCameraAngle", "0 0 0")
		return out
		
	#Call after finished calling export_solid()
	def export_map_end(self):
		out = ""
		out += LINS(0, "}")
		return out
	
	def export_solid(self, solid):
		out = ""
		
		out += LINS(0, "// primitive " + self.get_primitive_id()) #todo: reset prim_id to 0 per entity?
		out += LINS(0, "{")
		out += LINS(0, "brushDef3")
		out += LINS(0, "{")
		for side in solid.sides:
			final_material = "textures/common/clip"
			if side.material_str != None:
				final_material = side.material_str
			out += PlaneStr(side.normal, side.distance, final_material, side.uv_data, side.texture_size, side.primidx, solid.bsp_island)
		out += LINS(0, "}")
		out += LINS(0, "}")
			
		return out
	
	def export_patch(self, patch):
		is_patchdef3 = patch.is_patchdef3()
	
		final_material = "textures/common/clip"
		if patch.material_str != None:
			final_material = patch.material_str
	
		out = ""
		out += LINS(0, "// primitive " + self.get_primitive_id())
		out += LINS(0, "{")
		out += LINS(0, "patchDef3" if is_patchdef3 else "patchDef2")
		out += LINS(0, "{")
		out += LINS(0, "\"{0}\"".format(final_material))
		if is_patchdef3:
			out += LINS(0, "( {0} {1} {2} {3} 0 0 0 )".format(patch.width, patch.height, patch.width_subdivisions, patch.height_subdivisions))
		else:
			out += LINS(0, "( {0} {1} 0 0 0 )".format(patch.width, patch.height))
		out += LINS(0, "(")
		for width_index in range(patch.width):
			patch_str = ""
			patch_str += "( "
			height_start = width_index * patch.height
			for height_index in range(patch.height):
				v = patch.vertices[height_start + height_index]
				v_str = (FloatUVStr(v[0]), FloatUVStr(v[1]), FloatUVStr(v[2]), FloatUVStr(v[3]), FloatUVStr(v[4]))
				patch_str += "( "
				patch_str += "{0} {1} {2} {3} {4}".format(v_str[0], v_str[1], v_str[2], v_str[3], v_str[4])
				patch_str += " )"
			patch_str += ")"
			out += LINS(0, patch_str)
		out += LINS(0, ")")
		out += LINS(0, "}")
		out += LINS(0, "}")
		return out
		
	def export_entity(self, keyvalue_dict, brushes = None, patches = None):
		entity_id_str = self.get_entity_id()
	
		classname = keyvalue_dict["classname"]
	
		if classname == "func_static":
			if "name" not in keyvalue_dict:
				keyvalue_dict["name"] = classname + "_" + entity_id_str
				
			if "model" not in keyvalue_dict:
				keyvalue_dict["model"] = keyvalue_dict["name"]
		else:
			if "name" not in keyvalue_dict:
				keyvalue_dict["name"] = classname + "_" + entity_id_str
			
		out = ""
		out += LINS(0, "// entity " + entity_id_str)
		out += LINS(0, "{")
		for key in keyvalue_dict:
			value = keyvalue_dict[key]
			out += LINE(0, key, value)
			
		if brushes != None:
			for brush in brushes:
				out += self.export_solid(brush)
		if patches != None:
			for patch in patches:
				out += self.export_patch(patch)
			
		out += LINS(0, "}")
		return out
		
	def export_point_entity(self, classname = None, kv_attrib_dict = None, location = None, rotation_euler = None):
	
		keyvalue_dict = dict()
		keyvalue_dict["classname"] = classname
		keyvalue_dict["origin"] = FloatStr(location[0]) + " " + FloatStr(location[1]) + " " + FloatStr(location[2])
		
		if rotation_euler != None:
			#	todo: check rotate order -- might be zyx ('yaw pitch roll')
			rotation = hou.Quaternion()
			rotation.setToEulerRotates(rotation_euler, rotate_order = "xyz") #fails to rotate to X-
			rotation_matrix = rotation.extractRotationMatrix3().asTuple()
			keyvalue_dict["rotation"] = Matrix3Str(rotation_matrix)
			
		if kv_attrib_dict != None:
			for key in kv_attrib_dict:
				value = kv_attrib_dict[key]
				assert key.lower() not in pmt_common.PMT_MAP_ENTITY_RESTRICTED_KEYVALUES, CCF(self, CF()) + " error: restricted key of keyvalue: {}(={})".format(key, value)
				keyvalue_dict[key] = value
				
		return self.export_entity(keyvalue_dict)

	def export_brush_entity(self, brushentity):
		num_brushes = len(brushentity.brushes)
		if num_brushes <= 0:
			return ""
			
		#assume that all brushes and prims of this brush entity have the same class and keyvalue dict
		ref_brush = brushentity.brushes[0]
		keyvalue_dict = ref_brush.entity_keyvalues_dict
		
		classname = ref_brush.entity_class
		keyvalue_dict["classname"] = classname
		
		origin = brushentity.origin
		origin_str = "{} {} {}".format(FloatUVStr(origin[0]), FloatUVStr(origin[1]), FloatUVStr(origin[2]))
		keyvalue_dict["origin"] = origin_str
			
		return self.export_entity(keyvalue_dict, brushentity.brushes)
		
	def export_patch_entity(self, patch_entity):
		keyvalue_dict = patch_entity.entity_keyvalues_dict
		classname = patch_entity.entity_class
		keyvalue_dict["classname"] = classname
		
		origin = hou.Vector3(0,0,0)
		for (x,y,z,u,v) in patch_entity.vertices:
			origin += hou.Vector3(x,y,z)
		origin /= float(len(patch_entity.vertices))
		origin_str = "{} {} {}".format(FloatUVStr(origin[0]), FloatUVStr(origin[1]), FloatUVStr(origin[2]))
		keyvalue_dict["origin"] = origin_str
		
		patch_entities = list()
		patch_entities.append(patch_entity)
		return self.export_entity(keyvalue_dict, None, patch_entities)
		
	
@pmt_common.HOUPROFILE_EVENT_DECO
def perform_export(node, map_export_path):
	N = node
	G = N.geometry()
	assert G != None, "map export: node at {} has no geometry".format(N.path())
	
	levelprops_class_attrib = G.findGlobalAttrib(pmt_common.PMT_MAP_LEVELPROPS_CLASS)
	levelprops_kv_attrib = G.findGlobalAttrib(pmt_common.PMT_MAP_LEVELPROPS_KEYVALUES)
	
	levelprops_class = None
	levelprops_kv = None
	if levelprops_class_attrib != None and levelprops_kv_attrib != None:
		levelprops_class = G.attribValue(levelprops_class_attrib)
		levelprops_kv = G.attribValue(levelprops_kv_attrib)
		
	### Load brushes
	def convert_houdini_prims_to_map_geo(geometry):
		print(CURFUNC(CF()))
				
		def prim_to_side(prim, has_brush_uv, texture_size_attrib, material_path = None):
			n = prim.normal()
			
			verts = list()
			for v in prim.vertices():
				verts.append( -v.point().position() )		#Note inverse position, this is needed to get brushes to line up with entities
		
			v0 = verts[0]
			halfspace = Side()
			halfspace.normal = (n.x(), n.y(), n.z())
			halfspace.distance = n.x() * v0.x() + n.y() * v0.y() + n.z() * v0.z()
		
			if material_path != None:
				halfspace.material_str = material_path
			if has_brush_uv:
				halfspace.uv_data = pmt_common.extract_uv_data(prim)
			if texture_size_attrib != None:
				halfspace.texture_size = prim.attribValue(texture_size_attrib)
			
			halfspace.vertices = verts
			
			return halfspace
						
		def prim_to_patch(prim, patch_uvs = None, material_path = None, is_patchdef3 = False, is_entity = False):
			assert prim.type() == hou.primType.BezierSurface, CURFUNC(CF()) + ": error - prim is not hou.primType.BezierSurface"
			
			columns = prim.numCols()
			rows = prim.numRows()
			if is_patchdef3:
				columns_subdivs = prim.attribValue(pmt_common.PMT_MAP_PATCHDEF3_WIDTH_SUBDIVS)
				rows_subdivs = prim.attribValue(pmt_common.PMT_MAP_PATCHDEF3_HEIGHT_SUBDIVS)
			
			patch = PatchDef()
			patch.width = columns
			patch.height = rows
			if is_patchdef3:
				patch.width_subdivisions = columns_subdivs
				patch.height_subdivisions = rows_subdivs
			
			
			for v_index in range(rows):
				for u_index in range(columns):
					vertex = prim.vertex(u_index, v_index)
					p = vertex.point().position()

					if patch_uvs != None:
						vertex_idx = vertex.linearNumber()
						uv_offset = vertex_idx * 3
						patch_uv = patch_uvs[uv_offset:uv_offset+3]
						uv = hou.Vector3(patch_uv)
					else:
						u = float(u_index) / float(columns - 1)
						v = float(v_index) / float(rows - 1)
						uv = hou.Vector3((u, v, 0))
					patch.vertices.append( (p.x(),p.y(),p.z(), uv.x(),uv.y()) )
			#patch.reverse()
			
			if material_path != None:
				patch.material_str = material_path
				
			if is_entity:
				patch.entity_class = prim.attribValue(pmt_common.PMT_MAP_ENTITY_CLASS)
				patch.entity_keyvalues_dict = prim.dictAttribValue(pmt_common.PMT_MAP_ENTITY_KEYVALUES)
			
			return patch
			
		materials = geometry.primStringAttribValues(pmt_common.PMT_MAP_MATERIAL) if geometry.findPrimAttrib(pmt_common.PMT_MAP_MATERIAL) != None else None
		has_brush_uv = pmt_common.houdini_geometry_has_uv_data(geometry)
		patch_uvs = geometry.vertexFloatAttribValues("uv") if geometry.findVertexAttrib("uv") != None else None
		texture_size_attrib = geometry.findPrimAttrib(pmt_common.PMT_MAP_TEXTURE_SIZE)
		
		bsp_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_BSP_ISLAND)
		entity_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_ENTITY_ISLAND)
		geometry_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOMETRY_PRIM)
		geotype_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOTYPE_PRIM)
		assert bsp_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_BSP_ISLAND)
		assert entity_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_ENTITY_ISLAND)
		assert geometry_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOMETRY_PRIM)
		assert geotype_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOTYPE_PRIM)
		
		entity_class_attrib = geometry.findPrimAttrib(pmt_common.PMT_MAP_ENTITY_CLASS)
		entity_kv_attrib = geometry.findPrimAttrib(pmt_common.PMT_MAP_ENTITY_KEYVALUES)
		
		entity_classes = geometry.primStringAttribValues(pmt_common.PMT_MAP_ENTITY_CLASS) if entity_class_attrib != None else None
		
		bsp_islands = geometry.primIntAttribValues(pmt_common.PMT_BSP_ISLAND)
		entity_islands = geometry.primIntAttribValues(pmt_common.PMT_ENTITY_ISLAND)
		geotypes = geometry.primStringAttribValues(pmt_common.PMT_GEOTYPE_PRIM)
		
		all_brushes = list()
		patchdefs = list()
		patch_entities = list()
		
		prims = geometry.prims()
		num_prims = len(prims)
		prev_bsp_island = None
		for prim_index in range(num_prims):
			if (prim_index % 1000) == 0:
				print("prim: {0} / {1}".format(prim_index, num_prims))
		
			prim = prims[prim_index]
			geotype = geotypes[prim_index]
			material_path = materials[prim_index] if materials != None else None
			
			if prim.type() != hou.primType.Polygon:
				if prim.type() == hou.primType.BezierSurface:
					is_patch_entity = False
					if entity_classes != None:
						classname = entity_classes[prim_index]
						is_patch_entity = len(classname) != 0 and classname != pmt_common.PMT_NONE
				
					is_patchdef2 = geotype == pmt_common.PMT_PATCHDEF2_GROUP
					is_patchdef3 = geotype == pmt_common.PMT_PATCHDEF3_GROUP
					if is_patchdef2 or is_patchdef3:
						patch = prim_to_patch(prim, patch_uvs, material_path, is_patchdef3, is_patch_entity)
						if not is_patch_entity:
							patchdefs.append(patch)
						else:
							patch_entities.append(patch)
				continue
			
			is_bsp = geotype == pmt_common.PMT_BSP_GROUP
			is_bspdetail = geotype == pmt_common.PMT_BSPDETAIL_GROUP
			is_bspentity = geotype == pmt_common.PMT_BSPENTITY_GROUP
			is_brushentity = is_bspdetail or is_bspentity
			
			if not (is_bsp or is_brushentity):
				continue
				
			bsp_island = bsp_islands[prim_index]
			entity_island = entity_islands[prim_index]
			
			is_new_bsp_island = bsp_island != prev_bsp_island
			if is_new_bsp_island:
				convex = BrushDef3()
				all_brushes.append(convex)
				all_brushes[-1].bsp_island = bsp_island
				
				if is_brushentity:
					if is_bspdetail:
						all_brushes[-1].entity_class = "func_static"
						all_brushes[-1].entity_keyvalues_dict = dict()
					elif is_bspentity:
						classname = prim.attribValue(pmt_common.PMT_MAP_ENTITY_CLASS)
						kv_dict = prim.dictAttribValue(pmt_common.PMT_MAP_ENTITY_KEYVALUES)
					
						if len(classname) != 0 and classname != pmt_common.PMT_NONE:
							all_brushes[-1].entity_class = classname
							all_brushes[-1].entity_keyvalues_dict = kv_dict
					all_brushes[-1].entity_island = entity_island
				else:
					all_brushes[-1].entity_island = None
				
			halfspace = prim_to_side(prim, has_brush_uv, texture_size_attrib, material_path)
			halfspace.primidx = prim_index
			all_brushes[-1].sides.append(halfspace)
			prev_bsp_island = bsp_island
		
		return all_brushes, patchdefs, patch_entities
	all_brushes, patchdefs, patch_entities = convert_houdini_prims_to_map_geo(G)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def separate_brushes_and_collect_brushentities(all_brushes):
		world_brushes = list()
		all_brushentities = list()
		num_brushes = len(all_brushes)
		for brush_index in range(num_brushes):
			brush = all_brushes[brush_index]
			if brush.entity_island == None:
				world_brushes.append(brush)
			else:
				is_new_entity_island = True if brush_index == 0 else brush.entity_island != all_brushes[brush_index - 1].entity_island
				if is_new_entity_island:
					brushentity = BrushEntity()
					all_brushentities.append(brushentity)
				all_brushentities[-1].brushes.append(brush)
		return world_brushes, all_brushentities
		
	world_brushes, all_brushentities = separate_brushes_and_collect_brushentities(all_brushes)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def compute_brushentity_centers(all_brushentities):
	
		@pmt_common.HOUPROFILE_EVENT_DECO
		def adjust_brushentity_planes(brushentity):
			num_verts = 0
			avg_position = hou.Vector3((0,0,0))
			
			for brush in brushentity.brushes:
				for side in brush.sides:
					num_verts += len(side.vertices)
					for v in side.vertices:
						avg_position += v
			center = avg_position / num_verts
			center = -center 	#Note inverse position
			
			num_brushes = len(brushentity.brushes)
			for brush_index in range(num_brushes):
				brush = brushentity.brushes[brush_index]
				num_sides = len(brush.sides)
				for side_index in range(num_sides):
					normal = hou.Vector3(brush.sides[side_index].normal)
					brush.sides[side_index].distance += normal.dot(center)
			
			brushentity.origin = center
			#brushentity.origin = hou.Vector3((0,0,0))
			return brushentity
		num_brushentities = len(all_brushentities)
		for i in range(num_brushentities):
			all_brushentities[i] = adjust_brushentity_planes(all_brushentities[i])
		return all_brushentities
	all_brushentities = compute_brushentity_centers(all_brushentities)
	
	exporter = MapExport()
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def extract_point_entities(exporter, geometry):
		print(CURFUNC(CF()))
		
		entity_points = geometry.findPointGroup(pmt_common.PMT_ENTITY)
		if entity_points == None:
			return ""
			
		entity_str = ""
		for point in entity_points.points():
			p = point.position()
			p_tuple = (p.x(), p.y(), p.z())
			
			classname = point.attribValue(pmt_common.PMT_MAP_ENTITY_CLASS)
			if len(classname) == 0 or classname == pmt_common.PMT_NONE:
				continue
				
			keyvalue_dict = point.dictAttribValue(pmt_common.PMT_MAP_ENTITY_KEYVALUES)
			rotation_euler_enabled = point.attribValue(pmt_common.PMT_HAS_EULER_ROTATION)
			rotation_euler = point.attribValue(pmt_common.PMT_MAP_ROTATION_EULER) if rotation_euler_enabled else None
			
			entity_str += exporter.export_point_entity(classname, keyvalue_dict, p_tuple, rotation_euler)
		return entity_str
	entity_str = extract_point_entities(exporter, G)			
	
	### Main export
	file_out = open(map_export_path, 'w')
	file_out.write( exporter.export_map_start(levelprops_class, levelprops_kv) )
	
	print("writing {} world brushes".format(len(world_brushes)))
	for brush in world_brushes:
		file_out.write( exporter.export_solid(brush) )
	
	print("writing {} world patches".format(len(patchdefs)))
	for patch in patchdefs:
		file_out.write( exporter.export_patch(patch) )
		
	file_out.write( exporter.export_map_end() )
	
	print("writing {} brush entities".format(len(all_brushentities)))
	for brushentity in all_brushentities:
		file_out.write( exporter.export_brush_entity(brushentity) )
		
	print("writing {} patch entities".format(len(patch_entities)))
	for patchentity in patch_entities:
		file_out.write( exporter.export_patch_entity(patchentity) )
	
	#Entity
	file_out.write( entity_str )
	
	#
	file_out.close()
	print(".map written to {}".format(map_export_path))
	

def main_export(node, map_export_path):
	profile = pmt_common.HOUPROFILE("map_export_path")
	perform_export(node, map_export_path)
