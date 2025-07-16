from typing import List, Optional, Union

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from transformers import CLIPModel, CLIPProcessor


class DinoV2ImageEncoder:
    """
    A class for encoding images into embeddings
    using models from the DINOv2 family.

    This class loads a specified DINOv2 model and its corresponding
    image transformations. It can process both single images and batches of images.

    Attributes:
        device (torch.device): The device (CPU or CUDA) on which the model is running.
        model (torch.nn.Module): The loaded DINOv2 model.
        transform (transforms.Compose): The image transformation pipeline.
    """

    def __init__(self, model_name: str = "dinov2_vitb14", device: Optional[str] = None):
        """
        Initializes the image encoder.

        Args:
            model_name (str): The name of the DINOv2 model to load.
                Available options include: 'dinov2_vits14', 'dinov2_vitb14',
                'dinov2_vitl14', 'dinov2_vitg14'.
            device (Optional[str]): The device to run the model on ('cuda', 'cpu').
                If None, it will auto-detect CUDA availability and use it,
                otherwise it will fall back to CPU.
        """
        print("Initializing DinoV2ImageEncoder...")

        self.device = self._get_device(device)
        print(f"Using device: {self.device}")

        print(f"Loading model '{model_name}'...")
        self.model = torch.hub.load("facebookresearch/dinov2", model_name)
        self.model.to(self.device)
        self.model.eval()  # Set the model to evaluation mode
        print("Model loaded successfully.")

        # Standard transformations for ViT/DINOv2 models
        self.transform = transforms.Compose(
            [
                transforms.Resize(
                    256, interpolation=transforms.InterpolationMode.BICUBIC
                ),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
                ),
            ]
        )

    def _get_device(self, device: Optional[str]) -> torch.device:
        """Determines the computation device."""
        if device and torch.cuda.is_available() and device.lower() == "cuda":
            return torch.device("cuda")
        elif device and device.lower() == "cpu":
            return torch.device("cpu")

        # Auto-select
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_and_preprocess_image(
        self, image_input: Union[str, Image.Image]
    ) -> torch.Tensor:
        """
        Loads and preprocesses a single image.

        Args:
            image_input (Union[str, Image.Image]): The path to the image file, a URL,
            or a PIL.Image object.

        Returns:
            torch.Tensor: The preprocessed image tensor.
        """
        if isinstance(image_input, str):
            image = Image.open(image_input)
        else:
            image = image_input
        image = image.convert("RGB")

        return self.transform(image)

    def encode(
        self,
        image_inputs: Union[str, Image.Image, List[Union[str, Image.Image]]],
        batch_size: int = 64,
    ) -> np.ndarray:
        """
        Encodes a single image or a batch of images into embeddings using mini-batching.

        Args:
            image_inputs (Union[str, Image.Image, List[Union[str, Image.Image]]]):
                A single image (as a path, URL, or PIL.Image) or a list of images.
            batch_size (int): The number of images to process in a single mini-batch.

        Returns:
            np.ndarray:
                A NumPy array containing the embeddings.
                - For a single image, the shape is (embedding_dim,).
                - For a list of images, the shape is (num_images, embedding_dim).
        """
        if not isinstance(image_inputs, list):
            image_inputs = [image_inputs]
            is_single_image = True
        else:
            is_single_image = False

        all_embeddings = []

        for i in range(0, len(image_inputs), batch_size):
            batch_inputs = image_inputs[i : i + batch_size]

            image_tensors = [
                self._load_and_preprocess_image(img) for img in batch_inputs
            ]
            batch_tensor = torch.stack(image_tensors).to(self.device)

            with torch.no_grad():
                embeddings = self.model(batch_tensor)

                all_embeddings.append(embeddings.cpu().numpy())

        if not all_embeddings:
            return np.array([])

        final_embeddings = np.vstack(all_embeddings)

        if is_single_image:
            return final_embeddings.squeeze(0)
        else:
            return final_embeddings


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
