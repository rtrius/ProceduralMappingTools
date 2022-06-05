#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_qt_materialsets_editor
#	script_section_name: 	pmt_qt_materialsets_editor.py
#
# An editor for materialsets, stored in .matlist.txt files.

#Houdini 18.5 docs state that PySide2/Qt must be run on Houdini's main thread.
#This means that any subclasses of PySide2/Qt classes must be implemented 
#as a python panel or as a tool on the tool shelf.
#
#Directly instantiating a MaterialSetsEditorWindow will cause it to close immediately, 
#so we use a different approach with python panels.
#
##First, create a .pypanel file that will create the window:
#def onCreateInterface():
#    pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
#    window = pmt__global_config.pmt_qt_materialsets_editor.MaterialSetsEditorWindow("vmf")
#    return window
#
##Then install the .pypanel in OnInstall(), which is run when the .hda is installed: 
#hou.pypanel.installFile(PYPANEL_FILE_PATH)
#
##In order to actually create the window, use:
#hou.ui.curDesktop().createFloatingPaneTab(hou.paneTabType.PythonPanel, position=(), size=(1024,768), python_panel_interface=INTERFACE_NAME, immediate=True)
	

import os
import sys
import random
import threading
import shutil
from PySide2 import QtCore, QtWidgets, QtGui

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
###__pmt::pmt__globalconfig__COMMON_SECTION_EXTERNAL__

IN_HOUDINI = 'hou' in sys.modules
def DPRINT(string, level = 1):
	#0 to turn off debug messages, higher level == more messages
	DEBUG_LEVEL = 1 if not IN_HOUDINI else 0
	if DEBUG_LEVEL >= level:
		print(string)
		
#Column indices for QTreeWidget
COLUMN_MATERIAL_NAME = 0	
COLUMN_MATERIAL_PATH_HIDDEN = 1

#Background colors for QListWidget
BRUSH_BACKGROUND_CHECKED = QtGui.QBrush(QtGui.QColor(64,128,192,255))
BRUSH_BACKGROUND_UNCHECKED = QtGui.QBrush(QtGui.QColor(0,0,0,0))
FONT_BOLD_ITALIC = QtGui.QFont()
FONT_BOLD_ITALIC.setBold(True)
FONT_BOLD_ITALIC.setItalic(True)
FONT_DEFAULT = QtGui.QFont()
FONT_DEFAULT.setBold(False)
FONT_DEFAULT.setItalic(False)

LISTWIDGET_ICON_SIZE = QtCore.QSize(128,128)
IMAGEVIEW_SIZE = QtCore.QSize(512,512)

COLUMN_MATERIALSET_STYLECATEGORY = 0
COLUMN_MATERIALSET_TYPE = 1
MATERIALSET_TYPE_ROOT = "root"
MATERIALSET_TYPE_STYLE = "style"
MATERIALSET_TYPE_CATEGORY = "type"

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
def get_path_sep(pmt_engine = "vmf"):
	if pmt_engine == "vmf":
		return '/'
	elif pmt_engine == "map":
		return '/'
	elif pmt_engine == "t3d":
		return '.'
		
	assert False, "MaterialsetsSelector get_path_sep() invalid pmt_engine {}".format(pmt_engine)
	return None

def get_materialsets_root_path(pmt_engine = "vmf"):
	materialsets_path = "{}_materialsets_path".format(pmt_engine)
	if pmt_engine == "vmf" or pmt_engine == "t3d" or pmt_engine == "map":
		return PMT__G_CFG.g_cfg.get_config(pmt_engine, materialsets_path)

	assert False, "MaterialsetsSelector get_materialsets_root_path() invalid pmt_engine {}".format(pmt_engine)
	return None

			
MATERIALSET_EXTENSION = ".matlist.txt"
def get_style_or_category_fs_path(pmt_engine, style, category):
	root = get_materialsets_root_path(pmt_engine)
	if not root.endswith('/'):
		root += '/'
		
	target_path = None
	target_error = None
		
	if style == "":
		if category == "":
			target_error = "Type in or select a 'style' and 'category'."
		else:
			target_error = "Type in or select a 'style'."
	else:
		if category == "":
			target_path = root + "{}".format(style)
		else:
			target_path = root + "{}/{}{}".format(style, category, MATERIALSET_EXTENSION)
			
	return (target_path, target_error)
def get_category_fs_path(pmt_engine, style, category):
	root = get_materialsets_root_path(pmt_engine)
	if not root.endswith('/'):
		root += '/'
		
	target_path = None
	target_error = None
		
	if style == "" or category == "":
		target_error = "Both 'style' and 'category' should must be valid."
	else:
		target_path = root + "{}/{}{}".format(style, category, MATERIALSET_EXTENSION)
			
	return (target_path, target_error)
		
def get_materialsets_styles_dict(pmt_engine):
	if pmt_engine == "vmf":
		return PMT__G_CFG.vmf_materialsets.styles_dict
	elif pmt_engine == "t3d":
		return PMT__G_CFG.t3d_materialsets.styles_dict
	elif pmt_engine == "map":
		return PMT__G_CFG.map_materialsets.styles_dict
		
	assert False, "MaterialsetsSelector get_materialsets() invalid pmt_engine {}".format(pmt_engine)
	return None

def reload_materialsets_styles_dict(pmt_engine):
	if pmt_engine == "vmf":
		return PMT__G_CFG.vmf_load_materialsets().styles_dict
	elif pmt_engine == "t3d":
		return PMT__G_CFG.t3d_load_materialsets().styles_dict
	elif pmt_engine == "map":
		return PMT__G_CFG.map_load_materialsets().styles_dict
		
	assert False, "MaterialsetsSelector load_materialsets() invalid pmt_engine {}".format(pmt_engine)
	return None

def create_qtreewidgetitems_for_materialsets(pmt_engine, styles_dict):
	materialsets_root = QtWidgets.QTreeWidgetItem(1)
	materialsets_root.setText(COLUMN_MATERIALSET_STYLECATEGORY, "[{}_materialsets_path]".format(pmt_engine))
	materialsets_root.setText(COLUMN_MATERIALSET_TYPE, MATERIALSET_TYPE_ROOT) #store the 'type' of the node in a hidden column
	for style in styles_dict:
		style_treeitem = QtWidgets.QTreeWidgetItem(materialsets_root, 1)
		style_treeitem.setText(COLUMN_MATERIALSET_STYLECATEGORY, style)
		style_treeitem.setText(COLUMN_MATERIALSET_TYPE, MATERIALSET_TYPE_STYLE) #store the 'type' of the node in a hidden column
		for category in styles_dict[style]:
			category_treeitem = QtWidgets.QTreeWidgetItem(style_treeitem, 1)
			category_treeitem.setText(COLUMN_MATERIALSET_STYLECATEGORY, category)
			category_treeitem.setText(COLUMN_MATERIALSET_TYPE, MATERIALSET_TYPE_CATEGORY) #store the 'type' of the node in a hidden column
			material_list = styles_dict[style][category]
	return materialsets_root
	
def paths_to_qtreewidgetitems(paths, path_sep):
	qtreeitem_dict = dict()
	top_level_paths = set()
	top_level_items = set()
	leaf_node_items = list()
	
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
				item.setCheckState(0, QtCore.Qt.Unchecked)
				item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsAutoTristate)
				item.setText(COLUMN_MATERIAL_NAME, material_or_directory) 
				item.setText(COLUMN_MATERIAL_PATH_HIDDEN, path)	 #store the complete material_path in column 1(not visible)
				if not is_leaf:
					item.setFont(COLUMN_MATERIAL_NAME, FONT_BOLD_ITALIC) #distinguish between materials and folders in the tree
					
				qtreeitem_dict[path] = item
				if depth == 0:
					top_level_paths.add(path)
					top_level_items.add(item)
				elif is_leaf: 
					leaf_node_items.append(item)
					
	return (qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items)

def create_listwidgetitems(qtreewidgetitems_dict, path_sep):
	qlistitem_dict = dict()

	for material_path in qtreewidgetitems_dict:
		treeitem = qtreewidgetitems_dict[material_path]
		
		#Images are loaded on demand, loading all(thousands of) images here is very slow, so use a placeholder icon
		icon = QtGui.QIcon()
		
		if path_sep in material_path:
			last_sep = material_path.rfind(path_sep)
			material_name = material_path[last_sep+1:]
		else:
			material_name = material_path
		listitem = QtWidgets.QListWidgetItem(icon, material_name)
		listitem.setBackground(BRUSH_BACKGROUND_UNCHECKED)
		listitem.setFont(FONT_DEFAULT)
	
		listitem.setData(QtCore.Qt.UserRole, material_path)	#listitem.data(QtCore.Qt.UserRole)
	
		qlistitem_dict[material_path] = listitem
	
	return qlistitem_dict
	
class MaterialSetsEditorWindow(QtWidgets.QWidget):
	def __init__(self, pmt_engine = "vmf"):
		super().__init__()
		
		#pmt_engine = "vmf"
		self.setWindowTitle("MaterialSets Editor (engine={})".format(pmt_engine))
		
		self.pmt_engine = pmt_engine
			
		#Top row tree and image display
		top_layout = QtWidgets.QHBoxLayout()
		if True:
			if True:
				matsets_tree_layout = QtWidgets.QVBoxLayout()
		
				self.matsets_treewidget = QtWidgets.QTreeWidget()
				self.matsets_treewidget.setHeaderLabels(["MaterialSets"])
				self.matsets_treeroot = create_qtreewidgetitems_for_materialsets(self.pmt_engine, get_materialsets_styles_dict(self.pmt_engine))
				self.matsets_treewidget.addTopLevelItem(self.matsets_treeroot)
				self.matsets_treewidget.itemClicked.connect(self.matsets_OnTreeItemClicked)
				matsets_tree_layout.addWidget(self.matsets_treewidget)
				
				if True: #Create style and category textboxes
					matsets_line_layout = QtWidgets.QHBoxLayout()
					self.matsets_style_line = QtWidgets.QLineEdit()
					self.matsets_category_line = QtWidgets.QLineEdit()
					matsets_line_layout.addWidget(QtWidgets.QLabel("Style:"))
					matsets_line_layout.addWidget(self.matsets_style_line)
					matsets_line_layout.addWidget(QtWidgets.QLabel("Category:"))
					matsets_line_layout.addWidget(self.matsets_category_line)
					matsets_tree_layout.addLayout(matsets_line_layout)
					
				if True: #Create create and delete buttons
					matsets_tree_button_layout = QtWidgets.QHBoxLayout()
					self.matsets_create_button = QtWidgets.QPushButton("Create")
					self.matsets_create_button.clicked.connect(self.matsets_OnCreateButton)
					self.matsets_delete_button = QtWidgets.QPushButton("Delete")
					self.matsets_delete_button.clicked.connect(self.matsets_OnDeleteButton)
					matsets_tree_button_layout.addWidget(self.matsets_create_button)
					matsets_tree_button_layout.addWidget(self.matsets_delete_button)
					matsets_tree_layout.addLayout(matsets_tree_button_layout)
				top_layout.addLayout(matsets_tree_layout)
				
			if True:
				material_tree_layout = QtWidgets.QVBoxLayout()
				self.material_treewidget = QtWidgets.QTreeWidget()
				self.material_treewidget.setHeaderLabels(["Select a category to select materials."])
				self.material_treewidget.setColumnCount(1)
				
				materials = get_materials(self.pmt_engine)
				(qtreeitem_dict, top_level_paths, top_level_items, leaf_node_items) = paths_to_qtreewidgetitems(materials, get_path_sep(self.pmt_engine))
				qlistitem_dict = create_listwidgetitems(qtreeitem_dict, get_path_sep(self.pmt_engine))
				
				self.qtreeitem_dict = qtreeitem_dict
				self.qlistitem_dict = qlistitem_dict
				self.leaf_node_items = leaf_node_items
				
				for qitem in top_level_items:
					self.material_treewidget.addTopLevelItem(qitem)
				self.material_treewidget.sortItems(0, QtCore.Qt.AscendingOrder)
						
				self.material_treewidget.itemClicked.connect(self.material_OnTreeItemClicked)
				self.material_treewidget.itemChanged.connect(self.OnTreeItemChanged)
			
				material_tree_layout.addWidget(self.material_treewidget)
				
				if True: #create the save button
					material_tree_button_layout = QtWidgets.QHBoxLayout()
					self.save_button = QtWidgets.QPushButton("Save")
					self.save_button.clicked.connect(self.OnSaveButton)
					self.load_button = QtWidgets.QPushButton("Load")
					self.load_button.clicked.connect(self.OnLoadButton)
					material_tree_button_layout.addWidget(self.save_button)
					material_tree_button_layout.addWidget(self.load_button)
					material_tree_layout.addLayout(material_tree_button_layout)
					
				top_layout.addLayout(material_tree_layout)
				
			if True: #create the 'main' image display
				self.image_display_label = QtWidgets.QLabel("[material]")
				self.image_display_label.setAlignment(QtCore.Qt.AlignCenter)
				self.image_display_label.setMaximumSize(IMAGEVIEW_SIZE)
				self.image_display_label.setMinimumSize(IMAGEVIEW_SIZE)
				top_layout.addWidget(self.image_display_label)
		
		
		#Mid row listwidget used to display items in the current folder
		list_layout = QtWidgets.QHBoxLayout()
		if True:
			self.listwidget = QtWidgets.QListWidget()
			self.listwidget.setViewMode(QtWidgets.QListView.IconMode)
			self.listwidget.setResizeMode(QtWidgets.QListView.Adjust)
			self.listwidget.setMovement(QtWidgets.QListView.Static)
			
			self.listwidget.setIconSize(LISTWIDGET_ICON_SIZE)
			self.listwidget.itemClicked.connect(self.OnListItemClicked)
			self.listwidget.itemChanged.connect(self.OnListItemChanged)
			list_layout.addWidget(self.listwidget)
		
		
		self.listwidget_label = QtWidgets.QLabel("[path]")
		self.listwidget_label.setAlignment(QtCore.Qt.AlignLeft)
		
		#Bottom row buttons
		#if True:
		#	self.close_button = QtWidgets.QPushButton("Close")
		#	self.close_button.clicked.connect(self.OnCloseButton)
		
		#Main layout
		self.layout = QtWidgets.QVBoxLayout()
		self.layout.addLayout(top_layout)
		self.layout.addLayout(list_layout)
		self.layout.addWidget(self.listwidget_label)
		#self.layout.addWidget(self.close_button)
		self.setLayout(self.layout)
		
		#
		self.current_listwidget_folder = None
		
		#
		self.resize(1024, 768)
		#self.show()
		self.showMaximized()
	
	def matsets_OnTreeItemClicked(self, qtreewidgetitem, column):
		item = qtreewidgetitem
		
		is_root = item.text(COLUMN_MATERIALSET_TYPE) == MATERIALSET_TYPE_ROOT
		is_style = item.text(COLUMN_MATERIALSET_TYPE) == MATERIALSET_TYPE_STYLE
		is_category = item.text(COLUMN_MATERIALSET_TYPE) == MATERIALSET_TYPE_CATEGORY
		if is_root:
			self.matsets_style_line.setText("")
			self.matsets_category_line.setText("")
			self.material_treewidget.setHeaderLabels(["Select a category to select materials."])
		elif is_style:
			style = item.text(COLUMN_MATERIALSET_STYLECATEGORY)
			self.matsets_style_line.setText(style)
			self.matsets_category_line.setText("")
			self.material_treewidget.setHeaderLabels(["Select a category to select materials. (selected style '{}')".format(style)])
		elif is_category:
			style = item.parent().text(COLUMN_MATERIALSET_STYLECATEGORY)
			category = item.text(COLUMN_MATERIALSET_STYLECATEGORY)
			self.matsets_style_line.setText(style)
			self.matsets_category_line.setText(category)
			self.material_treewidget.setHeaderLabels(["Materials for style '{}' and category '{}'".format(style, category)])
		else:
			assert False
			
		
	def matsets_OnCreateButton(self):
		DPRINT("matsets_OnCreateButton")
		style = self.matsets_style_line.text().lower()
		category = self.matsets_category_line.text().lower()
		target_path, target_error = get_style_or_category_fs_path(self.pmt_engine, style, category)
		style_folder = target_path[:target_path.rfind('/')]
		DPRINT("target_path: {}".format(target_path))
		if target_error != None:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Create MaterialSet", "Error: {}".format(target_error))
			dialog.exec_()
		else:
			if os.path.exists(target_path):
				dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Create MaterialSet", "Error: path already exists: {}".format(target_path))
				dialog.exec_()
				DPRINT("path already exists: {}".format(target_path))
			else:
				def create_style_folder(self, style, style_folder_path):
					if not os.path.exists(style_folder_path):
						os.makedirs(style_folder_path)
						
						style_treeitem = QtWidgets.QTreeWidgetItem(self.matsets_treeroot, 1)
						style_treeitem.setText(COLUMN_MATERIALSET_STYLECATEGORY, style)
						style_treeitem.setText(COLUMN_MATERIALSET_TYPE, MATERIALSET_TYPE_STYLE) #store the 'type' of the node in a hidden column
						return style_treeitem
					else:
						return None
						
				def find_style_item(self, style):
					for style_index in range(self.matsets_treeroot.childCount()):
						treeitem = self.matsets_treeroot.child(style_index)
						if treeitem.text(COLUMN_MATERIALSET_STYLECATEGORY) == style:
							return treeitem
					return None	
					
				if target_path.endswith(MATERIALSET_EXTENSION):
					styles_dict = get_materialsets_styles_dict(self.pmt_engine)
					if style not in styles_dict:
						style_treeitem = create_style_folder(self, style, style_folder)
					else:
						style_treeitem = find_style_item(self, style)
					
					category_treeitem = QtWidgets.QTreeWidgetItem(style_treeitem, 1)
					category_treeitem.setText(COLUMN_MATERIALSET_STYLECATEGORY, category)
					category_treeitem.setText(COLUMN_MATERIALSET_TYPE, MATERIALSET_TYPE_CATEGORY) #store the 'type' of the node in a hidden column
						
					with open(target_path, 'wt') as f:
						pass
					
					reload_materialsets_styles_dict(self.pmt_engine)
				else:
					create_style_folder(self, style, style_folder)
					reload_materialsets_styles_dict(self.pmt_engine)
			
	def matsets_OnDeleteButton(self):
		DPRINT("matsets_OnDeleteButton")
		style = self.matsets_style_line.text().lower()
		category = self.matsets_category_line.text().lower()
		target_path, target_error = get_style_or_category_fs_path(self.pmt_engine, style, category)
	
		if target_error != None:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Delete MaterialSet", "Error: {}".format(target_error))
			dialog.exec_()
		else:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Delete MaterialSet", "Confirm delete? {}".format(target_path))
			dialog.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
			dialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
			response = dialog.exec_()
			if response == QtWidgets.QMessageBox.Ok:
				if target_path.endswith(MATERIALSET_EXTENSION):
				
					#remove the category from matsets tree
					found_style_treeitem = False
					style_treeitem = None
					for style_index in range(self.matsets_treeroot.childCount()):
						treeitem = self.matsets_treeroot.child(style_index)
						if treeitem.text(COLUMN_MATERIALSET_STYLECATEGORY) == style:
							found_style_treeitem = True
							style_treeitem = treeitem
							break
							
					if found_style_treeitem: #(style_treeitem != None) returns an 'operator not implemented' error
						for category_index in range(style_treeitem.childCount()):
							treeitem = style_treeitem.child(category_index)
							if treeitem.text(COLUMN_MATERIALSET_STYLECATEGORY) == category:
								style_treeitem.takeChild(category_index)
								break
					
					#delete the .matlist.txt on the actual filesystem
					os.remove(target_path) 
					reload_materialsets_styles_dict(self.pmt_engine)
				else:
					#remove the style from matsets tree
					for child_index in range(self.matsets_treeroot.childCount()):
						style_treeitem = self.matsets_treeroot.child(child_index)
						if style_treeitem.text(COLUMN_MATERIALSET_STYLECATEGORY) == style:
							self.matsets_treeroot.takeChild(child_index)
							break
							
					#delete the entire directory in target_path on the actual filesystem
					shutil.rmtree(target_path)
					reload_materialsets_styles_dict(self.pmt_engine)
			
	def material_OnTreeItemClicked(self, qtreewidgetitem, column):	   
		treeitem = qtreewidgetitem
		
		#update the main image display
		material_path = treeitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
		DPRINT("material_OnTreeItemClicked: column {} path {}".format(column, material_path))
		is_leaf_node = treeitem.childCount() == 0
		if is_leaf_node:
			diffuse_fs = get_diffuse_fs(self.pmt_engine, material_path)
			pixmap = QtGui.QPixmap(diffuse_fs)
			pixmap = pixmap.scaled(IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
			self.image_display_label.setPixmap(pixmap)
			
			listwidget_treeitem = qtreewidgetitem.parent()
		else:
			self.image_display_label.setPixmap(None)
			self.image_display_label.setText("[material]")
			listwidget_treeitem = qtreewidgetitem
		
		#if qtreewidgetitem is a leaf, updates listwidget with the items in the same folder,
		#otherwise, update listwidget in the folder at qtreewidgetitem
		def update_listwidget(listwidget, material_to_listitem_dict, qtreewidgetitem):
			child_leaves = list()
			num_children = qtreewidgetitem.childCount()
			for i in range(num_children):
				child = qtreewidgetitem.child(i)
				is_child_leaf = child.childCount() == 0
				if is_child_leaf:
					child_leaves.append(child)
			
			#Remove all items from the QListWidget
			for listitem in listwidget.findItems("*", QtCore.Qt.MatchWildcard):
				row = listwidget.row(listitem)
				listwidget.takeItem(row)
			
			USE_THREAD = True
			if not USE_THREAD:
				for qtreewidgetitem in child_leaves:
					material_path = qtreewidgetitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
					listitem = material_to_listitem_dict[material_path]
					diffuse_fs = get_diffuse_fs(self.pmt_engine, material_path)
					DPRINT("OnTreeItemClicked() load diffusefs {}".format(diffuse_fs))
					pixmap = QtGui.QPixmap(diffuse_fs)
					icon = QtGui.QIcon(pixmap)
					listitem.setIcon(icon)
					
					listwidget.addItem(listitem)
			else:
				#Update listitems in listwidget - use placeholder images/pixmap
				for qtreewidgetitem in child_leaves:
					material_path = qtreewidgetitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
					listitem = material_to_listitem_dict[material_path]
					
					empty_pixmap = QtGui.QPixmap(LISTWIDGET_ICON_SIZE)
					empty_pixmap.fill(QtGui.QColor(0,0,0,0))
					loading_icon = QtGui.QIcon(empty_pixmap)
					listitem.setIcon(loading_icon)	
					listwidget.addItem(listitem)
				
				#Image loading is run in a separate thread to prevent the main thread from stalling
				def listwidget_load_images(listwidget, child_leaves, material_to_listitem_dict, get_diffuse_fs_func, pmt_engine):
					for qtreewidgetitem in child_leaves:
						material_path = qtreewidgetitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
						listitem = material_to_listitem_dict[material_path]
						diffuse_fs = get_diffuse_fs_func(pmt_engine, material_path)
						DPRINT("OnTreeItemClicked() load diffusefs {}".format(diffuse_fs))
						pixmap = QtGui.QPixmap(diffuse_fs)
						icon = QtGui.QIcon(pixmap)
						listitem.setIcon(icon)
						listwidget.updateGeometry()
				listwidget_load_images_args = (listwidget, child_leaves, material_to_listitem_dict, get_diffuse_fs, self.pmt_engine)
				image_thread = threading.Thread(target=listwidget_load_images, args = listwidget_load_images_args)
				image_thread.start()
				
			
		selected_folder_path = listwidget_treeitem.text(COLUMN_MATERIAL_PATH_HIDDEN)	
		if self.current_listwidget_folder != selected_folder_path:
			update_listwidget(self.listwidget, self.qlistitem_dict, listwidget_treeitem)
			self.listwidget_label.setText(selected_folder_path)
		self.current_listwidget_folder = selected_folder_path
			
		self.listwidget.setCurrentItem(self.qlistitem_dict[material_path])
		
	def OnTreeItemChanged(self, qtreewidgetitem):
		DPRINT("OnTreeItemChanged")
		
		#This function is run when the user clicks on the checkbox in the QTreeWidget
		#Update the corresponding item in the QListView to show if it has been selected
		treeitem = qtreewidgetitem
		treecheck = treeitem.checkState(COLUMN_MATERIAL_NAME)
		material_path = qtreewidgetitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
		listitem = self.qlistitem_dict[material_path]
		if treecheck == QtCore.Qt.Checked or treecheck == QtCore.Qt.PartiallyChecked:
			listitem.setBackground(BRUSH_BACKGROUND_CHECKED)
			listitem.setFont(FONT_BOLD_ITALIC)
		else: #if treecheck == QtCore.Qt.Unchecked:
			listitem.setBackground(BRUSH_BACKGROUND_UNCHECKED)
			listitem.setFont(FONT_DEFAULT)
			
	def OnListItemClicked(self, qlistwidgetitem):
		#When we click an item in the list, find the corresponding tree item(material) and toggle the checkbox
		listitem = qlistwidgetitem
		material_path = listitem.data(QtCore.Qt.UserRole)
		treeitem = self.qtreeitem_dict[material_path]
		treecheck = treeitem.checkState(COLUMN_MATERIAL_NAME)
		if treecheck == QtCore.Qt.Checked or treecheck == QtCore.Qt.PartiallyChecked:
			treeitem.setCheckState(COLUMN_MATERIAL_NAME, QtCore.Qt.Unchecked)
		else: #if treecheck == QtCore.Qt.Unchecked:
			treeitem.setCheckState(COLUMN_MATERIAL_NAME, QtCore.Qt.Checked)
		self.material_treewidget.setCurrentItem(treeitem, COLUMN_MATERIAL_NAME)
		
		#Also, update the main image view to show the material we clicked on
		diffuse_fs = get_diffuse_fs(self.pmt_engine, material_path)
		pixmap = QtGui.QPixmap(diffuse_fs)
		pixmap = pixmap.scaled(IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
		self.image_display_label.setPixmap(pixmap)
		
	def OnListItemChanged(self, qlistwidgetitem):
		listitem = qlistwidgetitem
		
	def get_material_treewidget_checked_paths(self):
		checked_paths = list()
		for item in self.leaf_node_items:
			is_checked = item.checkState(COLUMN_MATERIAL_NAME) == QtCore.Qt.Checked
			if is_checked:
				material_path = item.text(COLUMN_MATERIAL_PATH_HIDDEN)
				checked_paths.append(material_path)
		return checked_paths
	def set_material_treewidget_checked_paths(self, material_path_list):
		for material_path in self.qtreeitem_dict:
			qtreeitem = self.qtreeitem_dict[material_path]
			qtreeitem.setCheckState(COLUMN_MATERIAL_NAME, QtCore.Qt.Unchecked)
		for material_path in material_path_list:
			qtreeitem = self.qtreeitem_dict[material_path.lower()] #older .matlist.txt might have uppercase letters, which are not in the material dict
			qtreeitem.setCheckState(COLUMN_MATERIAL_NAME, QtCore.Qt.Checked)
	
	def OnSaveButton(self):
		style = self.matsets_style_line.text().lower()
		category = self.matsets_category_line.text().lower()
		
		(target_path, target_error) = get_category_fs_path(self.pmt_engine, style, category)
		if target_error != None:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Save MaterialSet", "Error: {}".format(target_error))
			dialog.exec_()
		else:
			saved_material_paths = self.get_material_treewidget_checked_paths()
			
			def write_matlist_file(matlist_path, material_paths):
				with open(matlist_path, 'wt') as f:
					for material in material_paths:
						f.write("{}\n".format(material))
						
			if os.path.exists(target_path):
				dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Save MaterialSet", "Confirm overwrite? {}".format(target_path))
				dialog.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
				dialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
				response = dialog.exec_()
				if response == QtWidgets.QMessageBox.Ok:
					write_matlist_file(target_path, saved_material_paths)
					reload_materialsets_styles_dict(self.pmt_engine)
			else:
				write_matlist_file(target_path, saved_material_paths)
				reload_materialsets_styles_dict(self.pmt_engine)
					
				
	def OnLoadButton(self):
		style = self.matsets_style_line.text().lower()
		category = self.matsets_category_line.text().lower()
		
		(target_path, target_error) = get_category_fs_path(self.pmt_engine, style, category)
		if target_error != None:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Load MaterialSet", "Error: {}".format(target_error))
			dialog.exec_()
		else:
			dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Load MaterialSet", "Confirm: this will reset the current material selection.")
			dialog.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
			dialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
			response = dialog.exec_()
			if response == QtWidgets.QMessageBox.Ok:
				styles_dict = get_materialsets_styles_dict(self.pmt_engine)
				material_list = styles_dict[style][category]
				self.set_material_treewidget_checked_paths(material_list)
		
	#def OnCloseButton(self):
	#	self.close()

#Python Panel init for when this is used as a python module in pmt::pmt__global_config
# def onCreateInterface():
    # pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
    # window = pmt__global_config.pmt_qt_materialsets_editor.MaterialSetsEditorWindow("vmf")
    # return window	
	
# def onCreateInterface():
    # pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
    # window = pmt__global_config.pmt_qt_materialsets_editor.MaterialSetsEditorWindow("map")
    # return window
	
# def onCreateInterface():
    # pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
    # window = pmt__global_config.pmt_qt_materialsets_editor.MaterialSetsEditorWindow("t3d")
    # return window
	
#Python panel init for when this is used as a python panel, for testing
IS_PYTHON_PANEL = False
if IS_PYTHON_PANEL:
	def onCreateInterface():
		window = MaterialSetsEditorWindow("vmf")
		return window	