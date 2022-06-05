#!/usr/bin/env python3
import os
import struct
import json

PATH_IMAGEMAGICK_MAGICK = "..\\..\\bin\\ImageMagick-7.0.8-59-portable-Q16-x64\\magick.exe"
PATH_IMAGEMAGICK_IDENTIFY = "..\\..\\bin\\ImageMagick-7.0.8-59-portable-Q16-x64\\identify.exe"
PATH_IMAGEMAGICK_COMPARE = "..\\..\\bin\\ImageMagick-7.0.8-59-portable-Q16-x64\\compare.exe"

#imagemagick compare.exe requires an output file parameter
PATH_IMAGEMAGIC_DIFF = "imagemagick_temp_diff.bmp" 

PATH_TEXTURES = "..\\..\\textures\\"

		
def find_all_files_in(search_path, extension):
	path_list = list()
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			
			if not filepath.endswith(extension):
				continue
			
			print(extension + ": " + filepath.replace(search_path, ""))
			path_list.append(filepath)
	return path_list
	
#images are in .bmp or .png format; image metadata is stored in the same folder as:
#	IMAGE_PATH.analyze.txt for automatic analysis
#	IMAGE_PATH.tags.txt for manually added user tags
#json format is used; the top level item is a dict()
	
JSON_ANALYZE = "analyze"
JSON_TAGS = "tags"
	
def save_json(image_dict, image_path, json_type="analyze"):
	json_path = "{}.{}.txt".format(image_path, json_type)
	with open(json_path, "w", encoding=None) as json_out:
		json.dump(image_dict, json_out, indent='\t', sort_keys=True)

def load_json(image_path, json_type="analyze"):
	json_path = "{}.{}.txt".format(image_path, json_type)
	if not os.path.exists(json_path):
		return dict()

	with open(json_path, "r", encoding=None) as json_in:
		f_in = json.load(json_in)
		
	return f_in
	
	
	
def get_bmp_dimensions(filepath):
	file = open(filepath, 'rb')
	
	B = file.read(1)
	assert B == b'B'	#'B'
	M = file.read(1)
	assert M == b'M'	#'M'
	
	file.seek(14)
	header_size = struct.unpack('<l', file.read(4))[0]	#signed int32
	assert header_size == 40, "header_size != 40: {0}".format(header_size)	#Windows BITMAPINFOHEADER
	
	file.seek(18)
	width = struct.unpack('<l', file.read(4))[0]	#signed int32, little-endian
	file.seek(22)
	height = struct.unpack('<l', file.read(4))[0]	#signed int32, little-endian
	
	file.close()
	return (width, height)
	
def get_tga_dimensions(filepath):
	file = open(filepath, 'rb')
	
	#TGA 2.0 specification does not specify whether these are signed; assume unsigned 
	file.seek(12)
	width = struct.unpack('<H', file.read(2))[0]	#unsigned int16
	file.seek(14)
	height = struct.unpack('<H', file.read(2))[0]	#unsigned int16
	
	file.close()
	return (width, height)

def get_png_dimensions(filepath):
	file = open(filepath, 'rb')
	
	#First 8 bytes of .png are always
	png_id = [137, 80, 78, 71, 13, 10, 26, 10]
	for i in range(len(png_id)):
		b = file.read(1)
		assert int.from_bytes(b, byteorder='big') == png_id[i], "png_id byte #{}, {}, is not {} in ".format(i, b, png_id[i], filepath)
	
	#PNG 1.2 specification does not specify whether these are signed.
	#However it states that the max value is 2^31 - 1. Assume signed.
	file.seek(16)
	width = struct.unpack('>l', file.read(4))[0]	#signed int32, big-endian
	file.seek(20)
	height = struct.unpack('>l', file.read(4))[0]	#signed int32, big-endian
	
	file.close()
	return (width, height)
	
def get_image_dimensions(filepath):
	if filepath.endswith(".bmp"):
		return get_bmp_dimensions(filepath)
	if filepath.endswith(".tga"):
		return get_tga_dimensions(filepath)
	if filepath.endswith(".png"):
		return get_png_dimensions(filepath)
	
	assert False, "unsupported image format; must be .bmp, .tga, or .png"
	return (None, None)