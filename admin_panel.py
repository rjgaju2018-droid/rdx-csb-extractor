"""
Functional Admin Panel to view users and usage logs from Supabase.
"""
import tkinter
import customtkinter as ctk
from .auth.supabase_client import supabase
from .auth.user_roles import set_admin_status

def get_all_users():
    """Fetches all user profiles from the 'profiles' table."""
    try:
        res = supabase.table("profiles").select("id, username, is_admin, updated_at").order("updated_at", desc=True).execute()
        return res.data, None
    except Exception as e:
        return [], f"Error fetching users: {e}"

def get_usage_logs(page=1, page_size=50):
    """Fetches a paginated list of logs from the 'usage_logs' table."""
    try:
        # Calculate the range for pagination (0-indexed)
        from_idx = (page - 1) * page_size
        to_idx = from_idx + page_size - 1
        # The RLS policy allows admins to see all logs.
        # We fetch the data for the page and the total count in one query.
        # The 'count' parameter with 'exact' ensures we get the total number of rows
        # matching the query, ignoring the range limit.
        res = supabase.table("usage_logs").select("created_at, user_id, action", count='exact').order("created_at", desc=True).range(from_idx, to_idx).execute()
        return res.data, res.count, None
    except Exception as e:
        return [], 0, f"Error fetching logs: {e}"

class AdminPanel(ctk.CTkToplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.current_user_id = user_id  # Store the current admin's ID
        self.title("Admin Panel")
        self.geometry("700x550")
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Data Storage ---
        # Pagination state for logs
        self.log_page = 1
        self.log_page_size = 50

        # Initial data fetch for both tabs
        # Note: self.all_logs will only contain the first page of logs

        self.all_users, self.users_error = get_all_users()
        self.all_logs, self.total_logs, self.logs_error = get_usage_logs(page=self.log_page, page_size=self.log_page_size)

        self.user_widgets = []

        # Theme colors from rdx_csb_app.py
        DARK_BG = "#1A1510"
        CARD_BG = "#211C14"
        GOLD_LIGHT = "#E8C44A"
        GREY_TEXT = "#A09070"
        CREAM = "#F0EBE0"

        self.configure(fg_color=DARK_BG)

        ctk.CTkLabel(self, text="Administrator Dashboard", font=("Georgia", 18, "bold"), text_color=GOLD_LIGHT).grid(row=0, column=0, pady=(15, 10))

        self.tab_view = ctk.CTkTabview(self, fg_color=CARD_BG)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.tab_view.add("Users")
        self.tab_view.add("Usage Logs")

        # Users Tab
        users_tab = self.tab_view.tab("Users")
        users_tab.grid_columnconfigure(0, weight=1)
        users_tab.grid_rowconfigure(1, weight=1)
        
        user_search_frame = ctk.CTkFrame(users_tab, fg_color="transparent")
        user_search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(user_search_frame, text="🔎 Search Users:", font=("Segoe UI", 10), text_color=GREY_TEXT).pack(side="left")
        self.user_search_var = tkinter.StringVar()
        self.user_search_var.trace_add("write", lambda *args: self._render_users(self.user_search_var.get()))
        ctk.CTkEntry(user_search_frame, textvariable=self.user_search_var, fg_color=DARK_BG, border_color=GOLD_LIGHT, text_color=CREAM).pack(side="left", padx=8, fill="x", expand=True)

        self.users_frame = ctk.CTkScrollableFrame(users_tab, fg_color="transparent")
        self.users_frame.grid(row=1, column=0, sticky="nsew")
        self._render_users()

        # Usage Logs Tab
        logs_tab = self.tab_view.tab("Usage Logs")
        logs_tab.grid_columnconfigure(0, weight=1)
        logs_tab.grid_rowconfigure(1, weight=1) # Row for the scrollable frame

        log_search_frame = ctk.CTkFrame(logs_tab, fg_color="transparent")
        log_search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(log_search_frame, text="🔎 Search Logs:", font=("Segoe UI", 10), text_color=GREY_TEXT).pack(side="left")
        self.log_search_var = tkinter.StringVar()
        self.log_search_var.trace_add("write", lambda *args: self._render_logs(self.log_search_var.get()))
        ctk.CTkEntry(log_search_frame, textvariable=self.log_search_var, fg_color=DARK_BG, border_color=GOLD_LIGHT, text_color=CREAM).pack(side="left", padx=8, fill="x", expand=True)

        self.logs_frame = ctk.CTkScrollableFrame(logs_tab, fg_color="transparent")
        self.logs_frame.grid(row=1, column=0, sticky="nsew")
        self._render_logs()
        # Initial call to update pagination controls after rendering logs
        self._update_log_pagination_controls()

        # Log Pagination Controls
        log_pagination_frame = ctk.CTkFrame(logs_tab, fg_color="transparent")
        log_pagination_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        log_pagination_frame.grid_columnconfigure(1, weight=1)
        self.prev_log_btn = ctk.CTkButton(log_pagination_frame, text="< Previous", command=self._prev_log_page, width=100, fg_color="#3A2E20", text_color="#F0EBE0", hover_color="#8B6914")
        self.prev_log_btn.grid(row=0, column=0)
        self.log_page_label = ctk.CTkLabel(log_pagination_frame, text="", text_color=GREY_TEXT, font=("Segoe UI", 10))
        self.log_page_label.grid(row=0, column=1)
        self.next_log_btn = ctk.CTkButton(log_pagination_frame, text="Next >", command=self._next_log_page, width=100, fg_color="#3A2E20", text_color="#F0EBE0", hover_color="#8B6914")
        self.next_log_btn.grid(row=0, column=2)

        # Add a refresh button
        ctk.CTkButton(self, text="Refresh", command=self.refresh_data).grid(row=2, column=0, pady=(0, 15))

    def _render_users(self, query=""):
        """Clears and re-renders the user list based on a search query."""
        for widget in self.users_frame.winfo_children():
            widget.destroy()

        if self.users_error:
            ctk.CTkLabel(self.users_frame, text=self.users_error, text_color="red").pack(pady=10)
            return
        
        filtered_users = [
            u for u in self.all_users 
            if not query or query.lower() in u.get('username', '').lower() or query.lower() in u.get('id', '').lower()
        ]

        if not filtered_users:
            ctk.CTkLabel(self.users_frame, text="No matching users found.", text_color="#A09070").pack(pady=10)
            return

        for user in filtered_users:
            user_frame = ctk.CTkFrame(self.users_frame, fg_color="transparent")
            user_frame.pack(fill="x", padx=10, pady=5)
            user_frame.grid_columnconfigure(0, weight=1)

            user_text = f"👤 {user.get('username', 'N/A')}"
            ctk.CTkLabel(user_frame, text=user_text, justify="left", anchor="w", text_color="#F0EBE0", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w")

            is_admin_var = tkinter.BooleanVar(value=user.get("is_admin", False))
            admin_switch = ctk.CTkSwitch(
                user_frame, text="Admin", variable=is_admin_var,
                command=lambda uid=user.get('id'), var=is_admin_var: self.toggle_admin(uid, var.get()),
                fg_color="#A09070", progress_color="#E8C44A"
            )
            admin_switch.grid(row=0, column=1, padx=10)

            if user.get('id') == self.current_user_id:
                admin_switch.configure(state="disabled")

    def _render_logs(self, query=""):
        """Clears and re-renders the log list based on a search query."""
        for widget in self.logs_frame.winfo_children():
            widget.destroy()

        if self.logs_error:
            ctk.CTkLabel(self.logs_frame, text=self.logs_error, text_color="red").pack(pady=10)
            return

        filtered_logs = [
            l for l in self.all_logs
            if not query or query.lower() in l.get('action', '').lower() or query.lower() in l.get('user_id', '').lower()
        ]

        # Update pagination controls based on the current page's data
        self._update_log_pagination_controls()

        if not filtered_logs:
            ctk.CTkLabel(self.logs_frame, text="No matching logs found.", text_color="#A09070").pack(pady=10) # Using GREY_TEXT
            return

        for log in filtered_logs:
            ts = log.get('created_at', ' ').replace("T", " ").split('.')[0]
            log_text = f"🕒 {ts} | {log.get('action', 'N/A')}\n   User: {log.get('user_id')}"
            ctk.CTkLabel(self.logs_frame, text=log_text, justify="left", anchor="w", text_color="#F0EBE0", font=("Consolas", 10)).pack(anchor="w", padx=10, pady=4)

    def refresh_data(self):
        """Destroys and recreates the window to refresh data."""
        self.destroy()
        # The parent of the Toplevel is the main App window, not the Dashboard frame, so pass self.master
        AdminPanel(self.master, self.current_user_id)

    def toggle_admin(self, user_id, new_status):
        """Callback for the admin switch."""
        success, error = set_admin_status(user_id, new_status)
        if not success:
            tkinter.messagebox.showerror("Update Failed", f"Could not update admin status for user {user_id}.\n\nError: {error}", parent=self)
            # Revert the switch visually on failure
            self.refresh_data()

    def _update_log_pagination_controls(self):
        """Enables/disables log pagination buttons and updates the page label."""
        # Calculate total pages based on the total count from Supabase
        # Handle case where total_logs is 0 to avoid division by zero or incorrect page count
        total_pages = (self.total_logs + self.log_page_size - 1) // self.log_page_size if self.total_logs > 0 else 1
        self.log_page_label.configure(text=f"Page {self.log_page} of {max(1, total_pages)}") # Ensure at least "Page 1 of 1"

        # Disable 'Previous' button if on the first page
        if self.log_page <= 1:
            # Ensure log_page doesn't go below 1 if user clicks 'Previous' when already on page 1
            self.log_page = 1 # Ensure page doesn't go below 1
            self.prev_log_btn.configure(state="disabled")
        else:
            self.prev_log_btn.configure(state="normal")

        if self.log_page >= total_pages:
            self.next_log_btn.configure(state="disabled")
            self.log_page = total_pages # Ensure log_page doesn't exceed total_pages
        else:
            self.next_log_btn.configure(state="normal")

    def _fetch_and_render_logs(self):
        self.all_logs, self.total_logs, self.logs_error = get_usage_logs(page=self.log_page, page_size=self.log_page_size)
        self._render_logs(self.log_search_var.get())

    def _next_log_page(self):
        """Moves to the next page of logs, if available."""
        self.log_page += 1
        self._fetch_and_render_logs()

    def _prev_log_page(self):
        """Moves to the previous page of logs, if available."""
        self.log_page -= 1
        self._fetch_and_render_logs()