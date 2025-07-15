import requests
from typing import List

GOOGLE_API_URL = "https://www.googleapis.com/customsearch/v1"

# Для работы нужны GOOGLE API_KEY и CX (идентификатор поискового движка)
import os
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

def search_images_google(query: str, api_key: str = None, cx: str = None, num: int = 5) -> List[str]:
    """
    Search for images using Google Custom Search API by text query.
    Returns a list of image URLs.
    """
    api_key = api_key or GOOGLE_API_KEY
    cx = cx or GOOGLE_CX
    if not api_key or not cx:
        raise ValueError("Google API key and CX must be set.")
    params = {
        "q": query,
        "searchType": "image",
        "key": api_key,
        "cx": cx,
        "num": num
    }
    response = requests.get(GOOGLE_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return [item["link"] for item in data.get("items", [])] 