from typing import Any, Optional
import bpy, mathutils, bmesh
import numpy as np

from .transfer_map import TransferMap

# Kitsu has lots of utilities for transferring data between objects
# I stole everything below from Kitsu :)
# projects.blender.org/studio/blender-studio-pipeline/src/branch/main/scripts-blender/addons/asset_pipeline/docs/production_config_heist/task_layers.py

def transfer_new_modifiers(obj_source: bpy.types.Object, obj_target: bpy.types.Object):
	for i, mod in enumerate(obj_source.modifiers):
		if mod.name in [m.name for m in obj_target.modifiers]:
			continue
		mod_new = obj_target.modifiers.new(mod.name, mod.type)
		# Sort new modifier at correct index (default to beginning of the stack)
		idx = 0
		if i > 0:
			name_prev = obj_source.modifiers[i - 1].name
			for target_mod_i, target_mod in enumerate(obj_target.modifiers):
				if target_mod.name == name_prev:
					idx = target_mod_i + 1
		bpy.ops.object.modifier_move_to_index({"object": obj_target}, modifier=mod_new.name, index=idx)

def remap_new_modifiers(obj: bpy.types.Object, map: TransferMap):
	for i, mod_source in enumerate(obj.modifiers):
		for prop in [p.identifier for p in mod_source.bl_rna.properties if not p.is_readonly]:
			value = getattr(mod_source, prop)
			if type(value) == bpy.types.Object and value in map.matching_objs_target:
				# Remap modifiers to transferred objects if possible
				value = map.matching_objs_target[value]
			setattr(mod_source, prop, value)

def remap_modifiers(obj_source: bpy.types.Object, obj_target: bpy.types.Object, map: TransferMap):
	for i, mod_source in enumerate(obj_source.modifiers):
		mod_target = obj_target.modifiers.get(mod_source.name)
		if not mod_target:
			continue
		for prop in [p.identifier for p in mod_source.bl_rna.properties if not p.is_readonly]:
			value = getattr(mod_source, prop)
			if type(value) == bpy.types.Object and value in map.matching_objs_target:
				# Remap modifiers to transferred objects if possible
				value = map.matching_objs_target[value]
			setattr(mod_target, prop, value)

def rebind_modifiers(obj_target: bpy.types.Object):
	"""Rebinds corrective smooth, surface deform and mesh deform modifiers"""
	for mod in obj_target.modifiers:
		if mod.type == "SURFACE_DEFORM":
			if not mod.is_bound:
				continue
			for i in range(2):
				bpy.ops.object.surfacedeform_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)
		elif mod.type == "MESH_DEFORM":
			if not mod.is_bound:
				continue
			for i in range(2):
				bpy.ops.object.meshdeform_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)
		elif mod.type == "CORRECTIVE_SMOOTH":
			if not mod.is_bind:
				continue
			for i in range(2):
				bpy.ops.object.correctivesmooth_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)

def match_topology(a: bpy.types.Object, b: bpy.types.Object) -> bool:
	"""Checks if two objects have matching topology (efficiency over exactness)"""
	if a.type != b.type:
		return False
	if a.type == 'MESH':
		if len(a.data.vertices) != len(b.data.vertices):
			return False
		if len(a.data.edges) != len(b.data.edges):
			return False
		if len(a.data.polygons) != len(b.data.polygons):
			return False
		for e1, e2 in zip(a.data.edges, b.data.edges):
			for v1, v2 in zip(e1.vertices, e2.vertices):
				if v1 != v2:
					return False
		return True
	elif a.type == 'CURVE':
		if len(a.data.splines) != len(b.data.splines):
			return False
		for spline1, spline2 in zip(a.data.splines, b.data.splines):
			if len(spline1.points) != len(spline2.points):
				return False
		return True
	return False

def copy_transform(source_ob: bpy.types.Object, target_ob: bpy.types.Object):
	"""Copy source transform to target transform in world space"""
	con_vis = []
	for con in target_ob.constraints:
		con_vis += [con.enabled]
		con.enabled = False
	for con in source_ob.constraints:
		con.enabled = False

	target_ob.matrix_world = source_ob.matrix_world
	for con, vis in zip(target_ob.constraints, con_vis):
		con.enabled = vis

def copy_parenting(source_ob: bpy.types.Object, target_ob: bpy.types.Object) -> None:
	"""Copy parenting data from one object to another."""
	target_ob.parent = source_ob.parent
	target_ob.parent_type = source_ob.parent_type
	target_ob.parent_bone = source_ob.parent_bone
	target_ob.matrix_parent_inverse = source_ob.matrix_parent_inverse.copy()

_invalid_keys: "set[str]" = {"group", "is_valid", "rna_type", "bl_rna"}

def copy_attributes(a: Any, b: Any) -> None:
	keys = dir(a)
	for key in keys:
		if key.startswith("_") or key.startswith("error_") or key in _invalid_keys:
			continue
		try:
			setattr(b, key, getattr(a, key))
		except AttributeError:
			pass

def copy_driver(
	source_fcurve: bpy.types.FCurve,
	target_obj: bpy.types.Object,
	data_path: Optional[str] = None,
	index: Optional[str] = None,
) -> bpy.types.FCurve:
	if not data_path:
		data_path = source_fcurve.data_path

	new_fc = None
	try:
		if index:
			new_fc = target_obj.driver_add(data_path, index)
		else:
			new_fc = target_obj.driver_add(data_path)
	except:
		print(f"ERROR: Couldn't copy driver {source_fcurve.data_path} to {target_obj.name}")
		return

	copy_attributes(source_fcurve, new_fc)
	copy_attributes(source_fcurve.driver, new_fc.driver)

	# Remove default modifiers, variables, etc.
	for m in new_fc.modifiers:
		new_fc.modifiers.remove(m)
	for v in new_fc.driver.variables:
		new_fc.driver.variables.remove(v)

	# Copy modifiers
	for m1 in source_fcurve.modifiers:
		m2 = new_fc.modifiers.new(type=m1.type)
		copy_attributes(m1, m2)

	# Copy variables
	for v1 in source_fcurve.driver.variables:
		v2 = new_fc.driver.variables.new()
		copy_attributes(v1, v2)
		for i in range(len(v1.targets)):
			copy_attributes(v1.targets[i], v2.targets[i])

	return new_fc

def copy_drivers(source_ob: bpy.types.Object, target_ob: bpy.types.Object) -> None:
	"""Copy all drivers from one object to another."""
	if not hasattr(source_ob, "animation_data") or not source_ob.animation_data:
		return

	for fc in source_ob.animation_data.drivers:
		copy_driver(fc, target_ob)

def copy_rigging_object_data(
	source_ob: bpy.types.Object, target_ob: bpy.types.Object
) -> None:
	"""Copy all object data that could be relevant to rigging."""
	# TODO: Object constraints, if needed.
	copy_drivers(source_ob, target_ob)
	copy_parenting(source_ob, target_ob)
	# HACK: For some reason Armature constraints on grooming objects lose their target when updating? Very strange...
	for c in target_ob.constraints:
		if c.type == "ARMATURE":
			for t in c.targets:
				if t.target == None:
					t.target = target_ob.parent

def edge_data_split(edge, data_layer, data_suffix: str):
	for vert in edge.verts:
		vals = []
		for loop in vert.link_loops:
			loops_edge_vert = set([loop for f in edge.link_faces for loop in f.loops])
			if loop not in loops_edge_vert:
				continue
			dat = data_layer[loop.index]
			element = list(getattr(dat,data_suffix))
			if not vals:
				vals.append(element)
			elif not vals[0] == element:
				vals.append(element)
		if len(vals) > 1:
			return True
	return False

def closest_edge_on_face_to_line(face, p1, p2, skip_edges=None):
	""" Returns edge of a face which is closest to line."""
	for edge in face.edges:
		if skip_edges:
			if edge in skip_edges:
				continue
		res = mathutils.geometry.intersect_line_line(p1, p2, * [edge.verts[i].co for i in range(2)])
		if not res:
			continue
		(p_traversal, p_edge) = res
		frac_1 = (edge.verts[1].co - edge.verts[0].co).dot(p_edge - edge.verts[0].co) / (edge.verts[1].co - edge.verts[0].co).length ** 2.
		frac_2 = (p2 - p1).dot(p_traversal - p1) / (p2 - p1).length ** 2.
		if (frac_1 >= 0 and frac_1 <= 1) and (frac_2 >= 0 and frac_2 <= 1):
			return edge
	return None

def interpolate_data_from_face(bm_source, tris_dict, face, p, data_layer_source, data_suffix = ''):
	""" Returns interpolated value of a data layer within a face closest to a point."""
	(tri, point) = closest_tri_on_face(tris_dict, face, p)
	if not tri:
		return None
	weights = mathutils.interpolate.poly_3d_calc([tri[i].vert.co for i in range(3)], point)

	if not data_suffix:
		cols_weighted = [weights[i] * np.array(data_layer_source[tri[i].index]) for i in range(3)]
		col = sum(np.array(cols_weighted))
	else:
		cols_weighted = [weights[i] * np.array(getattr(data_layer_source[tri[i].index], data_suffix)) for i in range(3)]
		col = sum(np.array(cols_weighted))
	return col

def closest_face_to_point(bm_source, p_target, bvh_tree = None):
	if not bvh_tree:
		bvh_tree = mathutils.bvhtree.BVHTree.FromBMesh(bm_source)
	(loc, norm, index, distance) = bvh_tree.find_nearest(p_target)
	return bm_source.faces[index]

def tris_per_face(bm_source):
	tris_source = bm_source.calc_loop_triangles()
	tris_dict = dict()
	for face in bm_source.faces:
		tris_face = []
		for i in range(len(tris_source))[::-1]:
			if tris_source[i][0] in face.loops:
				tris_face.append(tris_source.pop(i))
		tris_dict[face] = tris_face
	return tris_dict

def closest_tri_on_face(tris_dict, face, p):
	points = []
	dist = []
	tris = []
	for tri in tris_dict[face]:
		point = mathutils.geometry.closest_point_on_tri(p, *[tri[i].vert.co for i in range(3)])
		tris.append(tri)
		points.append(point)
		dist.append((point - p).length)
	min_idx = np.argmin(np.array(dist))
	point = points[min_idx]
	tri = tris[min_idx]
	return (tri, point)

def transfer_corner_data(obj_source, obj_target, data_layer_source, data_layer_target, data_suffix = ''):
	"""
	Transfers interpolated face corner data from data layer of a source object to data layer of a
	target object, while approximately preserving data seams (e.g. necessary for UV Maps).
	The transfer is face interpolated per target corner within the source face that is closest
	to the target corner point and does not have any data seams on the way back to the
	source face that is closest to the target face's center.
	"""
	bm_source = bmesh.new()
	bm_source.from_mesh(obj_source.data)
	bm_source.faces.ensure_lookup_table()
	bm_target = bmesh.new()
	bm_target.from_mesh(obj_target.data)
	bm_target.faces.ensure_lookup_table()

	bvh_tree = mathutils.bvhtree.BVHTree.FromBMesh(bm_source)
	tris_dict = tris_per_face(bm_source)

	for face_target in bm_target.faces:
		face_target_center = face_target.calc_center_median()

		face_source = closest_face_to_point(bm_source, face_target_center, bvh_tree)

		for corner_target in face_target.loops:
			# Find nearest face on target compared to face that loop belongs to
			p = corner_target.vert.co

			face_source_closest = closest_face_to_point(bm_source, p, bvh_tree)
			enclosed = face_source_closest is face_source
			face_source_int = face_source
			if not enclosed:
				# Traverse faces between point and face center
				traversed_faces = set()
				traversed_edges = set()
				while (face_source_int is not face_source_closest):
					traversed_faces.add(face_source_int)
					edge = closest_edge_on_face_to_line(face_source_int, face_target_center, p, skip_edges = traversed_edges)
					if edge == None:
						break
					if len(edge.link_faces) != 2:
						break
					traversed_edges.add(edge)

					split = edge_data_split(edge, data_layer_source, data_suffix)
					if split:
						break

					# Set new source face to other face belonging to edge
					face_source_int = edge.link_faces[1] if edge.link_faces[1] is not face_source_int else edge.link_faces[0]

					# Avoid looping behaviour
					if face_source_int in traversed_faces:
						face_source_int = face_source
						break

			# Interpolate data from selected face
			col = interpolate_data_from_face(bm_source, tris_dict, face_source_int, p, data_layer_source, data_suffix)
			if col is None:
				continue
			if not data_suffix:
				data_layer_target.data[corner_target.index] = col
			else:
				setattr(data_layer_target[corner_target.index], data_suffix, list(col))
	return

def transfer_shapekeys_proximity(obj_source, obj_target) -> None:
	"""Transfers shapekeys from one object to another based on the mesh proximity with face interpolation."""
	# Copy shapekey layout
	if not obj_source.data.shape_keys:
		return
	for sk_source in obj_source.data.shape_keys.key_blocks:
		if obj_target.data.shape_keys:
			sk_target = obj_target.data.shape_keys.key_blocks.get(sk_source.name)
			if sk_target:
				continue
		sk_target = obj_target.shape_key_add()
		sk_target.name = sk_source.name
	for sk_target in obj_target.data.shape_keys.key_blocks:
		sk_source = obj_source.data.shape_keys.key_blocks[sk_target.name]
		sk_target.vertex_group = sk_source.vertex_group
		sk_target.relative_key = obj_target.data.shape_keys.key_blocks[sk_source.relative_key.name]

	bm_source = bmesh.new()
	bm_source.from_mesh(obj_source.data)
	bm_source.faces.ensure_lookup_table()

	bvh_tree = mathutils.bvhtree.BVHTree.FromBMesh(bm_source)

	tris_dict = tris_per_face(bm_source)

	for i, vert in enumerate(obj_target.data.vertices):
		p = vert.co
		face = closest_face_to_point(bm_source, p, bvh_tree)

		(tri, point) = closest_tri_on_face(tris_dict, face, p)
		if not tri:
			continue
		weights = mathutils.interpolate.poly_3d_calc([tri[i].vert.co for i in range(3)], point)

		for sk_target in obj_target.data.shape_keys.key_blocks:
			sk_source = obj_source.data.shape_keys.key_blocks.get(sk_target.name)

			vals_weighted = [weights[i] * (sk_source.data[tri[i].vert.index].co-obj_source.data.vertices[tri[i].vert.index].co) for i in range(3)]
			val = mathutils.Vector(sum(np.array(vals_weighted)))
			sk_target.data[i].co = vert.co + val

def transfer_surfacing(obj_source: bpy.types.Object, obj_target: bpy.types.Object, topo_match: bool):
	"""Transfers materials, UVs, seams, vertex colors and face data"""
	# Wipe our material slots
	while len(obj_target.material_slots) > len(obj_source.material_slots):
		obj_target.active_material_index = len(obj_source.material_slots)
		bpy.ops.object.material_slot_remove({"object": obj_target})

	# Transfer material slots
	for idx in range(len(obj_source.material_slots)):
		if idx >= len(obj_target.material_slots):
			bpy.ops.object.material_slot_add({"object": obj_target})
		obj_target.material_slots[idx].link = obj_source.material_slots[idx].link
		obj_target.material_slots[idx].material = obj_source.material_slots[idx].material

	# Transfer active material slot
	obj_target.active_material_index = obj_source.active_material_index

	# Transfer material slot assignments for curve
	if obj_target.type == "CURVE":
		if not obj_target.data.splines:
			print(f"WARNING: Curve object '{obj_target.name}' has empty object data")
			return
		for spl_to, spl_from in zip(obj_target.data.splines, obj_source.data.splines):
			spl_to.material_index = spl_from.material_index

	# Rest of the code applies to meshes only
	if obj_target.type != "MESH":
		return

	if not obj_target.data.vertices:
		print(f"WARNING: Mesh object '{obj_target.name}' has empty object data")
		return
	
	# Placeholder for transfer source object
	obj_source_original: bpy.types.Object = None

	# Transfer face data
	if topo_match:
		for pol_to, pol_from in zip(obj_target.data.polygons, obj_source.data.polygons):
			pol_to.material_index = pol_from.material_index
			pol_to.use_smooth = pol_from.use_smooth
	else:
		# Generate new transfer source object, required to fix raycasting issues
		obj_source_original = bpy.data.objects.new(f"{obj_source.name}.original", obj_source.data)
		bpy.context.scene.collection.objects.link(obj_source_original)

		depsgraph = bpy.context.evaluated_depsgraph_get()
		obj_source_eval = obj_source_original.evaluated_get(depsgraph)
		for pol_target in obj_target.data.polygons:
			# This breaks unless the object is in the same scene, hence the transfer object
			(hit, loc, norm, face_index) = obj_source_eval.closest_point_on_mesh(pol_target.center)
			pol_source = obj_source_eval.data.polygons[face_index]
			pol_target.material_index = pol_source.material_index
			pol_target.use_smooth = pol_source.use_smooth

	# Transfer UV Seams
	if topo_match:
		for edge_from, edge_to in zip(obj_source.data.edges, obj_target.data.edges):
			edge_to.use_seam = edge_from.use_seam
	else:
		bpy.ops.object.data_transfer(
			{
				"object": obj_source_original,
				"active_object": obj_source_original,
				"selected_editable_objects": [obj_target],
			},
			data_type="SEAM",
			edge_mapping="NEAREST",
			mix_mode="REPLACE",
		)

	# Wipe our UV layers
	for _ in range(len(obj_target.data.uv_layers)):
		obj_target.data.uv_layers.remove(obj_target.data.uv_layers[0])

	# Transfer UV layers
	if topo_match:
		for uv_from in obj_source.data.uv_layers:
			uv_to = obj_target.data.uv_layers.new(name=uv_from.name, do_init=False)
			for loop in obj_target.data.loops:
				uv_to.data[loop.index].uv = uv_from.data[loop.index].uv
	else:
		for uv_from in obj_source.data.uv_layers:
			uv_to = obj_target.data.uv_layers.new(name=uv_from.name, do_init=False)
			transfer_corner_data(obj_source, obj_target, uv_from.data, uv_to.data, data_suffix="uv")

	# Make sure correct layer is active
	for uv_l in obj_source.data.uv_layers:
		if uv_l.active_render:
			obj_target.data.uv_layers[uv_l.name].active_render = True
			break

	# Wipe our vertex colors
	for _ in range(len(obj_target.data.vertex_colors)):
		obj_target.data.vertex_colors.remove(obj_target.data.vertex_colors[0])

	# Transfer vertex colors
	if topo_match:
		for vcol_from in obj_source.data.vertex_colors:
			vcol_to = obj_target.data.vertex_colors.new(name=vcol_from.name, do_init=False)
			for loop in obj_target.data.loops:
				vcol_to.data[loop.index].color = vcol_from.data[loop.index].color
	else:
		for vcol_from in obj_source.data.vertex_colors:
			vcol_to = obj_target.data.vertex_colors.new(name=vcol_from.name, do_init=False)
			transfer_corner_data(obj_source, obj_target, vcol_from.data, vcol_to.data, data_suffix="color")

	# Set 'PREVIEW' vertex color layer as active
	for idx, vcol in enumerate(obj_target.data.vertex_colors):
		if vcol.name == "PREVIEW":
			obj_target.data.vertex_colors.active_index = idx
			break

	# Set 'Baking' or 'UVMap' UV layer as active
	for idx, uvlayer in enumerate(obj_target.data.uv_layers):
		if uvlayer.name == "Baking":
			obj_target.data.uv_layers.active_index = idx
			break
		elif uvlayer.name == "UVMap":
			obj_target.data.uv_layers.active_index = idx

	# Select preview texture as active if found
	for mslot in obj_target.material_slots:
		if not mslot.material or not mslot.material.node_tree:
			continue
		for node in mslot.material.node_tree.nodes:
			if not node.type == "TEX_IMAGE" or not node.image:
				continue
			if "preview" in node.image.name:
				mslot.material.node_tree.nodes.active = node
				break
	
	if obj_source_original:
		bpy.data.objects.remove(obj_source_original)