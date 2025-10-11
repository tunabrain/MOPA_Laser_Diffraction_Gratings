import numpy as np
from PIL import Image
import matplotlib.colors as mcolors
import sys

# --- Hardcoded File Paths ---
INPUT_GRAYSCALE_PATH = 'vertical_gradient_input.png'  # This is a grayscale image containing a vertical gradient to compensate for viewing angle changes along the vertical dimension
INPUT_COLOR_PATH = 'color_input.png'          # The color input image to convert into different diffraction grating pitch values
OUTPUT_PATH = 'input_pitch_image.png'           # This file will be included in the next python script for conversion into svg

# --- Internal Program Parameters for Hue Mapping ---
# The hue value for violet on the 0-1 scale (approx. 270 degrees / 360).
HUE_VIOLET = 270 / 360.0

# Grayscale values that Red and Violet will map to.
# Red (high value) shall be mapped to 220.
MAP_HIGH = 240
# Violet (low value) shall be mapped to 30.
MAP_LOW = 15

def combine_images(grayscale_path, color_path, output_path):
    """
    Combines a grayscale image with a hue-mapped color image, using hardcoded 
    mapping parameters.
    """
    try:
        # Step 1: Load input images.
        gray_img = Image.open(grayscale_path).convert('L')
        color_img = Image.open(color_path).convert('RGB')
    except FileNotFoundError as e:
        print(f"Error: Input file not found - {e}", file=sys.stderr)
        # Suggest creating test images for easy execution if files are missing
        if grayscale_path == 'grayscale_input.png' or color_path == 'color_input.png':
            print("\nHint: Run the 'create_test_images()' function (uncommented below) to generate the required sample files.")
        sys.exit(1)

    # Step 2: Verify that image dimensions match.
    if gray_img.size != color_img.size:
        raise ValueError("Input images must have the same x and y size.")

    # Step 3: Convert images to NumPy arrays.
    gray_arr = np.array(gray_img)
    color_arr = np.array(color_img)

    # --- Process the Color Image ---
    # Step 4: Normalize color values [0, 255] to [0.0, 1.0] for HSV conversion.
    color_norm_arr = color_arr / 255.0

    # Step 5: Convert RGB to HSV.
    hsv_arr = mcolors.rgb_to_hsv(color_norm_arr)

    # Step 6: Isolate the hue channel (0.0 to 1.0).
    hue_arr = hsv_arr[:, :, 0]

    # Step 7: Map the hue values to the grayscale range [MAP_LOW, MAP_HIGH].
    
    # 7a. Scale the hue from its range [0, HUE_VIOLET] to a normalized [0, 1].
    # Clips hues > HUE_VIOLET to the max value of the scale.
    #hue_scaled = np.clip(hue_arr, 0, HUE_VIOLET) / HUE_VIOLET
    hue_scaled = (hue_arr + 0.13) % 1.0    

    # 7b. Perform the inverse linear mapping:
    # hue_scaled=0 (Red) maps to MAP_HIGH (220).
    # hue_scaled=1 (Violet) maps to MAP_LOW (30).
    mapped_color_arr = ( MAP_HIGH - hue_scaled * (MAP_HIGH - MAP_LOW) ) -127

    # --- Combine and Save the Final Image ---
    # Step 8: Add the original grayscale values to the hue-mapped values.
    mapped_color_arr[hsv_arr[:,:,1]<0.2] = 0
    summed_arr = gray_arr.astype(float) + mapped_color_arr

    # Step 9: Constrain (clip) the final values to the valid 0-255 range.
    final_arr = np.clip(summed_arr, 0, 255)

    # Step 10: Convert to 8-bit integers and save.
    output_arr = final_arr.astype(np.uint8)
    output_img = Image.fromarray(output_arr)
    output_img.save(output_path)
    print(f"✅ Successfully created combined image at '{output_path}'")

def create_test_images(width=512, height=100):
    """Generates sample input files for testing."""
    print("⚙️  Creating test images...")
    
    # Create Grayscale Image (Black to White Gradient)
    gray_arr = np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1))
    Image.fromarray(gray_arr).save(INPUT_GRAYSCALE_PATH)

    # Create Color Image (Full Hue Spectrum)
    hsv_arr = np.zeros((height, width, 3), dtype=float)
    hsv_arr[:, :, 0] = np.linspace(0, 1, width)  # Hue
    hsv_arr[:, :, 1] = 1.0                       # Saturation
    hsv_arr[:, :, 2] = 1.0                       # Value/Brightness
    
    rgb_arr_float = mcolors.hsv_to_rgb(hsv_arr)
    rgb_arr_uint8 = (rgb_arr_float * 255).astype(np.uint8)
    Image.fromarray(rgb_arr_uint8).save(INPUT_COLOR_PATH)
    
    print(f"✅ Test images '{INPUT_GRAYSCALE_PATH}' and '{INPUT_COLOR_PATH}' created.")

# --- Main Execution ---
if __name__ == "__main__":
    # UNCOMMENT THE LINE BELOW TO CREATE SAMPLE IMAGES FOR FIRST-TIME RUNS
    # create_test_images() 

    combine_images(
        INPUT_GRAYSCALE_PATH, 
        INPUT_COLOR_PATH, 
        OUTPUT_PATH
    )