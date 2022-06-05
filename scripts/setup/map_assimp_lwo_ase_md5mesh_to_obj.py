#!/usr/bin/env python3
# map_assimp_lwo_ase_md5mesh_to_obj.py - uses assimp.exe to convert .lwo/.ase/.md5mesh to .obj
#
# For setup run 'map_assimp_lwo_ase_md5mesh_to_obj.py -d'.
# This script should be run from 'C:/pmt_resources/scripts/setup/';
# the current working directory must be 'C:/pmt_resources/scripts/setup/'.
#
# search_path is in format C:\dir

import os
import sys
import subprocess

PATH_ASSIMP = "../../bin/assimp-sdk-4.1.0/bin/x64/assimp.exe"
PATH_ASSIMP_QUOTES = "\"" + PATH_ASSIMP + "\""

DEFAULT_SEARCH_PATH = "../../models/map"

if __name__ == '__main__':
	if len(sys.argv) != 2:
		print("t3d_assimp_3d_to_obj.py [search_path] -- to convert all .lwo/.ase/.md5mesh to .obj in search_path")
		print("t3d_assimp_3d_to_obj.py -d -- to convert all .lwo/.ase/.md5mesh to .obj in {}".format(DEFAULT_SEARCH_PATH))
		exit()
	else:
		search_path = sys.argv[1]
		if search_path == "-d":
			cwd = os.getcwd()
			(cwd, first_folder) = os.path.split(cwd)
			(cwd, second_folder) = os.path.split(cwd)
			if first_folder.lower() != "setup" or second_folder.lower() != "scripts":
				print("When using -d, this script must be run from /pmt_resources/scripts/setup/.")
				exit()
			search_path = DEFAULT_SEARCH_PATH
	
	if not os.path.exists(PATH_ASSIMP):
		print("Could not find assimp.exe (PATH_ASSIMP={})".format(PATH_ASSIMP))
		exit()
	
	print("search_path: " + search_path)
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath.replace(os.sep, "/") + "/" + filename
			
			if not (filepath.endswith(".lwo") or filepath.endswith(".ase")): #or filepath.endswith(".md5mesh")): #assimp crashes on .md5mesh convert often
				continue
			
			#wavefront obj; Houdini calls gwavefront.exe
			command_string = "{0} {1} {2} {3}".format(PATH_ASSIMP_QUOTES, "export", filepath, filepath + ".obj")
		
			#Warning: make sure that the command does not end with a ^
			#https://stackoverflow.com/questions/15466298/simple-caret-at-end-of-windows-batch-file-consumes-all-memory
			print(command_string)
			print("")
		
			subprocess.call(command_string)

