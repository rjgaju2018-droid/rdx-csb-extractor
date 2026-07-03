import tkinter as tk
import customtkinter as ctk
from typing import List
from auth.supabase_client import supabase


class AdminPanel(ctk.CTkToplevel):
    def __init__(self, parent, current_user_id: str):
        super().__init__(parent)
        self.title("Admin Panel — RDX Solution")
        self.geometry("900x560")
        self.configure(fg_color="#121212")
        self.current_user_id = current_user_id
        self._build()
        self._load_users()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="#1E1E1E")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Admin Panel", font=("Segoe UI", 18, "bold"), text_color="#F5D97A").grid(row=0, column=0, sticky="w", padx=12, pady=12)
        ctk.CTkLabel(header, text="Overview of registered users and their usage.", font=("Segoe UI", 11), text_color="#CFCFCF").grid(row=1, column=0, sticky="w", padx=12)

        self.list_frame = ctk.CTkFrame(self, fg_color="#1B1B1B", border_color="#3A3A3A", border_width=1)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.grid_rowconfigure(0, weight=1)

        headings = ["Email", "Role", "Signup Date", "Last Login", "Usage Count"]
        heading_row = ctk.CTkFrame(self.list_frame, fg_color="#2A2A2A")
        heading_row.grid(row=0, column=0, sticky="ew")
        for idx, text in enumerate(headings):
            ctk.CTkLabel(heading_row, text=text, font=("Segoe UI", 10, "bold"), text_color="#E8E8E8").grid(row=0, column=idx, sticky="ew", padx=8, pady=10)
            heading_row.grid_columnconfigure(idx, weight=1)

        self.scroll_canvas = tk.Canvas(self.list_frame, bg="#1B1B1B", highlightthickness=0)
        self.scroll_canvas.grid(row=1, column=0, sticky="nsew")
        self.scrollbar = tk.Scrollbar(self.list_frame, orient="vertical", command=self.scroll_canvas.yview)
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="#1B1B1B")
        self.scroll_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_frame.bind("<Configure>", lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))

    def _load_users(self):
        try:
            response = supabase.from_("profiles").select("id, email, role, created_at, last_sign_in_at").execute()
            users = response.data if response and getattr(response, "data", None) else []
        except Exception:
            users = []

        for index, row in enumerate(users, start=1):
            usage_count = self._fetch_usage_count(row.get("id"))
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="#252525", corner_radius=8)
            row_frame.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=1)
            row_frame.grid_columnconfigure(3, weight=1)
            row_frame.grid_columnconfigure(4, weight=1)

            ctk.CTkLabel(row_frame, text=row.get("email") or "—", text_color="#FFFFFF", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=10)
            ctk.CTkLabel(row_frame, text=row.get("role") or "user", text_color="#CFCFCF", font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=10)
            ctk.CTkLabel(row_frame, text=row.get("created_at") or "—", text_color="#CFCFCF", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w", padx=10)
            ctk.CTkLabel(row_frame, text=row.get("last_sign_in_at") or "—", text_color="#CFCFCF", font=("Segoe UI", 10)).grid(row=0, column=3, sticky="w", padx=10)
            ctk.CTkLabel(row_frame, text=str(usage_count), text_color="#E8E8E8", font=("Segoe UI", 10)).grid(row=0, column=4, sticky="w", padx=10)

    def _fetch_usage_count(self, user_id: str) -> int:
        if not user_id:
            return 0
        try:
            resp = supabase.from_("usage_logs").select("id", count="exact").eq("user_id", user_id).execute()
            if resp and getattr(resp, "count", None) is not None:
                return resp.count
        except Exception:
            pass
        return 0
