#!/usr/bin/env python3
#
#adds the 'size' attrib to texture metadata, which is a tuple:
#	(width, height)

import image_common
import sys

if __name__ == "__main__":
	num_args = len(sys.argv)
	if num_args == 1:
		search_path = image_common.PATH_TEXTURES
	elif num_args == 2:
		search_path = sys.argv[1]
	else:
		print("image_size.py [search_path]")
		exit()
	
	print("search_path: " + search_path)

	
	bmp_files = image_common.find_all_files_in(search_path, ".bmp")
	png_files = image_common.find_all_files_in(search_path, ".png")
	
	for image_path in bmp_files + png_files:
		size = image_common.get_image_dimensions(image_path)
		
		json_dict = image_common.load_json(image_path, image_common.JSON_ANALYZE)
		json_dict["size"] = size
		image_common.save_json(json_dict, image_path, image_common.JSON_ANALYZE)
	