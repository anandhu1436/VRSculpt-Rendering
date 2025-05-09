import os

# === Parameters ===
folder = "/Users/anandhu/Documents/proxy/SIGRAPH-ASIA/BlenderToolbox/"
# subfolder = "data/wireframes"
subfolder = "renders"
root_folder = os.path.join(folder, subfolder)
output_svg = os.path.join(folder,subfolder+".svg")
image_width = 300  # width per image in px
image_height = 300  # height per image in px
padding = 20

column_names = ["ribbon", "marching", "final","ribbon-final"]

# === Collect Image Paths ===
rows = []
for subfolder in sorted(os.listdir(root_folder)):
    sub_path = os.path.join(root_folder, subfolder)
    if not os.path.isdir(sub_path):
        continue

    render_path = os.path.join(sub_path, "renders_rotated")
    if not os.path.exists(render_path):
        continue

    row = []
    for col in column_names:
        image_path = os.path.join(render_path, f"render_from_{col}.png")
        if os.path.exists(image_path):
            row.append(image_path)
        else:
            row.append(None)
    rows.append((subfolder, row))

# === Build SVG ===
svg_width = 3 * image_width + 4 * padding
svg_height = len(rows) * (image_height + padding) + padding

svg_content = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">'
]

import base64

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"  # or image/jpeg if JPG

# Assuming 'href' is a file path to the image


for i, (folder_name, images) in enumerate(rows):
    y = padding + i * (image_height + padding)
    
    # Optional: Folder name as label
    # svg_content.append(f'<text x="{padding}" y="{y - 5}" font-size="16" fill="black">{folder_name}</text>')

    for j, img_path in enumerate(images):
        x = padding + j * (image_width + padding)
        if img_path:
            href = os.path.relpath(img_path, os.path.dirname(output_svg))

            embedded_href = image_to_base64(href)

            svg_content.append(
                f'<image x="{x}" y="{y}" width="{image_width}" height="{image_height}" href="{embedded_href}"/>'
            )
            # svg_content.append(
            #     f'<image x="{x}" y="{y}" width="{image_width}" height="{image_height}" href="{href}"/>'
            # )
        else:
            # Placeholder for missing image
            svg_content.append(
                f'<rect x="{x}" y="{y}" width="{image_width}" height="{image_height}" fill="#eee" stroke="#aaa" />'
            )

svg_content.append('</svg>')

# === Save SVG ===
with open(output_svg, 'w') as f:
    f.write("\n".join(svg_content))

print(f"SVG file saved to {output_svg}")
