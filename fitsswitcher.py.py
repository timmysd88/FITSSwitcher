import os
import shutil
import glob
import json
import tkinter as tk
import customtkinter as ctk
import sys
from tkinter import filedialog, messagebox
from astropy.io import fits
from datetime import datetime, timedelta
from PIL import Image

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")

planned_moves = []
PRESETS_FILE = os.path.join(os.path.expanduser("~"), "FITSSwitcher_presets.json")

# --- Preset Management ---
default_presets = {
    "PixInsight (WBPP)": ["Target", "Date", "Filter", "Type"],
    "Siril (Scripts)": ["Target", "Type", "None", "None"],
    "Astro Pixel Processor (APP)": ["Target", "Filter", "Type", "None"],
    "Comprehensive Mono": ["Target", "Filter", "Date", "Type"]
}

user_presets = {}
if os.path.exists(PRESETS_FILE):
    try:
        with open(PRESETS_FILE, "r") as f:
            user_presets = json.load(f)
    except Exception:
        pass

class DynamicToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)
        
        self.descriptions = {
            "Target": "Reads 'OBJECT' from the FITS header.\nExamples: M31, Pacman Nebula.",
            "Date": "Reads 'DATE-OBS'.\nUses a -12h offset so late-night sessions\n(e.g., 2 AM) group into the previous day.",
            "Filter": "Reads 'FILTER' from the FITS header.\nExamples: Ha, OIII, L, No_Filter.",
            "Type": "Reads 'IMAGETYP'.\nSeparates Light, Flat, Dark, and Bias frames.",
            "None": "Skips creating a folder for this level."
        }

    def show_tip(self, event=None):
        current_val = self.widget.get()
        text = self.descriptions.get(current_val, "")
        if not text: 
            return
        
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tip_window, text=text, justify="left",
                         background="#2b2b2b", foreground="#ffffff", 
                         relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack(ipadx=8, ipady=5)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

def browse_source():
    folder = filedialog.askdirectory(title="Select Incoming FITS Folder")
    if folder:
        source_var.set(folder)
        generate_preview()

def browse_dest():
    folder = filedialog.askdirectory(title="Select Destination Folder")
    if folder:
        dest_var.set(folder)
        generate_preview()

def browse_counter_source():
    folder = filedialog.askdirectory(title="Select Folder to Count")
    if folder:
        counter_source_var.set(folder)

def get_astronomical_date(date_str):
    if not date_str:
        return "Unknown_Date"
    try:
        clean_date_str = date_str.split('.')[0]
        obs_dt = datetime.strptime(clean_date_str, "%Y-%m-%dT%H:%M:%S")
        logical_night = obs_dt - timedelta(hours=12)
        return logical_night.strftime("%Y-%m-%d")
    except Exception:
        return "Unknown_Date"

def apply_preset(choice):
    all_presets = {**default_presets, **user_presets}
    if choice in all_presets:
        layout = all_presets[choice]
        cb1.set(layout[0])
        cb2.set(layout[1])
        cb3.set(layout[2])
        cb4.set(layout[3])
    generate_preview()

def save_custom_preset():
    dialog = ctk.CTkInputDialog(text="Enter a name for your custom layout:", title="Save Preset")
    preset_name = dialog.get_input()
    
    if preset_name:
        if preset_name in default_presets or preset_name == "Custom":
            messagebox.showerror("Error", "Cannot overwrite default presets. Choose a different name.")
            return
            
        current_layout = [cb1.get(), cb2.get(), cb3.get(), cb4.get()]
        user_presets[preset_name] = current_layout
        
        try:
            with open(PRESETS_FILE, "w") as f:
                json.dump(user_presets, f)
            
            updated_options = ["Custom"] + list(default_presets.keys()) + list(user_presets.keys())
            preset_cb.configure(values=updated_options)
            preset_var.set(preset_name)
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")

def on_manual_structure_change(*args):
    preset_var.set("Custom")
    generate_preview()

def generate_preview(*args):
    preview_box.delete("0.0", "end")
    planned_moves.clear()
    sort_btn.configure(state="disabled", fg_color="gray")

    source_dir = source_var.get()
    dest_dir = dest_var.get()
    
    order_selections = [cb1.get(), cb2.get(), cb3.get(), cb4.get()]
    valid_keys = [k for k in order_selections if k != "None"]
    
    if len(set(valid_keys)) < len(valid_keys):
        preview_box.insert("end", "Error: Duplicate folder levels selected. Please adjust dropdowns.\n")
        return
    
    if not valid_keys:
        preview_box.insert("end", "Error: You must select at least one folder level.\n")
        return

    if not source_dir or not dest_dir:
        preview_box.insert("end", "Waiting for both folders to be selected...\n")
        return

    preview_box.insert("end", "Scanning FITS files recursively, please wait...\n")
    window.update()

    search_pattern = os.path.join(source_dir, "**", "*.fit*")
    files = glob.glob(search_pattern, recursive=True)

    if not files:
        preview_box.delete("0.0", "end")
        preview_box.insert("end", "No FITS files found in the incoming folder.\n")
        return

    folder_structure = {}

    for file_path in files:
        try:
            with fits.open(file_path) as hdul:
                header = hdul[0].header
                raw_target = header.get('OBJECT', 'Unknown_Target').strip()
                raw_filter = header.get('FILTER', 'No_Filter').strip()
                date_obs = header.get('DATE-OBS', '').strip()
                raw_type = header.get('IMAGETYP', 'Unknown_Type').strip()

            session_date = get_astronomical_date(date_obs)
            target = "".join(c for c in raw_target if c.isalnum() or c in (' ', '_', '-'))
            filter_name = "".join(c for c in raw_filter if c.isalnum() or c in (' ', '_', '-'))
            image_type = "".join(c for c in raw_type if c.isalnum() or c in (' ', '_', '-'))

            if preset_var.get() == "Siril (Scripts)":
                if image_type.lower() == "light": image_type = "lights"
                elif image_type.lower() == "flat": image_type = "flats"
                elif image_type.lower() == "bias": image_type = "biases"
                elif image_type.lower() == "dark": image_type = "darks"

            data_map = {
                "Target": target, "Filter": filter_name,
                "Date": session_date, "Type": image_type
            }

            path_parts = [data_map[k] for k in valid_keys]
            dest_path = os.path.join(dest_dir, *path_parts)
            
            planned_moves.append({
                "source": file_path, "dest_dir": dest_path, "filename": os.path.basename(file_path)
            })

            current_level = folder_structure
            for part in path_parts[:-1]:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
            
            last_part = path_parts[-1]
            if last_part not in current_level:
                current_level[last_part] = 0
            current_level[last_part] += 1

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    preview_box.delete("0.0", "end")
    preview_box.insert("end", f"Found {len(planned_moves)} images to sort.\n")
    preview_box.insert("end", "The following structure will be generated:\n\n")

    def render_preview(d, indent=0):
        spacing = "    " * indent
        arrow = "↳ " if indent > 0 else ""
        for k, v in d.items():
            if isinstance(v, dict):
                preview_box.insert("end", f"{spacing}{arrow}📁 {k}\n")
                render_preview(v, indent + 1)
            else:
                preview_box.insert("end", f"{spacing}{arrow}📁 {k}  ({v} images)\n")

    render_preview(folder_structure)

    if planned_moves:
        sort_btn.configure(state="normal", fg_color="#2FA572")

def execute_sort():
    if not planned_moves:
        return

    moved_count = 0
    sort_btn.configure(state="disabled", fg_color="gray")
    preview_box.insert("end", "\nSorting files...\n")
    window.update()

    for move in planned_moves:
        try:
            os.makedirs(move["dest_dir"], exist_ok=True)
            new_path = os.path.join(move["dest_dir"], move["filename"])
            
            # Handle duplicates
            base, extension = os.path.splitext(new_path)
            counter = 1
            while os.path.exists(new_path):
                new_path = f"{base}_{counter}{extension}"
                counter += 1
                
            shutil.move(move["source"], new_path)
            moved_count += 1
        except Exception as e:
            print(f"Failed to move {move['filename']}: {e}")

    # Empty folder cleanup
    preview_box.insert("end", "Cleaning up empty folders...\n")
    window.update()
    source_dir = source_var.get()
    cleaned_count = 0
    for root, dirs, files in os.walk(source_dir, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                os.rmdir(dir_path)
                cleaned_count += 1
            except OSError:
                pass

    messagebox.showinfo("Success", f"Successfully sorted {moved_count} images!\nRemoved {cleaned_count} empty folders.")
    planned_moves.clear()
    preview_box.delete("0.0", "end")
    preview_box.insert("end", "Sort complete. Select a new incoming folder to sort more files.\n")

# --- Custom Sorting Function for LRGBSHO ---
def get_filter_priority(filter_name):
    f_upper = filter_name.upper()
    if f_upper in ['L', 'LUM', 'LUMINANCE']: return 1
    if f_upper in ['R', 'RED']: return 2
    if f_upper in ['G', 'GREEN']: return 3
    if f_upper in ['B', 'BLUE']: return 4
    if f_upper in ['SII', 'S2', 'S']: return 5
    if f_upper in ['HA', 'H-ALPHA', 'H']: return 6
    if f_upper in ['OIII', 'O3', 'O']: return 7
    return 99 # Pushes unrecognized/calibration filters to the bottom

# --- Standalone Counter Logic ---
def run_filter_count():
    folder = counter_source_var.get()
    if not folder:
        messagebox.showerror("Error", "Please select a folder to analyze first.")
        return

    counter_box.delete("0.0", "end")
    counter_box.insert("end", "Scanning files for filter counts...\n")
    window.update()

    search_pattern = os.path.join(folder, "**", "*.fit*")
    files = glob.glob(search_pattern, recursive=True)

    if not files:
        counter_box.delete("0.0", "end")
        counter_box.insert("end", "No FITS files found in this directory.")
        return

    stats = {}
    total_files = 0

    for file_path in files:
        try:
            with fits.open(file_path) as hdul:
                header = hdul[0].header
                target = header.get('OBJECT', 'Unknown_Target').strip()
                filt = header.get('FILTER', 'No_Filter').strip()
                img_type = header.get('IMAGETYP', 'Light').strip()

            total_files += 1
            
            # Group by Target -> Frame Type -> Filter
            if target not in stats:
                stats[target] = {}
            if img_type not in stats[target]:
                stats[target][img_type] = {}
            if filt not in stats[target][img_type]:
                stats[target][img_type][filt] = 0
                
            stats[target][img_type][filt] += 1
        except Exception:
            pass

    counter_box.delete("0.0", "end")
    counter_box.insert("end", f"Scan Complete! Analyzed {total_files} total files.\n\n")

    for target, types in stats.items():
        counter_box.insert("end", f"🎯 Target: {target}\n")
        for img_type, filters in types.items():
            counter_box.insert("end", f"    └─ Frame Type: {img_type}\n")
            
            # Sort filters using the LRGBSHO priority function, then alphabetically
            sorted_filters = sorted(filters.items(), key=lambda x: (get_filter_priority(x[0]), x[0]))
            
            for filt, count in sorted_filters:
                counter_box.insert("end", f"        └─ Filter [{filt}]: {count} exposures\n")
        counter_box.insert("end", "\n")

# --- Build the Modern User Interface ---
window = ctk.CTk()
window.title("FITSSwitcher")
window.geometry("650x900")

# Apply the custom .ico icon to the top left of the window
try:
    window.iconbitmap(resource_path("FSico.ico"))
except Exception:
    pass

# Initialize variables
source_var = ctk.StringVar()
dest_var = ctk.StringVar()
preset_var = ctk.StringVar(value="Custom")
counter_source_var = ctk.StringVar()

tabview = ctk.CTkTabview(window, width=610, height=650)
tabview.pack(padx=20, pady=10)

tab_sorter = tabview.add("FITS Sorter")
tab_counter = tabview.add("Filter Counter")

# ==================== TAB 1: SORTER ====================
ctk.CTkLabel(tab_sorter, text="1. Select Incoming FITS Folder:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
source_frame = ctk.CTkFrame(tab_sorter, fg_color="transparent")
source_frame.pack()
ctk.CTkEntry(source_frame, textvariable=source_var, width=330, state="readonly").pack(side="left", padx=5)
ctk.CTkButton(source_frame, text="Browse...", width=90, command=browse_source).pack(side="left")

ctk.CTkLabel(tab_sorter, text="2. Select Destination Folder:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
dest_frame = ctk.CTkFrame(tab_sorter, fg_color="transparent")
dest_frame.pack()
ctk.CTkEntry(dest_frame, textvariable=dest_var, width=330, state="readonly").pack(side="left", padx=5)
ctk.CTkButton(dest_frame, text="Browse...", width=90, command=browse_dest).pack(side="left")

ctk.CTkLabel(tab_sorter, text="3. Define Folder Structure:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(25, 5))

preset_frame = ctk.CTkFrame(tab_sorter, fg_color="transparent")
preset_frame.pack(pady=(0, 10))
initial_options = ["Custom"] + list(default_presets.keys()) + list(user_presets.keys())
preset_cb = ctk.CTkComboBox(preset_frame, values=initial_options, variable=preset_var, width=230, command=apply_preset)
preset_cb.pack(side="left", padx=5)
ctk.CTkButton(preset_frame, text="Save Setup", width=90, fg_color="#1f538d", command=save_custom_preset).pack(side="left", padx=5)

struct_frame = ctk.CTkFrame(tab_sorter, fg_color="transparent")
struct_frame.pack()

options = ["Target", "Date", "Filter", "Type", "None"]

cb1 = ctk.CTkComboBox(struct_frame, values=options, width=95, command=on_manual_structure_change)
cb1.set("Target")
cb1.pack(side="left", padx=3)
ctk.CTkLabel(struct_frame, text="/").pack(side="left")

cb2 = ctk.CTkComboBox(struct_frame, values=options, width=95, command=on_manual_structure_change)
cb2.set("Date")
cb2.pack(side="left", padx=3)
ctk.CTkLabel(struct_frame, text="/").pack(side="left")

cb3 = ctk.CTkComboBox(struct_frame, values=options, width=95, command=on_manual_structure_change)
cb3.set("Type")
cb3.pack(side="left", padx=3)
ctk.CTkLabel(struct_frame, text="/").pack(side="left")

cb4 = ctk.CTkComboBox(struct_frame, values=options, width=95, command=on_manual_structure_change)
cb4.set("None")
cb4.pack(side="left", padx=3)

DynamicToolTip(cb1)
DynamicToolTip(cb2)
DynamicToolTip(cb3)
DynamicToolTip(cb4)

ctk.CTkLabel(tab_sorter, text="4. Preview Generated Folders:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(25, 5))
preview_box = ctk.CTkTextbox(tab_sorter, width=540, height=170, font=ctk.CTkFont(family="Consolas", size=12))
preview_box.pack(padx=20, pady=5)
preview_box.insert("end", "Select folders to generate a preview...")

sort_btn = ctk.CTkButton(tab_sorter, text="Sort Images", command=execute_sort, width=180, height=35, 
                         font=ctk.CTkFont(size=14, weight="bold"), state="disabled", fg_color="gray")
sort_btn.pack(pady=15)

# ==================== TAB 2: COUNTER ====================
ctk.CTkLabel(tab_counter, text="Select Folder to Analyze:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
c_frame = ctk.CTkFrame(tab_counter, fg_color="transparent")
c_frame.pack()
ctk.CTkEntry(c_frame, textvariable=counter_source_var, width=330, state="readonly").pack(side="left", padx=5)
ctk.CTkButton(c_frame, text="Browse...", width=90, command=browse_counter_source).pack(side="left")

count_btn = ctk.CTkButton(tab_counter, text="Scan & Count Filters", command=run_filter_count, width=200, height=38,
                          font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1f538d")
count_btn.pack(pady=20)

counter_box = ctk.CTkTextbox(tab_counter, width=540, height=350, font=ctk.CTkFont(family="Consolas", size=12))
counter_box.pack(padx=10, pady=10)
counter_box.insert("end", "Select a folder above and click 'Scan & Count Filters'\nto view your LRGB / SHO exposure breakdown.")

# --- Aesthetic Banner ---
try:
    # Changed to your new FSjpeg.jpg
    img_data = Image.open(resource_path("FSjpeg.jpg"))
    aspect_ratio = img_data.height / img_data.width
    banner_height = int(650 * aspect_ratio)
    banner_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(650, banner_height))
    banner_label = ctk.CTkLabel(window, image=banner_img, text="")
    banner_label.pack(side="bottom", fill="x", pady=(5, 0))
except Exception:
    pass

window.mainloop()