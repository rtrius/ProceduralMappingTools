#!/usr/bin/env python3
#
#Runs image_similar.py with fuzz == 15.

import sys

import image_common
import image_similar

if __name__ == "__main__":
	num_args = len(sys.argv)
	if num_args == 1:
		search_path = image_common.PATH_TEXTURES
	elif num_args == 2:
		search_path = sys.argv[1]
	else:
		print("image_similar15.py [search_path]")
		exit()
	
	print("search_path: " + search_path)

	fuzz = 15
	image_similar.run_similar(search_path, fuzz)
	