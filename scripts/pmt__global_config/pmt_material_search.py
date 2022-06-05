#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_material_search
#	script_section_name: 	pmt_material_search.py

import os
import sys
import string
import math

###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules
import hou
if hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config") != None:
	PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt__global_config = PMT__G_CFG.pmt__global_config
	
	#0 for internal modules,
	#1 for 'higher-level' modules in pmt__global_config, and 
	#2+ for external nodes and modules
	PMT_REFLEVEL = 1
	if PMT_REFLEVEL >= 0:
		pmt_common = PMT__G_CFG.pmt_common
		pmt_common_texture = PMT__G_CFG.pmt_common_texture
		pmt_common_json = PMT__G_CFG.pmt_common_json
	if PMT_REFLEVEL >= 1:
		pmt_parse_source1_fgd = PMT__G_CFG.pmt_parse_source1_fgd
		pmt_parse_unreal1_uc = PMT__G_CFG.pmt_parse_unreal1_uc
		pmt_parse_idtech4_def = PMT__G_CFG.pmt_parse_idtech4_def
		pmt_materialdb_source1_vmt = PMT__G_CFG.pmt_materialdb_source1_vmt
		pmt_materialdb_unreal1 = PMT__G_CFG.pmt_materialdb_unreal1
		pmt_materialdb_idtech4_mtr = PMT__G_CFG.pmt_materialdb_idtech4_mtr
		pmt_sounddb_source1 = PMT__G_CFG.pmt_sounddb_source1
		pmt_sounddb_unreal1 = PMT__G_CFG.pmt_sounddb_unreal1
		pmt_sounddb_idtech4_sndshd = PMT__G_CFG.pmt_sounddb_idtech4_sndshd
		pmt_meshdb_unreal1 = PMT__G_CFG.pmt_meshdb_unreal1
	if PMT_REFLEVEL >= 2:
		pmt_material_select = PMT__G_CFG.pmt_material_select
		pmt_material_search = PMT__G_CFG.pmt_material_search
###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__

IN_HOUDINI = 'hou' in sys.modules
def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
def get_materials(pmt_engine = "vmf"):
	if pmt_engine == "vmf":
		material_paths = list()
		for material in PMT__G_CFG.vmf_materialdb.material_to_diffuse_dict:
			material_paths.append(material)
		return material_paths
	elif pmt_engine == "t3d":
		material_paths = list()
		for unreal_path in PMT__G_CFG.t3d_materialdb.unreal_path_to_filesystem_path:
			material_paths.append(unreal_path)
		return material_paths
	elif pmt_engine == "map":
		material_paths = list()
		for material in PMT__G_CFG.map_materialdb.material_to_diffuse_dict:
			material_paths.append(material)
		return material_paths
	return material_paths
	
	assert False, "MaterialsetsSelector get_materials() invalid pmt_engine {}".format(pmt_engine)
	return None
	
def get_diffuse_fs(pmt_engine, material_path):
	if pmt_engine == "vmf":
		diffuse_relpath = PMT__G_CFG.vmf_materialdb.get_diffuse_of_material(material_path)
		vmf_textures_path = PMT__G_CFG.g_cfg.get_config("vmf", "vmf_textures_path")
		diffuse_fs = pmt_materialdb_source1_vmt.convert_source_path_to_fs(diffuse_relpath, vmf_textures_path)
		return diffuse_fs
	elif pmt_engine == "t3d":
		return PMT__G_CFG.t3d_materialdb.get_filesystem_path(material_path)
	elif pmt_engine == "map":
		diffuse_relpath = PMT__G_CFG.map_materialdb.get_diffuse_of_material(material_path)
		map_textures_path = PMT__G_CFG.g_cfg.get_config("map", "map_textures_path")
		diffuse_fs = pmt_materialdb_idtech4_mtr.convert_idtech4_path_to_fs(diffuse_relpath, map_textures_path)
		return diffuse_fs
	
	assert False, "MaterialsetsSelector get_diffuse_fs() invalid pmt_engine {}".format(pmt_engine)
	return None
	
def get_materials_using_diffuse_fs(pmt_engine, diffuse_absolute_fs_path):
	if pmt_engine == "vmf":
		vmf_textures_path = PMT__G_CFG.g_cfg.get_config("vmf", "vmf_textures_path")
		diffuse_fs = pmt_materialdb_source1_vmt.convert_fs_to_source_path(diffuse_absolute_fs_path, vmf_textures_path)
		return PMT__G_CFG.vmf_materialdb.diffuse_to_materials_dict[diffuse_fs]
	elif pmt_engine == "t3d":
		#vmf and map are lists, while t3d is a string, but return a list for consistency
		return [ PMT__G_CFG.t3d_materialdb.filesystem_path_to_unreal_path[diffuse_fs_path] ]
	elif pmt_engine == "map":
		map_textures_path = PMT__G_CFG.g_cfg.get_config("map", "map_textures_path")
		diffuse_fs = pmt_materialdb_idtech4_mtr.convert_fs_to_idtech4_path(diffuse_absolute_fs_path, map_textures_path)
		return PMT__G_CFG.map_materialdb.diffuse_to_materials_dict[diffuse_fs]
	
	assert False, "MaterialsetsSelector get_materials_using_diffuse_fs() invalid pmt_engine {}".format(pmt_engine)
	return None
	
def get_path_sep(pmt_engine = "vmf"):
	if pmt_engine == "vmf":
		return '/'
	elif pmt_engine == "t3d":
		return '.'
	elif pmt_engine == "map":
		return '/'
		
	assert False, "MaterialsetsSelector get_path_sep() invalid pmt_engine {}".format(pmt_engine)
	return None

def get_material_analyze_dict(pmt_engine, material_path):
	diffuse_fs = get_diffuse_fs(pmt_engine, material_path)
	if pmt_engine == "vmf" and diffuse_fs in PMT__G_CFG.vmf_materialdb.fs_diffuse_to_analyze:
		return PMT__G_CFG.vmf_materialdb.fs_diffuse_to_analyze[diffuse_fs]
	elif pmt_engine == "t3d" and diffuse_fs in PMT__G_CFG.t3d_materialdb.filesystem_path_to_analyze:
		return PMT__G_CFG.t3d_materialdb.filesystem_path_to_analyze[diffuse_fs]
	elif pmt_engine == "map" and diffuse_fs in PMT__G_CFG.map_materialdb.fs_diffuse_to_analyze:
		return PMT__G_CFG.map_materialdb.fs_diffuse_to_analyze[diffuse_fs]
		
	#assert pmt_engine in ["vmf", "t3d", "map"], "MaterialsetsSelector get_material_analyze_dict() invalid pmt_engine {}".format(pmt_engine)
	return None
def get_material_tags_dict(pmt_engine, material_path):
	diffuse_fs = get_diffuse_fs(pmt_engine, material_path)
	if pmt_engine == "vmf" and diffuse_fs in PMT__G_CFG.vmf_materialdb.fs_diffuse_to_tags:
		return PMT__G_CFG.vmf_materialdb.fs_diffuse_to_tags[diffuse_fs]
	elif pmt_engine == "t3d" and diffuse_fs in PMT__G_CFG.t3d_materialdb.filesystem_path_to_tags:
		return PMT__G_CFG.t3d_materialdb.filesystem_path_to_tags[diffuse_fs]
	elif pmt_engine == "map" and diffuse_fs in PMT__G_CFG.map_materialdb.fs_diffuse_to_tags:
		return PMT__G_CFG.map_materialdb.fs_diffuse_to_tags[diffuse_fs]
		
	#assert pmt_engine in ["vmf", "t3d", "map"], "MaterialsetsSelector get_material_tags_dict() invalid pmt_engine {}".format(pmt_engine)
	return None
	
def perform_material_search(pmt_engine, materials_list, query):
	if len(query) == 0:
		report_string = "No search query entered."
		return None, report_string
		
	query = query.lower()

	def tokenize_query(query):
		def simplify_whitespace(text):
			for char in string.whitespace:
				text = text.replace(char, " ")
			return text
		query = simplify_whitespace(query)
		
		def pad_operators(text):
			PAD_CHARS = "{}"
			for char in PAD_CHARS:
				text = text.replace(char, " {} ".format(char))
			return text
		query = pad_operators(query)
		
		def compact_spaces(text):
			SPACES_4 = "    "
			SPACES_2 = "  "
			while text.find(SPACES_4) != -1:
				text = text.replace(SPACES_4, " ")
			while text.find(SPACES_2) != -1:
				text = text.replace(SPACES_2, " ")
			return text
		query = compact_spaces(query)
		
		#
		tokens = query.split(sep = " ", maxsplit = -1)
		
		while "" in tokens:
			tokens.remove("")
		
		#DPRINT("tokens: {}".format(tokens))	
		return tokens
	query_tokens = tokenize_query(query)
	
	def validate_query(tokens):
		num_tokens = len(tokens)
		for i in range(num_tokens):
			t = tokens[i]
			if t == "{":
				t_next = tokens[i+1]
				if not t_next.startswith("similar0?") and not t_next.startswith("similar5?") and not t_next.startswith("similar15?"):
					return False, "Similar search is in the format {similar0?0.5}, {similar5?0.5} or {similar15?0.5}"
			if t.startswith("color:"):
				color_parms = t[len("color:")]
				rgbv = color_parms.split(",")
				for t2 in rgbv:
					if not t2.isdecimal():
						return False, "'color:' search is in the format 'color:r,g,b,match', where r, g, b, and match are all floats from 0 to 1."
				if len(rgbv) != 4:
					return False, "'color:' search is in the format 'color:r,g,b,match', where r, g, b, and match are all floats from 0 to 1."
					
		if tokens.count("{") != tokens.count("}"):
			return False, "Missing closing bracket for similar search '{' '}'"
			
		return True, "success"
	is_query_valid, validation_message = validate_query(query_tokens)
	if not is_query_valid:
		return None, validation_message
		
	def extract_subsearches(tokens):
		subsearches = list()
		while tokens.count("{") > 0:
			lo = tokens.index("{")
			hi = tokens.index("}") + 1
			
			subsearches.append(tokens[lo:hi])
			tokens = tokens[:lo] + tokens[hi:]
		return tokens, subsearches
		
	query_tokens, subsearches = extract_subsearches(query_tokens)
	DPRINT("query_tokens: {}".format(query_tokens))	
	DPRINT("subsearches: {}".format(subsearches))	
		
	def filter_material_list_with_search_query(pmt_engine, materials_list, query_tokens):
		path_sep = get_path_sep(pmt_engine)
		
		#'name:str' matches if 'str' is in the name of the material, the name is the text at the right of the rightmost path_separator
		def filter_by_name(path_sep, materials_list, name_query):
			results = set()
			for material_path in materials_list:
				last_sep = material_path.rfind(path_sep)
				folder, sep, material_name = material_path.rpartition(path_sep)
				if name_query in material_name:
					results.add(material_path)
			return results
		#'path:str' matches if 'str' is in the path of the material
		def filter_by_path(path_sep, materials_list, path_query):
			results = set()
			for material_path in materials_list:
				if path_query in material_path:
					DPRINT("filter_by_path: {} {}".format(path_query, material_path))
					results.add(material_path)
			return results
		#'color:r,g,b,match' matches if the average color of the material is within 'match'
		#all values are floats in [0.0, 1.0]
		def filter_by_color(pmt_engine, materials_list, color_query):
			tokens = color_query.split(",")
			assert len(tokens) == 4, "filter_by_color(): color_query should be of the form 'color:r,g,b,match', where all values are floats [0.0, 1.0]"
			r = float(tokens[0])
			g = float(tokens[1])
			b = float(tokens[2])
			match = float(tokens[3])
			DPRINT("filter_by_color r,g,b,match: {}, {}, {}, {}".format(r, g, b, match))
			
			results = set()
			for material_path in materials_list:
				analyze = get_material_analyze_dict(pmt_engine, material_path)
				if analyze == None:
					continue
					
				mean = analyze["color_mean"]
				#dot = math.sqrt(r * mean[0] + g * mean[1] + b * mean[2]) #todo: magnitude is not 1.0
				#if dot > match:
				if abs(mean[0] - r) <= match and abs(mean[1] - g) <= match and abs(mean[2] - b) <= match:
					DPRINT("color_match: {} (avg {},{},{},{})".format(material_path, *mean))
					results.add(material_path)
			return results
			
		results = set(materials_list)
		tags = list()
		for t in query_tokens:
			if ":" in t:
				filtertype, sep, filterstr = t.partition(":")
				if filtertype == "name":
					results = filter_by_name(path_sep, results, filterstr)
				elif filtertype == "path":
					results = filter_by_path(path_sep, results, filterstr)
				elif filtertype == "color":
					results = filter_by_color(pmt_engine, results, filterstr)
			else:
				tags.append(t)
				
		return results, tags
	search_results, tags_list = filter_material_list_with_search_query(pmt_engine, materials_list, query_tokens)
	
	def filter_search_results_with_tags(search_results, tags_list):
		if len(tags_list) > 0:	
			def material_has_tag(pmt_engine, material_path, tag):
				material_tags = get_material_tags_dict(pmt_engine, material_path)
				if material_tags == None or "tags" not in material_tags:
					return False
				return tag in material_tags["tags"]
			results_with_tags = list()
			for material_path in search_results:
				for tag in tags_list:
					if material_has_tag(pmt_engine, material_path, tag):
						results_with_tags.append(material_path)
			search_results = set(results_with_tags)
		return search_results
	search_results = filter_search_results_with_tags(search_results, tags_list)
	
	def perform_variant_subsearch(pmt_engine, found_material_paths, subsearch_tokens):
		#For each found material, perform a subsearch which adds similar materials to the results.
		#A subsearch is in the format {similar0?0.5 t t t ... t},
		#where t is a token that is either a tag or search token in the format searchtype:str
		DPRINT("found_material_paths: {}".format(found_material_paths))
		subsearch_tokens = subsearch_tokens[1:-1] #remove '{' '}' brackets
		similar_type, sep, similar_fraction = subsearch_tokens[0].partition("?")
		similar_fraction = float(similar_fraction)
		assert similar_type in ["similar0", "similar5", "similar15"]
		
		DPRINT("similar_type,frac: {}, {}".format(similar_type, similar_fraction))
		path_sep = get_path_sep(pmt_engine)
		
		similar_diffuse = set()
		for material_path in found_material_paths:
			analyze = get_material_analyze_dict(pmt_engine, material_path)
			if analyze == None:
				continue
				
			#similar dict only inclues diffuse in same folder, 
			#so the path of similar diffuse can be determined by decomposing
			#the filesystem path of the current diffuse
			diffuse_path = get_diffuse_fs(pmt_engine, material_path)
			diffuse_folder, sep, diffuse_name = diffuse_path.rpartition("/")
			
			names_key = similar_type + "_names"
			fracs_key = similar_type + "_fracs"
			if names_key in analyze and fracs_key in analyze:
				diffuse_names = analyze[names_key]
				diffuse_fracs = analyze[fracs_key]
				num_similar = len(diffuse_names)
				assert(num_similar == len(diffuse_fracs))
				
				for i in range(num_similar):
					if diffuse_fracs[i] >= similar_fraction:
						similar_diffuse.add(diffuse_folder + sep + diffuse_names[i])
		DPRINT("similar_diffuse: {}".format(similar_diffuse))
		
		subsearch_results = set()
		for diffuse_fs_path in similar_diffuse:
			#multiple materials can use the same diffuse texture, just use the first match to convert diffuse to material
			materials = get_materials_using_diffuse_fs(pmt_engine, diffuse_fs_path)
			if len(materials) > 0:
				subsearch_results.add(materials[0])
		DPRINT("subsearch_results: {}".format(subsearch_results))
			
		subsearch_tokens = subsearch_tokens[1:] #remove 1st token 'similar#?1.f' 
		if len(subsearch_tokens) > 0:	
			subsearch_results, subsearch_tags = filter_material_list_with_search_query(pmt_engine, subsearch_results, subsearch_tokens)
			subsearch_results = filter_search_results_with_tags(subsearch_results, subsearch_tags)
		return subsearch_results	
		
	for subsearch_tokens in subsearches:
		search_results |= perform_variant_subsearch(pmt_engine, search_results, subsearch_tokens)
		
	report_string = "Last query: '{}' ({} results)".format(query, len(search_results))
	return list(search_results), report_string