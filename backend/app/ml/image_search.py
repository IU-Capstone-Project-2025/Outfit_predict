import asyncio
import os
import tempfile
from typing import List, Tuple, Union

import numpy as np
from app.core.logging import get_logger
from app.ml.encoding_models import FashionClipEncoder
from app.schemas.outfit import MatchedItem, RecommendedOutfit
from app.storage.qdrant_client import QdrantService
from PIL import Image

# Initialize logger for image search operations
logger = get_logger("app.ml.image_search")

COMPLEMENT_OUTFIT_DICT = {
    "sunglass": {
        "product_link": "https://www.lamoda.ru/p/mp002xu03gxl/accs-grandvoyage-ochki-solntsezaschitnye/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XU03GXL_12283458_1_v2.jpg",
    },
    "hat": {
        "product_link": "https://www.lamoda.ru/p/mp002xb07r81/accs-lcwaikiki-shlyapa/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XB07R81_28627118_1_v1_2x.jpg",
    },
    "jacket": {
        "product_link": "https://www.lamoda.ru/p/mp002xm0bk4i/clothes-oodji-pidzhak/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XM0BK4I_24439180_1_v1.jpeg",
    },
    "shirt": {
        "product_link": "https://www.lamoda.ru/p/mp002xm0viqh/clothes-kanzler-rubashka/?promotion_provider_id=30fff14b-0d4c-4580-a353-68bf0c477993",  # noqa: E501
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XM0VIQH_22043826_1_v1.jpeg",
    },
    "pants": {
        "product_link": "https://www.lamoda.ru/p/mp002xm0bi76/clothes-hibio-bryuki/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XM0BI76_24348073_1_v1.jpeg",
    },
    "shorts": {
        "product_link": "https://www.lamoda.ru/p/mp002xm0d0gi/clothes-alpex-shorty-sportivnye/?promotion_provider_id=450cd72c-2db7-4ae2-8b3a-40c44a4dc010",  # noqa: E501
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XM0D0GI_26852591_1_v2_2x.jpg",
    },
    "skirt": {
        "product_link": "https://www.lamoda.ru/p/mp002xw1fogz/clothes-sela-yubka/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XW1FOGZ_26465959_1_v3_2x.jpg",
    },
    "dress": {
        "product_link": "https://www.lamoda.ru/p/mp002xw17r8r/clothes-sela-plate/",
        "image_link": "https://a.lmcdn.ru/product/M/P/MP002XW17R8R_24390173_1_v1_2x.jpg",
    },
    "bag": {
        "product_link": "https://www.lamoda.ru/p/rtlabh953303/bags-robertarossi-sumka-i-brelok/",
        "image_link": "https://a.lmcdn.ru/product/R/T/RTLABH953303_21498981_1_v1.jpg",
    },
    "shoe": {
        "product_link": "https://www.lamoda.ru/p/rtlacz458203/shoes-reebok-kedy/",
        "image_link": "https://a.lmcdn.ru/product/R/T/RTLADZ894701_25971334_1_v1_2x.jpg",
    },
}


class ImageSearchEngine:
    """
    Class represents an engine for searching for similar images using FashionCLIP and Qdrant
    """

    def __init__(self, model_name: str = "patrickjohncyh/fashion-clip"):
        """Initialization of search engine with FashionCLIP model

        Args:
            model_name (str): FashionCLIP model name (by default, 'patrickjohncyh/fashion-clip')
        """
        logger.info(f"Initializing ImageSearchEngine with model: {model_name}")

        try:
            # Initialize FashionCLIP encoder
            logger.debug("Loading FashionCLIP model...")
            self.encoder = FashionClipEncoder(model_name=model_name)

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
        Create embeddings for images using FashionCLIP model

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
            # Use FashionCLIP encoder to generate embeddings
            embeddings = self.encoder.encode_images(
                images, batch_size=batch_size, normalize=True
            )

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
        collection_name: str = None,  # type: ignore
    ) -> List[Tuple[str, float]]:
        """
        Find similar images using FashionCLIP embeddings and Qdrant vector search.

        Args:
            image: PIL Image to find similar images for
            qdrant: QdrantService instance
            limit: Maximum number of similar images to return
            score_threshold: Minimum similarity score threshold
            collection_name: Qdrant collection to search (default: outfit collection)

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
                query_vector=query_vector.tolist(),
                limit=limit,
                score_threshold=score_threshold,
                collection_name=collection_name,
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
        Add a single image to the outfit Qdrant index

        Args:
            image: PIL Image to add
            image_id: Unique identifier for the image
            outfit_id: ID of the outfit this image belongs to
            qdrant: QdrantService instance
            clothing_type: Optional clothing type label (from YOLO detection)
        """
        logger.debug(
            f"Adding image to outfit index: image_id={image_id}, outfit_id={outfit_id}, clothing_type={clothing_type}"
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
                "vector": vector.tolist(),
                "payload": payload,
            }

            # Upsert to Qdrant outfit collection
            logger.debug("Upserting vector to Qdrant outfit collection")
            qdrant.upsert_vectors(
                [point], collection_name=qdrant.outfit_collection_name
            )

            logger.info(
                f"Successfully added image to outfit index: {image_id} with clothing_type: {clothing_type}"
            )

        except Exception as e:
            logger.error(
                f"Error adding image to outfit index (image_id={image_id}): {str(e)}"
            )
            raise

    async def add_wardrobe_image_to_index(
        self,
        image: Image.Image,
        image_id: str,
        user_id: str,
        object_name: str,
        qdrant: QdrantService,
        clothing_type: str,
    ) -> None:
        """
        Add a single wardrobe image to the wardrobe Qdrant index

        Args:
            image: PIL Image to add
            image_id: Unique identifier for the image
            user_id: ID of the user who owns this image
            object_name: Object name in MinIO storage
            qdrant: QdrantService instance
            clothing_type: Clothing type label
        """
        logger.debug(
            f"Adding wardrobe image to index: image_id={image_id}, user_id={user_id}, object_name={object_name},\
                clothing_type={clothing_type}"
        )

        try:
            # Create embedding
            logger.debug("Generating embedding for wardrobe image")
            vector = self.get_image_embeddings(image)[0]

            # Create point with vector and metadata
            payload = {
                "user_id": user_id,
                "object_name": object_name,
                "clothing_type": clothing_type,
            }

            point = {
                "id": image_id,
                "vector": vector.tolist(),
                "payload": payload,
            }

            # Upsert to Qdrant wardrobe collection
            logger.debug("Upserting vector to Qdrant wardrobe collection")
            qdrant.upsert_vectors(
                [point], collection_name=qdrant.wardrobe_collection_name
            )

            logger.info(
                f"Successfully added wardrobe image to index: {image_id} with clothing_type: {clothing_type}"
            )

        except Exception as e:
            logger.error(
                f"Error adding wardrobe image to index (image_id={image_id}): {str(e)}"
            )
            raise

    async def _process_outfit(
        self,
        outfit_id: str,
        qdrant: "QdrantService",
        wardrobe_embeddings: np.ndarray,
        wardrobe_clothing_types: List[str],
        wardrobe_object_names_actual: List[str],
    ) -> Union[RecommendedOutfit, None]:
        """Processes a single outfit to find matches in the wardrobe."""
        logger.debug(f"Processing candidate outfit: {outfit_id}")

        outfit_item_records = await asyncio.to_thread(
            qdrant.get_outfit_vectors, outfit_id
        )
        if not outfit_item_records:
            logger.debug(f"No item records found for outfit {outfit_id}, skipping.")
            return None

        outfit_item_embeddings = np.array([r.vector for r in outfit_item_records])
        outfit_item_ids = [r.id for r in outfit_item_records]

        outfit_item_clothing_types = [
            r.payload.get("clothing_type", "unknown") if r.payload else "unknown"
            for r in outfit_item_records
        ]

        matched_items = []
        outfit_scores = []
        used_wardrobe_indices = set()

        for i in range(len(outfit_item_ids)):
            outfit_item_id = outfit_item_ids[i]
            outfit_item_embedding = outfit_item_embeddings[i]
            outfit_item_clothing_type = outfit_item_clothing_types[i]

            best_match_score = -1.0
            best_wardrobe_idx = -1

            for j in range(len(wardrobe_embeddings)):
                if (
                    wardrobe_clothing_types[j] == outfit_item_clothing_type
                    and j not in used_wardrobe_indices
                ):
                    wardrobe_embedding = wardrobe_embeddings[j]
                    similarity_score = np.dot(wardrobe_embedding, outfit_item_embedding)

                    if similarity_score > best_match_score:
                        best_match_score = similarity_score
                        best_wardrobe_idx = j

            if best_wardrobe_idx != -1:
                used_wardrobe_indices.add(best_wardrobe_idx)
                outfit_scores.append(best_match_score)

                matched_items.append(
                    MatchedItem(
                        outfit_item_id=str(outfit_item_id),
                        wardrobe_image_index=int(best_wardrobe_idx),
                        wardrobe_image_object_name=str(
                            wardrobe_object_names_actual[best_wardrobe_idx]
                        ),
                        score=float(best_match_score),
                    )
                )
            else:
                logger.debug(
                    f"No unused wardrobe item of type '{outfit_item_clothing_type}' found for outfit {outfit_id}"
                )
                suggestion = COMPLEMENT_OUTFIT_DICT.get(outfit_item_clothing_type)
                if suggestion:
                    matched_items.append(
                        MatchedItem(
                            outfit_item_id=str(outfit_item_id),
                            score=0.5 * np.mean(outfit_scores),
                            suggested_item_product_link=suggestion["product_link"],
                            suggested_item_image_link=suggestion["image_link"],
                        )
                    )

        if not matched_items:
            return None

        completeness_score = float(np.mean(outfit_scores)) if outfit_scores else 0.0

        return RecommendedOutfit(
            outfit_id=outfit_id,
            completeness_score=completeness_score,
            matches=matched_items,
        )

    async def find_similar_outfit_v2(
        self,
        user_id: str,
        wardrobe_object_names: List[str],
        sampled_outfit_ids: List[str],
        qdrant: QdrantService,
        limit_outfits: int = 10,
    ) -> List[RecommendedOutfit]:
        """
        Finds the best-matching outfits from a sampled list using pre-calculated wardrobe embeddings.
        This version retrieves wardrobe embeddings from Qdrant instead of calculating them.
        It processes outfits in parallel for improved performance.

        Args:
            user_id: ID of the user whose wardrobe to use
            wardrobe_object_names: A list of object names for wardrobe items to consider
            sampled_outfit_ids: A list of outfit IDs to evaluate, typically pre-sampled randomly.
            qdrant: An instance of the QdrantService for vector database operations.
            limit_outfits: The maximum number of recommended outfits to return.

        Returns:
            A list of `RecommendedOutfit` objects, sorted by their completeness
            score in descending order.
        """
        logger.info(
            f"Starting new outfit recommendation for user {user_id} with {len(wardrobe_object_names)} wardrobe items."
        )
        logger.debug(
            f"Evaluating {len(sampled_outfit_ids)} sampled outfits. Limit: {limit_outfits}"
        )

        if not wardrobe_object_names:
            logger.error("Wardrobe object names list is empty.")
            raise ValueError("Wardrobe object names must be non-empty.")

        # 1. Retrieve wardrobe embeddings from Qdrant (non-blocking)
        logger.debug("Retrieving wardrobe embeddings from Qdrant")
        wardrobe_records = await asyncio.to_thread(qdrant.get_wardrobe_vectors, user_id)

        if not wardrobe_records:
            logger.warning(f"No wardrobe embeddings found for user {user_id}")
            return []

        # Filter wardrobe records to only include requested object names
        wardrobe_records = [
            record
            for record in wardrobe_records
            if record.payload
            and record.payload.get("object_name") in wardrobe_object_names
        ]

        if not wardrobe_records:
            logger.warning(
                "No matching wardrobe items found for requested object names"
            )
            return []

        wardrobe_embeddings = np.array([record.vector for record in wardrobe_records])
        wardrobe_clothing_types = [
            record.payload.get("clothing_type", "unknown")
            for record in wardrobe_records
        ]
        wardrobe_object_names_actual = [
            record.payload.get("object_name", "") for record in wardrobe_records
        ]

        logger.info(
            f"Retrieved {len(wardrobe_embeddings)} wardrobe embeddings from Qdrant"
        )

        # 2. Process outfits in parallel
        tasks = [
            self._process_outfit(
                outfit_id,
                qdrant,
                wardrobe_embeddings,
                wardrobe_clothing_types,
                wardrobe_object_names_actual,
            )
            for outfit_id in sampled_outfit_ids
        ]

        outfit_results = await asyncio.gather(*tasks)

        # 3. Filter out null results and sort
        ranked_outfits = [outfit for outfit in outfit_results if outfit is not None]

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

    async def remove_wardrobe_image_from_index(
        self,
        user_id: str,
        object_name: str,
        qdrant: QdrantService,
    ) -> None:
        """
        Remove a wardrobe image from the wardrobe Qdrant index

        Args:
            user_id: ID of the user who owns the image
            object_name: Object name in MinIO storage
            qdrant: QdrantService instance
        """
        logger.debug(
            f"Removing wardrobe image from index: user_id={user_id}, object_name={object_name}"
        )

        try:
            success = qdrant.delete_wardrobe_vectors(
                user_id=user_id, object_name=object_name
            )
            if success:
                logger.info(
                    f"Successfully removed wardrobe image from index: user_id={user_id}, object_name={object_name}"
                )
            else:
                logger.warning(
                    f"Failed to remove wardrobe image from index: user_id={user_id}, object_name={object_name}"
                )

        except Exception as e:
            logger.error(f"Error removing wardrobe image from index: {str(e)}")
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
