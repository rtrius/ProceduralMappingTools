#!/usr/bin/env python3
#	node               : 	pmt::pme_t3d_model
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


#hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pme_t3d_model").hdaModule().OnClassChanged(hou.pwd())
def OnClassChanged(node):
	t3d_models_path = PMT__G_CFG.g_cfg.get_config("t3d", "t3d_models_path")
	
	new_uclass = node.parm("set_uclass_to").evalAsString()
	if new_uclass in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
		node.parm("pmt_t3d_entity_class").set(new_uclass)
		
		unrealclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[new_uclass]
		if unrealclass.mesh3d != None:
			mesh = unrealclass.mesh3d
			origin = mesh.origin
			rotation = mesh.rotation_degrees
			scale = mesh.scale
			
			#mesh.filepath does not correspond to the mesh name exported from UnrealEd
			#fs_path = t3d_models_path + unrealclass.package + "/" + mesh.filepath
			#use the unreal path name mesh.name instead
			fs_path = t3d_models_path + unrealclass.package + "/models/" + mesh.name + "_d.3d"
			
			fs_obj_path = fs_path + ".obj"
			node.parm("mesh").set(fs_obj_path)

			#set the mesh parameters as specified by the '#exec' preprocessor in the .uc file
			node.parm("tx").set(-origin[0])		#note inversion of x-axis
			node.parm("ty").set(-origin[1]) 	#note inversion of y-axis
			node.parm("tz").set(origin[2])
			node.parm("rx").set(rotation[0])
			node.parm("ry").set(rotation[1])
			node.parm("rz").set(rotation[2])
			node.parm("sx").set(scale[0])
			node.parm("sy").set(scale[1])
			node.parm("sz").set(scale[2])
		
		