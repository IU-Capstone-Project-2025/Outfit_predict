from typing import List

import torch
from app.ml.encoding_models import FashionClipEncoder
from PIL import Image


def identify_clothes_type(
    encoder: FashionClipEncoder, images: List[Image.Image]
) -> List[str]:
    """
    Identify the clothing type for each image using FashionCLIP.

    Args:
        encoder: FashionClipEncoder instance
        images: List of PIL Images to classify

    Returns:
        List of clothing type labels, one for each input image
    """
    classes_text = [
        "a photo of a sunglass",
        "a photo of a hat",
        "a photo of a jacket",
        "a photo of a shirt",
        "a photo of a pants",
        "a photo of a shorts",
        "a photo of a skirt",
        "a photo of a dress",
        "a photo of a bag",
        "a photo of a shoe",
    ]

    classes = [
        "sunglass",
        "hat",
        "jacket",
        "shirt",
        "pants",
        "shorts",
        "skirt",
        "dress",
        "bag",
        "shoe",
    ]

    if not images:
        return []

    # Use classes_text for the actual text prompts
    inputs = encoder.processor(
        text=classes_text, images=images, return_tensors="pt", padding=True
    ).to(encoder.device)

    with torch.no_grad():
        outputs = encoder.model(**inputs)
        logits = outputs.logits_per_image  # Shape: [num_images, num_classes]
        probs = logits.softmax(dim=1)

    # Get the predicted class index for each image
    predicted_indices = torch.argmax(probs, dim=1)

    # Convert indices to class labels
    labels = [classes[idx.item()] for idx in predicted_indices]

    return labels
