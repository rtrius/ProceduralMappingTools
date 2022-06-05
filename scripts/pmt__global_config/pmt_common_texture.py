#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_common_texture
#	script_section_name: 	pmt_common_texture.py
# When run outside of Houdini: this script outputs dimensions of all .bmp, .tga, .png in a directory.
# In Houdini, this module is a library; image dimensions are stored elsewhere.
#
# The dimensions of images need to be stored since the uv 
# mapping process for brushes in (vmf and t3d) uses offsets in pixels.
import os
import sys

import struct

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
	
IN_HOUDINI = 'hou' in sys.modules
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) != 2:
		print("pmt_common_texture.py [search_path]")
		exit()
	else:
		search_path = sys.argv[1]
	
	# search_path is in format C:\dir
	print("search_path: " + search_path)
	
	for dirpath, dirnames_list, filenames_list in os.walk(search_path):
		for filename in filenames_list:
			filepath = dirpath + os.sep + filename
			
			if filepath.endswith(".bmp"):
				x,y = get_bmp_dimensions(filepath)
				print("bmp: {0} - {1} x {2}".format(filepath, x, y))
			if filepath.endswith(".tga"):
				x,y = get_tga_dimensions(filepath)
				print("tga: {0} - {1} x {2}".format(filepath, x, y))
			if filepath.endswith(".png"):
				x,y = get_png_dimensions(filepath)
				print("png: {0} - {1} x {2}".format(filepath, x, y))
				
			if filepath.endswith(".jpg"):
				pass
				

