# System Information & Requirements

## 📋 System Requirements

### Minimum System Requirements
- **OS:** Windows 7 or higher (64-bit recommended)
- **RAM:** 2 GB minimum (4 GB recommended)
- **Storage:** 500 MB free space
- **Internet:** Required for auto-updates (optional for offline use)

### For Development (Python Setup)
- **Python:** 3.10 or higher
- **RAM:** 4 GB minimum
- **Storage:** 2 GB free space
- **Internet:** Required for package installation

## 🔧 Required Software

### Windows Users (Using .exe)
No additional software required! The `.exe` bundle includes everything needed.

**Optional:** Tesseract OCR (for scanned PDFs only)
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Installation: Run the installer and use default settings
- Path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### Linux Users (Development)
```bash
# Install Python 3 and dependencies
sudo apt update
sudo apt install python3 python3-pip python3-tk

# Install Tesseract OCR (optional, for scanned PDFs)
sudo apt install tesseract-ocr
```

### macOS Users (Development)
```bash
# Install Python 3 (if not already installed)
brew install python3

# Install Tesseract OCR (optional, for scanned PDFs)
brew install tesseract
```

## 📦 Python Dependencies (Development Only)

### Runtime Dependencies
```
customtkinter>=5.2.0          # Modern GUI framework
pillow>=10.0.0                # Image processing
psutil>=5.9.0                 # System monitoring (CPU/RAM gauges)
pdfplumber>=0.10.0            # PDF text extraction
pymupdf>=1.23.0               # Alternative PDF processing
pytesseract>=0.3.10           # OCR engine (fallback)
openpyxl>=3.1.0               # Excel file creation
pandas>=2.0.0                 # Data handling
```

### Build Dependencies (PyInstaller Only)
```
pyinstaller>=6.11.0           # Create standalone .exe
```

## ✅ Installation Steps

### For End Users (Windows .exe)
1. Download `RDX_CSBV_Extractor.exe` from [GitHub Releases](https://github.com/rjgaju2018-droid/rdx-csb-extractor/releases)
2. Double-click to run
3. Login with credentials (default: admin/admin123)
4. Start extracting shipping bills!

**First Run:**
- Desktop shortcut will be created automatically
- Start Menu entry will be added automatically

### For Developers (Python Setup)

#### 1. Clone Repository
```bash
git clone https://github.com/rjgaju2018-droid/rdx-csb-extractor.git
cd rdx-csb-extractor
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Install Tesseract (Optional)
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt install tesseract-ocr`
- macOS: `brew install tesseract`

#### 5. Run Application
```bash
python rdx_csb_app.py
```

### For Building .exe (Developers)

#### Prerequisites
- All runtime dependencies installed
- Tesseract OCR installed (optional)
- PyInstaller installed: `pip install pyinstaller>=6.11.0`

#### Build Command
```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build the .exe
pyinstaller build.spec
```

**Output:** `dist/RDX_CSBV_Extractor.exe`

## 🔐 Security & Credentials

### Default Credentials (First Login)
- **Username:** admin
- **Password:** admin123

⚠️ **Important:** Change default credentials immediately after first login!

User credentials are stored locally in `rdx_users.json` (encrypted with SHA256).

## 🐛 Troubleshooting

### Application Won't Start
1. Ensure .NET Framework 4.5+ is installed
2. Try running as Administrator
3. Check Windows Defender isn't blocking the .exe
4. Verify system meets minimum requirements

### PDF Extraction Issues
- **Text extraction failing:** PDF might be scanned/image-only. Install Tesseract OCR.
- **Excel export errors:** Ensure sufficient disk space and write permissions.
- **Memory issues:** Close other applications to free up RAM.

### Update Issues
- **Update not showing:** Check internet connection
- **Auto-update fails:** Try manual download from [GitHub Releases](https://github.com/rjgaju2018-droid/rdx-csb-extractor/releases)

### Tesseract Issues
- **"tesseract is not installed":** Install Tesseract OCR or add to PATH
- **OCR slow:** OCR only activates for scanned PDFs. Normal PDFs are much faster.

## 📞 Support

- **Email:** rjgaju2018@gmail.com
- **Phone:** +91 9983000552
- **Instagram:** [@gaja_vibe](https://insta.com/@gaja_vibe)
- **GitHub Issues:** [Report bugs here](https://github.com/rjgaju2018-droid/rdx-csb-extractor/issues)

## 📝 System Specifications Document

### Application Information
- **Name:** RDX Solution — CSB-V Shipping Bill Extractor
- **Current Version:** 1.0.7
- **Repository:** https://github.com/rjgaju2018-droid/rdx-csb-extractor
- **Auto-Update:** ✅ Enabled (checks on every Dashboard open)
- **Update Frequency:** Automatic (when new version tagged on GitHub)

### Features
- ✅ User authentication with secure password hashing
- ✅ Real-time CPU/RAM monitoring with analog gauges
- ✅ PDF text & image extraction
- ✅ Automatic Excel file generation
- ✅ Batch processing support
- ✅ Auto-update mechanism
- ✅ Desktop shortcuts (Windows)
- ✅ OCR fallback for scanned PDFs

### Performance
- **Startup Time:** 1-3 seconds (packaged .exe)
- **PDF Processing:** 0.5-2 seconds per PDF (depends on size/complexity)
- **Memory Usage:** 150-300 MB (depends on PDF batch size)
- **CPU Usage:** 20-60% during processing (multi-threaded)

---

**Last Updated:** 2026-07-01  
**Maintained by:** RDX Solution Team
