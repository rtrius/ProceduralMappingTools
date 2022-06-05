#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_common_json
#	script_section_name: 	pmt_common_json.py

import os
import json

##### this section must match scripts/analyze/image_common.py #####
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
##### this section must match scripts/analyze/image_common.py #####