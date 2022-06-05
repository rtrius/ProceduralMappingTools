#!/usr/bin/env python3
#
#adds the 'color_mean' and 'color_stddev' attrib to texture metadata, which are both tuples:
#	(r, g, b, overall)
#each value is a float [0.0, 1.0]; 'color_mean' is the average color and 'color_stddev' is the standard deviation

import os
import sys
import subprocess

import image_common


def imagemagick_identify(image_path, debug_level = 1):
	if debug_level >= 1:
		print("image: {}".format(image_path))
		
	command_string = list()
	command_string.append("{} -verbose {}".format(image_common.PATH_IMAGEMAGICK_IDENTIFY, image_path))
	
	#Warning: make sure that the command does not end with a ^
	#https://stackoverflow.com/questions/15466298/simple-caret-at-end-of-windows-batch-file-consumes-all-memory
	merged_command = ""
	for comstr in command_string:
		merged_command += comstr
		#print(comstr)
	if debug_level >= 2: 
		print("")
		print(merged_command)
	
	process = subprocess.Popen(merged_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS, text=True)
	(stdoutdata, stderrdata) = process.communicate()
	if debug_level >= 2: 
		print("stdoutdata: {0}".format(stdoutdata))
		print("stderrdata: {0}".format(stderrdata))
	
	#ImageMagick-7.0.8-59-portable-Q16-x64 identify.exe -verbose stdout contains:
	"""
	Image: IMAGE_PATH.png
		Format: PNG (Portable Network Graphics)
		Mime type: image/png
		Class: DirectClass
		Geometry: 1024x1024+0+0
		Units: Undefined
		Colorspace: sRGB
		Type: TrueColor
		Base type: Undefined
		Endianess: Undefined
		Depth: 8-bit
		Channel depth:
			Red: 8-bit
			Green: 8-bit
			Blue: 8-bit
		Channel statistics:
			Pixels: 1048576
			Red:
				min: 0  (0)
				max: 255 (1)
				mean: 128 (0.5)
				standard deviation: 128.0000 (0.5)
				kurtosis: 0.000000
				skewness: 0.000000
				entropy: 0.000000
			Green:
				min: 0  (0)
				max: 255 (1)
				mean: 128 (0.5)
				standard deviation: 128.0000 (0.5)
				kurtosis: 0.000000
				skewness: 0.000000
				entropy: 0.000000
			Blue:
				min: 0  (0)
				max: 255 (1)
				mean: 128 (0.5)
				standard deviation: 128.0000 (0.5)
				kurtosis: 0.000000
				skewness: 0.000000
				entropy: 0.000000
		Image statistics:
			Overall:
				min: 0  (0)
				max: 255 (1)
				mean: 128 (0.5)
				standard deviation: 128.0000 (0.5)
				kurtosis: 0.000000
				skewness: 0.000000
				entropy: 0.000000
		Rendering intent: Perceptual
		Gamma: 0.5
	"""
	#for a greyscale .png, the 'channel statistics' section might instead be of the form:
	"""
		Channel depth:
			Gray: 1-bit
		Channel statistics:
			Pixels: 1048576
			Gray:
				min: 0  (0)
				max: 0 (0)
				mean: 0 (0)
				standard deviation: 0 (0)
				kurtosis: 0
				skewness: 0
				entropy: 0
		Colors: 1
		Histogram:
		   1048576: (  0,  0,  0) #000000 gray(0)
		Colormap entries: 2
		Colormap:
			0: (  0,  0,  0,255) #000000FF graya(0,1)
			1: (255,255,255,255) #FFFFFFFF graya(255,1)
		Rendering intent: Undefined
		Gamma: 0.45455
	"""
	def find_value(stdout_string, color = "red", key = "mean"):
		s = stdout_string.lower()
		channel_index = s.find("channel statistics:")
		gamma_index = s.find("gamma:", channel_index)
		color_index = s.find(color, channel_index, gamma_index)
		if color_index == -1:
			color_index = s.find("gray", channel_index, gamma_index) #note: spelling is 'gray' not 'grey'
		key_index = s.find(key, color_index)
		left_parenthesis = s.find("(", key_index, gamma_index)
		right_parenthesis = s.find(")", key_index, gamma_index)
		#print("channel, gamma: {}, {}".format(channel_index, gamma_index))
		#print("color, key, l, r: {}, {}, {}, {}".format(color_index, key_index, left_parenthesis, right_parenthesis))
		
		value_str = s[left_parenthesis+1:right_parenthesis] #might be '-1.#IND', check for '#ind' since stdout is converted to lowercase
		return float(value_str) if len(value_str) > 0 and not "#ind" in value_str else 0.0
		
	r = find_value(stdoutdata, "red", "mean")
	g = find_value(stdoutdata, "green", "mean")
	b = find_value(stdoutdata, "blue", "mean")
	o = find_value(stdoutdata, "overall", "mean")
	r2 = find_value(stdoutdata, "red", "standard deviation")
	g2 = find_value(stdoutdata, "green", "standard deviation")
	b2 = find_value(stdoutdata, "blue", "standard deviation")
	o2 = find_value(stdoutdata, "overall", "standard deviation")
	
	color_mean = (r, g, b, o)
	color_stddev = (r2, g2, b2, o2)
	if debug_level >= 1:
		print("  color_mean: {}".format(color_mean))
		print("  color_stddev: {}".format(color_stddev))
	return (color_mean, color_stddev)


def extract_image_colors(image_paths):
	assert os.path.exists(image_common.PATH_IMAGEMAGICK_IDENTIFY), "Could not find imagemagick at {0}".format(image_common.PATH_IMAGEMAGICK_IDENTIFY)
	for image_fullpath in image_paths:
		(color_mean, color_stddev) = imagemagick_identify(image_fullpath)
		
		WRITE_JSON = True
		if WRITE_JSON:
			json_dict = image_common.load_json(image_fullpath, image_common.JSON_ANALYZE)
			json_dict["color_mean"] = color_mean
			json_dict["color_stddev"] = color_stddev
			image_common.save_json(json_dict, image_fullpath, image_common.JSON_ANALYZE)

if __name__ == "__main__":
	num_args = len(sys.argv)
	if num_args == 1:
		search_path = image_common.PATH_TEXTURES
	elif num_args == 2:
		search_path = sys.argv[1]
	else:
		print("image_color.py [search_path]")
		exit()
	
	print("search_path: " + search_path)

	bmp_files = image_common.find_all_files_in(search_path, ".bmp")
	png_files = image_common.find_all_files_in(search_path, ".png")
	extract_image_colors(bmp_files + png_files)
	