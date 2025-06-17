from PIL import Image
import torch
import clip
from typing import List, Tuple
from collections import Counter
from app.storage.qdrant_client import QdrantService


class ImageSearchEngine:
    """
    Class represents an engine for searching for similar images using CLIP and Qdrant
    """

    def __init__(self, model_name: str = "ViT-B/32"):
        """Initialization of search engine with model indication

        Args:
            model_name (str): CLIP model name (by default, 'ViT-B/32')
        """
        # Load clip model
        self.model, self.preprocess = clip.load(model_name)
        # Move model to GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        # Set model to evaluation mode
        self.model.eval()

    def get_image_embedding(self, image: Image.Image) -> List[float]:
        """
        Create embedding for a single image using CLIP model

        Args:
            image: PIL Image to create embedding for

        Returns:
            List of floats representing the image embedding
        """
        # Preprocess image and move to device
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        # Get embedding
        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor)
            # Move to CPU and convert to list
            embedding = embedding.cpu().numpy()[0].tolist()

        return embedding

    async def find_similar_images(
            self,
            image: Image.Image,
            qdrant: QdrantService,
            limit: int = 10,
            score_threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Find similar images using CLIP embeddings and Qdrant vector search.

        Args:
            image: PIL Image to find similar images for
            qdrant: QdrantService instance
            limit: Maximum number of similar images to return
            score_threshold: Minimum similarity score threshold

        Returns:
            List of tuples containing (image_id, similarity_score)
        """
        # Create embedding for the input image
        query_vector = self.get_image_embedding(image)

        # Search for similar vectors in Qdrant
        similar_points = qdrant.search_vectors(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )

        # Extract image IDs and scores from results
        results = [(point.id, point.score) for point in similar_points]

        return results

    async def add_image_to_index(
            self,
            image: Image.Image,
            image_id: str,
            outfit_id: str,
            qdrant: QdrantService
    ) -> None:
        """
        Add a single image to the Qdrant index

        Args:
            image: PIL Image to add
            image_id: Unique identifier for the image
            outfit_id: ID of the outfit this image belongs to
            qdrant: QdrantService instance
        """
        # Create embedding
        vector = self.get_image_embedding(image)

        # Create point with vector and metadata
        point = {
            "id": image_id,
            "vector": vector,
            "payload": {
                "outfit_id": outfit_id
            }
        }

        # Upsert to Qdrant
        qdrant.upsert_vectors([point])

    async def find_similar_outfit(
            self,
            images: List[Image.Image],
            qdrant: QdrantService,
            score_threshold: float = 0.7,
            limit_outfits: int = 5,
            min_common_images: int = 2
    ) -> List[Tuple[str, float]]:
        """
        Find outfits that have similar images to all query images

        Args:
            images: List of query images (1-8 images)
            qdrant: Qdrant client
            score_threshold: Minimum similarity score threshold (0.0 to 1.0)
            limit_outfits: Maximum number of returned outfits
            min_common_images: Minimum number of query images that should have matches

        Returns:
            List of (outfit_id, average_similarity_score) tuples, sorted by score
        """
        if not 1 <= len(images) <= 8:
            raise ValueError("Number of images must be between 1 and 8")

        # Get similar images for each query image
        all_similar_images = []
        for image in images:
            similar = await self.find_similar_images(
                image=image,
                qdrant=qdrant,
                score_threshold=score_threshold
            )
            all_similar_images.append(similar)

        # Count outfit_ids and collect scores
        outfit_scores = Counter()
        outfit_counts = Counter()

        for similar_images in all_similar_images:
            # Get unique outfit_ids for this query image's results
            seen_outfits = set()
            for image_id, score in similar_images:
                # Get outfit_id from Qdrant
                point = qdrant.get_point(image_id)
                outfit_id = point.payload["outfit_id"]

                # Only count each outfit once per query image
                if outfit_id not in seen_outfits:
                    outfit_scores[outfit_id] += score
                    outfit_counts[outfit_id] += 1
                    seen_outfits.add(outfit_id)

        # Calculate average scores and filter by minimum common images
        results = []
        for outfit_id, count in outfit_counts.items():
            if count >= min_common_images:
                avg_score = outfit_scores[outfit_id] / count
                results.append((outfit_id, avg_score))

        # Sort by average score in descending order
        return sorted(results, key=lambda x: x[1], reverse=True)[:limit_outfits]
