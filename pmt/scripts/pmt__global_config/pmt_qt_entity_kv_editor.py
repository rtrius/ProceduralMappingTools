#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_qt_entity_kv_editor
#	script_section_name: 	pmt_qt_entity_kv_editor.py
#
#	Entity key-value dictionary editor.
#
#	The kv-editor has 3 parts:
#		1) KVTABLE - the main key-value table used to select which property to edit.
#		2) PROPBAR - a widget in the KVTABLE window used to edit the selected property.
#		3) NODE - the node to save and load kv-table values from.
#	Each part has slightly different ways of representing the data, so
#	it is necessary to perform conversions when moving values from one part to another.
import sys
import os
import random
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2 import QtMultimedia, QtMultimediaWidgets 

###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__
###\scripts\pmt__global_config\pmt__global_config.py
###Copy-paste this section to reference pmt__global_config modules from external nodes.
import hou
if hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config") != None:
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
	pmt_sounddb_source1 = PMT__G_CFG.pmt_sounddb_source1
	pmt_sounddb_unreal1 = PMT__G_CFG.pmt_sounddb_unreal1
	pmt_sounddb_idtech4_sndshd = PMT__G_CFG.pmt_sounddb_idtech4_sndshd
	pmt_meshdb_unreal1 = PMT__G_CFG.pmt_meshdb_unreal1
###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__

IN_HOUDINI = 'hou' in sys.modules
def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
import inspect
CF = inspect.currentframe
def CURFUNC(inspect_currentframe): #return the name of the 'current function':  CURFUNC(CF())
	return inspect_currentframe.f_code.co_name
def CCF(self, inspect_currentframe, sep = "::", suffix = "()"): #return the name the the 'current class function': CCF(self, CF())
	return type(self).__qualname__ + sep + inspect_currentframe.f_code.co_name +  suffix

LARGE_SPACING = 4096 #Spacing to compact items in a QHBoxLayout

COLUMN_KVTREE_KEY = 0
COLUMN_KVTREE_VALUE = 1
COLUMN_KVTREE_PROP_TYPE = 2
COLUMN_KVTREE_PROPBAR_TYPE = 3

PROP_TYPE_UNSUPPORTED = "unsupported"
PROP_TYPE_ROOTNODE = "root_node"
PROP_TYPE_INTERNALNODE = "internal_node"
PROP_TYPE_BOOL = "bool"
PROP_TYPE_INT = "int"
PROP_TYPE_FLOAT = "float"
PROP_TYPE_VECTOR2 = "vector2"
PROP_TYPE_VECTOR3 = "vector3"
PROP_TYPE_STRING = "string"
PROP_TYPE_COLOR = "color"
PROP_TYPE_ENUM = "enum"
PROP_TYPE_FLAGS = "flags"
PROP_TYPE_ASSET = "asset"
PROP_TYPE_ASSET_CLASS = "asset_class"
PROP_TYPE_ASSET_SOUND = "asset_sound"
PROP_TYPE_ASSET_MATERIAL = "asset_material"
PROP_TYPE_ASSET_MESH = "asset_mesh"

PROPBAR_TYPES = []
PROPBAR_TYPES += [PROP_TYPE_UNSUPPORTED]
PROPBAR_TYPES += [PROP_TYPE_ROOTNODE]
PROPBAR_TYPES += [PROP_TYPE_INTERNALNODE]
PROPBAR_TYPES += [PROP_TYPE_BOOL]
PROPBAR_TYPES += [PROP_TYPE_INT]
PROPBAR_TYPES += [PROP_TYPE_FLOAT]
PROPBAR_TYPES += [PROP_TYPE_VECTOR2]
PROPBAR_TYPES += [PROP_TYPE_VECTOR3]
PROPBAR_TYPES += [PROP_TYPE_STRING]
PROPBAR_TYPES += [PROP_TYPE_COLOR]
PROPBAR_TYPES += [PROP_TYPE_ENUM]
PROPBAR_TYPES += [PROP_TYPE_FLAGS]
PROPBAR_TYPES += [PROP_TYPE_ASSET]
PROPBAR_TYPES += [PROP_TYPE_ASSET_CLASS]
PROPBAR_TYPES += [PROP_TYPE_ASSET_SOUND]
PROPBAR_TYPES += [PROP_TYPE_ASSET_MATERIAL]
PROPBAR_TYPES += [PROP_TYPE_ASSET_MESH]


PROPBAR_TYPES_SET = frozenset(PROPBAR_TYPES)
assert len(PROPBAR_TYPES) == len(PROPBAR_TYPES_SET), "len(PROPBAR_TYPES) != len(PROPBAR_TYPES_SET)"

COLUMN_PROPERTY_KEY = 0
COLUMN_PROPERTY_VALUE = 1
	
def get_node_parameters(node, pmt_engine):
	if pmt_engine == "vmf":
		classname = node.parm("pmt_vmf_entity_class").evalAsString()
		keyvalue_dict = node.parm("vmf_keyvalues").evalAsJSONMap()
	elif pmt_engine == "t3d":
		classname = node.parm("pmt_t3d_entity_class").evalAsString()
		keyvalue_dict = node.parm("t3d_keyvalues").evalAsJSONMap()
	elif pmt_engine == "map":
		classname = node.parm("pmt_map_entity_class").evalAsString()
		keyvalue_dict = node.parm("map_keyvalues").evalAsJSONMap()
	
	return (classname, keyvalue_dict)

def set_node_parameters(node, pmt_engine, keyvalue_dict):
	if pmt_engine in ["vmf", "t3d", "map"]:
		node.parm("{}_keyvalues".format(pmt_engine)).set(keyvalue_dict)

#converts the property type used by the kv-table and node to one used by the propbar
def prop_type_to_propbar_type(prop_type, pmt_engine):
	if pmt_engine == "vmf":
		if prop_type == "void": return PROP_TYPE_UNSUPPORTED
		if prop_type == "string": return PROP_TYPE_STRING
		if prop_type == "integer": return PROP_TYPE_INT
		if prop_type == "float": return PROP_TYPE_FLOAT
		if prop_type == "choices": return PROP_TYPE_ENUM
		if prop_type == "flags": return PROP_TYPE_FLAGS
		#entity properties ui
		#if prop_type == "axis": return PROP_TYPE_
		if prop_type == "angle": return PROP_TYPE_VECTOR3
		if prop_type == "color255": return PROP_TYPE_COLOR	#RGB byte [0, 255]
		if prop_type == "color1": return PROP_TYPE_COLOR	#RGB float [0, 1]
		#if prop_type == "filterclass": return PROP_TYPE_
		if prop_type == "material": return PROP_TYPE_ASSET_MATERIAL
		if prop_type == "decal": return PROP_TYPE_ASSET_MATERIAL
		#if prop_type == "node_dest": return PROP_TYPE_
		if prop_type == "npcclass": return PROP_TYPE_ASSET_CLASS			#string; name of a @NPCClass entity
		if prop_type == "origin": return PROP_TYPE_VECTOR3
		if prop_type == "pointentityclass": return PROP_TYPE_ASSET_CLASS	#string; name of a @PointClass entity
		#if prop_type == "scene": return PROP_TYPE_
		#if prop_type == "sidelist": return PROP_TYPE_
		if prop_type == "sound": return PROP_TYPE_ASSET_SOUND
		if prop_type == "sprite": return PROP_TYPE_ASSET_MATERIAL
		if prop_type == "studio": return PROP_TYPE_STRING
		if prop_type == "target_destination": return PROP_TYPE_STRING			#string; name of a entity
		if prop_type == "target_name_or_class": return PROP_TYPE_ASSET_CLASS	#string; name of a entity or class; checking the .fgd files, generally refers to a @NPCClass when a class
		if prop_type == "target_source": return PROP_TYPE_STRING				#string; name of a entity
		#if prop_type == "vecline": return PROP_TYPE_
		if prop_type == "vector": return PROP_TYPE_VECTOR3
	elif pmt_engine == "t3d":
		if prop_type == "bool": return PROP_TYPE_BOOL
		if prop_type == "byte": return PROP_TYPE_INT
		if prop_type == "int": return PROP_TYPE_INT
		if prop_type == "float": return PROP_TYPE_FLOAT
		if prop_type == "string": return PROP_TYPE_STRING
		if prop_type == "name": return PROP_TYPE_STRING
		
		if prop_type == "object": return PROP_TYPE_STRING
		if prop_type == "model": return PROP_TYPE_STRING
		if prop_type == "music": return PROP_TYPE_STRING
		if prop_type == "class": return PROP_TYPE_ASSET_CLASS
		if prop_type == "sound": return PROP_TYPE_ASSET_SOUND
		if prop_type == "texture": return PROP_TYPE_ASSET_MATERIAL
		if prop_type == "mesh": return PROP_TYPE_ASSET_MESH
		if prop_type == "lodmesh": return PROP_TYPE_ASSET_MESH
		
		#type 'class<actor>' restricts class type to actor and child classes of actor
		if prop_type.startswith("class") and "<" in prop_type and ">" in prop_type: return PROP_TYPE_ASSET_CLASS
		#base_class = prop_type[prop_type.find("<")+1:prop_type.find(">")]
		#if prop_type == "vector": return PROP_TYPE_VECTOR3
		#if prop_type == "rotator": return PROP_TYPE_VECTOR3
		#if prop_type == "color": return PROP_TYPE_COLOR	#RGBA byte [0, 255]
		if prop_type in PMT__G_CFG.t3d_unrealscript_defs.all_enum_dict: return PROP_TYPE_ENUM
		
	elif pmt_engine == "map":
		if prop_type == "editor_bool": return PROP_TYPE_BOOL
		if prop_type == "editor_int": return PROP_TYPE_INT
		if prop_type == "editor_float": return PROP_TYPE_FLOAT
		if prop_type == "editor_string": return PROP_TYPE_STRING
		if prop_type == "editor_color": return PROP_TYPE_COLOR		#RGB float [0, 1]
		if prop_type == "editor_vector": return PROP_TYPE_VECTOR3
		if prop_type == "editor_angle": return PROP_TYPE_VECTOR3	#(Y, Z, X) euler rotation in degrees
		
		if prop_type == "editor_setkeyvalue": return PROP_TYPE_STRING	#
		if prop_type == "editor_var": return PROP_TYPE_STRING			#used for bool, int, float, string, possibly others
		
		if prop_type == "editor_model": return PROP_TYPE_ASSET_MESH
		if prop_type == "editor_snd": return PROP_TYPE_ASSET_SOUND			#soundshader reference
		if prop_type == "editor_material": return PROP_TYPE_ASSET_MATERIAL 	#path to a material

	return PROP_TYPE_UNSUPPORTED

#returns the property type used by the kv-table and node
def get_prop_type(classname, prop_name, pmt_engine):
	type = None

	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			vmf_prop = vmf_entity.all_property_dict[prop_name]
			type = vmf_prop.type
	elif pmt_engine == "t3d" and classname in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
		uclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[classname]
		if prop_name in uclass.all_editor_vars_dict:
			t3d_var = uclass.all_editor_vars_dict[prop_name]
			type = t3d_var.type
	elif pmt_engine == "map" and classname in PMT__G_CFG.map_entity_dict:
		map_entity = PMT__G_CFG.map_entity_dict[classname]
		if prop_name in map_entity.all_property_dict_editor:
			map_prop = map_entity.all_property_dict_editor[prop_name]
			type = map_prop.editor_tag
			
	return type

def KVTABLE_get_vmf_choices_value(vmf_choice):
	#vmf_choice.value is the actual text saved to .vmf files, so when saving a choice 
	#to a node, this needs to be converted into the corresponding choice
	return vmf_choice.description

#converts a NODE choice to KVTABLE
def choices_value_to_description(choice_value, classname, prop_name, pmt_engine):
	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			vmf_prop = vmf_entity.all_property_dict[prop_name]
			assert vmf_prop.type == "choices" and vmf_prop.choices_list != None, "vmf entity {} has invalid choices_list"
			for choice_index in range(len(vmf_prop.choices_list)):
				vmf_choice = vmf_prop.choices_list[choice_index]
				
				if choice_value == vmf_choice.value:
					return vmf_choice.description
	
	assert False
	return None
	
#converts a KVTABLE choice to NODE
def choices_description_to_value(choice_description, classname, prop_name, pmt_engine):
	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			vmf_prop = vmf_entity.all_property_dict[prop_name]
			assert vmf_prop.type == "choices" and vmf_prop.choices_list != None, "vmf entity {} has invalid choices_list"
			for choice_index in range(len(vmf_prop.choices_list)):
				vmf_choice = vmf_prop.choices_list[choice_index]
				
				if choice_description == vmf_choice.description:
					return vmf_choice.value
	
	assert False
	return None
	
	
def KVTABLE_get_prop_options_enum(classname, prop_name, pmt_engine):
	enum_list = list()
	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			vmf_prop = vmf_entity.all_property_dict[prop_name]
			assert vmf_prop.type == "choices" and vmf_prop.choices_list != None, "vmf entity {} has invalid choices_list"
			for choice_index in range(len(vmf_prop.choices_list)):
				choice = vmf_prop.choices_list[choice_index]
				
				enum_list.append( KVTABLE_get_vmf_choices_value(choice) )
	elif pmt_engine == "t3d" and classname in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
		uclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[classname]
		if prop_name in uclass.all_editor_vars_dict:
			t3d_var = uclass.all_editor_vars_dict[prop_name]
			unreal_enum = PMT__G_CFG.t3d_unrealscript_defs.all_enum_dict[t3d_var.type]
			for i in range(len(unreal_enum.int_to_enum)):
				enum_text = unreal_enum.int_to_enum[i]
				enum_list.append(enum_text)
	elif pmt_engine == "map" and classname in PMT__G_CFG.map_entity_dict:
		#return None #todo: check if map has enum/choices type
		pass
		#map_entity = PMT__G_CFG.map_entity_dict[classname]
		#if prop_name in map_entity.all_property_dict_editor:
		#	map_prop = map_entity.all_property_dict_editor[prop_name]
			
	return enum_list
	
def get_flags_descriptions(classname, prop_name, pmt_engine):
	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			flags_prop = vmf_entity.all_property_dict[prop_name]
			return flags_prop.get_flags_descriptions()
			
	assert False
	return None
	
def KVTABLE_get_prop_default(classname, prop_name, pmt_engine):
	default_value = None

	if pmt_engine == "vmf" and classname in PMT__G_CFG.vmf_entity_dict:
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		if prop_name in vmf_entity.all_property_dict:
			vmf_prop = vmf_entity.all_property_dict[prop_name]
			default_value = vmf_prop.default_value
			
			if vmf_prop.type == "choices":
				default_value = KVTABLE_get_vmf_choices_value(vmf_prop.choices_list[default_value])	
	elif pmt_engine == "map" and classname in PMT__G_CFG.map_entity_dict:
		map_entity = PMT__G_CFG.map_entity_dict[classname]
		if prop_name in map_entity.all_property_dict_editor:
			map_prop = map_entity.all_property_dict_editor[prop_name]
			default_value = map_prop.value
			
	return default_value

def get_list_of_class_prop_names(classname, pmt_engine):
	prop_names = list()
	if pmt_engine == "vmf":
		if classname not in PMT__G_CFG.vmf_entity_dict:
			return None
		vmf_entity = PMT__G_CFG.vmf_entity_dict[classname]
		for prop_name in vmf_entity.all_property_dict:
			prop_names.append(prop_name)
			
	elif pmt_engine == "t3d":
		if classname not in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
			return None
		uclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[classname]
		for var_name in uclass.all_editor_vars_dict:
			prop_names.append(var_name)
			
	elif pmt_engine == "map":
		if classname not in PMT__G_CFG.map_entity_dict:
			return None
		map_entity = PMT__G_CFG.map_entity_dict[classname]
		for prop_name in map_entity.all_property_dict_editor:
			prop_names.append(prop_name)
			
	return prop_names
	
#converts 1 level of a defaultproperties string to a dict
#example input: 
#	(x=XV,y=YV,z=ZV,w=(wx=W1,wy=W2,wz=W3))
#should return return the dict:
#	{'x':'XV', 'y':'YV', 'z':'ZV', w:'(wx=W1,wy=W2,wz=W3)'}
#
#todo: current approach does not support arrays such as:
#	'x(0)=VALUE'
#	'x(1)=VALUE'
#	...
#	'x(N)=VALUE'
def t3d_value_str_to_dict(value_str):
	#remove first and last parenthesis
	if value_str.startswith("(") and value_str.endswith(")"):
		value_str = value_str[1:-1]

	defaults_dict = dict()
	value_str += "," #use "," to mark the end
	
	COLLECT_VAR_NAME = 0
	COLLECT_VAR_VALUE = 1
	COLLECT_QUOTE = 2
	COLLECT_PARENTHESIS = 3
	
	state = COLLECT_VAR_NAME
	prev_state = None
	
	quote_char = None
	var_name = ""
	var_value = ""
	quote_or_parenthesis_buffer = ""
	parenthesis_level = 0
	for char in value_str:
		if char == "(": parenthesis_level += 1
		if char == ")": parenthesis_level -= 1
	
		if state == COLLECT_VAR_NAME:
			if char != "=":
				var_name += char
			else:
				prev_state = None
				state = COLLECT_VAR_VALUE
		elif state == COLLECT_VAR_VALUE:
			if char == ",":
				defaults_dict[var_name] = var_value
				var_name = ""
				var_value = ""
				prev_state = None
				state = COLLECT_VAR_NAME
			elif char == "\"":
				quote_char = char
				prev_state = COLLECT_VAR_VALUE
				state = COLLECT_QUOTE
			elif char == "\'":
				quote_char = char
				prev_state = COLLECT_VAR_VALUE
				state = COLLECT_QUOTE
			elif char == "(":
				prev_state = COLLECT_VAR_VALUE
				state = COLLECT_PARENTHESIS
			else:
				var_value += char
		elif state == COLLECT_QUOTE:
			if char != quote_char:
				var_value += char
			else:
				state = prev_state
		elif state == COLLECT_PARENTHESIS:
			if char != ")" or parenthesis_level != 0:
				var_value += char
			else:
				state = prev_state
				
	#print("{} -> {}".format(value_str, defaults_dict))
	return defaults_dict
	
#inverse of default_value_str_to_dict()
def dict_to_t3d_value_str(t3d_value_dict):
	val_str = "("
	for var_name in t3d_value_dict:
		val_str += "{}={},".format(var_name, t3d_value_dict[var_name])
	if val_str.endswith(","): val_str = val_str[:-1]
	val_str += ")"
	return val_str
	
def vmf_pointclasses_to_treeitems():
	paths_list = list()
	for classname in PMT__G_CFG.vmf_entity_dict:
		entity_def = PMT__G_CFG.vmf_entity_dict[classname]
		type = entity_def.classtype.lower()
		if type == "@pointclass":
			paths_list.append("/{}".format(classname))
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def vmf_npcclasses_to_treeitems():
	paths_list = list()
	for classname in PMT__G_CFG.vmf_entity_dict:
		entity_def = PMT__G_CFG.vmf_entity_dict[classname]
		type = entity_def.classtype.lower()
		if type == "@npcclass":
			paths_list.append("/{}".format(classname))
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def vmf_sounds_to_treeitems():
	#We want to use the same tree to access 'raw' sound files and soundscripts.
	#In order to do this there are some discrepancies that need to be resolved.
	#
	#A 'raw' sound path is in the format:
	#	sound/FOLDER/a.wav
	#while soundscript names have the format:
	#	category.name
	#so we replace "." with "/" and add ":soundscripts/" at the start of the path
	#to indicate that it is from a script.
	#
	#Additionally, it is worth noting that a 'raw' path has to be handled in multiple ways.
	#The actual filesystem path (used for sound preview):
	#	C:/pmt_resources/sounds/vmf/sound/FOLDER/a.wav
	#relative path to vmf_sounds_path (used by the tree, to select which sound to use): 
	#	sound/FOLDER/a.wav
	#relative to sound/ (the path that is stored in the .vmf file and in vmf_keyvalues): 
	#	FOLDER/a.wav

	paths_list = list()
	for sound_path in PMT__G_CFG.vmf_sounddb.fs_sounds_list:
		paths_list.append(sound_path)
	for sound_path in PMT__G_CFG.vmf_sounddb.all_soundscripts:
		paths_list.append(":soundscripts/" + sound_path.replace(".", "/"))
	#for sound_path in PMT__G_CFG.vmf_sounddb.all_soundscapes:
	#	paths_list.append(":soundscapes/" + sound_path.replace(".", "/"))
	paths_list.sort()
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def vmf_materials_to_treeitems():
	paths_list = list()
	for material_path in PMT__G_CFG.vmf_materialdb.material_to_diffuse_dict:
		paths_list.append(material_path)
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
	
def uclass_to_treeitems(classname):
	if classname not in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
		return None
		
	uclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[classname]
	
	treeroot = QtWidgets.QTreeWidgetItem(1)
	treeroot.setText(COLUMN_KVTREE_PROPBAR_TYPE, "class: {}".format(classname))
	treeroot.setText(COLUMN_KVTREE_PROPBAR_TYPE, PROP_TYPE_ROOTNODE)
	
	def expand_var(uclass, unreal_var, parent_qtreeitem, default_value_from_struct = None):
		treeitem = QtWidgets.QTreeWidgetItem(parent_qtreeitem, 1)
		treeitem.setText(COLUMN_KVTREE_KEY, unreal_var.name)
		
		parser_type = PMT__G_CFG.t3d_unrealscript_defs.get_parser_type(unreal_var.type)
		if parser_type != pmt_parse_unreal1_uc.PARSER_VARTYPE_STRUCT:
        
			if default_value_from_struct != None:
				treeitem.setText(COLUMN_KVTREE_VALUE, default_value_from_struct)
			else:
				if unreal_var.name in uclass.defaultproperties_dict:
					default_value = uclass.defaultproperties_dict[unreal_var.name]
				else:
					default_value = PMT__G_CFG.t3d_unrealscript_defs.get_empty_default(unreal_var.type)
				treeitem.setText(COLUMN_KVTREE_VALUE, default_value)
			treeitem.setText(COLUMN_KVTREE_PROP_TYPE, unreal_var.type)
			treeitem.setText(COLUMN_KVTREE_PROPBAR_TYPE, prop_type_to_propbar_type(unreal_var.type, "t3d"))
		else:
			ustruct = PMT__G_CFG.t3d_unrealscript_defs.all_struct_dict[unreal_var.type]
			
			if unreal_var.name in uclass.defaultproperties_dict:
				default_value = uclass.defaultproperties_dict[unreal_var.name]
			else:
				default_value = ""
				
			empty_default = PMT__G_CFG.t3d_unrealscript_defs.get_empty_default(unreal_var.type)
			
			#print("structdef: {} -> {}".format(unreal_var.name, empty_default))
			
				
			defaults_dict = t3d_value_str_to_dict(default_value)
			empty_defaults_dict = t3d_value_str_to_dict(empty_default)
			
			merged_defaults_dict = empty_defaults_dict
			for var_name in merged_defaults_dict:
				if var_name in defaults_dict:
					merged_defaults_dict[var_name] = defaults_dict[var_name]
			
			default_str = dict_to_t3d_value_str(merged_defaults_dict)
			treeitem.setText(COLUMN_KVTREE_VALUE, default_str)
			treeitem.setText(COLUMN_KVTREE_PROP_TYPE, unreal_var.type)
			treeitem.setText(COLUMN_KVTREE_PROPBAR_TYPE, PROP_TYPE_INTERNALNODE)
			
			for var_name in ustruct.variables:
				default_from_struct = merged_defaults_dict[var_name]
				
				struct_var = ustruct.variables[var_name]
				expand_var(uclass, struct_var, treeitem, default_from_struct)
		return treeitem
		
	category_treeitems = dict()
	for var_name in uclass.all_editor_vars_dict:
		uvar = uclass.all_editor_vars_dict[var_name]
		category = uvar.editor_category if uvar.editor_category != None else "_no_category"
		if category not in category_treeitems:
			treeitem = QtWidgets.QTreeWidgetItem(treeroot, 1)
			treeitem.setText(COLUMN_KVTREE_KEY, category)
			#treeitem.setText(COLUMN_KVTREE_VALUE, "")
			#treeitem.setText(COLUMN_KVTREE_PROP_TYPE, "")
			treeitem.setText(COLUMN_KVTREE_PROPBAR_TYPE, PROP_TYPE_INTERNALNODE)
			category_treeitems[category] = treeitem
		expand_var(uclass, uvar, category_treeitems[category])
	
	return treeroot
	
def paths_to_qtreewidgetitems(paths, path_sep = '/'):
	qtreeitem_dict = dict()
	top_level_paths_set = set()
	#top_level_items_set = set()
	leaf_node_items = list()
	
	COLUMN_MATERIAL_NAME = 0
	COLUMN_MATERIAL_PATH_HIDDEN = 1
	FONT_BOLD_ITALIC = QtGui.QFont()
	FONT_BOLD_ITALIC.setBold(True)
	FONT_BOLD_ITALIC.setItalic(True)
	
	for material_path in paths:
	
		path_parts = material_path.split(path_sep, maxsplit = -1)
		DPRINT("material_path: {}".format(material_path))
		DPRINT("path_parts start: {}".format(path_parts))
		while "" in path_parts:
			path_parts.remove("")
		DPRINT("path_parts filter: {}".format(path_parts))
		if len(path_parts) > 0:
			dirs = path_parts[:-1]
			material = path_parts[-1]
			
		path = ""
		num_path_parts = len(path_parts)
		for depth in range(num_path_parts):
			#all paths are materials, so the highest depth means that this item is a material/leaf
			is_leaf = (depth == num_path_parts - 1)
			
			if depth > 0:
				parentpath = path
				parentitem = qtreeitem_dict[parentpath]
			else:
				parentpath = None
				parentitem = None
		
			material_or_directory = path_parts[depth]
			if depth != 0:
				path += path_sep
			path += material_or_directory
			DPRINT("path: {} (material_or_directory {}) (parent {})".format(path, material_or_directory, parentpath))
			if path not in qtreeitem_dict:
				item = QtWidgets.QTreeWidgetItem(parentitem, 1)
				item.setText(COLUMN_MATERIAL_NAME, material_or_directory) 
				item.setText(COLUMN_MATERIAL_PATH_HIDDEN, path)	 #store the complete material_path in column 1(not visible)
				if not is_leaf:
					item.setFont(COLUMN_MATERIAL_NAME, FONT_BOLD_ITALIC) #distinguish between materials and folders in the tree
					
				qtreeitem_dict[path] = item
				if depth == 0:
					top_level_paths_set.add(path)
					#top_level_items_set.add(item)
				elif is_leaf: 
					leaf_node_items.append(item)
	
	SORT_SECOND_LEVEL_TREEITEMS = True
	if SORT_SECOND_LEVEL_TREEITEMS:
		#sort treeitems at depth >= 1 (not direct child of root): a first, z last
		def sort_qtreeitem_children(column, qtreewidgetitem):
			qtreewidgetitem.sortChildren(column, QtCore.Qt.AscendingOrder)
			for child_index in range(qtreewidgetitem.childCount()):
				child_item = qtreewidgetitem.child(child_index)
				sort_qtreeitem_children(column, child_item)
			
		for path in qtreeitem_dict:
			qtreeitem = qtreeitem_dict[path]
			sort_qtreeitem_children(COLUMN_MATERIAL_PATH_HIDDEN, qtreeitem)
	
	#output top level treeitems in sorted order
	top_level_paths = list()
	for path in top_level_paths_set:
		top_level_paths.append(path)
	top_level_paths.sort()
	
	top_level_items = list()
	for i in range(len(top_level_paths)):
		path = top_level_paths[i]
		top_level_items.append(qtreeitem_dict[path])
	
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
	
def t3d_classes_to_treeitems():
	paths_list = list()
	for classname in PMT__G_CFG.t3d_unrealscript_defs.class_dict:
		uclass = PMT__G_CFG.t3d_unrealscript_defs.class_dict[classname]
		path = ""
		
	 #inheritance_chain starts with 'deepest' class and ends with root class('actor'), reverse() to start with root
		for parent in reversed(uclass.inheritance_chain):
			path += "{}.".format(parent)
		path += classname
		
		paths_list.append(path)
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, ".")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
	
	
def t3d_materials_to_treeitems():
	paths_list = list()
	for unreal_path in PMT__G_CFG.t3d_materialdb.unreal_path_to_filesystem_path:
		paths_list.append(unreal_path)
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, ".")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def t3d_meshes_to_treeitems():
	paths_list = list()
	for unreal_path in PMT__G_CFG.t3d_meshdb.unreal_path_to_filesystem_path:
		paths_list.append(unreal_path)
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, ".")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def t3d_sounds_to_treeitems():
	paths_list = list()
	for unreal_path in PMT__G_CFG.t3d_sounddb.unreal_path_to_filesystem_path:
		paths_list.append(unreal_path)
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, ".")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)


def map_materials_to_treeitems():
	paths_list = list()
	for material_path in PMT__G_CFG.map_materialdb.material_to_diffuse_dict:
		paths_list.append(material_path)
	paths_list.sort()
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def map_meshes_to_treeitems():
	paths_list = list()
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)
def map_sounds_to_treeitems():
	paths_list = list()
	for name in PMT__G_CFG.map_sounddb.sndshd_dict:
		soundshader = PMT__G_CFG.map_sounddb.sndshd_dict[name]
		if soundshader.path != None:
			paths_list.append(soundshader.path)
		else:
			paths_list.append("_nofolder/" + name)
	paths_list.sort()
	(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(paths_list, "/")
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)


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
	
#FlagsCheckboxesWidget is used to edit the vmf 'flags' type
class FlagsCheckboxesWidget(QtWidgets.QWidget):
	anyCheckboxChanged = QtCore.Signal()
	NUM_CHECKBOX = 32
		
	def __init__(self):
		super().__init__()

		self.p_flags_list = list()
		for i in range(self.NUM_CHECKBOX):
			checkbox = QtWidgets.QCheckBox("checkbox #{}".format(i))
			checkbox.setToolTipDuration(0)
			checkbox.stateChanged.connect(self.OnStateChanged)
			self.p_flags_list.append(checkbox)
			
		self.layout = QtWidgets.QVBoxLayout()
		
		NUM_CHECKBOX_ROWS = 8
		NUM_CHECKBOX_COLUMNS = 4
		assert NUM_CHECKBOX_ROWS * NUM_CHECKBOX_COLUMNS == self.NUM_CHECKBOX
		grid_layout = QtWidgets.QGridLayout()
		for column in range(NUM_CHECKBOX_COLUMNS):
			for row in range(NUM_CHECKBOX_ROWS):
				checkbox_index = column * NUM_CHECKBOX_ROWS + row
				grid_layout.addWidget(self.p_flags_list[checkbox_index], row, column)
		self.layout.addLayout(grid_layout)
		self.setLayout(self.layout)
		
	
	def OnStateChanged(self, state):
		self.anyCheckboxChanged.emit()
		
	def get_flags_value(self):
		int32_flags = 0
		for checkbox_index in range(self.NUM_CHECKBOX):
			if self.p_flags_list[checkbox_index].checkState() == QtCore.Qt.Checked:
				int32_flags |= (1 << checkbox_index)
		return int32_flags	
	def set_flags_value(self, int32_flags):
		for checkbox_index in range(self.NUM_CHECKBOX):
			check = QtCore.Qt.Checked if int32_flags & (1 << checkbox_index) != 0 else QtCore.Qt.Unchecked
			self.p_flags_list[checkbox_index].setCheckState(check)
	
	def set_checkbox_descriptions(self, flags_descriptions_list):
		assert len(flags_descriptions_list) == self.NUM_CHECKBOX
		for checkbox_index in range(self.NUM_CHECKBOX):
			checkbox = self.p_flags_list[checkbox_index]
			checkbox.setText(str(checkbox_index) + ": " + flags_descriptions_list[checkbox_index])
			checkbox.setToolTip(flags_descriptions_list[checkbox_index])

# AssetWidget is used to preview and set 'asset' type; it contains a tree, textbox, preview/set buttons, and a volume slider 
class AssetWidget(QtWidgets.QWidget):
	setPathButtonPressed = QtCore.Signal()

	IMAGEVIEW_SIZE = QtCore.QSize(256,256)
	
	def __init__(self, pmt_engine):
		super().__init__()
		self.layout = QtWidgets.QVBoxLayout()
		self.asset_type = None
		self.pmt_engine = pmt_engine
		
		if True:
			tree_layout = QtWidgets.QHBoxLayout()
			self.treewidget = QtWidgets.QTreeWidget()
			self.treewidget.setHeaderLabels(["node", "path"])
			self.treewidget.setColumnCount(2)
			tree_layout.addWidget(self.treewidget)
			
			if True:
				self.image_preview = QtWidgets.QLabel("[material]")
				self.image_preview.setAlignment(QtCore.Qt.AlignCenter)
				self.image_preview.setMaximumSize(AssetWidget.IMAGEVIEW_SIZE)
				self.image_preview.setMinimumSize(AssetWidget.IMAGEVIEW_SIZE)
				tree_layout.addWidget(self.image_preview)
			self.layout.addLayout(tree_layout)
				
		if True:
			path_layout = QtWidgets.QHBoxLayout()
			#self.path_editbox = hou.qt.InputField(hou.qt.InputField.StringType, 1, "string")
			self.path_editbox = QtWidgets.QLineEdit()
			self.set_path = QtWidgets.QPushButton("set")
			self.sound_preview = QtWidgets.QPushButton("preview_sound")
			self.sound_stop = QtWidgets.QPushButton("stop_sound")
			self.sound_volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
			self.sound_volume.setMinimum(0)
			self.sound_volume.setMaximum(100)
			self.sound_volume.setValue(50)
			path_layout.addWidget(self.path_editbox)
			path_layout.addWidget(self.set_path)
			path_layout.addWidget(self.sound_preview)
			path_layout.addWidget(self.sound_stop)
			path_layout.addWidget(self.sound_volume)
			self.layout.addLayout(path_layout)
			
		if True:
			mpl = QtMultimedia.QMediaPlayer()
			mpl.setVolume(50)
			
			if False:
				print("mpl.duration(): {}".format(mpl.duration()))
				print("mpl.bufferStatus(): {}".format(mpl.bufferStatus()))
				print("mpl.mediaStatus(): {}".format(mpl.mediaStatus()))
				print("mpl.state(): {}".format(mpl.state()))
				print("mpl.isAudioAvailable(): {}".format(mpl.isAudioAvailable()))
				print("mpl.media(): {}".format(mpl.media()))
				print("mpl.currentMedia(): {}".format(mpl.currentMedia()))
				print("mpl.currentMedia().canonicalUrl(): {}".format(mpl.currentMedia().canonicalUrl()))
			
			if False:
				info = QtMultimedia.QAudioDeviceInfo(QtMultimedia.QAudioDeviceInfo.defaultOutputDevice())
				name = info.deviceName()
				codecs = info.supportedCodecs()
				types = info.supportedSampleTypes()
				print("default_name: {}".format(name))
				print("default_codecs: {}".format(codecs))
				print("default_types: {}".format(types))
				
				devices = QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput)
				for d in devices:
					print("device: {}".format(d.deviceName()))
				
			self.mediaplayer = mpl

			
		self.setLayout(self.layout)
		
		if True:
			
			self.set_path.clicked.connect(self.OnSetPathButton)
			
			self.sound_preview.clicked.connect(self.OnSoundPreviewButton)
			self.sound_stop.clicked.connect(self.OnSoundStopButton)
			
			self.treewidget.itemClicked.connect(self.OnQTreeWidget_itemClicked)
		
	def OnSetPathButton(self):
		self.setPathButtonPressed.emit()
		
	def OnSoundPreviewButton(self):
		if self.asset_type != "sound":
			return
		
		sound_path = self.value()
		if True: #path_is_valid
			volume = self.sound_volume.value()
			volume = max(0, min(volume, 100))
			self.mediaplayer.setVolume(volume)
			
			qurl = None
			if self.pmt_engine == "vmf":
				#todo: handle $PLACEHOLDER in vmf sound_path
				#in vmf soundscripts, the first 2 chars of the path can contain chars in SOUND_CHARS
				#to indicate certain characteristics about the sound
				def remove_sound_chars(sound_path):
					SOUND_CHARS = "*#@><^(}$!?&~`+%"
					if len(sound_path) > 0 and sound_path[0] in SOUND_CHARS:
						sound_path = sound_path[1:]
					if len(sound_path) > 0 and sound_path[0] in SOUND_CHARS:
						sound_path = sound_path[1:]
					return sound_path
					
				#':' is used to indicate soundscript/soundscape see also vmf_sounds_to_treeitems()
				if sound_path.startswith(":soundscripts/"):
					soundscript_name = sound_path[len(":soundscripts/"):].replace("/", ".")
					script_dict = PMT__G_CFG.vmf_sounddb.all_soundscripts
					if soundscript_name in script_dict:
						if "wave" in script_dict[soundscript_name]:
							num_waves = len(script_dict[soundscript_name]["wave"])
							if num_waves > 0:
								#index might always be 0 - not sure if multiple "wave" in a soundscript is supported
								#when not using "rndwave"
								sound_index = random.randint(0, num_waves - 1)
								sound_path = script_dict[soundscript_name]["wave"][sound_index]
								sound_path = remove_sound_chars(sound_path)
								sound_path = "sound/" + sound_path
							else:
								message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "'wave' in soundscript '{}' has no sound paths".format(soundscript_name), QtWidgets.QMessageBox.Ok, self)
								message.show()
						elif "rndwave" in script_dict[soundscript_name]:
							if len(script_dict[soundscript_name]["rndwave"]) > 0:
								waves = list()
								for rndwave_dict in script_dict[soundscript_name]["rndwave"]:
									if "wave" in rndwave_dict:
										waves += rndwave_dict["wave"]
								
								num_waves = len(waves)
								if num_waves > 0:
									wave_index = random.randint(0, len(waves) - 1)
									sound_path = waves[wave_index]
									sound_path = remove_sound_chars(sound_path)
									sound_path = "sound/" + sound_path
							else:
								 num_waves = 0
								 
							if num_waves <= 0:
								message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "'rndwave' in soundscript '{}' has no sound paths".format(soundscript_name), QtWidgets.QMessageBox.Ok, self)
								message.show()
						else:
							message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "No 'wave' or 'rndwave' found for soundscript '{}'".format(soundscript_name), QtWidgets.QMessageBox.Ok, self)
							message.show()
				#elif sound_path.startswith(":soundscapes/"):
				#	soundscape_name = sound_path[len(":soundscapes/"):].replace("/", ".")
				#	scape_dict = PMT__G_CFG.vmf_sounddb.all_soundscapes
								
				vmf_sounds_path = PMT__G_CFG.g_cfg.get_config("vmf", "vmf_sounds_path")
				vmf_sound_fs_path = vmf_sounds_path + sound_path #PMT__G_CFG.vmf_sounddb
				if os.path.exists(vmf_sound_fs_path):
					qurl = QtCore.QUrl(vmf_sound_fs_path)
				else:
					message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "File not found: {}".format(vmf_sound_fs_path), QtWidgets.QMessageBox.Ok, self)
					message.show()
			elif self.pmt_engine == "t3d":
				if sound_path.startswith("sound'"):
					sound_path = sound_path[sound_path.find("'")+1:]
				if sound_path.endswith("'"):
					sound_path = sound_path[:-1]
				t3d_sound_fs_path = PMT__G_CFG.t3d_sounddb.get_filesystem_path(sound_path)
				qurl = QtCore.QUrl(t3d_sound_fs_path)
			elif self.pmt_engine == "map":
				sndshd_name = sound_path[sound_path.rfind("/")+1:]
				if sndshd_name in PMT__G_CFG.map_sounddb.sndshd_dict:
					soundshader = PMT__G_CFG.map_sounddb.sndshd_dict[sndshd_name]
					if len(soundshader.sounds) > 0:
						sound0 = soundshader.sounds[0]
						#if sound0.endswith("ogg"):
						#	message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", ".ogg preview not supported. (sndshd={}, sound0={})".format(sndshd_name, sound0), QtWidgets.QMessageBox.Ok, self)
						#	message.show()
							
						map_sounds_path = PMT__G_CFG.g_cfg.get_config("map", "map_sounds_path")
						map_fs_sound_path = map_sounds_path + sound0
				
						if os.path.exists(map_fs_sound_path):
							qurl = QtCore.QUrl(map_fs_sound_path)
						else:
							message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "File not found: {} (sndshd={})".format(map_fs_sound_path, sndshd), QtWidgets.QMessageBox.Ok, self)
							message.show()
			if qurl != None:	
				#QUrl() is in the format "C:/pmt_resources/sounds/engine/sound.wav"
				self.mediaplayer.setMedia(qurl)
				self.mediaplayer.play()
			
				#if self.mediaplayer.error() != QtMultimedia.QMediaPlayer.NoError:
				#	message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "sound_preview", "QMediaPlayer error: {}".format(self.mediaplayer.errorString()), QtWidgets.QMessageBox.Ok, self)
				#	message.show()
			
	def OnSoundStopButton(self):
		self.mediaplayer.stop()
	def OnQSlider_sliderMoved(self, value):
		volume = value
		volume = max(0, min(volume, 100))
		self.mediaplayer.setVolume(volume)
		
	def OnQTreeWidget_itemClicked(self, qtreewidgetitem, column):
		

		#todo: fix placement and name
		COLUMN_MATERIAL_PATH_HIDDEN = 1
		
		treeitem = qtreewidgetitem
		is_leaf_node = treeitem.childCount() == 0
		
		if self.asset_type != "class":
			asset_path = treeitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
		else:
			asset_path = treeitem.text(0)
		
		if self.pmt_engine == "vmf":
			if self.asset_type == "material":
				if is_leaf_node:
					diffuse_fs = get_diffuse_fs(self.pmt_engine, asset_path)
					pixmap = QtGui.QPixmap(diffuse_fs)
					pixmap = pixmap.scaled(AssetWidget.IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
					self.image_preview.setPixmap(pixmap)
				else:
					self.image_preview.setPixmap(None)
					self.image_preview.setText("[material]")
		elif self.pmt_engine == "t3d":
			if self.asset_type == "class":
				t3d_asset_type = "class"
				asset_path = PMT__G_CFG.t3d_unrealscript_defs.class_dict[asset_path].get_unreal_path()
			elif self.asset_type == "sound":
				t3d_asset_type = "sound"
			elif self.asset_type == "material":
				t3d_asset_type = "texture"
				
				if is_leaf_node:
					diffuse_fs = get_diffuse_fs(self.pmt_engine, asset_path)
					pixmap = QtGui.QPixmap(diffuse_fs)
					pixmap = pixmap.scaled(AssetWidget.IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
					self.image_preview.setPixmap(pixmap)
				else:
					self.image_preview.setPixmap(None)
					self.image_preview.setText("[material]")
				
			elif self.asset_type == "mesh":
				t3d_asset_type = "lodmesh"
		elif self.pmt_engine == "map":
			if self.asset_type == "material":
				if is_leaf_node:
					diffuse_fs = get_diffuse_fs(self.pmt_engine, asset_path)
					pixmap = QtGui.QPixmap(diffuse_fs)
					pixmap = pixmap.scaled(AssetWidget.IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
					self.image_preview.setPixmap(pixmap)
				else:
					self.image_preview.setPixmap(None)
					self.image_preview.setText("[material]")
					
		if is_leaf_node or self.asset_type == "class":
			if self.pmt_engine == "t3d":
				asset_path = "{}'{}'".format(t3d_asset_type, asset_path)
			
			self.set_value(asset_path)
		
	def set_asset_type(self, asset_type, pmt_engine_proptype):
		self.asset_type = asset_type
		self.treewidget.clear()
		
		get_treeitems_func = None
		if self.pmt_engine == "vmf":
			if self.asset_type == "class":
				#print("pmt_engine_proptype: {}".format(pmt_engine_proptype))
				if pmt_engine_proptype == "npcclass" or pmt_engine_proptype == "target_name_or_class":
					#when target_name_or_class refers to a class, it seems to refer to a @NPCClass 
					get_treeitems_func = vmf_npcclasses_to_treeitems
				if pmt_engine_proptype == "pointentityclass":
					get_treeitems_func = vmf_pointclasses_to_treeitems
			elif self.asset_type == "sound":
				get_treeitems_func = vmf_sounds_to_treeitems
			elif self.asset_type == "material":
				get_treeitems_func = vmf_materials_to_treeitems
			elif self.asset_type == "mesh":
				pass
		elif self.pmt_engine == "t3d":
			if self.asset_type == "class":
				get_treeitems_func = t3d_classes_to_treeitems
			elif self.asset_type == "sound":
				get_treeitems_func = t3d_sounds_to_treeitems
			elif self.asset_type == "material": #also includes textures and sprites
				get_treeitems_func = t3d_materials_to_treeitems
			elif self.asset_type == "mesh":
				get_treeitems_func = t3d_meshes_to_treeitems
		elif self.pmt_engine == "map":
			if self.asset_type == "class":
				pass
			elif self.asset_type == "sound":
				get_treeitems_func = map_sounds_to_treeitems
			elif self.asset_type == "material": #also includes textures and sprites
				get_treeitems_func = map_materials_to_treeitems
			elif self.asset_type == "mesh":
				get_treeitems_func = map_meshes_to_treeitems
					
		if get_treeitems_func != None:
			(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = get_treeitems_func()
			for item in top_level_items:
				self.treewidget.addTopLevelItem(item)
		
	def value(self):
		return self.path_editbox.text()
	def set_value(self, asset_path):
		self.path_editbox.setText(asset_path)
		
#EntityPropWidget is the 'propbar' used to edit the values in the key-value table		
class EntityPropWidget(QtWidgets.QWidget):
	anyPropChanged = QtCore.Signal()

	def __init__(self, pmt_engine):
		super().__init__()
		self.pmt_engine = pmt_engine
		self.pmt_engine_proptype = None
		
		
		self.layout = QtWidgets.QVBoxLayout()
		
		if True:
			proptype_layout = QtWidgets.QHBoxLayout()
			self.prop_key = QtWidgets.QLabel("Key: (Click on a row to edit.)")
			#self.prop_type_label = QtWidgets.QLabel("Prop type")
			
			self.prop_type_combobox = QtWidgets.QComboBox()
			self.prop_type_combobox.setEnabled(False)
			for typestr in PROPBAR_TYPES:
				self.prop_type_combobox.addItem(typestr)
				
			proptype_layout.addWidget(self.prop_key, stretch = 0, alignment = QtCore.Qt.AlignLeft)
			#proptype_layout.addWidget(self.prop_type_label)
			proptype_layout.addWidget(self.prop_type_combobox, stretch = 0, alignment = QtCore.Qt.AlignRight)
			#proptype_layout.addSpacing(LARGE_SPACING)
			self.layout.addLayout(proptype_layout)

		
		if True:
			self.prop_widgets = dict()
			self.prop_widgets[PROP_TYPE_UNSUPPORTED] = QtWidgets.QLabel("Select a property to edit it.")
			self.prop_widgets[PROP_TYPE_ROOTNODE] = QtWidgets.QLabel("Select a property to edit it.")
			self.prop_widgets[PROP_TYPE_INTERNALNODE] = QtWidgets.QLabel("Select a leaf node to edit the property.")
			self.prop_widgets[PROP_TYPE_BOOL] = QtWidgets.QCheckBox("bool")
			self.prop_widgets[PROP_TYPE_INT] = hou.qt.InputField(hou.qt.InputField.IntegerType, 1, "int")
			self.prop_widgets[PROP_TYPE_FLOAT] = hou.qt.InputField(hou.qt.InputField.FloatType, 1, "float")
			self.prop_widgets[PROP_TYPE_VECTOR2] = hou.qt.InputField(hou.qt.InputField.FloatType, 2, "vector2")
			self.prop_widgets[PROP_TYPE_VECTOR3] = hou.qt.InputField(hou.qt.InputField.FloatType, 3, "vector3")
			self.prop_widgets[PROP_TYPE_STRING] = hou.qt.InputField(hou.qt.InputField.StringType, 1, "string")
			
			#See also hou.qt.ColorSwatchButton.colorChanged
			#Side Effects Software\Houdini 18.5.408\houdini\python3.7libs\houpythonportion\qt\ColorField.py
			self.prop_widgets[PROP_TYPE_COLOR] = hou.qt.ColorField("color", include_alpha=True)
			
			self.prop_widgets[PROP_TYPE_ENUM] = QtWidgets.QComboBox()
			self.prop_widgets[PROP_TYPE_FLAGS] = FlagsCheckboxesWidget()
			#self.prop_widgets[PROP_TYPE_ASSET] = QtWidgets.QTreeWidget()
			self.prop_widgets[PROP_TYPE_ASSET] = AssetWidget(pmt_engine)
			self.prop_widgets[PROP_TYPE_ASSET_CLASS] = QtWidgets.QLabel("[PROP_TYPE_ASSET_CLASS]")
			self.prop_widgets[PROP_TYPE_ASSET_MATERIAL] = QtWidgets.QLabel("[PROP_TYPE_ASSET_MATERIAL]")
			self.prop_widgets[PROP_TYPE_ASSET_MESH] = QtWidgets.QLabel("[PROP_TYPE_ASSET_MESH]")
			self.prop_widgets[PROP_TYPE_ASSET_SOUND] = QtWidgets.QLabel("[PROP_TYPE_ASSET_SOUND]")
			
			for type in self.prop_widgets:
				self.prop_widgets[type].hide()
				self.layout.addWidget(self.prop_widgets[type])
			self.prop_widgets[PROP_TYPE_UNSUPPORTED].show()
			
		if True:
			#connect OnPropTypeChanged after self.prop_widgets is created
			#otherwise, OnPropTypeChanged() seems to be run immediately giving the error:
			#	AttributeError: 'EntityPropWidget' object has no attribute 'prop_widgets'
			self.prop_type_combobox.currentTextChanged.connect(self.OnPropTypeChanged)
			
			self.prop_widgets[PROP_TYPE_BOOL].stateChanged.connect(self.OnQCheckBox_stateChanged)
			self.prop_widgets[PROP_TYPE_INT].valueChanged.connect(self.OnHouQtInputField_valueChanged)
			self.prop_widgets[PROP_TYPE_FLOAT].valueChanged.connect(self.OnHouQtInputField_valueChanged)
			self.prop_widgets[PROP_TYPE_VECTOR2].valueChanged.connect(self.OnHouQtInputField_valueChanged)
			self.prop_widgets[PROP_TYPE_VECTOR3].valueChanged.connect(self.OnHouQtInputField_valueChanged)
			self.prop_widgets[PROP_TYPE_STRING].valueChanged.connect(self.OnHouQtInputField_valueChanged)
			self.prop_widgets[PROP_TYPE_COLOR].colorChanged.connect(self.OnHouQtColorSwatchButton_colorChanged) 
			self.prop_widgets[PROP_TYPE_ENUM].currentIndexChanged.connect(self.OnQComboBox_currentIndexChanged)
			self.prop_widgets[PROP_TYPE_FLAGS].anyCheckboxChanged.connect(self.OnFlagsCheckboxesWidget_anyCheckboxChanged)
			self.prop_widgets[PROP_TYPE_ASSET].setPathButtonPressed.connect(self.OnAssetWidget_setPathButtonPressed)
			#self.prop_widgets[PROP_TYPE_ASSET].itemClicked.connect(self.OnQTreeWidget_itemClicked)
			#self.prop_widgets[PROP_TYPE_ASSET].setHeaderLabels(["node", "path"])
			#self.prop_widgets[PROP_TYPE_ASSET].setColumnCount(2)
		self.setLayout(self.layout)
	
	
	def OnQCheckBox_stateChanged(self, state):
		self.anyPropChanged.emit()
	def OnQComboBox_currentIndexChanged(self, text_or_index): 
		#Qt docs state that there are 2 currentIndexChanged(); 
		#one returns a string and the other an int.
		#Not sure which the Python(PySide2) version is.
		self.anyPropChanged.emit()
	def OnHouQtInputField_valueChanged(self):
		self.anyPropChanged.emit()
	def OnHouQtColorSwatchButton_colorChanged(self, qcolor):
		self.anyPropChanged.emit()
	def OnFlagsCheckboxesWidget_anyCheckboxChanged(self):
		self.anyPropChanged.emit()
	def OnAssetWidget_setPathButtonPressed(self):
		self.anyPropChanged.emit()
	#def OnQTreeWidget_itemClicked(self):
	#	self.anyPropChanged.emit()
		
	#
	def get_current_prop(self, prop_owner_class, prop_name, prop_type, propbar_type, pmt_engine):
		self.pmt_engine_proptype = prop_type
		
		prop = self.prop_widgets[propbar_type]
		if propbar_type == PROP_TYPE_UNSUPPORTED:
			pass
		elif propbar_type == PROP_TYPE_ROOTNODE:
			pass
		elif propbar_type == PROP_TYPE_INTERNALNODE:
			pass
		elif propbar_type == PROP_TYPE_BOOL:
			check_state = prop.checkState()
			return str(check_state == QtCore.Qt.Checked).lower()
		elif propbar_type == PROP_TYPE_INT:
			return str(prop.value(0))
		elif propbar_type == PROP_TYPE_FLOAT:
			if pmt_engine == "t3d": return "{:6f}".format(prop.value(0))
			return "{}".format(prop.value(0))
		elif propbar_type == PROP_TYPE_VECTOR2:
			return "{} {}".format(*prop.values())
		elif propbar_type == PROP_TYPE_VECTOR3:
			return "{} {} {}".format(*prop.values())
		elif propbar_type == PROP_TYPE_STRING:
			return prop.value(0)
		elif propbar_type == PROP_TYPE_COLOR:
			qcolor = prop.color()
			color = [ qcolor.redF(), qcolor.greenF(), qcolor.blueF(), qcolor.alphaF() ]
			if pmt_engine == "vmf":
				if prop_type == "color1":
					return "{} {} {}".format(*color[0:3])
				if prop_type == "color255":
					for i in range(len(color)):
						color[i] = int(color[i] * 255.0)
					return "{} {} {}".format(*color[0:3])
			return color
		elif propbar_type == PROP_TYPE_ENUM:
			enum_index = prop.currentIndex()
			enum_list = KVTABLE_get_prop_options_enum(prop_owner_class, prop_name, pmt_engine)
			return enum_list[enum_index]
		elif propbar_type == PROP_TYPE_FLAGS:
			return str(prop.get_flags_value())
		elif propbar_type.startswith(PROP_TYPE_ASSET):
			prop = self.prop_widgets[PROP_TYPE_ASSET]
			propvalue = prop.value()
			
			if pmt_engine == "vmf" and self.prop_widgets[PROP_TYPE_ASSET].asset_type == "sound":
				#if propvalue.startswith(":soundscapes/"):
				#	propvalue = propvalue[len(":soundscapes/"):].replace("/", ".")
				if propvalue.startswith(":soundscripts/"):
					propvalue = propvalue[len(":soundscripts/"):].replace("/", ".")
				elif propvalue.startswith("sound/"):
					propvalue = propvalue[len("sound/"):]
					
			return propvalue
		return None
		
	def set_current_prop(self, prop_owner_class, prop_name, prop_type, propbar_type, prop_value_str, pmt_engine):
		self.pmt_engine_proptype = prop_type
	
		self.prop_key.setText("Key: {} ({})".format(prop_name, prop_type))
		
		combobox_item_index = self.prop_type_combobox.findText(propbar_type, QtCore.Qt.MatchFixedString)
		self.prop_type_combobox.setCurrentIndex(combobox_item_index)
	
		prop = self.prop_widgets[propbar_type]
		if propbar_type == PROP_TYPE_UNSUPPORTED:
			pass
		elif propbar_type == PROP_TYPE_BOOL:
			if prop_value_str.isnumeric():
				is_true = int(prop_value_str)
			elif prop_value_str.lower() == "true":
				is_true = True
			elif prop_value_str.lower() == "false":
				is_true = False
			elif len(prop_value_str) == 0:
				is_true = False
			else:
				assert False, "could not convert prop_value_str '{}'(len {}) into bool".format(prop_value_str, len(prop_value_str))
				
			check_state = QtCore.Qt.Checked if is_true else QtCore.Qt.Unchecked
			prop.setCheckState(check_state)
		elif propbar_type == PROP_TYPE_INT:
			prop.setValue( int(prop_value_str) if prop_value_str.isnumeric() else 0 )
		elif propbar_type == PROP_TYPE_FLOAT:
			prop.setValue( float(prop_value_str) if prop_value_str.isnumeric() else 0.0 ) 
		elif propbar_type == PROP_TYPE_VECTOR2:
			vals = prop_value_str.split(" ", maxsplit = -1)
			vector2 = ( float(vals[0]), float(vals[1]) ) 
			prop.setValues(vector2)
		elif propbar_type == PROP_TYPE_VECTOR3:
			vals = prop_value_str.split(" ", maxsplit = -1)
			vector3 = ( float(vals[0]), float(vals[1]), float(vals[2]) ) 
			prop.setValues(vector3)
		elif propbar_type == PROP_TYPE_STRING:
			prop.setValue(prop_value_str) #string
		elif propbar_type == PROP_TYPE_COLOR:
			#assume prop_value_str is floats in [0.0, 1.0]
			vals = prop_value_str.split(" ", maxsplit = -1)
			rgba = list()
			for valstr in vals:
				rgba.append( float(valstr) )
				
			if pmt_engine == "vmf":
				if prop_type == "color255":
					for i in range(len(rgba)):
						rgba[i] /= 255.0
					
			if len(rgba) < 4:
				rgba.append(1.0)
			qcolor = QtGui.QColor()
			qcolor.setRgbF(*rgba)
			prop.setColor(qcolor)
		elif propbar_type == PROP_TYPE_ENUM:
			enum_list = KVTABLE_get_prop_options_enum(prop_owner_class, prop_name, pmt_engine)
			prop.clear()
			
			value_index = None
			for choice_index in range(len(enum_list)):
				prop.addItem(enum_list[choice_index])
				if prop_value_str.lower() == enum_list[choice_index].lower():
					value_index = choice_index
					
			prop.setCurrentIndex(value_index)		
		elif propbar_type == PROP_TYPE_FLAGS:
			flags_descriptions = get_flags_descriptions(prop_owner_class, prop_name, pmt_engine)
			prop.set_flags_value(int(prop_value_str))
			prop.set_checkbox_descriptions(flags_descriptions)
		elif propbar_type.startswith(PROP_TYPE_ASSET):
			prop = self.prop_widgets[PROP_TYPE_ASSET]
			return prop.set_value(prop_value_str)
			
	def OnPropTypeChanged(self, propbar_type):
		assert propbar_type in PROPBAR_TYPES, "no propbar_type {} in self.prop_widgets".format(propbar_type)
		for type in self.prop_widgets:
			self.prop_widgets[type].hide()
		
		if propbar_type.startswith(PROP_TYPE_ASSET):
			if propbar_type == PROP_TYPE_ASSET_CLASS:
				self.prop_widgets[PROP_TYPE_ASSET].set_asset_type("class", self.pmt_engine_proptype)
			elif propbar_type == PROP_TYPE_ASSET_MATERIAL:
				self.prop_widgets[PROP_TYPE_ASSET].set_asset_type("material", self.pmt_engine_proptype)
			elif propbar_type == PROP_TYPE_ASSET_MESH:
				self.prop_widgets[PROP_TYPE_ASSET].set_asset_type("mesh", self.pmt_engine_proptype)
			elif propbar_type == PROP_TYPE_ASSET_SOUND:
				self.prop_widgets[PROP_TYPE_ASSET].set_asset_type("sound", self.pmt_engine_proptype)
			propwidget = self.prop_widgets[PROP_TYPE_ASSET]
		else:
			propwidget = self.prop_widgets[propbar_type]
		propwidget.show()
		
class EntityKvEditorWindow(QtWidgets.QWidget):
	def __init__(self, pane_tab = None, pmt_engine = "vmf"):
		super().__init__()

		self.current_node = None
		self.current_entity_class = None
			
		self.pane_tab = pane_tab
		self.pmt_engine = pmt_engine
		
		#
		if True:
			self.node_type = QtWidgets.QLabel("Node type:")
			self.node_path_label = QtWidgets.QLabel("Node path:")
			self.node_path = hou.qt.InputField(hou.qt.InputField.StringType, 1, "")
			self.node_path.setMinimumWidth(512)
			self.node_path.setEnabled(False)
			self.node_chooser = hou.qt.NodeChooserButton()
			self.node_chooser.setNodeChooserFilter(hou.nodeTypeFilter.Sop)
			self.node_chooser.nodeSelected.connect(self.OnNodeChooserNodeSelected)
			
		#
		self.kv_treewidget = QtWidgets.QTreeWidget()
		self.kv_treewidget.setHeaderLabels(["key", "value"])
		self.kv_treewidget.setColumnCount(2)
		self.kv_key_to_treeitem = None
		
		#
		self.entpropwidget = EntityPropWidget(pmt_engine)
		self.save_button = QtWidgets.QPushButton("Save to Node")
		self.load_button = QtWidgets.QPushButton("Load from Node")
		self.close_button = QtWidgets.QPushButton("Close")
		
		self.layout = QtWidgets.QVBoxLayout()
		
		node_layout = QtWidgets.QHBoxLayout()
		node_layout.addWidget(self.node_path_label)
		node_layout.addWidget(self.node_chooser)
		node_layout.addWidget(self.node_path)
		#node_layout.addSpacing(LARGE_SPACING)
		self.layout.addLayout(node_layout)
		self.layout.addWidget(self.node_type)
		
		self.layout.addWidget(self.kv_treewidget)
		self.layout.addWidget(self.entpropwidget)
		
		button_layout = QtWidgets.QHBoxLayout()
		button_layout.addWidget(self.save_button)
		button_layout.addWidget(self.load_button)
		self.layout.addLayout(button_layout)
		
		if self.is_in_floating_window():
			self.layout.addWidget(self.close_button)
		
		self.setLayout(self.layout)
		
		#
		if True:
			self.save_button.clicked.connect(self.OnSaveToNodeButton)
			self.load_button.clicked.connect(self.OnLoadFromNodeButton)
			self.close_button.clicked.connect(self.OnCloseButton)
			self.kv_treewidget.itemClicked.connect(self.OnTreeItemClicked)
			self.entpropwidget.anyPropChanged.connect(self.OnPropValueEdited)
		#
		self.setWindowTitle("Entity Editor (engine={})".format(pmt_engine))
		#self.resize(1024, 768)
		#self.show()
		#self.showMaximized()

	def OnPropValueEdited(self):
		if self.current_node != None and self.current_entity_class != None:
			current_item = self.kv_treewidget.currentItem()
			prop_key = current_item.text(COLUMN_KVTREE_KEY)
			prop_type = current_item.text(COLUMN_KVTREE_PROP_TYPE)
			propbar_type = current_item.text(COLUMN_KVTREE_PROPBAR_TYPE)
			prop_value = self.entpropwidget.get_current_prop(self.current_entity_class, prop_key, prop_type, propbar_type, self.pmt_engine)
			current_item.setText(COLUMN_KVTREE_VALUE, prop_value)
			
			#t3d uses a tree for props, so we need to update parent node values until we get to the root
			if self.pmt_engine == "t3d":
				update_item = current_item
				
				#first level of the tree contains categories
				def is_root_or_first_level(treeitem):
					parent = treeitem.parent()
				
					#directly comparing without using type() as below gives a NotImplementedError
					#	treeitem.parent() == None
					is_parent_root = type(parent) == type(None)
					if is_parent_root:
						return True
				
					is_parent_of_parent_root = type(parent.parent()) == type(None)
					return is_parent_of_parent_root
				
				if is_root_or_first_level(update_item):
					return
				
				while type(update_item.parent()) != type(None):
					parent = update_item.parent()
					parent_is_root_or_category = is_root_or_first_level(parent)
					if not parent_is_root_or_category:
						prop_key = update_item.text(COLUMN_KVTREE_KEY)
						prop_value = update_item.text(COLUMN_KVTREE_VALUE)
						
						parent_value = parent.text(COLUMN_KVTREE_VALUE)
						parent_dict = t3d_value_str_to_dict(parent_value)
						parent_dict[prop_key] = prop_value
						updated_value = dict_to_t3d_value_str(parent_dict)
						parent.setText(COLUMN_KVTREE_VALUE, updated_value)
						
					update_item = parent
					
	def OnTreeItemClicked(self,  qtreewidgetitem, column):
		if self.current_node != None and self.current_entity_class != None:
			key = qtreewidgetitem.text(COLUMN_KVTREE_KEY)
			prop_type = qtreewidgetitem.text(COLUMN_KVTREE_PROP_TYPE)
			propbar_type = qtreewidgetitem.text(COLUMN_KVTREE_PROPBAR_TYPE)
			value = qtreewidgetitem.text(COLUMN_KVTREE_VALUE)
			self.entpropwidget.set_current_prop(self.current_entity_class, key, prop_type, propbar_type, value, self.pmt_engine)
			
		
	#signal is hou.qt.NodeChooserButton.nodeSelected(str)
	#note that 'str' is a Houdini node and not a string
	def OnNodeChooserNodeSelected(self, node):
		self.OnNodePathChanged(node)
	def OnNodePathChanged(self, node):
		if node == None: return
	
		self.entpropwidget.OnPropTypeChanged(PROP_TYPE_UNSUPPORTED)
		
		path = node.path()
		self.node_path.setValue(path)
		self.node_type.setText("Node type: " + node.type().nameWithCategory())
	
		self.kv_treewidget.clear()
		self.kv_key_to_treeitem = dict()
		
		def has_class_and_kv_parms(node, pmt_engine):
			class_parm_name = "pmt_{}_entity_class".format(pmt_engine)
			class_parm = node.parm(class_parm_name)
			if class_parm == None:
				has_classname = False
			else:
			#	has_classname = type(str()) == type(class_parm.eval())
				has_classname = type(str()) == type(class_parm.evalAsString())
			
			kv_parm_name = "{}_keyvalues".format(pmt_engine)
			possible_dict_parm = node.parm(kv_parm_name)
			if possible_dict_parm == None:
				has_dict_parm = False
			else:	
				has_dict_parm = type(dict()) == type(possible_dict_parm.eval())
			return (has_classname, has_dict_parm)
			
		TARGET_NODE_TYPE = "pmt::Sop/pmi_entity_init"
		node_type_str = node.type().nameWithCategory()
		#if node_type_str != TARGET_NODE_TYPE:
		#	node_type_text = "Node type: {} (select a {} to edit.)".format(node_type_str, TARGET_NODE_TYPE)
		#	self.node_type.setText(node_type_text)
		#	
		#	self.current_node = None
		#	self.current_entity_class = None
		(has_classname, has_dict_parm) = has_class_and_kv_parms(node, self.pmt_engine)
		if not has_classname or not has_dict_parm:
			class_parm_name = "pmt_{}_entity_class".format(self.pmt_engine)
			kv_parm_name = "{}_keyvalues".format(self.pmt_engine)
		
			if not has_classname and has_dict_parm:
				node_type_text = "Node type: {} (node needs a classname(string) parm '{}')".format(node_type_str, class_parm_name)
			if has_classname and not has_dict_parm:
				node_type_text = "Node type: {} (node needs a keyvalue(dict) parm '{}')".format(node_type_str, kv_parm_name)
			if not has_classname and not has_dict_parm:
				node_type_text = "Node type: {} (node needs a classname(string) parm '{}' and keyvalue(dict) parm '{}')".format(node_type_str, class_parm_name, kv_parm_name)
			self.node_type.setText(node_type_text)
			
			self.current_node = None
			self.current_entity_class = None
		else:
			node_classname, node_keyvalue_dict = get_node_parameters(node, self.pmt_engine)
			propname_list = get_list_of_class_prop_names(node_classname, self.pmt_engine)
			
			if propname_list != None:
				node_type_text = "Node type: {} (class: {})".format(node_type_str, node_classname)
				self.node_type.setText(node_type_text)
				
				self.current_node = node
				self.current_entity_class = node_classname
				
				num_props = len(propname_list)
				
				if self.pmt_engine == "vmf" or self.pmt_engine == "map":
					treeroot = QtWidgets.QTreeWidgetItem(1)
					treeroot.setText(0, "class: {}".format(node_classname))
					treeroot.setText(COLUMN_KVTREE_PROPBAR_TYPE, PROP_TYPE_ROOTNODE)
					self.kv_treewidget.addTopLevelItem(treeroot)
					self.kv_treewidget.setColumnWidth(COLUMN_PROPERTY_KEY, 320)
					treeroot.setExpanded(True) #Qt docs state setExpanded() must be called after addTopLevelItem()
					
					for row_index in range(num_props):
						name = propname_list[row_index]
						
						name_label = QtWidgets.QLabel(name)
						name_label.setIndent(16)
						
						prop_type = get_prop_type(self.current_entity_class, name, self.pmt_engine)
						if name in node_keyvalue_dict:
							node_value = node_keyvalue_dict[name]
							if self.pmt_engine == "vmf" and prop_type == "choices":
								node_value = choices_value_to_description(node_value, self.current_entity_class, name, self.pmt_engine)
							prop_value = node_value
						else:
							prop_value = KVTABLE_get_prop_default(self.current_entity_class, name, self.pmt_engine)
							
						treeitem = QtWidgets.QTreeWidgetItem(treeroot, 1)
						treeitem.setText(COLUMN_KVTREE_KEY, name)
						treeitem.setText(COLUMN_KVTREE_VALUE, prop_value)
						treeitem.setText(COLUMN_KVTREE_PROP_TYPE, prop_type)
						treeitem.setText(COLUMN_KVTREE_PROPBAR_TYPE, prop_type_to_propbar_type(prop_type, self.pmt_engine))
						self.kv_key_to_treeitem[name] = treeitem
					#according to qt docs, sortChildren() has no effect if QTreeWidgetItem is not assigned to a QTreeWidget
					treeroot.sortChildren(COLUMN_KVTREE_KEY, QtCore.Qt.AscendingOrder)
				elif self.pmt_engine == "t3d":
					treeroot = uclass_to_treeitems(node_classname)
					self.kv_treewidget.addTopLevelItem(treeroot)
					self.kv_treewidget.setColumnWidth(COLUMN_PROPERTY_KEY, 320)
					treeroot.setExpanded(True) #Qt docs state setExpanded() must be called after addTopLevelItem()
					
					SORT_UCLASS_TREE = True
					if SORT_UCLASS_TREE:
						#according to qt docs, sortChildren() has no effect if QTreeWidgetItem is not assigned to a QTreeWidget
						treeroot.sortChildren(COLUMN_KVTREE_KEY, QtCore.Qt.AscendingOrder)
						for category_index in range(treeroot.childCount()):
							category_treeitem = treeroot.child(category_index)
							category_treeitem.sortChildren(COLUMN_KVTREE_KEY, QtCore.Qt.AscendingOrder)
			
					for root_child in range(treeroot.childCount()):
						treecategory = treeroot.child(root_child)
						for category_child in range(treecategory.childCount()):
							treevar = treecategory.child(category_child)
							key = treevar.text(COLUMN_KVTREE_KEY)
							self.kv_key_to_treeitem[key] = treevar
					
			else:
				node_type_text = "Node type: {} (class: {}) (ERROR: entity class not found)".format(node_type_str, node_classname)
				self.node_type.setText(node_type_text)
			
	def OnLoadFromNodeButton(self):
		if self.current_node != None and self.current_entity_class != None:
			node_classname, node_keyvalue_dict = get_node_parameters(self.current_node, self.pmt_engine)
			
			for key in self.kv_key_to_treeitem:
				treeitem = self.kv_key_to_treeitem[key]
				if key in node_keyvalue_dict:
					prop_type = get_prop_type(self.current_entity_class, key, self.pmt_engine)
					node_value = node_keyvalue_dict[key]
					if self.pmt_engine == "vmf" and prop_type == "choices":
						node_value = choices_value_to_description(node_value, self.current_entity_class, key, self.pmt_engine)
					treeitem.setText(COLUMN_KVTREE_VALUE, node_value)
					
					if self.pmt_engine == "t3d" and treeitem.childCount() > 0:
						def propagate_loaded_value_to_children(node, value):
							t3d_value_dict = t3d_value_str_to_dict(node_value)
							for child_index in range(node.childCount()):
								child = node.child(child_index)
								
								child_key = child.text(COLUMN_KVTREE_KEY)
								if child_key in t3d_value_dict:
									child_value = t3d_value_dict[child_key]
									child.setText(COLUMN_KVTREE_VALUE, child_value)
									propagate_loaded_value_to_children(child, child_value)
						propagate_loaded_value_to_children(treeitem, node_value)
						
	def OnSaveToNodeButton(self):
		if self.current_node != None and self.current_entity_class != None:
			nondefault_kv_dict = dict()
			
			for key in self.kv_key_to_treeitem:
				treeitem = self.kv_key_to_treeitem[key]
				prop_value = treeitem.text(COLUMN_KVTREE_VALUE)
				prop_type = get_prop_type(self.current_entity_class, key, self.pmt_engine)
				if self.pmt_engine == "vmf" or self.pmt_engine == "map":
					default_value = KVTABLE_get_prop_default(self.current_entity_class, key, self.pmt_engine)
					if prop_value != default_value:
						if self.pmt_engine == "vmf" and prop_type == "choices":
							prop_value = choices_description_to_value(prop_value, self.current_entity_class, key, self.pmt_engine)
						nondefault_kv_dict[key] = prop_value
				elif self.pmt_engine == "t3d":
					nondefault_kv_dict[key] = prop_value
			set_node_parameters(self.current_node, self.pmt_engine, nondefault_kv_dict)
			
	def is_in_floating_window(self):
		return self.pane_tab != None and self.pane_tab.floatingPanel() != None
		
	def OnCloseButton(self):
		pane_tab = self.pane_tab
		if pane_tab != None:
			floating_panel = pane_tab.floatingPanel()
			if floating_panel != None:
				floating_panel.close()	
		
#Python panel init for when this is used as a python module in pmt::pmt__global_config
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_entity_kv_editor.EntityKvEditorWindow(pane_tab, "vmf")
	# return window	
# def onNodePathChanged(node):
	# if window != None: window.OnNodePathChanged(node)
	
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_entity_kv_editor.EntityKvEditorWindow(pane_tab, "t3d")
	# return window	
# def onNodePathChanged(node):
	# if window != None: window.OnNodePathChanged(node)
	
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_entity_kv_editor.EntityKvEditorWindow(pane_tab, "map")
	# return window	
# def onNodePathChanged(node):
	# if window != None: window.OnNodePathChanged(node)

#Python panel init for when this is used as a python panel, for testing
IS_PYTHON_PANEL = False
if IS_PYTHON_PANEL:
	window = None
	def onCreateInterface():
		pane_tab = kwargs["paneTab"]
		global window
		#window = EntityKvEditorWindow(pane_tab, "vmf")
		#window = EntityKvEditorWindow(pane_tab, "t3d")
		window = EntityKvEditorWindow(pane_tab, "map")
		return window
	def onNodePathChanged(node):
		window.OnNodePathChanged(node)
