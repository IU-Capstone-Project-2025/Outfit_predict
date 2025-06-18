from PIL import Image
import torch
import clip
from typing import List, Tuple
from app.storage.minio_client import MinioService
from app.crud import outfit as outfit_crud
from sqlalchemy.ext.asyncio import AsyncSession
import io


class OutfitSearchEngine:
    """
    Class represents an engine for searching for similar outfits using CLIP
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

    async def find_similar_outfits(
            self,
            images: List[Image.Image],
            db: AsyncSession,
            minio: MinioService,
            score_threshold: float = 0.6,
            limit_outfits: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find similar outfits by comparing query images with all outfits in the database

        Args:
            images: List of query images (1-8 images)
            db: Database session
            minio: MinIO service for accessing outfit images
            score_threshold: Minimum similarity score threshold (0.0 to 1.0)
            limit_outfits: Maximum number of returned outfits

        Returns:
            List of (outfit_id, average_similarity_score) tuples, sorted by score
        """
        if not 1 <= len(images) <= 8:
            raise ValueError("Number of images must be between 1 and 8")

        # Get all outfits from database
        outfits = await outfit_crud.list_outfits(db, limit=1000)  # Adjust limit as needed

        # Get embeddings for query images
        query_embeddings = [self.get_image_embedding(img) for img in images]

        # Calculate similarity scores for each outfit
        outfit_scores = []
        for outfit in outfits:
            try:
                # Get outfit image from MinIO
                obj = minio.get_stream(outfit.object_name)
                outfit_image = Image.open(io.BytesIO(obj.read()))
                obj.close()

                # Get embedding for outfit image
                outfit_embedding = self.get_image_embedding(outfit_image)

                # Calculate average similarity score across all query images
                total_score = 0
                for query_embedding in query_embeddings:
                    # Calculate cosine similarity
                    similarity = torch.nn.functional.cosine_similarity(
                        torch.tensor(query_embedding).unsqueeze(0),
                        torch.tensor(outfit_embedding).unsqueeze(0)
                    ).item()
                    total_score += similarity

                avg_score = total_score / len(query_embeddings)
                if avg_score >= score_threshold:
                    outfit_scores.append((str(outfit.id), avg_score))

            except Exception as e:
                print(f"Error processing outfit {outfit.id}: {str(e)}")
                continue

        # Sort by score in descending order and return top results
        return sorted(outfit_scores, key=lambda x: x[1], reverse=True)[:limit_outfits] 