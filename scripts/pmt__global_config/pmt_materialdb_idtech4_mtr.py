#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_materialdb_idtech4_mtr
#	script_section_name: 	pmt_materialdb_idtech4_mtr.py
# Parses .mtr files to extract diffuse texture paths.

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

#Parses a single .mtr file, which can contain multiple material definitions
def load_material_to_diffuse_dict(mtr_path):
	material_to_diffuse_dict = dict()
	with open(mtr_path, 'rt', encoding=TEXT_CODEC) as mtr_file:
	
		indentation_level = 0
		
		current_material_path = None
		path_diffusemap = None
		path_blend_diffusemap = None
		path_qer_editorimage = None
		
		lines = list()
		for line in mtr_file:
			lines.append(line)
		num_lines = len(lines)
		for line_index in range(num_lines):
			line = lines[line_index]

			if True: #remove '//' comments
				if len(line) == 0: 
					continue
				left, sep, right = line.partition("//")
				line = left
		
			if "{" in line:
				indentation_level += line.count("{")
			if "}" in line:
				indentation_level -= line.count("}")
		
			#Format of materials is:
			#	MATERIAL_PATH
			#	{
			#		diffusemap textures/path/to/image
			#		qer_editorimage textures/path/to/image
			#		{
			#			blend diffusemap
			#			map textures/path/to/image
			#		}
			#	}
			#
			#Assume that if the line(MATERIAL_PATH) begins with this, it is the name of a material
			MATERIAL_STR = "textures/"
			if current_material_path == None and indentation_level == 0:
				if not line.startswith(MATERIAL_STR) or indentation_level >= 1:
					continue
				else:
					current_material_path = line.split()[0]		#Assume that 1st token is path of material; split to remove any comments
					assert current_material_path.startswith(MATERIAL_STR)
					#DPRINT("current_material_path: " + current_material_path)
			else:
				#Encountered closing bracket "}"; store the diffuse, if it has been found, and move onto next material
				if indentation_level == 0:
					if current_material_path != None:
						mat_diffuse_path = None
					
						#path_qer_editorimage is sometimes used for materials without a diffuse, such as textures/common/nodraw
						#it is only used for display within the editor and not in game.
						#If there is a diffusemap, we want to prioritize it over qer_editorimage.
						if path_qer_editorimage != None:
							mat_diffuse_path = path_qer_editorimage
						
						#there are special textures such as '_white' which are not actual textures and should be ignored
						#to avoid them check for '/' as there are no textures in the root directory
						if path_blend_diffusemap != None and "/" in path_blend_diffusemap:
							mat_diffuse_path = path_blend_diffusemap
							
						if path_diffusemap != None and "/" in path_diffusemap:
							mat_diffuse_path = path_diffusemap
						
						if mat_diffuse_path != None:
							#currently we convert all images to .png, and assume that all images end with .png
							#paths are stored in the dict without file type extensions
							TRUNCATE_EXTENSIONS = [".tga", ".jpg", ".dds"]
							for extention in TRUNCATE_EXTENSIONS:
								if mat_diffuse_path.endswith(extention):
									mat_diffuse_path = mat_diffuse_path[:-len(extention)]
							material_to_diffuse_dict[current_material_path] = mat_diffuse_path
						
					current_material_path = None
					path_diffusemap = None
					path_qer_editorimage = None
			
				#Found a 'diffusemap'; store the texture path, which might not exist on disk
				if indentation_level == 1 and ("diffusemap" in line or "qer_editorimage" in line):
					splitline = line.split()
					key_index = None
					if "diffusemap" in splitline:
						key_index = splitline.index("diffusemap")
					elif "qer_editorimage" in splitline:
						key_index = splitline.index("qer_editorimage")
					assert key_index != None, "material {} split() failed: {} (mtr_path={})".format(current_material_path, splitline, mtr_path)
					diffuse_index = key_index + 1
					
					if diffuse_index < len(splitline):
						texture_path = splitline[diffuse_index]
						if "diffusemap" in line:
							path_diffusemap = texture_path
						elif "qer_editorimage" in line:
							path_qer_editorimage = texture_path
				
				#Handle 'blend diffusemap map /texture/path/' cases
				if indentation_level == 2 and ("blend" in line and "diffusemap" in line):
					next_line_index = line_index + 1
					merged_lines = line 
					if next_line_index < num_lines:
						merged_lines += " " + lines[next_line_index]
						
					splitline = merged_lines.split()
					if "map" in splitline:
						key_index = splitline.index("map")
						diffuse_index = key_index + 1
						if diffuse_index < len(splitline):
							path_blend_diffusemap = splitline[diffuse_index]
	
	return material_to_diffuse_dict
	
class MaterialsMtr:
	def __init__(self):
		#material_to_diffuse_dict[material_path] = diffuse_path
		self.material_to_diffuse_dict = dict()
		
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
		#	print("MaterialsMtr::get_diffuse_of_material() no material_path in dict {}".format(material_path))
		#	return None
		return self.material_to_diffuse_dict[material_path]
		
	#returns a list of strings material_path(s), which reference diffuse_path; both paths are relative
	def get_materials_using_diffuse(self, diffuse_path):
		diffuse_path = diffuse_path.lower()
		#if diffuse_path not in self.diffuse_to_materials_dict:
		#	print("MaterialsMtr::get_materials_using_diffuse() no diffuse_path in dict {}".format(diffuse_path))
		#	return None
		return self.diffuse_to_materials_dict[diffuse_path]

	#returns a (width, height) tuple
	def get_diffuse_dimensions(self, absolute_diffuse_path):
		absolute_diffuse_path = absolute_diffuse_path.lower()
		#if absolute_diffuse_path not in self.diffuse_to_materials_dict:
		#	print("MaterialsMtr::get_diffuse_dimensions() no diffuse_path in dict {}".format(absolute_diffuse_path))
		#	return None
		return self.fs_diffuse_to_dimensions[absolute_diffuse_path]
			
#Converts between idtech4 and filesystem paths:
#filesystem: C:/pmt_resources/textures/map/textures/folder/texture.png
#   idtech4: /textures/folder/texture
def convert_fs_to_idtech4_path(fs_path, map_textures_path, extension = ".png"):
	idtech4_path = fs_path[len(map_textures_path):-len(extension)]
	return idtech4_path
def convert_idtech4_path_to_fs(idtech4_path, map_textures_path, extension = ".png"):
	if not map_textures_path.endswith('/'):
		map_textures_path += '/'
	return map_textures_path + idtech4_path + extension
	
def parse_mtr_files(map_material_path, map_texture_path = None):
	#
	global_material_to_diffuse_dict = dict()
	
	mtr_files = find_all_files_in(map_material_path, ".mtr")
	for (filename, filepath) in mtr_files:
		material_to_diffuse_dict = load_material_to_diffuse_dict(filepath)
		for material_path in material_to_diffuse_dict:
			diffuse_path = material_to_diffuse_dict[material_path]
			
			diffuse_path_lower = diffuse_path.lower()
			material_path_lower = material_path.lower()
			
			if material_path_lower not in global_material_to_diffuse_dict:
				global_material_to_diffuse_dict[material_path_lower] = diffuse_path_lower
			else:
				DPRINT("warning: material {}] is defined multiple times.".format(material_path_lower))

	#'reverse' global_material_to_diffuse_dict;
	#since global_material_to_diffuse_dict should already be lowercase
	#we do not call lower() here
	global_diffuse_to_materials_dict = dict()	
	
	for material_path in global_material_to_diffuse_dict:
		diffuse_path = global_material_to_diffuse_dict[material_path]
		if diffuse_path not in global_diffuse_to_materials_dict:
			global_diffuse_to_materials_dict[diffuse_path] = list()
		global_diffuse_to_materials_dict[diffuse_path].append(material_path)
	
	#
	for material in global_material_to_diffuse_dict:
		diffuse = global_material_to_diffuse_dict[material]
		DPRINT("material: {} -> {}".format(material, diffuse))
	for diffuse in global_diffuse_to_materials_dict:
		DPRINT("diffuse: {}".format(diffuse))
		material_list = global_diffuse_to_materials_dict[diffuse]
		for material in material_list:
			DPRINT("-> {}".format(material))
		DPRINT("")
		
	#
	mtr_db = MaterialsMtr()
	mtr_db.material_to_diffuse_dict = global_material_to_diffuse_dict
	mtr_db.diffuse_to_materials_dict = global_diffuse_to_materials_dict
	
	#
	if map_texture_path != None:
		png_files = find_all_files_in(map_texture_path, ".png")
		png_fs_fullpaths = list()
		for (filename, filepath) in png_files:
			fs_path = filepath.replace(os.sep, '/')
			fs_path = fs_path.lower()
			png_fs_fullpaths.append(fs_path)
		
		fs_path_to_dimensions = dict()
		for fs_path in png_fs_fullpaths:
			(width, height) = pmt_common_texture.get_image_dimensions(fs_path)
			fs_path_to_dimensions[fs_path] = (width, height)
		mtr_db.fs_diffuse_to_dimensions = fs_path_to_dimensions
		
		fs_path_to_analyze = dict()
		for fs_path in png_fs_fullpaths:
			analyze_dict = pmt_common_json.load_json(fs_path, pmt_common_json.JSON_ANALYZE)
			fs_path_to_analyze[fs_path] = analyze_dict
		mtr_db.fs_diffuse_to_analyze = fs_path_to_analyze
		
		fs_path_to_tags = dict()
		for fs_path in png_fs_fullpaths:
			tags_dict = pmt_common_json.load_json(fs_path, pmt_common_json.JSON_TAGS)
			fs_path_to_tags[fs_path] = tags_dict
		mtr_db.fs_diffuse_to_tags = fs_path_to_tags
	
	#
	return mtr_db
	
if __name__ == "__main__" and not IN_HOUDINI:
	num_argv = len(sys.argv)
	if not (2 <= num_argv and num_argv <= 3):
		print("pmt_materialdb_idtech4_mtr.py [map_materials_path]")
		print("pmt_materialdb_idtech4_mtr.py [map_materials_path] [map_textures_path]")
		exit()
	elif num_argv == 2:
		map_materials_path = sys.argv[1]
		map_textures_path = None
	elif num_argv == 3:
		map_materials_path = sys.argv[1]
		map_textures_path = sys.argv[2]
	else:
		assert False
		exit()
	
	DPRINT("map_materials_path: ".format(map_materials_path))
	DPRINT("map_textures_path: ".format(map_textures_path))
	mtr_db = parse_mtr_files(map_materials_path, map_textures_path)
