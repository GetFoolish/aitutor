from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio import ImageKit 
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv
import os

# Try to import cairosvg, but make it optional (requires Cairo library on Windows)
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except (ImportError, OSError) as e:
    CAIROSVG_AVAILABLE = False
    print(f"Warning: cairosvg not available ({e}). SVG conversion will be skipped.")

# Load .env from root folder (aitutor/)
root_dir = Path(__file__).parent.parent.parent.resolve()  # aitutor/GenAIQuestions/utils -> aitutor/
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Define BASE_DIR to correctly locate the assets directory
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)

async def process_svg(svg, filepath):
    if not CAIROSVG_AVAILABLE:
        raise ImportError(
            "cairosvg is not available. Please install Cairo library:\n"
            "1. Download GTK3-Runtime from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\n"
            "2. Install it and add 'C:\\Program Files\\GTK3-Runtime Win64\\bin' to your PATH\n"
            "3. Or restart your terminal after installing GTK3"
        )
    
    svg = svg.strip()
    if svg.startswith("```svg"):
        svg = svg.removeprefix("```svg")
    if svg.endswith("```"):
        svg = svg.removesuffix("```")
    try:
        cairosvg.svg2png(bytestring=svg, write_to=str(filepath))
    except Exception as e:
       print("Unable to convert svg to png", e)
       raise
       

async def upload_to_imagekit(image_name, image_path):
    """Upload image to ImageKit and return the URL"""
    # Validate file exists and has content
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    file_size = Path(image_path).stat().st_size
    if file_size == 0:
        raise ValueError(f"Image file is empty: {image_path}")
    
    print(f"📤 Uploading {image_name} ({file_size} bytes) to ImageKit...")
    
    #  Put essential values of keys [UrlEndpoint, PrivateKey, PublicKey]
    imagekit = ImageKit(
        private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
        public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
        url_endpoint=os.getenv("IMAGEKIT_URL_ENDPOINT")
    )
    
    try:
        upload = imagekit.upload_file(
            file=open(str(image_path), "rb"),
            file_name=image_name,
            options=UploadFileRequestOptions(
                folder="/perseus-generated",
                use_unique_file_name=True,
                is_private_file=False,
                tags=["ai-generated", "perseus-question"]
            )
        )
        
        # Get the full URL - use upload.url if available, otherwise construct it
        if hasattr(upload, 'url') and upload.url:
            image_url = upload.url
        else:
            image_url = imagekit.url({"path": upload.file_path})
        
        print(f"✅ Upload successful: {image_url}")
        return image_url
        
    except Exception as e:
        print(f"❌ ImageKit upload failed: {e}")
        raise


def clean_png_files(
    recursive: bool = True,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Remove all PNG files from a directory.
    
    Args:
        directory_path: Path to the directory to clean
        recursive: If True, clean PNG files in subdirectories as well
        exclude_patterns: List of patterns to exclude from deletion
    
    Returns:
        Dictionary with 'deleted_count' and 'freed_bytes' keys
    
    Raises:
        ValueError: If directory doesn't exist or isn't a directory
    """
    directory = BASE_DIR / "assets"
    exclude_patterns = exclude_patterns or []
    
    if not directory.exists():
        raise ValueError(f"Directory {directory_path} does not exist")
    
    if not directory.is_dir():
        raise ValueError(f"{directory_path} is not a directory")
    
    deleted_count = 0
    freed_bytes = 0
    
    # Choose iteration method based on recursive flag
    if recursive:
        file_iterator = directory.rglob('*')
    else:
        file_iterator = directory.glob('*')
    
    for item in file_iterator:
        if not item.is_file():
            continue
        
        # Check if file is a PNG
        if item.suffix.lower() not in ['.png', '.PNG']:
            continue
        
        # Check if file should be excluded
        if any(pattern in str(item) for pattern in exclude_patterns):
            continue
        
        # Delete the PNG file
        try:
            file_size = item.stat().st_size
            item.unlink()
            deleted_count += 1
            freed_bytes += file_size
        except Exception:
            # Silently continue on errors (permission issues, etc.)
            continue
    
    return {
        'deleted_count': deleted_count,
        'freed_bytes': freed_bytes
    }
