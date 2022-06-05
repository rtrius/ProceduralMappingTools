#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_materialdb_source1_vmt
#	script_section_name: 	pmt_materialdb_source1_vmt.py
# Parses .vmt files to extract diffuse texture paths.

import os
import sys
	
#By default open() uses locale.getpreferredencoding();
#Houdini 18.5 on Windows 10 locale.getpreferredencoding() returns 'cp65001', but
#a standalone Python3 install returns 'cp1252'. Using cp65001 causes the decoding to
#fail, so explicitly set the codec here.
TEXT_CODEC = "cp1252" #windows-1252 'Western Europe'

IN_HOUDINI = 'hou' in sys.modules
def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
def find_all_files_in(search_path, extension):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			#filepath = dirpath + filename
			if filepath.endswith(extension):
				paths.append((filename, filepath))
				DPRINT("{0}: {1}".format(extension, filepath))
	return paths
	
###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules from a module inside pmt__global_config.
###Only modules starting with "pmt_common" should be accessed from inside pmt::pmt__global_config.
import sys
IN_HOUDINI = 'hou' in sys.modules
if IN_HOUDINI:
	import hou
	PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt_common = PMT__G_CFG.pmt_common
	pmt_common_texture = PMT__G_CFG.pmt_common_texture
	pmt_common_json = PMT__G_CFG.pmt_common_json
###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__

#Parses a single .vmt file, which contains a single material definition
def get_vmt_diffuse_path_and_surfaceprop(vmt_path):
	basetexture_path = None
	surfaceprop = None
	with open(vmt_path, 'rt', encoding=TEXT_CODEC) as vmt_file:
		found_basetexture = False
		found_surfaceprop = False
		for line in vmt_file:
			#Format of a diffuse map is:
			#	"$basetexture" "dir/material_name"
			#There can be multiple $basetexture in a single material
			#to specify different diffuse maps for each rendering level(DX8, DX9, ...),
			#but just assume that the first $basetexture is the main one.
			if not found_basetexture and "$basetexture" in line.lower():
				basetexture_path = line.split()[1].replace("\"", "") #+ ".vtf"
				found_basetexture = True
			#same as basetexture; assume the first surfaceprop is the main
			if not found_surfaceprop and "$surfaceprop" in line.lower():
				surfaceprop = line.split()[1].replace("\"", "")
				found_surfaceprop = True
			if found_basetexture and found_surfaceprop:
				break
	
		if not found_basetexture:
			DPRINT("No $basetexture {}".format(vmt_path))
			
	return basetexture_path, surfaceprop
	
class MaterialsVmt:
	def __init__(self):
		#paths are stored in the format:
		#	foldera/folderb/texture
		#with no '/' at the beginning
		
		#material_to_diffuse_dict[material_path] = diffuse_path
		self.material_to_diffuse_dict = dict()
		#material_to_surfaceprop_dict[material_path] = surfaceprop
		self.material_to_surfaceprop_dict = dict()
		
		#diffuse_to_material_list[diffuse_path] = list()
		#where list contains a material_path(s) that reference the diffuse_path
		self.diffuse_to_materials_dict = dict()
		
		#diffuse dicts: each key is a absolute filesystem path to an image file ('fs_path')
		self.fs_diffuse_to_dimensions = dict()	#fs_diffuse_to_dimensions[fs_path] = (width, height)
		self.fs_diffuse_to_analyze = dict()		#texture metadata dict
		self.fs_diffuse_to_tags = dict()		#user generated tags dict
		
	#returns a string diffuse_path, which is refered to by the material at material_path; both paths are relative
	def get_diffuse_of_material(self, material_path):
		material_path = material_path.lower()
		#if material_path not in self.material_to_diffuse_dict:
		#	print("MaterialsVmt::get_diffuse_of_material() no material_path in dict {}".format(material_path))
		#	return None
		return self.material_to_diffuse_dict[material_path]
		
	#returns a list of strings material_path(s), which reference diffuse_path; both paths are relative
	def get_materials_using_diffuse(self, diffuse_path):
		diffuse_path = diffuse_path.lower()
		#if diffuse_path not in self.diffuse_to_materials_dict:
		#	print("MaterialsVmt::get_materials_using_diffuse() no diffuse_path in dict {}".format(diffuse_path))
		#	return None
		return self.diffuse_to_materials_dict[diffuse_path]

	#returns a (width, height) tuple
	def get_diffuse_dimensions(self, absolute_diffuse_path):
		absolute_diffuse_path = absolute_diffuse_path.lower()
		#if absolute_diffuse_path not in self.diffuse_to_materials_dict:
		#	print("MaterialsVmt::get_diffuse_dimensions() no diffuse_path in dict {}".format(absolute_diffuse_path))
		#	return None
		return self.fs_diffuse_to_dimensions[absolute_diffuse_path]
		
#Converts between source and filesystem paths:
#filesystem: C:/pmt_resources/textures/vmf/materials/folder/texture.png
#    source: folder/texture
def convert_fs_to_source_path(fs_path, vmf_textures_path, extension = ".png"):
	source_path = fs_path[len(vmf_textures_path):-len(extension)]
	while source_path.startswith("/"):
		source_path = source_path[1:]
	return source_path
def convert_source_path_to_fs(source_path, vmf_textures_path, extension = ".png"):
	if not vmf_textures_path.endswith('/'):
		vmf_textures_path += '/'
	return vmf_textures_path + source_path + extension

def parse_vmt_files(vmf_materials_path, vmf_textures_path = None):
	#
	global_material_to_surfaceprop_dict = dict()
	global_material_to_diffuse_dict = dict()
	global_diffuse_to_materials_dict = dict()
	
	vmt_files = find_all_files_in(vmf_materials_path, ".vmt")
	
	#map-specific prop materials are duplicates of other materials,
	#and should not be directly referenced; they are placed in vmf_materials_path + "/_msp/"
	EXCLUDE_MAPSPECIFIC_PROP_MATERIALS = True
	if EXCLUDE_MAPSPECIFIC_PROP_MATERIALS:
		mat_path = vmf_materials_path.replace(os.sep, "/")
		if mat_path.endswith("/"): 
			mat_path = mat_path[:-1]
		vmf_files_no_msp = list()
		for (filename, filepath) in vmt_files:
			rel_path = filepath[len(mat_path):].replace(os.sep, "/")
			folders = rel_path.split("/")[:-1]
			top_folders = folders[:2]
			is_msp = False
			for folder in top_folders:
				if folder.startswith("_msp"):
					DPRINT("exclude _msp: {}".format(rel_path))
					is_msp = True
					break
			if not is_msp:
				vmf_files_no_msp.append((filename, filepath))
		DPRINT("vmf_files_no_msp: {}/{} .vmt".format(len(vmf_files_no_msp), len(vmt_files)))
		vmt_files = vmf_files_no_msp	
		
	for (filename, filepath) in vmt_files:
		diffuse_path, surfaceprop = get_vmt_diffuse_path_and_surfaceprop(filepath)
		
		if diffuse_path != None:
			material_path = filepath[len(vmf_materials_path):].replace("\\", "/").replace(".vmt", "")
			diffuse_path = diffuse_path.replace("\\", "/")
			
			material_path = material_path.lower()
			diffuse_path = diffuse_path.lower()
			
			while material_path.startswith("/"):
				material_path = material_path[1:]
			
			global_material_to_surfaceprop_dict[material_path] = surfaceprop
			global_material_to_diffuse_dict[material_path] = diffuse_path
			
			if diffuse_path not in global_diffuse_to_materials_dict:
				global_diffuse_to_materials_dict[diffuse_path] = list()
			global_diffuse_to_materials_dict[diffuse_path].append(material_path)
	
	#Debug print
	for material in global_material_to_diffuse_dict:
		diffuse = global_material_to_diffuse_dict[material]
		surfaceprop = global_material_to_surfaceprop_dict[material]
		DPRINT("material: {} -> {} (surf: {})".format(material, diffuse, surfaceprop))
	for diffuse in global_diffuse_to_materials_dict:
		DPRINT("diffuse: {}".format(diffuse))
		material_list = global_diffuse_to_materials_dict[diffuse]
		for material in material_list:
			DPRINT("-> {}".format(material))
		DPRINT("")
		
	#
	vmt_db = MaterialsVmt()
	vmt_db.material_to_diffuse_dict = global_material_to_diffuse_dict
	vmt_db.diffuse_to_materials_dict = global_diffuse_to_materials_dict
	vmt_db.material_to_surfaceprop_dict = global_material_to_surfaceprop_dict
	
	#
	if vmf_textures_path != None:
		png_files = find_all_files_in(vmf_textures_path, ".png")
		png_fs_fullpaths = list()
		for (filename, filepath) in png_files:
			fs_path = filepath.replace(os.sep, '/')
			fs_path = fs_path.lower()
			png_fs_fullpaths.append(fs_path)
			
		fs_path_to_dimensions = dict()
		for fs_path in png_fs_fullpaths:
			(width, height) = pmt_common_texture.get_image_dimensions(fs_path)
			fs_path_to_dimensions[fs_path] = (width, height)
		vmt_db.fs_diffuse_to_dimensions = fs_path_to_dimensions
		
		fs_path_to_analyze = dict()
		for fs_path in png_fs_fullpaths:
			analyze_dict = pmt_common_json.load_json(fs_path, pmt_common_json.JSON_ANALYZE)
			fs_path_to_analyze[fs_path] = analyze_dict
		vmt_db.fs_diffuse_to_analyze = fs_path_to_analyze
			
		fs_path_to_tags = dict()
		for fs_path in png_fs_fullpaths:
			tags_dict = pmt_common_json.load_json(fs_path, pmt_common_json.JSON_TAGS)
			fs_path_to_tags[fs_path] = tags_dict
		vmt_db.fs_diffuse_to_tags = fs_path_to_tags
		
	#	
	return vmt_db
	
if __name__ == "__main__" and not IN_HOUDINI:
	num_argv = len(sys.argv)
	if not (2 <= num_argv and num_argv <= 3):
		print("pmt_materialdb_source1_vmt.py [vmf_materials_path]")
		print("pmt_materialdb_source1_vmt.py [vmf_materials_path] [vmf_textures_path]")
		exit()
	elif num_argv == 2:
		vmf_materials_path = sys.argv[1]
		vmf_textures_path = None
	elif num_argv == 3:
		vmf_materials_path = sys.argv[1]
		vmf_textures_path = sys.argv[2]
	else:
		assert False
		exit()
		
	DPRINT("vmf_materials_path: {}".format(vmf_materials_path))
	DPRINT("vmf_textures_path: {}".format(vmf_textures_path))
	vmt_db = parse_vmt_files(vmf_materials_path, vmf_textures_path)
