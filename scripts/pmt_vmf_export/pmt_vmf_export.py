#!/usr/bin/env python3
#	node               : 	pmt::pmt_vmf_export
#	script_section_name: 	pmt_vmf_export.py

###__pmt::pmt__globalconfig__COMMON_SECTION__
if True:
	import hou
	main_module = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt__global_config = main_module.pmt__global_config
	pmt_common = main_module.pmt_common
	pmt_material_select = main_module.pmt_material_select
	pmt_parse_source1_fgd = main_module.pmt_parse_source1_fgd
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



class DispInfo:
	def __init__(self):
		self.power = 0							#int [2, 4]; size of lists depends on power
		self.start_position = (0.0, 0.0, 0.0)	#min point of side of solid
		
		self.normals_num_columns = 0
		self.normals_num_rows = 0
		self.distances_num_columns = 0
		self.distances_num_rows = 0
		self.triangle_tags_num_columns = 0
		self.triangle_tags_num_rows = 0
		
		#Contains floats only, length depends on power
		#Stored as rows, then columns(if power == 3, then distances[81], and distances[0:8] are the first row)
		self.normals = list()				#2: 15 x 5 rows		3: 27 x 9 rows		4: 51 x 17 rows
		self.distances = list()				#2: 5 x 5 rows		3: 9 x 9 rows		4: 17 x 17 rows	
		self.offsets = list()				#2: 15 x 5 rows		3: 27 x 9 rows		4: 51 x 17 rows
		self.offset_normals = list()		#2: 15 x 5 rows		3: 27 x 9 rows		4: 51 x 17 rows	
		self.alphas = list()				#2: 5 x 5 rows		3: 9 x 9 rows		4: 17 x 17 rows
		self.triangle_tags = list()			#2: 8 x 4 rows		3: 16 x 8 rows		4: 32 x 16 rows
		#self.allowed_verts = list()		#10 entries, default -1

	def setup(self, power):
		self.power = power
	
		if power == 2:
			self.normals_num_columns = (power * power + 1) * 3
			self.normals_num_rows = (power * power + 1)
			self.distances_num_columns = power * power + 1
			self.distances_num_rows = power * power + 1
			self.triangle_tags_num_columns = 2 * (2 ** power)
			self.triangle_tags_num_rows = power * power
		if power == 3:
			#normals, offsets, offset_normals
			self.normals_num_columns = power * power * 3
			self.normals_num_rows = power * power
			
			#distances, alphas
			self.distances_num_columns = power * power
			self.distances_num_rows = power * power
			
			#triangle_tags
			self.triangle_tags_num_columns = 2 * (2 ** power)
			self.triangle_tags_num_rows = power * power - 1
		if power == 4:
			self.normals_num_columns = (power * power + 1) * 3
			self.normals_num_rows = (power * power + 1)
			self.distances_num_columns = power * power + 1
			self.distances_num_rows = power * power + 1
			self.triangle_tags_num_columns = 2 * (2 ** power)
			self.triangle_tags_num_rows = power * power
		
		num_normals = self.get_num_normals()
		num_distances = self.get_num_distances()
		num_triangle_tags = self.get_num_triangle_tags()
		
		#
		for i in range(num_normals):
			self.normals += [0, 0, 0]
		for i in range(num_normals):
			self.offsets += [0, 0, 0]
		for i in range(num_normals):
			self.offset_normals += [0, 0, 1]
			
		for i in range(num_distances):
			self.distances.append(0)
		for i in range(num_distances):
			self.alphas.append(0.0)
			
		for i in range(num_triangle_tags):
			self.triangle_tags.append(9)	#9: No slope, walkable; 1: Slope, walkable, 0: Non-walkable
	
	def get_num_normals(self):
		return self.normals_num_rows * self.normals_num_columns
	def get_num_distances(self):
		return self.distances_num_rows * self.distances_num_columns
	def get_num_triangle_tags(self):
		return self.triangle_tags_num_rows * self.triangle_tags_num_columns
	
#A plane defined by 3 points
class Side:
	def __init__(self):
		self.prim_index = None
		self.bsp_island = None
		self.a = (0.0, 0.0, 0.0)
		self.b = (0.0, 0.0, 0.0)
		self.c = (0.0, 0.0, 0.0)
		self.uv_normal = (0.0, 0.0, 0.0)	#Not necessarily pointing in the same direction as the actual surface normal
		self.dispinfo = None
		self.material_str = None
		self.uv_data = None
		self.texture_size = None
		
		self.vertices = list()
	
#A convex solid defined by the intersections of multiple halfspaces(planes)
class Solid:
	def __init__(self):
		self.sides = list()
		self.source_prims = list()				#hou.Prim; original prims used to form each side
		
		self.entity_island = None
		self.entity_class = None
		self.entity_keyvalues_dict = None

#An entity composed of multiple solid brushes.
#We assume that all keyvalues of the solids are the same, 
#so we can get the keyvalues by looking at entity_keyvalues_list of solids[0].
class BrushEntity:
	def __init__(self):
		self.solids = list()
		
		
#converts float -> int -> string
def FloatStr(float_value):
	#return str( int( round(float_value) ) )
	return str( int(float_value) )
	
#converts float -> string
def FloatUVStr(float_value):
	#return str(float_value)
	return '{0:0=.6f}'.format(float_value)
	
def DispInfoColumnStr(value_list, num_columns, row_index, float_str_convert = FloatUVStr):
	column_str = ""
	for column in range(num_columns):
		list_index = row_index * num_columns + column
		column_str += float_str_convert(value_list[list_index])
		if column < num_columns - 1:
			column_str += " " 
	return column_str
	
def PlaneStr(a, b, c, float_to_str = FloatUVStr):
	plane_str = ""
	plane_str += "(" + float_to_str(a[0]) + " " + float_to_str(a[1]) + " " + float_to_str(a[2]) + ")"
	plane_str += " "
	plane_str += "(" + float_to_str(b[0]) + " " + float_to_str(b[1]) + " " + float_to_str(b[2]) + ")"
	plane_str += " "
	plane_str += "(" + float_to_str(c[0]) + " " + float_to_str(c[1]) + " " + float_to_str(c[2]) + ")"
	return plane_str
		
class VmfExport:
	def __init__(self):
		self.solid_id = 2		#World is id == 1, so start at 2 (also used for entities)
		self.side_id = 1
	
	def get_solid_id(self):
		id_out = self.solid_id
		self.solid_id += 1
		return str(id_out)
	def get_side_id(self):
		id_out = self.side_id
		self.side_id += 1
		return str(id_out)

	#Call before any other functions
	def export_vmf_start(self):
		out = ""
		out += LINS(0, "versioninfo")
		out += LINS(0, "{")
		out += LINE(1, "editorversion", "400")
		out += LINE(1, "editorbuild", "6157")
		out += LINE(1, "mapversion", "172")
		out += LINE(1, "formatversion", "100")
		out += LINE(1, "prefab", "0")
		out += LINS(0, "}")
		out += LINS(0, "visgroups")
		out += LINS(0, "{")
		out += LINS(0, "}")
		out += LINS(0, "viewsettings")
		out += LINS(0, "{")
		out += LINE(1, "bSnapToGrid", "0")
		out += LINE(1, "bShowGrid", "1")
		out += LINE(1, "bShowLogicalGrid", "0")
		out += LINE(1, "nGridSpacing", "64")
		out += LINE(1, "bShow3DGrid", "0")
		out += LINS(0, "}")
		return out
		
	#Call after all other functions
	def export_vmf_end(self):
		out = ""
		out += LINS(0, "cameras")
		out += LINS(0, "{")
		out += LINE(1, "activecamera", "-1")
		out += LINS(0, "}")
		out += LINS(0, "cordon")
		out += LINS(0, "{")
		out += LINE(1, "mins", "(-1024 -1024 -1024)")
		out += LINE(1, "maxs", "(1024 1024 1024)")
		out += LINE(1, "active", "0")
		out += LINS(0, "}")
		return out

	#Call before export_solid()
	def export_world_start(self, levelprops_class, levelprops_kv):
		out = ""
		out += LINS(0, "world")
		out += LINS(0, "{")
		out += LINE(1, "id", "1")
		out += LINE(1, "mapversion", "172")
		if levelprops_class != None and levelprops_kv != None:
			out += LINE(1, "classname", levelprops_class)
			for key in levelprops_kv:
				value = levelprops_kv[key]
				out += LINE(1, key, value)
		else:
			out += LINE(1, "classname", "worldspawn")
			out += LINE(1, "detailmaterial", "detail/detailsprites")
			out += LINE(1, "detailvbsp", "detail.vbsp")
			out += LINE(1, "maxpropscreenwidth", "-1")
			out += LINE(1, "skyname", "sky_day01_01")
		return out
	#Call after export_solid()
	def export_world_end(self):
		return LINS(0, "}")
	
	def export_solid(self, solid):
		out = ""
		out += LINS(1, "solid")
		out += LINS(1, "{")
		out += LINE(2, "id", self.get_solid_id())
		for side in solid.sides:
			out += self.export_side(side)
		#out += LINS(2, "editor")
		#out += LINS(2, "{")
		#out += LINE(3, "color", "0 130 167")
		#out += LINE(3, "visgroupshown", "1")
		#out += LINE(3, "visgroupautoshown", "1")
		#out += LINS(2, "}")
		out += LINS(1, "}")
		
		return out
		
	def export_side(self, side):
		n = side.uv_normal
		uv = pmt_common.btPlaneSpace1( (n[0], n[1], n[2]) )
		if uv == None:
			raise hou.NodeError(CCF(self, CF()) + " error: side has zero length normal. (prim_index={}, bsp_island={})".format(side.prim_index, side.bsp_island))
		u, v = uv
		texture_size = side.texture_size
		
		final_material = "DEV/DEV_MEASUREICE01"
		if side.material_str != None:
			final_material = side.material_str
		
		LIGHT_MAP_SCALE = 64	#Default 16; world units/luxel; value too low will cause vrad.exe to crash for large maps
			
		#offset: 
		#	offset in pixels (depends on image size -- 50% offset is 128 for 256^2 texture; 512 for 1024^1024 texture)
		#	not affected by size of brush/prim
		#scale:
		#	pixels per hammer unit? (for a 256 x 256 Hammer unit brush, a scale of 1 fits a 256^2 texture exactly)
		#	1 corresponds to a 128x128 image?
		#	not affected by size of brush/prim
		
		offset = (0, 0)
		scale = (0.25, 0.25)
		
		#Approach #2: axis, scale, offset are explicitly specified and mesh uvs are computed only for visualization
		if side.uv_data != None:
			u = side.uv_data.vmf_uv_u_axis
			v = side.uv_data.vmf_uv_v_axis
			scale = side.uv_data.vmf_uv_scale
			offset = side.uv_data.vmf_uv_offset
				
		out = ""
		out += LINS(2, "side")
		out += LINS(2, "{")
		out += LINE(3, "id", self.get_side_id())
		out += LINE(3, "plane", PlaneStr(side.a, side.b, side.c))
		out += LINE(3, "material", final_material)
		out += LINE(3, "uaxis", "[" + FloatUVStr(u[0]) + " " + FloatUVStr(u[1]) + " " + FloatUVStr(u[2]) + " " + FloatUVStr(offset[0]) + "] " + FloatUVStr(scale[0]))
		out += LINE(3, "vaxis", "[" + FloatUVStr(v[0]) + " " + FloatUVStr(v[1]) + " " + FloatUVStr(v[2]) + " " + FloatUVStr(offset[1]) + "] " + FloatUVStr(scale[1]))
		out += LINE(3, "rotation", "0")
		out += LINE(3, "lightmapscale", FloatStr(LIGHT_MAP_SCALE))
		out += LINE(3, "smoothing_groups", "0")
		if side.dispinfo != None:
			out += self.export_dispinfo(side.dispinfo)
		out += LINS(2, "}")
		return out
	
	def export_dispinfo(self, dispinfo):
		DI = dispinfo
	
		origin = DI.start_position
		#origin = (0,0,0)
		out = ""
		out += LINS(3, "dispinfo")
		out += LINS(3, "{")
		out += LINE(4, "power", str(DI.power))
		out += LINE(4, "startposition", "[" + FloatStr(origin[0]) + " " + FloatStr(origin[1]) + " " + FloatStr(origin[2]) + "]")
		out += LINE(4, "flags", "0")
		out += LINE(4, "elevation", "0")
		out += LINE(4, "subdiv", "0")
		out += LINS(4, "normals")
		out += LINS(4, "{")
		for row_index in range(DI.normals_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.normals, DI.normals_num_columns, row_index))
		out += LINS(4, "}")
		out += LINS(4, "distances")
		out += LINS(4, "{")
		for row_index in range(DI.distances_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.distances, DI.distances_num_columns, row_index))
		out += LINS(4, "}")
		out += LINS(4, "offsets")
		out += LINS(4, "{")
		for row_index in range(DI.normals_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.offsets, DI.normals_num_columns, row_index))
		out += LINS(4, "}")
		out += LINS(4, "offset_normals")
		out += LINS(4, "{")
		for row_index in range(DI.normals_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.offset_normals, DI.normals_num_columns, row_index))
		out += LINS(4, "}")
		out += LINS(4, "alphas")
		out += LINS(4, "{")
		for row_index in range(DI.distances_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.alphas, DI.distances_num_columns, row_index))
		out += LINS(4, "}")
		out += LINS(4, "triangle_tags")
		out += LINS(4, "{")
		for row_index in range(DI.triangle_tags_num_rows):
			out += LINE(5, "row" + str(row_index), DispInfoColumnStr(DI.triangle_tags, DI.triangle_tags_num_columns, row_index, FloatStr))
		out += LINS(4, "}")
		out += LINS(4, "allowed_verts")
		out += LINS(4, "{")
		out += LINE(5, "10", "-1 -1 -1 -1 -1 -1 -1 -1 -1 -1")
		out += LINS(4, "}")
		out += LINS(3, "}")
		return out
		
	#Entities follow brushes (call export_entity_* after export_solid)
	def export_entity(self, keyvalue_dict = None, connections = None, solids = None):
		out = ""
		out += LINS(0, "entity")
		out += LINS(0, "{")
		out += LINE(1, "id", self.get_solid_id())
		
		if keyvalue_dict != None:
			for key in keyvalue_dict:
				assert type(keyvalue_dict[key]) == type(""), CCF(self, CF()) + ": key '{}' value '{}' is not str".format(key, keyvalue_dict[key])
				out += LINE(1, key, keyvalue_dict[key])
		
		#connections is a list of strings, each set of 6 strings is one connection
		if connections != None:
			num_connections = len(connections) // 6
			out += LINS(1, "connections")
			out += LINS(1, "{")
			for i in range(num_connections):
				output = connections[i*6]
				targetname = connections[i*6+1]
				input_name = connections[i*6+2]
				input_parm = connections[i*6+3]
				delay_seconds = connections[i*6+4]
				fire_once = connections[i*6+5]
				out += LINE(2, output, "{},{},{},{},{}".format(targetname, input_name, input_parm, delay_seconds, fire_once))
			out += LINS(1, "}")
		
		if solids != None:
			for solid in solids:
				out += self.export_solid(solid)
		
		out += LINS(0, "}")
		return out
		
	def export_point_entity(self, classname = "", kv_attrib_dict = None, location = None, rotation_xyz = None):
		key_value_dict = dict()
		connections = None
		
		key_value_dict["classname"] = classname
		
		if kv_attrib_dict != None:
			if pmt_common.PMT_CONNECTIONS in kv_attrib_dict:
				connections = kv_attrib_dict[pmt_common.PMT_CONNECTIONS]
				del kv_attrib_dict[pmt_common.PMT_CONNECTIONS];
		
			for key in kv_attrib_dict:
				value = kv_attrib_dict[key]
				assert key.lower() not in pmt_common.PMT_VMF_ENTITY_RESTRICTED_KEYVALUES, CCF(self, CF()) + " error: restricted key of keyvalue: {}(={})".format(key, value)
				key_value_dict[key] = value
		
		if location != None:
			key_value_dict["origin"] = "{0} {1} {2}".format( str(location[0]), str(location[1]), str(location[2]) )
		
		if rotation_xyz != None:
			pitch = rotation_xyz[1]
			yaw  = rotation_xyz[2]
			roll = rotation_xyz[0]
			key_value_dict["angles"] = "{0} {1} {2}".format(FloatUVStr(pitch), FloatUVStr(yaw), FloatUVStr(roll))		#Pitch Yaw Roll (Y Z X)
			
			#special case for light_spot entity, where angles[0] is ignored
			if classname.lower() == "light_spot" or classname.lower() == "light_dynamic":
				key_value_dict["pitch"] = FloatUVStr(pitch)
			
		return self.export_entity(key_value_dict, connections)
		
	def export_brush_entity(self, brushentity):
		if len(brushentity.solids) <= 0:
			return ""
	
		#Assume all entity_keyvalues_dict in brushentity.solids are the same for this brush entity
		solid0 = brushentity.solids[0]
		
		key_value_dict = dict()
		connections = None
		
		key_value_dict["classname"] = solid0.entity_class
		
		if solid0.entity_keyvalues_dict != None:
			if pmt_common.PMT_CONNECTIONS in solid0.entity_keyvalues_dict:
				connections = solid0.entity_keyvalues_dict[pmt_common.PMT_CONNECTIONS]
				del solid0.entity_keyvalues_dict[pmt_common.PMT_CONNECTIONS];
				
			for key in solid0.entity_keyvalues_dict:
				value = solid0.entity_keyvalues_dict[key]
				assert key.lower() not in pmt_common.PMT_VMF_ENTITY_RESTRICTED_KEYVALUES,CCF(self, CF()) + " error: restricted key of keyvalue: {}(={}) (pmt_entity_island={})".format(key, value, solid0.entity_island)
				key_value_dict[key] = value
				
		return self.export_entity(key_value_dict, connections, brushentity.solids)

@pmt_common.HOUPROFILE_EVENT_DECO
def perform_export(node_pmt_vmf_export, vmf_export_path):
	
	### Load brushes
	node = node_pmt_vmf_export
	geometry = node.geometry()
	assert geometry != None, "vmf export: node at {} has no geometry".format(node.path())
	
	levelprops_class_attrib = geometry.findGlobalAttrib(pmt_common.PMT_VMF_LEVELPROPS_CLASS)
	levelprops_kv_attrib = geometry.findGlobalAttrib(pmt_common.PMT_VMF_LEVELPROPS_KEYVALUES)
	
	levelprops_class = None
	levelprops_kv = None
	if levelprops_class_attrib != None and levelprops_kv_attrib != None:
		levelprops_class = geometry.attribValue(levelprops_class_attrib)
		levelprops_kv = geometry.attribValue(levelprops_kv_attrib)
		
	@pmt_common.HOUPROFILE_EVENT_DECO
	def convert_houdini_prims_to_brushes(geometry):
	
		@pmt_common.HOUPROFILE_EVENT_DECO		
		def prim_to_halfspace(prim, prim_index, bsp_island, texture_attrib, texture_size_attrib, has_uv, is_dispmap):
			n = prim.normal()
			
			@pmt_common.HOUPROFILE_EVENT_DECO
			def get_prim_vertices(prim):
				verts = list()
				verts_indices = list()
				for v in prim.vertices():
					verts.append( v.point().position() )
					verts_indices.append( v.number() )
				return verts, verts_indices
			verts, verts_indices = get_prim_vertices(prim)
			
			selected_verts = verts[0:3]
			
			v0 = selected_verts[0]
			v1 = selected_verts[1]
			v2 = selected_verts[2]
			halfspace = Side()
			halfspace.prim_index = prim_index
			halfspace.bsp_island = bsp_island
			halfspace.a = (v0.x(), v0.y(), v0.z())
			halfspace.b = (v1.x(), v1.y(), v1.z())
			halfspace.c = (v2.x(), v2.y(), v2.z())
			halfspace.uv_normal = (n.x(), n.y(), n.z())
				
			for v in prim.vertices():
				halfspace.vertices.append( v.point().position() )
				
			if texture_attrib != None:
				halfspace.material_str = prim.attribValue(texture_attrib)
			if texture_size_attrib != None:
				halfspace.texture_size = prim.attribValue(texture_size_attrib)
			if has_uv:
				halfspace.uv_data = pmt_common.extract_uv_data(prim)

			@pmt_common.HOUPROFILE_EVENT_DECO
			def extract_displacement_info2(prim):
				distances = prim.attribValue("pmt_dispinfo_distances")
				normals = prim.attribValue("pmt_dispinfo_normals")
				offset_normals = prim.attribValue("pmt_dispinfo_offset_normals")
				alphas = prim.attribValue("pmt_dispinfo_alphas")
				start_position_vtxidx = prim.attribValue("pmt_dispinfo_start_position_vtxidx")
				if True: #attempt to fix issue where dispmap breaks after translation(axis align) since start_position is not always moved
					start = prim.vertex(start_position_vtxidx).point().position()
					start_position = (start.x(), start.y(), start.z())
				else:
					start_position = prim.attribValue("pmt_dispinfo_start_position")
				power = prim.attribValue("pmt_dispinfo_power")
				
				dispinfo = DispInfo()
				dispinfo.setup(power)
				dispinfo.start_position = start_position
				
				for i in range(0, dispinfo.get_num_normals(), 3 ):
					dispinfo.normals[i] = normals[i]
					dispinfo.normals[i+1] = normals[i+1]
					dispinfo.normals[i+2] = normals[i+2]
				for i in range(0, dispinfo.get_num_normals(), 3 ):
					dispinfo.offset_normals[i] = offset_normals[i]
					dispinfo.offset_normals[i+1] = offset_normals[i+1]
					dispinfo.offset_normals[i+2] = offset_normals[i+2]
				for i in range( dispinfo.get_num_distances() ):
					dispinfo.distances[i] = distances[i]
				for i in range( dispinfo.get_num_distances() ):
					dispinfo.alphas[i] = alphas[i]
				return dispinfo
			halfspace.dispinfo = extract_displacement_info2(prim) if is_dispmap else None
			return halfspace
		
		has_uv = pmt_common.houdini_geometry_has_uv_data(geometry)
		texture_attrib = geometry.findPrimAttrib(pmt_common.PMT_VMF_MATERIAL)
		texture_size_attrib = geometry.findPrimAttrib(pmt_common.PMT_VMF_TEXTURE_SIZE)
		
		bsp_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_BSP_ISLAND)
		entity_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_ENTITY_ISLAND)
		geometry_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOMETRY_PRIM)
		geotype_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOTYPE_PRIM)
		assert bsp_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_BSP_ISLAND)
		assert entity_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_ENTITY_ISLAND)
		assert geometry_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOMETRY_PRIM)
		assert geotype_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOTYPE_PRIM)
		
		#bsp_group = geometry.findPrimGroup(pmt_common.PMT_BSP_GROUP)
		#bspdetail_group = geometry.findPrimGroup(pmt_common.PMT_BSPDETAIL_GROUP)
		#bspentity_group = geometry.findPrimGroup(pmt_common.PMT_BSPENTITY_GROUP)
		#dispmap_group = geometry.findPrimGroup(pmt_common.PMT_DISPLACEMENT_GROUP)
		
		all_brushes = list()
		
		prims = geometry.prims()
		num_prims = len(prims)
		prev_prim = None
		for prim_index in range(num_prims):
			if (prim_index % 1000) == 0:
				print("prim_index: {0} / {1}".format(prim_index, num_prims))
		
			prim = prims[prim_index]
			if prim.type() != hou.primType.Polygon:
				continue
			
			geotype = prim.attribValue(geotype_prim_attrib)
			
			is_bsp = geotype == pmt_common.PMT_BSP_GROUP
			is_bspdetail = geotype == pmt_common.PMT_BSPDETAIL_GROUP
			is_bspentity = geotype == pmt_common.PMT_BSPENTITY_GROUP
			is_dispmap = geotype == pmt_common.PMT_DISPLACEMENT_GROUP
			is_entity = is_bspdetail or is_bspentity
			
			if not (is_bsp or is_entity or is_dispmap):
				continue
			
			bsp_island = prim.attribValue(bsp_island_attrib)
			entity_island = prim.attribValue(entity_island_attrib)
			#is_pmt_geometry = prim.attribValue(geometry_prim_attrib)
			
			prev_bsp_island = prev_prim.attribValue(bsp_island_attrib) if (prev_prim != None) else None
			is_new_bsp_island = bsp_island != prev_bsp_island
			if is_new_bsp_island:
				convex = Solid()
				all_brushes.append(convex)
				
				if is_entity:
					#assume all prims assigned to this entity have same classname and keyvalues
					if is_bspdetail:
						all_brushes[-1].entity_keyvalues_dict = dict()
						all_brushes[-1].entity_class = "func_detail"
					elif is_bspentity:
						classname = prim.attribValue(pmt_common.PMT_VMF_ENTITY_CLASS)
						kv_attrib_dict = prim.dictAttribValue(pmt_common.PMT_VMF_ENTITY_KEYVALUES)
						#print("prim classname {0}".format(classname))
						#print("prim key_value_list {0}".format(key_value_list))
							
						entity_keyvalues_dict = dict()
						for key in kv_attrib_dict:
							value = kv_attrib_dict[key]
							entity_keyvalues_dict[key] = value
						
						if len(classname) != 0 and classname != pmt_common.PMT_NONE:
							all_brushes[-1].entity_keyvalues_dict = entity_keyvalues_dict
							all_brushes[-1].entity_class = classname
					all_brushes[-1].entity_island = entity_island
				else:
					all_brushes[-1].entity_island = None
				
			halfspace = prim_to_halfspace(prim, prim_index, bsp_island, texture_attrib, texture_size_attrib, has_uv, is_dispmap)
			all_brushes[-1].sides.append(halfspace)
			prev_prim = prim
			
		return all_brushes
	all_brushes = convert_houdini_prims_to_brushes(geometry)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def separate_brushes(all_brushes):
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
			
				all_brushentities[-1].solids.append(brush)
		
		detail_brushentities = list()
		entity_brushentities = list()
		for brushentity in all_brushentities:
			if len(brushentity.solids) == 0 or len(brushentity.solids[0].entity_class) == 0 or brushentity.solids[0].entity_class == pmt_common.PMT_NONE:
				continue
		
			if brushentity.solids[0].entity_class == "func_detail":
				detail_brushentities.append(brushentity)
			else:
				entity_brushentities.append(brushentity)
		
		return world_brushes, detail_brushentities, entity_brushentities
	brushes, detail_brushentities, entity_brushentities = separate_brushes(all_brushes)
	
	exporter = VmfExport()
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def export_brushes(exporter, brushes, detail_brushentities, entity_brushentities):
		BRUSHES_PER_PRINT = 250
	
		num_brushes_processed = 0
		num_brushes = len(brushes)
		bsp_str = ""
		for brush in brushes:
			if (num_brushes_processed % BRUSHES_PER_PRINT) == 0:
				print("brushes: {0} / {1}".format(num_brushes_processed, num_brushes))
			num_brushes_processed += 1
			bsp_str += exporter.export_solid(brush)
			
		num_detail_brushes_processed = 0
		num_detail_brushes = len(detail_brushentities)
		bspdetail_str = ""
		for brushentity in detail_brushentities:
			if (num_detail_brushes_processed % BRUSHES_PER_PRINT) == 0:
				print("detail_brushentities: {0} / {1}".format(num_detail_brushes_processed, num_detail_brushes))
			num_detail_brushes_processed += 1
			bspdetail_str += exporter.export_brush_entity(brushentity)
			
		num_entity_brushes_processed = 0
		num_entity_brushes = len(entity_brushentities)
		bspentity_str = ""
		for brushentity in entity_brushentities:
			if (num_entity_brushes_processed % BRUSHES_PER_PRINT) == 0:
				print("entity_brushentities: {0} / {1}".format(num_entity_brushes_processed, num_entity_brushes))
			num_entity_brushes_processed += 1
			bspentity_str += exporter.export_brush_entity(brushentity)
			
		return (exporter, bsp_str, bspdetail_str, bspentity_str)
	exporter, bsp_str, bspdetail_str, bspentity_str = export_brushes(exporter, brushes, detail_brushentities, entity_brushentities)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def export_point_entities(exporter, geometry):
		ENTITIES_PER_PRINT = 250
		
		entity_str = ""
		for pointGroup in geometry.pointGroups():
			if pointGroup.name() != pmt_common.PMT_ENTITY:
				continue
				
			num_point_entities = len(pointGroup.points())
			num_point_entities_exported = 0
			for point in pointGroup.points():
				p = point.position()
				p_tuple = (p.x(), p.y(), p.z())
				
				classname = point.attribValue(pmt_common.PMT_VMF_ENTITY_CLASS)
				if classname == "pmt_none":
					continue
				
				key_value_list = point.dictAttribValue(pmt_common.PMT_VMF_ENTITY_KEYVALUES)
				rotation_euler_enabled = point.attribValue(pmt_common.PMT_HAS_EULER_ROTATION)
				rotation_euler = point.attribValue(pmt_common.PMT_VMF_ROTATION_EULER) if rotation_euler_enabled else None
					
				#print("ent classname {0}".format(classname))
				#print("ent key_value_list {0}".format(key_value_list))
				entity_str += exporter.export_point_entity(classname, key_value_list, p_tuple, rotation_euler)
				
				if (num_point_entities_exported % ENTITIES_PER_PRINT) == 0:
					print("point_entities: {0} / {1}".format(num_point_entities_exported, num_point_entities))
				num_point_entities_exported += 1
				
		return exporter, entity_str
	exporter, entity_str = export_point_entities(exporter, geometry)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def write_file(exporter, bsp_str, bspdetail_str, bspentity_str, entity_str):
		file_out = open(vmf_export_path, 'w')
		file_out.write( exporter.export_vmf_start() )
		
		#world
		file_out.write( exporter.export_world_start(levelprops_class, levelprops_kv) )
		file_out.write(bsp_str)
		file_out.write( exporter.export_world_end() )
		
		#entity
		file_out.write(bspdetail_str)
		file_out.write(bspentity_str)
		file_out.write(entity_str)
		
		#
		file_out.write( exporter.export_vmf_end() )
		file_out.close()
	write_file(exporter, bsp_str, bspdetail_str, bspentity_str, entity_str)
	print(".vmf written to {}".format(vmf_export_path))
	
def main_export(node_pmt_vmf_export, vmf_export_path):
	profile = pmt_common.HOUPROFILE("pmt_export_vmf")
	perform_export(node_pmt_vmf_export, vmf_export_path)
	