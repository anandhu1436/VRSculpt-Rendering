import bpy
import os
from math import radians
import math

# === Define list of blend files with their corresponding rotations (in degrees) ===
blend_files_with_rotations = [
    ((114, 26, 0), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429094726/20250429094726_scene.blend"),
    ((0, 100, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429100653/20250429100653_scene.blend"),
    ((0, 132, 182), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429101214/20250429101214_scene.blend"),
    ((0, 96, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429102330/20250429102330_scene.blend"),
    ((0, 254, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429102955/20250429102955_scene.blend"),
    ((82, 12, 8), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429111122/20250429111122_scene.blend"),
    ((-88, 0, -116), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429111701/20250429111701_scene.blend"),
    ((88, -66, 0), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429112813/20250429112813_scene.blend"),
    ((0, 228, 0), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429114010/20250429114010_scene.blend"),
    ((-6, 92, -90), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429114851/20250429114851_scene.blend"),
    ((114, -158, 16), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429115607/20250429115607_scene.blend"),
    ((0, 180, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429130946/20250429130946_scene.blend"),
    ((-102, -14, -190), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429132013/20250429132013_scene.blend"),
    ((-6, 254, 100), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429132559/20250429132559_scene.blend"),
    ((0, 100, 0), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429133920/20250429133920_scene.blend"),
    ((66, 0, 0), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429134436/20250429134436_scene.blend"),
    ((0, 126, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429135017/20250429135017_scene.blend"),
    ((10, 242, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429092236/20250429092236_scene.blend"),
    ((0, 48, 180), "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/renders/20250429133006/20250429133006_scene.blend"),
]

# === Rendering parameters ===
imgRes_x, imgRes_y = 5000, 5000

for rotation_euler_deg, blend_file_path in blend_files_with_rotations:
    print(f"\n📂 Processing: {os.path.basename(blend_file_path)}")

    # Open the .blend file
    bpy.ops.wm.open_mainfile(filepath=blend_file_path)

    # Convert degrees to radians
    rotation_euler = tuple(radians(v) for v in rotation_euler_deg)

    # Apply rotation to all mesh objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.rotation_euler = rotation_euler

    bpy.context.view_layer.update()

    # Set render resolution
    scene = bpy.context.scene
    scene.render.resolution_x = imgRes_x
    scene.render.resolution_y = imgRes_y

    # Output directory next to the blend file
    base_dir = os.path.dirname(blend_file_path)
    output_dir = os.path.join(base_dir, "renders_rotated")
    os.makedirs(output_dir, exist_ok=True)

    # Render from each camera
    for cam in [obj for obj in bpy.data.objects if obj.type == 'CAMERA']:
        scene.camera = cam
        render_path = os.path.join(output_dir, f"render_from_{cam.name}.png")
        scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)
        print(f"🖼️ Rendered: {render_path}")

print("\n✅ Done rendering all files from all cameras.")
