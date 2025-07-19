from app.core.config import get_settings
from app.core.logging import get_logger
from qdrant_client import QdrantClient
from qdrant_client.http import models

settings = get_settings()

# Initialize logger for Qdrant operations
logger = get_logger("app.storage.qdrant")


class QdrantService:
    def __init__(self) -> None:
        logger.info(f"Initializing Qdrant client for URL: {settings.QDRANT_URL}")
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            self.outfit_collection_name = "outfit"
            self.wardrobe_collection_name = "wardrobe"
            logger.info(
                f"Qdrant client initialized successfully for\
                    collections: {self.outfit_collection_name}, {self.wardrobe_collection_name}"
            )
            self._ensure_collections()
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            raise

    def _ensure_collections(self) -> None:
        """Ensure both outfit and wardrobe collections exist with proper configuration."""
        logger.debug("Checking if collections exist")
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]

            # Create outfit collection if it doesn't exist (using FashionCLIP embeddings now)
            if self.outfit_collection_name not in collection_names:
                logger.info(
                    f"Collection '{self.outfit_collection_name}' does not exist, creating it"
                )
                self.client.create_collection(
                    collection_name=self.outfit_collection_name,
                    vectors_config=models.VectorParams(
                        size=512,  # FashionCLIP embedding size (changed from 768)
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(
                    f"Successfully created collection: {self.outfit_collection_name}"
                )
            else:
                logger.debug(
                    f"Collection '{self.outfit_collection_name}' already exists"
                )

            # Create wardrobe collection if it doesn't exist
            if self.wardrobe_collection_name not in collection_names:
                logger.info(
                    f"Collection '{self.wardrobe_collection_name}' does not exist, creating it"
                )
                self.client.create_collection(
                    collection_name=self.wardrobe_collection_name,
                    vectors_config=models.VectorParams(
                        size=512,  # FashionCLIP embedding size
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(
                    f"Successfully created collection: {self.wardrobe_collection_name}"
                )
            else:
                logger.debug(
                    f"Collection '{self.wardrobe_collection_name}' already exists"
                )

            # Ensure payload indices exist for efficient filtering
            logger.debug("Creating payload indices")

            # For outfit collection
            self.client.create_payload_index(
                collection_name=self.outfit_collection_name,
                field_name="outfit_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            # For wardrobe collection
            self.client.create_payload_index(
                collection_name=self.wardrobe_collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.wardrobe_collection_name,
                field_name="clothing_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.debug("Payload indices ensured")

        except Exception as e:
            logger.error(f"Error ensuring collections exist: {str(e)}")
            raise

    # Legacy collection property for backward compatibility
    @property
    def collection_name(self) -> str:
        """Legacy property for backward compatibility with outfit collection"""
        return self.outfit_collection_name

    def upsert_vectors(
        self, points: list[models.PointStruct], collection_name: str = None  # type: ignore
    ) -> None:
        """Upsert vectors into the specified collection."""
        collection = collection_name or self.outfit_collection_name
        logger.debug(f"Upserting {len(points)} vectors into collection '{collection}'")
        try:
            self.client.upsert(collection_name=collection, points=points)
            logger.info(
                f"Successfully upserted {len(points)} vectors into collection '{collection}'"
            )
        except Exception as e:
            logger.error(
                f"Error upserting vectors into collection '{collection}': {str(e)}"
            )
            raise

    def search_vectors(
        self,
        query_vector: list[float],
        limit: int = 50,
        score_threshold: float = 0.3,
        collection_name: str = None,  # type: ignore
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the specified collection."""
        collection = collection_name or self.outfit_collection_name
        logger.debug(
            f"Searching vectors in collection '{collection}' (limit={limit}, threshold={score_threshold})"
        )
        try:
            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            logger.info(
                f"Vector search completed: found {len(results)} results above threshold {score_threshold}"
            )
            logger.debug(
                f"Search results scores: {[r.score for r in results[:5]]}"
            )  # Log top 5 scores
            return results
        except Exception as e:
            logger.error(
                f"Error searching vectors in collection '{collection}': {str(e)}"
            )
            raise

    def get_point(self, point_id: str, collection_name: str = None):  # type: ignore
        """Retrieve a single point by its ID from the specified collection."""
        collection = collection_name or self.outfit_collection_name
        results = self.client.retrieve(
            collection_name=collection,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            raise ValueError(
                f"Point with id {point_id} not found in Qdrant collection '{collection}'."
            )
        return results[0]

    def get_outfit_vectors(self, outfit_id: str) -> list[models.Record]:
        """Retrieve all vectors for a specific outfit_id using scrolling."""
        records, next_offset = self.client.scroll(
            collection_name=self.outfit_collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="outfit_id",
                        match=models.MatchValue(value=outfit_id),
                    )
                ]
            ),
            limit=100,  # Adjust limit as needed
            with_payload=True,
            with_vectors=True,
        )
        # Note: This basic implementation does not handle pagination.
        # If an outfit can have more than `limit` items, you'll need to
        # loop using the `next_offset` until it is None.
        return records

    def get_wardrobe_vectors(self, user_id: str) -> list[models.Record]:
        """Retrieve all wardrobe vectors for a specific user_id using scrolling."""
        records, next_offset = self.client.scroll(
            collection_name=self.wardrobe_collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            ),
            limit=1000,  # Allow for larger wardrobes
            with_payload=True,
            with_vectors=True,
        )
        return records

    def search_wardrobe_vectors(
        self,
        user_id: str,
        clothing_type: str = None,  # type: ignore
        limit: int = 1000,
    ) -> list[models.Record]:
        """Search wardrobe vectors for a specific user, optionally filtered by clothing type."""
        filter_conditions = [
            models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id),
            )
        ]

        if clothing_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="clothing_type",
                    match=models.MatchValue(value=clothing_type),
                )
            )

        records, next_offset = self.client.scroll(
            collection_name=self.wardrobe_collection_name,
            scroll_filter=models.Filter(must=filter_conditions),
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )
        return records

    # --- delete -------------------------------------------------------------
    def delete_point(self, point_id: str, collection_name: str = None) -> bool:  # type: ignore
        """Delete a single point by its ID from the specified collection."""
        collection = collection_name or self.outfit_collection_name
        try:
            self.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(points=[point_id]),
            )
            return True
        except Exception as exc:
            print(
                f"Error deleting point {point_id} from collection '{collection}': {exc}"
            )
            return False

    def delete_points(
        self, point_ids: list[str], collection_name: str = None  # type: ignore
    ) -> dict[str, bool]:
        """Delete multiple points by their IDs from the specified collection."""
        results = {}
        for point_id in point_ids:
            results[point_id] = self.delete_point(point_id, collection_name)
        return results

    def delete_outfit_vectors(self, outfit_id: str) -> bool:
        """Delete all vectors for a specific outfit_id."""
        logger.debug(f"Deleting vectors for outfit_id: {outfit_id}")
        try:
            self.client.delete(
                collection_name=self.outfit_collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="outfit_id",
                                match=models.MatchValue(value=outfit_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Successfully deleted vectors for outfit_id: {outfit_id}")
            return True
        except Exception as exc:
            logger.error(f"Error deleting vectors for outfit {outfit_id}: {exc}")
            return False

    def delete_wardrobe_vectors(
        self, user_id: str, object_name: str = None  # type: ignore
    ) -> bool:  # type: ignore
        """Delete wardrobe vectors for a specific user, optionally for a specific object."""
        logger.debug(
            f"Deleting wardrobe vectors for user_id: {user_id}, object_name: {object_name}"
        )
        try:
            filter_conditions = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]

            if object_name:
                filter_conditions.append(
                    models.FieldCondition(
                        key="object_name",
                        match=models.MatchValue(value=object_name),
                    )
                )

            self.client.delete(
                collection_name=self.wardrobe_collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=filter_conditions)
                ),
            )
            logger.info(
                f"Successfully deleted wardrobe vectors for user_id: {user_id}, object_name: {object_name}"
            )
            return True
        except Exception as exc:
            logger.error(
                f"Error deleting wardrobe vectors for user {user_id}, object {object_name}: {exc}"
            )
            return False

    def point_exists(
        self, point_id: str, collection_name: str = None  # type: ignore
    ) -> bool:  # type: ignore
        """Check if a point exists in the specified collection."""
        try:
            self.get_point(point_id, collection_name)
            return True
        except ValueError:
            return False

    def get_collection_info(self, collection_name: str = None) -> dict:  # type: ignore
        """Get information about the specified collection."""
        collection = collection_name or self.outfit_collection_name
        logger.debug(f"Getting collection info for '{collection}'")
        try:
            info = self.client.get_collection(collection)
            logger.debug(f"Collection '{collection}' has {info.points_count} points")
            return {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
            }
        except Exception as e:
            logger.error(f"Error getting collection info for '{collection}': {str(e)}")
            raise
