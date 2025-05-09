import cv2
import numpy as np
from matplotlib import pyplot as plt
from scipy.spatial import Delaunay
import math

def compute_vertex_normals(points):
    points = points.astype(np.float64)
    num_points = len(points)
    normals = np.zeros_like(points, dtype=float)

    for i in range(num_points):
        prev_idx = (i - 1) if i > 0 else num_points - 1
        next_idx = (i + 1) if i < num_points - 1 else 0

        left = points[prev_idx]
        right = points[next_idx]
        tangent = right - left
        normal = np.array([-tangent[1], tangent[0]])
        norm = np.linalg.norm(normal)
        if norm != 0:
            normal /= norm
        normals[i] = normal

    return normals

def resample_contour(points, desired_spacing):
    distances = np.sqrt(np.sum(np.diff(points, axis=0)**2, axis=1))
    cumulative_distances = np.insert(np.cumsum(distances), 0, 0)
    total_length = cumulative_distances[-1]
    num_samples = int(np.ceil(total_length / desired_spacing))
    new_distances = np.linspace(0, total_length, num_samples)
    resampled_points = np.zeros((num_samples, 2))
    for i in range(2):
        resampled_points[:, i] = np.interp(new_distances, cumulative_distances, points[:, i])
    return resampled_points

def extract_and_triangulate_internal_contours(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    internal_contours = []
    for i, contour in enumerate(contours):
        if hierarchy[0][i][3] == 2:
            internal_contours.append(contour)

    contour = internal_contours[0]
    points = contour.reshape(-1, 2)
    points = resample_contour(points, desired_spacing=10)
    normals = compute_vertex_normals(points)

    total_points = len(points)
    include_length = 14
    exclude_length = 3

    del_points = []
    new_normals = []

    # --- FIRST --- Calculate final bounding box using all parts (for consistent view)
    full_points = []
    i = 0
    while i < total_points:
        start = i
        end = min(i + include_length, total_points)
        full_points.append(points[start:end])
        i += include_length + exclude_length
    full_points = np.concatenate(full_points)
    min_x, max_x = np.min(full_points[:,0]), np.max(full_points[:,0])
    min_y, max_y = np.min(full_points[:,1]), np.max(full_points[:,1])
    padding = 10
    xlim = (min_x - padding, max_x + padding)
    ylim = (min_y - padding, max_y + padding)

    # --- THEN --- Iteratively build and plot
    i = 0
    part_counter = 0
    parts = []
    while i < total_points:
        start = i
        end = min(i + include_length, total_points)
        part = points[start:end]
        normals_part = normals[start:end]
        
        parts.append(part)

        del_points.append(part)
        new_normals.append(normals_part)

        accumulated_points = np.concatenate(del_points)
        accumulated_normals = np.concatenate(new_normals)

        # ---- Create new figure with 3 subplots ----
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        titles = ['Input Sketch', 'Circumcircles', 'Valid Triangles (Filled)']

        # Common settings
        for ax in axes:
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.set_aspect('equal')
            ax.axis('off')

        # --- First subplot: Input sketch ---
        for part in parts:
            axes[0].plot(part[:, 0], part[:, 1], '-', color='black', markersize=4)
            axes[2].plot(part[:, 0], part[:, 1], 'o-', color='black', markersize=4)
            axes[1].plot(part[:, 0], part[:, 1], 'o', color='blue', markersize=4)
        # axes[0].plot(accumulated_points[:, 0], accumulated_points[:, 1], 'o-', color='black', markersize=4)
        scale = 5
        for p, n in zip(accumulated_points, accumulated_normals):
            axes[1].arrow(p[0], p[1], -n[0]*scale, -n[1]*scale, head_width=0.8, head_length=1, fc='black', ec='black')

        # --- Triangulation (same for second and third plot) ---
        if len(accumulated_points) >= 3:
            tri = Delaunay(accumulated_points)

            for simplex in tri.simplices:
                A = accumulated_points[simplex[0]]
                B = accumulated_points[simplex[1]]
                C = accumulated_points[simplex[2]]
                NA = accumulated_normals[simplex[0]]
                NB = accumulated_normals[simplex[1]]
                NC = accumulated_normals[simplex[2]]

                x1, y1 = A
                x2, y2 = B
                x3, y3 = C
                D_val = 2 * (x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))
                if D_val == 0:
                    continue
                ux = ((x1**2 + y1**2)*(y2 - y3) + (x2**2 + y2**2)*(y3 - y1) + (x3**2 + y3**2)*(y1 - y2)) / D_val
                uy = ((x1**2 + y1**2)*(x3 - x2) + (x2**2 + y2**2)*(x1 - x3) + (x3**2 + y3**2)*(x2 - x1)) / D_val
                R = math.sqrt((ux - x1)**2 + (uy - y1)**2)

                vA = np.array([ux, uy]) - A
                vB = np.array([ux, uy]) - B
                vC = np.array([ux, uy]) - C
                vA /= np.linalg.norm(vA)
                vB /= np.linalg.norm(vB)
                vC /= np.linalg.norm(vC)

                dotA = np.dot(vA, NA)
                dotB = np.dot(vB, NB)
                dotC = np.dot(vC, NC)

                valid = (dotA > 0) and (dotB > 0) and (dotC > 0)

                if valid:
                    color = 'green'  # Blue for valid
                else:
                    color = 'purple'  # Orange for invalid

                # Plot circles in 2nd subplot (edges only)
                circle = plt.Circle((ux, uy), R, color=color, fill=False, linewidth=0.5)
                axes[1].add_patch(circle)

                # Plot filled valid triangles in 3rd subplot
                if valid:
                    # triangle = plt.Polygon([A, B, C], color='#0072B2', alpha=0.3)
                    # axes[2].add_patch(triangle)
                    circle = plt.Circle((ux, uy), R, color="green", fill=True, linewidth=0.5)
                    axes[2].add_patch(circle)

        # Set titles
        # for ax, title in zip(axes, titles):
        #     ax.set_title(title)

        # plt.suptitle(f"Stage {part_counter + 1}", fontsize=16)
        plt.tight_layout()
        plt.savefig(f"figures/stage_{part_counter + 1}.svg")  # <-- save as SVG

        plt.show()

        part_counter += 1
        i += include_length + exclude_length

# Path to your image
image_path = 'download.jpeg'

# Run
extract_and_triangulate_internal_contours(image_path)
