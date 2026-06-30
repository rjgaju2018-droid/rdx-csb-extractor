# RDx Solution — CSB-V Shipping Bill Extractor

Login + Dashboard (stats) + Processing Window (CPU/RAM live monitor, shipping
bill PDF se data extract, Excel me export).

---

## 📁 Repo me kaun-kaun si files honi chahiye

```
rdx-csb-extractor/
├── rdx_csb_app.py                       ← main app
├── requirements.txt                     ← required libraries list
├── .gitignore                           ← user-data files repo me na jaayein
├── README.md                            ← yeh file
├── rdx_soloution_logo.png  (optional)   ← apna logo (na ho to text-logo dikhega)
└── .github/
    └── workflows/
        └── build-windows-exe.yml        ← auto .exe banane ke liye (optional)
```

**Repo me MAT daalo** (ye khud-ba-khud app run karne par ban jaati hain, isliye `.gitignore` me already excluded hain):
- `rdx_users.json` (login accounts)
- `rdx_stats.json` (dashboard stats)
- koi bhi `*_output.xlsx` / `*_output.csv` (extraction results)

---

## 🚀 GitHub par upload karne ka step-by-step

### 1. GitHub par naya repository banao
- github.com → **New repository** → naam do (e.g. `rdx-csb-extractor`) → **Create repository** (README add mat karo, hum khud denge).

### 2. Apne PC par folder taiyar karo
Ek folder banao (e.g. `rdx-csb-extractor`) aur usme ye files daalo:
- `rdx_csb_app.py`
- `requirements.txt`
- `.gitignore`
- `README.md`
- (optional) apna logo `rdx_soloution_logo.png`
- (optional) `.github/workflows/build-windows-exe.yml`

### 3. Git commands chalao (folder ke andar, cmd/terminal me)
```bash
git init
git add .
git commit -m "RDx CSB-V Extractor - initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/rdx-csb-extractor.git
git push -u origin main
```
(`<your-username>` apna GitHub username daalo. Pehli baar push karte waqt GitHub login/token maangega.)

Bas — code ab GitHub par upload ho gaya. ✅

---

## ⚠️ Important: GitHub khud is app ko "run" nahi karega

Yeh ek **desktop GUI app** hai (window khulti hai, click hoti hai) — GitHub sirf code store karta hai, GUI render nahi kar sakta. Isliye 2 tarike hain "use" karne ke:

### Option A — Koi bhi clone karke apne PC par chalaye (sabse simple)
```bash
git clone https://github.com/<your-username>/rdx-csb-extractor.git
cd rdx-csb-extractor
pip install -r requirements.txt
python rdx_csb_app.py
```

### Option B — Automatic Windows .exe (bina Python install kiye chalaane ke liye)
`.github/workflows/build-windows-exe.yml` already is repo me hai. Jab bhi aap ek version-tag push karoge, GitHub Actions khud-ba-khud ek `.exe` bana kar **Releases** section me daal dega — log seedha download karke double-click se chala payenge.

Tag push karne ka tarika:
```bash
git tag v1.0.0
git push origin v1.0.0
```
Phir GitHub repo ke **Actions** tab me build chalti dikhegi (~2-3 min), aur complete hone par **Releases** tab me `RDx-CSB-Extractor.exe` mil jaayega.

(Manually bhi chala sakte ho: repo → **Actions** tab → **Build Windows EXE** → **Run workflow**.)

---

## 🔑 Default Login
- Username: `admin`
- Password: `admin123`

(Pehli baar run karne par `rdx_users.json` khud ban jaayegi.)

---

## 🛠 Local setup (development)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python rdx_csb_app.py
```

OCR (scanned PDFs) ke liye optional: [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) install karo. Normal text-PDFs ke liye iski zaroorat nahi.
