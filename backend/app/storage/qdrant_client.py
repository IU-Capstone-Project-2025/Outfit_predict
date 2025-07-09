from app.core.config import get_settings
from qdrant_client import QdrantClient
from qdrant_client.http import models

settings = get_settings()


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = "outfit"
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure the collection exists with proper configuration."""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=512,  # CLIP ViT-B/32 embedding size
                    distance=models.Distance.COSINE,
                ),
            )

        # Ensure a payload index exists for 'outfit_id' for efficient filtering.
        # This is idempotent and safe to run on every startup.
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="outfit_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    def upsert_vectors(self, points: list[models.PointStruct]) -> None:
        """Upsert vectors into the collection."""
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search_vectors(
        self, query_vector: list[float], limit: int = 50, score_threshold: float = 0.3
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

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
                points_selector=models.PointIdsList(points=[point_id])
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
                )
            )
            return True
        except Exception as exc:
            print(f"Error deleting vectors for outfit {outfit_id}: {exc}")
            return False

    def point_exists(self, point_id: str) -> bool:
        """Check if a point exists in the collection."""
        try:
            self.get_point(point_id)
            return True
        except ValueError:
            return False
