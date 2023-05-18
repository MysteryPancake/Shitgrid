from typing import Any, Optional
import bpy, mathutils, bmesh
import numpy as np

# Kitsu has lots of utilities for transferring data between objects
# I stole everything below from their codebase :)
# projects.blender.org/studio/blender-studio-pipeline/src/branch/main/scripts-blender/addons/asset_pipeline/docs/production_config_heist/task_layers.py

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
	"""Transfers world transform data between objects"""
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

def copy_attributes(a: Any, b: Any) -> None:
	keys = dir(a)
	for key in keys:
		if (
			not key.startswith("_")
			and not key.startswith("error_")
			and key != "group"
			and key != "is_valid"
			and key != "rna_type"
			and key != "bl_rna"
		):
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
		print(f"Couldn't copy driver {source_fcurve.data_path} to {target_obj.name}")
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
			#find nearest face on target compared to face that loop belongs to
			p = corner_target.vert.co

			face_source_closest = closest_face_to_point(bm_source, p, bvh_tree)
			enclosed = face_source_closest is face_source
			face_source_int = face_source
			if not enclosed:
				# traverse faces between point and face center
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

					# set new source face to other face belonging to edge
					face_source_int = edge.link_faces[1] if edge.link_faces[1] is not face_source_int else edge.link_faces[0]

					# avoid looping behaviour
					if face_source_int in traversed_faces:
						face_source_int = face_source
						break

			# interpolate data from selected face
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