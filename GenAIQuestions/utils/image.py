from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio import ImageKit 
import cairosvg 
import os


async def process_svg(svg, filepath):
    try:
        cairosvg.svg2png(bytestring=svg, write_to=filepath)
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
            file=open(image_path,"rb"),
            file_name=image_name,
            options=UploadFileRequestOptions(
                response_fields=["is_private_file", "tags"],
                tags=["tag1", "tag2"]
            )
        )     
    image_url = imagekit.url({"path": upload.file_path})
    return image_url