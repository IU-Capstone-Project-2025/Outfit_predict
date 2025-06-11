from sklearn.neighbors import NearestNeighbors
from PIL import Image
import numpy as np
import torch
import clip
import os


class ImageSearchEngine:
    """
    Class represents an engine for searching for similar images using CLIP
    """

    def __init__(self, model_name: str):
        """Initialization of search engine with model indication

        Args:
            model_name (str): CLIP model name (by default, 'ViT-B/32')
        """
        # Load clip model
        self.model, self.preprocess = clip.load(model_name)
        self.image_embeddings = []
        self.image_paths = []

    def create_embeddings(self, image_folder):
        """Create embeddings of images located at indicated folder

        Args:
            image_folder (str): Path to the folder with images
        """
        # Get image files from folder
        image_files = [img for img in os.listdir(image_folder)
                       if img.endswith(('.jpg', '.png', '.jpeg'))]

        for img_file in image_files:
            try:
                image_path = os.path.join(image_folder, img_file)
                # Open and preprocess (for CLIP model input) image
                image = self.preprocess(Image.open(image_path)).unsqueeze(0)
                # Get embeddings for images
                with torch.no_grad():
                    embedding = self.model.encode_image(image).numpy()
                # Save image embedding and path
                self.image_embeddings.append(embedding)
                self.image_paths.append(image_path)
            except Exception as error:
                print(f"Error processing {img_file}: {error}")

        # Get embeddings in matrix form (n_images x embedding_dimension)
        self.image_embeddings = np.vstack(self.image_embeddings)
        print(f"Embeddings are created. Total number of embeddings: {len(image_files)}")

    def find_similar(self, target_image_path, top_k=3) -> list:
        """Search for top_k similar images to the target one

        Args:
            target_image_path (str): Path to target image
            top_k (int): Number of top similar returned images

        Returns:
            list: list of tuples of the form (image_path, distance)
        """
        # Image processing
        target_image = self.preprocess(Image.open(target_image_path)).unsqueeze(0)
        # Get image embedding
        with torch.no_grad():
            query_embedding = self.model.encode_image(target_image).numpy()

        # Create and learn model for searching for the most similar embeddings
        knn = NearestNeighbors(n_neighbors=top_k, metric='cosine')
        knn.fit(self.image_embeddings)

        # Get the most similar embeddings
        distances, indices = knn.kneighbors(query_embedding)

        return [(self.image_paths[indices[0][i]], 1 - distances[0][i])
                for i in range(len(indices[0]))]


def initialize_image_search_engine(image_folder: str, model_name: str = "ViT-B/32") -> ImageSearchEngine:
    """Initialization of the image search engine

    Args:
        image_folder (str): image_folder (str): Path to the folder with images
        model_name (str): CLIP model name (by default, 'ViT-B/32')

    Returns:
        ImageSearchEngine: Initialized image search engine
    """
    search_engine = ImageSearchEngine(model_name)
    search_engine.create_embeddings(image_folder)
    return search_engine
