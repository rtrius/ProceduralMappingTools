# pmt_material_select.py 2019 06 15
import os
import sys
import re
import random

#texturesets\[type]\[style]\...
#type == t3d, map, or vmf

MATERIAL_ENGINE_STYLE = "!ENGINE"
MATERIAL_CATEGORY_FILENAME_EXTENSION = ".matlist.txt"

EXPORT_TYPE_VMF = "vmf"
EXPORT_TYPE_MAP = "map"
EXPORT_TYPE_T3D = "t3d"

VALID_EXPORT_TYPE = [EXPORT_TYPE_VMF, EXPORT_TYPE_MAP, EXPORT_TYPE_T3D]

PMT_MATERIAL_STYLE = "pmt_material_style"			#string; A style collects multiple material categories
PMT_MATERIAL_CATEGORY = "pmt_material_category"		#string; Category groups multiple materials of similar type: wall, floor, metal, etc.
PMT_MATERIAL_CLUSTER = "pmt_material_cluster"		#int; Cluster is used as seed for random selection

class MaterialData:
	def __init__(self):
		self.style = None
		self.category = None
		self.cluster = None

def has_material_data(houdini_geometry):
	has_material_style = (houdini_geometry.findPrimAttrib(PMT_MATERIAL_STYLE) != None)
	has_material_category = (houdini_geometry.findPrimAttrib(PMT_MATERIAL_CATEGORY) != None)
	has_material_cluster = (houdini_geometry.findPrimAttrib(PMT_MATERIAL_CLUSTER) != None)
	return has_material_style and has_material_category and has_material_cluster
	
def retrieve_material_data(houdini_prim):
	material_data = MaterialData()
	material_data.style = houdini_prim.attribValue(PMT_MATERIAL_STYLE)
	material_data.category = houdini_prim.attribValue(PMT_MATERIAL_CATEGORY)
	material_data.cluster = houdini_prim.attribValue(PMT_MATERIAL_CLUSTER)
	return material_data
	
def select_texture(styles_dict, style_name, category_name, cluster_index, export_type = EXPORT_TYPE_VMF):
	assert export_type in VALID_EXPORT_TYPE, "pmt_material_select select_texture() export_type must be one of {0}".format(VALID_EXPORT_TYPE)

	if style_name not in styles_dict:
		#print("warning: pmt_material_select select_texture() failed to find style {0} for exporter {1}".format(style_name, export_type))
		return None
	if category_name not in styles_dict[style_name]:
		#print("warning: pmt_material_select select_texture() failed to find category {0} in style {1} for exporter {2}".format(category_name, style_name, export_type))
		return None
		
	random.seed(cluster_index)
	
	num_textures = len(styles_dict[style_name][category_name])
	assert num_textures > 0,  "pmt_material_select select_texture() no texture for {0} {1} {2}".format(export_type, style_name, category_name)
	
	material_index = random.randint(0, num_textures - 1) if num_textures > 1 else 0
	return styles_dict[style_name][category_name][material_index]
	
def generate_styles_dict(materialset_path, export_type):
	generate_styles_dict_DEBUG = False

	assert export_type in VALID_EXPORT_TYPE, "error: invalid export type; must be one of " + str(VALID_EXPORT_TYPE)
	assert os.path.exists(materialset_path), "error: materialset_path does not exist:" + materialset_path
	
	materialset_path += os.sep
	if generate_styles_dict_DEBUG:
		print("materialset_path: " + materialset_path)
	
	#styles_dict[STYLE_NAME][CATEGORY_NAME]
	#dict() containing dict() containing list()
	styles_dict = dict()
	
	for dirpath, dirnames_list, filenames_list in os.walk(materialset_path):
		for file_name in filenames_list:
			if not file_name.endswith(MATERIAL_CATEGORY_FILENAME_EXTENSION):
				continue
		
			file_path = dirpath + os.sep + file_name
			relative_path = file_path.replace(materialset_path, "")
			
			material_style = relative_path[0:relative_path.find(os.sep)].lower()
			material_category = file_name.replace(MATERIAL_CATEGORY_FILENAME_EXTENSION, "").lower()
			
			if generate_styles_dict_DEBUG:
				print("filepath: " + file_path)
				print("rel path: " + relative_path)
				
				print("style: " + material_style)
				print("category: " + material_category)
			
			if material_style not in styles_dict:
				styles_dict[material_style] = dict()
			
			if material_category not in styles_dict[material_style]:
				styles_dict[material_style][material_category] = list()
			
			file = open(file_path, 'r')
			for line in file:
				if not re.search("[a-zA-Z0-9]", line):
					print("warning: line with no alphanumeric chars; ignoring: " + line)
					continue
				
				line = line.replace("\r", "").replace("\n", "")
				
				if generate_styles_dict_DEBUG:
					print("material: " + line)
				styles_dict[material_style][material_category].append(line)
	return styles_dict		

#extracts styles and categories for a Houdini menu parameter script
def generate_style_category_menus(styles_dict):
	styles_menu = list()
	categories_menu = dict()

	for style in styles_dict:
		styles_menu.append(style)
		styles_menu.append(style)
		
		if style not in categories_menu:
			categories_menu[style] = list()
		for category in styles_dict[style]:
			categories_menu[style].append(category)
			categories_menu[style].append(category)
	return (styles_menu, categories_menu)
	
class MaterialSets:
	def __init__(self):
		self.export_type = ""
		self.styles_dict = None
		self.hou_menu_styles = None
		self.hou_menu_categories = None #hou_menu_categories[style] == list()
	def load_styles(self, materialset_path, export_type):
		self.export_type = export_type
		self.styles_dict = generate_styles_dict(materialset_path, export_type)
		self.hou_menu_styles, self.hou_menu_categories = generate_style_category_menus(self.styles_dict)
		
IN_HOUDINI = 'hou' in sys.modules
if __name__ == "__main__" and not IN_HOUDINI:
	if len(sys.argv) == 3:
		export_type = sys.argv[1]
		materialset_path = sys.argv[2]
	elif len(sys.argv) == 2:
		export_type = sys.argv[1]
		materialset_path = os.getcwd()
	else:
		print("pmt_material_select.py export_type [materialset_path]")
		print("[export_type] is one of " + str(VALID_EXPORT_TYPE))
		print("[materialset_path] is optional; refers to the directory containing texturesets folder")
		exit()
		
	generate_styles_dict(materialset_path, export_type)