# This script requires the following libraries:
# pip install Pillow matplotlib numpy

from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os

# Removed the create_synthetic_image function to load an existing file instead.

def perform_manipulation(input_img, scale_factor=.01):
    """
    Performs the described image manipulation:
    1. Input=255 -> Output=255
    2. Diff=0 -> Output=127
    3. Diff<0 -> Gradient (255 -> 127) fills previous pixels
    4. Diff>0 -> Gradient (127 -> 0) fills next pixels (starting at current pixel=127)
    """
    
    # Ensure the image is grayscale ('L' mode)
    if input_img.mode != 'L':
        print("Warning: Input image is not in 'L' (grayscale) mode. Converting...")
        input_img = input_img.convert('L')
        
    # Convert image to a NumPy array for fast pixel access and manipulation
    # Use uint16 to prevent overflow when calculating differences (0-255 range)
    img_array = np.array(input_img, dtype=np.uint16)
    H, W = img_array.shape

    # Initialize output array. Using float32 for precise gradient values.
    # FIX: Initialize the array to 127.0 instead of 0.0. This ensures that any pixel 
    # corresponding to Diff=0 (Rule 2) which might be skipped by the gradient logic, 
    # or the first pixel, defaults correctly to the neutral gray 127.
    output_array = np.full((H, W), 255.0, dtype=np.float32)

    # Flatten the arrays for sequential scanning (left-to-right, line-by-line)
    I_flat = img_array.flatten()
    O_flat = output_array.ravel()
    total_pixels = len(I_flat)

    # The input pixel value from the *previous* step, used for difference calculation.
    I_prev = 255

    # Start scanning through every pixel
    i = 0
    while i < total_pixels-1:
        i = i+1
        I_curr = I_flat[i]
        
        # Handle the very first pixel (i=0) separately
        if i == 1:
            # I_prev is initialized to 0. Any initial rise will trigger Rule 4 
            # for the *next* pixel's calculation.
            I_prev = I_curr
            continue

        # --- Calculate Difference for Rules 2, 3, 4 ---
        # I_prev holds the value of the pixel *immediately* before the current one in the scan order
        # FIX: Explicitly cast to Python's native integer type for subtraction to avoid 
        # NumPy RuntimeWarning when subtracting unsigned integers that result in a negative value.
        Diff = int(I_curr) - int(I_prev)
        
        
        if Diff == 0:
            # --- Rule 2: Difference is zero (Output is 127) ---
            # Explicitly set to 127.0 to ensure it overrides any gradient value written 
            # by an earlier Rule 4 trigger.
            if I_curr == 255:
               O_flat[i] = 255
            else:
               O_flat[i] = 127.0
            
        elif Diff < 0 and int(I_prev) == 255:
            # --- Rule 3: Negative difference.  Leading edge of object
            Diff = int(I_curr) - 127
            Magnitude = abs(Diff)
            Length = int(Magnitude * scale_factor)

            # The gradient spans from index 'start_index' to the current index 'i' (inclusive).
            start_index = max(0, i - Length)
            
            # Number of points in the gradient (i.e., the length of the segment being overwritten)
            num_points = i - start_index + 1
            
            # Generate linear gradient from 255 (left/start) to 127 (right/current pixel)
            if num_points > 1:
                if int(I_curr) < 127:
                   gradient = np.linspace(255, 127, num_points, dtype=np.float32)
                else:
                   gradient = np.linspace(0, 127, num_points, dtype=np.float32)
                # Overwrite segment [start_index, i]
                O_flat[start_index:i+1] = gradient
            else:
                # If Length=0, just set the current pixel to 127
                O_flat[i] = 127.0
                

        elif Diff > 0 and int(I_curr) == 255:
            # --- Rule 4: Positive difference.  Trailing edge
            Diff = int(I_prev) - 127
            Magnitude = abs(Diff)
            Length = int(Magnitude * scale_factor)
            
            # The current pixel is set to 127 (start of the forward-looking gradient)
            O_flat[i] = 127.0
            
            # The gradient spans from index 'i' to 'end_index' (inclusive), where the value is 0.
            end_index = min(total_pixels - 1, i + Length)
            
            # Number of points in the gradient (i.e., the length of the segment being overwritten)
            num_points = end_index - i + 1
            
            if num_points > 1:
                # Generate linear gradient from 127 (current pixel) to 0 (end point)
                if int(I_prev) < 127:
                   gradient = np.linspace(127, 0, num_points, dtype=np.float32)
                else:
                   gradient = np.linspace(127, 255, num_points, dtype=np.float32)
                
                # Overwrite the segment, starting from the current pixel 'i'
                O_flat[i:end_index + 1] = gradient
                
                i = i + num_points
                I_prev = I_flat[i-1]
            else:
                 O_flat[i] = 127.0
            
        else:
          O_flat[i] = 127;


        # Update I_prev for the next iteration
        I_prev = I_curr
        

    # Final step: Reshape the array back to 2D, clamp to 0-255, and convert to uint8
    output_array = np.clip(output_array, 0, 255).astype(np.uint8)
    output_img = Image.fromarray(output_array, 'L').convert('RGB')
    
    return output_img

def display_images(img1, title1, img2, title2):
    """Displays two images side-by-side using Matplotlib."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # Display Input Image
    axes[0].imshow(img1, cmap='gray')
    axes[0].set_title(title1)
    axes[0].axis('off')

    # Display Output Image
    axes[1].imshow(img2, cmap='gray')
    axes[1].set_title(title2)
    axes[1].axis('off')

    plt.tight_layout()
    plt.show()

# --- Main Execution ---
if __name__ == "__main__":
    # --- Configuration ---
    # Change this filename to the path of your grayscale PNG image
    INPUT_FILENAME = "my_image.png"
    OUTPUT_FILENAME = "processed_output.png"
    SCALE_FACTOR = .06 # Used to determine gradient length: Length = |Diff| * SCALE_FACTOR

    try:
        # 1. Load the input image
        print(f"-> Attempting to load input image: {INPUT_FILENAME}")
        input_image = Image.open(INPUT_FILENAME)
        
        # 2. Perform the manipulation
        print(f"-> Performing manipulation with SCALE_FACTOR={SCALE_FACTOR}...")
        output_image = perform_manipulation(input_image, scale_factor=SCALE_FACTOR)
        
        # 3. Save the output image
        output_image.save(OUTPUT_FILENAME)
        print(f"-> Output image saved as: {OUTPUT_FILENAME}")
        
        # 4. Display both images
        display_images(
            input_image, f"Input Image ({input_image.mode})",
            output_image, "Output Processed Image (L)"
        )

    except FileNotFoundError:
        print(f"\nError: Input file '{INPUT_FILENAME}' not found.")
        print("Please ensure the file exists in the correct directory or update the INPUT_FILENAME variable.")
        print("Note: The input image will be automatically converted to grayscale ('L' mode) if it's not already.")
    except ImportError as e:
        print(f"\nError: {e}")
        print("Please install the required libraries: pip install Pillow matplotlib numpy")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
