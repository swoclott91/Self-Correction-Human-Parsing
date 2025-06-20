import os
import requests

TMP_DIR = "./tmp"

def download_image(image_url: str, alt_text: str) -> str:
    """
    Downloads the image from Shopify CDN and stores it locally in ./tmp.
    Returns the local file path.
    """
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)

    filename = alt_text.replace(" ", "-").replace("/", "-").lower() + ".jpg"
    path = os.path.join(TMP_DIR, filename)

    if not os.path.exists(path):
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
        else:
            raise Exception(f"Failed to download image from {image_url}")

    return path
