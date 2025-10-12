import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# A small value to prevent "shadow acne" when calculating intersections.
EPSILON = 1e-4

# --- Vector and Math Utilities ---
def normalize(v):
    """Normalize a vector."""
    norm = np.linalg.norm(v)
    return v / norm if norm != 0 else np.zeros_like(v)

def dot(v1, v2):
    """Calculate the dot product of two vectors."""
    return np.dot(v1, v2)

def generate_diffuse_direction(N):
    """
    Generates a random direction vector cosine-weighted sampled over the hemisphere
    defined by the surface normal N (diffuse reflection - Lambertian model).
    """
    # Create a coordinate system (TBN) where N is the Z-axis
    if np.abs(N[0]) > 0.9: 
        T = normalize(np.cross(np.array([0, 1, 0]), N))
    else: 
        T = normalize(np.cross(np.array([1, 0, 0]), N))
    B = np.cross(N, T)
    
    # Sample random direction in local hemisphere (cosine-weighted sampling)
    r1 = np.random.rand() 
    r2 = np.random.rand()
    
    r_disk = np.sqrt(r1) 
    phi = 2 * np.pi * r2

    x_local = r_disk * np.cos(phi)
    y_local = r_disk * np.sin(phi)
    z_local = np.sqrt(1.0 - r1)

    local_dir = np.array([x_local, y_local, z_local])
    
    # Transform local direction to world space
    scattered_direction = local_dir[0] * T + local_dir[1] * B + local_dir[2] * N
    
    return normalize(scattered_direction)


# --- Scene Objects ---

class Sphere:
    def __init__(self, center, radius, color):
        self.center = np.array(center)
        self.radius = radius
        self.color = np.array(color)

    def intersect(self, ray_origin, ray_direction):
        """Calculates the distance (t) to the intersection point or infinity."""
        oc = ray_origin - self.center
        a = dot(ray_direction, ray_direction)
        b = 2.0 * dot(oc, ray_direction)
        c = dot(oc, oc) - self.radius**2
        discriminant = b*b - 4*a*c
        
        if discriminant < 0:
            return float('inf')
        
        t0 = (-b - np.sqrt(discriminant)) / (2.0 * a)
        t1 = (-b + np.sqrt(discriminant)) / (2.0 * a)
        
        t = float('inf')
        if t0 > EPSILON:
            t = t0
        elif t1 > EPSILON:
            t = t1
            
        return t

    def get_normal(self, point):
        """Returns the normal vector at an intersection point on the sphere."""
        return normalize(point - self.center)

class Cube:
    def __init__(self, center, size, color):
        self.center = np.array(center)
        self.size = size
        self.color = np.array(color)
        self.min_bounds = self.center - self.size / 2
        self.max_bounds = self.center + self.size / 2

    def intersect(self, ray_origin, ray_direction):
        """
        Calculates the intersection of a ray with the cube using the slab method.
        Returns the distance (t) to the intersection point or infinity.
        """
        t_min = float('-inf')
        t_max = float('inf')

        for i in range(3):
            if ray_direction[i] == 0:
                if not (self.min_bounds[i] <= ray_origin[i] <= self.max_bounds[i]):
                    return float('inf')
                t1, t2 = float('-inf'), float('inf')
            else:
                t1 = (self.min_bounds[i] - ray_origin[i]) / ray_direction[i]
                t2 = (self.max_bounds[i] - ray_origin[i]) / ray_direction[i]
            
            t_min_i = min(t1, t2)
            t_max_i = max(t1, t2)

            t_min = max(t_min, t_min_i)
            t_max = min(t_max, t_max_i)

            if t_max <= t_min:
                return float('inf')
        
        if t_min > EPSILON:
            return t_min
        if t_max > EPSILON:
            return t_max

        return float('inf')

    def get_normal(self, point):
        """Returns the normal vector at an intersection point on the cube."""
        local_point = point - self.center
        
        # Determine the dominant axis (which face was hit)
        abs_lp = np.abs(local_point)
        max_idx = np.argmax(abs_lp)
        
        normal = np.zeros(3)
        normal[max_idx] = np.sign(local_point[max_idx])
        return normal

# --- Scene and Hologram Setup ---

def calculate_scene_bounds(objects):
    """Calculates the Axis-Aligned Bounding Box (AABB) for all objects in the scene."""
    min_coords = np.array([float('inf')] * 3)
    max_coords = np.array([float('-inf')] * 3)
    
    for obj in objects:
        if isinstance(obj, Sphere):
            obj_min = obj.center - obj.radius
            obj_max = obj.center + obj.radius
        elif isinstance(obj, Cube):
            obj_min = obj.min_bounds
            obj_max = obj.max_bounds
        else:
            continue
            
        min_coords = np.minimum(min_coords, obj_min)
        max_coords = np.maximum(max_coords, obj_max)

    return {
        'min': min_coords,
        'max': max_coords
    }

def calculate_target_angles(light_pos, bounds):
    """
    Calculates the min/max spherical coordinates (phi, theta) required for a ray 
    originating at light_pos to hit the scene's AABB.
    """
    min_p, max_p = bounds['min'], bounds['max']
    
    # 8 corners of the AABB
    corners = [
        np.array([min_p[0], min_p[1], min_p[2]]),
        np.array([max_p[0], min_p[1], min_p[2]]),
        np.array([min_p[0], max_p[1], min_p[2]]),
        np.array([max_p[0], max_p[1], min_p[2]]),
        np.array([min_p[0], min_p[1], max_p[2]]),
        np.array([max_p[0], min_p[1], max_p[2]]),
        np.array([min_p[0], max_p[1], max_p[2]]),
        np.array([max_p[0], max_p[1], max_p[2]]),
    ]
    
    phi_list = []
    theta_list = []
    
    # Determine the angular bounds by checking the 8 corners
    for corner in corners:
        direction = normalize(corner - light_pos)
        
        # Phi (azimuthal angle, around Z-axis, in [-pi, pi])
        phi = np.arctan2(direction[1], direction[0]) 
        
        # Theta (polar angle, from Z-axis, in [0, pi])
        theta = np.arccos(direction[2]) 
        
        phi_list.append(phi)
        theta_list.append(theta)

    # Simple min/max for bounds
    theta_min = min(theta_list)
    theta_max = max(theta_list)
    phi_min = min(phi_list)
    phi_max = max(phi_list)

    return {
        'phi_min': phi_min,
        'phi_max': phi_max,
        'theta_min': theta_min,
        'theta_max': theta_max
    }

def create_scene():
    """Defines and returns the scene objects and light source."""
    
    # Define scene objects
    sphere = Sphere(center=[0, 0, -7.5], radius=1.5, color=[255, 0, 0])
    cube = Cube(center=[2.5, -1, -7], size=2, color=[0, 255, 0])
    
    # Define the point light source
    light_source = {
        'position': np.array([0, 5, 10]),
        'intensity': 1000.0
    }
    
    return [sphere, cube], light_source

def setup_hologram_plane(plane_position_z=-5, size=5, resolution_mm=25):
    """
    Sets up the hologram plane properties and initializes the accumulation buffer.
    Returns the plane properties dict and the accumulation data array.
    """
    pixel_size = resolution_mm / 1000.0  # Convert mm to meters
    pixels_per_side = int(size / pixel_size)
    
    plane_bounds = {
        'z': plane_position_z,
        'min_x': -size / 2,
        'max_x': size / 2,
        'min_y': -size / 2,
        'max_y': size / 2,
        'size': size,
        'pixels_per_side': pixels_per_side,
        'pixel_size': pixel_size
    }
    
    # Accumulation data: (Acc_Intensity, Acc_Dir_X, Acc_Dir_Y, Acc_Dir_Z, Hit_Count)
    H = W = pixels_per_side
    accumulation_data = np.zeros((H, W, 5), dtype=np.float64) 
    
    return plane_bounds, accumulation_data

def intersect_plane(ray_origin, ray_direction, plane_bounds):
    """
    Checks if a ray intersects the hologram plane and returns pixel indices.
    Returns (row_index, col_index, t_distance) or None.
    """
    plane_z = plane_bounds['z']
    
    if ray_direction[2] == 0:
        return None 

    t = (plane_z - ray_origin[2]) / ray_direction[2]
    
    if t < EPSILON:
        return None 
    
    P = ray_origin + t * ray_direction
    x, y = P[0], P[1]
    
    min_x, max_x = plane_bounds['min_x'], plane_bounds['max_x']
    min_y, max_y = plane_bounds['min_y'], plane_bounds['max_y']
    
    if min_x <= x <= max_x and min_y <= y <= max_y:
        size = plane_bounds['size']
        pps = plane_bounds['pixels_per_side']
        
        normalized_x = (x - min_x) / size
        normalized_y = (y - min_y) / size
        
        col_index = int(normalized_x * pps)
        row_index = int((1 - normalized_y) * pps) # (1 - normalized_y) for Y-flip
        
        H = W = pps
        col_index = max(0, min(W - 1, col_index))
        row_index = max(0, min(H - 1, row_index))
        
        return row_index, col_index, t
    else:
        return None

# --- Image Processing Functions ---

def save_grayscale_image(data, mask, filename, scale_factor):
    """
    Scales the data and saves it as a grayscale PNG image.
    data: (H, W) array of floating point values.
    mask: (H, W) boolean mask for hit pixels.
    """
    image_data = data.copy()
    
    # Scale only the hit pixels and clip them to [0, 1] for image representation
    image_data[mask] *= scale_factor
    image_data = np.clip(image_data, 0.0, 1.0)
    
    # Set non-hit pixels to black
    image_data[~mask] = 0.0
    
    # Use matplotlib to save the grayscale image
    plt.imsave(filename, image_data, cmap='gray')
    print(f"Grayscale image saved to {filename}")

def calculate_angle_image(avg_direction, plane_bounds, light_pos, hit_mask):
    """
    Calculates the angle between the average scattered ray and the light-to-pixel vector 
    in the XZ plane for all hit pixels.
    """
    H, W, _ = avg_direction.shape
    angle_map = np.zeros((H, W), dtype=np.float64)
    
    pixel_size = plane_bounds['pixel_size']
    plane_z = plane_bounds['z']
    
    # Coordinates of the pixel centers
    pixel_x_coords = np.linspace(
        plane_bounds['min_x'] + pixel_size / 2, 
        plane_bounds['max_x'] - pixel_size / 2, 
        W
    )
    # Note: Y coordinates are typically flipped to match row index
    pixel_y_coords = np.linspace(
        plane_bounds['max_y'] - pixel_size / 2, 
        plane_bounds['min_y'] + pixel_size / 2, 
        H
    )

    for r in range(H):
        for c in range(W):
            if hit_mask[r, c]:
                # 1. Calculate Pixel Center P
                P = np.array([pixel_x_coords[c], pixel_y_coords[r], plane_z])
                
                # 2. Projected Average Scattered Ray (V1) in XZ plane
                D_avg = avg_direction[r, c]
                # V1 = (Dx, Dz)
                V1 = np.array([D_avg[0], D_avg[2]])
                
                # 3. Projected Light Source to Pixel Vector (V2) in XZ plane
                LP = P - light_pos
                # V2 = (LPx, LPz)
                V2 = np.array([LP[0], LP[2]])
                
                # 4. Calculate Angle alpha: arccos( (V1 . V2) / (|V1| |V2|) )
                norm_V1 = np.linalg.norm(V1)
                norm_V2 = np.linalg.norm(V2)
                
                if norm_V1 < EPSILON or norm_V2 < EPSILON:
                    continue

                dot_product = np.dot(V1, V2)
                cos_alpha = dot_product / (norm_V1 * norm_V2)
                
                # Clamp value to [-1, 1] for arccos robustness
                cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
                
                # Angle in radians [0, pi]
                alpha = np.arccos(cos_alpha)
                
                angle_map[r, c] = alpha

    # Normalize angle data for display as grayscale image [0, 1]
    # Maximum possible angle is pi (180 degrees).
    # We only normalize the hit pixels.
    max_angle = np.pi
    angle_map[hit_mask] = angle_map[hit_mask] / max_angle
    
    return angle_map

# --- Visualization Function (Unchanged) ---

def visualize_scene(objects, light_source, plane_bounds, rays_to_plot):
    """
    Creates a 3D visualization of the scene, hologram plane, and selected rays.
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_title("Diffuse Ray Tracer Visualization (Scattered Rays Only)")

    ax.scatter(light_source['position'][0], light_source['position'][1], light_source['position'][2],
               color='yellow', s=100, label='Light Source')

    # Plot the sphere (as a wireframe for visibility)
    sphere = objects[0]
    u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
    x_sphere = sphere.radius * np.cos(u) * np.sin(v) + sphere.center[0]
    y_sphere = sphere.radius * np.sin(u) * np.sin(v) + sphere.center[1]
    z_sphere = sphere.radius * np.cos(v) + sphere.center[2]
    ax.plot_wireframe(x_sphere, y_sphere, z_sphere, color='red', alpha=0.5, label='Sphere')

    # Plot the cube (as a wireframe)
    cube = objects[1]
    verts = [
        [cube.min_bounds[0], cube.min_bounds[1], cube.min_bounds[2]],
        [cube.max_bounds[0], cube.min_bounds[1], cube.min_bounds[2]],
        [cube.max_bounds[0], cube.max_bounds[1], cube.min_bounds[2]],
        [cube.min_bounds[0], cube.max_bounds[1], cube.min_bounds[2]],
        [cube.min_bounds[0], cube.min_bounds[1], cube.max_bounds[2]],
        [cube.max_bounds[0], cube.min_bounds[1], cube.max_bounds[2]],
        [cube.max_bounds[0], cube.max_bounds[1], cube.max_bounds[2]],
        [cube.min_bounds[0], cube.max_bounds[1], cube.max_bounds[2]]
    ]
    verts = np.array(verts)
    faces = [[verts[0], verts[1], verts[2], verts[3]],
             [verts[4], verts[5], verts[6], verts[7]],
             [verts[0], verts[1], verts[5], verts[4]],
             [verts[2], verts[3], verts[7], verts[6]],
             [verts[1], verts[2], verts[6], verts[5]],
             [verts[4], verts[7], verts[3], verts[0]]]
    ax.add_collection3d(Poly3DCollection(faces, facecolors='green', linewidths=1, edgecolors='r', alpha=0.3))

    # Plot the hologram plane
    plane_size = plane_bounds['size']
    plane_z = plane_bounds['z']
    x_plane = np.linspace(-plane_size / 2, plane_size / 2, 2)
    y_plane = np.linspace(-plane_size / 2, plane_size / 2, 2)
    X, Y = np.meshgrid(x_plane, y_plane)
    Z = np.full(X.shape, plane_z)
    ax.plot_surface(X, Y, Z, color='cyan', alpha=0.2, label='Hologram Plane')

    # Plot the rays
    for start, end in rays_to_plot:
        ax.plot([start[0], end[0]], [start[1], end[1]], [start[2], end[2]],
                color='blue', linestyle='-', alpha=0.3)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_xlim(-8, 8)
    ax.set_ylim(-8, 8)
    ax.set_zlim(-15, 5)
    ax.view_init(elev=20, azim=-60)

    plt.show()

# --- Main Program ---

def main():
    objects, light = create_scene()
    plane_bounds, accumulation_data = setup_hologram_plane()
    
    # Optimization: Calculate the bounding solid angle
    scene_bounds = calculate_scene_bounds(objects)
    target_angles = calculate_target_angles(light['position'], scene_bounds)
    
    phi_min = target_angles['phi_min']
    phi_max = target_angles['phi_max']
    theta_min = target_angles['theta_min']
    theta_max = target_angles['theta_max']
    
    phi_range = phi_max - phi_min
    theta_range = theta_max - theta_min
    
    NUM_RAYS = 5000000 
    
    rays_to_visualize = []
    vis_pixel_set = set()

    H, W, _ = accumulation_data.shape
        
    print("Hologram Plane Size: {}x{} pixels".format(W, H))
    print("Total Rays Sampled: {}".format(NUM_RAYS))
    print(f"Restricted Sampling Angles (deg): Phi [{np.degrees(phi_min):.1f}, {np.degrees(phi_max):.1f}], Theta [{np.degrees(theta_min):.1f}, {np.degrees(theta_max):.1f}]")
    print("Starting diffuse ray-tracing simulation...")
        
    for k in range(NUM_RAYS):
        # 1. Generate random ray direction from the light source (RESTRICTED SAMPLING)
        
        theta_sample = theta_min + theta_range * np.random.rand()
        phi_sample = phi_min + phi_range * np.random.rand()
        
        # Convert restricted spherical coordinates (phi, theta) to Cartesian direction
        direction = np.array([
            np.sin(theta_sample) * np.cos(phi_sample),
            np.sin(theta_sample) * np.sin(phi_sample),
            np.cos(theta_sample)
        ])
        ray_origin = light['position']
        
        # 2. Trace primary ray (Source -> Object)
        closest_t = float('inf')
        hit_object = None
        
        for obj in objects:
            t = obj.intersect(ray_origin, direction)
            if t < closest_t:
                closest_t = t
                hit_object = obj
                
        if hit_object is not None and closest_t != float('inf'):
            # Primary ray hits an object
            
            # 3. Calculate diffuse scattering
            hit_point = ray_origin + closest_t * direction
            surface_normal = hit_object.get_normal(hit_point)
            
            scattered_direction = generate_diffuse_direction(surface_normal)
            scattered_origin = hit_point + EPSILON * surface_normal
            
            # 4. Trace scattered ray (Object -> Plane)
            result = intersect_plane(scattered_origin, scattered_direction, plane_bounds)
            
            if result is not None:
                r, c, t_plane = result
                
                # 5. Calculate and accumulate intensity and direction
                
                distance_to_object = closest_t
                initial_intensity = light['intensity'] / (distance_to_object**2)
                
                # Attenuation due to Lambertian shading
                cos_theta = max(0, -dot(direction, surface_normal))
                initial_intensity *= cos_theta
                
                distance_to_plane_hit = t_plane
                final_intensity = initial_intensity / (distance_to_plane_hit**2)
                
                # Accumulate data
                accumulation_data[r, c, 0] += final_intensity
                accumulation_data[r, c, 1:4] += scattered_direction
                accumulation_data[r, c, 4] += 1
                
                # Record the hit for visualization (only a subset)
                if len(rays_to_visualize) < 500 and (r, c) not in vis_pixel_set:
                    plane_hit_point = scattered_origin + t_plane * scattered_direction
                    rays_to_visualize.append((hit_point, plane_hit_point))
                    vis_pixel_set.add((r, c))

        # Print progress
        if (k + 1) % 10000 == 0 or (k + 1) == NUM_RAYS:
            print("Processed {} of {} rays...".format(k + 1, NUM_RAYS))
            
    # --- 6. Final Calculation and Data Output ---
    
    print("\nSimulation complete. Calculating averages...")

    # Calculate final averages
    hit_counts = accumulation_data[:, :, 4]
    hit_mask = hit_counts > 0
    
    # Calculate Average Intensity
    avg_intensity = np.zeros_like(hit_counts, dtype=np.float64)
    avg_intensity[hit_mask] = accumulation_data[hit_mask, 0] / hit_counts[hit_mask]
    
    # Calculate Average Direction Vector (Normalized sum of direction vectors)
    avg_direction = np.zeros_like(accumulation_data[:, :, 1:4], dtype=np.float64)
    norm_acc_dir = np.linalg.norm(accumulation_data[hit_mask, 1:4], axis=1) + EPSILON 
    avg_direction[hit_mask] = accumulation_data[hit_mask, 1:4] / norm_acc_dir[:, np.newaxis]
    
    # Write results to text file
    with open('hologram_data.txt', 'w') as f:
        f.write("# Pixel_ID, X_pos, Y_pos, Z_pos, Avg_Direction_X, Avg_Direction_Y, Avg_Direction_Z, Avg_Intensity, Hit_Count\n")
        
        pixel_size = plane_bounds['pixel_size']
        pixel_x_center = np.linspace(plane_bounds['min_x'] + pixel_size/2, plane_bounds['max_x'] - pixel_size/2, W)
        pixel_y_center = np.linspace(plane_bounds['max_y'] - pixel_size/2, plane_bounds['min_y'] + pixel_size/2, H)
        
        pixel_id = 0
        for r in range(H):
            for c in range(W):
                f.write("{}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {}\n".format(
                    pixel_id, pixel_x_center[c], pixel_y_center[r], plane_bounds['z'],
                    avg_direction[r, c, 0], avg_direction[r, c, 1], avg_direction[r, c, 2],
                    avg_intensity[r, c], hit_counts[r, c]))
                pixel_id += 1
                
    print("\nData saved to hologram_data.txt.")
    
    # --- 7. Image Generation and Output ---
    
    # 7.1 Save Intensity Image (First grayscale PNG)
    # A scale factor is needed to map raw intensity values (which are usually small) to the 0-1 range.
    INTENSITY_SCALE_FACTOR = 0.05 
    print(f"Saving Intensity Map (scaled by {INTENSITY_SCALE_FACTOR:.1f}) to intensity_map.png...")
    save_grayscale_image(avg_intensity, hit_mask, "intensity_map.png", INTENSITY_SCALE_FACTOR)
    
    # 7.2 Calculate and Save Angle Map (Second grayscale PNG)
    print("Calculating and saving Angle Map to angle_map.png...")
    # Angle data is normalized to [0, 1] inside the function, so scale_factor=1.0
    angle_data = calculate_angle_image(avg_direction, plane_bounds, light['position'], hit_mask)
    save_grayscale_image(angle_data, hit_mask, "angle_map.png", 0.5) 
    
    # Now, visualize the scene
    print("Generating 3D visualization...")
    visualize_scene(objects, light, plane_bounds, rays_to_visualize)

if __name__ == "__main__":
    main()
