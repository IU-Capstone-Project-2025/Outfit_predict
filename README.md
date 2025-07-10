<img src="logo.png" alt="Outfit Predict Logo">

Outfit Predict is a web platform for creating perfect outfits based on your wardrobe. It automatically searches outfits storage to assemble flawless looks from your wardrobe.

[**Link to the deployed project**](https://outfitpredict.ru)

## 📋 Table of Contents

- [🤵‍♂️ Problem & Audience](#️-problem--audience)
- [💡 Proposed Workflow](#-proposed-workflow)
- [🔪 Tech Stack](#-tech-stack)
- [📥 Repository Setup](#-repository-setup)
- [🛠️ Environment Setup](#️-environment-setup)
- [🚀 Running the Application](#-running-the-application)
- [👥 Team](#-team)
- [📊 Progress Table](#-progress-table)
- [🛠️ Developing guide](#-developing-guide)
## 🤵‍♂️ Problem & Audience

- **Problem**: Imagine a situation where you have a lot of items in your wardrobe and you want to decide what to wear. Scanning through the clothes and trying different combinations of them could take enormous amount of time. Still, this random approach will not lead you to perfect outfit.
- **Audience**: Any person who cares about their outfit, watches current trends in fashion, and wants to look attractive.

## 💡 Proposed Workflow

1. User uploads clothes - from wardrobe, offline store, online shop, and others. This process of uploading more clothes could be continued, and the clothes could be deleted.

2. User chooses the clothes from their app wardrobe that they want to compose outfit from.

3. From our side, we store already composed perfect outfits. They could be obtained through e-commerce sites, fashion sites, and any other source.

4. The system takes the clothes and runs optimized similarity search to match the items from person's wardrobe to items from outfits.

5. User gets ranked list of possible outfits that could be composed from selected clothes.

## 🔪 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Frontend** | Next.js, React, TypeScript, Tailwind CSS |
| **Backend** | FastAPI |
| **Deep Learning Models** | YOLOv11 (Object Detection), CLIP (Image Embeddings) |
| **Storage** | MinIO (Object Storage), Qdrant (Vector Database), PostgreSQL (Relational Database) |
| **Containerization** | Docker, Docker Compose |
| **Image Processing** | Pillow, OpenCV |

## 📥 Repository Setup

This repository uses **Git LFS (Large File Storage)** for managing large machine learning model files (`.pt` files).

### Prerequisites

Make sure you have Git LFS installed:

```bash
# Install Git LFS (if not already installed)
# On Ubuntu/Debian:
sudo apt install git-lfs

# On macOS:
brew install git-lfs

# On Windows, download from: https://git-lfs.github.io/
```

### Cloning the Repository

**⚠️ Important**: Use Git LFS clone to properly download all model files:

```bash
# Clone with Git LFS support
git lfs clone https://github.com/IU-Capstone-Project-2025/Outfit_predict.git

# Alternative: Regular clone followed by LFS pull
git clone https://github.com/IU-Capstone-Project-2025/Outfit_predict.git
cd Outfit_predict
git lfs pull
```

### Verify LFS Files

After cloning, verify that model files are properly downloaded:

```bash
# Check LFS files status
git lfs ls-files

# Model files should be actual files, not pointer files
ls -lh backend/app/ml/*.pt
```

## 🛠️ Environment Setup

1. Before running the application, you should register at [Qdrant](https://qdrant.tech/) for obtaining API key.

2. Then you should replace fields related to Qdrant in `.env.example`

3. After you have performed changes, copy the example environment file:
```bash
cp .env.example .env
```

4. Perform another updates on the `.env` file with your configuration values.

## 🚀 Running the Application

To run the application using Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# To run in detached mode (in the background)
docker-compose up --build -d

# To stop all services
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- MinIO Console: http://localhost:9001

## 👥 Team

| Name | Role |
|----------|-------------|
| **Bulat Sharipov** | ML, Backend, Managing |
| **Victor Mazanov** | Managing, Customer Development |
| **Dinar Yakupov** | Frontend |
| **Danil Fathutdinov** | ML, Backend |
| **Artyom Grishin** | Product Designer |
| **Remal Gareev** | Backend, DevOps |

## 📊 Progress Table

| № | Week Topic | What Have Been Done |
|------|------|---------------------|
| Week 1 | Finding team & deciding project idea | - Researched project ideas<br>- Basic market research & user stories<br>- Basic backend development with database for wardrobe<br>- Trained YOLO model<br>- CLIP Embedder was included |
| Week 2 | First CustDevs and market research, sub-MVP functionality | - Vector Database introduced<br>- Second table for outfits introduced<br>- Developed function for finding most similar outfits<br>- CustDev conducted<br>- Market Research and Concurrent research |
| Week 3| Introducing MVP | - Developed and enhanced our algorithm for searching best outfits<br> -Developed migrations and deployed the project<br>- Conducted customer developments and created hypotheses for future features<br>- Developed frontend pages for checking wardrobe, uploading items, and making outfit predictions.

## 🛠️ Developing guide [link](dev.md)
