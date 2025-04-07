# TinkerHub v0.4.0 

## Prerequisites

### System Requirements
- Windows 10 or Windows 11 (64-bit)
- Minimum 16GB RAM (32GB recommended)
- NVIDIA GPU with CUDA support (highly recommended)
- Python 3.10
- Node.js 18+ 
- Git

### Hardware Recommendations
- GPU: NVIDIA RTX 3060 or better (8GB+ VRAM)

## Installation Steps

### 1. Install Python 3.10
1. Download Python 3.10 from [Official Python Website](https://www.python.org/downloads/windows/)
2. During installation, check "Add Python to PATH"
3. Open Command Prompt and verify:
   ```bash
   python --version
   pip --version
   ```

### 2. Install CUDA Toolkit 11.8
1. Download CUDA Toolkit 11.8 from [NVIDIA CUDA Toolkit Archive](https://developer.nvidia.com/cuda-11-8-0-download-archive)
2. Select: Windows → x86_64 → 11 → exe (local)
3. Run installer and follow these steps:
   - Accept the EULA (select "Yes")
   - Choose "Express Installation" (recommended)
   - During installation, several dialog boxes may appear - accept all default options
4. Verify installation:
   ```bash
   nvidia-smi
   ```
   This should display your GPU and CUDA version

### 3. Install Node.js
1. Download from [Node.js Official Site](https://nodejs.org/)
2. Choose LTS version
3. Run installer, accept all defaults
4. Verify in Command Prompt:
   ```bash
   node --version
   npm --version
   ```

### 4. Install Ollama
1. Download from [Ollama Official Website](https://ollama.com/download/windows)
2. Run installer and follow the prompts
3. Open Command Prompt and verify:
   ```bash
   ollama --version
   ```

### 5. Clone Repository
```bash
git clone https://github.com/wen-da-ng/TinkerHub.git
cd TinkerHub
```

### 6. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip setuptools

# Install PyTorch with CUDA 11.8 support
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# Install transformers (will download models on first use)
pip install transformers

# Install remaining backend dependencies
pip install -r requirements.txt
```

### 7. Frontend Setup
```bash
cd frontend
npm install
```

### 8. Pull Ollama Models
```bash
# In a new Command Prompt window, pull models
ollama pull [MODEL NAME]( refer : https://ollama.com/search)

# Start Ollama server if not already running
ollama serve
```

### 9. Start the Application

#### Option 1: Run with Web GUI

**Start Backend:**
```bash
# From the project root directory
venv\Scripts\activate
python api_server.py
```

**Start Frontend:**
```bash
# In a new Command Prompt window, from the project root directory
cd frontend
npm run dev
```

#### Option 2: Run with CLI
```batch
venv\Scripts\activate
python app.py
```

## Troubleshooting

### Common Issues

#### CUDA Installation Problems
- Ensure you install CUDA 11.8, as other versions may not be compatible with the PyTorch version
- If `nvidia-smi` doesn't work, try reinstalling your NVIDIA drivers first, then CUDA
- Verify CUDA paths are in your system PATH environment variable

#### PyTorch CUDA Issues
- Verify PyTorch can see your GPU:
  ```python
  python -c "import torch; print(torch.cuda.is_available())"
  ```
  This should print "True"
- If False, reinstall PyTorch with the exact CUDA version specified

#### Ollama Model Download Failures
- Check your internet connection
- Ensure you have sufficient disk space
- Try restarting the Ollama service:
  ```bash
  ollama serve
  ```

### RAM Management

If you have 16GB RAM:
- Use smaller models (7B parameter models)
- Close unnecessary applications
- Reduce the maximum context size in the Ollama client settings

## License

MIT License - See LICENSE.md for details

---

**Note**: This installation guide was created on April 8, 2025. If you're using this guide significantly later, some components may have been updated. Check for newer versions and compatibility.
