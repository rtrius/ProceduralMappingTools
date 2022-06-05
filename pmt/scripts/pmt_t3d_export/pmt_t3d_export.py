#!/usr/bin/env python3
#	node               : 	pmt::pmt_t3d_export
#	script_section_name: 	pmt_t3d_export.py
#
# Important: must call 'Build -> Rebuild Geometry Only' in UnrealEd menu after importing .t3d
#

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
import functools
import copy

import inspect
CF = inspect.currentframe
def CURFUNC(inspect_currentframe): #return the name of the 'current function':  CURFUNC(CF())
	return inspect_currentframe.f_code.co_name
def CCF(self, inspect_currentframe, sep = "::", suffix = "()"): #return the name the the 'current class function': CCF(self, CF())
	return type(self).__qualname__ + sep + inspect_currentframe.f_code.co_name +  suffix


#We assume that all keyvalues of the polylists are the same, 
#so we can get the keyvalues by looking at entity_keyvalues_dict of polylists[0].
class MoverBrush:
	def __init__(self):
		self.polylists = list()
		
#A polylist here refers to a convex set of prims with the same pmt_bsp_island
class PolyList:
	def __init__(self):
		self.polygons = list()
		self.brush_order = None
		self.is_additive = True
		self.is_terrain = False
		self.is_detail = False
		self.is_nonsolid = False
		
		self.entity_island = None
		self.entity_class = None
		self.entity_keyvalues_dict = None
class Polygon:
	def __init__(self):
		self.primidx = -1
		self.vertices = list()
		self.normal = (0.0, 0.0, 0.0)
		self.material_str = None
		self.uv_data = None
		self.texture_size = None
		self.flags = 0

#For brushes
def FloatStr(float_value):
	return '{0:0=+13.6f}'.format(float_value)

def FloatIntStr(float_value):
	#return str( int( round(float_value) ) )
	return str( int(float_value) )
	
#For location
def FloatStrEntity(float_value):
	return '{0:0=.6f}'.format(float_value)
	
class T3dExport:
	def __init__(self):
		self.brush_id = 10		#Arbitrary
		self.model_id = 10		#Arbitrary
		self.actor_id = 1		#Arbitrary
		self.link_id = 0
	
	def get_brush_id(self):
		id_out = self.brush_id
		self.brush_id += 1
		return str(id_out)
	def get_model_id(self):
		id_out = self.model_id
		self.model_id += 1
		return str(id_out)
	def get_actor_id(self):
		id_out = self.actor_id
		self.actor_id += 1
		return str(id_out)
	def get_link_id(self):
		id_out = self.link_id
		self.link_id += 1
		return str(id_out)
	
	#Call before any other functions
	def export_t3d_start(self, levelprops_class, levelprops_kv):
		out = ""
		out += LINS(0, "Begin Map")
		if levelprops_class != None and levelprops_kv != None:
			out += LINS(0, "Begin Actor Class={} Name={}0".format(levelprops_class, levelprops_class))
			for key in levelprops_kv:
				value = levelprops_kv[key]
				out += LINS(1, "{}={}".format(key, value))
			out += LINS(0, "End Actor")
		else:
			out += LINS(0, "Begin Actor Class=LevelInfo Name=LevelInfo0")
			out += LINS(1, "TimeSeconds=241.013458")
			out += LINS(1, "Summary=LevelSummary'MyLevel.LevelSummary'")
			out += LINS(1, "VisibleGroups=\"\"")
			out += LINS(1, "AIProfile(0)=5831")
			out += LINS(1, "AmbientBrightness=11")
			out += LINS(0, "End Actor")
		return out
		
	#Call after all other functions
	def export_t3d_end(self):
		out = ""
		out += LINS(0, "End Map")
		return out
	
	#Insert default subtractive CSG brushes
	def export_t3d_start_insert_sub_brushes(self):
		out = ""
		
		#First brush seems to be the active/cursor brush, which does not contribute to world geometry
		DEFAULT_BRUSH = True
		if DEFAULT_BRUSH:
			out += LINS(0, "Begin Actor Class=Brush Name=Brush0")
			out += LINS(1, "Group=\"Cube\"")
			out += LINS(0, "")
			out += LINS(1, "Begin Brush Name=Brush")
			out += LINS(2, "Begin PolyList")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   -01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Normal   -00001.000000,+00000.000000,+00000.000000")
			out += LINS(4, "TextureU +00000.000000,+00000.061266,+00000.000000")
			out += LINS(4, "TextureV +00000.000000,+00000.000000,-00000.061266")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,-01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   -01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Normal   +00000.000000,+00001.000000,+00000.000000")
			out += LINS(4, "TextureU +00000.061266,+00000.000000,+00000.000000")
			out += LINS(4, "TextureV +00000.000000,+00000.000000,-00000.061266")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,-01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   +01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Normal   +00001.000000,+00000.000000,+00000.000000")
			out += LINS(4, "TextureU +00000.000000,-00000.061266,+00000.000000")
			out += LINS(4, "TextureV +00000.000000,+00000.000000,-00000.061266")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,-01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   +01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Normal   +00000.000000,-00001.000000,+00000.000000")
			out += LINS(4, "TextureU -00000.061266,-00000.000000,-00000.000000")
			out += LINS(4, "TextureV +00000.000000,+00000.000000,-00000.061266")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,-01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   -01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Normal   +00000.000000,+00000.000000,+00001.000000")
			out += LINS(4, "TextureU +00000.061266,+00000.000000,+00000.000000")
			out += LINS(4, "TextureV +00000.000000,+00000.061266,+00000.000000")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,+01024.000000")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,+01024.000000")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,+01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(3, "Begin Polygon")
			out += LINS(4, "Origin   -01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Normal   +00000.000000,+00000.000000,-00001.000000")
			out += LINS(4, "TextureU +00000.061266,+00000.000000,+00000.000000")
			out += LINS(4, "TextureV +00000.000000,-00000.061266,+00000.000000")
			out += LINS(4, "Pan      U=0 V=0")
			out += LINS(4, "Vertex   -01024.000000,-01024.000000,-01024.000000")
			out += LINS(4, "Vertex   -01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Vertex   +01024.000000,+01024.000000,-01024.000000")
			out += LINS(4, "Vertex   +01024.000000,-01024.000000,-01024.000000")
			out += LINS(3, "End Polygon")
			out += LINS(2, "End PolyList")
			out += LINS(1, "End Brush")
			out += LINS(1, "Brush=Model'MyLevel.Brush'")
			out += LINS(0, "End Actor")
		
		return out

		
	def export_polygon(self, polygon, is_terrain, is_detail, is_nonsolid, is_mover = False):
		o = polygon.vertices[0]
		n = polygon.normal
	
		#u, v:
		#	For a 256x256 brush,
		#		128^2 texture needs scale 2.0 to match the brush 1:1
		#		512^2 texture needs scale 0.5 to match the brush 1:1
		#	For a 512x512 brush,
		#		128^2 texture needs scale 2.0 to match the brush 1:1
		#		512^2 texture needs scale 0.5 to match the brush 1:1
		#pan: in pixels
		uv = pmt_common.btPlaneSpace1(n)
		assert uv != None, "poly from prim [{}] has invalid normal [{}] or zero area".format(polygon.primidx, n)
		u, v = uv
		pan_u, pan_v = 0.0, 0.0			
		
		final_material = "Detail.Marble"
		if polygon.material_str != None:
			final_material = polygon.material_str
		
		if polygon.uv_data != None:
			if polygon.texture_size == None:
				assert False, "t3d export_polygon(): error - polygon has uv_data but not texture_size"
		
			#Approach #2: axis, scale, offset are explicitly specified and mesh uvs are computed only for visualization	
			LOAD_UV_DIRECT = True
			if LOAD_UV_DIRECT:
				#UV data is stored by VMF convention -- convert it to T3D
				scale = polygon.uv_data.t3d_uv_scale
				scale_u = 1.0 / scale[0]
				scale_v = 1.0 / scale[1]
				
				u = polygon.uv_data.t3d_uv_u_axis
				v = polygon.uv_data.t3d_uv_v_axis
				u = (u[0] * scale_u, u[1] * scale_u, u[2] * scale_u)
				v = (v[0] * scale_v, v[1] * scale_v, v[2] * scale_v)
				offset = polygon.uv_data.t3d_uv_offset
				pan_u = offset[0]
				pan_v = offset[1]
				
			
		out = ""
		if not is_terrain:
			beginstr = "Begin Polygon Texture={0}".format(final_material)
			if is_nonsolid:
				beginstr += " Item=Sheets"
		else:
			beginstr = "Begin Polygon Item=ground Texture={0}".format(final_material) #todo: support 'Item=sky'
		
		flags_sum = 0
		
		if is_detail:
			flags_sum += 32
		elif is_nonsolid:
			flags_sum += 8
			
		if polygon.flags != 0:
			flags_sum += polygon.flags
			
		if flags_sum != 0:
			beginstr += " Flags={}".format(flags_sum)
			
		if is_mover: #'Link' might be needed for dynamic/mover prims, not sure
			beginstr += " Link={}".format(self.get_link_id())
			
		out += LINS(3, beginstr)
		
		out += LINS(4, "Origin   " + FloatStr(o[0]) + "," + FloatStr(o[1]) + "," + FloatStr(o[2]))
		out += LINS(4, "Normal   " + FloatStr(n[0]) + "," + FloatStr(n[1]) + "," + FloatStr(n[2]))
		out += LINS(4, "TextureU " + FloatStr(u[0]) + "," + FloatStr(u[1]) + "," + FloatStr(u[2]))
		out += LINS(4, "TextureV " + FloatStr(v[0]) + "," + FloatStr(v[1]) + "," + FloatStr(v[2]))
		#out += LINS(4, "TextureU -00001.000000,-00000.000000,-00000.000000")		#todo get u
		#out += LINS(4, "TextureV +00000.000000,+00000.000000,-00001.000000")		#todo get v
		#out += LINS(4, "Pan      U=0 V=0")
		out += LINS(4, "Pan      U={0} V={1}".format(FloatIntStr(pan_u), FloatIntStr(pan_v)))
		for v in polygon.vertices:
			out += LINS(4, "Vertex   " + FloatStr(v[0]) + "," + FloatStr(v[1]) + "," + FloatStr(v[2]))
		out += LINS(3, "End Polygon")
		return out
	
	
	def export_actor(self, classname, keyvalues_dict = None, polylist = None, is_mover = False):
		actor_id_str = self.get_actor_id()
		out = ""
		out += LINS(0, "Begin Actor Class={0} Name={0}{1}".format(classname, actor_id_str))
		
		kv_dict = keyvalues_dict if keyvalues_dict != None else dict()
		
		if polylist != None:
			kv_dict["csgoper"] = "CSG_Add" if polylist.is_additive else "CSG_Subtract"
			
			#a semi-solid brush with volume has (PolyFlags=32) at the brush level, and (Flags=32) at the poly level
			#a non-solid brush with volume has (PolyFlags=8) at the brush level
			#a non-solid sheet/sheets with no volume has (Item=Sheet for a single quad, Item=Sheets for 2 quads and Flags=8) at the poly level
			if polylist.is_detail:
				kv_dict["polyflags"] = "32"
			elif polylist.is_nonsolid:
				kv_dict["polyflags"] = "8"
				
			if polylist.is_terrain:
				kv_dict["mainscale"] = "(SheerAxis=SHEER_ZX)"
				kv_dict["postscale"] = "(SheerAxis=SHEER_ZX)"
				
			
		for key in kv_dict:
			value = kv_dict[key]
			out += LINS(1, "{0}={1}".format(key, value))
		
		if polylist != None:
			model_id_str = self.get_model_id()
			out += pmt_common.NEWLINE
			out += LINS(1, "Begin Brush Name=Model" + model_id_str)
			out += LINS(2, "Begin PolyList")
			for polygon in polylist.polygons:
				out += self.export_polygon(polygon, polylist.is_terrain, polylist.is_detail, polylist.is_nonsolid, is_mover)
			out += LINS(2, "End PolyList")
			out += LINS(1, "End Brush")
			out += LINS(1, "Brush=Model'MyLevel.Model" + model_id_str + "'")
		
		out += LINS(0, "End Actor")
		return out
		
	def export_point_entity(self, classname, keyvalues_dict = None, location = None, pitchY_yawZ_rollX = None):
		kv_dict = keyvalues_dict if keyvalues_dict != None else dict()
		
		if location != None:
			p = ( FloatStrEntity(location[0]), FloatStrEntity(location[1]), FloatStrEntity(location[2]) )
			kv_dict["location"] = "(X={},Y={},Z={})".format(p[0], p[1], p[2])
		
		if pitchY_yawZ_rollX != None:
			DEGREES_TO_U1 = 65536.0 / 360.0
			r = ( FloatIntStr(pitchY_yawZ_rollX[0] * DEGREES_TO_U1), FloatIntStr(pitchY_yawZ_rollX[1] * DEGREES_TO_U1), FloatIntStr(pitchY_yawZ_rollX[2] * DEGREES_TO_U1) )
			kv_dict["rotation"] = "(Pitch={},Yaw={},Roll={})".format(r[0], r[1], r[2])
		
		return self.export_actor(classname, keyvalues_dict)
		
	def export_static_brush(self, polylist):
		return self.export_actor("brush", None, polylist)
	def export_mover_brush(self, polylist):
		return self.export_actor(polylist.entity_class, polylist.entity_keyvalues_dict, polylist, True)
		

@pmt_common.HOUPROFILE_EVENT_DECO
def perform_export(node, t3d_export_path):
	N = node
	G = N.geometry()
	assert G != None, "t3d export: node at {} has no geometry".format(N.path())
	
	levelprops_class_attrib = G.findGlobalAttrib(pmt_common.PMT_T3D_LEVELPROPS_CLASS)
	levelprops_kv_attrib = G.findGlobalAttrib(pmt_common.PMT_T3D_LEVELPROPS_KEYVALUES)
	
	levelprops_class = None
	levelprops_kv = None
	if levelprops_class_attrib != None and levelprops_kv_attrib != None:
		levelprops_class = G.attribValue(levelprops_class_attrib)
		levelprops_kv = G.attribValue(levelprops_kv_attrib)
		
	@pmt_common.HOUPROFILE_EVENT_DECO
	def convert_houdini_prims_to_t3d_brushes(geometry):
		print(CURFUNC(CF()))
		
		@pmt_common.HOUPROFILE_EVENT_DECO
		def prim_to_poly(prim, has_material, has_uv, texture_size_attrib, brush_order_attrib, polyflags_attrib):
			n = prim.normal()
				
			poly = Polygon()
			poly.primidx = prim.number()
			poly.normal = (n.x(), n.y(), n.z())
			for v in prim.vertices():
				p = v.point().position()
				poly.vertices.append( (p.x(), p.y(), p.z()) )
			poly.vertices.reverse()	#Note reverse winding
			
			if has_material:
				poly.material_str = prim.attribValue(pmt_common.PMT_T3D_MATERIAL)
			if has_uv:
				poly.uv_data = pmt_common.extract_uv_data(prim)
			if texture_size_attrib != None:
				poly.texture_size = prim.attribValue(texture_size_attrib)
			if brush_order_attrib != None:
				poly.brush_order = prim.attribValue(brush_order_attrib)
			if polyflags_attrib != None:
				poly.flags = prim.attribValue(polyflags_attrib)
			return poly
			
		has_material = (geometry.findPrimAttrib(pmt_common.PMT_T3D_MATERIAL) != None)
		has_uv = pmt_common.houdini_geometry_has_uv_data(geometry)
		texture_size_attrib = geometry.findPrimAttrib(pmt_common.PMT_T3D_TEXTURE_SIZE)
		brush_order_attrib = geometry.findPrimAttrib(pmt_common.PMT_T3D_BRUSH_ORDER)
		polyflags_attrib = geometry.findPrimAttrib(pmt_common.PMT_T3D_POLYFLAGS)
		has_brush_order = brush_order_attrib != None
		
		bsp_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_BSP_ISLAND)
		entity_island_attrib = geometry.findPrimAttrib(pmt_common.PMT_ENTITY_ISLAND)
		geometry_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOMETRY_PRIM)
		geotype_prim_attrib = geometry.findPrimAttrib(pmt_common.PMT_GEOTYPE_PRIM)
		assert bsp_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_BSP_ISLAND)
		assert entity_island_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_ENTITY_ISLAND)
		assert geometry_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOMETRY_PRIM)
		assert geotype_prim_attrib != None, CURFUNC(CF()) + ": could not find '{}' prim attrib".format(pmt_common.PMT_GEOTYPE_PRIM)
		
		all_brushes = list()
		
		prims = geometry.prims()
		num_prims = len(prims)
		prev_prim = None
		for prim_index in range(num_prims):
			if (prim_index % 1000) == 0:
				print("prim: {0} / {1}".format(prim_index, num_prims))
		
			prim = prims[prim_index]
			if prim.type() != hou.primType.Polygon:
				continue
			
			geotype = prim.attribValue(geotype_prim_attrib)
			is_bsp = geotype == pmt_common.PMT_BSP_GROUP
			is_bspdetail = geotype == pmt_common.PMT_BSPDETAIL_GROUP
			is_bspnonsolid = geotype == pmt_common.PMT_BSPNONSOLID_GROUP
			is_bspsubtract = geotype == pmt_common.PMT_BSPSUBTRACT_GROUP
			
			is_bspterrainsubtract = geotype == pmt_common.PMT_BSPTERRAINSUBTRACT_GROUP
			is_bspterrain = geotype == pmt_common.PMT_BSPTERRAIN_GROUP
			is_bspterraindetail = geotype == pmt_common.PMT_BSPTERRAINDETAIL_GROUP
			is_bspterrainnonsolid = geotype == pmt_common.PMT_BSPTERRAINNONSOLID_GROUP
			
			is_bspentity = geotype == pmt_common.PMT_BSPENTITY_GROUP
			
			if not (is_bsp or is_bspdetail or is_bspnonsolid or is_bspsubtract or is_bspterrainsubtract or is_bspterrain or is_bspterraindetail or is_bspterrainnonsolid or is_bspentity):
				continue
				
			bsp_island = prim.attribValue(bsp_island_attrib)
			entity_island = prim.attribValue(entity_island_attrib)
			
			prev_bsp_island = prev_prim.attribValue(bsp_island_attrib) if (prev_prim != None) else None
			is_new_bsp_island = bsp_island != prev_bsp_island
			if is_new_bsp_island:
				brush = PolyList()
				all_brushes.append(brush)
				
				if is_bspsubtract:
					#For testing, we put subtractive brushes first.
					#the expected workflow is to subtract a large area then use additive methods to construct all other geometry.
					#This makes the geometry more easy to port to vmf and map, which both use additive bsp workflow.
					if not has_brush_order: all_brushes[-1].brush_order = -120
					all_brushes[-1].is_additive = False
					all_brushes[-1].is_terrain = False
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = False
				elif is_bspterrainsubtract:
					if not has_brush_order: all_brushes[-1].brush_order = -110
					all_brushes[-1].is_additive = False
					all_brushes[-1].is_terrain = True
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = False
				elif is_bsp:
					if not has_brush_order: all_brushes[-1].brush_order = -100
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = False
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = False
				elif is_bspdetail:
					if not has_brush_order: all_brushes[-1].brush_order = -90
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = False
					all_brushes[-1].is_detail = True
					all_brushes[-1].is_nonsolid = False
				elif is_bspnonsolid:
					if not has_brush_order: all_brushes[-1].brush_order = -90
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = False
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = True
				elif is_bspterrain:
					if not has_brush_order: all_brushes[-1].brush_order = -80
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = True
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = False
				elif is_bspterraindetail:
					if not has_brush_order: all_brushes[-1].brush_order = -70
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = True
					all_brushes[-1].is_detail = True
					all_brushes[-1].is_nonsolid = False
				elif is_bspterrainnonsolid:
					if not has_brush_order: all_brushes[-1].brush_order = -60
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = True
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = True
				elif is_bspentity:
					if not has_brush_order: all_brushes[-1].brush_order = 0 #t3d bspentity is always a mover, so its order is last
					all_brushes[-1].is_additive = True
					all_brushes[-1].is_terrain = False
					all_brushes[-1].is_detail = False
					all_brushes[-1].is_nonsolid = False
					all_brushes[-1].entity_island = entity_island
					
					#assume all prims assigned to this mover have same classname and keyvalues
					classname = prim.attribValue(pmt_common.PMT_T3D_ENTITY_CLASS)
					kv_attrib_dict = prim.dictAttribValue(pmt_common.PMT_T3D_ENTITY_KEYVALUES)
						
					if len(classname) != 0 and classname != pmt_common.PMT_NONE:
						all_brushes[-1].entity_keyvalues_dict = kv_attrib_dict
						all_brushes[-1].entity_class = classname
				else: assert False, CURFUNC(CF()) + ": invalid BSP type"
					
			
			poly = prim_to_poly(prim, has_material, has_uv, texture_size_attrib, brush_order_attrib, polyflags_attrib)
			if has_brush_order and all_brushes[-1].brush_order == None:
				all_brushes[-1].brush_order = poly.brush_order
			all_brushes[-1].polygons.append(poly)
			prev_prim = prim
			
		return all_brushes
	all_brushes = convert_houdini_prims_to_t3d_brushes(G)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def separate_static_and_mover_brushes(all_brushes):
		static = list()
		movers = list()
		num_brushes = len(all_brushes)
		for brush_index in range(num_brushes):
			brush = all_brushes[brush_index]
			if brush.entity_island == None:
				static.append(brush)
			else:
				is_new_entity_island = True if brush_index == 0 else brush.entity_island != all_brushes[brush_index - 1].entity_island
				if is_new_entity_island:
					brushentity = MoverBrush()
					movers.append(brushentity)
				movers[-1].polylists.append(brush)
		return static, movers
	static_polylists, mover_brushes = separate_static_and_mover_brushes(all_brushes)
	
	@pmt_common.HOUPROFILE_EVENT_DECO
	def sort_brushes(brushes):
		def compare_brushes(a, b):
			if a.brush_order < b.brush_order: 
				return -1
			elif a.brush_order == b.brush_order: 
				return 0
			else: #a.brush_order > b.brush_order: 
				return 1
			
		brushes.sort(key = functools.cmp_to_key(compare_brushes))
		return brushes
	static_polylists = sort_brushes(static_polylists)
	
	#a single mover can be non-convex and combine the prims of multiple brushes
	@pmt_common.HOUPROFILE_EVENT_DECO
	def merge_mover_brush_polylists(movers):
		mover_polylists = list()
		for mover in movers:
			if len(mover.polylists) > 0:
				#assume all values other than PolyList().polygons are the same for each entity_island
				mover_polylists.append(PolyList())
				mover_polylists[-1] = copy.deepcopy(mover.polylists[0])
				mover_polylists[-1].polygons = list()
				
				for polys in mover.polylists:
					mover_polylists[-1].polygons += polys.polygons
		return mover_polylists
	mover_polylists = merge_mover_brush_polylists(mover_brushes)
				
	
	exporter = T3dExport()
	
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
			
			classname = point.attribValue(pmt_common.PMT_T3D_ENTITY_CLASS)
			if len(classname) == 0 or classname == pmt_common.PMT_NONE:
				continue
					
			keyvalues_dict = point.dictAttribValue(pmt_common.PMT_T3D_ENTITY_KEYVALUES)
			rotation_euler = point.attribValue(pmt_common.PMT_T3D_ROTATION_EULER)
			rotation_euler_enabled = point.attribValue(pmt_common.PMT_HAS_EULER_ROTATION)
				
			if not rotation_euler_enabled:
				entity_str += exporter.export_point_entity(classname, keyvalues_dict, p_tuple)
			else:
				rot_x = -rotation_euler[0]
				rot_y = -rotation_euler[1]
				rot_z = rotation_euler[2]
				
				pitchY_yawZ_rollX = (rot_y, rot_z, rot_x)
				entity_str += exporter.export_point_entity(classname, keyvalues_dict, p_tuple, pitchY_yawZ_rollX)
		return entity_str
	entity_str = extract_point_entities(exporter, G)
	
	### Main export
	file_out = open(t3d_export_path, 'w')
	file_out.write( exporter.export_t3d_start(levelprops_class, levelprops_kv) )
	file_out.write( exporter.export_t3d_start_insert_sub_brushes() )
	
	for brush in static_polylists:
		file_out.write( exporter.export_static_brush(brush) )

	for polylist in mover_polylists:
		if polylist.entity_class != None:
			file_out.write( exporter.export_mover_brush(polylist) )

	file_out.write( entity_str )
	file_out.write( exporter.export_t3d_end() )
	
	file_out.close()
	print(".t3d written to {}".format(t3d_export_path))
	

def main_export(node, t3d_export_path):
	profile = pmt_common.HOUPROFILE("pmt_export_t3d")
	perform_export(node, t3d_export_path)



	