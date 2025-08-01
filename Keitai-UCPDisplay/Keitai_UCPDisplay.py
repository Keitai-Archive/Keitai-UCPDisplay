import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import zipfile
import io
import os
import sys
import argparse

class UCPViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UCP Image Viewer")
        self.geometry("800x600")

        # Menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open UCP File", command=self.open_ucp)
        filemenu.add_command(label="Open Folder (-F)", command=lambda: self.open_ucp_folder(filedialog.askdirectory()))
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        # Frames
        self.left_frame = ttk.Frame(self, width=300)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)
        self.right_frame = ttk.Frame(self)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Listbox with scrollbar
        self.listbox = tk.Listbox(self.left_frame, width=40)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Context menu for copy
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected)
        self.listbox.bind("<Button-3>", self.show_context_menu)

        # Image display
        self.image_label = ttk.Label(self.right_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # Data structures
        self.entries = []  # list of (zip_obj, image_name, display_name)
        self.image_cache = {}

    def populate_listbox(self):
        self.listbox.delete(0, tk.END)
        for _, _, display in self.entries:
            self.listbox.insert(tk.END, display)
        if self.entries:
            self.listbox.selection_set(0)
            self.on_select(None)

    def open_ucp(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Open UCP File",
                filetypes=[("UCP Files", "*.ucp"), ("All Files", "*.*")]
            )
        if not file_path:
            return
        try:
            zip_obj = zipfile.ZipFile(file_path, 'r')
        except zipfile.BadZipFile:
            messagebox.showerror("Invalid File", "Selected file is not a valid UCP archive.")
            return
        img_exts = ('.jpg', '.jpeg', '.gif', '.png')
        self.entries = []
        base = os.path.basename(file_path)
        for name in zip_obj.namelist():
            if name.lower().endswith(img_exts):
                display_name = f"{base}::{name}"
                self.entries.append((zip_obj, name, display_name))
        self.populate_listbox()

    def open_ucp_folder(self, folder_path):
        if not folder_path or not os.path.isdir(folder_path):
            return
        archives = []
        for root, _, files in os.walk(folder_path):
            for fname in files:
                if fname.lower().endswith('.ucp'):
                    archives.append(os.path.join(root, fname))
        if not archives:
            messagebox.showinfo("No UCP Files", "No UCP files found in the specified folder.")
            return
        img_exts = ('.jpg', '.jpeg', '.gif', '.png')
        self.entries = []
        for path in archives:
            try:
                zip_obj = zipfile.ZipFile(path, 'r')
            except zipfile.BadZipFile:
                continue
            base = os.path.basename(path)
            for name in zip_obj.namelist():
                if name.lower().endswith(img_exts):
                    display_name = f"{base}::{name}"
                    self.entries.append((zip_obj, name, display_name))
        self.populate_listbox()

    def on_select(self, event):
        if not self.entries:
            return
        idx = self.listbox.curselection()
        if not idx:
            return
        zip_obj, name, _ = self.entries[idx[0]]
        cache_key = (id(zip_obj), name)
        if cache_key in self.image_cache:
            photo = self.image_cache[cache_key]
        else:
            with zip_obj.open(name) as f:
                data = f.read()
            pil_img = Image.open(io.BytesIO(data))
            new_w, new_h = self.get_display_size(pil_img)
            new_w = max(1, new_w)
            new_h = max(1, new_h)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            self.image_cache[cache_key] = photo
        self.image_label.config(image=photo)
        self.image_label.image = photo

    def get_display_size(self, pil_img):
        max_w = self.right_frame.winfo_width() or 400
        max_h = self.right_frame.winfo_height() or 400
        w, h = pil_img.size
        ratio = min(max_w / w, max_h / h, 1)
        return int(w * ratio), int(h * ratio)

    def show_context_menu(self, event):
        # Select the item under cursor
        idx = self.listbox.nearest(event.y)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return
        text = self.listbox.get(idx[0])
        self.clipboard_clear()
        self.clipboard_append(text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCP Image Viewer")
    parser.add_argument("-F", "--folder", help="Recursively load all UCP files in a folder", metavar="FOLDER")
    parser.add_argument("file", nargs="?", help="Single UCP file to open")
    args = parser.parse_args()

    app = UCPViewer()
    if args.folder:
        app.open_ucp_folder(args.folder)
    elif args.file:
        app.open_ucp(args.file)
    app.mainloop()

