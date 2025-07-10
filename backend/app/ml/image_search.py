from typing import List, Tuple, Union

import clip
import numpy as np
import torch
from app.schemas.outfit import MatchedItem, RecommendedOutfit
from app.storage.qdrant_client import QdrantService
from PIL import Image


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

    def get_image_embeddings(
        self, images: Union[Image.Image, List[Image.Image]], batch_size: int = 32
    ) -> np.ndarray:
        """
        Create embeddings for images using CLIP model

        Args:
            images: Single PIL Image or list of PIL Images to create embeddings for
            batch_size: Number of images to process in each batch (default: 32)

        Returns:
            Numpy array of shape (num_images, embedding_dim) containing the image embeddings
        """
        # Convert single image to list for uniform processing
        if isinstance(images, Image.Image):
            images = [images]

        if not images:
            return np.array([])

        all_embeddings = []

        # Process images in batches
        for i in range(0, len(images), batch_size):
            batch_images = images[i : i + batch_size]

            # Preprocess all images in the batch
            image_tensors = []
            for image in batch_images:
                image_tensor = self.preprocess(image)
                image_tensors.append(image_tensor)

            # Stack tensors and move to device
            batch_tensor = torch.stack(image_tensors).to(self.device)

            # Get embeddings for the batch
            with torch.no_grad():
                batch_embeddings = self.model.encode_image(batch_tensor)
                # Move to CPU and convert to numpy
                batch_embeddings = batch_embeddings.cpu().numpy()
                all_embeddings.append(batch_embeddings)

        # Concatenate all batch results
        if all_embeddings:
            return np.vstack(all_embeddings)
        else:
            return np.array([])

    async def find_similar_images(
        self,
        image: Image.Image,
        qdrant: QdrantService,
        limit: int = 10,
        score_threshold: float = 0.7,
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
        query_vector = self.get_image_embeddings(image)[0]

        # Search for similar vectors in Qdrant
        similar_points = qdrant.search_vectors(
            query_vector=query_vector, limit=limit, score_threshold=score_threshold
        )

        # Extract image IDs and scores from results
        results = [(point.id, point.score) for point in similar_points]

        return results

    async def add_image_to_index(
        self, image: Image.Image, image_id: str, outfit_id: str, qdrant: QdrantService
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
        vector = self.get_image_embeddings(image)[0]

        # Create point with vector and metadata
        point = {"id": image_id, "vector": vector, "payload": {"outfit_id": outfit_id}}

        # Upsert to Qdrant
        qdrant.upsert_vectors([point])

    async def find_similar_outfit(
        self,
        images: List[Image.Image],
        wardrobe_object_names: List[str],
        qdrant: QdrantService,
        score_threshold: float = 0.7,
        limit_outfits: int = 5,
    ) -> List[RecommendedOutfit]:
        """
        Finds the best-matching outfits from the database for a given set of wardrobe items.
        This method uses a two-stage process:
        1. Candidate Generation: Quickly identifies a list of potential outfits by finding outfits
           that contain at least one item similar to any of the user's wardrobe items.
        2. Re-ranking: For each candidate outfit, it calculates a "completeness score" by finding
           the best possible match from the wardrobe for *each* item in the outfit. The final
           score is the average similarity of these best matches. This ensures that the
           recommended outfits are those that can be most completely assembled from the user's wardrobe.

        Args:
            images: A list of PIL Images representing the user's wardrobe.
            wardrobe_object_names: A list of strings representing the names of the wardrobe items.
            qdrant: An instance of the QdrantService for vector database operations.
            score_threshold: The minimum similarity score for an item to be considered a match during
                             the candidate generation phase.
            limit_outfits: The maximum number of recommended outfits to return.

        Returns:
            A list of `RecommendedOutfit` objects, sorted by their completeness
            score in descending order.
            Each object includes the outfit ID, its score,
            and a list of `MatchedItem`s detailing which
            wardrobe item matches which outfit item.
        """
        if not images or len(images) != len(wardrobe_object_names):
            raise ValueError(
                "Mismatched number of images and object names, or lists are empty."
            )

        # STAGE 1: CANDIDATE GENERATION
        # Get embeddings for all wardrobe images in a single batch
        wardrobe_embeddings = self.get_image_embeddings(images)
        if wardrobe_embeddings.size == 0:
            return []

        # Find similar items for each wardrobe image and collect unique candidate outfit IDs
        candidate_outfit_ids = set()
        for i in range(wardrobe_embeddings.shape[0]):
            query_vector = wardrobe_embeddings[i].tolist()
            similar_points = qdrant.search_vectors(
                query_vector=query_vector,
                limit=50,  # Get more candidates per item
                score_threshold=score_threshold,
            )
            for point in similar_points:
                if "outfit_id" in point.payload:
                    candidate_outfit_ids.add(point.payload["outfit_id"])

        if not candidate_outfit_ids:
            return []

        # STAGE 2: RE-RANKING
        ranked_outfits = []
        for outfit_id in candidate_outfit_ids:
            # Get all item records for the candidate outfit
            outfit_item_records = qdrant.get_outfit_vectors(outfit_id)
            if not outfit_item_records:
                continue

            # Extract embeddings and IDs
            outfit_item_embeddings = np.array(
                [record.vector for record in outfit_item_records]
            )
            outfit_item_ids = [record.id for record in outfit_item_records]

            # Calculate similarity matrix between all wardrobe items and all outfit items at once
            # Shape: (num_wardrobe_items, num_outfit_items)
            similarity_matrix = np.dot(wardrobe_embeddings, outfit_item_embeddings.T)

            # For each outfit item, find the best matching wardrobe item
            best_matches_indices = np.argmax(similarity_matrix, axis=0)
            best_matches_scores = np.max(similarity_matrix, axis=0)

            # Create match details and calculate completeness score
            matches = []
            for i, outfit_item_id in enumerate(outfit_item_ids):
                wardrobe_idx = int(best_matches_indices[i])
                matches.append(
                    MatchedItem(
                        wardrobe_image_index=wardrobe_idx,
                        wardrobe_image_object_name=wardrobe_object_names[wardrobe_idx],
                        outfit_item_id=str(outfit_item_id),
                        score=float(best_matches_scores[i]),
                    )
                )

            # Score is the average of the best-match scores for each outfit item
            completeness_score = np.mean(best_matches_scores)

            ranked_outfits.append(
                RecommendedOutfit(
                    outfit_id=outfit_id,
                    completeness_score=completeness_score,
                    matches=matches,
                )
            )

        # Sort outfits by the final completeness score
        ranked_outfits.sort(key=lambda x: x.completeness_score, reverse=True)

        return ranked_outfits[:limit_outfits]
