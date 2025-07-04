import os
import gc
import time
import random
import traceback
import mlx.core as mx
from PIL import Image
import numpy as np
from pathlib import Path
import json
from mflux.config.config import Config
from backend.mlx_utils import force_mlx_cleanup, print_memory_usage
from backend.flux_manager import parse_scale_factor

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def upscale_image(image_path, upscale_factor=2):
    """
    Upscale an image using MFLUX upscaler.
    """
    try:
        from mflux.upscaler.upscaler import Upscaler
        
        # Load the image
        image = Image.open(image_path).convert("RGB")
        
        # Initialize upscaler
        upscaler = Upscaler()
        
        # Upscale the image
        upscaled = upscaler.upscale(image, scale_factor=upscale_factor)
        
        return upscaled
        
    except Exception as e:
        print(f"Error upscaling image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def upscale_image_gradio(
    input_image, upscale_factor, output_format, metadata
):
    """
    Upscale an image using the MFLUX upscaler.
    """
    try:
        # Parse inputs
        if not input_image:
            return None, "Error: Input image is required"
        
        # Get original image dimensions
        original_image = Image.open(input_image)
        original_width, original_height = original_image.width, original_image.height
        
        # Parse upscale factor (can be scale factor like "2x" or absolute value)
        if isinstance(upscale_factor, str) and upscale_factor.strip():
            # Try to parse as scale factor
            if upscale_factor.strip().lower().endswith('x'):
                try:
                    scale = float(upscale_factor.strip().lower().replace('x', ''))
                    upscale_factor_int = int(scale)
                except ValueError:
                    upscale_factor_int = 2
            else:
                try:
                    upscale_factor_int = int(float(upscale_factor))
                except ValueError:
                    upscale_factor_int = 2
        else:
            upscale_factor_int = int(upscale_factor) if upscale_factor else 2
        
        # Validate upscale factor
        if upscale_factor_int not in [2, 3, 4]:
            return None, "Error: Upscale factor must be 2, 3, or 4"
            
        # Upscale the image
        print(f"Upscaling image with factor {upscale_factor_int}x")
        upscaled_image = upscale_image(input_image, upscale_factor_int)
        
        if upscaled_image is None:
            return None, "Error: Failed to upscale image"
            
        # Save the upscaled image
        timestamp = int(time.time())
        
        # Determine file extension
        if output_format == "PNG":
            ext = "png"
            save_kwargs = {"format": "PNG"}
        elif output_format == "JPEG":
            ext = "jpg"
            save_kwargs = {"format": "JPEG", "quality": 95}
        else:  # WebP
            ext = "webp"
            save_kwargs = {"format": "WebP", "quality": 95}
            
        filename = f"upscaled_{upscale_factor_int}x_{timestamp}.{ext}"
        output_path = os.path.join(OUTPUT_DIR, filename)
        upscaled_image.save(output_path, **save_kwargs)
        
        # Save metadata if requested
        if metadata:
            metadata_path = os.path.join(OUTPUT_DIR, f"upscaled_{upscale_factor_int}x_{timestamp}.json")
            
            # Get original image info
            original_image = Image.open(input_image)
            
            metadata_dict = {
                "original_width": original_image.width,
                "original_height": original_image.height,
                "upscaled_width": upscaled_image.width,
                "upscaled_height": upscaled_image.height,
                "upscale_factor": upscale_factor_int,
                "output_format": output_format,
                "generation_time": str(time.ctime()),
                "original_file": os.path.basename(input_image)
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f, indent=2)
                
        print(f"Upscaled image saved to {output_path}")
        
        # Return both the image and a success message
        info_message = f"Successfully upscaled image {upscale_factor_int}x to {upscaled_image.width}x{upscaled_image.height}"
        return upscaled_image, info_message
        
    except Exception as e:
        print(f"Error in upscaling: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, f"Error: {str(e)}"
        
    finally:
        # Cleanup
        gc.collect()
        force_mlx_cleanup()

# Expose this module as `upscale_manager`
import sys as _sys
upscale_manager = _sys.modules[__name__]

def upscale_with_custom_dimensions_gradio(
    input_image, target_width, target_height, output_format, metadata
):
    """
    Upscale an image to custom dimensions using scale factors or absolute values.
    """
    try:
        if not input_image:
            return None, "Error: Input image is required"
        
        # Get original image dimensions
        original_image = Image.open(input_image)
        original_width, original_height = original_image.width, original_image.height
        
        # Parse target dimensions
        final_width = parse_scale_factor(target_width, original_width)
        final_height = parse_scale_factor(target_height, original_height)
        
        # Calculate effective scale factor
        scale_x = final_width / original_width
        scale_y = final_height / original_height
        
        # Use the larger scale factor to maintain aspect ratio
        effective_scale = max(scale_x, scale_y)
        
        # Round to nearest supported scale factor
        if effective_scale <= 2.5:
            upscale_factor_int = 2
        elif effective_scale <= 3.5:
            upscale_factor_int = 3
        else:
            upscale_factor_int = 4
        
        # Upscale the image
        print(f"Upscaling image with factor {upscale_factor_int}x to target {final_width}x{final_height}")
        upscaled_image = upscale_image(input_image, upscale_factor_int)
        
        if upscaled_image is None:
            return None, "Error: Failed to upscale image"
        
        # Resize to exact target dimensions if needed
        if upscaled_image.width != final_width or upscaled_image.height != final_height:
            upscaled_image = upscaled_image.resize((final_width, final_height), Image.Resampling.LANCZOS)
        
        # Save the upscaled image
        timestamp = int(time.time())
        
        # Determine file extension
        if output_format == "PNG":
            ext = "png"
            save_kwargs = {"format": "PNG"}
        elif output_format == "JPEG":
            ext = "jpg"
            save_kwargs = {"format": "JPEG", "quality": 95}
        else:  # WebP
            ext = "webp"
            save_kwargs = {"format": "WebP", "quality": 95}
            
        filename = f"upscaled_custom_{final_width}x{final_height}_{timestamp}.{ext}"
        output_path = os.path.join(OUTPUT_DIR, filename)
        upscaled_image.save(output_path, **save_kwargs)
        
        # Save metadata if requested
        if metadata:
            metadata_path = os.path.join(OUTPUT_DIR, f"upscaled_custom_{final_width}x{final_height}_{timestamp}.json")
            
            metadata_dict = {
                "original_width": original_width,
                "original_height": original_height,
                "upscaled_width": upscaled_image.width,
                "upscaled_height": upscaled_image.height,
                "target_width": target_width,
                "target_height": target_height,
                "effective_scale": effective_scale,
                "upscale_factor_used": upscale_factor_int,
                "output_format": output_format,
                "generation_time": str(time.ctime()),
                "original_file": os.path.basename(input_image)
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f, indent=2)
                
        print(f"Upscaled image saved to {output_path}")
        
        # Return both the image and a success message
        info_message = f"Successfully upscaled image to {upscaled_image.width}x{upscaled_image.height}"
        return upscaled_image, info_message
        
    except Exception as e:
        print(f"Error in custom upscaling: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, f"Error: {str(e)}"
        
    finally:
        # Cleanup
        gc.collect()
        force_mlx_cleanup()

def batch_upscale_gradio(
    input_images, upscale_factor, output_format, metadata
):
    """
    Batch upscale multiple images.
    """
    try:
        if not input_images:
            return [], "Error: No images provided"
            
        upscaled_images = []
        errors = []
        
        for idx, image_path in enumerate(input_images):
            try:
                print(f"Processing image {idx+1}/{len(input_images)}")
                
                # Upscale individual image
                upscaled, message = upscale_image_gradio(
                    image_path, upscale_factor, output_format, metadata
                )
                
                if upscaled:
                    upscaled_images.append(upscaled)
                else:
                    errors.append(f"Image {idx+1}: {message}")
                    
            except Exception as e:
                errors.append(f"Image {idx+1}: {str(e)}")
                
        if upscaled_images:
            success_msg = f"Successfully upscaled {len(upscaled_images)} image(s)"
            if errors:
                success_msg += f"\n\nErrors:\n" + "\n".join(errors)
            return upscaled_images, success_msg
        else:
            return [], "Failed to upscale any images\n\n" + "\n".join(errors)
            
    except Exception as e:
        print(f"Error in batch upscaling: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], f"Error: {str(e)}"
