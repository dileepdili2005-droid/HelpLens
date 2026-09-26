import os
import io
import base64
import logging
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

logger = logging.getLogger(__name__)

# Check for Tesseract availability in standard Windows/Linux locations
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    
    # Check standard Windows paths if not already in system PATH
    possible_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in possible_tesseract_paths:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break
            
    # Quick probe to test if tesseract command actually responds
    version = pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    logger.info("Tesseract OCR detected, version: %s", version)
except Exception as e:
    TESSERACT_AVAILABLE = False
    logger.info("Tesseract binary not detected (%s). Gemini Vision OCR will handle image text extraction.", str(e))

def preprocess_image(image_path, max_dim=1600):
    """
    Load image, apply EXIF orientation correction, resize if too large,
    and return an optimized PIL Image object and image metadata.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    with Image.open(image_path) as img:
        # Correct orientation based on EXIF tag
        img = ImageOps.exif_transpose(img)
        
        # Convert RGBA / P mode images to RGB for consistency
        if img.mode in ("RGBA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img.paste(img)
            img = rgb_img
        elif img.mode != "RGB":
            img = img.convert("RGB")
            
        orig_width, orig_height = img.size
        
        # Calculate new dimensions if image exceeds max_dim
        scale = 1.0
        if max(orig_width, orig_height) > max_dim:
            scale = max_dim / float(max(orig_width, orig_height))
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_width, new_height = orig_width, orig_height
            
        # Estimate image brightness (0 to 255)
        greyscale = img.convert("L")
        stat = greyscale.histogram()
        brightness = sum(i * n for i, n in enumerate(stat)) / float(greyscale.size[0] * greyscale.size[1])
        
        metadata = {
            "original_width": orig_width,
            "original_height": orig_height,
            "processed_width": new_width,
            "processed_height": new_height,
            "brightness_score": round(brightness, 1),
            "is_low_light": brightness < 60,
            "is_overexposed": brightness > 230,
            "file_size_kb": round(image_path.stat().st_size / 1024, 1),
            "ocr_engine": "Tesseract OCR" if TESSERACT_AVAILABLE else "Gemini Multimodal Vision OCR"
        }
        
        # Save optimized image back over file or to memory
        return img, metadata

def extract_text_from_image(image_path):
    """
    Extract visible text from image using local Tesseract if available,
    plus enhanced contrast preprocessing.
    """
    try:
        img, metadata = preprocess_image(image_path)
        
        if not TESSERACT_AVAILABLE:
            return {
                "text": "",
                "status": "vision_ai_delegated",
                "message": "Local Tesseract binary not present. Text, labels, and error codes will be recognized directly by Gemini Multimodal Vision.",
                "metadata": metadata
            }
            
        # Enhance contrast for OCR accuracy
        enhancer = ImageEnhance.Contrast(img)
        contrast_img = enhancer.enhance(1.4)
        
        # Run Tesseract OCR
        extracted_text = pytesseract.image_to_string(contrast_img)
        cleaned_text = extracted_text.strip()
        
        return {
            "text": cleaned_text,
            "status": "success" if cleaned_text else "no_text_found",
            "message": "Extracted text via Tesseract OCR" if cleaned_text else "No visible text detected by OCR",
            "metadata": metadata
        }
    except Exception as e:
        logger.warning("OCR processing warning: %s", str(e))
        return {
            "text": "",
            "status": "error",
            "message": f"OCR processing notice: {str(e)}",
            "metadata": {"ocr_engine": "Gemini Multimodal Vision"}
        }

def get_image_base64_and_mime(image_path):
    """
    Helper to return base64 encoded string and mime type for Gemini multimodal requests.
    """
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "bmp": "image/bmp"
    }
    mime_type = mime_types.get(ext, "image/jpeg")
    
    # Preprocess & compress to optimize payload
    img, _ = preprocess_image(image_path)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=88, optimize=True)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    return b64_str, "image/jpeg"
