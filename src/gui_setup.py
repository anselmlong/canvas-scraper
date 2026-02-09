import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import sys

from config import Config
from canvas_client import CanvasClient
from course_manager import CourseManager


class SetupGUI:
    def __init__(self, config: Config):
        self.config = config
        self.root = tk.Tk()
        self.root.title(f"Canvas Scraper Setup")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        self.style = ttk.Style()
        self.style.configure("TLabel", padding=5)
        self.style.configure("TButton", padding=5)

        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.current_step = 1
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header_label = ttk.Label(
            self.main_frame,
            text="Canvas Scraper Setup Wizard",
            font=("Helvetica", 16, "bold"),
        )
        self.header_label.pack(pady=(0, 20))

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.footer_frame = ttk.Frame(self.main_frame)
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(20, 0))

        self.next_button = ttk.Button(
            self.footer_frame, text="Next", command=self.next_step
        )
        self.next_button.pack(side=tk.RIGHT)

        self.show_step_1()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_step_1(self):
        self.clear_content()
        self.header_label.config(text="Step 1: Canvas Settings")

        ttk.Label(self.content_frame, text="Canvas Base URL:").pack(anchor=tk.W)
        self.url_entry = ttk.Entry(self.content_frame, width=50)
        self.url_entry.insert(
            0, self.config.get("canvas.base_url") or "https://canvas.nus.edu.sg/"
        )
        self.url_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(self.content_frame, text="Canvas API Token:").pack(anchor=tk.W)
        self.token_entry = ttk.Entry(self.content_frame, width=50, show="*")
        self.token_entry.insert(0, self.config.canvas_api_token or "")
        self.token_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            self.content_frame,
            text="Tip: Find your token in Canvas under Account > Settings > New Access Token",
            font=("Helvetica", 8, "italic"),
        ).pack(anchor=tk.W)

    def show_step_2(self):
        self.clear_content()
        self.header_label.config(text="Step 2: Download Location")

        ttk.Label(self.content_frame, text="Where should files be saved?").pack(
            anchor=tk.W
        )

        path_frame = ttk.Frame(self.content_frame)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        self.path_entry = ttk.Entry(path_frame)
        self.path_entry.insert(0, str(self.config.download_path))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Browse...", command=self.browse_folder).pack(
            side=tk.RIGHT, padx=(5, 0)
        )

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def show_step_3(self):
        self.clear_content()
        self.header_label.config(text="Step 3: Course Selection")

        ttk.Label(self.content_frame, text="Checking courses... please wait.").pack(
            pady=20
        )
        self.next_button.config(state=tk.DISABLED)

        # Run course fetching in a thread to keep GUI responsive
        threading.Thread(target=self.fetch_courses, daemon=True).start()

    def fetch_courses(self):
        try:
            client = CanvasClient(self.url_entry.get(), self.token_entry.get())
            mgr = CourseManager(client, self.config)
            self.courses = mgr.get_active_courses()
            self.root.after(0, self.display_courses)
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Error", f"Failed to fetch courses: {e}"),
            )
            self.root.after(0, lambda: self.show_step_1())

    def display_courses(self):
        self.clear_content()
        self.next_button.config(state=tk.NORMAL)
        self.next_button.config(text="Finish")

        ttk.Label(self.content_frame, text="Select courses to sync:").pack(anchor=tk.W)

        # Use a canvas for scrolling if many courses
        canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(
            self.content_frame, orient="vertical", command=canvas.yview
        )
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.course_vars = {}
        whitelist = self.config.get("courses.whitelist", [])

        for course in self.courses:
            var = tk.BooleanVar(value=course["id"] in whitelist)
            self.course_vars[course["id"]] = var
            ttk.Checkbutton(
                scroll_frame, text=f"[{course['code']}] {course['name']}", variable=var
            ).pack(anchor=tk.W)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def next_step(self):
        if self.current_step == 1:
            url = self.url_entry.get().strip()
            token = self.token_entry.get().strip()
            if not url or not token:
                messagebox.showwarning("Required", "Please enter both URL and Token.")
                return
            self.config.set("canvas.base_url", url)
            self.config.set_env("CANVAS_API_TOKEN", token)
            self.current_step = 2
            self.show_step_2()
        elif self.current_step == 2:
            path = self.path_entry.get().strip()
            if not path:
                messagebox.showwarning("Required", "Please select a download folder.")
                return
            self.config.set("download.base_path", path)
            self.current_step = 3
            self.show_step_3()
        elif self.current_step == 3:
            selected_ids = [cid for cid, var in self.course_vars.items() if var.get()]
            if not selected_ids:
                if not messagebox.askyesno(
                    "Confirm", "No courses selected. Proceed anyway?"
                ):
                    return

            self.config.set("courses.whitelist", selected_ids)
            self.config.save()
            messagebox.showinfo("Done", "Setup complete! You can now run the sync.")
            self.root.destroy()


def run_gui_setup(config: Config):
    app = SetupGUI(config)
    app.root.mainloop()


if __name__ == "__main__":
    # Test
    c = Config()
    run_gui_setup(c)
