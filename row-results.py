import os
import bpy
import numpy as np
import blendertoolbox as bt
from mathutils import Vector

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

# === Parameters ===

root_folder = "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/dataset/flowrep"
imgRes_x, imgRes_y = 1000, 1000

# === Loop over all subfolders ===
for subfolder in sorted(os.listdir(root_folder)):
    folder_path = os.path.join(root_folder, subfolder)
    if not os.path.isdir(folder_path):
        continue

    print(f"\n--- Processing: {subfolder} ---")

    # === Start a New Blender Scene ===
    clear_scene()
    bt.blenderInit(imgRes_x, imgRes_y, numSamples=100, exposure=1.5)

    # === Collect Mesh Files ===
    mesh_paths = []
    mesh_types = []

    for f in os.listdir(folder_path):
        if not f.endswith(".obj"):
            continue
        f_path = os.path.join(folder_path, f)
        if "network.obj" in f:
            mesh_paths.append(f_path)
            mesh_types.append("lines")
        elif "marching" in f:
            mesh_paths.append(f_path)
            mesh_types.append("marching")
        elif "final" in f:
            mesh_paths.append(f_path)
            mesh_types.append("final")
        elif "spheres" in f:
            mesh_paths.append(f_path)
            mesh_types.append("spheres")

    if not mesh_paths:
        print(f"No meshes found in {folder_path}")
        continue

    # === Reference Bounding Box ===
    ref_mesh = bt.readMesh(mesh_paths[-1], (0, 0, 0), (0, 0, 0), (1, 1, 1))
    ref_width = get_bounding_box_diagonal(ref_mesh)
    bpy.data.objects.remove(ref_mesh, do_unlink=True)

    all_meshes = []

    for i, (path, mtype) in enumerate(zip(mesh_paths, mesh_types)):
        x_offset = i * ref_width * 1.5
        translation = np.array([x_offset, 0.0, 0.0])
        rotation = (0, 0, 0)

        if mtype == 'lines':
            vertices, lines = read_lines_from_obj(path)
            translated = translate(vertices, translation)
            rotated = rotate(translated, rotation)
            p1List = np.array([rotated[line[0]] for line in lines])
            p2List = np.array([rotated[line[1]] for line in lines])
            colorList = np.tile([0.1, 0.1, 0.1, 1], (len(p1List), 1))
            bt.drawLines(p1List, p2List, 0.01 * ref_width, colorList)
            all_meshes.append(None)

        elif mtype == 'spheres':
            data = np.loadtxt(path)
            centers = data[:, :3]
            radii = data[:, 3]
            translated = translate(centers, translation)
            rotated = rotate(translated, rotation)
            ptColor = bt.colorObj([1.0, 0.55, 0.0, 1.0], 0.5, 1.0, 1.0, 0.0, 0.0)
            for center, radius in zip(rotated, radii):
                bt.drawSphere(radius, ptColor, center)
            all_meshes.append(None)

        else:
            mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))
            meshColor = bt.colorObj((1.0, 0.55, 0.0, 1), 0.5, 1.0, 1.0, 0.0, 2.0)
            bt.setMat_plastic(mesh, meshColor)
            bpy.ops.object.shade_smooth()
            all_meshes.append(mesh)

    # === Lighting ===
    bt.setLight_sun((6, -30, -155), 2, 0.3)
    bt.setLight_ambient((0.1, 0.1, 0.1, 1))
    bt.shadowThreshold(alphaThreshold=0.025, interpolationMode='CARDINAL')

    # === Render with Camera per Object ===
    output_dir = os.path.join(folder_path, 'renders')
    os.makedirs(output_dir, exist_ok=True)

    for i, mesh in enumerate(all_meshes):
        x_pos = i * ref_width * 1.5
        camLocation = (x_pos, 0, 2 * ref_width)
        lookAtLocation = (x_pos, 0, 0)
        cam = bt.setCamera(camLocation, lookAtLocation, focalLength=45)
        img_path = os.path.join(output_dir, f"render_{mesh_types[i]}.png")
        bt.renderImage(img_path, cam)

    # === Save Blender File for This Subfolder ===
    blend_file = os.path.join(output_dir, f"{subfolder}_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_file)
