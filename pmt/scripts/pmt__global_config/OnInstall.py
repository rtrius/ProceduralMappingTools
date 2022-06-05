#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	script_section_name: 	OnInstall

### pmt::pmt__globalconfig common section
if True:
	PMT__G_CFG = kwargs["type"].hdaModule()
	pmt__global_config = PMT__G_CFG.pmt__global_config
### pmt::pmt__globalconfig common section

if True:
	print("")
	print("pmt::pmt__globalconfig OnInstall()")

#Load config ProceduralMappingTools_globals.ini
if True:
	S = pmt__global_config.PmtGlobalConfigSerializer()
	S.load_ini(PMT__G_CFG.g_cfg)
	
#Load assets, including class definitions, textures, materials, sound files, etc.
if True:
	PMT__G_CFG.load_assets()
	
#Load python panels
if True:
	this_node_type = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config")
	multiple_globalcfg = len(this_node_type.allInstalledDefinitions()) > 1
	if multiple_globalcfg:
		print("pmt::pmt__global_config.OnInstall():error: multiple defs for pmt::pmt__global_config")
		print("cannot determine path for ProceduralMappingTools/python_panels")
	else:
		this_def = this_node_type.definition()
		hda_path = this_def.libraryFilePath()
		hda_path.replace("\\", "/")
		python_panels_path = hda_path[:hda_path.rfind(".")] + "/python_panels/"
		
		pypanel_paths = list()
		pypanel_paths.append(python_panels_path + "pmt_qt_entity_kv_editor.pypanel")
		pypanel_paths.append(python_panels_path + "pmt_qt_material_selector.pypanel")
		pypanel_paths.append(python_panels_path + "pmt_qt_materialsets_editor.pypanel")
		for path in pypanel_paths:
			hou.pypanel.installFile(path)