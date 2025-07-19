from typing import List

import numpy as np
from app.ml.encoding_models import FashionClipEncoder


def identify_style(
    encoder: FashionClipEncoder, image_paths: List[str], threshold: float = 0.2
) -> List[str]:
    style_descriptions = {
        "formal": "business formal, sharply tailored suit, polished",
        "streetwear": "streetwear, urban casual, relax",
        "minimalist": "minimal, clean, monochrome, high‑quality, neutral tones, sophisticated",
        "athleisure": "athleisure, sporty outfit",
    }
    label_items = style_descriptions.items()

    labels = [item[0] for item in label_items]
    labels.append("other")
    descriptions = [item[1] for item in label_items]

    text_embs = encoder.encode_texts(descriptions, batch_size=64, verbose=True)
    image_embs = encoder.encode_images(image_paths, batch_size=64, verbose=True)

    sim_matrix = image_embs @ text_embs.T
    predictions, confidence = np.argmax(sim_matrix, axis=1), np.max(sim_matrix, axis=1)
    predictions = np.where(confidence >= threshold, predictions, len(labels) - 1)

    predicted_labels = []
    for label_idx in predictions:
        predicted_labels.append(labels[label_idx])

    return predicted_labels
