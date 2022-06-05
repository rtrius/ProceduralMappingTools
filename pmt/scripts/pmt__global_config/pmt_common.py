#pmt_common.py
#

import math

LARGE_FLOAT = 1e15

PMT_BSP_ISLAND = "pmt_bsp_island"
PMT_ENTITY_ISLAND = "pmt_entity_island"
PMT_GROUP_ISLAND = "pmt_group_island"

#pmt_geometry_* is an integer attrib set to 1 if a point/prim 
#is a brush, brush entity, displacement map, or patch.
#set to 0 otherwise.
PMT_GEOMETRY_POINT = "pmt_geometry_point"
PMT_GEOMETRY_PRIM = "pmt_geometry_prim"
#pmt_geotype is a string attrib set to the group ths point/prim is in
PMT_GEOTYPE_POINT = "pmt_geotype_point"
PMT_GEOTYPE_PRIM = "pmt_geotype_prim"

#disjoint groups for points and prims used by the exporter
PMT_BSP_GROUP = "pmt_bsp"
PMT_BSPDETAIL_GROUP = "pmt_bspdetail"
PMT_BSPENTITY_GROUP = "pmt_bspentity"
PMT_BSPNONSOLID_GROUP = "pmt_bspnonsolid"					#t3d only
PMT_BSPSUBTRACT_GROUP = "pmt_bspsubtract"					#t3d only
PMT_BSPTERRAIN_GROUP = "pmt_bspterrain"						#t3d only
PMT_BSPTERRAINDETAIL_GROUP = "pmt_bspterraindetail"			#t3d only
PMT_BSPTERRAINSUBTRACT_GROUP = "pmt_bspterrainsubtract"		#t3d only
PMT_BSPTERRAINNONSOLID_GROUP = "pmt_bspterrainnonsolid"		#t3d only
PMT_DISPLACEMENT_GROUP = "pmt_displacement"					#vmf only
PMT_PATCHDEF2_GROUP = "pmt_patchdef2"						#map only
PMT_PATCHDEF3_GROUP = "pmt_patchdef3"						#map only

#
PMT_MAP_PATCHDEF3_WIDTH_SUBDIVS = "pmt_map_patchdef3_width_subdivs"
PMT_MAP_PATCHDEF3_HEIGHT_SUBDIVS = "pmt_map_patchdef3_height_subdivs"

PMT_T3D_BRUSH_ORDER = "pmt_t3d_brush_order"
PMT_T3D_POLYFLAGS = "pmt_t3d_polyflags"

#'pmt_entity' is a point or prim group
#	when it is a point group, each point in that group is a separate point entity 
#	when it is a prim group, each prim island and all points of that island is a single brush entity
#A point assigned to the point 'pmt_entity' group should not be part of the prim 'pmt_entity' group,
#and all prims in the prim 'pmt_entity' group should not have any points in the point 'pmt_entity' group.
#
#Entities can be configured with point/prim attribs such as
#PMT_*_ENTITY_CLASS, PMT_*_ENTITY_KEYVALUES, PMT_ROTATION_EULER, PMT_ROTATION_EULER_ENABLED.
PMT_ENTITY = "pmt_entity"	

PMT_NONE = "pmt_none"

#BSPENTITY PMT_POINT_ENTITY
PMT_VMF_ENTITY_CLASS = "pmt_vmf_entity_class"
PMT_T3D_ENTITY_CLASS = "pmt_t3d_entity_class"
PMT_MAP_ENTITY_CLASS = "pmt_map_entity_class"
PMT_VMF_ENTITY_KEYVALUES = "pmt_vmf_entity_keyvalues"
PMT_T3D_ENTITY_KEYVALUES = "pmt_t3d_entity_keyvalues"
PMT_MAP_ENTITY_KEYVALUES = "pmt_map_entity_keyvalues"

#PMT_CONNECTIONS is a special key for vmf keyvalue dict;
#it is a array of strings(x6) that stores entity io connections
PMT_CONNECTIONS = "pmt_connections"

#Detail attribs for per-level properties
PMT_VMF_LEVELPROPS_CLASS = "pmt_vmf_levelprops_class"
PMT_T3D_LEVELPROPS_CLASS = "pmt_t3d_levelprops_class"
PMT_MAP_LEVELPROPS_CLASS = "pmt_map_levelprops_class"
PMT_VMF_LEVELPROPS_KEYVALUES = "pmt_vmf_levelprops_keyvalues"
PMT_T3D_LEVELPROPS_KEYVALUES = "pmt_t3d_levelprops_keyvalues"
PMT_MAP_LEVELPROPS_KEYVALUES = "pmt_map_levelprops_keyvalues"


#Restricted values should not be in PMT_*_ENTITY_KEYVALUES, but are stored elsewhere.
#
#id: is determined by the exporter
#classname: is stored in PMT_*_ENTITY_CLASS
#origin: position is specified by @P
#angles: rotation is specified by PMT_*_ROTATION_EULER
PMT_VMF_ENTITY_RESTRICTED_KEYVALUES = ["id", "classname", "origin", "angles"]

#class: is stored in PMT_*_ENTITY_CLASS
#name: is determined by the exporter
#location: position is specified by @P
#rotation: rotation is specified by PMT_*_ROTATION_EULER
PMT_T3D_ENTITY_RESTRICTED_KEYVALUES = ["class", "name", "location", "rotation"]

#classname: is stored in PMT_*_ENTITY_CLASS
#origin: position is specified by @P
#rotation: rotation is specified by PMT_*_ROTATION_EULER
PMT_MAP_ENTITY_RESTRICTED_KEYVALUES = ["classname", "origin", "rotation"] #"texture"

#rotation in degrees about the x, y, z, axes - element 0 is x, 1 is y, and 2 is z
PMT_VMF_ROTATION_EULER = "pmt_vmf_rotation_euler"
PMT_T3D_ROTATION_EULER = "pmt_t3d_rotation_euler"
PMT_MAP_ROTATION_EULER = "pmt_map_rotation_euler"
PMT_HAS_EULER_ROTATION = "pmt_has_euler_rotation"		#int [0-1]; set to 1 to apply PMT_*_ROTATION_EULER

#PMT_ROTATION_SIGN_* is used to accumulate euler rotations in 'Houdini' space(Y-up)
#before converting to the output space (vmf, t3d, or map).
#It accounts for differences in the direction of rotation between coordinate systems.
#For example a rotation of 45 degrees in Houdini space about the x-axis is:
#	+45 degrees in vmf,
#	-45 degrees in t3d, and
#	-45 degrees in map.
PMT_ROTATION_SIGN_VMF = (1.0, -1.0, -1.0) 	#x+, y-, z-
PMT_ROTATION_SIGN_T3D = (-1.0, -1.0, -1.0)	#x-, y-, z-
PMT_ROTATION_SIGN_MAP = (-1.0, -1.0, -1.0)	#x-, y-, z-

#prim attributes
PMT_VMF_MATERIAL = "pmt_vmf_material"
PMT_T3D_MATERIAL = "pmt_t3d_material"
PMT_MAP_MATERIAL = "pmt_map_material"

PMT_VMF_TEXTURE_SIZE = "pmt_vmf_texture_size" #width, height of the texture at pmt_vmf_texture_path
PMT_T3D_TEXTURE_SIZE = "pmt_t3d_texture_size"
PMT_MAP_TEXTURE_SIZE = "pmt_map_texture_size"

PMT_VMF_TEXTURE_PATH = "pmt_vmf_texture_path" #absolute filesystem path of the diffuse map of pmt_vmf_material
PMT_T3D_TEXTURE_PATH = "pmt_t3d_texture_path"
PMT_MAP_TEXTURE_PATH = "pmt_map_texture_path"

PMT_VMF_LIGHTMAPSCALE = "pmt_vmf_lightmapscale"

#To simplify the UV align/transform nodes we store brush UV data in VMF form and convert to t3d/map.
#Differences in scale (in the actual map file and not in the UI):
#	vmf: double scale doubles size of brush needed to display the entire texture,
#	t3d: double scale halves size (1/vmf_scale)
#	map: double scale halves size (1/vmf_scale)
PMT_VMF_UV_U_AXIS = "pmt_vmf_uv_u_axis"		#VMF convention - normalized
PMT_VMF_UV_V_AXIS = "pmt_vmf_uv_v_axis"		#VMF convention - normalized
PMT_VMF_UV_SCALE = "pmt_vmf_uv_scale"		#VMF convention - scale 2 doubles texture size and 0.5 halves
PMT_VMF_UV_OFFSET = "pmt_vmf_uv_offset"		#VMF convention - offset in pixels

PMT_T3D_UV_U_AXIS = "pmt_t3d_uv_u_axis"		#VMF convention - normalized (actual values in .t3d are scaled by uv scale)
PMT_T3D_UV_V_AXIS = "pmt_t3d_uv_v_axis"		#VMF convention - normalized (actual values in .t3d are scaled by uv scale)
PMT_T3D_UV_SCALE = "pmt_t3d_uv_scale"		#VMF convention - scale 2 doubles texture size and 0.5 halves (implicitly stored in u/v axes)
PMT_T3D_UV_OFFSET = "pmt_t3d_uv_offset"		#VMF convention - offset in pixels

PMT_MAP_UV_SCALE = "pmt_map_uv_scale"		#VMF convention - scale 2 doubles texture size and 0.5 halves
PMT_MAP_UV_OFFSET = "pmt_map_uv_offset"		#VMF convention - offset in pixels
PMT_MAP_UV_ROTATION_DEGREES = "pmt_map_uv_rotation_degrees"

class UvData:
	def __init__(self):
		self.vmf_uv_u_axis = None		#vector3; direction of u axis in 3D space (3d vector corresponding to uv vector [1, 0])
		self.vmf_uv_v_axis = None		#vector3; direction of v axis in 3D space (3d vector corresponding to uv vector [0, 1])
		self.vmf_uv_scale = None
		self.vmf_uv_offset = None
		
		self.map_uv_scale = None
		self.map_uv_offset = None
		self.map_uv_rotation_degrees = None
		
		self.t3d_uv_u_axis = None		#vector3; direction of u axis in 3D space (3d vector corresponding to uv vector [1, 0])
		self.t3d_uv_v_axis = None		#vector3; direction of v axis in 3D space (3d vector corresponding to uv vector [0, 1])
		self.t3d_uv_scale = None
		self.t3d_uv_offset = None

def houdini_geometry_has_uv_data(hou_geometry):
	vmf_uv_u = (hou_geometry.findPrimAttrib(PMT_VMF_UV_U_AXIS) != None)
	vmf_uv_v = (hou_geometry.findPrimAttrib(PMT_VMF_UV_V_AXIS) != None)
	vmf_scale = (hou_geometry.findPrimAttrib(PMT_VMF_UV_SCALE) != None)
	vmf_offset = (hou_geometry.findPrimAttrib(PMT_VMF_UV_OFFSET) != None)
	has_vmf = (vmf_uv_u and vmf_uv_v and vmf_scale and vmf_offset)
	
	map_scale = (hou_geometry.findPrimAttrib(PMT_MAP_UV_SCALE) != None)
	map_offset = (hou_geometry.findPrimAttrib(PMT_MAP_UV_OFFSET) != None)
	map_rotation_degrees = (hou_geometry.findPrimAttrib(PMT_MAP_UV_ROTATION_DEGREES) != None)
	has_map = (map_scale and map_offset and map_rotation_degrees)
	
	t3d_uv_u = (hou_geometry.findPrimAttrib(PMT_T3D_UV_U_AXIS) != None)
	t3d_uv_v = (hou_geometry.findPrimAttrib(PMT_T3D_UV_V_AXIS) != None)
	t3d_scale = (hou_geometry.findPrimAttrib(PMT_T3D_UV_SCALE) != None)
	t3d_offset = (hou_geometry.findPrimAttrib(PMT_T3D_UV_OFFSET) != None)
	has_t3d = (t3d_uv_u and t3d_uv_v and t3d_scale and t3d_offset)
	
	has_uv = (has_vmf and has_map and has_t3d)
	return has_uv
	
def extract_uv_data(hou_primitive):
	vmf_uv_u = hou_primitive.attribValue(PMT_VMF_UV_U_AXIS)
	vmf_uv_v = hou_primitive.attribValue(PMT_VMF_UV_V_AXIS)
	vmf_scale = hou_primitive.attribValue(PMT_VMF_UV_SCALE)
	vmf_offset = hou_primitive.attribValue(PMT_VMF_UV_OFFSET)
	
	map_scale = hou_primitive.attribValue(PMT_MAP_UV_SCALE)
	map_offset = hou_primitive.attribValue(PMT_MAP_UV_OFFSET)
	map_rotation_degrees = hou_primitive.attribValue(PMT_MAP_UV_ROTATION_DEGREES)
	
	t3d_uv_u = hou_primitive.attribValue(PMT_T3D_UV_U_AXIS)
	t3d_uv_v = hou_primitive.attribValue(PMT_T3D_UV_V_AXIS)
	t3d_scale = hou_primitive.attribValue(PMT_T3D_UV_SCALE)
	t3d_offset = hou_primitive.attribValue(PMT_T3D_UV_OFFSET)
	
	import hou
	uv_data = UvData()
	uv_data.vmf_uv_u_axis = vmf_uv_u
	uv_data.vmf_uv_v_axis = vmf_uv_v
	uv_data.vmf_uv_scale = vmf_scale
	uv_data.vmf_uv_offset = vmf_offset
	
	uv_data.map_uv_scale = map_scale
	uv_data.map_uv_offset = map_offset
	uv_data.map_uv_rotation_degrees = map_rotation_degrees
	
	uv_data.t3d_uv_u_axis = t3d_uv_u
	uv_data.t3d_uv_v_axis = t3d_uv_v
	uv_data.t3d_uv_scale = t3d_scale
	uv_data.t3d_uv_offset = t3d_offset
	return uv_data

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
	
#BulletPhysics bullet\src\LinearMath\btVector3.h
def btPlaneSpace1(normal, EPSILON = 0.0001):
	p = [0.0, 0.0, 0.0]
	q = [0.0, 0.0, 0.0]

	if abs(normal[2]) > math.sqrt(1.0 / 2.0):
		#choose p in y-z plane
		a = normal[1]*normal[1] + normal[2]*normal[2];
		if a < EPSILON: return None #modification to avoid divide by 0
		k = 1.0 / math.sqrt(a);
		p[0] = 0;
		p[1] = -normal[2]*k;
		p[2] = normal[1]*k;
		# set q = n x p
		q[0] = a*k;
		q[1] = -normal[0]*p[2];
		q[2] = normal[0]*p[1];
	else:
		# choose p in x-y plane
		a = normal[0]*normal[0] + normal[1]*normal[1];
		if a < EPSILON: return None #modification to avoid divide by 0
		k = 1.0 / math.sqrt(a);
		p[0] = -normal[1]*k;
		p[1] = normal[0]*k;
		p[2] = 0;
		# set q = n x p
		q[0] = -normal[2]*p[1];
		q[1] = normal[2]*p[0];
		q[2] = a*k;
	
	#TypeError 'tuple' object does not support item assignment
	#(A[0] = ...) requires that A is a list
	p2 = (p[0], p[1], p[2])
	q2 = (q[0], q[1], q[2])
	return (p2, q2)

import datetime
import time
def TIME(): 
	date_time = datetime.datetime.utcfromtimestamp( time.time() )
	return str(date_time) + (".000000" if date_time.microsecond == 0 else "")

import hou
class HOUPROFILE:
	def __init__(self, profile_name, debug_print = False):
		profile_name += " " + TIME()
		self.debug_print = debug_print
		self.name = profile_name
		
		self.profile = hou.perfMon.startProfile(self.name)
		if self.debug_print: print("HOUPROFILE {0}".format(self.name))
	def __del__(self): 
		self.profile.stop()
		if self.debug_print: print("~HOUPROFILE {0}".format(self.name))
		
class HOUPROFILE_EVENT:
	def __init__(self, event_name, debug_print = False):
		self.debug_print = debug_print
		self.name = event_name
		
	def __enter__(self):
		self.event = hou.perfMon.startEvent(self.name)
		if self.debug_print: print("HOUPROFILE_EVENT {0}".format(self.name))
	
	def __exit__(self, type, value, tb):
		self.event.stop()
		if self.debug_print: print("~HOUPROFILE_EVENT {0}".format(self.name))
		
#def HOUPROFILE_DECO(function):
#	def wrapper(*args, **keywords):
#		with HOUPROFILE(function.__name__):
#			return function(*args, **keywords)
#	return wrapper

def HOUPROFILE_EVENT_DECO(function):
	def wrapper(*args, **keywords):
		with HOUPROFILE_EVENT(function.__name__):
			return function(*args, **keywords)
	return wrapper
	