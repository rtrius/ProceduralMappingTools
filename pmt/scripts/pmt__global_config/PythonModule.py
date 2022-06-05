#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	script_section_name: 	PythonModule
#
#The main Python module for pmt::pmt__global_config
#load other modules from this module

### Load modules
import toolutils
pmt__global_config = toolutils.createModuleFromSection("pmt__global_config", kwargs["type"], "pmt__global_config.py")
#shared modules pmt_common
pmt_common = toolutils.createModuleFromSection("pmt_common", kwargs["type"], "pmt_common.py")
pmt_common_texture = toolutils.createModuleFromSection("pmt_common_texture", kwargs["type"], "pmt_common_texture.py")
pmt_common_json = toolutils.createModuleFromSection("pmt_common_json", kwargs["type"], "pmt_common_json.py")
#non-shared modules; these modules should not access each other
pmt_parse_source1_fgd = toolutils.createModuleFromSection("pmt_parse_source1_fgd", kwargs["type"], "pmt_parse_source1_fgd.py")
pmt_parse_unreal1_uc = toolutils.createModuleFromSection("pmt_parse_unreal1_uc", kwargs["type"], "pmt_parse_unreal1_uc.py")
pmt_parse_idtech4_def = toolutils.createModuleFromSection("pmt_parse_idtech4_def", kwargs["type"], "pmt_parse_idtech4_def.py")
pmt_materialdb_source1_vmt = toolutils.createModuleFromSection("pmt_materialdb_source1_vmt", kwargs["type"], "pmt_materialdb_source1_vmt.py")
pmt_materialdb_unreal1 = toolutils.createModuleFromSection("pmt_materialdb_unreal1", kwargs["type"], "pmt_materialdb_unreal1.py")
pmt_materialdb_idtech4_mtr = toolutils.createModuleFromSection("pmt_materialdb_idtech4_mtr", kwargs["type"], "pmt_materialdb_idtech4_mtr.py")
pmt_sounddb_source1 = toolutils.createModuleFromSection("pmt_sounddb_source1", kwargs["type"], "pmt_sounddb_source1.py")
pmt_sounddb_unreal1 = toolutils.createModuleFromSection("pmt_sounddb_unreal1", kwargs["type"], "pmt_sounddb_unreal1.py")
pmt_sounddb_idtech4_sndshd = toolutils.createModuleFromSection("pmt_sounddb_idtech4_sndshd", kwargs["type"], "pmt_sounddb_idtech4_sndshd.py")
pmt_meshdb_unreal1 = toolutils.createModuleFromSection("pmt_meshdb_unreal1", kwargs["type"], "pmt_meshdb_unreal1.py")
#higher-level modules
pmt_material_select = toolutils.createModuleFromSection("pmt_material_select", kwargs["type"], "pmt_material_select.py")
pmt_material_search = toolutils.createModuleFromSection("pmt_material_search", kwargs["type"], "pmt_material_search.py")
pmt_qt_entity_kv_editor = toolutils.createModuleFromSection("pmt_qt_entity_kv_editor", kwargs["type"], "pmt_qt_entity_kv_editor.py")
pmt_qt_material_selector = toolutils.createModuleFromSection("pmt_qt_material_selector", kwargs["type"], "pmt_qt_material_selector.py")
pmt_qt_materialsets_editor = toolutils.createModuleFromSection("pmt_qt_materialsets_editor", kwargs["type"], "pmt_qt_materialsets_editor.py")

#To access the modules from other modules in this node:
#kwargs["type"].hdaModule().pmt__global_config
#To access the modules from other nodes:
#hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule().pmt__global_config

###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules from a module inside pmt__global_config.
import sys
IN_HOUDINI = 'hou' in sys.modules
if IN_HOUDINI:
	import hou
	PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	pmt_common = PMT__G_CFG.pmt_common
	pmt_common_texture = PMT__G_CFG.pmt_common_texture
	pmt_common_json = PMT__G_CFG.pmt_common_json
###__pmt::pmt__globalconfig__COMMON_SECTION_INTERNAL__

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
	PMT_REFLEVEL = 0
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


if True:
	g_cfg = pmt__global_config.PmtGlobalConfig()
	
def copy_configs_from_node(pmt_global_config, node):
	SECTIONS = ["vmf", "t3d", "map"]
	for section in SECTIONS:
		for parm in node.parms():
			config = parm.name()
			if pmt_global_config.config_exists(section, config):
				value = parm.evalAsString()
				pmt_global_config.set_config(section, config, value)
def button_save(node):
	copy_configs_from_node(g_cfg, node)

	S = pmt__global_config.PmtGlobalConfigSerializer()
	S.save_ini(g_cfg)

def copy_configs_to_node(pmt_global_config, node):
	parm_dict = dict()
	
	for section in pmt_global_config.section_dict:
		for config in pmt_global_config.section_dict[section]:
			value = pmt_global_config.section_dict[section][config]
			parm_dict[config] = value
	
	node.setParms(parm_dict)
def button_load(node):
	g_cfg.set_defaults()
	
	S = pmt__global_config.PmtGlobalConfigSerializer()
	S.load_ini(g_cfg)

	copy_configs_to_node(g_cfg, node)
	
def button_default(node):
	g_cfg.set_defaults()
	copy_configs_to_node(g_cfg, node)
	

vmf_all_entity_menu = list()
vmf_placeable_entity_menu = list()
vmf_placeable_point_entity_menu = list()
vmf_placeable_npc_entity_menu = list()
vmf_placeable_model_entity_menu = list()
vmf_placeable_brush_entity_menu = list()
vmf_placeable_nonbrush_entity_menu = list()
vmf_entity_dict = None
def vmf_load_entity_dict():
	vmf_all_entity_menu.clear()
	vmf_placeable_entity_menu.clear()
	vmf_placeable_point_entity_menu.clear()
	vmf_placeable_npc_entity_menu.clear()
	vmf_placeable_model_entity_menu.clear()
	vmf_placeable_brush_entity_menu.clear()
	vmf_placeable_nonbrush_entity_menu.clear()
	global vmf_entity_dict
	vmf_entity_dict = None

	vmf_fgd_search_path = g_cfg.get_config("vmf", "vmf_fgd_search_path")
	vmf_entity_dict = pmt_parse_source1_fgd.parse_fgds_in_path(vmf_fgd_search_path)
	for name in vmf_entity_dict:
		entity_def = vmf_entity_dict[name]
		
		#Houdini parameter menu is a flat list of paired strings in the format
		#[value_0, label_0, value_1, label_1, ..., value_n, label_n]
		#so we add each entry twice
		vmf_all_entity_menu.append(entity_def.classname)
		vmf_all_entity_menu.append(entity_def.classname)
		
		if entity_def.is_placeable():
			vmf_placeable_entity_menu.append(entity_def.classname)
			vmf_placeable_entity_menu.append(entity_def.classname)
			type = entity_def.classtype.lower()
			if type == "@pointclass":
				vmf_placeable_point_entity_menu.append(entity_def.classname)
				vmf_placeable_point_entity_menu.append(entity_def.classname)
			if type == "@npcclass":
				vmf_placeable_npc_entity_menu.append(entity_def.classname)
				vmf_placeable_npc_entity_menu.append(entity_def.classname)
			if entity_def.has_model():
				vmf_placeable_model_entity_menu.append(entity_def.classname)
				vmf_placeable_model_entity_menu.append(entity_def.classname)
				
			if type == "@solidclass":
				vmf_placeable_brush_entity_menu.append(entity_def.classname)
				vmf_placeable_brush_entity_menu.append(entity_def.classname)
			else:
				vmf_placeable_nonbrush_entity_menu.append(entity_def.classname)
				vmf_placeable_nonbrush_entity_menu.append(entity_def.classname)
		#print("vmf: {}".format(entity_def.classname))
	vmf_all_entity_menu.sort()
	vmf_placeable_entity_menu.sort()
	vmf_placeable_point_entity_menu.sort()
	vmf_placeable_npc_entity_menu.sort()
	vmf_placeable_model_entity_menu.sort()
	vmf_placeable_brush_entity_menu.sort()
	vmf_placeable_nonbrush_entity_menu.sort()
	print("vmf: loaded {} entity classes.".format(len(vmf_entity_dict)))

t3d_placeable_pawns_menu = list()
t3d_placeable_actor_menu = list()
t3d_placeable_nonbrush_menu = list()
t3d_placeable_brush_menu = list()
t3d_unrealscript_defs = None
def t3d_load_class_dict():
	t3d_placeable_pawns_menu.clear()
	t3d_placeable_actor_menu.clear()
	t3d_placeable_nonbrush_menu.clear()
	t3d_placeable_brush_menu.clear()
	global t3d_unrealscript_defs
	t3d_unrealscript_defs = None
	
	t3d_uc_search_path = g_cfg.get_config("t3d", "t3d_uc_search_path")
	t3d_unrealscript_defs = pmt_parse_unreal1_uc.parse_uc_in_path(t3d_uc_search_path)
	for classname in t3d_unrealscript_defs.class_dict:
		if t3d_unrealscript_defs.class_dict[classname].is_a("pawn"):
			t3d_placeable_pawns_menu.append(classname)
			t3d_placeable_pawns_menu.append(classname)
		if t3d_unrealscript_defs.class_dict[classname].is_a("actor"):
			t3d_placeable_actor_menu.append(classname)
			t3d_placeable_actor_menu.append(classname)
			if not t3d_unrealscript_defs.class_dict[classname].is_a("brush"):
				t3d_placeable_nonbrush_menu.append(classname)
				t3d_placeable_nonbrush_menu.append(classname)
		if t3d_unrealscript_defs.class_dict[classname].is_a("brush"):
			t3d_placeable_brush_menu.append(classname)
			t3d_placeable_brush_menu.append(classname)
	
	t3d_placeable_pawns_menu.sort()
	t3d_placeable_actor_menu.sort()
	t3d_placeable_nonbrush_menu.sort()
	t3d_placeable_brush_menu.sort()
	#print("t3d: loaded {} classes ({} pawns).".format(len(t3d_unrealscript_defs.class_dict), len(t3d_placeable_pawns_menu) // 2))		
	print("t3d: loaded {} classes ({} actors).".format(len(t3d_unrealscript_defs.class_dict), len(t3d_placeable_actor_menu) // 2))		

map_placeable_entity_menu = list()
#map_placeable_point_entity_menu = list()
map_placeable_npc_entity_menu = list()
map_placeable_model_entity_menu = list()
map_entity_dict = None
def map_load_entity_dict():
	map_placeable_entity_menu.clear()
	#map_placeable_point_entity_menu.clear()
	map_placeable_npc_entity_menu.clear()
	map_placeable_model_entity_menu.clear()
	global map_entity_dict
	map_entity_dict = None

	map_def_search_path = g_cfg.get_config("map", "map_def_search_path")
	map_entity_dict = pmt_parse_idtech4_def.parse_def_in_path(map_def_search_path)
	for name in map_entity_dict:
		entity_def = map_entity_dict[name]
		
		#Houdini parameter menu is a flat list of paired strings in the format
		#[value_0, label_0, value_1, label_1, ..., value_n, label_n]
		#so we add each entry twice
		map_placeable_entity_menu.append(name)
		map_placeable_entity_menu.append(name)
		
		if "atdm:ai_base" in entity_def.inheritance_chain:
			map_placeable_npc_entity_menu.append(name)
			map_placeable_npc_entity_menu.append(name)
		if "model" in entity_def.all_property_dict:
			modelprop = entity_def.all_property_dict["model"]
			if modelprop.value != None:
				if modelprop.value.endswith(".ase") or modelprop.value.endswith(".lwo"):
					map_placeable_model_entity_menu.append(name)
					map_placeable_model_entity_menu.append(name)
	map_placeable_entity_menu.sort()
	#map_placeable_point_entity_menu.sort()
	map_placeable_npc_entity_menu.sort()
	map_placeable_model_entity_menu.sort()
	print("map: loaded {} entity classes({} atdm:ai_base).".format(len(map_entity_dict), len(map_placeable_npc_entity_menu)))
		


vmf_materialdb = None
def vmf_load_materials():
	vmf_materials_path = g_cfg.get_config("vmf", "vmf_materials_path")
	vmf_textures_path = g_cfg.get_config("vmf", "vmf_textures_path")
	#print("vmf_materials_path: {}".format(vmf_materials_path))
	#print("vmf_textures_path: {}".format(vmf_textures_path))
	global vmf_materialdb
	vmf_materialdb = pmt_materialdb_source1_vmt.parse_vmt_files(vmf_materials_path, vmf_textures_path)
	print("vmf: loaded {} .vmt materials ({} diffuse) ({} diffuse fs).".format(len(vmf_materialdb.material_to_diffuse_dict), len(vmf_materialdb.diffuse_to_materials_dict), len(vmf_materialdb.fs_diffuse_to_dimensions)))

t3d_materialdb = None
def t3d_load_materials():
	t3d_textures_path = g_cfg.get_config("t3d", "t3d_textures_path")
	global t3d_materialdb
	t3d_materialdb = pmt_materialdb_unreal1.generate_unreal_paths_from_bmp(t3d_textures_path)
	print("t3d: loaded {} diffuse textures.".format(len(t3d_materialdb.unreal_path_to_filesystem_path)))
	
map_materialdb = None
def map_load_materials():
	map_materials_path = g_cfg.get_config("map", "map_materials_path")
	map_textures_path = g_cfg.get_config("map", "map_textures_path")
	global map_materialdb
	map_materialdb = pmt_materialdb_idtech4_mtr.parse_mtr_files(map_materials_path, map_textures_path)
	print("map: loaded {} .mtr materials ({} diffuse) ({} diffuse fs).".format(len(map_materialdb.material_to_diffuse_dict), len(map_materialdb.diffuse_to_materials_dict), len(map_materialdb.fs_diffuse_to_dimensions)))

vmf_materialsets = None
def vmf_load_materialsets():
	vmf_materialsets_path = g_cfg.get_config("vmf", "vmf_materialsets_path")
	global vmf_materialsets
	vmf_materialsets = pmt_material_select.MaterialSets()
	vmf_materialsets.load_styles(vmf_materialsets_path, "vmf")
	print("vmf: loaded {} materialset styles".format(len(vmf_materialsets.styles_dict)))
	return vmf_materialsets
	
t3d_materialsets = None
def t3d_load_materialsets():
	t3d_materialsets_path = g_cfg.get_config("t3d", "t3d_materialsets_path")
	global t3d_materialsets
	t3d_materialsets = pmt_material_select.MaterialSets()
	t3d_materialsets.load_styles(t3d_materialsets_path, "t3d")
	print("t3d: loaded {} materialset styles".format(len(t3d_materialsets.styles_dict)))
	return t3d_materialsets
	
map_materialsets = None
def map_load_materialsets():
	map_materialsets_path = g_cfg.get_config("map", "map_materialsets_path")
	global map_materialsets
	map_materialsets = pmt_material_select.MaterialSets()
	map_materialsets.load_styles(map_materialsets_path, "map")
	print("map: loaded {} materialset styles".format(len(map_materialsets.styles_dict)))
	return map_materialsets

vmf_sounddb = None
def vmf_load_sounds():
	vmf_sounds_path = g_cfg.get_config("vmf", "vmf_sounds_path")
	global vmf_sounddb
	vmf_sounddb = pmt_sounddb_source1.parse_vmf_sounds(vmf_sounds_path)
	num_soundscripts = len(vmf_sounddb.all_soundscripts)
	num_soundscapes = len(vmf_sounddb.all_soundscapes)
	num_fs_sounds = len(vmf_sounddb.fs_sounds_list)
	print("vmf: loaded {} soundscripts and {} soundscapes ({} fs .wav)".format(num_soundscripts, num_soundscapes, num_fs_sounds))
	
t3d_sounddb = None
def t3d_load_sounds():
	t3d_sounds_path = g_cfg.get_config("t3d", "t3d_sounds_path")
	global t3d_sounddb
	t3d_sounddb = pmt_sounddb_unreal1.generate_unreal_paths_from_wav(t3d_sounds_path)
	print("t3d: loaded {} .wav sounds".format(len(t3d_sounddb.unreal_path_to_filesystem_path)))
	
map_sounddb = None
def map_load_sounds():
	map_sounds_path = g_cfg.get_config("map", "map_sounds_path")
	global map_sounddb
	map_sounddb = pmt_sounddb_idtech4_sndshd.parse_sndshd_files(map_sounds_path)
	
	num_soundshaders = len(map_sounddb.sndshd_to_sounds)
	num_sounds = len(map_sounddb.sound_to_sndshds)
	num_fs_sounds = len(map_sounddb.fs_sounds_list)
	print("map: loaded {} soundshaders ({} .wav/.ogg sounds)({} fs .wav/.ogg)".format(num_soundshaders, num_sounds, num_fs_sounds))

t3d_meshdb = None
def t3d_load_meshes():
	t3d_models_path = g_cfg.get_config("t3d", "t3d_models_path")
	global t3d_meshdb
	t3d_meshdb = pmt_meshdb_unreal1.generate_unreal_paths_from_obj(t3d_models_path)
	print("t3d: loaded {} ._d.3d.obj meshes".format(len(t3d_meshdb.unreal_path_to_filesystem_path)))
	
def find_or_create_globalattrib(geo, attrib_name, default):
	dict_attrib = geo.findGlobalAttrib(attrib_name)
	if dict_attrib != None:
		return dict_attrib
	return geo.addAttrib(hou.attribType.Global, attrib_name, default)
def find_or_create_globaldict(geo, attrib_name):
	dict_attrib = geo.findGlobalAttrib(attrib_name)
	if dict_attrib != None:
		return dict_attrib
	return geo.addAttrib(hou.attribType.Global, attrib_name, dict())
	
#Adds an int attrib, value 1, to indicate that a serialize_*() function was run on the node.
#This is an optimization to avoid copying from Python -> VEX multiple times.
def mark_serialized_attrib(geo, attrib_name):
	find_or_create_globalattrib(geo, attrib_name, 0)
	geo.setGlobalAttribValue(attrib_name, 1)
	
#transfers pmt__global_config configs to a detail attrib on node.geometry(), for access from VEX	
def VEX_TRANSFER_global_configs(node):
	geo = node.geometry()
	
	mark_serialized_attrib(geo, "VEX_TRANSFER_global_configs")
	
	configs_dict = g_cfg.get_all_configs()
	find_or_create_globaldict(geo, "pmt__global_config");
	geo.setGlobalAttribValue("pmt__global_config", configs_dict);
	

#transfers material db to a detail attrib on node.geometry(), for access from VEX	
def VEX_TRANSFER_material_dbs(node):
	geo = node.geometry()
	
	mark_serialized_attrib(geo, "VEX_TRANSFER_material_dbs")
	
	if vmf_materialdb != None:
		find_or_create_globaldict(geo, "vmf_materialdb_mat_to_surfaceprop")
		geo.setGlobalAttribValue("vmf_materialdb_mat_to_surfaceprop", vmf_materialdb.material_to_surfaceprop_dict)
		find_or_create_globaldict(geo, "vmf_materialdb_mat_to_diff")
		geo.setGlobalAttribValue("vmf_materialdb_mat_to_diff", vmf_materialdb.material_to_diffuse_dict)
		find_or_create_globaldict(geo, "vmf_materialdb_diff_to_mat")
		geo.setGlobalAttribValue("vmf_materialdb_diff_to_mat", vmf_materialdb.diffuse_to_materials_dict)
		find_or_create_globaldict(geo, "vmf_materialdb_diff_to_size")
		geo.setGlobalAttribValue("vmf_materialdb_diff_to_size", vmf_materialdb.fs_diffuse_to_dimensions)
		find_or_create_globaldict(geo, "vmf_materialdb_diff_to_analyze")
		geo.setGlobalAttribValue("vmf_materialdb_diff_to_analyze", vmf_materialdb.fs_diffuse_to_analyze)
		find_or_create_globaldict(geo, "vmf_materialdb_diff_to_tags")
		geo.setGlobalAttribValue("vmf_materialdb_diff_to_tags", vmf_materialdb.fs_diffuse_to_tags)
	if t3d_materialdb != None:
		find_or_create_globaldict(geo, "t3d_materialdb_unreal_to_fs")
		geo.setGlobalAttribValue("t3d_materialdb_unreal_to_fs", t3d_materialdb.unreal_path_to_filesystem_path)
		find_or_create_globaldict(geo, "t3d_materialdb_fs_to_unreal")
		geo.setGlobalAttribValue("t3d_materialdb_fs_to_unreal", t3d_materialdb.filesystem_path_to_unreal_path)
		find_or_create_globaldict(geo, "t3d_materialdb_fs_to_size")
		geo.setGlobalAttribValue("t3d_materialdb_fs_to_size", t3d_materialdb.filesystem_path_to_dimensions)
		find_or_create_globaldict(geo, "t3d_materialdb_fs_to_analyze")
		geo.setGlobalAttribValue("t3d_materialdb_fs_to_analyze", t3d_materialdb.filesystem_path_to_analyze)
		find_or_create_globaldict(geo, "t3d_materialdb_fs_to_tags")
		geo.setGlobalAttribValue("t3d_materialdb_fs_to_tags", t3d_materialdb.filesystem_path_to_tags)
	if map_materialdb != None:
		find_or_create_globaldict(geo, "map_materialdb_mat_to_diff")
		geo.setGlobalAttribValue("map_materialdb_mat_to_diff", map_materialdb.material_to_diffuse_dict)
		find_or_create_globaldict(geo, "map_materialdb_diff_to_mat")
		geo.setGlobalAttribValue("map_materialdb_diff_to_mat", map_materialdb.diffuse_to_materials_dict)
		find_or_create_globaldict(geo, "map_materialdb_diff_to_size")
		geo.setGlobalAttribValue("map_materialdb_diff_to_size", map_materialdb.fs_diffuse_to_dimensions)
		find_or_create_globaldict(geo, "map_materialdb_diff_to_analyze")
		geo.setGlobalAttribValue("map_materialdb_diff_to_analyze", map_materialdb.fs_diffuse_to_analyze)
		find_or_create_globaldict(geo, "map_materialdb_diff_to_tags")
		geo.setGlobalAttribValue("map_materialdb_diff_to_tags", map_materialdb.fs_diffuse_to_tags)
		
#transfers materialsets db to a detail attrib on node.geometry(), for access from VEX	
def VEX_TRANSFER_materialsets(node):
	geo = node.geometry()
	
	mark_serialized_attrib(geo, "VEX_TRANSFER_materialsets")
	
	if vmf_materialsets != None:
		find_or_create_globaldict(geo, "vmf_materialsets_styles_dict")
		geo.setGlobalAttribValue("vmf_materialsets_styles_dict", vmf_materialsets.styles_dict)
	if t3d_materialsets != None:
		find_or_create_globaldict(geo, "t3d_materialsets_styles_dict")
		geo.setGlobalAttribValue("t3d_materialsets_styles_dict", t3d_materialsets.styles_dict)
	if map_materialsets != None:
		find_or_create_globaldict(geo, "map_materialsets_styles_dict")
		geo.setGlobalAttribValue("map_materialsets_styles_dict", map_materialsets.styles_dict)

def button_vmf_load_entity_dict():
	vmf_load_entity_dict()			
def button_t3d_load_class_dict():
	t3d_load_class_dict()
def button_map_load_entity_dict():
	map_load_entity_dict()	
	
def button_vmf_load_materials():
	vmf_load_materials()	
def button_t3d_load_materials():
	t3d_load_materials()		
def button_map_load_materials():
	map_load_materials()
	
def button_vmf_load_materialsets():
	vmf_load_materialsets()	
def button_t3d_load_materialsets():
	t3d_load_materialsets()		
def button_map_load_materialsets():
	map_load_materialsets()	

#hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule().vmf_start_materialsets_editor()
def vmf_start_materialsets_editor():
	pass
	#pmt_qw_materialsets_editor.MaterialSetsEditorWindow("vmf")
def t3d_start_materialsets_editor():
	pass
	#pmt_qw_materialsets_editor.MaterialSetsEditorWindow("t3d")
def map_start_materialsets_editor():
	pass
	#pmt_qw_materialsets_editor.MaterialSetsEditorWindow("map")

#OnInstall seems to run twice on load, so manually check whether assets are loaded
assets_loaded = False
def load_assets():
	global assets_loaded
	if assets_loaded: 
		print("pmt::pmt__globalconfig load_assets() already loaded.")
		return
	
	print("pmt::pmt__globalconfig load_assets()")
	assets_loaded = True
	
	vmf_load_entity_dict()
	t3d_load_class_dict()
	map_load_entity_dict()

	vmf_load_materials()
	t3d_load_materials()
	map_load_materials()
	
	vmf_load_materialsets()
	t3d_load_materialsets()
	map_load_materialsets()
	
	vmf_load_sounds()
	t3d_load_sounds()
	map_load_sounds()
	
	t3d_load_meshes()
	
#menu script to get choices - run this in the parameter's menu script
# def menu_script():
	# node = kwargs["node"]
	# parm = kwargs["parm"]
	# parm_number_string = parm.name().replace("choices_", "")
	# choices_parm_name = "key_" + parm_number_string
	# choices_name = node.parm(choices_parm_name).evalAsString()

	# entity = node.parm("entity").evalAsString()

	# type = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config")
	# return type.hdaModule().get_choices_list(entity, choices_name)
def get_choices_list(entity_class, prop_name):
	if vmf_entity_dict == None:
		print("PMT:error: get_choices_list() vmf_entity_dict is None")
		return []
	
	if entity_class not in vmf_entity_dict:
		return []
	
	prop_dict = vmf_entity_dict[entity_class].all_property_dict
	if prop_name not in prop_dict:
		return []
	
	prop = prop_dict[prop_name]
	if prop.type != "choices":
		return []
	
	menu = list()
	for choice in prop.choices_list:
		menu.append("{}".format(choice.value))
		menu.append("{}".format(choice.description))
	return menu
	
#to access menu see
#'parameter menu scripts' in 'python script locations'
#in Houdini help
###example to access the menu from another node
###type = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config")
###return type.hdaModule().testmenu
#testmenu = ["a", "b", "d","q", "1", "s"]
testmenu = vmf_placeable_npc_entity_menu