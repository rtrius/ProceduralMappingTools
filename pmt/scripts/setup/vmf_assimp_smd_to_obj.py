#!/usr/bin/env python3
# vmf_assimp_smd_to_obj.py - uses assimp.exe to convert .smd to .obj
#
# For setup run 'vmf_assimp_smd_to_obj.py -d'.
# This script should be run from 'C:/pmt/scripts/setup/';
# the current working directory must be 'C:/pmt/scripts/setup/'.
#
# search_path is in format C:\dir

import os
import sys
import subprocess

PATH_ASSIMP = "../../bin/assimp-sdk-4.1.0/bin/x64/assimp.exe"
PATH_ASSIMP_QUOTES = "\"" + PATH_ASSIMP + "\""

DEFAULT_SEARCH_PATH = "../../models/vmf"
	
if __name__ == '__main__':
	if len(sys.argv) != 2:
		print("vmf_assimp_smd_to_obj.py [search_path] -- to convert all .smd to .obj in search_path")
		print("vmf_assimp_smd_to_obj.py -d -- to convert all .smd to .obj in {}".format(DEFAULT_SEARCH_PATH))
		exit()
	else:
		search_path = sys.argv[1]
		if search_path == "-d":
			cwd = os.getcwd()
			(cwd, first_folder) = os.path.split(cwd)
			(cwd, second_folder) = os.path.split(cwd)
			if first_folder.lower() != "setup" or second_folder.lower() != "scripts":
				print("When using -d, this script must be run from /pmt/scripts/setup/.")
				exit()
			search_path = DEFAULT_SEARCH_PATH
	
	if not os.path.exists(PATH_ASSIMP):
		print("Could not find assimp.exe (PATH_ASSIMP={})".format(PATH_ASSIMP))
		exit()
		
	print("search_path: " + search_path)
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath.replace(os.sep, "/") + "/" + filename
			
			if not filepath.endswith(".smd"):
				continue
			
			#wavefront obj; Houdini calls gwavefront.exe
			command_string = "{0} {1} {2} {3}".format(PATH_ASSIMP_QUOTES, "export", filepath, filepath + ".obj")
			
			#Warning: make sure that the subprocess.call() command does not end with a ^
			#https://stackoverflow.com/questions/15466298/simple-caret-at-end-of-windows-batch-file-consumes-all-memory
			print(command_string)
			print("")
			
			subprocess.call(command_string)
			
