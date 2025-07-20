# Machine Learning

This directory contains the core machine learning models and logic for Outfit Predict.

## 🤖 Models

We use a combination of models to power our outfit suggestion engine:

- **Object Detection (YOLO)**: To identify and locate clothing items in an uploaded image.
- **Image Embeddings (FashionCLIP)**: To convert images of clothing items into vector embeddings, which allows us to perform similarity searches.
- **Clothes Type Classification**: We utilize FashionCLIP to classify the type of each wardrobe clothing item (e.g., "t-shirt", "jeans", "shoes").
- **Style Classification**: We utilize FashionCLIP to classify the style of an outfit (e.g., "casual", "formal").

The pre-trained model weights are stored in this directory and are managed using [Git LFS](https://git-lfs.github.com/).

## ⚙️ How it Works

1.  **Image Segmentation**: When user uploads image, we identify the clothing type of this image. We do this with predefined text embeddings of clothing types and user's image
2.  **Embedding Generation**: After the clothing type classification, we obtain calculated embeddings for this particular image.
3.  **Similarity Search**: These embeddings are stored in the [Qdrant](https://qdrant.tech/) vector database. To find matching outfits, we perform a similarity search between the user's clothing embeddings and the embeddings of clothes in our pre-styled outfit database.

## 📂 Files

- **`best.pt`**: The main weights for our YOLO object detection model.
- **`sam_b.pt`**: Weights for the Segment Anything Model (SAM).
- **`clothes_type_classification.py`**: Script for classifying clothing types.
- **`encoding_models.py`**: Contains the logic for generating image embeddings using FashionCLIP.
- **`image_search.py`**: Implements the similarity search using Qdrant.
- **`ml_models.py`**: A helper module to load and manage the different ML models.
- **`outfit_processing.py`**: Orchestrates the end-to-end ML pipeline for processing outfits.
- **`style_classification.py`**: Script for classifying the style of an outfit.

## 📓 Notebooks

For a deeper dive into the experiments, model training, and evaluation, you can refer to the Jupyter notebooks in the `/notebooks` directory at the root of the project.
