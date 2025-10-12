import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

def calculate_hologram_point(object_point, hologram_plane, wavelength, reference_source):
    """
    Calculates the complex amplitude contribution of a single object point to the hologram.

    Args:
        object_point (np.array): (x, y, z) coordinates of the object point.
        hologram_plane (np.array): Grid of (x, y) coordinates for the hologram.
        wavelength (float): Wavelength of light in meters.
        reference_source (np.array): (x, y, z) coordinates of the reference point source.
    
    Returns:
        np.array: The complex amplitude from the object point and reference source.
    """
    # Distance from object point to each hologram point
    dist_obj_to_holo = np.sqrt(
        (hologram_plane[:, :, 0] - object_point[0])**2 +
        (hologram_plane[:, :, 1] - object_point[1])**2 +
        object_point[2]**2
    )

    # Distance from reference source to each hologram point
    dist_ref_to_holo = np.sqrt(
        (hologram_plane[:, :, 0] - reference_source[0])**2 +
        (hologram_plane[:, :, 1] - reference_source[1])**2 +
        reference_source[2]**2
    )

    # Complex amplitude of object beam (assuming unit amplitude)
    object_wave = np.exp(1j * 2 * np.pi * dist_obj_to_holo / wavelength)
    
    # Complex amplitude of reference beam
    reference_wave = np.exp(1j * 2 * np.pi * dist_ref_to_holo / wavelength)

    # Interference pattern
    return object_wave + reference_wave



def generate_benton_hologram(object_points, holo_dims, px_size, wavelength):
    """
    Generates a Benton hologram by summing contributions from object points
    with a spatially varying reference beam.

    Args:
        object_points (list of np.array): List of (x, y, z) coordinates for object points.
        holo_dims (tuple): (width, height) of the hologram in pixels.
        px_size (float): Pixel size of the hologram in meters.
        wavelength (float): Wavelength of light in meters.

    Returns:
        np.array: The intensity of the resulting Benton hologram.
    """
    holo_width, holo_height = holo_dims
    total_hologram = np.zeros(holo_dims, dtype=np.complex128)

    # Create the coordinate grid for the hologram plane
    x_h = np.linspace(-holo_width / 2, holo_width / 2, holo_width) * px_size
    y_h = np.linspace(-holo_height / 2, holo_height / 2, holo_height) * px_size
    xx_h, yy_h = np.meshgrid(x_h, y_h)
    hologram_plane = np.stack([xx_h, yy_h], axis=-1)

    # Define the Benton hologram reference wave setup
    # The reference source is far away on the y-axis, and its position
    # changes based on the object's y-coordinate. This creates the rainbow effect.
    benton_angle_factor = np.pi / (2 * np.max(np.abs(object_points[:, 1])))

    # Loop through each object point to calculate its contribution
    for obj_point in object_points:
        # A simple model for the reference beam for Benton holography is a plane wave
        # tilted vertically, where the tilt angle depends on the object's y-coordinate.
        # This simulates the horizontal slit and white light reconstruction.
        #ref_wave_angle = benton_angle_factor * obj_point[1]
        ref_wave_angle = .0000001

        # Complex amplitude for the object point
        object_wave = np.exp(1j * 2 * np.pi * np.sqrt(
            (xx_h - obj_point[0])**2 +
            (yy_h - obj_point[1])**2 +
            obj_point[2]**2
        ) / wavelength)

        # Complex amplitude for the reference beam
        reference_wave = np.exp(1j * 2 * np.pi * yy_h * np.sin(ref_wave_angle) / wavelength)

        total_hologram += object_wave * np.conjugate(reference_wave)
        #total_hologram += object_wave
        #total_hologram += np.conjugate(reference_wave)

    # The final hologram is the magnitude squared of the total complex amplitude
    hologram_intensity = np.abs(total_hologram) ** 2
    return hologram_intensity

def main():
    """Main function to set up the scene and generate the hologram."""
    # --- Hologram and Optical Parameters ---
    wavelength = 1000e-9  # Wavelength of a Helium-Neon laser in meters
    holo_width_px = 1000    # Hologram width in pixels
    holo_height_px = 1000   # Hologram height in pixels
    px_size = 5e-6         # Pixel size in meters (e.g., 5 microns)
    
    # --- 3D Scene Definition ---
    object_points = []
    
    # Floating Cube
    cube_size = 0.05       # 5 cm
    cube_y_pos = 0.08      # Position of the cube on the y-axis
    cube_z_pos = 0.35      # Cube distance from the hologram plane (z-axis)
    
    # Generate points for the vertices of the cube
    #for x in [-1, 1,.01]:
    #    for y in [-1, 1, .01]:
    #        for z in [-1, 1, .01]:
    #           object_points.append(
    #                np.array([x * cube_size / 2, y * cube_size / 2 + cube_y_pos, z * cube_size / 2 + cube_z_pos])
    #           )
    
    object_points.append([0,0,1])
    #object_points.append([0.00,0.001,.1])
    #object_points.append([0.0,0.11,.1])
    #object_points.append([0.0,0.12,.1])
    #object_points.append([0.0,0.13,.1])
    #object_points.append([0.0,0.14,.1])
    #object_points.append([0.0,0.15,.1])
    
    #object_points.append([0.0,-0.25,.1])
    #object_points.append([0.0,0.25,.1])
    #object_points.append([-0.25,0,.1])
    #object_points.append([0.25,0,.1])

    # Grid Floor
  #  grid_spacing = 0.02    # 2 cm spacing
  #  grid_extent = 0.25     # Extent of the grid in x and y
  #  floor_z_pos = 0.50     # Floor distance from hologram plane
    
    # Generate points for the grid lines
  #  for x in np.arange(-grid_extent, grid_extent + grid_spacing, grid_spacing):
    #    for y in np.arange(-grid_extent, grid_extent + grid_spacing, grid_spacing):
    #        object_points.append(np.array([x, y, floor_z_pos]))
            
    object_points = np.array(object_points)

    print("Generating Benton Hologram...")
    hologram = generate_benton_hologram(
        object_points,
        (holo_width_px, holo_height_px),
        px_size,
        wavelength
    )
    print("Hologram generation complete.")

    # --- Visualization and Saving ---
    # Normalize the hologram to a 0-255 range for image saving
    hologram_normalized = (hologram - np.min(hologram)) / (np.max(hologram) - np.min(hologram))
    hologram_8bit = (hologram_normalized * 255).astype(np.uint8)

    # Display the hologram using matplotlib
    plt.figure(figsize=(16, 16))
    plt.imshow(hologram_8bit, cmap='gray')
    plt.title("Computer-Generated Benton Hologram")
    plt.axis('off')
    plt.show()

    # Save the hologram image
    im = Image.fromarray(hologram_8bit)
    im.save('benton_hologram.png')
    print("Hologram saved as benton_hologram.png")

if __name__ == "__main__":
    main()
