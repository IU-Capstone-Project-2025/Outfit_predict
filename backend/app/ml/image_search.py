import os
import tempfile
from typing import List, Tuple, Union

import numpy as np
from app.core.logging import get_logger
from app.ml.encoding_models import DinoV2ImageEncoder, FashionClipEncoder
from app.schemas.outfit import MatchedItem, RecommendedOutfit
from app.storage.qdrant_client import QdrantService
from PIL import Image

# Initialize logger for image search operations
logger = get_logger("app.ml.image_search")


class ImageSearchEngine:
    """
    Class represents an engine for searching for similar images using DINO V2 and Qdrant
    """

    def __init__(self, model_name: str = "dinov2_vitb14"):
        """Initialization of search engine with model indication

        Args:
            model_name (str): DINO V2 model name (by default, 'dinov2_vitb14')
        """
        logger.info(f"Initializing ImageSearchEngine with model: {model_name}")

        try:
            # Initialize DINO V2 encoder
            logger.debug("Loading DINO V2 model...")
            self.encoder = DinoV2ImageEncoder(model_name=model_name)

            logger.info(
                f"ImageSearchEngine initialized successfully with {model_name} on {self.encoder.device}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ImageSearchEngine: {str(e)}")
            raise

    def get_image_embeddings(
        self, images: Union[Image.Image, List[Image.Image]], batch_size: int = 32
    ) -> np.ndarray:
        """
        Create embeddings for images using DINO V2 model

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
            logger.warning("Empty image list provided for embedding generation")
            return np.array([])

        logger.debug(
            f"Generating embeddings for {len(images)} images with batch_size={batch_size}"
        )

        try:
            # Use DINO V2 encoder to generate embeddings
            embeddings = self.encoder.encode(images, batch_size=batch_size)

            # Ensure we return a 2D array even for single images
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            logger.info(f"Successfully generated embeddings: shape {embeddings.shape}")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    async def find_similar_images(
        self,
        image: Image.Image,
        qdrant: QdrantService,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Find similar images using DINO V2 embeddings and Qdrant vector search.

        Args:
            image: PIL Image to find similar images for
            qdrant: QdrantService instance
            limit: Maximum number of similar images to return
            score_threshold: Minimum similarity score threshold

        Returns:
            List of tuples containing (image_id, similarity_score)
        """
        logger.debug(
            f"Finding similar images (limit={limit}, threshold={score_threshold})"
        )

        try:
            # Create embedding for the input image
            logger.debug("Creating embedding for input image")
            query_vector = self.get_image_embeddings(image)[0]

            # Search for similar vectors in Qdrant
            logger.debug("Searching for similar vectors in Qdrant")
            similar_points = qdrant.search_vectors(
                query_vector=query_vector, limit=limit, score_threshold=score_threshold
            )

            # Extract image IDs and scores from results
            results = [(point.id, point.score) for point in similar_points]

            logger.info(
                f"Found {len(results)} similar images above threshold {score_threshold}"
            )
            if results:
                logger.debug(f"Best match score: {results[0][1]:.3f}")

            return results

        except Exception as e:
            logger.error(f"Error finding similar images: {str(e)}")
            raise

    async def add_image_to_index(
        self,
        image: Image.Image,
        image_id: str,
        outfit_id: str,
        qdrant: QdrantService,
        clothing_type: str,
    ) -> None:
        """
        Add a single image to the Qdrant index

        Args:
            image: PIL Image to add
            image_id: Unique identifier for the image
            outfit_id: ID of the outfit this image belongs to
            qdrant: QdrantService instance
            clothing_type: Optional clothing type label (from YOLO detection)
        """
        logger.debug(
            f"Adding image to index: image_id={image_id}, outfit_id={outfit_id}, clothing_type={clothing_type}"
        )

        try:
            # Create embedding
            logger.debug("Generating embedding for image")
            vector = self.get_image_embeddings(image)[0]

            # Create point with vector and metadata
            payload = {"outfit_id": outfit_id}
            if clothing_type:
                payload["clothing_type"] = clothing_type

            point = {
                "id": image_id,
                "vector": vector,
                "payload": payload,
            }

            # Upsert to Qdrant
            logger.debug("Upserting vector to Qdrant")
            qdrant.upsert_vectors([point])

            logger.info(
                f"Successfully added image to index: {image_id} with clothing_type: {clothing_type}"
            )

        except Exception as e:
            logger.error(f"Error adding image to index (image_id={image_id}): {str(e)}")
            raise

    async def find_similar_outfit_v2(
        self,
        images: List[Tuple[Image.Image, str]],  # (image, clothing_type)
        wardrobe_object_names: List[str],
        sampled_outfit_ids: List[str],
        qdrant: QdrantService,
        limit_outfits: int = 10,
    ) -> List[RecommendedOutfit]:
        """
        Finds the best-matching outfits from a sampled list for a given set of wardrobe items.
        This version uses clothing type matching to ensure correct item pairing and avoids
        using the same wardrobe item multiple times within a single outfit.

        Args:
            images: A list of tuples, each containing a PIL Image of a wardrobe item
                    and its corresponding clothing type string.
            wardrobe_object_names: A list of object names for each wardrobe item.
            sampled_outfit_ids: A list of outfit IDs to evaluate, typically pre-sampled randomly.
            qdrant: An instance of the QdrantService for vector database operations.
            limit_outfits: The maximum number of recommended outfits to return.

        Returns:
            A list of `RecommendedOutfit` objects, sorted by their completeness
            score in descending order.
        """
        logger.info(
            f"Starting new outfit recommendation for {len(images)} wardrobe items."
        )
        logger.debug(
            f"Evaluating {len(sampled_outfit_ids)} sampled outfits. Limit: {limit_outfits}"
        )

        if (
            not images
            or not wardrobe_object_names
            or len(images) != len(wardrobe_object_names)
        ):
            logger.error(
                "Wardrobe images, clothing types, or object names are missing or mismatched."
            )
            raise ValueError(
                "Invalid input: images, and wardrobe_object_names must be non-empty and have same length."
            )

        # 1. Prepare wardrobe data
        wardrobe_pil_images = [img for img, _ in images]
        wardrobe_embeddings = self.get_image_embeddings(wardrobe_pil_images)
        wardrobe_clothing_types = [ctype for _, ctype in images]

        if wardrobe_embeddings.size == 0:
            logger.warning("Could not generate embeddings for wardrobe images.")
            return []

        ranked_outfits = []

        # 2. Iterate through each sampled outfit
        for outfit_id in sampled_outfit_ids:
            logger.debug(f"Processing candidate outfit: {outfit_id}")

            outfit_item_records = qdrant.get_outfit_vectors(outfit_id)
            if not outfit_item_records:
                logger.debug(f"No item records found for outfit {outfit_id}, skipping.")
                continue

            outfit_item_embeddings = np.array([r.vector for r in outfit_item_records])
            outfit_item_ids = [r.id for r in outfit_item_records]

            # Ensure payload and clothing_type exist
            outfit_item_clothing_types = [
                r.payload.get("clothing_type", "unknown") if r.payload else "unknown"
                for r in outfit_item_records
            ]

            matched_items = []
            outfit_scores = []
            used_wardrobe_indices = set()

            # 3. For each item in the outfit, find the best match in the wardrobe
            for i in range(len(outfit_item_ids)):
                outfit_item_id = outfit_item_ids[i]
                outfit_item_embedding = outfit_item_embeddings[i]
                outfit_item_clothing_type = outfit_item_clothing_types[i]

                best_match_score = -1.0
                best_wardrobe_idx = -1

                # Search for a matching wardrobe item of the same type
                for j in range(len(wardrobe_embeddings)):
                    if (
                        wardrobe_clothing_types[j] == outfit_item_clothing_type
                        and j not in used_wardrobe_indices
                    ):
                        wardrobe_embedding = wardrobe_embeddings[j]
                        similarity_score = np.dot(
                            wardrobe_embedding, outfit_item_embedding
                        )

                        if similarity_score > best_match_score:
                            best_match_score = similarity_score
                            best_wardrobe_idx = j

                # If a match was found, record it and mark wardrobe item as used for this outfit
                if best_wardrobe_idx != -1:
                    used_wardrobe_indices.add(best_wardrobe_idx)
                    outfit_scores.append(best_match_score)

                    matched_items.append(
                        MatchedItem(
                            outfit_item_id=str(outfit_item_id),
                            wardrobe_image_index=int(best_wardrobe_idx),
                            wardrobe_image_object_name=str(
                                wardrobe_object_names[best_wardrobe_idx]
                            ),
                            score=float(best_match_score),
                        )
                    )
                else:
                    logger.debug(
                        f"No unused wardrobe item of type '{outfit_item_clothing_type}' found for outfit {outfit_id}"
                    )
                    outfit_scores.append(-10000)

            # 4. Calculate completeness score for the outfit
            if outfit_scores:
                completeness_score = float(np.mean(outfit_scores))
            else:
                completeness_score = 0.0

            # Only add outfits that have at least one match
            if matched_items:
                ranked_outfits.append(
                    RecommendedOutfit(
                        outfit_id=outfit_id,
                        completeness_score=completeness_score,
                        matches=matched_items,
                    )
                )

        # 5. Sort outfits by score and return top results
        ranked_outfits.sort(key=lambda x: x.completeness_score, reverse=True)
        result = ranked_outfits[:limit_outfits]

        logger.info(
            f"Outfit recommendation V2 completed: returning {len(result)} outfits."
        )
        if result:
            logger.debug(
                f"Best recommendation score: {result[0].completeness_score:.3f}"
            )

        return result

    async def find_similar_outfit(
        self,
        images: List[Image.Image],
        wardrobe_object_names: List[str],
        qdrant: QdrantService,
        score_threshold: float = 0.35,
        limit_outfits: int = 15,
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
        logger.info(f"Starting outfit recommendation for {len(images)} wardrobe items")
        logger.debug(
            f"Parameters: score_threshold={score_threshold}, limit_outfits={limit_outfits}"
        )

        try:
            if not images or len(images) != len(wardrobe_object_names):
                error_msg = (
                    "Mismatched number of images and object names, or lists are empty."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            # STAGE 1: CANDIDATE GENERATION
            logger.info("Stage 1: Candidate generation")
            logger.debug("Generating embeddings for all wardrobe images")

            # Get embeddings for all wardrobe images in a single batch
            wardrobe_embeddings = self.get_image_embeddings(images)
            if wardrobe_embeddings.size == 0:
                logger.warning("No embeddings generated for wardrobe images")
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

            logger.info(
                f"Found {len(candidate_outfit_ids)} candidate outfits from wardrobe matching"
            )

            if not candidate_outfit_ids:
                logger.warning("No candidate outfits found")
                return []

            # STAGE 2: RE-RANKING
            logger.info("Stage 2: Re-ranking candidate outfits")
            ranked_outfits = []

            for i, outfit_id in enumerate(candidate_outfit_ids):
                logger.debug(
                    f"Processing candidate outfit {i+1}/{len(candidate_outfit_ids)}: {outfit_id}"
                )

                # Get all item records for the candidate outfit
                outfit_item_records = qdrant.get_outfit_vectors(outfit_id)
                if not outfit_item_records:
                    logger.debug(f"No item records found for outfit {outfit_id}")
                    continue

                # Extract embeddings and IDs
                outfit_item_embeddings = np.array(
                    [record.vector for record in outfit_item_records]
                )
                outfit_item_ids = [record.id for record in outfit_item_records]

                # Calculate similarity matrix between wardrobe and outfit items
                similarity_matrix = np.dot(
                    wardrobe_embeddings, outfit_item_embeddings.T
                )

                # For each outfit item, find the best matching wardrobe item
                matched_items = []
                outfit_scores = []

                for j, outfit_item_id in enumerate(outfit_item_ids):
                    similarities = similarity_matrix[:, j]
                    best_wardrobe_idx = np.argmax(similarities)
                    best_score = similarities[best_wardrobe_idx]

                    # Create MatchedItem object with correct fields
                    matched_item = MatchedItem(
                        outfit_item_id=str(outfit_item_id),
                        wardrobe_image_index=int(best_wardrobe_idx),
                        wardrobe_image_object_name=str(
                            wardrobe_object_names[best_wardrobe_idx]
                        ),
                        score=float(best_score),
                    )
                    matched_items.append(matched_item)
                    outfit_scores.append(best_score)

                # Calculate the overall completeness score as the average of all item matches
                completeness_score = float(np.mean(outfit_scores))

                ranked_outfits.append(
                    RecommendedOutfit(
                        outfit_id=outfit_id,
                        completeness_score=completeness_score,
                        matches=matched_items,
                    )
                )

            # Sort by completeness score (descending) and return the top outfits
            ranked_outfits.sort(key=lambda x: x.completeness_score, reverse=True)
            result = ranked_outfits[:limit_outfits]

            logger.info(
                f"Outfit recommendation completed: returning {len(result)} outfits"
            )
            if result:
                logger.debug(
                    f"Best recommendation score: {result[0].completeness_score:.3f}"
                )

            return result

        except Exception as e:
            logger.error(f"Error in outfit recommendation: {str(e)}")
            raise

    async def assign_style_labels(
        self,
        outfit_images: List[Image.Image],
        fashion_encoder: FashionClipEncoder,
    ) -> List[str]:
        """
        Assign style labels to a list of outfit images using FashionCLIP.

        Args:
            outfit_images: List of PIL Images to classify
            fashion_encoder: Pre-initialized FashionClipEncoder instance

        Returns:
            List of style labels for each image
        """
        from app.ml.style_classification import identify_style

        if not outfit_images:
            return []

        # Save PIL images to temporary files since identify_style expects file paths
        temp_paths = []
        try:
            for i, pil_image in enumerate(outfit_images):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".jpg"
                ) as tmp_file:
                    pil_image.save(tmp_file.name, "JPEG")
                    temp_paths.append(tmp_file.name)

            # Get style predictions
            style_labels = identify_style(fashion_encoder, temp_paths, threshold=0.2)

            logger.info(f"Assigned style labels: {style_labels}")
            return style_labels

        finally:
            # Clean up temporary files
            for temp_path in temp_paths:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
