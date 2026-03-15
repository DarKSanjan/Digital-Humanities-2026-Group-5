# Setting Up CUDA-Enabled PyTorch Environment

## Problem
PyTorch with CUDA doesn't support Python 3.13 yet. You need Python 3.10, 3.11, or 3.12.

## Solution: Install Python 3.12 with Virtual Environment

### Step 1: Install Python 3.12

1. Download Python 3.12 from: https://www.python.org/downloads/
2. Run installer
3. **IMPORTANT**: Check "Add Python 3.12 to PATH" during installation
4. Install to a custom location like `C:\Python312\` to keep it separate from 3.13

### Step 2: Create Virtual Environment with Python 3.12

Open PowerShell in the `backend` directory and run:

```powershell
# Create virtual environment using Python 3.12
C:\Python312\python.exe -m venv venv_cuda

# Activate the virtual environment
.\venv_cuda\Scripts\Activate.ps1

# Verify Python version (should show 3.12.x)
python --version

# Upgrade pip
python -m pip install --upgrade pip
```

### Step 3: Install PyTorch with CUDA 12.1

```powershell
# Install PyTorch with CUDA 12.1 support (matches your CUDA 13.0 driver)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 4: Install Other Dependencies

```powershell
# Install project dependencies
pip install -r requirements.txt

# Install additional dependencies for tha3
pip install matplotlib scipy
```

### Step 5: Verify CUDA is Working

```powershell
python check_cuda.py
```

Expected output:
```
PyTorch: 2.x.x+cu121
CUDA available: True
CUDA version: 12.1
GPU: NVIDIA GeForce RTX 3080 Laptop GPU
```

### Step 6: Run the Backend

```powershell
python src/main.py
```

You should see:
```
[INFO] CUDA available: NVIDIA GeForce RTX 3080 Laptop GPU, 8192MB VRAM, CUDA 12.1
[INFO] Rendering mode: GPU (30 FPS target)
[INFO] Loading standard_float model variant...
```

## Alternative: Quick Test with Conda

If you have Anaconda/Miniconda installed:

```powershell
# Create conda environment with Python 3.12
conda create -n chatbot_cuda python=3.12 -y

# Activate environment
conda activate chatbot_cuda

# Install PyTorch with CUDA
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia

# Install other dependencies
pip install -r requirements.txt
pip install matplotlib scipy

# Run
python src/main.py
```

## Why This Matters

**CPU Mode (Current):**
- Model: separable_float
- Speed: ~10-15 FPS
- Rendering: Slow, may lag

**GPU Mode (With CUDA):**
- Model: standard_float
- Speed: 30+ FPS
- Rendering: Smooth, real-time
- VRAM: ~2-3GB (you have 8GB, plenty of room)

Your RTX 3080 is a beast - it will render avatar frames 2-3x faster than CPU!

## Troubleshooting

### If Python 3.12 installer doesn't add to PATH:
Manually add `C:\Python312\` and `C:\Python312\Scripts\` to your PATH environment variable.

### If CUDA still not detected after install:
1. Check NVIDIA driver is up to date: `nvidia-smi`
2. Verify PyTorch installation: `python -c "import torch; print(torch.version.cuda)"`
3. Make sure you're using the virtual environment: `.\venv_cuda\Scripts\Activate.ps1`

### If you get "DLL load failed" errors:
Install Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
