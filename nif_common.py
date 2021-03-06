"""Helper functions for nif import and export scripts."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2005-2015, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
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

import logging

import bpy
import re

import pyffi
from pyffi.formats.nif import NifFormat


class NifCommon:
    """Abstract base class for import and export. Contains utility functions
    that are commonly used in both import and export.
    """

    # dictionary of bones that belong to a certain armature
    # maps NIF armature name to list of NIF bone name
    dict_armatures = {}
    # dictionary of bones, maps Blender bone name to matrix that maps the
    # NIF bone matrix on the Blender bone matrix
    # B' = X * B, where B' is the Blender bone matrix, and B is the NIF bone matrix
    dict_bones_extra_matrix = {}

    # dictionary of bones, maps Blender bone name to matrix that maps the
    # NIF bone matrix on the Blender bone matrix
    # Recall from the import script
    #   B' = X * B,
    # where B' is the Blender bone matrix, and B is the NIF bone matrix,
    # both in armature space. So to restore the NIF matrices we need to do
    #   B = X^{-1} * B'
    # Hence, we will restore the X's, invert them, and store those inverses in the
    # following dictionary.
    dict_bones_extra_matrix_inv = {}

    # dictionary mapping bhkRigidBody objects to objects imported in Blender;
    # we use this dictionary to set the physics constraints (ragdoll etc)
    dict_havok_objects = {}

    # dictionary of names, to map NIF blocks to correct Blender names
    dict_names = {}

    # dictionary of bones, maps Blender name to NIF block
    dict_blocks = {}

    # keeps track of names of exported blocks, to make sure they are unique
    dict_block_names = []

    # bone animation priorities (maps NiNode name to priority number);
    # priorities are set in import_kf_root and are stored into the name
    # of a NULL constraint (for lack of something better) in
    # import_armature
    dict_bone_priorities = {}

    # dictionary of materials, to reuse materials
    dict_materials = {}

    # dictionary of texture files, to reuse textures
    dict_textures = {}
    dict_mesh_uvlayers = []

    VERTEX_RESOLUTION = 1000
    NORMAL_RESOLUTION = 100

    EXTRA_SHADER_TEXTURES = ["EnvironmentMapIndex",
                             "NormalMapIndex",
                             "SpecularIntensityIndex",
                             "EnvironmentIntensityIndex",
                             "LightCubeMapIndex",
                             "ShadowTextureIndex"
                             ]
    """Names (ordered by default index) of shader texture slots for
    Sid Meier's Railroads and similar games.
    """

    HAVOK_SCALE = 6.996

    Nif_Version = 0
    Nif_User_Version = 0
    Nif_User_Version_2 = 0

    def __init__(self, operator, context):
        """Common initialization functions for executing the import/export
        operators:

        - initialize progress bar
        - set logging level
        - set self.context
        - set self.selected_objects
        """
        # print scripts info
        from . import bl_info
        operator.report(
            {'INFO'},
            "Blender NIF Scripts %s"
            " (running on Blender %s, PyFFI %s)"
            % (".".join(str(i) for i in bl_info["version"]),
               bpy.app.version_string,
               pyffi.__version__))

        # copy properties from operator (contains import/export settings)
        self.operator = operator
        self.properties = operator.properties

        # set logging level
        log_level_num = getattr(logging, self.properties.log_level)
        logging.getLogger("niftools").setLevel(log_level_num)
        logging.getLogger("pyffi").setLevel(log_level_num)

        # save context (so it can be used in other methods without argument
        # passing)
        self.context = context

        # get list of selected objects
        # (find and store this list now, as creating new objects adds them
        # to the selection list)
        self.selected_objects = self.context.selected_objects[:]

    def execute(self):
        """Import/export entry point. Default implementation does nothing."""
        return {'FINISHED'}

    def debug(self, message):
        """Report a debug message."""
        self.operator.report({'DEBUG'}, message)

    def info(self, message):
        """Report an informative message."""
        self.operator.report({'INFO'}, message)

    def warning(self, message):
        """Report a warning message."""
        self.operator.report({'WARNING'}, message)

    def error(self, message):
        """Report an error and return ``{'FINISHED'}``. To be called by
        the :meth:`execute` method, as::

            return error('Something went wrong.')

        Blender will raise an exception that is passed to the caller.

        .. seealso::

            The :ref:`error reporting <dev-design-error-reporting>` design.
        """
        self.operator.report({'ERROR'}, message)
        return {'FINISHED'}

    def get_game_to_trans(self, gname):
        symbols = ":,'\" +-*!?;./="
        table = str.maketrans(symbols, "_" * len(symbols))
        enum = gname.upper().translate(table).replace("__", "_")
        return enum

    def get_bone_name_for_blender(self, name):
        """Convert a bone name to a name that can be used by Blender: turns
        'Bip01 R xxx' into 'Bip01 xxx.R', and similar for L.

        :param name: The bone name as in the nif file.
        :type name: :class:`str`
        :return: Bone name in Blender convention.
        :rtype: :class:`str`
        """
        if isinstance(name, bytes):
            name = name.decode()
        if name.startswith("Bip01 L "):
            return "Bip01 " + name[8:] + ".L"
        elif name.startswith("Bip01 R "):
            return "Bip01 " + name[8:] + ".R"
        elif name.startswith("NPC L ") and name.endswith("]"):
            name = name.replace("NPC L", "NPC")
            name = name.replace("[L", "[")
            name = name.replace("]", "].L")
            return name
        elif name.startswith("NPC R ") and name.endswith("]"):
            name = name.replace("NPC R", "NPC")
            name = name.replace("[R", "[")
            name = name.replace("]", "].R")
            return name

        return name

    def get_bone_name_for_nif(self, name):
        """Convert a bone name to a name that can be used by the nif file:
        turns 'Bip01 xxx.R' into 'Bip01 R xxx', and similar for L.

        :param name: The bone name as in Blender.
        :type name: :class:`str`
        :return: Bone name in nif convention.
        :rtype: :class:`str`
        """
        if isinstance(name, bytes):
            name = name.decode()
        if name.startswith("Bip01 "):
            if name.endswith(".L"):
                return "Bip01 L " + name[6:-2]
            elif name.endswith(".R"):
                return "Bip01 R " + name[6:-2]
        elif name.startswith("NPC ") and name.endswith("].L"):
            name = name.replace("NPC ", "NPC L")
            name = name.replace("[", "[L")
            name = name.replace("].L", "]")
            return name
        elif name.startswith("NPC ") and name.endswith("].R"):
            name = name.replace("NPC ", "NPC R")
            name = name.replace("[", "[R")
            name = name.replace("].R", "]")
            return name

        return name

    def hex_to_dec(self, nif_ver_hex):

        nif_ver_hex_1 = str(int('0x{0:.2}'.format(hex(nif_ver_hex)[2:].zfill(8)), 0))
        nif_ver_hex_2 = str(int('0x{0:.2}'.format(hex(nif_ver_hex)[2:].zfill(8)[2:]), 0))
        nif_ver_hex_3 = str(int('0x{0:.2}'.format(hex(nif_ver_hex)[2:].zfill(8)[4:]), 0))
        nif_ver_hex_4 = str(int('0x{0:.2}'.format(hex(nif_ver_hex)[2:].zfill(8)[6:]), 0))

        nif_ver_dec = str(nif_ver_hex_1 + "." + nif_ver_hex_2 + "." + nif_ver_hex_3 + "." + nif_ver_hex_4)

        return nif_ver_dec

    def dec_to_hex(self, nif_ver_dec):

        dec_split = re.compile(r'\W+')
        dec_split = dec_split.split(nif_ver_dec)

        nif_ver_dec_1, nif_ver_dec_2, nif_ver_dec_3, nif_ver_dec_4 = dec_split
        nif_ver_dec_1 = hex(int(nif_ver_dec_1, 10))[2:].zfill(2)
        nif_ver_dec_2 = hex(int(nif_ver_dec_2, 10))[2:].zfill(2)
        nif_ver_dec_3 = hex(int(nif_ver_dec_3, 10))[2:].zfill(2)
        nif_ver_dec_4 = hex(int(nif_ver_dec_4, 10))[2:].zfill(2)
        nif_ver_hex = int(
            (nif_ver_dec_1 + nif_ver_dec_2 + nif_ver_dec_3 + nif_ver_dec_4), 16)
        return nif_ver_hex

    def get_havok_material(self, material_item, collision_item):
        if self.Nif_Version == '20.2.0.7':
            if self.Nif_User_Version == 12 and self.Nif_User_Version_2 == 83:
                nif_havok_material = NifFormat.SkyrimHavokMaterial._enumkeys[material_item]
                collision_item.skyrim_havok_material = nif_havok_material
            elif self.Nif_User_Version == 11 and self.Nif_User_Version_2 == 34:
                nif_havok_material = NifFormat.Fallout3HavokMaterial._enumkeys[material_item]
                collision_item.fallout3_havok_material = nif_havok_material
        elif self.Nif_Version != 0:
            nif_havok_material = NifFormat.OblivionHavokMaterial._enumkeys[material_item]
            collision_item.oblivion_havok_material = nif_havok_material

        return collision_item

    def set_havok_material(self, niftools_item, collision_item):
        if niftools_item.nif_version == '20.2.0.7':
            if niftools_item.user_version == 12 and niftools_item.user_version_2 == 83:
                nif_havok_material_index = NifFormat.SkyrimHavokMaterial._enumkeys.index(collision_item.skyrim_havok_material)
                nif_havok_material = NifFormat.SkyrimHavokMaterial._enumvalues[nif_havok_material_index]
                nif_havok_col_layer = collision_item.skyrim_layer
            elif niftools_item.user_version == 11 and niftools_item.user_version_2 == 34:
                nif_havok_material_index = NifFormat.Fallout3HavokMaterial._enumkeys.index(collision_item.fallout3_havok_material)
                nif_havok_material = NifFormat.Fallout3HavokMaterial._enumvalues[nif_havok_material_index]
                nif_havok_col_layer = collision_item.fallout3_layer
        elif niftools_item.nif_version:
            nif_havok_material_index = NifFormat.OblivionHavokMaterial._enumkeys.index(collision_item.oblivion_havok_material)
            nif_havok_material = NifFormat.OblivionHavokMaterial._enumvalues[nif_havok_material_index]
            nif_havok_col_layer = collision_item.oblivion_layer

        return nif_havok_material, nif_havok_col_layer

    def get_havok_col_layer(self, layer_item, collision_item):
        if self.Nif_Version == '20.2.0.7':
            if self.Nif_User_Version == 12 and self.Nif_User_Version_2 == 83:
                nif_havok_layer = NifFormat.SkyrimLayer._enumkeys[layer_item]
                collision_item.skyrim_layer = nif_havok_layer
            elif self.Nif_User_Version == 11 and self.Nif_User_Version_2 == 34:
                nif_havok_layer = NifFormat.Fallout3Layer._enumkeys[layer_item]
                collision_item.fallout3_layer = nif_havok_layer
        elif self.Nif_Version != 0:
            nif_havok_layer = NifFormat.OblivionLayer._enumkeys[layer_item]
            collision_item.oblivion_layer = nif_havok_layer

        return collision_item

    def get_extend_from_flags(self, b_fcurve, flags):
        if flags & 6 == 4:  # 0b100
            return b_fcurve
        elif flags & 6 == 0:  # 0b000
            b_fcurve.modifiers.new('CYCLES')
            return b_fcurve

        self.warning(
            "Unsupported cycle mode in nif, using clamped.")
        return bpy.types.FCurve.extrapolation("CONSTANT")

    def get_b_action_interpolation_from_n_action_interpolation(self, n_action_interpolation):
        if n_action_interpolation == NifFormat.KeyType.LINEAR:
            return bpy.types.Keyframe.interpolation("LINEAR")
        elif n_action_interpolation == NifFormat.KeyType.QUADRATIC:
            return bpy.types.Keyframe.interpolation("BEZIER")
        elif n_action_interpolation == 0:
            # guessing, not documented in nif.xml
            return bpy.types.Keyframe.interpolation("CONSTANT")

        self.warning("Unsupported interpolation mode in nif, using quadratic/bezier.")
        return bpy.types.Keyframe.interpolation("BEZIER")

    def get_n_action_interpolation_from_b_action_interpolation(self, b_action_interpolation):
        if b_action_interpolation == bpy.types.Keyframe.interpolation("LINEAR"):
            return NifFormat.KeyType.LINEAR
        elif b_action_interpolation == bpy.types.Keyframe.interpolation("BEZIER"):
            return NifFormat.KeyType.QUADRATIC
        elif b_action_interpolation == bpy.types.Keyframe.interpolation("CONSTANT"):
            return NifFormat.KeyType.CONSTANT
        self.warning("Unsupported interpolation mode in blend, using quadratic/bezier.")
        return NifFormat.KeyType.QUADRATIC

    def get_n_apply_mode_from_b_blend_type(self, b_blend_type):
        if b_blend_type == "LIGHTEN":
            return NifFormat.ApplyMode.HILIGHT
        elif b_blend_type == "MULTIPLY":
            return NifFormat.ApplyMode.HILIGHT2
        elif b_blend_type == "MIX":
            return NifFormat.ApplyMode.MODULATE
        self.warning("Unsupported blend type (%s) in material, using apply mode MODULATE"
                     % b_blend_type
                     )
        return NifFormat.ApplyMode.MODULATE
