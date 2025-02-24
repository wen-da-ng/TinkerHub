# TinkerHub v0.3.6: AI Conversational Platform Setup Guide for Windows

## Prerequisites

### System Requirements
- Windows 10 or Windows 11 (64-bit)
- Minimum 16GB RAM (128GB recommended)
- NVIDIA GPU with CUDA support (highly recommended)
- Python 3.10 or later
- Node.js 18+ 
- Git

### Hardware Recommendations
- CPU: Intel Core i5/i7 or AMD Ryzen 5/7
- RAM: 16GB (Minimum) 
- GPU: NVIDIA RTX 3060 or better
- Storage: 50GB free SSD space

## Installation Steps

### 1. Install Python
1. Download Python 3.10+ from [Official Python Website](https://www.python.org/downloads/windows/)
2. During installation, check "Add Python to PATH"
3. Open Command Prompt and verify:
   ```bash
   python --version
   pip --version
   ```

### 2. Install CUDA (For GPU Support)
1. Download CUDA Toolkit from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
2. Choose Windows, x64, Installer type
3. Run installer, follow prompts
4. Verify installation:
   ```bash
   nvidia-smi
   ```

### 3. Install Node.js
1. Download from [Node.js Official Site](https://nodejs.org/)
2. Choose LTS version
3. Run installer, include npm
4. Verify in Command Prompt:
   ```bash
   node --version
   npm --version
   ```

### 4. Install Ollama
1. Download from [Ollama Official Website](https://ollama.com/download/windows)
2. Run installer
3. Open Command Prompt:
   ```bash
   ollama --version
   ```

### 5. Install Tesseract OCR
1. Download from [Tesseract GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install and add to PATH
3. Verify in Command Prompt:
   ```bash
   tesseract --version
   ```

### 6. Clone Repository
```bash
git clone https://github.com/wen-da-ng/TinkerHub.git
cd tinkerhub
```

### 7. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt
```

### 8. Frontend Setup
```bash
cd frontend
npm install
npm run build
```

### 9. Pull Ollama Models
```bash
ollama pull deepseek-r1:14b
ollama pull llama2:13b
```

### 10. Start Services

#### Start Ollama server
```bash
ollama serve
```

#### Start Backend
```bash
# In backend directory
cd backend
python -m uvicorn app:app --reload
```

#### Start Frontend
```bash
# In frontend directory
npm run dev
```

## Troubleshooting

### Common Issues
- Ensure all prerequisites are installed
- Check PATH environment variables
- Verify GPU drivers are up-to-date
- Restart computer after installations

## Performance Optimization
- Use an SSD for faster model loading
- Close background applications
- Update GPU drivers regularly

## Recommended Models
- deepseek-r1:14b (Balanced performance)
- llama2:13b (General purpose)

## License
MIT License - See LICENSE.md for details

---

**Note**: This guide assumes basic technical proficiency. If you encounter difficulties, seek help from technical support or community forums.