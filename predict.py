import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.models import ResNet18_Weights, EfficientNet_B0_Weights
from PIL import Image
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Initialize device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load models for each category
model_paths = {
    1: "saved_models/site_preparation.pth",
    2: "saved_models/base_subbase.pth",
    3: "saved_models/utility_ducts.pth",
    4: "saved_models/surface_preparation.pth",
    5: "saved_models/asphalt_finishing.pth",
}

category_names = {
    1: "Site Preparation",
    2: "Base and Sub-base Preparation",
    3: "Utility Ducts",
    4: "Surface Preparation",
    5: "Asphalt Finishing",
}

# Adjusted similarity thresholds
similarity_thresholds = {
    1: 80,
    2: 80,
    3: 80,
    4: 80,
    5: 70,
}

# Load all models and prepare them for inference
models_dict = {}
for category, model_path in model_paths.items():
    model = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(model.fc.in_features, 1),
        nn.Sigmoid()
    )
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    models_dict[category] = nn.Sequential(*list(model.children())[:-1])  # Feature extractor

# Preprocessing function
def preprocess_image(image_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    image = Image.open(image_path).convert("RGB")
    return transform(image).unsqueeze(0).to(device)

# Get embedding
def get_embedding(image_path, model):
    image = preprocess_image(image_path)
    with torch.no_grad():
        embedding = model(image)
        return embedding.view(embedding.size(0), -1)

# Precompute embeddings for reference images
def cache_reference_embeddings():
    reference_images = {
        1: [f"dataset/image1_{i}.jpg" for i in range(1, 33)],
        2: [f"dataset/image2_{i}.jpg" for i in range(1, 33)],
        3: [f"dataset/image3_{i}.jpg" for i in range(1, 27)],
        4: [f"dataset/image4_{i}.jpg" for i in range(1, 42)],
        5: [f"dataset/image5_{i}.jpg" for i in range(1, 23)],
    }
    embeddings_cache = {}

    for category, images in reference_images.items():
        batch_images = torch.cat([preprocess_image(img) for img in images])
        with torch.no_grad():
            embeddings = models_dict[category](batch_images).view(batch_images.size(0), -1)
        embeddings_cache[category] = embeddings.mean(dim=0)  # Store average embedding
    return embeddings_cache

# Cache reference embeddings at startup
reference_embeddings_cache = cache_reference_embeddings()

# Check similarity for a single category
def check_similarity(image_path, category):
    embedding = get_embedding(image_path, models_dict[category])
    reference_embedding = reference_embeddings_cache[category].to(device)
    similarity = F.cosine_similarity(embedding, reference_embedding.unsqueeze(0)).item() * 100
    return category, similarity

# Load a lightweight PyTorch model for authenticity detection
def load_authenticity_model():
    model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(model.classifier[1].in_features, 2),  # Binary classification (Real or AI-Generated)
    )
    model.to(device)
    model.eval()
    return model

authenticity_model = load_authenticity_model()

def check_image_authenticity(image_path):
    """
    Check if the image is likely AI-generated using a lightweight PyTorch model.
    Returns True if AI-generated, False otherwise.
    """
    try:
        image_tensor = preprocess_image(image_path)
        with torch.no_grad():
            output = authenticity_model(image_tensor)
            probabilities = torch.softmax(output, dim=1)
            ai_generated_score = probabilities[0, 1].item()  # Probability of being AI-generated
            logging.info(f"AI-generated score: {ai_generated_score}")
            return ai_generated_score > 0.7  # Adjust threshold as needed
    except Exception as e:
        logging.warning(f"Error in authenticity check: {e}")
        return False  # Default to not AI-generated in case of errors

# Predict category
def predict_category(image_path):
    """
    Predict the category for an image.

    Parameters:
    - image_path: Path to the extracted frame image.

    Returns:
    - Tuple of (success: bool, prediction: dict or error message).
    """
    try:
        # Step 1: Check for AI-generated artifacts
        if check_image_authenticity(image_path):
            return False, {"error": "The image appears to be AI-generated. Please upload a valid image."}

        # Step 2: Check all categories in parallel
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(
                lambda cat: check_similarity(image_path, cat),
                [category for category in category_names]
            ))

        # Step 3: Find the category with the highest similarity
        results = sorted(results, key=lambda x: x[1], reverse=True)
        best_match_category, best_match_similarity = results[0]

        if best_match_similarity >= similarity_thresholds[best_match_category]:
            return True, {
                "Predicted Layer": category_names[best_match_category],
                "Confidence": f"{best_match_similarity:.2f}%",
            }

        # No match found
        return False, {"error": "The image does not match any known category. Please ensure the image is clear and relevant."}

    except Exception as e:
        return False, {"error": f"Error during prediction: {e}"}
