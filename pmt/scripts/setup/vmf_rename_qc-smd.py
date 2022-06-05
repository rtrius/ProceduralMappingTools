#!/usr/bin/env python3
# vmf_rename_qc-smd.py
# Takes .qc and .smd files unpacked by Crowbar and 
# renames so that .smd files have the same name as the decompiled .mdl
#
# The script is run as:
# 'vmf_rename_qc-smd.py search_path output_path', where
# search_path is the path to search for .qc and .smd files, and
# output_path is the path to write renamed .smd files.
# The folder structure of search_path is also copied to output_path.
#
# Example: if model.mdl is decompiled to model.qc, model_reference.smd, model_physics.smd,
# this script will copy .smd to another directory and rename as:
#		model_reference.smd -> model.mdl.ref.smd
#		model_physics.smd -> model.mdl.phy.smd
import os
import sys
import string
import shutil
	
	
def find_all_files_in(search_path, extension = ".qc"):
	paths = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			#filepath = dirpath + filename
			if filepath.endswith(extension):
				filename = filename.replace(os.sep, '/')
				filepath = filepath.replace(os.sep, '/')
				paths.append((filename, filepath))
				print("{0}: {1}".format(extension, filepath))
	return paths
	
if __name__ == '__main__':
	if len(sys.argv) != 3:
		print("vmf_rename_qc-smd.py [search_path] [output_path]")
		exit()
	else:
		search_path = sys.argv[1]
		output_path = sys.argv[2]
		search_path = search_path.replace(os.sep, '/')
		if not search_path.endswith('/'):
			search_path += '/'
		output_path = output_path.replace(os.sep, '/')
		if not output_path.endswith('/'):
			output_path += '/'
			
	qc_files = find_all_files_in(search_path)
	
	#Decompiling .mdl with Crowbar produces a .qc, *_reference.smd and *_physics.smd.
	#The issue is that the .smd files do not always have the same name as the .mdl file.
	#So, this script reads the .qc, which should have the same name as the .mdl,
	#and renames the .smd files so that they match the .mdl name.
	#
	#Example format of .qc:
	#	$modelname "modelpath/modelname.mdl"
	#
	#	$bodygroup "Body"
	#	{
	#		studio "smd_in_same_folder_main_visual.smd"
	#	}
	#	$collisionmodel "smd_in_same_folder_main_physics.smd"
	#	
	#The key lines we are searching for are: 'studio' in $bodygroup and $collisionmodel.
	#Ignore $modelname since the .qc should already be in the same path as the .mdl.
	#
	for (filename, filepath) in qc_files:
		print("")
		qc_name = filename.replace(".qc", "")
		qc_rel_path = filepath[:filepath.rfind('/')+1].replace(search_path, "")
		
		print("qc_name, qc_rel_path: {}, {}".format(qc_name, qc_rel_path))
		with open(filepath, 'rt') as f:
			print(filepath)
			
			bodygroup_smd_filenames = list()
			collisionmodel_smd_filenames = list()
			
			in_bodygroup = False
			bracket_depth = 0
			for line in f:
				for char in string.whitespace:
					line = line.replace(char, " ")
			
				lowline = line.lower()
				
				if not in_bodygroup:
					if "$bodygroup" in lowline:
						in_bodygroup = True
				else:
					if '{' in lowline: bracket_depth += 1
					if '}' in lowline: bracket_depth -= 1
					
					STUDIO = "studio"
					if bracket_depth == 1 and STUDIO in lowline:
						assert lowline.count('\"') == 2, "no $bodygroup studio quotes in {}".format(filepath)
						left, sep, right = lowline.partition(STUDIO)
						ref_smd = right[right.find('\"')+1:right.rfind('\"')]
						bodygroup_smd_filenames.append(ref_smd)
						print("{} $bodygroup studio: {}".format(filename, ref_smd))
					if bracket_depth == 0:
						in_bodygroup = False
				
				COLLISION = "$collisionmodel"
				if COLLISION in lowline:
					assert lowline.count('\"') == 2, "no collisionmodel quotes in {}".format(filepath)
					left, sep, right = lowline.partition(COLLISION)
					phy_smd = right[right.find('\"')+1:right.rfind('\"')]
					collisionmodel_smd_filenames.append(phy_smd)
					print("{} collisionmodel: {}".format(filename, phy_smd))
			
			out_dir = output_path + qc_rel_path
			if not os.path.exists(out_dir):
				os.makedirs(out_dir)
			
			#there can be multiple bodygroups, for now just select the first one
			if len(bodygroup_smd_filenames) > 0:
				in_path = search_path + qc_rel_path + bodygroup_smd_filenames[0]
				out_path = out_dir + qc_name + ".mdl.ref.smd"
				print(".reference {} -> {}".format(in_path, out_path))
				
				shutil.copyfile(in_path, out_path)
				
			if len(collisionmodel_smd_filenames) > 0:
				assert len(collisionmodel_smd_filenames) == 1
				in_path = search_path + qc_rel_path + collisionmodel_smd_filenames[0]
				out_path = out_dir + qc_name + ".mdl.phy.smd"
				print(".physics {} -> {}".format(in_path, out_path))
				
				shutil.copyfile(in_path, out_path)