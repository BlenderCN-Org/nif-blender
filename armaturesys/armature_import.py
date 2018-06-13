'''Script to import/export all the skeleton related objects.'''

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

import os

import bpy
import mathutils
import math

from pyffi.formats.nif import NifFormat

from ..utility import nif_utils

correction_local = mathutils.Euler((math.radians(90), 0, math.radians(90))).to_matrix().to_4x4()
correction_global = mathutils.Euler((math.radians(-90), math.radians(-90), 0)).to_matrix().to_4x4()

def vec_roll_to_mat3(vec, roll):
	#port of the updated C function from armature.c
	#https://developer.blender.org/T39470
	#note that C accesses columns first, so all matrix indices are swapped compared to the C version
	
	nor = vec.normalized()
	THETA_THRESHOLD_NEGY = 1.0e-9
	THETA_THRESHOLD_NEGY_CLOSE = 1.0e-5
	
	#create a 3x3 matrix
	bMatrix = mathutils.Matrix().to_3x3()

	theta = 1.0 + nor[1]

	if (theta > THETA_THRESHOLD_NEGY_CLOSE) or ((nor[0] or nor[2]) and theta > THETA_THRESHOLD_NEGY):

		bMatrix[1][0] = -nor[0]
		bMatrix[0][1] = nor[0]
		bMatrix[1][1] = nor[1]
		bMatrix[2][1] = nor[2]
		bMatrix[1][2] = -nor[2]
		if theta > THETA_THRESHOLD_NEGY_CLOSE:
			#If nor is far enough from -Y, apply the general case.
			bMatrix[0][0] = 1 - nor[0] * nor[0] / theta
			bMatrix[2][2] = 1 - nor[2] * nor[2] / theta
			bMatrix[0][2] = bMatrix[2][0] = -nor[0] * nor[2] / theta
		
		else:
			#If nor is too close to -Y, apply the special case.
			theta = nor[0] * nor[0] + nor[2] * nor[2]
			bMatrix[0][0] = (nor[0] + nor[2]) * (nor[0] - nor[2]) / -theta
			bMatrix[2][2] = -bMatrix[0][0]
			bMatrix[0][2] = bMatrix[2][0] = 2.0 * nor[0] * nor[2] / theta

	else:
		#If nor is -Y, simple symmetry by Z axis.
		bMatrix = mathutils.Matrix().to_3x3()
		bMatrix[0][0] = bMatrix[1][1] = -1.0

	#Make Roll matrix
	rMatrix = mathutils.Matrix.Rotation(roll, 3, nor)
	
	#Combine and output result
	mat = rMatrix * bMatrix
	return mat

def mat3_to_vec_roll(mat):
	#this hasn't changed
	vec = mat.col[1]
	vecmat = vec_roll_to_mat3(mat.col[1], 0)
	vecmatinv = vecmat.inverted()
	rollmat = vecmatinv * mat
	roll = math.atan2(rollmat[0][2], rollmat[2][2])
	return vec, roll
	
def import_bone_matrix(niBlock, relative_to=None):
	"""Retrieves a niBlock's transform matrix as a Mathutil.Matrix."""
	return mathutils.Matrix(niBlock.get_transform(relative_to).as_list())


class Armature():

	def __init__(self, parent):
		self.nif_import = parent
		self.properties = parent.properties

	def import_armature(self, niArmature):
		"""Scans an armature hierarchy, and returns a whole armature.
		This is done outside the normal node tree scan to allow for positioning
		of the bones before skins are attached."""
		armature_name = self.nif_import.import_name(niArmature)

		b_armatureData = bpy.data.armatures.new(armature_name)
		b_armatureData.show_names = True
		b_armatureData.show_axes = True
		b_armatureData.draw_type = 'STICK'
		b_armature = bpy.data.objects.new(armature_name, b_armatureData)
		b_armature.select = True
		b_armature.show_x_ray = True

		# Link object to scene
		scn = bpy.context.scene
		scn.objects.link(b_armature)
		scn.objects.active = b_armature
		scn.update()

		# make armature editable and create bones
		bpy.ops.object.mode_set(mode='EDIT', toggle=False)
		niChildBones = [child for child in niArmature.children if self.is_bone(child)]
		for niBone in niChildBones:
			self.import_bone(niBone, b_armature, b_armatureData, niArmature)

		#fix the bone length
		for bone in b_armatureData.edit_bones:
			#don't change Bip01
			if bone.parent:
				if bone.children:
					childheads = mathutils.Vector()
					for child in bone.children:
						childheads += child.head
					bone_length = (bone.head - childheads/len(bone.children)).length
					if bone_length < 0.01:
						bone_length = 0.25
				# end of a chain
				else:
					bone_length = bone.parent.length
				bone.length = bone_length
				
		bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
		scn = bpy.context.scene
		scn.objects.active = b_armature
		scn.update()

		# The armature has been created in editmode,
		# now we are ready to set the bone keyframes.
		if self.properties.animation:
			self.nif_import.animationhelper.armature_animation.import_armature_animation(b_armature)

		# constraints (priority)
		# must be done outside edit mode hence after calling
		for bone_name, b_posebone in b_armature.pose.bones.items():
			# find bone nif block
			if bone_name.startswith("InvMarker"):
				bone_name = "InvMarker"
			niBone = self.nif_import.dict_blocks[bone_name]
			# store bone priority, if applicable
			if niBone.name in self.nif_import.dict_bone_priorities:
				constr = b_posebone.constraints.new('ACTION')
				constr.name = "priority:%i" % self.nif_import.dict_bone_priorities[niBone.name]

		scn = bpy.context.scene
		scn.objects.active = b_armature
		scn.update()
		return b_armature

	def import_bone(self, niBlock, b_armature, b_armatureData, niArmature):
		"""Adds a bone to the armature in edit mode."""
		# check that niBlock is indeed a bone
		if not self.is_bone(niBlock):
			return None

		#scale = self.properties.scale_correction_import
		# bone name
		bone_name = self.nif_import.import_name(niBlock, 32)
		niChildBones = [child for child in niBlock.children if self.is_bone(child)]
		# create a new bone
		b_bone = b_armatureData.edit_bones.new(bone_name)
		# head: get position from niBlock
		armature_space_matrix = nif_utils.import_matrix(niBlock, relative_to=niArmature)
		#set transformation
		bind = correction_global * correction_local * armature_space_matrix * correction_local.inverted()
		tail, roll = mat3_to_vec_roll(bind.to_3x3())
		b_bone.head = bind.to_translation()
		b_bone.tail = tail + b_bone.head
		b_bone.roll = roll
		# # set bone children
		for niBone in niChildBones:
			b_child_bone = self.import_bone(niBone, b_armature, b_armatureData, niArmature)
			b_child_bone.parent = b_bone
		return b_bone

	def append_armature_modifier(self, b_obj, b_armature):
		"""Append an armature modifier for the object."""
		armature_name = b_armature.name
		b_mod = b_obj.modifiers.new(armature_name, 'ARMATURE')
		b_mod.object = b_armature
		b_mod.use_bone_envelopes = False
		b_mod.use_vertex_groups = True

	def mark_armatures_bones(self, niBlock):
		"""Mark armatures and bones by peeking into NiSkinInstance blocks."""
		# case where we import skeleton only,
		# or importing an Oblivion or Fallout 3 skeleton:
		# do all NiNode's as bones
		if(self.properties.skeleton == "SKELETON_ONLY" or
		   (self.nif_import.data.version in (0x14000005, 0x14020007) and
			(os.path.basename(self.properties.filepath).lower()
			 in ('skeleton.nif',
				 'skeletonbeast.nif'
				 )
			 )
			)
		   ):

			if not isinstance(niBlock, NifFormat.NiNode):
				raise nif_utils.NifError("cannot import skeleton: root is not a NiNode")
			# for morrowind, take the Bip01 node to be the skeleton root
			if self.nif_import.data.version == 0x04000002:
				skelroot = niBlock.find(block_name='Bip01',
										block_type=NifFormat.NiNode)
				if not skelroot:
					skelroot = niBlock
			else:
				skelroot = niBlock
			if skelroot not in self.nif_import.dict_armatures:
				self.nif_import.dict_armatures[skelroot] = []
			self.nif_import.info("Selecting node '%s' as skeleton root"
								 % skelroot.name
								 )
			# add bones
			for bone in skelroot.tree():
				if bone is skelroot:
					continue
				if not isinstance(bone, NifFormat.NiNode):
					continue
				if self.nif_import.is_grouping_node(bone):
					continue
				if bone not in self.nif_import.dict_armatures[skelroot]:
					self.nif_import.dict_armatures[skelroot].append(bone)
			return  # done!

		# attaching to selected armature -> first identify armature and bones
		elif(self.properties.skeleton == "GEOMETRY_ONLY" and not
			 self.nif_import.dict_armatures
			 ):
			skelroot = niBlock.find(block_name=self.nif_import.selected_objects[0].name)
			if not skelroot:
				raise nif_utils.NifError("nif has no armature '%s'"
										 % self.nif_import.selected_objects[0].name
										 )
			self.nif_import.debug("Identified '%s' as armature"
								  % skelroot.name
								  )
			self.nif_import.dict_armatures[skelroot] = []
			for bone_name in self.nif_import.selected_objects[0].data.bones.keys():
				# blender bone naming -> nif bone naming
				nif_bone_name = self.nif_import.get_bone_name_for_nif(bone_name)
				# find a block with bone name
				bone_block = skelroot.find(block_name=nif_bone_name)
				# add it to the name list if there is a bone with that name
				if bone_block:
					self.nif_import.info("Identified nif block '%s' with bone '%s' in selected armature"
										 % (nif_bone_name, bone_name)
										 )
					self.nif_import.dict_names[bone_block] = bone_name
					self.nif_import.dict_armatures[skelroot].append(bone_block)
					self.complete_bone_tree(bone_block, skelroot)

		# search for all NiTriShape or NiTriStrips blocks...
		if isinstance(niBlock, NifFormat.NiTriBasedGeom):
			# yes, we found one, get its skin instance
			if niBlock.is_skin():
				self.nif_import.debug("Skin found on block '%s'"
									  % niBlock.name
									  )
				# it has a skin instance, so get the skeleton root
				# which is an armature only if it's not a skinning influence
				# so mark the node to be imported as an armature
				skininst = niBlock.skin_instance
				skelroot = skininst.skeleton_root
				if self.properties.skeleton == "EVERYTHING":
					if skelroot not in self.nif_import.dict_armatures:
						self.nif_import.dict_armatures[skelroot] = []
						self.nif_import.debug("'%s' is an armature"
											  % skelroot.name
											  )
				elif self.properties.skeleton == "GEOMETRY_ONLY":
					if skelroot not in self.nif_import.dict_armatures:
						raise nif_utils.NifError("nif structure incompatible with '%s' as armature: node '%s' has '%s' as armature"
												 % (self.nif_import.selected_objects[0].name,
													niBlock.name,
													skelroot.name
													)
												 )

				for boneBlock in skininst.bones:
					# boneBlock can be None; see pyffi issue #3114079
					if not boneBlock:
						continue
					if boneBlock not in self.nif_import.dict_armatures[skelroot]:
						self.nif_import.dict_armatures[skelroot].append(boneBlock)
						self.nif_import.debug("'%s' is a bone of armature '%s'"
											  % (boneBlock.name,
												 skelroot.name
												 )
											  )
					# now we "attach" the bone to the armature:
					# we make sure all NiNodes from this bone all the way
					# down to the armature NiNode are marked as bones
					self.complete_bone_tree(boneBlock, skelroot)

				# mark all nodes as bones if asked
				if self.nif_import.IMPORT_EXTRANODES:
					# add bones
					for bone in skelroot.tree():
						if bone is skelroot:
							continue
						if not isinstance(bone, NifFormat.NiNode):
							continue
						if isinstance(bone, NifFormat.NiLODNode):
							# LOD nodes are never bones
							continue
						if self.nif_import.is_grouping_node(bone):
							continue
						if bone not in self.nif_import.dict_armatures[skelroot]:
							self.nif_import.dict_armatures[skelroot].append(bone)
							self.nif_import.debug("'%s' marked as extra bone of armature '%s'"
												  % (bone.name,
													 skelroot.name
													 )
												  )
							# we make sure all NiNodes from this bone
							# all the way down to the armature NiNode
							# are marked as bones
							self.complete_bone_tree(bone, skelroot)

		# continue down the tree
		for child in niBlock.get_refs():
			if not isinstance(child, NifFormat.NiAVObject):
				continue  # skip blocks that don't have transforms
			self.mark_armatures_bones(child)

	def complete_bone_tree(self, bone, skelroot):
		"""Make sure that the bones actually form a tree all the way
		down to the armature node. Call this function on all bones of
		a skin instance.
		"""
		# we must already have marked this one as a bone
		assert skelroot in self.nif_import.dict_armatures  # debug
		assert bone in self.nif_import.dict_armatures[skelroot]  # debug
		# get the node parent, this should be marked as an armature or as a bone
		boneparent = bone._parent
		if boneparent != skelroot:
			# parent is not the skeleton root
			if boneparent not in self.nif_import.dict_armatures[skelroot]:
				# neither is it marked as a bone: so mark the parent as a bone
				self.nif_import.dict_armatures[skelroot].append(boneparent)
				# store the coordinates for realignement autodetection
				self.nif_import.debug("'%s' is a bone of armature '%s'"
									  % (boneparent.name,
										 skelroot.name
										 )
									  )
			# now the parent is marked as a bone
			# recursion: complete the bone tree,
			# this time starting from the parent bone
			self.complete_bone_tree(boneparent, skelroot)

	def is_bone(self, niBlock):
		"""Tests a NiNode to see if it's a bone."""
		if not niBlock:
			return False
		for bones in self.nif_import.dict_armatures.values():
			if niBlock in bones:
				return True
		return False

	def is_armature_root(self, niBlock):
		"""Tests a block to see if it's an armature."""
		if isinstance(niBlock, NifFormat.NiNode):
			return niBlock in self.nif_import.dict_armatures
		return False

	def get_closest_bone(self, niBlock, skelroot):
		"""Detect closest bone ancestor."""
		par = niBlock._parent
		while par:
			if par == skelroot:
				return None
			if self.is_bone(par):
				return par
			par = par._parent
		return par

	def get_blender_object(self,
						   niBlock
						   ):
		"""Retrieves the Blender object or Blender bone matching the block."""
		if self.is_bone(niBlock):
			bone_name = self.nif_import.dict_names[niBlock]
			armatureName = None
			for armatureBlock, boneBlocks in self.nif_import.dict_armatures.items():
				if niBlock in boneBlocks:
					armatureName = self.nif_import.dict_names[armatureBlock]
					break
				else:
					raise nif_utils.NifError("cannot find bone '%s'"
											 % bone_name
											 )
			armatureObject = bpy.types.Object(armatureName)
			return armatureObject.data.bones[bone_name]
		else:
			return bpy.types.Object(self.nif_import.dict_names[niBlock])

	def decompose_srt(self,
					  matrix
					  ):
		"""Decompose Blender transform matrix as a scale, rotation matrix, and translation vector."""
		# get scale components
		trans_vec, rot_quat, scale_vec = matrix.decompose()
		scale_rot = rot_quat.to_matrix()
		b_scale = mathutils.Vector((scale_vec[0] ** 0.5,
									scale_vec[1] ** 0.5,
									scale_vec[2] ** 0.5))
		# and fix their sign
		if (scale_rot.determinant() < 0):
			b_scale.negate()
		# only uniform scaling
		if(abs(scale_vec[0] - scale_vec[1]) >= self.properties.epsilon or
		   abs(scale_vec[1] - scale_vec[2]) >= self.properties.epsilon
		   ):
			self.nif_import.warning("Corrupt rotation matrix in nif: geometry errors may result.")
		b_scale = b_scale[0]
		# get rotation matrix
		b_rot = scale_rot * b_scale
		# get translation
		b_trans = trans_vec
		# done!
		return [b_scale, b_rot, b_trans]

	def store_names(self):
		"""Stores the original, long object names so that they can be
		re-exported. In order for this to work it is necessary to mantain the
		imported names unaltered. Since the text buffer is cleared on each
		import only the last import will be exported correctly."""
		# clear the text buffer, or create new buffer
		try:
			namestxt = bpy.data.texts["FullNames"]
			namestxt.clear()
		except KeyError:
			namestxt = bpy.data.texts.new("FullNames")

		# write the names to the text buffer
		for block, shortname in self.nif_import.dict_names.items():
			block_name = block.name.decode()
			if block_name and shortname != block_name:
				namestxt.write('%s;%s\n' % (shortname, block_name))
