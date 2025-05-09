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

def get_bounding_box_diagonal(obj):
    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_corner = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    return (max_corner - min_corner).length

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


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

folder_path = "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/heart/rib"

if not os.path.isdir(folder_path):
    exit(f"Folder {folder_path} does not exist.")

# === Start a New Blender Scene ===
clear_scene()
bt.blenderInit(5000, 5000, numSamples=100, exposure=1.5)

# === Collect .obj and .ply Files ===
mesh_paths = []
for f in sorted(os.listdir(folder_path)):
    if f.lower().endswith(('.obj', '.ply')):
        mesh_paths.append(os.path.join(folder_path, f))

if not mesh_paths:
    print(f"No .obj or .ply meshes found in {folder_path}")
    exit()

# === Reference Bounding Box ===
ref_mesh = bt.readMesh(mesh_paths[-1], (0, 0, 0), (0, 0, 0), (1, 1, 1))
ref_width = get_bounding_box_diagonal(ref_mesh)

ref_bbox = [ref_mesh.matrix_world @ Vector(corner) for corner in ref_mesh.bound_box]
ref_y_center = sum(v.y for v in ref_bbox) / 8
bpy.data.objects.remove(ref_mesh, do_unlink=True)

all_meshes = []

import colorsys

rotation = (90, 0, 0)

for i, path in enumerate(mesh_paths):
    x_offset = i * ref_width * 1.5
    translation = np.array([x_offset, -ref_y_center, 0])
    

    mesh = bt.readMesh(path, translation, rotation, (1, 1, 1))

    # Generate a distinct color using HSV and convert to RGB
    hue = (i / len(mesh_paths)) % 1.0  # Ensure hue is in [0,1)
    r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)  # Saturation=0.8, Value=1.0
    meshColor = bt.colorObj((r, g, b, 1), 0.5, 1.0, 1.0, 0.0, 2.0)

    bt.setMat_balloon(mesh, meshColor, 0)
    bpy.ops.object.shade_smooth()
    # Add two-sided material

    mat = create_two_sided_material()
    if mesh.data.materials:
        mesh.data.materials[0] = mat
    else:
        mesh.data.materials.append(mat)

    # === Create wireframe display ===
    wireframe_mesh = mesh.copy()
    wireframe_mesh.data = mesh.data.copy()
    bpy.context.collection.objects.link(wireframe_mesh)

    # Add Wireframe modifier
    modifier = wireframe_mesh.modifiers.new(name="Wireframe", type='WIREFRAME')
    modifier.thickness = 0.003 * ref_width  # Adjust thickness as needed
    modifier.use_replace = False  # So mesh is shown both solid and wireframe

    # Create black material for wireframe
    wire_mat = bpy.data.materials.new(name="WireMaterial")
    wire_mat.diffuse_color = (0, 0, 0, 1)
    wire_mat.use_nodes = True
    bsdf = wire_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
        bsdf.inputs["Roughness"].default_value = 1.0

    # Assign material to wireframe mesh
    wireframe_mesh.data.materials.append(wire_mat)


    all_meshes.append(mesh)


# === Lighting ===
bt.setLight_sun((6, -30, -155), 2, 0.3)
bt.setLight_ambient((0.1, 0.1, 0.1, 1))
bt.shadowThreshold(alphaThreshold=0.025, interpolationMode='CARDINAL')

# === Render with Camera per Object ===
output_dir = os.path.join(folder_path, 'renders')
os.makedirs(output_dir, exist_ok=True)

for i, (mesh, path) in enumerate(zip(all_meshes, mesh_paths)):
    base_name = os.path.splitext(os.path.basename(path))[0]
    x_pos = i * ref_width * 1.5
    camLocation = (x_pos, 0, 2 * ref_width)
    lookAtLocation = (x_pos, 0, 0)
    cam = bt.setCamera(camLocation, lookAtLocation, focalLength=45)
    img_path = os.path.join(output_dir, f"render_{base_name}.png")
    bt.renderImage(img_path, cam)

# === Save Blender File for This Subfolder ===
blend_file = os.path.join(output_dir, f"{folder_path}_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_file)
