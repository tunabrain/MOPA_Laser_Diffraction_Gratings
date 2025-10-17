# This script converts a grayscale bitmap image into a Scalable Vector Graphics (SVG) file.
# The SVG is composed of square patches, where the angle of the parallel lines
# within each patch is determined by the grayscale value of the corresponding pixel.

import os
import webbrowser
import math
from PIL import Image

def create_svg_from_image(input_image_path, output_svg_path, patch_size=10, line_spacing=2, color_image_path=None):
    """
    Converts a grayscale image to an SVG file with patterned patches.

    Args:
        input_image_path (str): The file path to the input grayscale image (determines line angle).
        output_svg_path (str): The file path where the SVG will be saved.
        patch_size (int): The size (in millimeters) of each square patch in the SVG.
        line_spacing (int): The spacing (in millimeters) between parallel lines.
        color_image_path (str, optional): The path to a second image (determines line color).
                                          If None, lines will be black.
    """
    # Define the 21-color palette
    COLOR_PALETTE = [
        "#000000", "#0000FF", "#FF0000", "#00E000", "#D0D000", "#FF8000",
        "#00E0E0", "#FF00FF", "#B4B4B4", "#0000A0", "#A00000", "#00A000",
        "#A0A000", "#C08000", "#00A0FF", "#A000A0", "#808080", "#7D87B9",
        "#BB7784", "#4A6FE3", "#D33F6A"
    ]
    N_COLORS = len(COLOR_PALETTE)

    try:
        # 1. Load the angle image (determines rotation)
        img = Image.open(input_image_path).convert('L')
        width, height = img.size
        pixels = img.load()
    except FileNotFoundError:
        print(f"Error: The angle image file '{input_image_path}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred while opening the angle image: {e}")
        return

    # 2. Optionally load the color image
    color_pixels = None
    if color_image_path:
        try:
            color_img = Image.open(color_image_path).convert('L')
            c_width, c_height = color_img.size
            if (c_width, c_height) != (width, height):
                print(f"Warning: Color image dimensions ({c_width}x{c_height}) do not match angle image ({width}x{height}). Using black lines.")
            else:
                color_pixels = color_img.load()
        except FileNotFoundError:
            print(f"Warning: Color file '{color_image_path}' not found. Using black lines.")
        except Exception as e:
            print(f"Warning: Error loading color image: {e}. Using black lines.")

    # Calculate the total SVG dimensions in millimeters
    svg_width = width * patch_size
    svg_height = height * patch_size

    # Start the SVG file content, now with millimeters as the unit
    svg_file = open(output_svg_path, "w")
    svg_file.write(f"""<svg viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}mm" height="{svg_height}mm" xmlns="http://www.w3.org/2000/svg">""")

    # Loop through each pixel of the input image
    for y in range(height):
        for x in range(width):
            # --- ANGLE CALCULATION ---
            pixel_value = pixels[x, y]
            # Map the grayscale value (0-255) to a full 360-degree angle
            angle = ((pixel_value / 255.0) * 180 ) -90
            
            # --- COLOR DETERMINATION ---
            stroke_color = "black"
            if color_pixels:
                color_pixel_value = color_pixels[x, y]
                # Map 0-255 value to an index in the 21-color palette
                # floor((value / 256) * N) ensures 255 maps to the highest index (20)
                color_index = math.floor((color_pixel_value / 256) * N_COLORS)
                # Ensure index is within bounds (0 to 20)
                color_index = max(0, min(N_COLORS - 1, color_index))
                stroke_color = COLOR_PALETTE[color_index]


            # Calculate the top-left corner of the current patch in SVG coordinates
            patch_x = x * patch_size
            patch_y = y * patch_size

            # Start a group for the current patch to apply transformations
            # Only use a translation transform to position the patch
            svg_file.write(f"""
    <g transform="translate({patch_x}, {patch_y})">
""")
            
            # Geometry setup for line calculation
            rad_angle = math.radians(angle)
            cos_a = math.cos(rad_angle)
            sin_a = math.sin(rad_angle)
            half_size = patch_size / 2
            
            # Draw parallel lines within the patch
            # We iterate through offsets perpendicular to the line direction
            # The maximum offset is to a corner of the square
            max_offset = math.sqrt(2) * half_size
            
            i = -max_offset
            while i <= max_offset:
                line_offset = i
                
                # Coordinates for the line endpoints
                endpoints = []
                
                # The line equation is x*cos(angle) + y*sin(angle) = line_offset (in the centered system)
                # Find the intersection points with the square boundaries (-half_size to +half_size)

                # Intersection with x = -half_size (Left edge)
                if abs(sin_a) > 1e-6:
                    y_intersect = (line_offset - (-half_size) * cos_a) / sin_a
                    if -half_size <= y_intersect <= half_size:
                        endpoints.append((-half_size, y_intersect))
                
                # Intersection with x = half_size (Right edge)
                if abs(sin_a) > 1e-6:
                    y_intersect = (line_offset - (half_size) * cos_a) / sin_a
                    if -half_size <= y_intersect <= half_size:
                        endpoints.append((half_size, y_intersect))
                
                # Intersection with y = -half_size (Top edge)
                if abs(cos_a) > 1e-6:
                    x_intersect = (line_offset - (-half_size) * sin_a) / cos_a
                    if -half_size <= x_intersect <= half_size:
                        endpoints.append((x_intersect, -half_size))
                
                # Intersection with y = half_size (Bottom edge)
                if abs(cos_a) > 1e-6:
                    x_intersect = (line_offset - (half_size) * sin_a) / cos_a
                    if -half_size <= x_intersect <= half_size:
                        endpoints.append((x_intersect, half_size))
                
                # Find the two unique endpoints to define the line segment
                unique_endpoints = []
                for p in endpoints:
                    # Check for approximate uniqueness to handle floating-point issues near corners
                    if not any(math.isclose(p[0], up[0], abs_tol=1e-6) and math.isclose(p[1], up[1], abs_tol=1e-6) for up in unique_endpoints):
                        unique_endpoints.append(p)
                
                if len(unique_endpoints) == 2:
                    p1 = unique_endpoints[0]
                    p2 = unique_endpoints[1]
                    
                    # Output the line segment. The coordinates are translated from the
                    # centered system (-half_size to +half_size) to the SVG group's
                    # local system (0 to patch_size) by adding half_size.
                    svg_file.write(f"""
        <line x1="{p1[0] + half_size}" y1="{p1[1] + half_size}" x2="{p2[0] + half_size}" y2="{p2[1] + half_size}" 
              stroke="{stroke_color}" stroke-width="0.01" />
""")
                i += line_spacing
            
            # Close the group for the current patch
            svg_file.write("""
    </g>
""")

    # Close the SVG file content
    svg_file.write("</svg>")
    svg_file.close()
    
    print(f"Successfully generated SVG file: {output_svg_path}")

    # Open the SVG file in the default web browser to display it
    try:
        webbrowser.open(f"file://{os.path.abspath(output_svg_path)}")
        print("Opening the SVG file in your default web browser.")
    except Exception as e:
        print(f"Could not open the SVG file in the browser. You can view it manually at: {os.path.abspath(output_svg_path)}")

if __name__ == "__main__":
    # Example usage:
    # 1. Ensure you have a grayscale image named 'input_image.png' (for angle)
    # 2. If using color, ensure 'input_pitch_image.png' exists and has the same dimensions.
    # 3. To change the appearance, modify the patch_size and line_spacing parameters.

    input_file = "input_angle_image.png"          # Primary image (Angle)
    color_input_file = "input_pitch_image.png" # Secondary image (Color)
    output_file = "output_pattern.svg"

    # Define the global parameters for the SVG output in millimeters
    PATCH_SIZE = .4  # Size of each square patch in the SVG (in millimeters)
    LINE_SPACING = .06  # Spacing between the parallel lines

    # To generate colored output, provide the color_image_path:
    create_svg_from_image(
        input_file, 
        output_file, 
        patch_size=PATCH_SIZE, 
        line_spacing=LINE_SPACING, 
        color_image_path=color_input_file # Change this to None to generate black lines
    )
    
    # To generate black lines, you would call:
    # create_svg_from_image(input_file, output_file, patch_size=PATCH_SIZE, line_spacing=LINE_SPACING, color_image_path=None)