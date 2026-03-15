"""Download talking-head-anime-3 models from HuggingFace."""

from huggingface_hub import snapshot_download
from pathlib import Path

# Download models to the tha3_repo/data/models directory
models_dir = Path(__file__).parent / "tha3_repo" / "data" / "models"
models_dir.mkdir(parents=True, exist_ok=True)

print("Downloading talking-head-anime-3 models from HuggingFace...")
print(f"Target directory: {models_dir}")

try:
    snapshot_download(
        repo_id="ksuriuri/talking-head-anime-3-models",
        local_dir=str(models_dir),
        local_dir_use_symlinks=False
    )
    print("✅ Models downloaded successfully!")
    print(f"Models location: {models_dir}")
except Exception as e:
    print(f"❌ Error downloading models: {e}")
    print("You may need to download them manually from:")
    print("https://huggingface.co/ksuriuri/talking-head-anime-3-models")
