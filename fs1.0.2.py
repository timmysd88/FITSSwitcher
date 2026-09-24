
import os
import shutil
import glob
import json
import threading
import re
import tkinter as tk
import customtkinter as ctk
import sys
import requests
import webbrowser
from tkinter import filedialog, messagebox
from astropy.io import fits
from datetime import datetime, timedelta
from PIL import Image

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")

# --- VERSION & UPDATE STATE ---
CURRENT_VERSION = "v1.12"
GITHUB_REPO_URL = "https://api.github.com/repos/timmysd88/FITSSwitcher/releases/latest"
RELEASE_PAGE_URL = "https://github.com/timmysd88/FITSSwitcher/releases/latest"

# --- GLOBAL STATE MANAGEMENT ---
PRESETS_FILE = os.path.join(os.path.expanduser("~"), "FITSSwitcher_presets.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), "FITSSwitcher_history.json")
preview_generation_id = 0
current_valid_plan_id = None
planned_moves = []

default_presets = {
    "PixInsight (WBPP)": ["Target", "Session", "Filter", "Type", "None"],
    "Siril (Scripts)": ["Target", "Type", "None", "None", "None"],
    "Astro Pixel Processor (APP)": ["Target", "Filter", "Type", "None", "None"],
    "Comprehensive Mono": ["Target", "Filter", "Session", "Type", "Exposure"]
}

user_presets = {}
if os.path.exists(PRESETS_FILE):
    try:
        with open(PRESETS_FILE, "r") as f: user_presets = json.load(f)
    except Exception: pass

# --- AUTO-UPDATE CHECKER ---
def check_for_updates():
    def _check():
        try:
            response = requests.get(GITHUB_REPO_URL, timeout=3)
            response.raise_for_status()
            latest_version = response.json().get("tag_name", "")
            
            if not latest_version: 
                return

            # Robust version parser (e.g., turns "v1.12" into [1, 12])
            def parse_v(v_str):
                return [int(x) for x in re.sub(r'[^\d.]', '', v_str).split('.') if x]
            
            if parse_v(latest_version) > parse_v(CURRENT_VERSION):
                window.after(1000, prompt_update, latest_version)
        except Exception:
            pass # Fail silently if no internet connection or GitHub API is blocked

    threading.Thread(target=_check, daemon=True).start()

def prompt_update(latest_version):
    if messagebox.askyesno("Update Available", f"A new version of FITSSwitcher ({latest_version}) is available on GitHub!\n\nWould you like to download it now?"):
        webbrowser.open(RELEASE_PAGE_URL)

class SimpleToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip_window, text=self.text, justify="left",
                         background="#2b2b2b", foreground="#ffffff", 
                         relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack(ipadx=8, ipady=5)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

def get_astronomical_date(date_str):
    if not date_str: return "Unknown_Date"
    try:
        clean_date_str = date_str.split('.')[0]
        obs_dt = datetime.strptime(clean_date_str, "%Y-%m-%dT%H:%M:%S")
        logical_night = obs_dt - timedelta(hours=12)
        return logical_night.strftime("%Y-%m-%d")
    except Exception:
        return "Unknown_Date"

def parse_fits_metadata(header, siril_mode=False):
    target = "".join(c for c in header.get('OBJECT', 'Unknown').strip() if c.isalnum() or c in (' ', '_', '-')).strip().upper() or "UNKNOWN_TARGET"
    filt = "".join(c for c in header.get('FILTER', 'No_Filter').strip() if c.isalnum() or c in (' ', '_', '-')).strip().upper() or "NO_FILTER"
    
    astro_night = get_astronomical_date(header.get('DATE-OBS', '').strip())
    camera = "".join(c for c in header.get('INSTRUME', header.get('CAMERA', 'Unknown')).strip() if c.isalnum() or c in (' ', '_', '-')).upper()
    
    raw_type = header.get('IMAGETYP', 'Unknown_Type').strip()
    img_type = "".join(c for c in raw_type if c.isalnum() or c in (' ', '_', '-')).strip().title()

    if siril_mode:
        if img_type.lower() in ["light", "lights"]: img_type = "lights"
        elif img_type.lower() in ["flat", "flats"]: img_type = "flats"
        elif img_type.lower() in ["bias", "biases"]: img_type = "biases"
        elif img_type.lower() in ["dark", "darks"]: img_type = "darks"

    exptime = header.get('EXPTIME', '0')
    try: exp_formatted = f"{float(exptime):.0f}s" if float(exptime) >= 1 else f"{float(exptime):.2f}s"
    except (ValueError, TypeError): exp_formatted = f"{exptime}s"

    return target, filt, astro_night, img_type, exp_formatted, camera

def browse_source():
    if folder := filedialog.askdirectory(title="Select Incoming FITS Folder"):
        source_var.set(folder)
        trigger_preview_generation()

def browse_dest():
    if folder := filedialog.askdirectory(title="Select Destination Folder"):
        dest_var.set(folder)
        trigger_preview_generation()

def browse_counter_source():
    if folder := filedialog.askdirectory(title="Select Folder to Count"):
        counter_source_var.set(folder)

def save_custom_preset():
    dialog = ctk.CTkInputDialog(text="Enter a name for your custom layout:", title="Save Preset")
    preset_name = dialog.get_input()
    if preset_name:
        if preset_name in default_presets or preset_name == "Custom":
            messagebox.showerror("Error", "Cannot overwrite default presets. Choose a different name.")
            return
        user_presets[preset_name] = [cb1.get(), cb2.get(), cb3.get(), cb4.get(), cb5.get()]
        try:
            with open(PRESETS_FILE, "w") as f:
                json.dump(user_presets, f)
            preset_cb.configure(values=["Custom"] + list(default_presets.keys()) + list(user_presets.keys()))
            preset_var.set(preset_name)
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")

def apply_preset(choice):
    all_presets = {**default_presets, **user_presets}
    if choice in all_presets:
        layout = all_presets[choice]
        cb1.set(layout[0]); cb2.set(layout[1]); cb3.set(layout[2]); cb4.set(layout[3])
        cb5.set(layout[4] if len(layout) > 4 else "None")
    trigger_preview_generation()

def trigger_preview_generation(*args):
    global preview_generation_id, current_valid_plan_id
    preview_generation_id += 1
    current_valid_plan_id = None
    sort_btn.configure(state="disabled", fg_color="gray")
    preview_box.delete("0.0", "end")
    
    config = {
        "id": preview_generation_id,
        "source": source_var.get(),
        "dest": dest_var.get(),
        "keys": [k for k in [cb1.get(), cb2.get(), cb3.get(), cb4.get(), cb5.get()] if k != "None"],
        "preset": preset_var.get(),
        "global_calib": global_calib_var.get(),
        "dry_run": dry_run_var.get(),
        "types": {
            "lights": sort_lights_var.get(),
            "flats": sort_flats_var.get(),
            "darks": sort_darks_var.get(),
            "biases": sort_biases_var.get()
        }
    }

    if not config["source"] or not config["dest"]:
        preview_box.insert("end", "Waiting for folders to be selected...\n")
        return

    try:
        real_src = os.path.realpath(config["source"])
        real_dst = os.path.realpath(config["dest"])
        if os.path.commonpath([real_src, real_dst]) == real_src:
            preview_box.insert("end", "CRITICAL ERROR: Destination cannot be inside Source.\nPrevented recursive loop.")
            return
    except ValueError: pass

    if len(set(config["keys"])) < len(config["keys"]) or not config["keys"]:
        preview_box.insert("end", "Error: Invalid folder levels selected.\n")
        return

    if not any(config["types"].values()):
        preview_box.insert("end", "Error: No frame types selected to sort.\n")
        return

    preview_box.insert("end", "Scanning FITS files in background, please wait...\n")
    threading.Thread(target=_generate_preview_thread, args=(config,), daemon=True).start()

def _generate_preview_thread(config):
    files = []
    for ext in ('*.fit', '*.fits'):
        files.extend(glob.glob(os.path.join(config["source"], "**", ext), recursive=True))
        files.extend(glob.glob(os.path.join(config["source"], "**", ext.upper()), recursive=True))
    files = list(dict.fromkeys(files))

    if not files:
        window.after(0, lambda: [preview_box.delete("0.0", "end"), preview_box.insert("end", "No FITS files found.")])
        return

    local_planned_moves, folder_structure, file_cache = [], {}, []
    inheritance_log = []
    siril_mode = config["preset"] == "Siril (Scripts)"
    skipped_count = 0

    # Pass 1: Parse and Cache
    for file_path in files:
        if config["id"] != preview_generation_id: return 

        try:
            with fits.open(file_path, ignore_missing_end=True) as hdul:
                target, filt, astro_night, img_type, exp, camera = parse_fits_metadata(hdul[0].header, siril_mode)

            file_cache.append({"path": file_path, "filename": os.path.basename(file_path),
                               "target": target, "filter": filt, "astro_night": astro_night, 
                               "type": img_type, "exposure": exp, "camera": camera})
        except Exception:
            skipped_count += 1

    # Pass 2: Smart Auto-Inheritance for Flats
    night_targets = {}
    for fd in file_cache:
        if fd["type"].lower() in ["light", "lights"] and fd["target"] != "UNKNOWN_TARGET":
            night_targets.setdefault(fd["astro_night"], set()).add(fd["target"])
            
    for fd in file_cache:
        if fd["type"].lower() in ["flat", "flats"] and fd["target"] == "UNKNOWN_TARGET":
            targets = night_targets.get(fd["astro_night"], set())
            if len(targets) == 1:
                fd["target"] = list(targets)[0]
                if config["types"]["flats"]:
                    inheritance_log.append(f"🔗 Auto-Inherited Target '{fd['target']}' for Flat {fd['filename']}")
            elif len(targets) > 1:
                fd["target"] = list(targets)[0]
                if config["types"]["flats"]:
                    inheritance_log.append(f"⚠️ Multiple targets found on {fd['astro_night']}. Assigned '{fd['target']}' to {fd['filename']}")

    # Pass 3: PERSISTENT SESSION MAPPING
    incoming_target_dates = {}
    for fd in file_cache:
        incoming_target_dates.setdefault(fd["target"], set()).add(fd["astro_night"])

    target_session_map = {}
    dest_dir = config["dest"]
    
    for tgt, dates in incoming_target_dates.items():
        existing_sessions = set()
        tgt_dest_path = os.path.join(dest_dir, tgt)
        
        if os.path.exists(tgt_dest_path):
            try:
                for item in os.listdir(tgt_dest_path):
                    match = re.match(r'^(?i)(s|session)\s*[-_]?\s*(\d+)$', item.strip())
                    if match:
                        existing_sessions.add(int(match.group(2)))
            except Exception: pass

        max_existing_s = max(existing_sessions) if existing_sessions else 0
        sorted_incoming_dates = sorted(list(dates))
        target_session_map[tgt] = {}
        for idx, d in enumerate(sorted_incoming_dates):
            target_session_map[tgt][d] = f"S{max_existing_s + idx + 1}"

    # Pass 4: Evaluate and Build Paths
    for fd in file_cache:
        t_lower = fd["type"].lower()
        if t_lower in ["light", "lights"] and not config["types"]["lights"]: continue
        if t_lower in ["flat", "flats"] and not config["types"]["flats"]: continue
        if t_lower in ["dark", "darks"] and not config["types"]["darks"]: continue
        if t_lower in ["bias", "biases"] and not config["types"]["biases"]: continue

        fd["Session"] = target_session_map[fd["target"]][fd["astro_night"]]

        if config["global_calib"] and fd["type"].lower() in ["dark", "darks"]:
            path_parts = ["Darks", fd["camera"], fd["exposure"]]
        elif config["global_calib"] and fd["type"].lower() in ["bias", "biases"]:
            path_parts = ["Biases", fd["camera"]]
        else:
            data_map = {"Target": fd["target"], "Filter": fd["filter"], "Date": fd["astro_night"], 
                        "Session": fd["Session"], "Type": fd["type"], "Exposure": fd["exposure"]}
            path_parts = [data_map[k] for k in config["keys"]]
        
        dest_path = os.path.join(config["dest"], *path_parts)
        local_planned_moves.append({"source": fd["path"], "dest_dir": dest_path, "filename": fd["filename"]})

        current = folder_structure
        for p in path_parts[:-1]:
            if p not in current: current[p] = {}
            current = current[p]
        last = path_parts[-1]
        if last not in current: current[last] = 0
        current[last] += 1

    if config["id"] == preview_generation_id:
        window.after(0, _render_preview_ui, folder_structure, inheritance_log, local_planned_moves, config, skipped_count)

def _render_preview_ui(folder_structure, inheritance_log, moves, config, skipped):
    global planned_moves, current_valid_plan_id
    if config["id"] != preview_generation_id: return
    
    planned_moves = moves
    current_valid_plan_id = config["id"]
    preview_box.delete("0.0", "end")
    
    if config["dry_run"]: preview_box.insert("end", "--- SIMULATION / DRY RUN MODE ACTIVE ---\n")
    preview_box.insert("end", f"Successfully planned moves for {len(planned_moves)} selected images.\n")
    if skipped > 0: preview_box.insert("end", f"⚠️ Skipped {skipped} unreadable/corrupt files.\n")
    
    if inheritance_log:
        preview_box.insert("end", f"🔗 Auto-Inherited Targets for {len(inheritance_log)} Flat frames based on matching Lights.\n")

    preview_box.insert("end", "\nGenerated Directory Structure:\n\n")

    def render_dict(d, indent=0):
        for k, v in d.items():
            preview_box.insert("end", f"{'    '*indent}↳ 📁 {k}\n" if isinstance(v, dict) else f"{'    '*indent}↳ 📁 {k}  ({v} images)\n")
            if isinstance(v, dict): render_dict(v, indent + 1)
    render_dict(folder_structure)

    if planned_moves:
        sort_btn.configure(state="normal", fg_color="#2FA572", text="Simulate Sort" if config["dry_run"] else "Sort Images")

def execute_sort():
    if not planned_moves or current_valid_plan_id != preview_generation_id:
        messagebox.showerror("Error", "Configuration changed. Please wait for preview to refresh.")
        return
    if dry_run_var.get():
        messagebox.showinfo("Simulation Complete", f"DRY RUN PASSED for {len(planned_moves)} files.")
        return

    sort_btn.configure(state="disabled", fg_color="gray")
    threading.Thread(target=_execute_sort_thread, args=(planned_moves.copy(), source_var.get()), daemon=True).start()

def _execute_sort_thread(moves, source_dir):
    moved_count, history, error_log = 0, [], []
    
    for idx, move in enumerate(moves):
        try:
            if idx % 10 == 0: window.after(0, lambda c=idx, t=len(moves): preview_box.insert("end", f"\rMoving files... {c}/{t}"))
            os.makedirs(move["dest_dir"], exist_ok=True)
            new_path = os.path.join(move["dest_dir"], move["filename"])
            base, ext = os.path.splitext(new_path)
            c = 1
            while os.path.exists(new_path):
                new_path = f"{base}_{c}{ext}"
                c += 1
            shutil.move(move["source"], new_path)
            history.append({"source": move["source"], "moved_to": new_path})
            moved_count += 1
        except Exception as e: 
            error_log.append(f"{move['filename']}: {e}")

    try:
        with open(HISTORY_FILE, "w") as f: json.dump(history, f)
        window.after(0, lambda: undo_btn.configure(state="normal"))
    except Exception: pass

    for root, dirs, files in os.walk(source_dir, topdown=False):
        for d in dirs:
            try: os.rmdir(os.path.join(root, d))
            except OSError: pass

    window.after(0, _sort_complete_callback, moved_count, error_log)

def _sort_complete_callback(moved_count, error_log):
    global planned_moves
    planned_moves.clear()
    preview_box.insert("end", f"\nDone! Successfully sorted {moved_count} images.\n")
    if error_log:
        err_msg = "Some files could not be moved:\n\n" + "\n".join(error_log[:5])
        if len(error_log) > 5: err_msg += f"\n...and {len(error_log)-5} more."
        messagebox.showwarning("Sort Completed with Errors", err_msg)
    else:
        messagebox.showinfo("Success", f"Sorted {moved_count} images!")

def execute_undo():
    if not os.path.exists(HISTORY_FILE): return
    try:
        with open(HISTORY_FILE, "r") as f: history = json.load(f)
    except Exception: return
    if not history or not messagebox.askyesno("Confirm Undo", f"Restore {len(history)} files?"): return

    restored, error_log = 0, []
    for record in history:
        if os.path.exists(record["moved_to"]):
            dest = record["source"]
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.exists(dest):
                    base, ext = os.path.splitext(dest)
                    c = 1
                    while os.path.exists(dest):
                        dest = f"{base}_restored_{c}{ext}"
                        c += 1
                shutil.move(record["moved_to"], dest)
                restored += 1
            except Exception as e: error_log.append(f"{record['moved_to']}: {e}")
    
    try: os.remove(HISTORY_FILE)
    except Exception: pass
    undo_btn.configure(state="disabled")

    if error_log:
        err_msg = "Some files could not be restored:\n\n" + "\n".join(error_log[:5])
        messagebox.showwarning("Undo Completed with Errors", err_msg)
    else:
        messagebox.showinfo("Undo Complete", f"Successfully restored {restored} files!")

def get_filter_priority(name):
    u = name.upper()
    return 1 if u in ['L','LUM','LUMINANCE'] else 2 if u in ['R','RED'] else 3 if u in ['G','GREEN'] else 4 if u in ['B','BLUE'] else 5 if u in ['SII','S2','S'] else 6 if u in ['HA','H-ALPHA','H'] else 7 if u in ['OIII','O3','O'] else 99

def run_filter_count():
    if not counter_source_var.get():
        messagebox.showerror("Error", "Select a folder to analyze.")
        return
    count_btn.configure(state="disabled")
    counter_box.delete("0.0", "end")
    counter_box.insert("end", "Scanning files in background...\n")
    threading.Thread(target=_run_filter_count_thread, args=(counter_source_var.get(),), daemon=True).start()

def _run_filter_count_thread(folder):
    files = []
    for ext in ('*.fit', '*.fits'):
        files.extend(glob.glob(os.path.join(folder, "**", ext), recursive=True))
        files.extend(glob.glob(os.path.join(folder, "**", ext.upper()), recursive=True))
    files = list(dict.fromkeys(files))

    if not files:
        window.after(0, lambda: [counter_box.delete("0.0", "end"), counter_box.insert("end", "No FITS files found."), count_btn.configure(state="normal")])
        return

    stats, global_filters, valid_files = {}, {}, 0
    for fp in files:
        try:
            with fits.open(fp, ignore_missing_end=True) as hdul:
                target, filt, _, img_type, _, _ = parse_fits_metadata(hdul[0].header)
            if target not in stats: stats[target] = {}
            if img_type not in stats[target]: stats[target][img_type] = {}
            if filt not in stats[target][img_type]: stats[target][img_type][filt] = 0
            stats[target][img_type][filt] += 1
            if filt not in global_filters: global_filters[filt] = 0
            global_filters[filt] += 1
            valid_files += 1
        except Exception: pass
    window.after(0, _render_filter_count_ui, stats, global_filters, valid_files)

def _render_filter_count_ui(stats, global_filters, total):
    counter_box.delete("0.0", "end")
    counter_box.insert("end", f"Analyzed {total} valid frames. Breakdown below:\n\n")
    for tgt, types in stats.items():
        counter_box.insert("end", f"🎯 Target: {tgt}\n")
        for itype, filters in types.items():
            counter_box.insert("end", f"    └─ Frame Type: {itype}\n")
            for filt, c in sorted(filters.items(), key=lambda x: (get_filter_priority(x[0]), x[0])):
                counter_box.insert("end", f"        └─ Filter [{filt}]: {c} exposures\n")
        counter_box.insert("end", "\n")
    counter_box.insert("end", "=" * 45 + "\n📊 TOTAL FILTER COUNTS\n" + "=" * 45 + "\n")
    for filt, c in sorted(global_filters.items(), key=lambda x: (get_filter_priority(x[0]), x[0])):
        counter_box.insert("end", f" [{filt}] Filter Total: {c} exposures\n")
    count_btn.configure(state="normal")

window = ctk.CTk()
window.title(f"FITSSwitcher {CURRENT_VERSION}")
window.geometry("700x820")
try: window.iconbitmap(resource_path("FSico.ico"))
except Exception: pass

source_var, dest_var, preset_var, counter_source_var = ctk.StringVar(), ctk.StringVar(), ctk.StringVar(value="Custom"), ctk.StringVar()
sort_lights_var, sort_flats_var, sort_darks_var, sort_biases_var = ctk.BooleanVar(value=True), ctk.BooleanVar(value=True), ctk.BooleanVar(value=True), ctk.BooleanVar(value=True)
global_calib_var = ctk.BooleanVar(value=True)
dry_run_var = ctk.BooleanVar(value=False)

tabview = ctk.CTkTabview(window, width=660, height=650)
tabview.pack(padx=20, pady=10)
tab_sorter, tab_counter = tabview.add("FITS Sorter"), tabview.add("Filter Counter")

ctk.CTkLabel(tab_sorter, text="1. Select Incoming FITS Folder:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5, 5))
f1 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f1.pack()
src_entry = ctk.CTkEntry(f1, textvariable=source_var, width=350, state="readonly"); src_entry.pack(side="left", padx=5)
src_btn = ctk.CTkButton(f1, text="Browse...", width=90, command=browse_source); src_btn.pack(side="left")

ctk.CTkLabel(tab_sorter, text="2. Select Destination Folder:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
f2 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f2.pack()
dest_entry = ctk.CTkEntry(f2, textvariable=dest_var, width=350, state="readonly"); dest_entry.pack(side="left", padx=5)
dest_btn = ctk.CTkButton(f2, text="Browse...", width=90, command=browse_dest); dest_btn.pack(side="left")

ctk.CTkLabel(tab_sorter, text="3. Select Frame Types to Sort:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
f_types = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f_types.pack()
ctk.CTkCheckBox(f_types, text="Lights", variable=sort_lights_var, command=trigger_preview_generation).pack(side="left", padx=10)
ctk.CTkCheckBox(f_types, text="Flats", variable=sort_flats_var, command=trigger_preview_generation).pack(side="left", padx=10)
ctk.CTkCheckBox(f_types, text="Darks", variable=sort_darks_var, command=trigger_preview_generation).pack(side="left", padx=10)
ctk.CTkCheckBox(f_types, text="Biases", variable=sort_biases_var, command=trigger_preview_generation).pack(side="left", padx=10)
SimpleToolTip(f_types, "Uncheck frame types to exclude them from the move process.\nUnchecked Lights will still be scanned to auto-target your Flats.")

ctk.CTkLabel(tab_sorter, text="4. Define Folder Structure:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
f3 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f3.pack(pady=(0, 10))
preset_cb = ctk.CTkComboBox(f3, values=["Custom"] + list(default_presets.keys()) + list(user_presets.keys()), variable=preset_var, width=230, command=apply_preset)
preset_cb.pack(side="left", padx=5)
save_btn = ctk.CTkButton(f3, text="Save Setup", width=90, fg_color="#1f538d", command=save_custom_preset); save_btn.pack(side="left", padx=5)

f4 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f4.pack()
opts = ["Target", "Session", "Date", "Filter", "Type", "Exposure", "None"]
cb1 = ctk.CTkComboBox(f4, values=opts, width=80, command=trigger_preview_generation); cb1.set("Target"); cb1.pack(side="left", padx=2); ctk.CTkLabel(f4, text="/").pack(side="left")
cb2 = ctk.CTkComboBox(f4, values=opts, width=80, command=trigger_preview_generation); cb2.set("Session"); cb2.pack(side="left", padx=2); ctk.CTkLabel(f4, text="/").pack(side="left")
cb3 = ctk.CTkComboBox(f4, values=opts, width=80, command=trigger_preview_generation); cb3.set("Type"); cb3.pack(side="left", padx=2); ctk.CTkLabel(f4, text="/").pack(side="left")
cb4 = ctk.CTkComboBox(f4, values=opts, width=80, command=trigger_preview_generation); cb4.set("Exposure"); cb4.pack(side="left", padx=2); ctk.CTkLabel(f4, text="/").pack(side="left")
cb5 = ctk.CTkComboBox(f4, values=opts, width=80, command=trigger_preview_generation); cb5.set("None"); cb5.pack(side="left", padx=2)

f_global = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f_global.pack(pady=(15, 0))
global_switch = ctk.CTkSwitch(f_global, text="Route Darks/Biases to Global Library", variable=global_calib_var, command=trigger_preview_generation); global_switch.pack()

f6 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f6.pack(pady=(15, 0))
dry_switch = ctk.CTkSwitch(f6, text="Dry Run / Simulation Mode", variable=dry_run_var, command=trigger_preview_generation); dry_switch.pack()

ctk.CTkLabel(tab_sorter, text="5. Preview Generated Folders:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
preview_box = ctk.CTkTextbox(tab_sorter, width=560, height=140, font=ctk.CTkFont(family="Consolas", size=12))
preview_box.pack(padx=20, pady=5); preview_box.insert("end", "Select folders to generate a preview...")

f7 = ctk.CTkFrame(tab_sorter, fg_color="transparent"); f7.pack(pady=10)
sort_btn = ctk.CTkButton(f7, text="Sort Images", command=execute_sort, width=160, height=35, font=ctk.CTkFont(size=14, weight="bold"), state="disabled", fg_color="gray")
sort_btn.pack(side="left", padx=10)
undo_btn = ctk.CTkButton(f7, text="Undo Last Sort", command=execute_undo, width=160, height=35, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#A52A2A", state="normal" if os.path.exists(HISTORY_FILE) else "disabled")
undo_btn.pack(side="left", padx=10)

ctk.CTkLabel(tab_counter, text="Select Folder to Analyze:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
cf = ctk.CTkFrame(tab_counter, fg_color="transparent"); cf.pack()
count_entry = ctk.CTkEntry(cf, textvariable=counter_source_var, width=350, state="readonly"); count_entry.pack(side="left", padx=5)
count_browse = ctk.CTkButton(cf, text="Browse...", width=90, command=browse_counter_source); count_browse.pack(side="left")
count_btn = ctk.CTkButton(tab_counter, text="Scan & Count Filters", command=run_filter_count, width=200, height=38, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1f538d"); count_btn.pack(pady=20)
counter_box = ctk.CTkTextbox(tab_counter, width=560, height=380, font=ctk.CTkFont(family="Consolas", size=12)); counter_box.pack(padx=10, pady=10)
counter_box.insert("end", "Select a folder above and click 'Scan & Count Filters'\nto view your LRGB / SHO exposure breakdown.")

try:
    img_data = Image.open(resource_path("FSjpeg.jpg"))
    ctk.CTkLabel(window, image=ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(700, int(700 * (img_data.height / img_data.width)))), text="").pack(side="bottom", fill="x", pady=(5, 0))
except Exception: pass

# Launch the auto-update checker in the background before drawing the window
check_for_updates()

window.mainloop()
