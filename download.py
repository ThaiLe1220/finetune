"""
This script provides functionality to download translation models from Hugging Face. 
You can either download a specific model or all models defined in the 'direct_model_mapping'.

* Download a specific model:
    
    python download.py --direction en-vi 
    

* Download all models:
    
    python download.py --all 
    

Available translation directions are listed in the 'direct_model_mapping' dictionary.
"""

import os
import subprocess
import argparse
from dotenv import load_dotenv

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from huggingface_hub import HfApi, HfFolder

# Load environment variables from .env file
load_dotenv()
# Your Hugging Face access token (replace with your actual token)
huggingface_token = os.getenv("HF_TOKEN_READ")


def login_to_huggingface():
    # Retrieve the Hugging Face token from environment variables
    huggingface_token = os.getenv("HF_TOKEN_READ")

    if huggingface_token:
        try:
            # Use the HfApi to set the token
            HfFolder.save_token(huggingface_token)
            print("Logged in to Hugging Face successfully.")
        except Exception as e:
            print(f"An error occurred while trying to log in: {e}")
    else:
        print("Hugging Face token not found. Please ensure HF_TOKEN_READ is set.")


# Model mapping - specifies private model names & save locations
direct_model_mapping = {
    "en-vi": "Eugenememe/netflix-en-vi",
    "en-vi-2": "Eugenememe/news-en-vi",
}


# Function to download and save a single model
def download_and_save_model(model_name, model_dir):
    """Downloads a specific model"""
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, use_auth_token=huggingface_token
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name, use_auth_token=huggingface_token
        )

        os.makedirs(model_dir, exist_ok=True)
        model.save_pretrained(model_dir)
        tokenizer.save_pretrained(model_dir)

        print(f"Model '{model_name}' downloaded and saved to '{model_dir}'")
    except Exception as e:
        print(f"Error downloading or saving '{model_name}': {e}")


def download_all_models():
    """Downloads all models specified in the direct_model_mapping."""
    for direction, model_name in direct_model_mapping.items():
        model_dir = f"./{direction}"
        if os.path.exists(model_dir):
            print(f"Model '{model_name}' already downloaded (skipping)")
        else:
            download_and_save_model(model_name, model_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download a translation model from Hugging Face"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all models in the mapping",
    )
    args = parser.parse_args()

    if args.all:
        # Download all models
        login_to_huggingface()
        download_all_models()

    else:
        # If no argument is provided, show help
        parser.print_help()
