#!/usr/bin/env python3
#	node               : 	pmt::pmt__globalconfig
#	houdini_module_name: 	pmt_qt_material_selector
#	script_section_name: 	pmt_qt_material_selector.py
#
# A material browser.

#Houdini 18.5 docs state that PySide2/Qt must be run on Houdini's main thread.
#This means that any subclasses of PySide2/Qt classes must be implemented 
#as a python panel or as a tool on the tool shelf.
#
#Directly instantiating a MaterialSelectorWindow will cause it to close immediately, 
#so we use a different approach with python panels.
#
##First, create a .pypanel file that will create the window:
#def onCreateInterface():
#    pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
#    window = pmt__global_config.pmt_qt_material_selector.MaterialSelectorWindow("vmf")
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
import string
import math
from PySide2 import QtCore, QtWidgets, QtGui

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
	PMT_REFLEVEL = 2
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

FONT_BOLD_ITALIC_STRIKEOUT = QtGui.QFont()
FONT_BOLD_ITALIC_STRIKEOUT.setBold(True)
FONT_BOLD_ITALIC_STRIKEOUT.setItalic(True)
FONT_BOLD_ITALIC_STRIKEOUT.setStrikeOut(True)

FONT_DEFAULT_STRIKEOUT = QtGui.QFont()
FONT_DEFAULT_STRIKEOUT.setBold(False)
FONT_DEFAULT_STRIKEOUT.setItalic(False)
FONT_DEFAULT_STRIKEOUT.setStrikeOut(True)

LISTWIDGET_ICON_SIZE = QtCore.QSize(128,128)
IMAGEVIEW_SIZE = QtCore.QSize(512,512)

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
	elif pmt_engine == "t3d":
		return '.'
	elif pmt_engine == "map":
		return '/'
		
	assert False, "MaterialsetsSelector get_path_sep() invalid pmt_engine {}".format(pmt_engine)
	return None

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
				#item.setCheckState(0, QtCore.Qt.Unchecked)
				#item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsAutoTristate)
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
	
class MaterialSelectorWindow(QtWidgets.QWidget):
	TARGET_NODE_TYPE = "pmt::sop/pmt_material_assign"

	def __init__(self, pane_tab, pmt_engine):
		super().__init__()
		
		self.setWindowTitle("Material Selector(engine={})".format(pmt_engine))
		
		self.pmt_engine = pmt_engine
		self.current_node = None
		self.current_listwidget_folder = None
		self.search_result_materials = list()
		self.search_result_folders = list()
			
		node_layout = QtWidgets.QVBoxLayout()
		if True:
			LARGE_SPACING = 4096 #Spacing to compact items in a QHBoxLayout
			node_pathbar_layout = QtWidgets.QHBoxLayout()
			self.node_path_label = QtWidgets.QLabel("Node path:")
			#self.node_path_label.setMaximumWidth(80)
			self.node_path_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
			self.node_path = hou.qt.InputField(hou.qt.InputField.StringType, 1, "")
			self.node_path.setMinimumWidth(512)
			self.node_path.setEnabled(False)
			self.node_chooser = hou.qt.NodeChooserButton()
			self.node_chooser.setNodeChooserFilter(hou.nodeTypeFilter.Sop)
			self.node_chooser.nodeSelected.connect(self.OnNodeChooserNodeSelected)
			node_pathbar_layout.addWidget(self.node_path_label)
			node_pathbar_layout.addWidget(self.node_chooser)
			node_pathbar_layout.addWidget(self.node_path)
			#node_pathbar_layout.addSpacing(LARGE_SPACING)
			node_pathbar_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
				
			self.node_type = QtWidgets.QLabel("Node type:")
			
			node_layout.addLayout(node_pathbar_layout)
			node_layout.addWidget(self.node_type)
			
		main_layout = QtWidgets.QHBoxLayout()
		if True:
			if True:
				material_tree_layout = QtWidgets.QVBoxLayout()
				self.material_treewidget = QtWidgets.QTreeWidget()
				self.material_treewidget.setHeaderLabels(["materials(engine={})".format(self.pmt_engine)])
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
			
				material_tree_layout.addWidget(self.material_treewidget)
				
				main_layout.addLayout(material_tree_layout)
				
			#Mid row listwidget used to display items in the current folder
			list_layout = QtWidgets.QHBoxLayout()
			if True:
				self.listwidget = QtWidgets.QListWidget()
				self.listwidget.setViewMode(QtWidgets.QListView.IconMode)
				self.listwidget.setResizeMode(QtWidgets.QListView.Adjust)
				self.listwidget.setMovement(QtWidgets.QListView.Static)
				
				self.listwidget.setIconSize(LISTWIDGET_ICON_SIZE)
				self.listwidget.itemClicked.connect(self.OnListItemClicked)
				list_layout.addWidget(self.listwidget)
				main_layout.addLayout(list_layout)
			
			if True: #create the 'main' image display
				image_display_layout = QtWidgets.QVBoxLayout()
				self.image_display_label = QtWidgets.QLabel("[material]")
				self.image_display_label.setAlignment(QtCore.Qt.AlignCenter)
				self.image_display_label.setMaximumSize(IMAGEVIEW_SIZE)
				self.image_display_label.setMinimumSize(IMAGEVIEW_SIZE)
				image_display_layout.addWidget(self.image_display_label)
				
				add_material_button = QtWidgets.QPushButton("Add Material to Node")
				add_material_button.clicked.connect(self.OnAddMaterialButton)
				image_display_layout.addWidget(add_material_button)
				
				main_layout.addLayout(image_display_layout)
		
		self.material_path_label = QtWidgets.QLabel("[path]")
		self.material_path_label.setAlignment(QtCore.Qt.AlignLeft)
		
		#Bottom row buttons
		search_layout1 = QtWidgets.QHBoxLayout()
		if True:
			self.search_checkbox = QtWidgets.QCheckBox("Filter Search Results")
			search_button = QtWidgets.QPushButton("Run Search")
			self.search_editbox = QtWidgets.QLineEdit("")
			self.search_checkbox.stateChanged.connect(self.OnSearchCheckbox_stateChanged)
			search_button.clicked.connect(self.OnSearchButton)
		
			search_layout1.addWidget(self.search_checkbox)
			search_layout1.addWidget(search_button)
			search_layout1.addWidget(self.search_editbox)
			
		search_layout2 = QtWidgets.QHBoxLayout()
		if True:
			self.search_result_label = QtWidgets.QLabel("[search_result]")
			search_layout2.addWidget(self.search_result_label)
		
		#Main layout
		self.layout = QtWidgets.QVBoxLayout()
		self.layout.addLayout(node_layout)
		self.layout.addLayout(main_layout)
		self.layout.addLayout(search_layout1)
		self.layout.addLayout(search_layout2)
		self.layout.addWidget(self.material_path_label)
		self.setLayout(self.layout)
		
		#
		self.resize(1024, 768)
		#self.show()
		self.showMaximized()
	
	def material_OnTreeItemClicked(self, qtreewidgetitem, column):	   
		treeitem = qtreewidgetitem
		
		#update the main image display
		material_path = treeitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
		self.material_path_label.setText(material_path)
			
		DPRINT("material_OnTreeItemClicked: column {} path {}".format(column, material_path))
		is_leaf_node = treeitem.childCount() == 0
		if is_leaf_node:
			diffuse_fs = get_diffuse_fs(self.pmt_engine, material_path)
			pixmap = QtGui.QPixmap(diffuse_fs)
			if not pixmap.isNull():
				pixmap = pixmap.scaled(IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
				self.image_display_label.setPixmap(pixmap)
			else:
				self.image_display_label.setPixmap(None)
				self.image_display_label.setText("[no_fs_image]")
			
			listwidget_treeitem = qtreewidgetitem.parent()
		else:
			self.image_display_label.setPixmap(None)
			self.image_display_label.setText("[material]")
			listwidget_treeitem = qtreewidgetitem
				
		check_state = self.search_checkbox.checkState()
		if check_state == QtCore.Qt.Checked:
			#if in 'display search results' mode, the listwidget will show all results
			#instead of what is the current folder
			self.current_listwidget_folder = None
		else:			
			#if qtreewidgetitem is a leaf, updates listwidget with the items in the same folder,
			#otherwise, update listwidget in the folder at qtreewidgetitem
			def update_listwidget_search_unchecked(listwidget, material_to_listitem_dict, qtreewidgetitem):
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
				if USE_THREAD:
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
				update_listwidget_search_unchecked(self.listwidget, self.qlistitem_dict, listwidget_treeitem)
			self.current_listwidget_folder = selected_folder_path
			
		self.listwidget.setCurrentItem(self.qlistitem_dict[material_path])
		
	def OnListItemClicked(self, qlistwidgetitem):
		#When we click an item in the list, find the corresponding tree item(material) and set it as the selection
		listitem = qlistwidgetitem
		material_path = listitem.data(QtCore.Qt.UserRole)
		treeitem = self.qtreeitem_dict[material_path]
		
		#self.material_OnTreeItemClicked(treeitem, COLUMN_MATERIAL_NAME)
		self.material_treewidget.setCurrentItem(treeitem, COLUMN_MATERIAL_NAME)
		
		self.material_path_label.setText(material_path)
		
		#Also, update the main image view to show the material we clicked on
		diffuse_fs = get_diffuse_fs(self.pmt_engine, material_path)
		pixmap = QtGui.QPixmap(diffuse_fs)
		pixmap = pixmap.scaled(IMAGEVIEW_SIZE, QtCore.Qt.KeepAspectRatio)
		self.image_display_label.setPixmap(pixmap)
		
	def OnAddMaterialButton(self):
		if self.current_node == None:
			return
		
		nodetype = self.current_node.type().nameWithCategory()
		if nodetype.lower() != self.TARGET_NODE_TYPE:
			errortext = "Node type must be '{}' to add material. Selected node type is '{}'.".format(self.TARGET_NODE_TYPE, nodetype)
			message = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "pmt_material_selector", errortext, QtWidgets.QMessageBox.Ok, self)
			message.show()
			return
			
		current_treeitem = self.material_treewidget.currentItem()
		material_path = current_treeitem.text(COLUMN_MATERIAL_PATH_HIDDEN)
		is_leaf_node = current_treeitem.childCount() == 0
		if not is_leaf_node:
			return
			
		material_props = self.current_node.parm("{}_materials".format(self.pmt_engine))
		num_props = material_props.evalAsInt()
		material_props.insertMultiParmInstance(num_props)

		prop_index = num_props + 1	#index 0 is numbered as key_1, index 1 as key_2 and so on
		parm_name = "{}_matpath_{}".format(self.pmt_engine, prop_index)
		mat_prop = self.current_node.parm(parm_name)
		assert mat_prop != None, "mat_prop is None: {}".format(parm_name)
		mat_prop.set(material_path)
		
	def OnSearchButton(self):
		query = self.search_editbox.text().lower()
		
		materials_list = list()
		for path in self.qtreeitem_dict:
			treeitem = self.qtreeitem_dict[path]
			is_leaf_node = treeitem.childCount() == 0
			if is_leaf_node:
				materials_list.append(path)
		
		results, report_string = pmt_material_search.perform_material_search(self.pmt_engine, materials_list, query)
		
		if results != None:
			self.search_result_materials = results
			path_sep = get_path_sep(self.pmt_engine)
			
			folders = set()
			for path in self.search_result_materials:
				index = path.rfind(path_sep)
				while index != -1:
					path = path[:index]
					folders.add(path)
					index = path.rfind(path_sep)
			
			self.search_result_folders.clear()
			for folder in folders:
				self.search_result_folders.append(folder)
			#self.search_result_folders.sort()
			#for folder in folders:
			#	print("folder: "+ folder)
		
		self.search_result_label.setText(report_string)
		self.OnSearchCheckbox_stateChanged(self.search_checkbox.checkState())
		
	def OnSearchCheckbox_stateChanged(self, check_state):
		#check_state = self.search_checkbox.checkState()
		if check_state == QtCore.Qt.Checked:
		
			HIDE_NONMATCHING_MATERIAL = True
		
			for path in self.qtreeitem_dict:
				treeitem = self.qtreeitem_dict[path]
				if HIDE_NONMATCHING_MATERIAL:
					treeitem.setHidden(True)
				is_leaf_node = treeitem.childCount() == 0
				if is_leaf_node:
					treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_DEFAULT_STRIKEOUT)
				else:
					treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_BOLD_ITALIC_STRIKEOUT)
				
			for path in self.search_result_materials:
				treeitem = self.qtreeitem_dict[path]
				treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_DEFAULT)
				if HIDE_NONMATCHING_MATERIAL:
					treeitem.setHidden(False)
				
			for folder_path in self.search_result_folders:	
				treeitem = self.qtreeitem_dict[folder_path]
				treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_BOLD_ITALIC)
				if HIDE_NONMATCHING_MATERIAL:
					treeitem.setHidden(False)
				
			#Remove all items from the QListWidget
			for listitem in self.listwidget.findItems("*", QtCore.Qt.MatchWildcard):
				row = self.listwidget.row(listitem)
				self.listwidget.takeItem(row)
				
			#Add all search results to QListWidget
			USE_THREAD = True
			if USE_THREAD:
				#Update listitems in listwidget - use placeholder images/pixmap
				material_to_listitem_dict = self.qlistitem_dict
				for material_path in self.search_result_materials:
					listitem = material_to_listitem_dict[material_path]
					
					empty_pixmap = QtGui.QPixmap(LISTWIDGET_ICON_SIZE)
					empty_pixmap.fill(QtGui.QColor(0,0,0,0))
					loading_icon = QtGui.QIcon(empty_pixmap)
					listitem.setIcon(loading_icon)	
					self.listwidget.addItem(listitem)
				
				#Image loading is run in a separate thread to prevent the main thread from stalling
				def listwidget_load_images(listwidget, material_paths, material_to_listitem_dict, get_diffuse_fs_func, pmt_engine):
					for material_path in material_paths:
						listitem = material_to_listitem_dict[material_path]
						diffuse_fs = get_diffuse_fs_func(pmt_engine, material_path)
						DPRINT("OnTreeItemClicked() load diffusefs {}".format(diffuse_fs))
						pixmap = QtGui.QPixmap(diffuse_fs)
						icon = QtGui.QIcon(pixmap)
						listitem.setIcon(icon)
						listwidget.updateGeometry()
				listwidget_load_images_args = (self.listwidget, self.search_result_materials, material_to_listitem_dict, get_diffuse_fs, self.pmt_engine)
				image_thread = threading.Thread(target=listwidget_load_images, args = listwidget_load_images_args)
				image_thread.start()
		else:
			for path in self.qtreeitem_dict:
				treeitem = self.qtreeitem_dict[path]
				treeitem.setHidden(False)
				is_leaf_node = treeitem.childCount() == 0
				if is_leaf_node:
					treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_DEFAULT)
				else:
					treeitem.setFont(COLUMN_MATERIAL_NAME, FONT_BOLD_ITALIC)
		
			for material_path in self.qlistitem_dict:
				listitem = self.qlistitem_dict[material_path]
				listitem.setFont(FONT_DEFAULT)
		

	#signal is hou.qt.NodeChooserButton.nodeSelected(str)
	#note that 'str' is a Houdini node and not a string
	def OnNodeChooserNodeSelected(self, node):
		self.OnNodePathChanged(node)
	def OnNodePathChanged(self, node):
		if node == None: return
		self.current_node = node
		
		path = node.path()
		nodetype = self.current_node.type().nameWithCategory()
		
		self.node_path.setValue(path)
		
		if nodetype.lower() == self.TARGET_NODE_TYPE:
			self.node_type.setText("Node type: {}".format(nodetype))
		else:
			self.node_type.setText("Node type: {} (type must be '{}') to add material.".format(nodetype, self.TARGET_NODE_TYPE))
		
#Python Panel init for when this is used as a python module in pmt::pmt__global_config
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_material_selector.MaterialSelectorWindow(pane_tab, "vmf")
	# return window   
# def onNodePathChanged(node):
	# if window != None: window.OnNodePathChanged(node)
	
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_material_selector.MaterialSelectorWindow(pane_tab, "t3d")
	# return window   
# def onNodePathChanged(node):
	# if window != None: window.OnNodePathChanged(node)
	
# window = None
# def onCreateInterface():
	# pane_tab = kwargs["paneTab"]
	# pmt__global_config = hou.nodeType(hou.sopNodeTypeCategory(), "pmt::pmt__global_config").hdaModule()
	# global window
	# window = pmt__global_config.pmt_qt_material_selector.MaterialSelectorWindow(pane_tab, "map")
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
		window = MaterialSelectorWindow(pane_tab, "vmf")
		#window = MaterialSelectorWindow(pane_tab, "t3d")
		#window = MaterialSelectorWindow(pane_tab, "map")
		return window
	def onNodePathChanged(node):
		window.OnNodePathChanged(node)


