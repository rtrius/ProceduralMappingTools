#!/usr/bin/env python3
#	node               : 	pmt::pme_vmf_model
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

import os

#hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pme_vmf_model").hdaModule().OnVmfEntityChanged(hou.pwd())
def OnVmfEntityChanged(node):
	override_model = node.parm("override_model").evalAsInt()
	override_model_path = node.parm("override_model_path").evalAsString()
	#vmf_keyvalues = node.parm("vmf_keyvalues").evalAsJSONMap()
	vmf_models_path = PMT__G_CFG.g_cfg.get_config("vmf", "vmf_models_path")
	
	new_vmf_class = node.parm("set_class_to").evalAsString()
	if new_vmf_class in PMT__G_CFG.vmf_entity_dict:
		node.parm("pmt_vmf_entity_class").set(new_vmf_class)
		entity = PMT__G_CFG.vmf_entity_dict[new_vmf_class]
		
		vmf_keyvalues = dict()
		for prop_name in entity.all_property_dict:
			prop = entity.all_property_dict[prop_name]
			vmf_keyvalues[prop_name] = prop.get_default_value_str()
		node.parm("vmf_keyvalues").set(vmf_keyvalues)
		
		if not override_model:
			modelpath = entity.get_default_model()
			
			fs_obj_path_ref = vmf_models_path + modelpath + ".ref.smd.obj"
			fs_obj_path_phy = vmf_models_path + modelpath + ".phy.smd.obj"
			fs_obj_path = fs_obj_path_ref if os.path.exists(fs_obj_path_ref) else fs_obj_path_phy
			
			node.parm("mesh").set(fs_obj_path)
			node.parm("override_model_path").set(fs_obj_path)
		else:
			fs_obj_path = override_model_path
			node.parm("mesh").set(fs_obj_path)