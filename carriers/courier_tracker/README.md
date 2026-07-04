# 🚀 Multi-Courier Tracking Software

## Supported Couriers
FedEx | DHL | UPS | Aramex | Shiprocket | OnPoint | ShipGlobal | Xindus

---

## ▶️ HOW TO RUN

### Windows (Sabse Easy):
```
Double-click: START.bat
```

### Manual:
```bash
pip install requests openpyxl
python app.py
```

---

## 📦 FILES
```
courier_tracker/
├── app.py                  ← Main GUI software
├── tracker_engine.py       ← Tracking engine (all couriers)
├── config.json             ← API keys (fill karein)
├── START.bat               ← Windows launcher
├── sample_tracking.csv     ← Sample import file
└── requirements.txt        ← Python packages
```

---

## ⚙️ SETUP

### Step 1: Software chalao
START.bat double-click karein

### Step 2: API Keys setup karein
"⚙️ API Settings" tab mein jaayein aur keys fill karein:

| Courier    | Kahan se milega API key          |
|------------|----------------------------------|
| FedEx      | developer.fedex.com              |
| DHL        | developer.dhl.com                |
| UPS        | developer.ups.com                |
| Aramex     | aramex.com (business account)    |
| Shiprocket | app.shiprocket.in (login creds)  |
| OnPoint    | 17track.net/en/api               |
| ShipGlobal | shipglobal.in (business account) |
| Xindus     | xindus.co (contact support)      |

### Step 3: Track karein
- Tracking numbers paste karein (ek line mein ek)
- "🚀 START TRACKING" click karein
- 200-300 numbers simultaneously track honge

---

## 💡 TRACKING NUMBER FORMAT

```
# Auto detect (recommended):
799999999999
1Z999AA10123456784

# Courier specify karein:
FedEx:799999999999
DHL:1234567890
UPS:1Z999AA10123456784
Aramex:12345678901
Shiprocket:SR123456789
```

---

## 📊 FEATURES
- ✅ 200-300 simultaneous tracking (30 parallel threads)
- ✅ Auto courier detection
- ✅ CSV/Excel import
- ✅ Excel export with color coding
- ✅ Live progress log
- ✅ Filter by status (Delivered/Transit/Error)
- ✅ Search by tracking number/courier
- ✅ Double-click for full tracking history
- ✅ No hanging - fully threaded
