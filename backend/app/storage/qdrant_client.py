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
            self.collection_name = "outfit"
            logger.info(
                f"Qdrant client initialized successfully for collection: {self.collection_name}"
            )
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            raise

    def _ensure_collection(self) -> None:
        """Ensure the collection exists with proper configuration."""
        logger.debug(f"Checking if collection '{self.collection_name}' exists")
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]

            if self.collection_name not in collection_names:
                logger.info(
                    f"Collection '{self.collection_name}' does not exist, creating it"
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=512,  # CLIP ViT-B/32 embedding size
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Successfully created collection: {self.collection_name}")
            else:
                logger.debug(f"Collection '{self.collection_name}' already exists")

            # Ensure a payload index exists for 'outfit_id' for efficient filtering.
            # This is idempotent and safe to run on every startup.
            logger.debug("Creating payload index for 'outfit_id'")
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="outfit_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.debug("Payload index for 'outfit_id' ensured")

        except Exception as e:
            logger.error(
                f"Error ensuring collection '{self.collection_name}' exists: {str(e)}"
            )
            raise

    def upsert_vectors(self, points: list[models.PointStruct]) -> None:
        """Upsert vectors into the collection."""
        logger.debug(
            f"Upserting {len(points)} vectors into collection '{self.collection_name}'"
        )
        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(
                f"Successfully upserted {len(points)} vectors into collection '{self.collection_name}'"
            )
        except Exception as e:
            logger.error(
                f"Error upserting vectors into collection '{self.collection_name}': {str(e)}"
            )
            raise

    def search_vectors(
        self, query_vector: list[float], limit: int = 50, score_threshold: float = 0.3
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        logger.debug(
            f"Searching vectors in collection '{self.collection_name}' (limit={limit}, threshold={score_threshold})"
        )
        try:
            results = self.client.search(
                collection_name=self.collection_name,
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
                f"Error searching vectors in collection '{self.collection_name}': {str(e)}"
            )
            raise

    def get_point(self, point_id: str):
        """Retrieve a single point by its ID from the collection."""
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            raise ValueError(f"Point with id {point_id} not found in Qdrant.")
        return results[0]

    def get_outfit_vectors(self, outfit_id: str) -> list[models.Record]:
        """Retrieve all vectors for a specific outfit_id using scrolling."""
        records, next_offset = self.client.scroll(
            collection_name=self.collection_name,
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

    # --- delete -------------------------------------------------------------
    def delete_point(self, point_id: str) -> bool:
        """Delete a single point by its ID from the collection."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id]),
            )
            return True
        except Exception as exc:
            print(f"Error deleting point {point_id}: {exc}")
            return False

    def delete_points(self, point_ids: list[str]) -> dict[str, bool]:
        """Delete multiple points by their IDs from the collection."""
        results = {}
        for point_id in point_ids:
            results[point_id] = self.delete_point(point_id)
        return results

    def delete_outfit_vectors(self, outfit_id: str) -> bool:
        """Delete all vectors for a specific outfit_id."""
        logger.debug(f"Deleting vectors for outfit_id: {outfit_id}")
        try:
            self.client.delete(
                collection_name=self.collection_name,
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

    def point_exists(self, point_id: str) -> bool:
        """Check if a point exists in the collection."""
        try:
            self.get_point(point_id)
            return True
        except ValueError:
            return False

    def get_collection_info(self) -> dict:
        """Get information about the collection."""
        logger.debug(f"Getting collection info for '{self.collection_name}'")
        try:
            info = self.client.get_collection(self.collection_name)
            logger.debug(
                f"Collection '{self.collection_name}' has {info.points_count} points"
            )
            return {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
            }
        except Exception as e:
            logger.error(
                f"Error getting collection info for '{self.collection_name}': {str(e)}"
            )
            raise
