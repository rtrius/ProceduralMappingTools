#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt__global_config
#	script_section_name: 	PythonModule_pmt__global_config
import os
import configparser

import hou

class PmtGlobalConfig:
	def __init__(self):
		self.section_dict = dict()
		self.section_dict["vmf"] = dict()
		self.section_dict["t3d"] = dict()
		self.section_dict["map"] = dict()

		self.set_defaults()
	
	def config_exists(self, section, config_name):
		return section in self.section_dict and config_name in self.section_dict[section]
	
	def get_config(self, section, config_name):
		return self.section_dict[section][config_name]
		
	def get_all_configs(self):
		configs = dict()
		for section in self.section_dict:
			for config_name in self.section_dict[section]:
				config_value = self.section_dict[section][config_name]
				configs[config_name] = config_value
		return configs
		
	def set_config(self, section, config_name, value):
		self.section_dict[section][config_name] = value
		
	def set_defaults(self):
		#Each default config name should have a corresponding parameter in pmt::pmt__global_config
		DEFAULT_VMF_FGD_SEARCH_PATH = "c:/pmt/classdefs/vmf/"
		DEFAULT_T3D_UC_SEARCH_PATH = "c:/pmt/classdefs/t3d/"
		DEFAULT_MAP_DEF_SEARCH_PATH = "c:/pmt/classdefs/map/"
		self.set_config("vmf", "vmf_fgd_search_path", DEFAULT_VMF_FGD_SEARCH_PATH)
		self.set_config("t3d", "t3d_uc_search_path", DEFAULT_T3D_UC_SEARCH_PATH)
		self.set_config("map", "map_def_search_path", DEFAULT_MAP_DEF_SEARCH_PATH)
		
		DEFAULT_VMF_MODELS_PATH = "c:/pmt/models/vmf/"
		DEFAULT_T3D_MODELS_PATH = "c:/pmt/models/t3d/"
		DEFAULT_MAP_MODELS_PATH = "c:/pmt/models/map/"
		self.set_config("vmf", "vmf_models_path", DEFAULT_VMF_MODELS_PATH)
		self.set_config("t3d", "t3d_models_path", DEFAULT_T3D_MODELS_PATH)
		self.set_config("map", "map_models_path", DEFAULT_MAP_MODELS_PATH)
		
		DEFAULT_VMF_MATERIALS_PATH = "c:/pmt/materials/vmf/materials"
		DEFAULT_T3D_MATERIALS_PATH = "none" #UnrealEngine1 does not use materials
		DEFAULT_MAP_MATERIALS_PATH = "c:/pmt/materials/map/"
		self.set_config("vmf", "vmf_materials_path", DEFAULT_VMF_MATERIALS_PATH)
		self.set_config("t3d", "t3d_materials_path", DEFAULT_T3D_MATERIALS_PATH)
		self.set_config("map", "map_materials_path", DEFAULT_MAP_MATERIALS_PATH)
		
		DEFAULT_VMF_TEXTURES_PATH = "c:/pmt/textures/vmf/materials"
		DEFAULT_T3D_TEXTURES_PATH = "c:/pmt/textures/t3d/"
		DEFAULT_MAP_TEXTURES_PATH = "c:/pmt/textures/map/"
		self.set_config("vmf", "vmf_textures_path", DEFAULT_VMF_TEXTURES_PATH)
		self.set_config("t3d", "t3d_textures_path", DEFAULT_T3D_TEXTURES_PATH)
		self.set_config("map", "map_textures_path", DEFAULT_MAP_TEXTURES_PATH)
		
		DEFAULT_VMF_MATERIALSETS_PATH = "c:/pmt/materialsets/vmf/"
		DEFAULT_T3D_MATERIALSETS_PATH = "c:/pmt/materialsets/t3d/"
		DEFAULT_MAP_MATERIALSETS_PATH = "c:/pmt/materialsets/map/"
		self.set_config("vmf", "vmf_materialsets_path", DEFAULT_VMF_MATERIALSETS_PATH)
		self.set_config("t3d", "t3d_materialsets_path", DEFAULT_T3D_MATERIALSETS_PATH)
		self.set_config("map", "map_materialsets_path", DEFAULT_MAP_MATERIALSETS_PATH)
		
		DEFAULT_VMF_SOUNDS_PATH = "c:/pmt/sounds/vmf/"
		DEFAULT_T3D_SOUNDS_PATH = "c:/pmt/sounds/t3d/"
		DEFAULT_MAP_SOUNDS_PATH = "c:/pmt/sounds/map/"
		self.set_config("vmf", "vmf_sounds_path", DEFAULT_VMF_SOUNDS_PATH)
		self.set_config("t3d", "t3d_sounds_path", DEFAULT_T3D_SOUNDS_PATH)
		self.set_config("map", "map_sounds_path", DEFAULT_MAP_SOUNDS_PATH)
		
class PmtGlobalConfigSerializer:
	def __init__(self):
		self.ini_path = None
		
		self.initialize()
		
	def has_ini_path(self):
		return self.ini_path != None
		
	def initialize(self):
		this_node_type = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config")
		multiple_globalcfg = len(this_node_type.allInstalledDefinitions()) > 1
		if multiple_globalcfg:
			print("PmtGlobalConfigSerializer:warning: multiple defs for pmt::pmt__global_config")
			print("cannot determine path for ProceduralMappingTools.ini")
			return
			
		this_def = this_node_type.definition()
		hda_path = this_def.libraryFilePath()
		#print("PMT hda_path: {}".format(hda_path))
		#hip_path = hou.hipFile.path()
		#print("PMT hip_path: {}".format(hip_path))
		
		self.ini_path = hda_path[:hda_path.rfind(".")] + ".ini"
		
	def save_ini(self, pmt_global_config):   
		if not self.has_ini_path():
			print("PmtGlobalConfigSerializer::save_ini(): no .ini path found.")
			return
			
		cfg = configparser.RawConfigParser()
		
		for section in pmt_global_config.section_dict:
			cfg.add_section(section)
			for config in pmt_global_config.section_dict[section]:
				cfg.set(section, config, pmt_global_config.section_dict[section][config])
		
		with open(self.ini_path, 'w') as file:
			cfg.write(file)
	
	def load_ini(self, pmt_global_config):
		if not self.has_ini_path():
			print("PmtGlobalConfigSerializer::load_ini(): no .ini path found.")
			return
	 
		if not os.path.exists(self.ini_path):
			print("PmtGlobalConfigSerializer::load_ini(): no .ini found (ini_path={}).".format(self.ini_path))
			return
	
		print("ProceduralMappingTools ini_path={}.".format(self.ini_path))
	 
		cfg = configparser.RawConfigParser()
		cfg.read(self.ini_path)
		
		#print("self.ini_path: {}".format(self.ini_path))
		#print("items: {}".format(cfg.items()))
		#for (section_name, section_proxy) in cfg.items():
		#	print("items[{}]: {}".format(section_name, cfg.items(section_name)))
		
		for section in pmt_global_config.section_dict:
			for config in pmt_global_config.section_dict[section]:
				value_as_string = cfg.get(section, config).lower() #all paths should be lowercase
				pmt_global_config.set_config(section, config, value_as_string)
		
		return pmt_global_config
