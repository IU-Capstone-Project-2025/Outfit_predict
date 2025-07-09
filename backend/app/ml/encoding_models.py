from typing import List, Optional, Union

import clip
import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms


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


class ClipEncoder:
    """
    A high-performance embedding generator using OpenAI's CLIP models.
    Efficiently converts images and texts into semantic vector representations.

    Attributes:
        model (torch.nn.Module): Pre-trained CLIP model
        preprocess (callable): Image preprocessing pipeline
        device (torch.device): Computation device
    """

    def __init__(self, clip_model_name: str = "ViT-B/32", device: str = ""):
        """
        Initialize CLIP model and preprocessing pipeline.

        Args:
            clip_model_name (str): CLIP model variant (default: "ViT-B/32")
            device (str): Hardware device for computation
        """
        # Load CLIP model and preprocessing
        self.model, self.preprocess = clip.load(clip_model_name)

        # Configure device
        self.device = device.lower()
        if not self.device:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Move model to device
        self.model = self.model.to(self.device)
        self.model.eval()

    def get_image_embeddings(
        self,
        images: Union[Image.Image, np.ndarray, List[Union[Image.Image, np.ndarray]]],
        batch_size: int = 32,
    ) -> np.ndarray:
        """
        Generate embeddings for input images with efficient batch processing.

        Args:
            images: Single PIL.Image or list of PIL.Images
            batch_size: Processing batch size (optimize based on GPU memory)

        Returns:
            np.ndarray: Embedding matrix of shape (n_images, embedding_dim)

        Note: Embeddings are L2-normalized per CLIP's standard practice
        """
        # Normalize input to list
        if isinstance(images, Image.Image):
            images = [images]
        if isinstance(images, np.ndarray):
            images = [images]

        # Handle empty input
        if len(images) == 0:
            return np.array([])

        image_embeddings = []

        # Batch processing loop
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            batch_tensors = []

            for img in batch:
                # Convert cv2 image (BGR) to PIL Image (RGB)
                if isinstance(img, np.ndarray):
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)

                # Preprocess image
                img_tensor = self.preprocess(img)
                batch_tensors.append(img_tensor)
            # Stack tensors and move to device
            batch_tensors = torch.stack(batch_tensors).to(self.device)
            # Generate embeddings
            with torch.no_grad():
                batch_embeds = self.model.encode_image(batch_tensors)
                batch_embeds /= batch_embeds.norm(
                    dim=-1, keepdim=True
                )  # L2 normalization
                image_embeddings.append(batch_embeds.cpu().numpy())
        # Combine all batch results
        return np.vstack(image_embeddings)

    def get_texts_embeddings(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 128,
        context_length: int = 77,
    ) -> np.ndarray:
        """
            Generate embeddings for input text with efficient batch processing.

        Args:
            texts: Input string or list of strings
            batch_size: Text processing batch size (typically larger than image batches)
            context_length: Override default token limit (77 tokens)

        Returns:
            L2-normalized embeddings as numpy array (n_texts, embedding_dim)
        """
        # Input normalization
        texts = [texts] if isinstance(texts, str) else texts
        if not texts:
            return np.array([])

        # Use model's context length if not specified
        context_length = context_length

        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]

            # Tokenize with truncation
            batch_tokens = clip.tokenize(
                batch, truncate=True, context_length=context_length
            ).to(self.device)

            # Generate embeddings
            with torch.no_grad():
                batch_embeds = self.model.encode_text(batch_tokens)
                batch_embeds /= batch_embeds.norm(dim=-1, keepdim=True)
                embeddings.append(batch_embeds.cpu().numpy())

        return np.vstack(embeddings)
