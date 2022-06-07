#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_sounddb_unreal1
#	script_section_name: 	pmt_sounddb_unreal1.py
# pmt_sounddb_unreal1 collects .wav sound paths from the global config 't3d_sounds_path'.

import os
import sys
	
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
###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__

class SoundsUax:
	def __init__(self):
		#converts betweeen unreal_paths as would be found in a .t3d/.utx file
		#and the actual filesystem path on disk(Houdini only)
		self.unreal_path_to_filesystem_path = dict()
		self.filesystem_path_to_unreal_path = dict()
	
	#retuns an absolute path
	def get_filesystem_path(self, unreal_path):
		unreal_path = unreal_path.lower()
		#if unreal_path not in self.unreal_path_to_filesystem_path:
		#	print("SoundsUax::get_filesystem_path() no fs path for unreal path {}.".format(unreal_path))
		#	return None
		return self.unreal_path_to_filesystem_path[unreal_path]
		
	#returns string; filesystem_path is a absolute path(not relative path)
	def get_unreal_path(self, filesystem_path):
		filesystem_path = filesystem_path.lower()
		#if filesystem_path not in self.filesystem_path_to_unreal_path:
		#	print("SoundsUax::get_unreal_path() no unreal path for fs path {}.".format(filesystem_path))
		#	return None
		return self.filesystem_path_to_unreal_path[filesystem_path]

		
def make_unreal_path_from_fs_path(filesystem_path, t3d_base_path, assettype = "Textures", extension = ".bmp", path_sep = os.sep):
		#a texture with unreal_path:
		#	PACKAGE.FOLDER.texture
		#might have an filesystem path:
		#	C:\pmt\textures\t3d\PACKAGE\Textures\FOLDER\texture.bmp
		#with t3d_base_path:#
		#	C:\pmt\textures\t3d
		assettype = assettype.lower()
		
		#removes 'C:\pmt\textures\t3d'
		#leaving '\PACKAGE\Textures\FOLDER\texture.bmp'
		unreal_path = filesystem_path[len(t3d_base_path):].lower()
		
		#removes '.bmp' -> '\PACKAGE\Textures\FOLDER\texture'
		#unreal_path = unreal_path[:-len(".bmp")]
		unreal_path = unreal_path[:-len(extension)]
		
		#using UnrealEd 2.1 batch export to .bmp adds a \Textures\ folder 
		#in-between PACKAGE and FOLDER that needs to be removed
		#textures = os.sep + "Textures" + os.sep
		textures = path_sep + assettype + path_sep
		
		#replace the leftmost '\Textures\' with '\'
		#to get: '\PACKAGE\FOLDER\texture'
		assert textures in unreal_path, "unreal1 db error: could not find '{}' in '{}'".format(textures, unreal_path)
		textures_index = unreal_path.index(textures)
		textures_len = len(textures)
		unreal_path = unreal_path[:textures_index] + path_sep + unreal_path[textures_index+textures_len:]
		
		#replace slashes with dots
		#to get: '.PACKAGE.FOLDER.texture'
		unreal_path = unreal_path.replace(path_sep, ".")
		if unreal_path.startswith("."):
			unreal_path = unreal_path[1:]
		
		return unreal_path

def generate_unreal_paths_from_wav(t3d_sounds_path):
	#
	unreal_path_to_fs_path = dict()
	fs_path_to_unreal_path = dict()
	
	wav_files = find_all_files_in(t3d_sounds_path, ".wav")
	for (filename, filepath) in wav_files:
		unreal_path = make_unreal_path_from_fs_path(filepath, t3d_sounds_path, "Sounds", ".wav")
		
		#store paths
		fs_path = filepath.replace(os.sep, '/')
		fs_path = fs_path.lower()
		unreal_path_to_fs_path[unreal_path] = fs_path
		fs_path_to_unreal_path[fs_path] = unreal_path
		
		DPRINT("{} -> {}".format(fs_path, unreal_path))
		
	#
	uax_db = SoundsUax()
	uax_db.unreal_path_to_filesystem_path = unreal_path_to_fs_path
	uax_db.filesystem_path_to_unreal_path = fs_path_to_unreal_path
	return uax_db
	
		
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("pmt_sounddb_unreal1.py [search_path]")
		exit()
	else:
		search_path = sys.argv[1]
	
	DPRINT("search_path: " + search_path)
	uax_db = generate_unreal_paths_from_wav(search_path)
