from typing import List, Optional, Union

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


class FashionClipEncoder:
    def __init__(
        self,
        model_name: str = "patrickjohncyh/fashion-clip",
        device: Optional[str] = None,
    ) -> None:
        """
        Initializes the FashionCLIP encoder.

        Args:
            model_name: Hugging Face model identifier
            device: Optional device override ('cuda', 'cpu', or None for auto-detection)
        """
        self.device = device
        if not self.device:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

    def encode_images(
        self,
        images: List[Union[str, Image.Image]],
        batch_size: int = 32,
        verbose: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encodes images in batches.

        Args:
            images: List of image paths or PIL Images
            batch_size: Number of images to process simultaneously
            verbose: Whether to print progress
            normalize: Whether to normalize embeddings to unit vectors

        Returns:
            Numpy array of all image embeddings (len(images), embedding_dim)
        """
        if not isinstance(images, list):
            raise ValueError("Input must be a list of images")

        all_embeddings = []
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            if verbose:
                print(
                    f"Processing image batch {i // batch_size + 1}/{(len(images) - 1) // batch_size + 1}"
                )

            loaded_images = []
            for img in batch:
                if isinstance(img, str):
                    loaded_images.append(Image.open(img))
                else:
                    loaded_images.append(img)

            inputs = self.processor(
                images=loaded_images, return_tensors="pt", padding=True
            ).to(self.device)

            with torch.no_grad():
                embeddings = self.model.get_image_features(**inputs)
                if normalize:
                    embeddings = torch.nn.functional.normalize(embeddings, dim=-1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.concatenate(all_embeddings)

    def encode_texts(
        self,
        texts: List[str],
        batch_size: int = 128,
        verbose: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encodes texts in batches.

        Args:
            texts: List of text strings to encode
            batch_size: Number of texts to process simultaneously
            verbose: Whether to print progress
            normalize: Whether to normalize embeddings to unit vectors

        Returns:
            Numpy array of all text embeddings (len(texts), embedding_dim)
        """
        if not isinstance(texts, list):
            raise ValueError("Input must be a list of text strings")

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            if verbose:
                print(
                    f"Processing text batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}"
                )

            inputs = self.processor(
                text=batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77,
            ).to(self.device)

            with torch.no_grad():
                embeddings = self.model.get_text_features(**inputs)
                if normalize:
                    embeddings = torch.nn.functional.normalize(embeddings, dim=-1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.concatenate(all_embeddings)
