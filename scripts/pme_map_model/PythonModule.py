#!/usr/bin/env python3
#	node               : 	pmt::pme_map_model
#	script_section_name: 	PythonModule
#import toolutils

###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules from external nodes.
if True:
		import hou
		PMT__G_CFG = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
		pmt__global_config = PMT__G_CFG.pmt__global_config
		
		pmt_common = PMT__G_CFG.pmt_common
		pmt_common_texture = PMT__G_CFG.pmt_common_texture
		
		pmt_material_select = PMT__G_CFG.pmt_material_select
		pmt_parse_source1_fgd = PMT__G_CFG.pmt_parse_source1_fgd
		pmt_parse_unreal1_uc = PMT__G_CFG.pmt_parse_unreal1_uc
		pmt_parse_idtech4_def = PMT__G_CFG.pmt_parse_idtech4_def
		pmt_materialdb_source1_vmt = PMT__G_CFG.pmt_materialdb_source1_vmt
		pmt_materialdb_unreal1 = PMT__G_CFG.pmt_materialdb_unreal1
		pmt_materialdb_idtech4_mtr = PMT__G_CFG.pmt_materialdb_idtech4_mtr
###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__

#hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pme_map_model").hdaModule().OnMapEntityChanged(hou.pwd())
def OnMapEntityChanged(node):
	override_mesh = node.parm("override_mesh").evalAsInt()
	override_mesh_path = node.parm("override_mesh_path").evalAsString()
	new_map_entity = node.parm("set_entity_to").evalAsString()

	map_models_path = PMT__G_CFG.g_cfg.get_config("map", "map_models_path")
	if new_map_entity in PMT__G_CFG.map_entity_dict:
		node.parm("pmt_map_entity_class").set(new_map_entity)
		entdef = PMT__G_CFG.map_entity_dict[new_map_entity]
		if "model" in entdef.all_property_dict:
			if not override_mesh:
				modelpath = entdef.all_property_dict["model"].value
				
				fs_obj_path = map_models_path + modelpath + ".obj"
				node.parm("mesh").set(fs_obj_path)
				node.parm("override_mesh_path").set(fs_obj_path)
			else:
				fs_obj_path = override_mesh_path
				node.parm("mesh").set(fs_obj_path)