# TinkerHub v0.3.6: AI Conversational Platform Setup Guide for Windows

## Prerequisites

### System Requirements
- Windows 10 or Windows 11 (64-bit)
- Minimum 16GB RAM (32GB recommended)
- NVIDIA GPU with CUDA support (highly recommended)
- Python 3.10
- Node.js 18+ 
- Git

### Hardware Recommendations
- CPU: Intel Core i5/i7 or AMD Ryzen 5/7
- RAM: 16GB (Minimum), 32GB (Recommended)
- GPU: NVIDIA RTX 3060 or better (8GB+ VRAM)
- Storage: 50GB free SSD space

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

### 5. Install Tesseract OCR
1. Download from [Tesseract GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Choose the latest installer (tesseract-ocr-w64-setup-vX.X.X.exe)
3. During installation:
   - Select "Additional language data (download)" 
   - Choose at least English
   - Check "Add to PATH" option
4. Verify in Command Prompt:
   ```bash
   tesseract --version
   ```

### 6. Clone Repository
```bash
git clone https://github.com/wen-da-ng/TinkerHub.git
cd TinkerHub
```

### 7. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install PyTorch with CUDA 11.8 support
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# Install TTS (will prompt for agreement to terms)
pip install TTS
# When prompted with "Agree to the model's terms of use (yes/no)?" type "yes" and press Enter

# Install transformers (will download models on first use)
pip install transformers

# Install remaining backend dependencies
pip install -r requirements.txt
```

### 8. Frontend Setup
```bash
cd frontend
npm install
npm run build
cd ..
```

### 9. Pull Ollama Models
```bash
# Start Ollama server if not already running
ollama serve

# In a new Command Prompt window, pull models
ollama pull deepseek-r1:14b
# When prompted, agree to the model's terms of use

ollama pull llama2:13b
# When prompted, agree to the model's terms of use
```

### 10. Start the Application

#### Option 1: Using separate Command Prompt windows

**Start Backend:**
```bash
# From the project root directory
cd backend
venv\Scripts\activate
python -m uvicorn app:app --reload --log-level debug
```

**Start Frontend:**
```bash
# In a new Command Prompt window, from the project root directory
cd frontend
npm run dev
```

#### Option 2: Using a batch file (create start.bat in project root)
```batch
@echo off
echo Starting TinkerHub...
echo.
echo Starting backend server...
start cmd /k "cd backend && venv\Scripts\activate && python -m uvicorn app:app --host 0.0.0.0 --port 8000"
echo.
echo Starting frontend...
start cmd /k "cd frontend && npm run dev"
echo.
echo Opening application in browser...
timeout /t 5
start http://localhost:3000
echo.
echo TinkerHub started successfully!
```

Run the batch file by double-clicking it or from Command Prompt:
```bash
start.bat
```

## First-Run Setup

When you run the application for the first time:

1. TinkerHub will prompt for downloading required ML models
   - The first download may take several minutes depending on your connection
   - BLIP-2 image model (approximately 8GB)
   - XTTS voice model (approximately 2GB)

2. Navigate to http://localhost:3000 in your browser
   - If you used the start.bat file, it should open automatically

3. Select a model from the dropdown (start with smaller models like llama2:7b for testing)

4. Start chatting!

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

#### Backend Startup Errors
- Clear database file if corrupted:
  ```bash
  del backend\conversations.db
  ```
- Check for conflicting processes on port 8000:
  ```bash
  netstat -ano | findstr :8000
  ```

#### Frontend Build Issues
- Clear npm cache:
  ```bash
  npm cache clean --force
  ```
- Delete node_modules and reinstall:
  ```bash
  cd frontend
  rmdir /s /q node_modules
  npm install
  ```

### RAM Management

If you have 16GB RAM:
- Use smaller models (7B parameter models)
- Close unnecessary applications
- Reduce the maximum context size in the Ollama client settings

## Performance Tips

1. **Optimize for your hardware:**
   - Use models that fit your GPU VRAM (check model size in GB)
   - With 8GB VRAM: Use 7B models
   - With 16GB+ VRAM: Use 13B-14B models

2. **Improve inference speed:**
   - Use "deepseek-r1:14b" for best balance of quality and speed
   - Set lower temperature values (0.5-0.7) for faster responses

3. **Folder scanning optimization:**
   - Limit folder size to under 100 files for best performance
   - Exclude binary files and large datasets from scanned folders

## License

MIT License - See LICENSE.md for details

---

**Note**: This installation guide was created on March 3, 2025. If you're using this guide significantly later, some components may have been updated. Check for newer versions and compatibility.