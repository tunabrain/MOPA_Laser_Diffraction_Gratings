import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d

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

# --- Scene Objects ---

class Sphere:
    def __init__(self, center, radius, color):
        self.center = np.array(center)
        self.radius = radius
        self.color = np.array(color)

    def intersect(self, ray_origin, ray_direction):
        """
        Calculates the intersection of a ray with the sphere.
        Returns the distance to the intersection point or infinity if no intersection.
        """
        oc = ray_origin - self.center
        a = dot(ray_direction, ray_direction)
        b = 2.0 * dot(oc, ray_direction)
        c = dot(oc, oc) - self.radius**2
        discriminant = b*b - 4*a*c
        
        if discriminant < 0:
            return float('inf')
        
        t0 = (-b - np.sqrt(discriminant)) / (2.0 * a)
        t1 = (-b + np.sqrt(discriminant)) / (2.0 * a)
        
        if t0 > EPSILON:
            return t0
        if t1 > EPSILON:
            return t1
            
        return float('inf')

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
        Returns the distance to the intersection point or infinity.
        """
        t_min = float('-inf')
        t_max = float('inf')

        for i in range(3):
            if ray_direction[i] == 0:
                if not (self.min_bounds[i] <= ray_origin[i] <= self.max_bounds[i]):
                    return float('inf')
                t_min_i = float('-inf')
                t_max_i = float('inf')
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

# --- Scene and Hologram Setup ---

def create_scene():
    """Defines and returns the scene objects and light source."""
    
    # Define scene objects
    sphere = Sphere(center=[0, 0, -10], radius=1.5, color=[255, 0, 0])
    cube = Cube(center=[2, 0, -8], size=2, color=[0, 255, 0])
    
    # Define the point light source
    light_source = {
        'position': np.array([0, 0, -1]),
        'intensity': 1000.0
    }
    
    return [sphere, cube], light_source

def setup_hologram_plane(plane_position_z=-.01, size=.02, resolution_mm=0.25):
    """
    Creates a grid of pixel positions for the hologram plane.
    Size is in meters. Resolution is in millimeters.
    Returns the pixel grid, number of pixels, and pixel size.
    """
    pixel_size = resolution_mm / 1000.0  # Convert mm to meters
    pixels_per_side = int(size / pixel_size)
    
    # Create an array of pixel positions
    x = np.linspace(-size / 2, size / 2, pixels_per_side)
    y = np.linspace(-size / 2, size / 2, pixels_per_side)
    
    pixel_grid = []
    for yy in y:
        for xx in x:
            pixel_grid.append(np.array([xx, yy, plane_position_z]))
            
    return np.array(pixel_grid), pixels_per_side**2, pixel_size

# --- Visualization Function ---

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0,0), (0,0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_positions((xs[0],ys[0]),(xs[1],ys[1]))
        FancyArrowPatch.draw(self, renderer)

def visualize_scene(objects, light_source, hologram_pixels, rays_to_plot):
    """
    Creates a 3D visualization of the scene, hologram plane, and selected rays.
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_title("Ray Tracer Visualization")

    # Plot the light source as a yellow point
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
    plane_size = 5
    plane_z = hologram_pixels[0][2]
    x_plane = np.linspace(-plane_size / 2, plane_size / 2, 2)
    y_plane = np.linspace(-plane_size / 2, plane_size / 2, 2)
    X, Y = np.meshgrid(x_plane, y_plane)
    Z = np.full(X.shape, plane_z)
    ax.plot_surface(X, Y, Z, color='cyan', alpha=0.2, label='Hologram Plane')

    # Plot the rays
    for i, (is_blocked, pixel_pos) in enumerate(rays_to_plot):
        start = light_source['position']
        end = pixel_pos
        
        # Determine ray color based on whether it's blocked
        color = 'red' if is_blocked else 'blue'

        # Create a line from the start to the end of the ray
        ax.plot([start[0], end[0]], [start[1], end[1]], [start[2], end[2]],
                color=color, linestyle='--', alpha=0.5)

    # Set axis limits and labels for better visualization
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_xlim(-8, 8)
    ax.set_ylim(-8, 8)
    ax.set_zlim(-15, 5)

    plt.show()

# --- Main Program ---

def main():
    objects, light = create_scene()
    hologram_pixels, num_pixels, pixel_size = setup_hologram_plane()
    
    # List to store a subset of rays for visualization
    rays_to_visualize = []
    
    # Open a file to record the ray data
    with open('hologram_data.txt', 'w') as f:
        f.write("# Pixel_ID, X_pos, Y_pos, Z_pos, Ray_Direction_X, Ray_Direction_Y, Ray_Direction_Z, Intensity\n")
        
        print("Hologram Plane Size: {}x{} pixels".format(int(np.sqrt(num_pixels)), int(np.sqrt(num_pixels))))
        print("Total Pixels: {}".format(num_pixels))
        print("Starting ray-tracing simulation...")
        
        for i, pixel_pos in enumerate(hologram_pixels):
            # Calculate ray direction from the light source to the pixel
            ray_direction = normalize(pixel_pos - light['position'])
            
            # Check for intersections with objects
            closest_t = float('inf')
            
            for obj in objects:
                t = obj.intersect(light['position'], ray_direction)
                if t < closest_t:
                    closest_t = t
            
            # Check if the ray's path is blocked before reaching the plane
            # The distance from light source to pixel is np.linalg.norm(pixel_pos - light['position'])
            distance_to_pixel = np.linalg.norm(pixel_pos - light['position'])

            is_blocked = False
            if closest_t < distance_to_pixel:
                # Ray is blocked by an object, no light reaches the pixel
                intensity = 0.0
                is_blocked = True
            else:
                # Ray reaches the pixel, calculate intensity using inverse square law
                intensity = light['intensity'] / (distance_to_pixel**2)
            
            # Record the data
            f.write("{}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}, {:.4f}\n".format(
                i, pixel_pos[0], pixel_pos[1], pixel_pos[2],
                ray_direction[0], ray_direction[1], ray_direction[2],
                intensity))
            
            # Add a subset of rays to the visualization list
            if i % 1000 == 0:
                rays_to_visualize.append((is_blocked, pixel_pos))
            
            # Print progress
            if (i + 1) % 1000 == 0 or (i + 1) == num_pixels:
                print("Processed {} of {} pixels...".format(i + 1, num_pixels))
                
    print("\nSimulation complete. Data saved to hologram_data.txt.")
    
    # Now, visualize the scene
    print("Generating 3D visualization...")
    visualize_scene(objects, light, hologram_pixels, rays_to_visualize)

if __name__ == "__main__":
    main()
