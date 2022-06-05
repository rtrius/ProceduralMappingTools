#!/usr/bin/env python3
#
#Adds the 'similar#_names' and 'similar#_fracs' attrib to texture metadata, which is a list of tuples:
# similar#_names == the name of a .bmp or .png image in the same folder,
# similar#_fracs == the fraction of pixels that match in both images, where 0 == no matches and 1 all match.
#
#Where # is 'fuzz' parameter used by imagemagick compare.exe. 
#Fuzz is a parameter [0, 100] that determines how different 2 pixels need to be in order to be considered the same.
#0 == exact match, higher values mean that images with more differing pixels will be marked as 'similar'.

import os
import sys

import subprocess
import multiprocessing

import image_common


def imagemagick_compare(image_path_a, image_path_b, fuzz = 0, debug_level = 0):
	metric = "AE"	#Absolute difference in pixels
	#metric = "RMSE"	#Root mean squared
	#metric = "SSIM"	#Structural similarity index

	command_string = list()
	command_string.append(image_common.PATH_IMAGEMAGICK_COMPARE)
	if fuzz == 0:
		command_string.append(" -metric {} \"{}\" \"{}\" \"{}\"".format(metric, image_path_a, image_path_b, image_common.PATH_IMAGEMAGIC_DIFF))
	else:
		command_string.append(" -fuzz {}% -metric {} \"{}\" \"{}\" \"{}\"".format(int(fuzz), metric, image_path_a, image_path_b, image_common.PATH_IMAGEMAGIC_DIFF))
	
	#Warning: make sure that the command does not end with a ^
	#https://stackoverflow.com/questions/15466298/simple-caret-at-end-of-windows-batch-file-consumes-all-memory
	merged_command = ""
	for comstr in command_string:
		merged_command += comstr
		#print(comstr)
	if debug_level >= 2: 
		print("")
		print(merged_command)
	
	process = subprocess.Popen(merged_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
	(stdoutdata, stderrdata) = process.communicate()
	if debug_level >= 2: 
		print("stdoutdata: {0}".format(stdoutdata))
		print("stderrdata: {0}".format(stderrdata))
	
	#compare.exe should output the number of pixels that differ ("-metric AE") at STDERR
	pixel_diff = float(stderrdata) #cast to float, not int, since scientific notation('1.0e+005') is sometimes used 
	return pixel_diff

def find_similar_image_list(args):
	(image_fullpath_a, image_paths, size_dict, fuzz) = args
	
	size_a = size_dict[image_fullpath_a]
	(folder_a, filename_a) = os.path.split(image_fullpath_a)
	num_pixels = float(size_a[0] * size_a[1])
	
	result_list = list()
	for image_fullpath_b in image_paths:
		if image_fullpath_a == image_fullpath_b:
			continue
			
		size_b = size_dict[image_fullpath_b]
		(folder_b, filename_b) = os.path.split(image_fullpath_b)
		
		#only search for images in same folder, for performance
		if folder_a != folder_b:
			continue
		
		if size_a != size_b:
			continue
		
		diff_pixels = imagemagick_compare(image_fullpath_a, image_fullpath_b, fuzz, 0)
		match_pixels = num_pixels - diff_pixels
		similarity = match_pixels / num_pixels
		
		MATCH_THRESHOLD = 0.25
		if similarity > MATCH_THRESHOLD:
			result_list.append((filename_b, similarity))
	return result_list
			
			
#for each image, construct a list of similar images
def build_match_dict(image_paths, keyname = "similar", fuzz = 0, DEBUG_LEVEL = 1):
	assert os.path.exists(image_common.PATH_IMAGEMAGICK_COMPARE), "Could not find imagemagick at {0}".format(image_common.PATH_IMAGEMAGICK_COMPARE)
	assert not os.path.exists(image_common.PATH_IMAGEMAGIC_DIFF), "PATH_IMAGEMAGIC_DIFF is '{}' and exists; it should be set to an invalid path(or disable this assert, and the file will be overwritten)".format(image_common.PATH_IMAGEMAGIC_DIFF)
	
	num_images = len(image_paths)
	
	size_dict = dict()
	for image_fullpath in image_paths:
		size_dict[image_fullpath] = image_common.get_image_dimensions(image_fullpath)
		
	match_dict = dict()
	for image_fullpath in image_paths:
		match_dict[image_fullpath] = list()
	
	MULTIHTHREADED = True
	if not MULTIHTHREADED:
		for image_a_index in range(num_images):
			image_fullpath_a = image_paths[image_a_index]
			size_a = size_dict[image_fullpath_a]
			num_pixels = float(size_a[0] * size_a[1])
			
			(folder_a, filename_a) = os.path.split(image_fullpath_a)
			
			print("image: {0} / {1}: {2}".format(image_a_index, num_images, image_fullpath_a))
			for image_b_index in range(image_a_index + 1, num_images):
				image_fullpath_b = image_paths[image_b_index]
				size_b = size_dict[image_fullpath_b]
				(folder_b, filename_b) = os.path.split(image_fullpath_b)
				
				#only search for images in same folder, for performance
				if folder_a != folder_b:
					continue
				
				if size_a != size_b:
					continue
					
				diff_pixels = imagemagick_compare(image_fullpath_a, image_fullpath_b, fuzz, DEBUG_LEVEL)
				match_pixels = num_pixels - diff_pixels
				similarity = match_pixels / num_pixels
				if DEBUG_LEVEL >= 2: print("match: {0} ({1}/{2})".format(similarity, match_pixels, num_pixels))
				
				MATCH_THRESHOLD = 0.25
				if similarity > MATCH_THRESHOLD:
					match_dict[image_fullpath_a].append((filename_b, similarity))
					match_dict[image_fullpath_b].append((filename_a, similarity))
	else:
		args = list()
		for path in image_paths:
			args.append((path, image_paths, size_dict, fuzz))
			
		BLOCK_SIZE = 256
		DEBUG_SINGLE_BLOCK = False
		if DEBUG_SINGLE_BLOCK:
			args = args[:BLOCK_SIZE]
		
		while len(args) > 0:
			current_args = args[:BLOCK_SIZE]
			p = multiprocessing.Pool()
			results = p.map(find_similar_image_list, current_args)
			
			for i in range(len(current_args)):
				image_fullpath_a = current_args[i][0]
				image_a_similar_list = results[i]
				match_dict[image_fullpath_a] = image_a_similar_list
			
			args = args[BLOCK_SIZE:]
			print("image: {} / {}: {}".format(num_images - len(args), num_images, current_args[0][0]))
		
	for image_fullpath in match_dict:
		similiar_tuples = match_dict[image_fullpath]
		if len(similiar_tuples) == 0: continue
		if DEBUG_LEVEL >= 1: print("save_json: {}, ({} matches)): {}".format(image_fullpath, len(similiar_tuples), similiar_tuples))
		
		#split tuples by var type, since VEX dict entries do not support multiple types in a single array
		similar_names = list()
		similar_fracs = list()
		for (filename, similarity) in similiar_tuples:
			similar_names.append( filename.lower() ) #all .analyze.txt entries are lowercase
			similar_fracs.append(similarity)
		
		json_dict = image_common.load_json(image_fullpath, image_common.JSON_ANALYZE)
		json_dict["{}{}_names".format(keyname, int(fuzz))] = similar_names
		json_dict["{}{}_fracs".format(keyname, int(fuzz))] = similar_fracs
		image_common.save_json(json_dict, image_fullpath, image_common.JSON_ANALYZE)
		
	return match_dict

def run_similar(search_path, fuzz):
	bmp_files = image_common.find_all_files_in(search_path, ".bmp")
	png_files = image_common.find_all_files_in(search_path, ".png")
	build_match_dict(bmp_files + png_files, "similar", fuzz)

if __name__ == "__main__":
	num_args = len(sys.argv)
	if num_args == 1:
		search_path = image_common.PATH_TEXTURES
	elif num_args == 2:
		search_path = sys.argv[1]
	else:
		print("image_similar.py [search_path]")
		exit()
	
	print("search_path: " + search_path)

	fuzz = 0
	run_similar(search, fuzz)
	