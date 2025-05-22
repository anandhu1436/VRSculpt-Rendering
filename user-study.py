import os
import bpy
import numpy as np
import blendertoolbox as bt
from mathutils import Vector
from collections import defaultdict

# === Utility Functions ===

def translate(vertices, translation):
    return vertices + translation

def rotate(vertices, rotation):
    rx, ry, rz = np.radians(rotation)
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    return np.dot(vertices, (Rz @ Ry @ Rx).T)

def read_lines_from_obj(file_path):
    vertices = []
    lines = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split()
            if not parts: continue
            if parts[0] == 'v':
                vertices.append([float(p) for p in parts[1:4]])
            elif parts[0] == 'l':
                lines.append([int(p) - 1 for p in parts[1:]])
    return np.array(vertices), lines

def get_bounding_box_diagonal(obj):
    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_corner = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    return (max_corner - min_corner).length

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def read_lines_from_obj_grouped(file_path):
    vertices = []
    groups = []
    current_group = []

    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == 'v':
                vertices.append([float(p) for p in parts[1:4]])
                if current_group is not None:
                    current_group.append(len(vertices) - 1)
            elif parts[0] == 'g':
                if current_group:
                    groups.append(current_group)
                current_group = []
    
    if current_group:
        groups.append(current_group)

    # Generate line segments by connecting consecutive vertices in each group
    lines = []
    for group in groups:
        if len(group) < 2:
            continue
        lines.extend([[group[i], group[i + 1]] for i in range(len(group) - 1)])

    return np.array(vertices), lines

def create_two_sided_material(name="TwoSidedRibbon", front_color=(0, 0.2, 1, 1), back_color=(0.8, 0.1, 0.1, 1)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)

    # Add new nodes
    output = nodes.new(type='ShaderNodeOutputMaterial')
    mix_shader = nodes.new(type='ShaderNodeMixShader')
    front_bsdf = nodes.new(type='ShaderNodeBsdfDiffuse')
    back_bsdf = nodes.new(type='ShaderNodeBsdfDiffuse')
    geometry = nodes.new(type='ShaderNodeNewGeometry')

    # Set colors
    front_bsdf.inputs['Color'].default_value = back_color
    back_bsdf.inputs['Color'].default_value = front_color

    # Connect nodes
    links.new(geometry.outputs['Backfacing'], mix_shader.inputs['Fac'])
    links.new(front_bsdf.outputs['BSDF'], mix_shader.inputs[1])
    links.new(back_bsdf.outputs['BSDF'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])

    return mat


# === Parameters ===

root_folder = "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/VRSculpt-Rendering/user-study/Zhonghan"
imgRes_x, imgRes_y = 3000, 3000

# === Group files by prefix (before first underscore) ===

mesh_groups = defaultdict(list)

for f in sorted(os.listdir(root_folder)):
    if not (f.endswith('.obj') or f.endswith('.ply')):
        continue
    name_parts = f.split('_')
    group_key = name_parts[0]  # Group by prefix like 'model1'
    mesh_groups[group_key].append(f)

# === Process each group ===

for group_key, file_list in mesh_groups.items():
    print(f"\n--- Processing group: {group_key} ---")
    clear_scene()
    bt.blenderInit(imgRes_x, imgRes_y, numSamples=100, exposure=1.5)

    mesh_paths = []
    mesh_types = []

    for f in file_list:
        f_path = os.path.join(root_folder, f)
        fname_lower = f.lower()
        # if "marching" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("marching")
        # elif "uniform" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("uniform")
        # elif "circumspheres.obj" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("spheres")
        if "final" in fname_lower:
            mesh_paths.append(f_path)
            mesh_types.append("final")
        elif "strokes" in fname_lower:
            mesh_paths.append(f_path)
            mesh_types.append("ribbon")
        # elif "points.obj" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("lines")
        # elif "xyz" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("ballmerge")
        # elif "surface" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("vipss")
        # elif "poisson" in fname_lower:
        #     mesh_paths.append(f_path)
        #     mesh_types.append("poisson")
        

    if not mesh_paths:
        print(f"No valid mesh types found for group {group_key}")
        continue

    # === Reference Bounding Box ===
    ref_mesh = bt.readMesh(mesh_paths[-1], (0, 0, 0), (0, 0, 0), (1, 1, 1))
    ref_width = get_bounding_box_diagonal(ref_mesh)
    ref_bbox = [ref_mesh.matrix_world @ Vector(corner) for corner in ref_mesh.bound_box]
    ref_y_center = sum(v.y for v in ref_bbox) / 8
    ref_z_center = sum(v.z for v in ref_bbox) / 8
    bpy.data.objects.remove(ref_mesh, do_unlink=True)

    all_meshes = []
    mesh_paths.append(mesh_paths[0])  # Append the first mesh path for the reference
    mesh_types.append("ribbon-final")  # Append the first mesh type for the reference
    for i, (path, mtype) in enumerate(zip(mesh_paths, mesh_types)):
        x_offset = i * ref_width * 1.5
        translation = np.array([x_offset, -ref_y_center, 0])
        rotation = (0, 0, 0)

        if mtype == 'lines':
            pass
            # vertices, lines = read_lines_from_obj_grouped(path)
            # translated = translate(vertices, translation)
            # rotated = rotate(translated, rotation)
            # p1List = np.array([rotated[line[0]] for line in lines])
            # p2List = np.array([rotated[line[1]] for line in lines])
            # colorList = np.tile([0.1, 0.1, 0.1, 1], (len(p1List), 1))
            # lines_obj = bt.drawLines(p1List, p2List, 0.001 * ref_width, colorList)
            # bpy.ops.object.shade_smooth()
            # all_meshes.append(lines_obj)



        elif mtype == 'ribbon':
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            edgeThickness = 0.001
            edgeColor = bt.colorObj((0,0,0,1), 0.5, 1.0, 1.0, 0.0, 0.0)
            meshRGBA = (0, 0.7, 1, 1)
            AOStrength = 1.0
            bt.setMat_edge(mesh, edgeThickness, edgeColor, meshRGBA, AOStrength)
            bpy.ops.object.shade_smooth()

            # Add two-sided material
            mat = create_two_sided_material()
            if mesh.data.materials:
                mesh.data.materials[0] = mat
            else:
                mesh.data.materials.append(mat)

            all_meshes.append(mesh)
        elif mtype == 'spheres':
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj((0.1, 0.1, 0.8, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_balloon(mesh, meshColor, 1)
            bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

        elif mtype == 'ballmerge' or mtype == 'vipss' or mtype == 'poisson':
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj(bt.derekBlue, 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_balloon(mesh, meshColor, 1)
            # bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

        elif mtype == 'marching':
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj((0.0, 0.5, 0.8, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_balloon(mesh, meshColor, 1)
            bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

            wireframe_mesh = mesh.copy()

            wireframe_mesh.data = mesh.data.copy()
            bpy.context.collection.objects.link(wireframe_mesh)

            # Add Wireframe modifier
            modifier = wireframe_mesh.modifiers.new(name="Wireframe", type='WIREFRAME')
            modifier.thickness = 0.0003 * ref_width  # Adjust thickness as needed
            modifier.use_replace = False  # So mesh is shown both solid and wireframe

            # Create black material for wireframe
            wire_mat = bpy.data.materials.new(name="WireMaterial")
            wire_mat.use_nodes = True

            # Ensure the material renders as opaque
            wire_mat.blend_method = 'OPAQUE'
            wire_mat.shadow_method = 'OPAQUE'

            # Set the BSDF base color to solid black with full alpha
            bsdf = wire_mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (1, 0, 0, 1)  # Fully opaque black
                bsdf.inputs["Roughness"].default_value = 0.5


            # Assign material to wireframe mesh
            wireframe_mesh.data.materials.append(wire_mat)

        elif mtype == 'uniform':
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj((0.8, 0.5, 0.5, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_balloon(mesh, meshColor, 1)
            bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

            wireframe_mesh = mesh.copy()
            wireframe_mesh.data = mesh.data.copy()
            bpy.context.collection.objects.link(wireframe_mesh)

            # Add Wireframe modifier
            modifier = wireframe_mesh.modifiers.new(name="Wireframe", type='WIREFRAME')
            modifier.thickness = 0.001 * ref_width  # Adjust thickness as needed
            modifier.use_replace = False  # So mesh is shown both solid and wireframe

            # Create black material for wireframe
            wire_mat = bpy.data.materials.new(name="WireMaterial")
            wire_mat.use_nodes = True

            # Ensure the material renders as opaque
            wire_mat.blend_method = 'OPAQUE'
            wire_mat.shadow_method = 'OPAQUE'

            # Set the BSDF base color to solid black with full alpha
            bsdf = wire_mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (1, 0, 0, 1)  # Fully opaque black
                bsdf.inputs["Roughness"].default_value = 0.5


            # Assign material to wireframe mesh
            wireframe_mesh.data.materials.append(wire_mat)

        elif mtype == 'ribbon-final':
            final_mesh_path = None
            for f_sub, t_sub in zip(mesh_paths, mesh_types):
                if t_sub == 'final':
                    final_mesh_path = f_sub
                if t_sub == 'ribbon':
                    ribbon_mesh_path = f_sub
                    
            if final_mesh_path is None or ribbon_mesh_path is None:
                print(f"Missing final or ribbon mesh for group {group_key}")
                continue

            mesh = bt.readMesh(ribbon_mesh_path, translation, rotation, (1, 1, 1))
            edgeThickness = 0.001
            edgeColor = bt.colorObj((0,0,0,1), 0.5, 1.0, 1.0, 0.0, 0.0)
            meshRGBA = (0, 0.7, 1, 1)
            AOStrength = 1.0
            bt.setMat_edge(mesh, edgeThickness, edgeColor, meshRGBA, AOStrength)
            bpy.ops.object.shade_smooth()

            # Add two-sided material
            mat = create_two_sided_material()
            if mesh.data.materials:
                mesh.data.materials[0] = mat
            else:
                mesh.data.materials.append(mat)

            all_meshes.append(mesh)

             # === Also add corresponding 'final' mesh for joint rendering (not added to all_meshes) ===
            

            if final_mesh_path:
                final_translation = translation.copy()
                final_rotation = rotation
                extra_final_obj = bt.readMesh(final_mesh_path, final_translation, rotation, (1, 1, 1))
                extra_final_color = bt.colorObj((1.0, 0.55, 0.0, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
                bt.setMat_balloon(extra_final_obj, extra_final_color, 1)
                bpy.ops.object.shade_smooth()


        else:
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj((1.0, 0.55, 0.0, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_balloon(mesh, meshColor, 1)
            bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

    # === Lighting ===
    bt.setLight_sun((6, -30, -155), 2, 0.3)
    bt.setLight_ambient((0.1, 0.1, 0.1, 1))
    bt.shadowThreshold(alphaThreshold=0.025, interpolationMode='CARDINAL')

    # === Render with Camera per Object ===
    output_dir = os.path.join(root_folder, 'renders', group_key)
    os.makedirs(output_dir, exist_ok=True)

    for i, mesh in enumerate(all_meshes):


        x_pos = i * ref_width * 1.5
        camLocation = (x_pos, 0, 2 * ref_width)
        lookAtLocation = (x_pos, 0, 0)
        cam = bt.setCamera(camLocation, lookAtLocation, focalLength=45)
        cam.name = mesh_types[i]  # ← Rename the camera to match the mesh type


        # if mesh_types[i] == 'ribbon':
            # Render only lines
            # img_path_lines_only = os.path.join(output_dir, f"render_ribbon_only.png")
            # bt.renderImage(img_path_lines_only, cam)

            # Render lines + extra final mesh
            # if 'extra_final_obj' in locals() and extra_final_obj:
            #     extra_final_obj.hide_render = False
            #     img_path_lines_plus_final = os.path.join(output_dir, f"render_ribbon_plus_final.png")
                # bt.renderImage(img_path_lines_plus_final, cam)
                # extra_final_obj.hide_render = True  # Re-hide to be safe

        # else:
        img_path = os.path.join(output_dir, f"render_{mesh_types[i]}.png")
        bt.renderImage(img_path, cam)


    # === Save Blender File ===
    blend_file = os.path.join(output_dir, f"{group_key}_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_file)

