from app.core.config import get_settings
from qdrant_client import QdrantClient
from qdrant_client.http import models

settings = get_settings()


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
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
                    distance=models.Distance.COSINE
                )
            )

    def upsert_vectors(self, points: list[models.PointStruct]) -> None:
        """Upsert vectors into the collection."""
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search_vectors(
        self,
        query_vector: list[float],
        limit: int = 50,
        score_threshold: float = 0.65
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        ).points
