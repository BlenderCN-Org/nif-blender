"""This script imports Netimmerse/Gamebryo nif files to Blender."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2005-2015, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#	* Redistributions of source code must retain the above copyright
#	  notice, this list of conditions and the following disclaimer.
#
#	* Redistributions in binary form must reproduce the above
#	  copyright notice, this list of conditions and the following
#	  disclaimer in the documentation and/or other materials provided
#	  with the distribution.
#
#	* Neither the name of the NIF File Format Library and Tools
#	  project nor the names of its contributors may be used to endorse
#	  or promote products derived from this software without specific
#	  prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****

from .nif_common import NifCommon
from .utility import nif_utils

from .animationsys.animation_import import AnimationHelper
from .armaturesys.armature_import import Armature
from .collisionsys.collision_import import bhkshape_import, bound_import
from .constraintsys.constraint_import import constraint_import
from .materialsys.material_import import Material
from .texturesys.texture_import import Texture
from .texturesys.texture_loader import TextureLoader

import bpy
import mathutils

import pyffi.spells.nif.fix
from pyffi.formats.nif import NifFormat
from pyffi.formats.egm import EgmFormat

def mesh_from_data(name, verts, faces, wireframe = True):
	me = bpy.data.meshes.new(name)
	me.from_pydata(verts, [], faces)
	me.update()
	ob = bpy.data.objects.new(name, me)
	bpy.context.scene.objects.link(ob)
	if wireframe:
		ob.draw_type = 'WIRE'
	return ob, me

def create_sphere(name, x, y, z, r):
	verts = [(0.50,0.00,0.87),(0.87,0.00,0.50),(1.00,0.00,-0.00),(0.87,0.00,-0.50),(0.50,0.00,-0.87),(0.35,0.35,-0.87),(0.61,0.61,-0.50),(0.71,0.71,0.00),(0.61,0.61,0.50),(0.35,0.35,0.87),(0.00,0.00,1.00),(-0.00,0.50,0.87),(-0.00,0.87,0.50),(-0.00,1.00,0.00),(-0.00,0.87,-0.50),(-0.00,0.50,-0.87),(-0.35,0.35,-0.87),(-0.61,0.61,-0.50),(-0.71,0.71,0.00),(-0.61,0.61,0.50),(-0.35,0.35,0.87),(-0.50,-0.00,0.87),(-0.87,-0.00,0.50),(-1.00,-0.00,0.00),(-0.87,-0.00,-0.50),(-0.50,-0.00,-0.87),(-0.00,-0.00,-1.00),(-0.35,-0.35,-0.87),(-0.61,-0.61,-0.50),(-0.71,-0.71,0.00),(-0.61,-0.61,0.50),(-0.35,-0.35,0.87),(0.00,-0.50,0.87),(0.00,-0.87,0.50),(0.00,-1.00,0.00),(0.00,-0.87,-0.50),(0.00,-0.50,-0.87),(0.35,-0.35,-0.87),(0.61,-0.61,-0.50),(0.71,-0.71,0.00),(0.61,-0.61,0.50),(0.35,-0.35,0.87)]
	faces = [(26,5,4),(4,5,6,3),(3,6,7,2),(2,7,8,1),(9,0,1,8),(0,9,10),(9,11,10),(8,12,11,9),(7,13,12,8),(6,14,13,7),(5,15,14,6),(26,15,5),(26,16,15),(15,16,17,14),(14,17,18,13),(13,18,19,12),(12,19,20,11),(11,20,10),(20,21,10),(19,22,21,20),(18,23,22,19),(17,24,23,18),(16,25,24,17),(26,25,16),(26,27,25),(25,27,28,24),(24,28,29,23),(23,29,30,22),(22,30,31,21),(21,31,10),(31,32,10),(30,33,32,31),(29,34,33,30),(28,35,34,29),(27,36,35,28),(26,36,27),(26,37,36),(36,37,38,35),(35,38,39,34),(34,39,40,33),(33,40,41,32),(32,41,10),(41,0,10),(0,41,40,1),(39,2,1,40),(38,3,2,39),(37,4,3,38),(26,4,37)]
	ob, me = mesh_from_data(name,verts,faces)
	for v in me.vertices:
		v.co = v.co*r
	ob.location = (x,y,z)
	return ob	

def create_bounding_box(name, matrix, x, y, z):
	verts = [(x/2,y/2,-z/2),(x/2,-y/2,-z/2),(-x/2,-y/2,-z/2),(-x/2,y/2,-z/2),(x/2,y/2,z/2),(x/2,-y/2,z/2),(-x/2,-y/2,z/2),(-x/2,y/2,z/2)]
	faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
	ob, me = mesh_from_data(name,verts,faces)
	ob.matrix_local = matrix
	return ob
	
def create_capsule(name, start, end, r):
	#print(start,end,r)
	l = end.length
	#this primitive stands up and has radius of 0.5, height 1, the caps extend outward
	verts = [(1.00*r,0.00*r,-0.00*r),(0.87*r,0.00*r,-0.50*r),(0.50*r,0.00*r,-0.87*r),(0.35*r,0.35*r,-0.87*r),(0.61*r,0.61*r,-0.50*r),(0.71*r,0.71*r,0.00*r),(-0.00*r,1.00*r,0.00*r),(-0.00*r,0.87*r,-0.50*r),(-0.00*r,0.50*r,-0.87*r),(-0.35*r,0.35*r,-0.87*r),(-0.61*r,0.61*r,-0.50*r),(-0.71*r,0.71*r,0.00*r),(-1.00*r,-0.00*r,0.00*r),(-0.87*r,-0.00*r,-0.50*r),(-0.50*r,-0.00*r,-0.87*r),(-0.00*r,-0.00*r,-1.00*r),(-0.35*r,-0.35*r,-0.87*r),(-0.61*r,-0.61*r,-0.50*r),(-0.71*r,-0.71*r,0.00*r),(0.00*r,-1.00*r,0.00*r),(0.00*r,-0.87*r,-0.50*r),(0.00*r,-0.50*r,-0.87*r),(0.35*r,-0.35*r,-0.87*r),(0.61*r,-0.61*r,-0.50*r),(0.71*r,-0.71*r,0.00*r),(0.71*r,-0.71*r,0.00*r+l),(0.61*r,-0.61*r,0.50*r+l),(0.35*r,-0.35*r,0.87*r+l),(0.00*r,-0.50*r,0.87*r+l),(0.00*r,-0.87*r,0.50*r+l),(0.00*r,-1.00*r,0.00*r+l),(-0.71*r,-0.71*r,0.00*r+l),(-0.61*r,-0.61*r,0.50*r+l),(-0.35*r,-0.35*r,0.87*r+l),(-0.00*r,-0.00*r,1.00*r+l),(-0.50*r,-0.00*r,0.87*r+l),(-0.87*r,-0.00*r,0.50*r+l),(-1.00*r,-0.00*r,0.00*r+l),(-0.71*r,0.71*r,0.00*r+l),(-0.61*r,0.61*r,0.50*r+l),(-0.35*r,0.35*r,0.87*r+l),(-0.00*r,0.50*r,0.87*r+l),(-0.00*r,0.87*r,0.50*r+l),(-0.00*r,1.00*r,0.00*r+l),(0.71*r,0.71*r,0.00*r+l),(0.61*r,0.61*r,0.50*r+l),(0.35*r,0.35*r,0.87*r+l),(0.50*r,0.00*r,0.87*r+l),(0.87*r,0.00*r,0.50*r+l),(1.00*r,0.00*r,0.00*r+l)]
	faces = [(15,3,2),(2,3,4,1),(5,0,1,4),(4,7,6,5),(3,8,7,4),(15,8,3),(15,9,8),(8,9,10,7),(7,10,11,6),(10,13,12,11),(9,14,13,10),(15,14,9),(15,16,14),(14,16,17,13),(13,17,18,12),(17,20,19,18),(16,21,20,17),(15,21,16),(15,22,21),(21,22,23,20),(20,23,24,19),(0,24,23,1),(22,2,1,23),(15,2,22),(34,47,27),(27,47,48,26),(49,25,26,48),(29,26,25,30),(28,27,26,29),(34,27,28),(34,28,33),(33,28,29,32),(32,29,30,31),(36,32,31,37),(35,33,32,36),(34,33,35),(34,35,40),(40,35,36,39),(39,36,37,38),(42,39,38,43),(41,40,39,42),(34,40,41),(34,41,46),(46,41,42,45),(45,42,43,44),(44,49,48,45),(47,46,45,48),(34,46,47),(18,19,30,31),(19,24,25,30),(0,49,25,24),(0,5,44,49),(5,6,43,44),(6,11,38,43),(11,12,37,38),(12,18,31,37)]
	ob, me = mesh_from_data(name,verts,faces)
	#we want a rotation that, when multiplied with the up vector, equals the end vector
	rot = end.to_track_quat("Z", "Y" )
	#this shows our rotation is correct	#up = mathutils.Vector((0,0,1))	#result = rot*up*l	#print(result)	#print(end)	#these are all working = identical
	for v in me.vertices:
		v.co = rot*v.co+start
	ob.rotation_euler.z = 1.5708
	return ob
def select_layer(layer_nr): return tuple(i == layer_nr for i in range(0, 20))
	
class NifImport(NifCommon):

	# degrees to radians conversion constant
	D2R = 3.14159265358979 / 180.0
	IMPORT_EXTRANODES = True
	IMPORT_EXPORTEMBEDDEDTEXTURES = False

	def __init__(self, operator, context):
		NifCommon.__init__(self, operator, context)
		self.root_ninode = 'NiNode'

		# Helper systems
		self.animationhelper = AnimationHelper(parent=self)
		self.armaturehelper = Armature(parent=self)
		# TODO: create super collisionhelper
		self.bhkhelper = bhkshape_import(parent=self)
		self.boundhelper = bound_import(parent=self)
		self.constrainthelper = constraint_import(parent=self)
		self.textureloader = TextureLoader(parent=self)
		self.texturehelper = Texture(parent=self)
		self.texturehelper.set_texture_loader(self.textureloader)
		self.materialhelper = Material(parent=self)
		self.materialhelper.set_texture_helper(self.texturehelper)

	def execute(self):
		"""Main import function."""

		self.dict_armatures = {}
		self.dict_bone_priorities = {}
		self.dict_havok_objects = {}
		self.dict_names = {}
		self.dict_blocks = {}
		self.dict_block_names = []
		self.dict_materials = {}
		self.dict_textures = {}
		self.dict_mesh_uvlayers = []

		# catch nif import errors
		try:
			# check that one armature is selected in 'import geometry + parent
			# to armature' mode
			if self.properties.skeleton == "GEOMETRY_ONLY":
				if(len(self.selected_objects) != 1 or
				   self.selected_objects[0].type != 'ARMATURE'
				   ):
					raise nif_utils.NifError("You must select exactly one armature in 'Import Geometry Only + Parent To Selected Armature' mode.")

			# open file for binary reading
			self.info("Importing %s"
					  % self.properties.filepath
					  )
			niffile = open(self.properties.filepath, "rb")
			self.data = NifFormat.Data()
			try:
				# check if nif file is valid
				self.data.inspect(niffile)
				if self.data.version >= 0:
					# it is valid, so read the file
					self.info("NIF file version: 0x%08X"
							  % self.data.version
							  )
					self.info("Reading file")
					self.data.read(niffile)
				elif self.data.version == -1:
					raise nif_utils.NifError("Unsupported NIF version.")
				else:
					raise nif_utils.NifError("Not a NIF file.")
			finally:
				# the file has been read or an error occurred: close file
				niffile.close()

			if self.properties.keyframe_file:
				# open keyframe file for binary reading
				self.info("Importing %s"
						  % self.properties.keyframe_file
						  )
				kffile = open(self.properties.keyframe_file, "rb")
				self.kfdata = NifFormat.Data()
				try:
					# check if kf file is valid
					self.kfdata.inspect(kffile)
					if self.kfdata.version >= 0:
						# it is valid, so read the file
						self.info("KF file version: 0x%08X"
								  % self.kfdata.version
								  )
						self.info("Reading keyframe file")
						self.kfdata.read(kffile)
					elif self.kfdata.version == -1:
						raise nif_utils.NifError("Unsupported KF version.")
					else:
						raise nif_utils.NifError("Not a KF file.")
				finally:
					# the file has been read or an error occurred: close file
					kffile.close()
			else:
				self.kfdata = None

			if self.properties.egm_file:
				# open facegen egm file for binary reading
				self.info("Importing %s"
						  % self.properties.egm_file
						  )
				egmfile = open(self.properties.egm_file, "rb")
				self.egmdata = EgmFormat.Data()
				try:
					# check if kf file is valid
					self.egmdata.inspect(egmfile)
					if self.egmdata.version >= 0:
						# it is valid, so read the file
						self.info("EGM file version: %03i"
								  % self.egmdata.version
								  )
						self.info("Reading FaceGen egm file")
						self.egmdata.read(egmfile)
						# scale the data
						self.egmdata.apply_scale(self.properties.scale_correction_import)
					elif self.egmdata.version == -1:
						raise nif_utils.NifError("Unsupported EGM version.")
					else:
						raise nif_utils.NifError("Not an EGM file.")
				finally:
					# the file has been read or an error occurred: close file
					egmfile.close()
			else:
				self.egmdata = None

			self.info("Importing data")
			# calculate and set frames per second
			if self.properties.animation:
				self.fps = self.animationhelper.get_frames_per_second(self.data.roots +
																	  (self.kfdata.roots if self.kfdata else [])
																	  )
				self.context.scene.render.fps = self.fps

			# merge skeleton roots and transform geometry into the rest pose
			if self.properties.merge_skeleton_roots:
				pyffi.spells.nif.fix.SpellMergeSkeletonRoots(data=self.data).recurse()
			if self.properties.send_geoms_to_bind_pos:
				pyffi.spells.nif.fix.SpellSendGeometriesToBindPosition(data=self.data).recurse()
			if self.properties.send_detached_geoms_to_node_pos:
				pyffi.spells.nif.fix.SpellSendDetachedGeometriesToNodePosition(data=self.data).recurse()
			if self.properties.send_bones_to_bind_position:
				pyffi.spells.nif.fix.SpellSendBonesToBindPosition(data=self.data).recurse()
			if self.properties.apply_skin_deformation:
				for n_geom in self.data.get_global_iterator():
					if not isinstance(n_geom, NifFormat.NiGeometry):
						continue
					if not n_geom.is_skin():
						continue
					self.info('Applying skin deformation on geometry %s'
							  % n_geom.name
							  )
					vertices, normals = n_geom.get_skin_deformation()
					for vold, vnew in zip(n_geom.data.vertices, vertices):
						vold.x = vnew.x
						vold.y = vnew.y
						vold.z = vnew.z

			# scale tree
			toaster = pyffi.spells.nif.NifToaster()
			toaster.scale = self.properties.scale_correction_import
			pyffi.spells.nif.fix.SpellScale(data=self.data, toaster=toaster).recurse()

			# import all root blocks
			for block in self.data.roots:
				root = block
				# root hack for corrupt better bodies meshes
				# and remove geometry from better bodies on skeleton import
				for b in (b for b in block.tree() if
						  isinstance(b, NifFormat.NiGeometry) and
						  b.is_skin()
						  ):
					# check if root belongs to the children list of the
					# skeleton root (can only happen for better bodies meshes)
					if root in [c for c in b.skin_instance.skeleton_root.children]:
						# fix parenting and update transform accordingly
						b.skin_instance.data.set_transform(root.get_transform() *
														   b.skin_instance.data.get_transform()
														   )
						b.skin_instance.skeleton_root = root
						# delete non-skeleton nodes if we're importing
						# skeleton only
						if self.properties.skeleton == "SKELETON_ONLY":
							nonbip_children = (child for child in root.children
											   if child.name[:6] != 'Bip01 ')
							for child in nonbip_children:
								root.remove_child(child)
				# import this root block
				self.debug("Root block: %s"
						   % root.get_global_display()
						   )
				# merge animation from kf tree into nif tree
				if self.properties.animation and self.kfdata:
					for kf_root in self.kfdata.roots:
						self.animationhelper.import_kf_root(kf_root, root)
				# import the nif tree
				self.import_root(root)
		finally:
			# clear progress bar
			self.info("Finished")
			# XXX no longer needed?
			# do a full scene update to ensure that transformations are applied
			# self.context.scene.update()

		return {'FINISHED'}

	def import_bsxflag_data(self, root_block):
		for n_extra in root_block.get_extra_datas():
			if isinstance(n_extra, NifFormat.BSXFlags):
					# get bsx flags so we can attach it to collision object
					bsxflags = n_extra.integer_data
					return bsxflags

	def import_upbflag_data(self, root_block):
			# process extra data
			for n_extra in root_block.get_extra_datas():
				if isinstance(n_extra, NifFormat.NiStringExtraData):
					if n_extra.name.decode() == "UPB":
						upbflags = n_extra.string_data.decode()
						return upbflags

	def import_bsbound_data(self, root_block):
		for n_extra in root_block.get_extra_datas():
			if isinstance(n_extra, NifFormat.BSBound):
					self.boundhelper.import_bounding_box(n_extra)

	def import_version_set(self, b_obj):
		b_obj.niftools.nif_version = self.hex_to_dec(self.data._version_value_._value)
		b_obj.niftools.user_version = self.data._user_version_value_._value
		b_obj.niftools.user_version_2 = self.data._user_version_2_value_._value

	def import_root(self, root_block):
		"""Main import function."""
		# check that this is not a kf file
		if isinstance(root_block,
					  (NifFormat.NiSequence,
					   NifFormat.NiSequenceStreamHelper)):
			raise nif_utils.NifError("direct .kf import not supported")

		# divinity 2: handle CStreamableAssetData
		if isinstance(root_block, NifFormat.CStreamableAssetData):
			root_block = root_block.root

		# sets the root block parent to None, so that when crawling back the
		# script won't barf
		root_block._parent = None

		# set the block parent through the tree, to ensure I can always move
		# backward
		self.set_parents(root_block)
		self.bsxflags = self.import_bsxflag_data(root_block)
		self.upbflags = self.import_upbflag_data(root_block)
		self.objectflags = root_block.flags
		self.Nif_Version = self.hex_to_dec(self.data._version_value_._value)
		self.Nif_User_Version = self.data._user_version_value_._value
		self.Nif_User_Version_2 = self.data._user_version_2_value_._value

		if isinstance(root_block, NifFormat.BSFadeNode):
			self.root_ninode = 'BSFadeNode'

		# mark armature nodes and bones
		self.armaturehelper.mark_armatures_bones(root_block)

		# import the keyframe notes
		if self.properties.animation:
			self.animationhelper.import_text_keys(root_block)

		# read the NIF tree
		if self.armaturehelper.is_armature_root(root_block):
			# special case 1: root node is skeleton root
			self.debug("%s is an armature root"
					   % root_block.name
					   )
			b_obj = self.import_branch(root_block)
			b_obj.niftools.objectflags = root_block.flags
			self.import_version_set(b_obj)

		elif self.is_grouping_node(root_block):
			# special case 2: root node is grouping node
			self.debug("%s is a grouping node"
					   % root_block.name
					   )
			b_obj = self.import_branch(root_block)
			b_obj.niftools.bsxflags = self.bsxflags

		elif isinstance(root_block, NifFormat.NiTriBasedGeom):
			# trishape/tristrips root
			b_obj = self.import_branch(root_block)
			b_obj.niftools.bsxflags = self.bsxflags

		elif isinstance(root_block, NifFormat.NiNode):
			# root node is dummy scene node
			for n_extra in root_block.get_extra_datas():
				if isinstance(n_extra, NifFormat.BSBound):
					self.boundhelper.import_bounding_box(n_extra)
			# process collision
			if root_block.collision_object:
				bhk_body = root_block.collision_object.body
				if not isinstance(bhk_body, NifFormat.bhkRigidBody):
					self.warning("Unsupported collision structure under node %s"
								 % root_block.name
								 )
				self.bhkhelper.import_bhk_shape(bhkshape=bhk_body)

			# process all its children
			for child in root_block.children:
				b_obj = self.import_branch(child)

		elif isinstance(root_block, NifFormat.NiCamera):
			self.warning('Skipped NiCamera root')

		elif isinstance(root_block, NifFormat.NiPhysXProp):
			self.warning('Skipped NiPhysXProp root')

		else:
			self.warning("Skipped unsupported root block type '%s' (corrupted nif?)."
						 % root_block.__class__
						 )

		if hasattr(root_block, "extra_data_list"):
			for n_extra_list in root_block.extra_data_list:
				if isinstance(n_extra_list, NifFormat.BSInvMarker):
					b_obj.niftools_bs_invmarker.add()
					b_obj.niftools_bs_invmarker[0].name = n_extra_list.name.decode()
					b_obj.niftools_bs_invmarker[0].bs_inv_x = n_extra_list.rotation_x
					b_obj.niftools_bs_invmarker[0].bs_inv_y = n_extra_list.rotation_y
					b_obj.niftools_bs_invmarker[0].bs_inv_z = n_extra_list.rotation_z
					b_obj.niftools_bs_invmarker[0].bs_inv_zoom = n_extra_list.zoom

		if self.root_ninode:
			b_obj.niftools.rootnode = self.root_ninode

		# store original names for re-export
		if self.dict_names:
			self.armaturehelper.store_names()

		# now all havok objects are imported, so we are
		# ready to import the havok constraints
		self.bhkhelper.get_havok_objects()
		self.constrainthelper.import_bhk_constraints()

		# parent selected meshes to imported skeleton
		if self.properties.skeleton == "SKELETON_ONLY":
			# rename vertex groups to reflect bone names
			# (for blends imported with older versions of the scripts!)
			for b_child_obj in self.selected_objects:
				if b_child_obj.type == 'MESH':
					for oldgroupname in b_child_obj.vertex_groups.items():
						newgroupname = self.get_bone_name_for_blender(oldgroupname)
						if oldgroupname != newgroupname:
							self.info("%s: renaming vertex group %s to %s"
									  % (b_child_obj,
										 oldgroupname,
										 newgroupname
										 )
									  )
							b_child_obj.data.renameVertGroup(
								oldgroupname, newgroupname)
			# set parenting
			# TODO: Change parenting to use python rather than blender operators
			# b_obj.parent_set(self.selected_objects)
			bpy.ops.object.parent_set(type='OBJECT')
			scn = bpy.context.scene
			scn.objects.active = b_obj
			scn.update()

	def import_branch(self, niBlock, b_armature=None, n_armature=None):
		"""Read the content of the current NIF tree branch to Blender
		recursively.

		:param niBlock: The nif block to import.
		:param b_armature: The blender armature for the current branch.
		:param n_armature: The corresponding nif block for the armature for
			the current branch.
		"""
		self.info("Importing data")
		if not niBlock:
			return None
		elif(isinstance(niBlock, NifFormat.NiTriBasedGeom) and
			 self.properties.skeleton != "SKELETON_ONLY"
			 ):
			# it's a shape node and we're not importing skeleton only
			# (self.properties.skeleton ==  "SKELETON_ONLY")
			self.debug("Building mesh in import_branch")
			# note: transform matrix is set during import
			self.active_obj_name = niBlock.name.decode()
			b_obj = self.import_mesh(niBlock)
			b_obj.niftools.objectflags = niBlock.flags
			self.import_version_set(b_obj)

			if niBlock.properties:
				for b_prop in niBlock.properties:
					self.import_shader_types(b_obj, b_prop)
			elif niBlock.bs_properties:
				for b_prop in niBlock.bs_properties:
					self.import_shader_types(b_obj, b_prop)

			if niBlock.data.consistency_flags in NifFormat.ConsistencyType._enumvalues:
				cf_index = NifFormat.ConsistencyType._enumvalues.index(niBlock.data.consistency_flags)
				b_obj.niftools.consistency_flags = NifFormat.ConsistencyType._enumkeys[cf_index]
				b_obj.niftools.tangentsflags = niBlock.data.tangents_flags
			# skinning? add armature modifier
			if niBlock.skin_instance:
				self.armaturehelper.append_armature_modifier(b_obj, b_armature)
			return b_obj
		elif isinstance(niBlock, NifFormat.NiNode):
			children = niBlock.children
			
			# bounding box child?
			bsbound = nif_utils.find_extra(niBlock, NifFormat.BSBound)
			if not(children or
				   niBlock.collision_object or
				   bsbound or
				   niBlock.has_bounding_box or
				   self.IMPORT_EXTRANODES
				   ):
				# do not import unless the node is "interesting"
				return None
			# import object
			if self.armaturehelper.is_armature_root(niBlock):
				# all bones in the tree are also imported by
				# import_armature
				if self.properties.skeleton != "GEOMETRY_ONLY":
					b_obj = self.armaturehelper.import_armature(niBlock)
					b_armature = b_obj
					n_armature = niBlock
				else:
					b_obj = self.selected_objects[0]
					b_armature = b_obj
					n_armature = niBlock
					self.info("Merging nif tree '%s' with armature '%s'"
							  % (niBlock.name, b_obj.name)
							  )
					if niBlock.name != b_obj.name:
						self.warning("Taking nif block '%s' as armature '%s' but names do not match"
									 % (niBlock.name, b_obj.name)
									 )
				# armatures cannot group geometries into a single mesh
				geom_group = []
			elif self.armaturehelper.is_bone(niBlock):
				# bones have already been imported during import_armature
				b_obj = b_armature.data.bones[self.dict_names[niBlock]]
				# bones cannot group geometries into a single mesh
				b_obj.niftools_bone.bsxflags = self.bsxflags
				b_obj.niftools_bone.boneflags = niBlock.flags
				geom_group = []
			else:
				# is it a grouping node?
				geom_group = self.is_grouping_node(niBlock)
				# if importing animation, remove children that have
				# morph controllers from geometry group
				if self.properties.animation:
					for child in geom_group:
						if nif_utils.find_controller(child, NifFormat.NiGeomMorpherController):
							geom_group.remove(child)
				# import geometry/empty
				if(not (geom_group or
						self.properties.combine_shapes
						) or
				   len(geom_group) > 16
				   ):
					# no grouping node, or too many materials to
					# group the geometry into a single mesh
					# so import it as an empty
					if not niBlock.has_bounding_box:
						b_obj = self.import_empty(niBlock)
					else:
						b_obj = self.boundhelper.import_bounding_box(niBlock)
					geom_group = []
				else:
					# node groups geometries, so import it as a mesh
					self.info("Joining geometries %s to single object '%s'"
							  % ([child.name for child in geom_group],
								 niBlock.name)
							  )
					b_obj = None
					for child in geom_group:
						self.active_obj_name = niBlock.name.decode()
						b_obj = self.import_mesh(child,
												 group_mesh=b_obj,
												 applytransform=True
												 )
						b_obj.niftools.objectflags = child.flags
						self.import_version_set(b_obj)

						if child.properties:
							for b_prop in child.properties:
								self.import_shader_types(b_obj, b_prop)

						if child.bs_properties:
							for b_prop in child.bs_properties:
								self.import_shader_types(b_obj, b_prop)

						if child.data.consistency_flags in NifFormat.ConsistencyType._enumvalues:
							cf_index = NifFormat.ConsistencyType._enumvalues.index(child.data.consistency_flags)
							b_obj.niftools.consistency_flags = NifFormat.ConsistencyType._enumkeys[cf_index]

					b_obj.name = self.import_name(niBlock)

					# skinning? add armature modifier
					if any(child.skin_instance
						   for child in geom_group):
						self.armaturehelper.append_armature_modifier(b_obj, b_armature)
					# settings for collision node
					if isinstance(niBlock, NifFormat.RootCollisionNode):
						b_obj.draw_type = 'BOUNDS'
						b_obj.show_wire = True
						b_obj.draw_bounds_type = 'BOX'
						b_obj.game.use_collision_bounds = True
						b_obj.game.collision_bounds_type = 'TRIANGLE_MESH'
						b_obj.niftools.objectflags = niBlock.flags
						# also remove duplicate vertices
						b_mesh = b_obj.data
						b_mesh.validate()
						b_mesh.update()

			# find children that aren't part of the geometry group
			b_children_list = []
			children = [child for child in niBlock.children
						if child not in geom_group]
			for n_child in children:
				b_child = self.import_branch(
					n_child, b_armature=b_armature, n_armature=n_armature)
				if b_child:
					b_children_list.append((n_child, b_child))

			object_children = [
				(n_child, b_child) for (n_child, b_child) in b_children_list
				if isinstance(b_child, bpy.types.Object)]

			# if not importing skeleton only
			if self.properties.skeleton != "SKELETON_ONLY":
				# import collision objects
				if isinstance(niBlock.collision_object, NifFormat.bhkNiCollisionObject):
					bhk_body = niBlock.collision_object.body
					if not isinstance(bhk_body, NifFormat.bhkRigidBody):
						self.warning("Unsupported collision structure under node %s"
									 % niBlock.name
									 )

					collision_objs = self.bhkhelper.import_bhk_shape(bhk_body)
					# register children for parentship
					object_children += [
						(bhk_body, b_child) for b_child in collision_objs]

				# import bounding box
				if bsbound:
					object_children += [
						(bsbound, self.boundhelper.import_bounding_box(bsbound))]

			#collisions for BFB
			try:
				collider = niBlock.collision_object
				if collider:
					#print(collider)
					#print(collider.bounding_volume.collision_type)
					#sphere
					if collider.bounding_volume.collision_type == 0:
						center = collider.bounding_volume.sphere.center
						r = collider.bounding_volume.sphere.radius
						ob = create_sphere("sphere", center.x, center.y, center.z, r)
						ob.parent = b_obj
					#box
					if collider.bounding_volume.collision_type == 1:
						loc = collider.bounding_volume.box.center
						rot = collider.bounding_volume.box.axis
						x = collider.bounding_volume.box.extent[0]
						y = collider.bounding_volume.box.extent[1]
						z = collider.bounding_volume.box.extent[2]
						matrix = mathutils.Matrix().transposed()*mathutils.Matrix.Translation((loc.x,loc.y,loc.z))
						#ignores the rotation because of the stupid custom array
						ob = create_bounding_box("orientedbox", matrix, x*2, y*2, z*2)
						ob.parent = b_obj
					#capsule
					if collider.bounding_volume.collision_type == 2:
						start = collider.bounding_volume.capsule.center
						end = start + collider.bounding_volume.capsule.origin * collider.bounding_volume.capsule.unknown_float_1
						r = collider.bounding_volume.capsule.unknown_float_2
						#print("capsule", start, end, r)
						ob = create_capsule("capsule", mathutils.Vector((start.x,start.y,start.z)), mathutils.Vector((end.x,end.y,end.z)), r)
						ob.parent = b_armature
						ob.parent_bone = b_obj.name
						ob.parent_type = 'BONE'
						ob.location.y = -b_obj.length
						ob.layers = select_layer(5)
			except:
				print("BFB collision failed!")
			# fix parentship
			if isinstance(b_obj, bpy.types.Object):
				# simple object parentship
				for (n_child, b_child) in object_children:
					b_child.parent = b_obj

			elif isinstance(b_obj, bpy.types.Bone):

				# TODO: MOVE TO ANIMATIONHELPER

				# bone parentship, is a bit more complicated
				# go to rest position

				# b_armature.data.restPosition = True
				bpy.context.scene.objects.active = b_armature

				# set up transforms
				for n_child, b_child in object_children:
					b_child.parent = b_armature
					#b_child.parent_type = 'BONE'
					#b_child.parent_bone = b_obj.name

			else:
				raise RuntimeError("Unexpected object type %s"
								   % b_obj.__class__
								   )

			# track camera for billboard nodes
			if isinstance(niBlock, NifFormat.NiBillboardNode):
				# find camera object
				for obj in self.context.scene.objects:
					if obj.type == 'CAMERA':
						b_obj_camera = obj
						break
				else:
					raise nif_utils.NifError("Scene needs camera for billboard node (add a camera and try again)")
				# make b_obj track camera object
				# b_obj.setEuler(0,0,0)
				b_obj.constraints.new('TRACK_TO')
				constr = b_obj.constraints[-1]
				constr.target = b_obj_camera
				if constr.target is None:
					self.warning("Constraint for billboard node on %s added but target not set due to transform bug in Blender. Set target to Camera manually."
								 % b_obj
								 )
				constr.track_axis = 'TRACK_Z'
				constr.up_axis = 'UP_Y'
				# yields transform bug!
				# constr[Blender.Constraint.Settings.TARGET] = obj

			# set object transform
			# this must be done after all children objects have been
			# parented to b_obj
			if isinstance(b_obj, bpy.types.Object):
				# note: bones already have their matrix set
				b_obj.matrix_local = nif_utils.import_matrix(niBlock)

				# import the animations
				if self.properties.animation:
					self.animationhelper.set_animation(niBlock, b_obj)
					# import the extras
					self.animationhelper.import_text_keys(niBlock)
					# import vis controller
					self.animationhelper.object_animation.import_object_vis_controller(
						b_object=b_obj, n_node=niBlock)

			# import extra node data, such as node type
			# (other types should be added here too)
			if (isinstance(niBlock, NifFormat.NiLODNode) and
				# XXX additional isinstance(b_obj, bpy.types.Object)
				# XXX is a 'workaround' to the limitation that bones
				# XXX cannot have properties in Blender 2.4x
				# XXX (remove this check with Blender 2.5)
					isinstance(b_obj, bpy.types.Object)):
				b_obj.addProperty("Type", "NiLODNode", "STRING")
				# import lod data
				range_data = niBlock.lod_level_data
				for(lod_level, (n_child,
								b_child
								)
					) in zip(range_data.lod_levels,
							 b_children_list
							 ):
					b_child.addProperty("Near Extent",
										lod_level.near_extent,
										"FLOAT"
										)
					b_child.addProperty("Far Extent",
										lod_level.far_extent,
										"FLOAT"
										)

			return b_obj
		# all else is currently discarded
		return None

	def import_shader_types(self, b_obj, b_prop):
		if isinstance(b_prop, NifFormat.BSShaderPPLightingProperty):
			b_obj.niftools_shader.bs_shadertype = 'BSShaderPPLightingProperty'
			sf_type = NifFormat.BSShaderType._enumvalues.index(b_prop.shader_type)
			b_obj.niftools_shader.bsspplp_shaderobjtype = NifFormat.BSShaderType._enumkeys[sf_type]
			for b_flag_name in b_prop.shader_flags._names:
				sf_index = b_prop.shader_flags._names.index(b_flag_name)
				if b_prop.shader_flags._items[sf_index]._value == 1:
					b_obj.niftools_shader[b_flag_name] = True

		if isinstance(b_prop, NifFormat.BSLightingShaderProperty):
			b_obj.niftools_shader.bs_shadertype = 'BSLightingShaderProperty'
			sf_type = NifFormat.BSLightingShaderPropertyShaderType._enumvalues.index(b_prop.skyrim_shader_type)
			b_obj.niftools_shader.bslsp_shaderobjtype = NifFormat.BSLightingShaderPropertyShaderType._enumkeys[sf_type]
			self.import_shader_flags(b_obj, b_prop)

		elif isinstance(b_prop, NifFormat.BSEffectShaderProperty):
			b_obj.niftools_shader.bs_shadertype = 'BSEffectShaderProperty'
			b_obj.niftools_shader.bslsp_shaderobjtype = 'Default'
			self.import_shader_flags(b_obj, b_prop)

	def import_shader_flags(self, b_obj, b_prop):
		for b_flag_name_1 in b_prop.shader_flags_1._names:
			sf_index = b_prop.shader_flags_1._names.index(b_flag_name_1)
			if b_prop.shader_flags_1._items[sf_index]._value == 1:
				b_obj.niftools_shader[b_flag_name_1] = True
		for b_flag_name_2 in b_prop.shader_flags_2._names:
			sf_index = b_prop.shader_flags_2._names.index(b_flag_name_2)
			if b_prop.shader_flags_2._items[sf_index]._value == 1:
				b_obj.niftools_shader[b_flag_name_2] = True

	def import_dismember_body_part(self, body_part):
		if(self.Nif_Version == "20.2.0.7" and self.Nif_User_Version == 11 and self.Nif_User_Version_2 == 34):
			bodypart_group = body_part._attrs[0]
		else:
			bodypart_group = body_part._attrs[1]
		bodypart_value = bodypart_group.type_._enumvalues.index(body_part.dismember_type)
		bodypart_name = bodypart_group.type_._enumkeys[bodypart_value]
		return bodypart_name

	def import_name(self, niBlock, max_length=256):
		"""Get unique name for an object, preserving existing names.
		The maximum name length defaults to 22, since this is the
		maximum for Blender objects. Bone names can reach length 32.

		:param niBlock: A named nif block.
		:type niBlock: :class:`~pyffi.formats.nif.NifFormat.NiObjectNET`
		:param max_length: The maximum length of the name.
		:type max_length: :class:`int`
		"""
		if niBlock is None:
			return None

		if niBlock in self.dict_names:
			return self.dict_names[niBlock]

		self.debug(
			"Importing name for %s block from %s"
			% (niBlock.__class__.__name__, niBlock.name))

		# find unique name for Blender to use
		uniqueInt = 0
		niName = niBlock.name.decode()
		# if name is empty, create something non-empty
		if not niName:
			if isinstance(niBlock, NifFormat.RootCollisionNode):
				niName = "collision"
			else:
				niName = "noname"

		for uniqueInt in range(-1, 1000):
			# limit name length
			if uniqueInt == -1:
				shortName = niName[:max_length - 1]
			else:
				shortName = ('%s.%02d'
							 % (niName[:max_length - 4],
								uniqueInt
								)
							 )
			# bone naming convention for blender
			shortName = self.get_bone_name_for_blender(shortName)
			# make sure it is unique
			if niName == "InvMarker":
				if niName not in self.dict_names:
					break
			if(shortName not in bpy.data.objects and
			   shortName not in bpy.data.materials and
			   shortName not in bpy.data.meshes
			   ):
				# shortName not in use anywhere
				break
		else:
			raise RuntimeError("Ran out of names.")
		# save mapping
		# block niBlock has Blender name shortName
		self.dict_names[niBlock] = shortName
		# Blender name shortName corresponds to niBlock
		self.dict_blocks[shortName] = niBlock
		self.debug("Selected unique name %s"
				   % shortName
				   )
		return shortName

	def import_empty(self, niBlock):
		"""Creates and returns a grouping empty."""
		shortname = self.import_name(niBlock)
		b_empty = bpy.data.objects.new(shortname, None)

		b_empty.niftools.longname = niBlock.name.decode()

		self.context.scene.objects.link(b_empty)
		if self.bsxflags:
			b_empty.niftools.bsxflags = self.bsxflags
		b_empty.niftools.objectflags = niBlock.flags

		if niBlock.name in self.dict_bone_priorities:
			constr = b_empty.constraints.new('ACTION')
			constr.name = "priority:%i" % self.dict_bone_priorities[niBlock.name]
		return b_empty

	def import_mesh(self, niBlock,
					group_mesh=None,
					applytransform=False,
					relative_to=None):
		"""Creates and returns a raw mesh, or appends geometry data to
		group_mesh.

		:param niBlock: The nif block whose mesh data to import.
		:type niBlock: C{NiTriBasedGeom}
		:param group_mesh: The mesh to which to append the geometry
			data. If C{None}, a new mesh is created.
		:type group_mesh: A Blender object that has mesh data.
		:param applytransform: Whether to apply the niBlock's
			transformation to the mesh. If group_mesh is not C{None},
			then applytransform must be C{True}.
		:type applytransform: C{bool}
		"""
		assert(isinstance(niBlock, NifFormat.NiTriBasedGeom))

		self.info("Importing mesh data for geometry %s"
				  % niBlock.name
				  )

		if group_mesh:
			b_obj = group_mesh
			b_mesh = group_mesh.data
		else:
			# Mesh name -> must be unique, so tag it if needed
			b_name = self.import_name(niBlock)
			# create mesh data
			b_mesh = bpy.data.meshes.new(b_name)
			# create mesh object and link to data
			b_obj = bpy.data.objects.new(b_name, b_mesh)
			# link mesh object to the scene
			self.context.scene.objects.link(b_obj)
			# save original name as object property, for export
			if b_name != niBlock.name.decode():
				b_obj.niftools.longname = niBlock.name.decode()

			# Mesh hidden flag
			if niBlock.flags & 1 == 1:
				b_obj.draw_type = 'WIRE'  # hidden: wire
			else:
				b_obj.draw_type = 'TEXTURED'  # not hidden: shaded

		# set transform matrix for the mesh
		if not applytransform:
			if group_mesh:
				raise nif_utils.NifError("BUG: cannot set matrix when importing meshes in groups; use applytransform = True")

			b_obj.matrix_local = nif_utils.import_matrix(niBlock, relative_to=relative_to)

		else:
			# used later on
			transform = nif_utils.import_matrix(niBlock, relative_to=relative_to)

		# shortcut for mesh geometry data
		niData = niBlock.data
		if not niData:
			raise nif_utils.NifError("no shape data in %s"
									 % b_name
									 )

		# vertices
		n_verts = niData.vertices

		# polygons
		poly_gens = [list(tri) for tri in niData.get_triangles()]
		
		n_uvco = []
		# "sticky" UV coordinates: these are transformed in Blender UV's
		for i in range(len(niData.uv_sets)):
			n_uv = list()
			for lw in range(len(niData.uv_sets[i])):
				n_uvt = list()
				n_uvt.append(niData.uv_sets[i][lw].u)
				n_uvt.append(1.0 - (niData.uv_sets[i][lw].v))
				n_uv.append(tuple(n_uvt))
			n_uvco.append(n_uv)
		#n_uvco = tuple(n_uv)
		#why???
		n_uvco.reverse()
	
		
		# vertex normals
		n_norms = niData.normals

		'''
		Properties
		'''

		# Stencil (for double sided meshes)
		n_stencil_prop = nif_utils.find_property(niBlock, NifFormat.NiStencilProperty)
		# we don't check flags for now, nothing fancy
		if n_stencil_prop:
			b_mesh.show_double_sided = True
		else:
			b_mesh.show_double_sided = False

		# Material
		# note that NIF files only support one material for each trishape
		# find material property
		n_mat_prop = nif_utils.find_property(niBlock, NifFormat.NiMaterialProperty)
		n_shader_prop = nif_utils.find_property(niBlock, NifFormat.BSLightingShaderProperty)
		n_effect_shader_prop = nif_utils.find_property(niBlock, NifFormat.BSEffectShaderProperty)

		if n_mat_prop or n_shader_prop or n_effect_shader_prop:
			# Texture
			n_texture_prop = None
			if n_uvco:
				n_texture_prop = nif_utils.find_property(niBlock, NifFormat.NiTexturingProperty)

			# extra datas (for sid meier's railroads) that have material info
			extra_datas = []
			for extra in niBlock.get_extra_datas():
				if isinstance(extra, NifFormat.NiIntegerExtraData):
					if extra.name in self.EXTRA_SHADER_TEXTURES:
						# yes, it describes the shader slot number
						extra_datas.append(extra)

			# bethesda shader
			bsShaderType = None
			bsShaderType = nif_utils.find_property(
				niBlock, NifFormat.BSShaderPPLightingProperty)
			if bsShaderType is None:
				bsShaderType = nif_utils.find_property(niBlock, NifFormat.BSLightingShaderProperty)

			if bsShaderType:
				for textureslot in bsShaderType.texture_set.textures:
					if textureslot:
						self.bsShaderProperty1st = bsShaderType
						break
				else:
					bsShaderType = self.bsShaderProperty1st

			bsEffectShaderProperty = None
			bsEffectShaderProperty = nif_utils.find_property(niBlock, NifFormat.BSEffectShaderProperty)

			# texturing effect for environment map
			# in official files this is activated by a NiTextureEffect child
			# preceeding the niBlock
			textureEffect = None
			if isinstance(niBlock._parent, NifFormat.NiNode):
				lastchild = None
				for child in niBlock._parent.children:
					if child is niBlock:
						if isinstance(lastchild, NifFormat.NiTextureEffect):
							textureEffect = lastchild
						break
					lastchild = child
				else:
					raise RuntimeError("texture effect scanning bug")
				# in some mods the NiTextureEffect child follows the niBlock
				# but it still works because it is listed in the effect list
				# so handle this case separately
				if not textureEffect:
					for effect in niBlock._parent.effects:
						if isinstance(effect, NifFormat.NiTextureEffect):
							textureEffect = effect
							break

			# Alpha
			n_alpha_prop = nif_utils.find_property(niBlock, NifFormat.NiAlphaProperty)
			self.ni_alpha_prop = n_alpha_prop

			# Specularity
			n_specular_prop = nif_utils.find_property(niBlock, NifFormat.NiSpecularProperty)

			# Wireframe
			n_wire_prop = nif_utils.find_property(niBlock, NifFormat.NiWireframeProperty)

			# create material and assign it to the mesh
			# TODO: delegate search for properties to import_material
			material = self.materialhelper.import_material(n_mat_prop,
														   n_texture_prop,
														   n_alpha_prop,
														   n_specular_prop,
														   textureEffect,
														   n_wire_prop,
														   bsShaderType,
														   bsEffectShaderProperty,
														   extra_datas)

			# TODO: merge this call into import_material
			self.animationhelper.material_animation.import_material_controllers(material, niBlock)
			b_mesh_materials = list(b_mesh.materials)
			try:
				materialIndex = b_mesh_materials.index(material)
			except ValueError:
				materialIndex = len(b_mesh_materials)
				b_mesh.materials.append(material)

			'''
			# if mesh has one material with n_wire_prop, then make the mesh
			# wire in 3D view
			if n_wire_prop:
				b_obj.draw_type = 'WIRE'
			'''
		else:
			material = None
			materialIndex = 0

		# v_map will store the vertex index mapping
		# nif vertex i maps to blender vertex v_map[i]
		v_map = [(i) for i in range(len(n_verts))]  # pre-allocate memory, for faster performance

		# Following code avoids introducing unwanted cracks in UV seams:
		# Construct vertex map to get unique vertex / normal pair list.
		# We use a Python dictionary to remove doubles and to keep track of indices.
		# While we are at it, we also add vertices while constructing the map.
		n_map = {}
		b_v_index = len(b_mesh.vertices)
		for i, v in enumerate(n_verts):
			# The key k identifies unique vertex /normal pairs.
			# We use a tuple of ints for key, this works MUCH faster than a
			# tuple of floats.
			if n_norms:
				n = n_norms[i]
				k = (int(v.x * self.VERTEX_RESOLUTION),
					 int(v.y * self.VERTEX_RESOLUTION),
					 int(v.z * self.VERTEX_RESOLUTION),
					 int(n.x * self.NORMAL_RESOLUTION),
					 int(n.y * self.NORMAL_RESOLUTION),
					 int(n.z * self.NORMAL_RESOLUTION))
			else:
				k = (int(v.x * self.VERTEX_RESOLUTION),
					 int(v.y * self.VERTEX_RESOLUTION),
					 int(v.z * self.VERTEX_RESOLUTION))
			# check if vertex was already added, and if so, what index
			try:
				# this is the bottle neck...
				# can we speed this up?
				if not self.properties.combine_vertices:
					n_map_k = None
				else:
					n_map_k = n_map[k]
			except KeyError:
				n_map_k = None
			if not n_map_k:
				# not added: new vertex / normal pair
				n_map[k] = i		 # unique vertex / normal pair with key k was added, with NIF index i
				v_map[i] = b_v_index  # NIF vertex i maps to blender vertex b_v_index
				# add the vertex
				if applytransform:
					v = mathutils.Vector([v.x, v.y, v.z])
					v = v * transform
					b_mesh.vertices.add(1)
					b_mesh.vertices[-1].co = [v.x, v.y, v.z]
				else:
					b_mesh.vertices.add(1)
					b_mesh.vertices[-1].co = [v.x, v.y, v.z]
				# adds normal info if present (Blender recalculates these when
				# switching between edit mode and object mode, handled further)
				# if n_norms:
				#	mv = b_mesh.vertices[b_v_index]
				#	n = n_norms[i]
				#	mv.normal = mathutils.Vector(n.x, n.y, n.z)
				b_v_index += 1
			else:
				# already added
				# NIF vertex i maps to Blender vertex v_map[n_map_k]
				v_map[i] = v_map[n_map_k]
		# report
		self.debug("%i unique vertex-normal pairs" % len(n_map))
		# release memory
		del n_map

		# Adds the polygons to the mesh
		f_map = [None] * len(poly_gens)
		b_f_index = len(b_mesh.polygons)
		bf2_index = len(b_mesh.polygons)
		bl_index = len(b_mesh.loops)
		poly_count = len(poly_gens)
		b_mesh.polygons.add(poly_count)
		b_mesh.loops.add(poly_count * 3)
		num_new_faces = 0  # counter for debugging
		unique_faces = list()  # to avoid duplicate polygons
		tri_point_list = list()
		for i, f in enumerate(poly_gens):
			# get face index
			f_verts = [v_map[vert_index] for vert_index in f]
			if tuple(f_verts) in unique_faces:
				continue
			unique_faces.append(tuple(f_verts))
			f_map[i] = b_f_index
			tri_point_list.append(len(poly_gens[i]))
			ls_list = list()
			b_f_index += 1
			num_new_faces += 1
		for ls1 in range(0, num_new_faces * (tri_point_list[len(ls_list)]), (tri_point_list[len(ls_list)])):
			ls_list.append((ls1 + bl_index))
		for i in range(len(unique_faces)):
			if f_map[i] is None:
				continue
			b_mesh.polygons[f_map[i]].loop_start = ls_list[(f_map[i] - bf2_index)]
			b_mesh.polygons[f_map[i]].loop_total = len(unique_faces[(f_map[i] - bf2_index)])
			l = 0
			lp_points = [v_map[loop_point] for loop_point in poly_gens[(f_map[i] - bf2_index)]]
			while l < (len(poly_gens[(f_map[i] - bf2_index)])):
				b_mesh.loops[(l + (bl_index))].vertex_index = lp_points[l]
				l += 1
			bl_index += (len(poly_gens[(f_map[i] - bf2_index)]))

		# at this point, deleted polygons (degenerate or duplicate)
		# satisfy f_map[i] = None

		self.debug("%i unique polygons" % num_new_faces)

		# set face smoothing and material
		for b_polysmooth_index in f_map:
			if b_polysmooth_index is None:
				continue
			polysmooth = b_mesh.polygons[b_polysmooth_index]
			polysmooth.use_smooth = True if (n_norms or niBlock.skin_instance) else False
			polysmooth.material_index = materialIndex
		# vertex colors

		if b_mesh.polygons and niData.vertex_colors:
			n_vcol_map = list()
			for n_vcol, n_vmap in zip(niData.vertex_colors,
									  v_map
									  ):
				n_vcol_map.append((n_vcol, n_vmap))

			# create vertex_layers
			if "VertexColor" not in b_mesh.vertex_colors:
				b_mesh.vertex_colors.new(name="VertexColor")  # color layer
				b_mesh.vertex_colors.new(name="VertexAlpha")  # greyscale

			# Mesh Vertex Color / Mesh Face
			for b_polygon_loop in b_mesh.loops:
				b_loop_index = b_polygon_loop.index
				vcol = b_mesh.vertex_colors["VertexColor"].data[b_loop_index]
				vcola = b_mesh.vertex_colors["VertexAlpha"].data[b_loop_index]
				for n_col_index, n_map_index in n_vcol_map:
					if n_map_index == b_polygon_loop.vertex_index:
						col_list = n_col_index
						vcol.color.r = col_list.r
						vcol.color.g = col_list.g
						vcol.color.b = col_list.b
						vcola.color.v = col_list.a
			# vertex colors influence lighting...
			# we have to set the use_vertex_color_light flag on the material
			# see below

		# UV coordinates
		# NIF files only support 'sticky' UV coordinates, and duplicates
		# vertices to emulate hard edges and UV seam. So whenever a hard edge
		# or a UV seam is present the mesh, vertices are duplicated. Blender
		# only must duplicate vertices for hard edges; duplicating for UV seams
		# would introduce unnecessary hard edges.

		# only import UV if there are polygons
		# (some corner cases have only one vertex, and no polygons,
		# and b_mesh.faceUV = 1 on such mesh raises a runtime error)
		if b_mesh.polygons:

			# b_mesh.faceUV = 1
			# b_mesh.vertexUV = 0
			for i in range(len(niData.uv_sets)):
				# Set the face UV's for the mesh. The NIF format only supports
				# vertex UV's, but Blender only allows explicit editing of face
				# UV's, so load vertex UV's as face UV's
				uvlayer = self.texturehelper.get_uv_layer_name(i)
				if uvlayer not in b_mesh.uv_textures:
					b_mesh.uv_textures.new(uvlayer)
					uv_faces = b_mesh.uv_textures.active.data[:]
					#print(i,"case1")
				elif uvlayer in b_mesh.uv_textures:
					uv_faces = b_mesh.uv_textures[uvlayer].data[:]
					#print(i,"case2")
				else:
					uv_faces = None
					#print(i,"case3")
				if uv_faces:
					uvl = b_mesh.uv_layers.active.data[:]
					for b_f_index, f in enumerate(poly_gens):
						if b_f_index is None:
							continue
						uvlist = f
						v1, v2, v3 = uvlist
						# if v3 == 0:
						#   v1,v2,v3 = v3,v1,v2
						#print(n_uvco[i])
						b_poly_index = b_mesh.polygons[b_f_index + bf2_index]
						uvl[b_poly_index.loop_start].uv = n_uvco[i][v1]
						uvl[b_poly_index.loop_start + 1].uv = n_uvco[i][v2]
						uvl[b_poly_index.loop_start + 2].uv = n_uvco[i][v3]
			b_mesh.uv_textures.active_index = 0

		if material:
			# fix up vertex colors depending on whether we had textures in the
			# material
			mbasetex = self.texturehelper.has_base_texture(material)
			mglowtex = self.texturehelper.has_glow_texture(material)
			if b_mesh.vertex_colors:
				if mbasetex or mglowtex:
					# textured material: vertex colors influence lighting
					material.use_vertex_color_light = True
				else:
					# non-textured material: vertex colors incluence color
					material.use_vertex_color_paint = True

			# if there's a base texture assigned to this material sets it
			# to be displayed in Blender's 3D view
			# but only if there are UV coordinates
			if mbasetex and mbasetex.texture and n_uvco:
				imgobj = mbasetex.texture.image
				if imgobj:
					for b_polyimage_index in f_map:
						if b_polyimage_index is None:
							continue
						tface = b_mesh.uv_textures.active.data[b_polyimage_index]
						# gone in blender 2.5x+?
						# f.mode = Blender.Mesh.FaceModes['TEX']
						# f.transp = Blender.Mesh.FaceTranspModes['ALPHA']
						tface.image = imgobj

		# import skinning info, for meshes affected by bones
		skininst = niBlock.skin_instance
		if skininst:
			skindata = skininst.data
			bones = skininst.bones
			boneWeights = skindata.bone_list
			for idx, bone in enumerate(bones):
				# skip empty bones (see pyffi issue #3114079)
				if not bone:
					continue
				vertex_weights = boneWeights[idx].vertex_weights
				groupname = self.dict_names[bone]
				if groupname not in b_obj.vertex_groups.items():
					v_group = b_obj.vertex_groups.new(groupname)
				for skinWeight in vertex_weights:
					vert = skinWeight.index
					weight = skinWeight.weight
					v_group.add([v_map[vert]],
								weight,
								'REPLACE'
								)

		# import body parts as vertex groups
		if isinstance(skininst, NifFormat.BSDismemberSkinInstance):
			skinpart_list = []
			bodypart_flag = []
			skinpart = niBlock.get_skin_partition()
			for bodypart, skinpartblock in zip(skininst.partitions,
											   skinpart.skin_partition_blocks
											   ):
				groupname = self.import_dismember_body_part(bodypart.body_part)
				# create vertex group if it did not exist yet
				if not(groupname in b_obj.vertex_groups.items()):
					v_group = b_obj.vertex_groups.new(groupname)
					skinpart_index = len(skinpart_list)
					skinpart_list.append((skinpart_index, groupname))
					bodypart_flag.append(bodypart.part_flag)
				# find vertex indices of this group
				groupverts = [v_map[v_index] for
							  v_index in skinpartblock.vertex_map
							  ]
				# create the group
				v_group.add(groupverts, 1, 'ADD')
			b_obj.niftools_part_flags_panel.pf_partcount = len(skinpart_list)
			for i, pl_name in skinpart_list:
				b_obj_partflag = b_obj.niftools_part_flags.add()
				# b_obj.niftools_part_flags.pf_partint = (i)
				b_obj_partflag.name = (pl_name)
				b_obj_partflag.pf_editorflag = (bodypart_flag[i].pf_editor_visible)
				b_obj_partflag.pf_startflag = (bodypart_flag[i].pf_start_net_boneset)
		# import morph controller
		# TODO: move this to import_mesh_controllers
		if self.properties.animation:
			morphCtrl = nif_utils.find_controller(niBlock, NifFormat.NiGeomMorpherController)
			if morphCtrl:
				morphData = morphCtrl.data
				if morphData.num_morphs:
					bpy.context.scene.frame_set(1)
					# get name for base key
					keyname = morphData.morphs[0].frame_name.decode()
					if not keyname:
						keyname = 'Base'
					# set name for base key and
					# insert base key at frame 1, using relative keys
					b_obj.shape_key_add(name=keyname)
					b_mesh.shape_keys.name = b_obj.name
					# get base vectors and import all morphs
					baseverts = morphData.morphs[0].vectors
					b_action = bpy.data.actions.new('KEY')
					b_mesh.shape_keys.key_blocks[keyname].keyframe_insert("value",
																		  frame=1,
																		  group=b_obj.name
																		  )
					for idxMorph in range(1, morphData.num_morphs):
						# get name for key
						keyname = morphData.morphs[idxMorph].frame_name.decode()
						if not keyname:
							keyname = 'Key %i' % idxMorph
						self.info("inserting key '%s'"
								  % keyname
								  )

						b_obj.shape_key_add(name=keyname)
						# get vectors
						morphverts = morphData.morphs[idxMorph].vectors
						# for each vertex calculate the key position from base
						# pos + delta offset
						assert(len(baseverts) == len(morphverts) == len(v_map))
						for bv, mv, b_v_index in zip(baseverts, morphverts, v_map):
							base = mathutils.Vector((bv.x, bv.y, bv.z))
							delta = mathutils.Vector((mv.x, mv.y, mv.z))
							v = base + delta
							if applytransform:
								v *= transform
							b_mesh.vertices[b_v_index].co[0] = v.x
							b_mesh.vertices[b_v_index].co[1] = v.y
							b_mesh.vertices[b_v_index].co[2] = v.z
						# update the mesh and insert key
						b_mesh.shape_keys.key_blocks[keyname].keyframe_insert("value",
																			  frame=idxMorph,
																			  group=b_obj.name
																			  )
						# set name for key
						# set up the ipo key curve
						try:
							b_curve = b_mesh.shape_keys.key_blocks[keyname]
						except ValueError:
							# this happens when two keys have the same name
							# an instance of this is in fallout 3
							# meshes/characters/_male/skeleton.nif HeadAnims:0
							self.warning("skipped duplicate of key '%s'"
										 % keyname
										 )
						# no idea how to set up the bezier triples -> switching
						# to linear instead
						b_curve.interpolation = "KEY_LINEAR"
						# select extrapolation
						self.get_extend_from_flags(b_curve, morphCtrl.flags)
						# set up the curve's control points
						# first find the keys
						# older versions store keys in the morphData
						morphkeys = morphData.morphs[idxMorph].keys
						# newer versions store keys in the controller
						if (not morphkeys) and morphCtrl.interpolators:
							morphkeys = morphCtrl.interpolators[idxMorph].data.data.keys
						for key in morphkeys:
							x = key.value
							frame = 1 + int(key.time * self.fps + 0.5)
							b_curve.addBezier((frame, x))
						# finally: return to base position
						for bv, b_v_index in zip(baseverts, v_map):
							base = mathutils.Vector((bv.x, bv.y, bv.z))
							if applytransform:
								base *= transform
							b_mesh.vertices[b_v_index].co[0] = base.x
							b_mesh.vertices[b_v_index].co[1] = base.y
							b_mesh.vertices[b_v_index].co[2] = base.z

		# import facegen morphs
		if self.egmdata:
			# XXX if there is an egm, the assumption is that there is only one
			# XXX mesh in the nif
			sym_morphs = [list(morph.get_relative_vertices())
						  for morph in self.egmdata.sym_morphs]
			asym_morphs = [list(morph.get_relative_vertices()) for morph in self.egmdata.asym_morphs]

			# insert base key at frame 1, using relative keys
			b_mesh.insertKey(1, 'relative')

			if self.IMPORT_EGMANIM:
				# if morphs are animated: create key ipo for mesh
				b_action = bpy.data.actions.new('KEY')
				b_mesh.key.ipo = b_action

			morphs = ([(morph, "EGM SYM %i" % i) for i, morph in enumerate(sym_morphs)] +
					  [(morph, "EGM ASYM %i" % i) for i, morph in enumerate(asym_morphs)]
					  )

			for morphverts, keyname in morphs:
				# length check disabled
				# as sometimes, oddly, the morph has more vertices...
				# assert(len(verts) == len(morphverts) == len(v_map))

				# for each vertex calculate the key position from base
				# pos + delta offset
				for bv, mv, b_v_index in zip(n_verts, morphverts, v_map):
					base = mathutils.Vector(bv.x, bv.y, bv.z)
					delta = mathutils.Vector(mv[0], mv[1], mv[2])
					v = base + delta
					if applytransform:
						v *= transform
					b_mesh.vertices[b_v_index].co[0] = v.x
					b_mesh.vertices[b_v_index].co[1] = v.y
					b_mesh.vertices[b_v_index].co[2] = v.z
				# update the mesh and insert key
				b_mesh.insertKey(1, 'relative')
				# set name for key
				b_mesh.key.blocks[-1].name = keyname

				if self.IMPORT_EGMANIM:
					# set up the ipo key curve
					b_curve = b_action.addCurve(keyname)
					# linear interpolation
					b_curve.interpolation = bpy.types.Keyframe.interpolation("LINEAR")
					# constant extrapolation
					b_curve.extend = bpy.types.FCurve.extrapolation("CONSTANT")
					# set up the curve's control points
					framestart = 1 + len(b_mesh.key.blocks) * 10
					for frame, value in ((framestart, 0),
										 (framestart + 5, self.IMPORT_EGMANIMSCALE),
										 (framestart + 10, 0)):
						b_curve.addBezier((frame, value))

			if self.IMPORT_EGMANIM:
				# set begin and end frame
				self.context.scene.getRenderingContext().startFrame(1)
				self.context.scene.getRenderingContext().endFrame(
					11 + len(b_mesh.key.blocks) * 10)

			# finally: return to base position
			for bv, b_v_index in zip(n_verts, v_map):
				base = mathutils.Vector(bv.x, bv.y, bv.z)
				if applytransform:
					base *= transform
				b_mesh.vertices[b_v_index].co[0] = base.x
				b_mesh.vertices[b_v_index].co[1] = base.y
				b_mesh.vertices[b_v_index].co[2] = base.z

		# import priority if existing
		if niBlock.name in self.dict_bone_priorities:
			constr = b_obj.constraints.new('ACTION')
			constr.name = "priority:%i" % self.dict_bone_priorities[niBlock.name]

		# recalculate mesh to render correctly
		# implementation note: update() without validate() can cause crash

		b_mesh.validate()
		b_mesh.update()
		b_obj.select = True
		scn = bpy.context.scene
		scn.objects.active = b_obj

		return b_obj

	def set_parents(self, niBlock):
		"""Set the parent block recursively through the tree, to allow
		crawling back as needed."""
		if isinstance(niBlock, NifFormat.NiNode):
			# list of non-null children
			children = [child for child in niBlock.children if child]
			for child in children:
				child._parent = niBlock
				self.set_parents(child)

	def is_grouping_node(self, niBlock):
		"""Determine whether node is grouping node.
		Returns the children which are grouped, or empty list if it is not a
		grouping node.
		"""
		# combining shapes: disable grouping
		if not self.properties.combine_shapes:
			return []
		# check that it is a ninode
		if not isinstance(niBlock, NifFormat.NiNode):
			return []
		# NiLODNodes are never grouping nodes
		# (this ensures that they are imported as empties, with LODs
		# as child meshes)
		if isinstance(niBlock, NifFormat.NiLODNode):
			return []
		# root collision node: join everything
		if isinstance(niBlock, NifFormat.RootCollisionNode):
			return [child for child in niBlock.children if
					isinstance(child, NifFormat.NiTriBasedGeom)
					]
		# check that node has name
		node_name = niBlock.name
		if not node_name:
			return []
		# strip "NonAccum" trailer, if present
		if node_name[-9:].lower() == " nonaccum":
			node_name = node_name[:-9]
		# get all geometry children
		return [child for child in niBlock.children if
				(isinstance(child, NifFormat.NiTriBasedGeom) and
				 child.name.find(node_name) != -1
				 )
				]


def menu_func(self, context):
	"""Import operator for the menu."""
	# TODO: get default path from config registry
	# default_path = bpy.data.filename.replace(".blend", ".nif")
	default_path = "import.nif"
	self.layout.operator(NifImport.bl_idname,
						 text="NetImmerse/Gamebryo (.nif & .kf & .egm)"
						 ).filepath = default_path


def register():
	"""Register nif import operator."""
	bpy.types.register(NifImport)
	bpy.types.INFO_MT_file_import.append(menu_func)


def unregister():
	"""Unregister nif import operator."""
	bpy.types.unregister(NifImport)
	bpy.types.INFO_MT_file_import.remove(menu_func)

if __name__ == '__main__':
	"""Register nif import, when starting Blender."""
	register()
