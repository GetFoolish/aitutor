from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio import ImageKit 
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv
import cairosvg 
import os

load_dotenv()

# Define BASE_DIR to correctly locate the assets directory
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)

async def process_svg(svg, filepath):
    svg = svg.strip()
    if svg.startswith("```svg"):
        svg = svg.removeprefix("```svg")
    if svg.endswith("```"):
        svg = svg.removesuffix("```")
    try:
        cairosvg.svg2png(bytestring=svg, write_to=str(filepath))
    except Exception as e:
       print("Unable to convert svg to png", e)
       

async def upload_to_imagekit(image_name,image_path):
    #  Put essential values of keys [UrlEndpoint, PrivateKey, PublicKey]
    imagekit = ImageKit(
        private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
        public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
        url_endpoint=os.getenv("IMAGEKIT_URL_ENDPOINT")
    )
    upload = imagekit.upload_file(
            file=open(str(image_path),"rb"),
            file_name=image_name,
            options=UploadFileRequestOptions(
                response_fields=["is_private_file", "tags"],
                tags=["tag1", "tag2"]
            )
        )     
    image_url = imagekit.url({"path": upload.file_path})
    return image_url


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
