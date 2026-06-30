"""
RDX Solution — CSB-V Extractor  (Complete App)
===============================================
Flash Screen  +  Login Page  +  Dashboard (stats)  +  Processing Window
(CPU/RAM analog dial monitor + Add Shipping Bills + Excel export)

UI Libraries:
    pip install customtkinter pillow psutil

Extractor Libraries:
    pip install pdfplumber pymupdf pytesseract openpyxl pandas

Run:
    python rdx_csb_app.py
"""

# ══════════════════════════════════════════════════════════════════════════════
#  STANDARD IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import os, re, sys, glob, json, math, hashlib, threading, time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
try:
    _RESAMPLE = Image.Resampling.LANCZOS   # Pillow 10+
except AttributeError:
    _RESAMPLE = Image.LANCZOS              # Pillow <10

# ── Extractor imports ────────────────────────────────────────────────────────
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    import fitz
    import pytesseract
    if os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
#  THEME & COLOURS  (RDX Gold Palette)
# ══════════════════════════════════════════════════════════════════════════════
CREAM       = "#F0EBE0"
DARK_BG     = "#1A1510"
CARD_BG     = "#211C14"
GOLD_DARK   = "#8B6914"
GOLD_MID    = "#C9962A"
GOLD_LIGHT  = "#E8C44A"
GOLD_SHINE  = "#F5D97A"
WHITE       = "#FFFFFF"
GREY_TEXT   = "#A09070"
RED_ERR     = "#E05555"
GREEN_OK    = "#55B055"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ══════════════════════════════════════════════════════════════════════════════
#  USER STORE  (JSON file based — exe ke liye simple & portable)
# ══════════════════════════════════════════════════════════════════════════════
USER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rdx_users.json")

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    # Default admin account
    default = {"admin": {"password": _hash("admin123"), "email": "admin@rdxsolution.com"}}
    save_users(default)
    return default

def save_users(users: dict):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ══════════════════════════════════════════════════════════════════════════════
#  STATS STORE  (Dashboard ke liye — total files processed, last run, etc.)
# ══════════════════════════════════════════════════════════════════════════════
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rdx_stats.json")

def load_stats() -> dict:
    default = {"total_runs": 0, "total_files_processed": 0,
               "total_rows_extracted": 0, "last_run": None,
               "last_run_files": 0, "last_run_rows": 0, "last_output": None}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                data = json.load(f)
                default.update(data)
        except Exception:
            pass
    return default

def save_stats(stats: dict):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def record_run(files_count: int, rows_count: int, output_path: str):
    stats = load_stats()
    stats["total_runs"] += 1
    stats["total_files_processed"] += files_count
    stats["total_rows_extracted"] += rows_count
    stats["last_run"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    stats["last_run_files"] = files_count
    stats["last_run_rows"] = rows_count
    stats["last_output"] = output_path
    save_stats(stats)
    return stats

# ══════════════════════════════════════════════════════════════════════════════
#  LOGO HELPER
# ══════════════════════════════════════════════════════════════════════════════
LOGO_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "rdx_soloution_logo.png"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
]

def load_logo(size=(220, 90)) -> ImageTk.PhotoImage | None:
    for p in LOGO_PATHS:
        if os.path.exists(p):
            try:
                img = Image.open(p).convert("RGBA").resize(size, _RESAMPLE)
                return ImageTk.PhotoImage(img)
            except Exception:
                pass
    return None

def load_ctk_logo(size=(220, 90)) -> ctk.CTkImage | None:
    for p in LOGO_PATHS:
        if os.path.exists(p):
            try:
                img = Image.open(p).convert("RGBA")
                return ctk.CTkImage(img, size=size)
            except Exception:
                pass
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  ROUND DIAL GAUGE  (analog "watch" style — CPU / RAM monitor)
# ══════════════════════════════════════════════════════════════════════════════
class DialGauge(tk.Canvas):
    """An analog watch-style round gauge, 0-100%."""
    def __init__(self, parent, label="CPU", size=140, **kwargs):
        super().__init__(parent, width=size, height=size,
                          bg=CARD_BG, highlightthickness=0, **kwargs)
        self.size = size
        self.label = label
        self.value = 0
        self._draw(0)

    def _draw(self, value):
        self.delete("all")
        s = self.size
        cx, cy = s / 2, s / 2
        r = s * 0.42
        start_ang, sweep_ang = 135, 270   # degrees, watch-dial style

        # Outer ring (case)
        self.create_oval(cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8,
                          outline=GOLD_DARK, width=2, fill=DARK_BG)
        # Track arc
        self.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=start_ang, extent=-sweep_ang,
                         style="arc", outline="#3A3322", width=8)
        # Value arc (colour shifts green -> gold -> red)
        if value < 60:
            col = GREEN_OK
        elif value < 85:
            col = GOLD_MID
        else:
            col = RED_ERR
        val_extent = -sweep_ang * (value / 100.0)
        if value > 0:
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                             start=start_ang, extent=val_extent,
                             style="arc", outline=col, width=8)
        # Tick marks
        for i in range(11):
            ang = math.radians(start_ang - sweep_ang * (i / 10))
            x1 = cx + (r - 10) * math.cos(ang)
            y1 = cy - (r - 10) * math.sin(ang)
            x2 = cx + (r - 2) * math.cos(ang)
            y2 = cy - (r - 2) * math.sin(ang)
            self.create_line(x1, y1, x2, y2, fill=GREY_TEXT, width=1)
        # Needle
        needle_ang = math.radians(start_ang - sweep_ang * (value / 100.0))
        nx = cx + (r - 14) * math.cos(needle_ang)
        ny = cy - (r - 14) * math.sin(needle_ang)
        self.create_line(cx, cy, nx, ny, fill=col, width=3, capstyle="round")
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=GOLD_LIGHT, outline="")

        # Centre readout
        self.create_text(cx, cy + r * 0.45, text=f"{value:.0f}%",
                          fill=WHITE, font=("Segoe UI", 13, "bold"))
        self.create_text(cx, cy + r * 0.45 + 18, text=self.label,
                          fill=GREY_TEXT, font=("Segoe UI", 9))

    def set_value(self, value):
        self.value = max(0, min(100, value))
        self._draw(self.value)



# ══════════════════════════════════════════════════════════════════════════════
#  FLASH / SPLASH SCREEN  (in-window frame — NOT a Toplevel, no wait_window block)
# ══════════════════════════════════════════════════════════════════════════════
class SplashScreen(ctk.CTkFrame):
    """
    NOTE: pehle yeh ek alag Toplevel window thi jise root.withdraw() +
    self.wait_window(splash) se modal/blocking dikhaya jaata tha. Yeh
    combination (withdraw + wait_window) customtkinter ke background
    scaling-tracker thread ke saath Windows par kabhi-kabhi deadlock/freeze
    kar deta tha. Ab splash sirf ek normal Frame hai jo App window ke
    andar hi dikhti hai aur self.after() se timer-based aage badhti hai —
    koi blocking loop nahi, koi freeze nahi.
    """
    def __init__(self, parent, on_done):
        super().__init__(parent, fg_color=DARK_BG)
        self.on_done = on_done
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(self, fg_color=DARK_BG, border_color=GOLD_MID,
                              border_width=2, corner_radius=10)
        inner.place(relx=0.5, rely=0.5, anchor="center", width=480, height=280)

        logo_ctk = load_ctk_logo(size=(240, 98))
        if logo_ctk:
            ctk.CTkLabel(inner, image=logo_ctk, text="").place(relx=0.5, rely=0.30, anchor="center")
        else:
            ctk.CTkLabel(inner, text="RDx Solution", font=("Georgia", 26, "bold"),
                         text_color=GOLD_LIGHT).place(relx=0.5, rely=0.30, anchor="center")

        ctk.CTkLabel(inner, text="Courier Shipping Bill  ·  Data Extractor",
                     font=("Segoe UI", 11), text_color=GREY_TEXT
                     ).place(relx=0.5, rely=0.58, anchor="center")

        self.progress = ctk.CTkProgressBar(inner, width=360, height=6,
                                           fg_color="#3A3322", progress_color=GOLD_LIGHT)
        self.progress.set(0)
        self.progress.place(relx=0.5, rely=0.74, anchor="center")

        self.status = ctk.CTkLabel(inner, text="Initializing…",
                                   font=("Segoe UI", 9), text_color=GREY_TEXT)
        self.status.place(relx=0.5, rely=0.85, anchor="center")

        self._steps = [
            (0.25, "Loading configuration…"),
            (0.55, "Preparing modules…"),
            (0.80, "Almost ready…"),
            (1.00, "Welcome to RDx Solution!"),
        ]
        self._step_idx = 0
        self._finished = False
        self.after(300, self._advance)
        # Failsafe: agar koi step fail ho jaaye to bhi 4 sec me login khud khul jaaye
        self.after(4000, self._finish)

    def _advance(self):
        if self._finished:
            return
        if self._step_idx >= len(self._steps):
            self._finish()
            return
        frac, msg = self._steps[self._step_idx]
        try:
            self.progress.set(frac)
            self.status.configure(text=msg)
        except Exception:
            pass
        self._step_idx += 1
        self.after(450, self._advance)

    def _finish(self):
        if self._finished:
            return
        self._finished = True
        try:
            self.on_done()
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
class LoginPage(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=DARK_BG)
        self.on_login_success = on_login_success
        self.users = load_users()
        self._build()

    # ── Live clock ────────────────────────────────────────────────────────────
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL (decoration) ──────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, width=260)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        logo_ctk = load_ctk_logo(size=(200, 82))
        if logo_ctk:
            ctk.CTkLabel(left, image=logo_ctk, text="").grid(row=0, column=0, pady=(0, 10))
        else:
            ctk.CTkLabel(left, text="RDx\nSolution",
                         font=("Georgia", 26, "bold"),
                         text_color=GOLD_LIGHT).grid(row=0, column=0)

        ctk.CTkLabel(left,
                     text="Shipping Bill\nData Extractor",
                     font=("Segoe UI", 12),
                     text_color=GREY_TEXT).grid(row=1, column=0, pady=(0, 40))

        # Live datetime on left panel
        self.dt_label = ctk.CTkLabel(left, text="", font=("Consolas", 10),
                                     text_color=GOLD_DARK)
        self.dt_label.grid(row=2, column=0, pady=(0, 20))
        self._tick()

        # ── RIGHT PANEL (form) ───────────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=50)
        right.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Welcome Back",
                     font=("Georgia", 22, "bold"),
                     text_color=GOLD_LIGHT).grid(row=0, column=0, pady=(60, 4), sticky="w")
        ctk.CTkLabel(right, text="Sign in to continue",
                     font=("Segoe UI", 11),
                     text_color=GREY_TEXT).grid(row=1, column=0, sticky="w", pady=(0, 30))

        # Username
        ctk.CTkLabel(right, text="Username", font=("Segoe UI", 11),
                     text_color=GREY_TEXT).grid(row=2, column=0, sticky="w")
        self.user_entry = ctk.CTkEntry(right, placeholder_text="Enter username",
                                       height=42, fg_color=CARD_BG,
                                       border_color=GOLD_DARK, border_width=1,
                                       text_color=WHITE, font=("Segoe UI", 12))
        self.user_entry.grid(row=3, column=0, sticky="ew", pady=(4, 14))

        # Password
        ctk.CTkLabel(right, text="Password", font=("Segoe UI", 11),
                     text_color=GREY_TEXT).grid(row=4, column=0, sticky="w")
        self.pass_entry = ctk.CTkEntry(right, placeholder_text="Enter password",
                                       show="●", height=42, fg_color=CARD_BG,
                                       border_color=GOLD_DARK, border_width=1,
                                       text_color=WHITE, font=("Segoe UI", 12))
        self.pass_entry.grid(row=5, column=0, sticky="ew", pady=(4, 6))
        self.pass_entry.bind("<Return>", lambda e: self._login())

        # Show/hide password toggle
        self.show_pw = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(right, text="Show password", variable=self.show_pw,
                        command=self._toggle_pw,
                        font=("Segoe UI", 10), text_color=GREY_TEXT,
                        fg_color=GOLD_DARK, hover_color=GOLD_MID,
                        checkmark_color=WHITE, border_color=GOLD_DARK
                        ).grid(row=6, column=0, sticky="w", pady=(0, 4))

        # Forgot password link
        fp_btn = ctk.CTkButton(right, text="Forgot Password?", fg_color="transparent",
                               text_color=GOLD_MID, hover_color=CARD_BG,
                               font=("Segoe UI", 10, "underline"), height=20,
                               command=self._forgot_pw)
        fp_btn.grid(row=6, column=0, sticky="e")

        # Error label
        self.err_label = ctk.CTkLabel(right, text="", text_color=RED_ERR,
                                      font=("Segoe UI", 10))
        self.err_label.grid(row=7, column=0, pady=(4, 0))

        # Login button
        self.login_btn = ctk.CTkButton(
            right, text="LOGIN",
            height=44, corner_radius=6,
            fg_color=GOLD_MID, hover_color=GOLD_DARK,
            text_color=DARK_BG, font=("Segoe UI", 13, "bold"),
            command=self._login
        )
        self.login_btn.grid(row=8, column=0, sticky="ew", pady=(16, 10))

        # Divider
        div = ctk.CTkFrame(right, fg_color=GOLD_DARK, height=1)
        div.grid(row=9, column=0, sticky="ew", pady=10)

        # Create account
        ctk.CTkLabel(right, text="New user?", font=("Segoe UI", 10),
                     text_color=GREY_TEXT).grid(row=10, column=0, pady=(0, 2))
        ctk.CTkButton(right, text="Create New Account",
                      height=40, corner_radius=6,
                      fg_color="transparent", border_color=GOLD_DARK, border_width=1,
                      text_color=GOLD_LIGHT, hover_color=CARD_BG,
                      font=("Segoe UI", 11),
                      command=self._new_account
                      ).grid(row=11, column=0, sticky="ew", pady=(0, 40))

    def _tick(self):
        now = datetime.now()
        day  = now.strftime("%A")
        date = now.strftime("%d %B %Y")
        time_str = now.strftime("%I:%M:%S %p")
        self.dt_label.configure(text=f"{day}\n{date}\n{time_str}")
        self.after(1000, self._tick)

    def _toggle_pw(self):
        self.pass_entry.configure(show="" if self.show_pw.get() else "●")

    def _login(self):
        uname = self.user_entry.get().strip()
        pw    = self.pass_entry.get()
        self.users = load_users()
        if not uname or not pw:
            self.err_label.configure(text="⚠  Username aur password dono required hain.")
            return
        if uname not in self.users:
            self.err_label.configure(text="✗  Username nahi mila.")
            return
        if self.users[uname]["password"] != _hash(pw):
            self.err_label.configure(text="✗  Password galat hai.")
            return
        self.err_label.configure(text="")
        self.on_login_success(uname)

    # ── Forgot Password popup ─────────────────────────────────────────────────
    def _forgot_pw(self):
        win = ctk.CTkToplevel(self)
        win.title("Reset Password")
        win.geometry("380x300")
        win.configure(fg_color=DARK_BG)
        win.grab_set()

        ctk.CTkLabel(win, text="Reset Password", font=("Georgia", 16, "bold"),
                     text_color=GOLD_LIGHT).pack(pady=(24, 4))
        ctk.CTkLabel(win, text="Username aur naya password enter karo",
                     font=("Segoe UI", 10), text_color=GREY_TEXT).pack(pady=(0, 16))

        u = ctk.CTkEntry(win, placeholder_text="Username", height=38,
                         fg_color=CARD_BG, border_color=GOLD_DARK,
                         text_color=WHITE)
        u.pack(padx=30, fill="x", pady=4)
        p1 = ctk.CTkEntry(win, placeholder_text="Naya Password", show="●", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        p1.pack(padx=30, fill="x", pady=4)
        p2 = ctk.CTkEntry(win, placeholder_text="Password Confirm karo", show="●", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        p2.pack(padx=30, fill="x", pady=4)
        err = ctk.CTkLabel(win, text="", text_color=RED_ERR, font=("Segoe UI", 10))
        err.pack()

        def do_reset():
            uname = u.get().strip()
            np1   = p1.get()
            np2   = p2.get()
            users = load_users()
            if uname not in users:
                err.configure(text="✗  Username nahi mila.")
                return
            if len(np1) < 6:
                err.configure(text="⚠  Password kam se kam 6 characters ka hona chahiye.")
                return
            if np1 != np2:
                err.configure(text="✗  Passwords match nahi kar rahe.")
                return
            users[uname]["password"] = _hash(np1)
            save_users(users)
            messagebox.showinfo("Done", "Password reset ho gaya! ✅", parent=win)
            win.destroy()

        ctk.CTkButton(win, text="Reset Password", height=40,
                      fg_color=GOLD_MID, hover_color=GOLD_DARK,
                      text_color=DARK_BG, font=("Segoe UI", 11, "bold"),
                      command=do_reset).pack(padx=30, fill="x", pady=12)

    # ── New Account popup ─────────────────────────────────────────────────────
    def _new_account(self):
        win = ctk.CTkToplevel(self)
        win.title("Create Account")
        win.geometry("380x360")
        win.configure(fg_color=DARK_BG)
        win.grab_set()

        ctk.CTkLabel(win, text="Create Account", font=("Georgia", 16, "bold"),
                     text_color=GOLD_LIGHT).pack(pady=(24, 4))
        ctk.CTkLabel(win, text="Apna naya account banao",
                     font=("Segoe UI", 10), text_color=GREY_TEXT).pack(pady=(0, 16))

        u  = ctk.CTkEntry(win, placeholder_text="Username", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        u.pack(padx=30, fill="x", pady=4)
        em = ctk.CTkEntry(win, placeholder_text="Email (optional)", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        em.pack(padx=30, fill="x", pady=4)
        p1 = ctk.CTkEntry(win, placeholder_text="Password", show="●", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        p1.pack(padx=30, fill="x", pady=4)
        p2 = ctk.CTkEntry(win, placeholder_text="Confirm Password", show="●", height=38,
                          fg_color=CARD_BG, border_color=GOLD_DARK, text_color=WHITE)
        p2.pack(padx=30, fill="x", pady=4)
        err = ctk.CTkLabel(win, text="", text_color=RED_ERR, font=("Segoe UI", 10))
        err.pack()

        def do_create():
            uname = u.get().strip()
            email = em.get().strip()
            np1   = p1.get()
            np2   = p2.get()
            users = load_users()
            if not uname:
                err.configure(text="⚠  Username required hai."); return
            if uname in users:
                err.configure(text="✗  Yeh username pehle se exist karta hai."); return
            if len(np1) < 6:
                err.configure(text="⚠  Password kam se kam 6 characters."); return
            if np1 != np2:
                err.configure(text="✗  Passwords match nahi kar rahe."); return
            users[uname] = {"password": _hash(np1), "email": email}
            save_users(users)
            messagebox.showinfo("Account Bana!", f"Account '{uname}' ban gaya ✅\nAb login karo.", parent=win)
            win.destroy()

        ctk.CTkButton(win, text="Create Account", height=40,
                      fg_color=GOLD_MID, hover_color=GOLD_DARK,
                      text_color=DARK_BG, font=("Segoe UI", 11, "bold"),
                      command=do_create).pack(padx=30, fill="x", pady=12)

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD  (login ke baad — stats + "Open Processing Window")
# ══════════════════════════════════════════════════════════════════════════════
class Dashboard(ctk.CTkFrame):
    def __init__(self, master, username, on_open_processing):
        super().__init__(master, fg_color=DARK_BG)
        self.username = username
        self.on_open_processing = on_open_processing
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=56)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)

        logo_ctk = load_ctk_logo(size=(110, 44))
        if logo_ctk:
            ctk.CTkLabel(topbar, image=logo_ctk, text="").grid(row=0, column=0, padx=16, pady=6)
        else:
            ctk.CTkLabel(topbar, text="RDx Solution", font=("Georgia", 14, "bold"),
                         text_color=GOLD_LIGHT).grid(row=0, column=0, padx=16)

        ctk.CTkLabel(topbar, text="Dashboard", font=("Segoe UI", 13, "bold"),
                     text_color=GOLD_MID).grid(row=0, column=1, sticky="w")

        user_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        user_frame.grid(row=0, column=2, padx=16)
        ctk.CTkLabel(user_frame, text=f"👤 {self.username}",
                     font=("Segoe UI", 10), text_color=GREY_TEXT).pack(side="left", padx=(0, 8))
        ctk.CTkButton(user_frame, text="Logout", width=70, height=28,
                      fg_color=GOLD_DARK, hover_color=RED_ERR,
                      text_color=WHITE, font=("Segoe UI", 9),
                      command=self._logout).pack(side="left")

        # ── Welcome ──────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text=f"Welcome back, {self.username} 👋",
                     font=("Georgia", 20, "bold"),
                     text_color=GOLD_LIGHT).grid(row=1, column=0, sticky="w", padx=30, pady=(24, 2))
        ctk.CTkLabel(self, text="Shipping Bill Data Extractor — overview",
                     font=("Segoe UI", 11), text_color=GREY_TEXT
                     ).grid(row=2, column=0, sticky="w", padx=30, pady=(0, 16))

        # ── Stats cards ──────────────────────────────────────────────────────
        stats = load_stats()
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=3, column=0, sticky="ew", padx=30)
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)

        def stat_card(col, title, value):
            c = ctk.CTkFrame(cards, fg_color=CARD_BG, corner_radius=10,
                              border_color=GOLD_DARK, border_width=1)
            c.grid(row=0, column=col, sticky="nsew", padx=8, pady=4)
            ctk.CTkLabel(c, text=str(value), font=("Segoe UI", 22, "bold"),
                         text_color=GOLD_LIGHT).pack(pady=(16, 0))
            ctk.CTkLabel(c, text=title, font=("Segoe UI", 10),
                         text_color=GREY_TEXT).pack(pady=(2, 16))

        stat_card(0, "Total Files Processed", stats["total_files_processed"])
        stat_card(1, "Total Rows Extracted", stats["total_rows_extracted"])
        stat_card(2, "Total Runs", stats["total_runs"])
        stat_card(3, "Last Run", stats["last_run"] or "—")

        if stats["last_output"]:
            ctk.CTkLabel(self,
                         text=f"📄 Last Excel Output: {stats['last_output']}",
                         font=("Segoe UI", 10), text_color=GREY_TEXT
                         ).grid(row=4, column=0, sticky="w", padx=30, pady=(8, 0))

        # ── CPU / RAM mini-watch on dashboard ───────────────────────────────
        mon = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10,
                            border_color=GOLD_DARK, border_width=1)
        mon.grid(row=5, column=0, sticky="ew", padx=30, pady=24)
        ctk.CTkLabel(mon, text="System Monitor", font=("Segoe UI", 12, "bold"),
                     text_color=GOLD_MID).pack(pady=(12, 4))
        gframe = ctk.CTkFrame(mon, fg_color="transparent")
        gframe.pack(pady=(0, 14))
        self.cpu_gauge = DialGauge(gframe, label="CPU", size=120)
        self.cpu_gauge.grid(row=0, column=0, padx=20)
        self.ram_gauge = DialGauge(gframe, label="RAM", size=120)
        self.ram_gauge.grid(row=0, column=1, padx=20)
        self._monitoring = True
        self._update_gauges()

        # ── Open processing window button ───────────────────────────────────
        ctk.CTkButton(self, text="▶  Open Processing Window",
                      height=50, corner_radius=8,
                      fg_color=GOLD_MID, hover_color=GOLD_DARK,
                      text_color=DARK_BG, font=("Segoe UI", 14, "bold"),
                      command=self._open
                      ).grid(row=6, column=0, sticky="ew", padx=30, pady=(0, 30))

    def _update_gauges(self):
        if not getattr(self, "_monitoring", False):
            return
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
            else:
                cpu = ram = 0
            self.cpu_gauge.set_value(cpu)
            self.ram_gauge.set_value(ram)
            self.after(1200, self._update_gauges)
        except Exception:
            pass

    def _open(self):
        self._monitoring = False
        self.on_open_processing(self.username)

    def _logout(self):
        self._monitoring = False
        self.master._show_login()

# ══════════════════════════════════════════════════════════════════════════════
#  CSB EXTRACTOR — BACKEND  (same as csb_extractor_final.py)
# ══════════════════════════════════════════════════════════════════════════════
COLUMNS = [
    "File Name", "CSB Number", "Name of the Consignee", "Filing Date",
    "HAWB Number", "EGM Number", "EGM Date", "Invoice Number", "Invoice Date",
    "Goods Description", "Total Taxable Value", "Taxable Value Currency",
    "FOB Value (In INR)", "Exchange Rate",
]

def get_all_words(pdf_path):
    all_words = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg_num, page in enumerate(pdf.pages, 1):
            for w in page.extract_words():
                all_words.append({"text": w["text"], "x0": w["x0"],
                                  "top": w["top"], "page": pg_num})
    return all_words

def get_all_chars(pdf_path):
    all_chars = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg_num, page in enumerate(pdf.pages, 1):
            for c in page.chars:
                all_chars.append({"text": c["text"], "x0": c["x0"],
                                  "width": c["width"], "top": c["top"], "page": pg_num})
    return all_chars

def chars_to_text(chars, gap_threshold=2.0):
    if not chars:
        return ""
    chars = sorted(chars, key=lambda c: c["x0"])
    result = chars[0]["text"]
    for i in range(1, len(chars)):
        prev_end = chars[i-1]["x0"] + chars[i-1]["width"]
        if chars[i]["x0"] - prev_end > gap_threshold:
            result += " "
        result += chars[i]["text"]
    return result.strip()

def find_value_near_label(words, label_pattern, value_pattern=r".+"):
    label_re = re.compile(label_pattern, re.IGNORECASE)
    value_re = re.compile(r"^" + value_pattern + r"$", re.IGNORECASE)
    for w in words:
        if label_re.search(w["text"]):
            lpage, ltop = w["page"], w["top"]
            same = sorted([x for x in words if x["page"] == lpage
                           and abs(x["top"] - ltop) <= 5
                           and x["x0"] > w["x0"] + 5
                           and not label_re.search(x["text"])], key=lambda x: x["x0"])
            for x in same:
                if value_re.match(x["text"]):
                    return x["text"].strip()
            below = [x for x in words if x["page"] == lpage and 0 < x["top"] - ltop <= 18]
            if below:
                min_top = min(x["top"] for x in below)
                for x in sorted([x for x in below if abs(x["top"] - min_top) <= 3],
                                 key=lambda x: x["x0"]):
                    if value_re.match(x["text"]):
                        return x["text"].strip()
    return ""

def extract_csb_plumber(words):
    for w in words:
        if re.search(r"CSBNumber:", w["text"], re.IGNORECASE):
            lpage, ltop = w["page"], w["top"]
            same = sorted([x for x in words if x["page"] == lpage
                           and abs(x["top"] - ltop) <= 5 and x["x0"] > w["x0"] + 5],
                          key=lambda x: x["x0"])
            part1 = next((x["text"] for x in same
                          if re.match(r"CSBV_", x["text"], re.IGNORECASE)), "")
            if not part1:
                continue
            below = [x for x in words if x["page"] == lpage and 0 < x["top"] - ltop <= 20]
            if below:
                min_top = min(x["top"] for x in below)
                for x in sorted([x for x in below if abs(x["top"] - min_top) <= 3],
                                 key=lambda x: x["x0"]):
                    if re.match(r"^\d{2}[_\-]\d+$", x["text"]):
                        return part1 + "_" + x["text"]
            return part1
    return ""

def extract_name_from_chars(all_chars, words, label_pattern, y_tolerance=4):
    label_re = re.compile(label_pattern, re.IGNORECASE)
    for w in words:
        if label_re.search(w["text"]):
            lpage, ltop = w["page"], w["top"]
            vwords = sorted([x for x in words if x["page"] == lpage
                             and abs(x["top"] - ltop) <= 5 and x["x0"] > w["x0"] + 5
                             and not label_re.search(x["text"])], key=lambda x: x["x0"])
            if not vwords:
                continue
            vx = vwords[0]["x0"] - 1
            row_chars = [c for c in all_chars if c["page"] == lpage
                         and abs(c["top"] - ltop) <= y_tolerance and c["x0"] >= vx]
            if row_chars:
                return chars_to_text(row_chars)
    return ""

def extract_invoice_fields_plumber(words):
    inv_num_lbl = inv_date_lbl = None
    for w in words:
        if re.match(r"InvoiceNumber:", w["text"], re.IGNORECASE):
            inv_num_lbl = w
        if re.match(r"InvoiceDate:", w["text"], re.IGNORECASE):
            inv_date_lbl = w
    result = {"Invoice Number": "", "Invoice Date": ""}
    if not inv_num_lbl:
        return result
    lpage, ltop = inv_num_lbl["page"], inv_num_lbl["top"]
    below = [x for x in words if x["page"] == lpage and 0 < x["top"] - ltop <= 20]
    if not below:
        return result
    min_top  = min(x["top"] for x in below)
    data_row = sorted([x for x in below if abs(x["top"] - min_top) <= 3], key=lambda x: x["x0"])
    for x in data_row:
        if re.match(r"[A-Za-z][A-Za-z0-9\-\/\.]+", x["text"]) and abs(x["x0"] - inv_num_lbl["x0"]) < 80:
            result["Invoice Number"] = x["text"].strip()
            break
    if inv_date_lbl:
        for x in data_row:
            if re.match(r"\d{2}/\d{2}/\d{4}", x["text"]) and abs(x["x0"] - inv_date_lbl["x0"]) < 80:
                result["Invoice Date"] = x["text"].strip()
                break
    return result

def extract_all_items_plumber(all_chars, words):
    """
    BUG FIX: pehle yeh function plain word-join (" ".join(...)) use karta tha,
    jisse PDF-merged words jaise 'HANDMADE100COTTONRUG' bina space ke aate the.
    Ab character-gap detection (chars_to_text) use karte hain — same logic jo
    single-item extract_name_from_chars() me use hoti hai — taaki goods
    description sahi se spaced niklein, multi-item bills ke liye bhi.
    """
    goods_list, taxval_list = [], []
    goods_re  = re.compile(r"GoodsDescription:", re.IGNORECASE)
    taxval_re = re.compile(r"TotalTaxableValue:", re.IGNORECASE)
    seen_taxval_positions = set()

    for w in words:
        lpage, ltop = w["page"], w["top"]

        if goods_re.search(w["text"]):
            vwords = sorted([x for x in words if x["page"] == lpage
                             and abs(x["top"] - ltop) <= 5 and x["x0"] > w["x0"] + 5
                             and not goods_re.search(x["text"])], key=lambda x: x["x0"])
            if vwords:
                vx = vwords[0]["x0"] - 1
                row_chars = [c for c in all_chars if c["page"] == lpage
                             and abs(c["top"] - ltop) <= 4 and c["x0"] >= vx]
                val = chars_to_text(row_chars) if row_chars else ""
                if val:
                    goods_list.append(val)

        if taxval_re.search(w["text"]) and (lpage, round(ltop)) not in seen_taxval_positions:
            seen_taxval_positions.add((lpage, round(ltop)))
            vwords = sorted([x for x in words if x["page"] == lpage
                             and abs(x["top"] - ltop) <= 5 and x["x0"] > w["x0"] + 5
                             and not taxval_re.search(x["text"])], key=lambda x: x["x0"])
            val_re = re.compile(r"^[\d,\.]+$")
            val = next((x["text"].strip() for x in vwords if val_re.match(x["text"])), "")
            if val:
                taxval_list.append(val)

    n = max(len(goods_list), len(taxval_list), 1)
    return [(goods_list[i] if i < len(goods_list) else "",
             taxval_list[i] if i < len(taxval_list) else "") for i in range(n)]

def has_text_layer(pdf_path, min_chars=50):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = sum(len(page.extract_text() or "") for page in pdf.pages[:3])
        return total >= min_chars
    except Exception:
        return False

def parse_with_plumber(pdf_path):
    words     = get_all_words(pdf_path)
    all_chars = get_all_chars(pdf_path)
    inv   = extract_invoice_fields_plumber(words)
    items = extract_all_items_plumber(all_chars, words)
    base  = {
        "CSB Number":             extract_csb_plumber(words),
        "Name of the Consignee":  extract_name_from_chars(all_chars, words, r"NameoftheConsignee:"),
        "Filing Date":            find_value_near_label(words, r"FillingDate:",         r"\d{2}/\d{2}/\d{4}"),
        "HAWB Number":            find_value_near_label(words, r"HAWBNumber:",          r"[A-Z0-9]+"),
        "EGM Number":             find_value_near_label(words, r"EGMNumber:",           r"\d+"),
        "EGM Date":               find_value_near_label(words, r"EGMDate:",             r"\d{2}/\d{2}/\d{4}"),
        "Invoice Number":         inv["Invoice Number"],
        "Invoice Date":           inv["Invoice Date"],
        "Taxable Value Currency": find_value_near_label(words, r"TaxableValueCurrency:", r"[A-Z]{3}"),
        "FOB Value (In INR)":     find_value_near_label(words, r"FOBValue\(InINR\):",   r"[\d,\.]+"),
        "Exchange Rate":          find_value_near_label(words, r"ExchangeRate:",         r"[\d,\.]+"),
    }
    return base, items

def parse_with_ocr(pdf_path):
    doc   = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix  = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(pytesseract.image_to_string(img, config="--psm 6"))
    doc.close()
    text = "\n".join(pages)

    def rx(pattern, group=1, flags=re.IGNORECASE):
        m = re.search(pattern, text, flags)
        return m.group(group).strip() if m else ""

    egm_no = rx(r"EGM\s*Number[:\s|]*([\d]+)")
    egm_dt = rx(r"EGM\s*Date[:\s|]*([\d]{2}/[\d]{2}/[\d]{4})")

    m_inv = re.search(
        r"Invoice\s*Value\s*\(in\s*INR\)[^\n]*\n\s*([A-Z]{2,4}-[\d\s/\\\-]+?)\s+([\d]{2}/[\d]{2}/[\d]{4})",
        text, re.IGNORECASE | re.DOTALL)
    inv_no = re.sub(r"\s+", "", re.sub(r"\s*/\s*$", "7", m_inv.group(1).strip())) if m_inv else \
             rx(r"Invoice\s*Number[:\s|]+([A-Z]{2,4}-[\d\-]+)")
    inv_dt = m_inv.group(2).strip() if m_inv else rx(r"Invoice\s*Date[:\s|]+([\d]{2}/[\d]{2}/[\d]{4})")

    goods  = [re.sub(r"\s+", " ", g).strip()
              for g in re.findall(r"Goods\s*Description[:\s|]+([^\n]{3,80})", text, re.IGNORECASE)]
    taxval = [v.replace(",", "").strip()
              for v in re.findall(r"Total\s*Taxable\s*Value[:\s|]+([\d.,]+)", text, re.IGNORECASE)]
    n = max(len(goods), len(taxval), 1)
    items = [(goods[i] if i < len(goods) else "",
              taxval[i] if i < len(taxval) else "") for i in range(n)]

    base = {
        "CSB Number":             rx(r"CSB\s*Number[:\s|]+.*?\n\s*([\d\s_]+)"),
        "Name of the Consignee":  rx(r"Name\s*of\s*the\s*Consignee[:\s|]+([^\n]{3,80})"),
        "Filing Date":            rx(r"Filling\s*Date[:\s|]+([\d]{2}/[\d]{2}/[\d]{4})"),
        "HAWB Number":            rx(r"HAWB\s*Number[:\s|]+([1I][ZG0-9A-Z/\-]+)"),
        "EGM Number":             egm_no,
        "EGM Date":               egm_dt,
        "Invoice Number":         inv_no,
        "Invoice Date":           inv_dt,
        "Taxable Value Currency": rx(r"FOB\s*Currency[^|]*\|\s*([A-Z]{3})") or "USD",
        "FOB Value (In INR)":     rx(r"FOB\s*Value\s*\(In\s*INR\)[:\s|]*([\d,]+\.?\d*)").replace(",",""),
        "Exchange Rate":          rx(r"(?<!FOB)(?<!FOB )Exchange\s*Rate[:\s|]*([\d.]+)") or
                                  rx(r"FOB\s*Exchange\s*Rate[^|]*\|\s*([\d.]+)") or
                                  rx(r"FOB\s*Exchange\s*Rate[^\d\n]*([\d.]+)"),
    }
    return base, items

def parse_bill(pdf_path):
    if has_text_layer(pdf_path):
        base, items = parse_with_plumber(pdf_path)
        method = "plumber"
    elif OCR_AVAILABLE:
        base, items = parse_with_ocr(pdf_path)
        method = "ocr"
    else:
        raise RuntimeError("PDF mein text layer nahi + OCR install nahi hai.")
    fname = os.path.basename(pdf_path)
    rows  = [{"File Name": fname, **base,
               "Goods Description":   g,
               "Total Taxable Value": t} for g, t in items]
    return rows, method

def build_excel(all_rows, output_path):
    wb  = Workbook()
    ws  = wb.active
    ws.title = "Shipping Bills"
    ws.sheet_view.showGridLines = False
    thin     = Side(style="thin", color="BBBBBB")
    BDR      = Border(left=thin, right=thin, top=thin, bottom=thin)
    HDR_FILL = PatternFill("solid", fgColor="1F3864")
    ALT_FILL = PatternFill("solid", fgColor="EBF3FB")
    WHT_FILL = PatternFill("solid", fgColor="FFFFFF")
    HDR_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    DAT_FONT = Font(name="Arial", size=9)
    CTR      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LFT      = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    WIDTHS   = {
        "File Name": 24, "CSB Number": 28, "Name of the Consignee": 28,
        "Filing Date": 13, "HAWB Number": 22, "EGM Number": 13, "EGM Date": 13,
        "Invoice Number": 17, "Invoice Date": 13, "Goods Description": 35,
        "Total Taxable Value": 16, "Taxable Value Currency": 18,
        "FOB Value (In INR)": 16, "Exchange Rate": 13,
    }
    LEFT_COLS = {"File Name", "Goods Description", "Name of the Consignee"}
    ws.row_dimensions[1].height = 32
    for ci, col in enumerate(COLUMNS, 1):
        c = ws.cell(row=1, column=ci, value=col)
        c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CTR; c.border = BDR
        ws.column_dimensions[get_column_letter(ci)].width = WIDTHS.get(col, 15)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}1"
    for ri, row in enumerate(all_rows, 2):
        fill = ALT_FILL if ri % 2 == 0 else WHT_FILL
        ws.row_dimensions[ri].height = 18
        for ci, col in enumerate(COLUMNS, 1):
            val = row.get(col, "")
            if col in ("Total Taxable Value", "FOB Value (In INR)", "Exchange Rate"):
                try: val = float(str(val).replace(",", ""))
                except: pass
            c = ws.cell(row=ri, column=ci, value=val)
            c.font = DAT_FONT; c.fill = fill; c.border = BDR
            c.alignment = LFT if col in LEFT_COLS else CTR
    wb.save(output_path)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN EXTRACTOR WINDOW  (shown after login)
# ══════════════════════════════════════════════════════════════════════════════
class ExtractorWindow(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=DARK_BG)
        self.username    = username
        self.bill_files  = []          # added shipping bill PDFs
        self.output_file = tk.StringVar(value="")
        self.running     = False
        self._monitoring = True
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=56)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)

        logo_ctk = load_ctk_logo(size=(110, 44))
        if logo_ctk:
            ctk.CTkLabel(topbar, image=logo_ctk, text="").grid(row=0, column=0, padx=16, pady=6)
        else:
            ctk.CTkLabel(topbar, text="RDx Solution", font=("Georgia", 14, "bold"),
                         text_color=GOLD_LIGHT).grid(row=0, column=0, padx=16)

        ctk.CTkLabel(topbar, text="CSB-V Shipping Bill Extractor — Processing Window",
                     font=("Segoe UI", 13, "bold"),
                     text_color=GOLD_MID).grid(row=0, column=1, sticky="w")

        # Back + User + logout
        user_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        user_frame.grid(row=0, column=2, padx=16)
        ctk.CTkButton(user_frame, text="⬅ Dashboard", width=100, height=28,
                      fg_color=GOLD_DARK, hover_color=GOLD_MID,
                      text_color=WHITE, font=("Segoe UI", 9),
                      command=self._back_to_dashboard).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(user_frame, text=f"👤 {self.username}",
                     font=("Segoe UI", 10), text_color=GREY_TEXT).pack(side="left", padx=(0, 8))
        ctk.CTkButton(user_frame, text="Logout", width=70, height=28,
                      fg_color=GOLD_DARK, hover_color=RED_ERR,
                      text_color=WHITE, font=("Segoe UI", 9),
                      command=self._logout).pack(side="left")

        # ── Live datetime strip ───────────────────────────────────────────────
        self.dt_bar = ctk.CTkLabel(self, text="", font=("Consolas", 10),
                                   text_color=GOLD_DARK, fg_color=DARK_BG)
        self.dt_bar.grid(row=1, column=0, sticky="e", padx=20, pady=(4, 0))
        self._tick()

        # ── CPU / RAM monitor (round dial watches) ─────────────────────────────
        mon = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10)
        mon.grid(row=2, column=0, padx=30, pady=(16, 0), sticky="ew")
        ctk.CTkLabel(mon, text="🖥  System Monitor", font=("Segoe UI", 11, "bold"),
                     text_color=GOLD_MID).pack(pady=(10, 2))
        gframe = ctk.CTkFrame(mon, fg_color="transparent")
        gframe.pack(pady=(0, 10))
        self.cpu_gauge = DialGauge(gframe, label="CPU", size=110)
        self.cpu_gauge.grid(row=0, column=0, padx=16)
        self.ram_gauge = DialGauge(gframe, label="RAM", size=110)
        self.ram_gauge.grid(row=0, column=1, padx=16)
        self._update_gauges()

        # ── Card: Add shipping bills + output ───────────────────────────────────
        card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10)
        card.grid(row=3, column=0, padx=30, pady=16, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        btn_row.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(btn_row, text="➕  Add Shipping Bill(s)", height=36,
                      fg_color=GOLD_MID, hover_color=GOLD_DARK, text_color=DARK_BG,
                      font=("Segoe UI", 11, "bold"),
                      command=self._add_files).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btn_row, text="🗑  Remove Selected", height=36,
                      fg_color=GOLD_DARK, hover_color=RED_ERR, text_color=WHITE,
                      command=self._remove_selected).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(btn_row, text="✖  Clear All", height=36,
                      fg_color=GOLD_DARK, hover_color=RED_ERR, text_color=WHITE,
                      command=self._clear_files).grid(row=0, column=2, padx=(0, 8))
        self.count_lbl = ctk.CTkLabel(btn_row, text="0 shipping bill(s) added",
                                      font=("Segoe UI", 10), text_color=GREY_TEXT)
        self.count_lbl.grid(row=0, column=3, sticky="e")

        # Listbox for added shipping bills
        list_wrap = ctk.CTkFrame(card, fg_color=DARK_BG, corner_radius=6,
                                  border_color=GOLD_DARK, border_width=1)
        list_wrap.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.files_list = tk.Listbox(list_wrap, height=6, bg=DARK_BG, fg=GOLD_SHINE,
                                     selectmode="extended", activestyle="none",
                                     font=("Consolas", 9), bd=0, highlightthickness=0,
                                     selectbackground=GOLD_DARK)
        self.files_list.pack(fill="x", padx=6, pady=6)

        # Output Excel file
        out_row = ctk.CTkFrame(card, fg_color="transparent")
        out_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        out_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(out_row, text="💾  Save Excel As", font=("Segoe UI", 11),
                     text_color=GREY_TEXT).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkEntry(out_row, textvariable=self.output_file, height=36,
                     fg_color=DARK_BG, border_color=GOLD_DARK,
                     text_color=WHITE).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(out_row, text="Browse", width=80, height=36,
                      fg_color=GOLD_DARK, hover_color=GOLD_MID, text_color=WHITE,
                      command=self._browse_output).grid(row=0, column=2)

        # ── Process button ───────────────────────────────────────────────────────
        self.run_btn = ctk.CTkButton(
            self, text="▶  Process Shipping Bills",
            height=48, corner_radius=8,
            fg_color=GOLD_MID, hover_color=GOLD_DARK,
            text_color=DARK_BG, font=("Segoe UI", 13, "bold"),
            command=self._start, state="disabled"
        )
        self.run_btn.grid(row=4, column=0, padx=30, pady=(0, 10), sticky="ew")

        # ── Progress bar ──────────────────────────────────────────────────────
        self.progress = ctk.CTkProgressBar(self, fg_color=CARD_BG,
                                           progress_color=GOLD_MID, height=8)
        self.progress.set(0)
        self.progress.grid(row=5, column=0, padx=30, sticky="ew")

        self.status_lbl = ctk.CTkLabel(self, text="Pehle shipping bill PDF add karo.",
                                       font=("Segoe UI", 10), text_color=GREY_TEXT)
        self.status_lbl.grid(row=6, column=0, pady=(4, 0))

        # ── Log box ───────────────────────────────────────────────────────────
        self.log_box = ctk.CTkTextbox(self, height=180, fg_color=CARD_BG,
                                      text_color=GOLD_SHINE,
                                      font=("Consolas", 10), border_color=GOLD_DARK,
                                      border_width=1, corner_radius=6)
        self.log_box.grid(row=7, column=0, padx=30, pady=(10, 20), sticky="ew")
        self.log_box.configure(state="disabled")

    # ── System monitor ──────────────────────────────────────────────────────
    def _update_gauges(self):
        if not self._monitoring:
            return
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
            else:
                cpu = ram = 0
            self.cpu_gauge.set_value(cpu)
            self.ram_gauge.set_value(ram)
            self.after(1200, self._update_gauges)
        except Exception:
            pass

    def _tick(self):
        now = datetime.now()
        self.dt_bar.configure(
            text=f"{now.strftime('%A')}  {now.strftime('%d %b %Y')}  {now.strftime('%I:%M:%S %p')}"
        )
        self.after(1000, self._tick)

    # ── Shipping bill add / remove ─────────────────────────────────────────
    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Shipping Bill PDF(s) select karo",
            filetypes=[("PDF files", "*.pdf")])
        if not paths:
            return
        added = 0
        for p in paths:
            if p not in self.bill_files:
                self.bill_files.append(p)
                self.files_list.insert("end", os.path.basename(p))
                added += 1
        if added and not self.output_file.get().strip():
            default_dir = os.path.dirname(self.bill_files[0])
            self.output_file.set(os.path.join(default_dir, "shipping_bills_output.xlsx"))
        self._refresh_count()

    def _remove_selected(self):
        sel = list(self.files_list.curselection())
        for i in reversed(sel):
            self.files_list.delete(i)
            del self.bill_files[i]
        self._refresh_count()

    def _clear_files(self):
        self.files_list.delete(0, "end")
        self.bill_files.clear()
        self._refresh_count()

    def _refresh_count(self):
        n = len(self.bill_files)
        self.count_lbl.configure(text=f"{n} shipping bill(s) added")
        self.run_btn.configure(state=("normal" if n > 0 else "disabled"))
        self.status_lbl.configure(
            text="Process button dabao." if n > 0 else "Pehle shipping bill PDF add karo.")

    def _browse_output(self):
        f = filedialog.asksaveasfilename(
            title="Output Excel file", defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if f:
            self.output_file.set(f)

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Processing ───────────────────────────────────────────────────────────
    def _start(self):
        if self.running:
            return
        if not self.bill_files:
            messagebox.showerror("Error", "Pehle shipping bill PDF add karo.")
            return
        output = self.output_file.get().strip()
        if not output:
            messagebox.showerror("Error", "Output Excel file path enter karo.")
            return
        self.running = True
        self.run_btn.configure(state="disabled", text="⏳  Processing…")
        self.log_box.configure(state="normal"); self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        threading.Thread(target=self._run_extraction,
                         args=(list(self.bill_files), output), daemon=True).start()

    def _run_extraction(self, pdf_files, output):
        all_rows = []
        errors = []
        n = len(pdf_files)
        for i, pdf_path in enumerate(pdf_files):
            fname = os.path.basename(pdf_path)
            self.after(0, lambda f=fname: self.status_lbl.configure(text=f"Processing: {f}"))
            self.after(0, lambda p=(i/n): self.progress.set(p))
            try:
                rows, method = parse_bill(pdf_path)
                all_rows.extend(rows)
                self.after(0, lambda f=fname, r=len(rows), m=method:
                           self._log(f"✅ {f}  →  {r} row(s) [{m}]"))
            except Exception as e:
                errors.append((fname, str(e)))
                self.after(0, lambda f=fname, err=str(e): self._log(f"❌ {f}: {err}"))

        if not all_rows:
            self.after(0, lambda: self._done(False, "Koi data extract nahi hua.", 0, errors))
            return

        df = pd.DataFrame(all_rows)
        ordered = [c for c in COLUMNS if c in df.columns]
        df = df[ordered]
        build_excel(df.to_dict("records"), output)

        record_run(len(pdf_files), len(df), output)

        self.after(0, lambda: self.progress.set(1.0))
        msg = f"Done! {len(df)} rows  |  Excel saved: {output}"
        self.after(0, lambda: self._done(True, msg, len(df), errors))

    def _done(self, success, msg, rows=0, errors=None):
        self.running = False
        self.run_btn.configure(state="normal", text="▶  Process Shipping Bills")
        self.status_lbl.configure(
            text=msg,
            text_color=GREEN_OK if success else RED_ERR
        )
        if success:
            self._log(f"\n{'═'*50}")
            self._log(f"✅ DONE!  Total rows: {rows}")
            if errors:
                self._log(f"⚠  {len(errors)} file(s) mein error:")
                for f, e in errors:
                    self._log(f"   {f}: {e}")
            self._log(f"{'═'*50}")
            messagebox.showinfo("Extraction Complete! ✅", msg)
        else:
            self._log(f"❌ {msg}")
            messagebox.showerror("Error", msg)

    def _back_to_dashboard(self):
        self._monitoring = False
        self.master._show_dashboard(self.username)

    def _logout(self):
        self._monitoring = False
        self.master._show_login()

# ══════════════════════════════════════════════════════════════════════════════
#  ROOT APP CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RDx Solution — CSB-V Extractor")
        self.geometry("860x620")
        self.minsize(760, 560)
        self.configure(fg_color=DARK_BG)

        # Taskbar icon (logo)
        try:
            icon = load_logo(size=(32, 32))
            if icon:
                self.iconphoto(True, icon)
        except Exception:
            pass

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._current_frame = None

        # Splash (non-blocking) → Login
        self._show_splash()

    def _show_splash(self):
        self._clear()
        self.geometry("860x560")
        frame = SplashScreen(self, on_done=self._show_login)
        frame.grid(row=0, column=0, sticky="nsew")
        self._current_frame = frame

    def _clear(self):
        if self._current_frame:
            self._current_frame.destroy()

    def _show_login(self):
        self._clear()
        self.geometry("860x560")
        frame = LoginPage(self, on_login_success=self._show_dashboard)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(1, weight=1)
        self._current_frame = frame

    def _show_dashboard(self, username):
        self._clear()
        self.geometry("900x700")
        frame = Dashboard(self, username, on_open_processing=self._show_extractor)
        frame.grid(row=0, column=0, sticky="nsew")
        self._current_frame = frame

    def _show_extractor(self, username):
        self._clear()
        self.geometry("900x780")
        frame = ExtractorWindow(self, username)
        frame.grid(row=0, column=0, sticky="nsew")
        self._current_frame = frame

# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
