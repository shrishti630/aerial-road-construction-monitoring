import os
import logging
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.models import ResNet18_Weights, EfficientNet_B0_Weights

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Model file paths
model_paths = {
    1: os.path.join(BASE_DIR, "saved_models", "site_preparation.pth"),
    2: os.path.join(BASE_DIR, "saved_models", "base_subbase.pth"),
    3: os.path.join(BASE_DIR, "saved_models", "utility_ducts.pth"),
    4: os.path.join(BASE_DIR, "saved_models", "surface_preparation.pth"),
    5: os.path.join(BASE_DIR, "saved_models", "asphalt_finishing.pth"),
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

# Preprocessing transform
preprocess_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def preprocess_image(image_path):
    image = Image.open(image_path).convert("RGB")
    return preprocess_transform(image).unsqueeze(0).to(device)

# Load all models and prepare feature extractors
models_dict = {}
for category, model_path in model_paths.items():
    model = models.resnet18(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(model.fc.in_features, 1),
        nn.Sigmoid()
    )
    if os.path.exists(model_path):
        state = torch.load(model_path, map_location=device, weights_only=True)
        model.load_state_dict(state)
    else:
        logging.warning(f"Model file not found: {model_path}")
    model.to(device)
    model.eval()
    models_dict[category] = nn.Sequential(*list(model.children())[:-1])  # Feature extractor

# Get embedding
def get_embedding(image_path, model):
    image = preprocess_image(image_path)
    with torch.no_grad():
        embedding = model(image)
        return embedding.view(embedding.size(0), -1)

# Precompute or load embeddings for reference images
EMBEDDINGS_CACHE_PATH = os.path.join(BASE_DIR, "saved_models", "reference_embeddings.pt")

def load_or_cache_reference_embeddings():
    if os.path.exists(EMBEDDINGS_CACHE_PATH):
        try:
            cache = torch.load(EMBEDDINGS_CACHE_PATH, map_location=device, weights_only=True)
            logging.info("Loaded reference embeddings from disk cache.")
            return cache
        except Exception as e:
            logging.warning(f"Failed to load cached embeddings ({e}), recomputing...")

    reference_images = {
        1: [os.path.join(BASE_DIR, f"dataset/image1_{i}.jpg") for i in range(1, 33)],
        2: [os.path.join(BASE_DIR, f"dataset/image2_{i}.jpg") for i in range(1, 33)],
        3: [os.path.join(BASE_DIR, f"dataset/image3_{i}.jpg") for i in range(1, 27)],
        4: [os.path.join(BASE_DIR, f"dataset/image4_{i}.jpg") for i in range(1, 42)],
        5: [os.path.join(BASE_DIR, f"dataset/image5_{i}.jpg") for i in range(1, 23)],
    }
    embeddings_cache = {}

    for category, images in reference_images.items():
        existing_images = [img for img in images if os.path.exists(img)]
        if not existing_images:
            continue
        batch_images = torch.cat([preprocess_image(img) for img in existing_images])
        with torch.no_grad():
            embeddings = models_dict[category](batch_images).view(batch_images.size(0), -1)
        embeddings_cache[category] = embeddings.mean(dim=0)

    try:
        os.makedirs(os.path.dirname(EMBEDDINGS_CACHE_PATH), exist_ok=True)
        torch.save(embeddings_cache, EMBEDDINGS_CACHE_PATH)
        logging.info(f"Saved reference embeddings cache to {EMBEDDINGS_CACHE_PATH}")
    except Exception as e:
        logging.warning(f"Could not persist embeddings cache: {e}")

    return embeddings_cache

# Cache reference embeddings at startup
reference_embeddings_cache = load_or_cache_reference_embeddings()

# Check similarity for a single category
def check_similarity(image_path, category):
    embedding = get_embedding(image_path, models_dict[category])
    reference_embedding = reference_embeddings_cache[category].to(device)
    similarity = F.cosine_similarity(embedding, reference_embedding.unsqueeze(0)).item() * 100
    return category, similarity

# Load a lightweight PyTorch model for authenticity detection
def load_authenticity_model():
    try:
        model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    except Exception:
        model = models.efficientnet_b0(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(model.classifier[1].in_features, 2),
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
            ai_generated_score = probabilities[0, 1].item()
            logging.info(f"AI-generated score: {ai_generated_score}")
            return ai_generated_score > 0.7
    except Exception as e:
        logging.warning(f"Error in authenticity check: {e}")
        return False

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
        if not os.path.exists(image_path):
            return False, {"error": f"Image file not found: {image_path}"}

        # Step 1: Check for AI-generated artifacts
        if check_image_authenticity(image_path):
            return False, {"error": "The image appears to be AI-generated. Please upload a valid image."}

        # Step 2: Check all categories in parallel
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(
                lambda cat: check_similarity(image_path, cat),
                [category for category in category_names if category in reference_embeddings_cache]
            ))

        if not results:
            return False, {"error": "No category reference data available."}

        # Step 3: Find the category with the highest similarity
        results = sorted(results, key=lambda x: x[1], reverse=True)
        best_match_category, best_match_similarity = results[0]

        if best_match_similarity >= similarity_thresholds.get(best_match_category, 70):
            return True, {
                "Predicted Layer": category_names[best_match_category],
                "Confidence": f"{best_match_similarity:.2f}%",
            }

        # No match found
        return False, {"error": "The image does not match any known category. Please ensure the image is clear and relevant."}

    except Exception as e:
        return False, {"error": f"Error during prediction: {e}"}
