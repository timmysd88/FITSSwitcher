# FITSSwitcher v2.85 🌌

**FITSSwitcher** is an open-source, automated FITS file router, header editor, and organizer designed specifically for amateur astrophotographers. 

If you use ASIAIR, N.I.N.A., or similar capture software, you know the struggle: a messy hard drive full of dumped subframes, morning flats with "Unknown" targets, and calibration files mixed in with lights. FITSSwitcher takes your raw intake directory and transforms it into a clean, structured library ready for stacking in Astro Pixel Processor (APP), Siril, or PixInsight.

> ⚠️ **Note on Windows Defender / SmartScreen**  
> Because FITSSwitcher is an open-source, indie-developed application, Windows SmartScreen may flag the installer as an *"unrecognized app."* This is standard for unsigned Python executables. To install, click **More info**, then click **Run anyway**.

---

## 🚀 What's New in v2.85

* **Interactive Review Modal:** Preview proposed file movements, filter totals, and destination paths in an interactive window before a single file is moved.
* **Batch FITS Header Editor:** Rename target headers or update mosaic panel designations across entire subframe sets in seconds.
* **Granular Subfolder Controls:** Choose between full *Session + Filter* hierarchies or *Session Only* routing, with optional subfolder exclusions.
* **Enhanced Auto-Inheritance Engine:** Smarter matching between morning flat frames and overnight light sessions.

---

## ✨ Key Features

* **Chronological Session Mapping (`S1`, `S2`, `S3`):** Uses a 12-hour astronomical offset so your overnight lights and morning flats automatically group into the exact same logical session folder.
* **Target Auto-Inheritance for Flats:** Capture software frequently labels morning flats as "Unknown." FITSSwitcher detects the session timestamp, matches flats to lights taken on the same astronomical night, and inherits the correct target name automatically.
* **Batch Mosaic Header Editor:** Easily re-label target headers or batch-assign panel numbers (`Panel_1`, `Panel_2`) across complex multi-panel mosaic projects.
* **Smart Global Calibration Routing:** Route Darks and Biases into a master library (`Destination/Darks/[Camera]/[Exposure]`), while keeping Lights and Flats neatly organized by target and session.
* **Session Persistence:** Never overwrites existing data. Scans your destination folder and continues session numbering right where you left off (e.g., automatically starting at `S4` if `S3` exists).
* **Filter Counter & Priority Sorting:** Scans your directory and tallies total exposures per target. Automatically orders filters into logical astronomical sequence (`L`, `R`, `G`, `B`, `H`, `O`, `S`).
* **Dry Run & Undo Protection:** Test your sorting configuration with a simulated dry run. Made a mistake? Use **Undo Last Sort** to safely return files to your incoming folder.

---

## 📖 How to Use FITSSwitcher

### Step 1: Select Your Directories
Select your **Incoming Folder** (where your capture software dumped the subframes) and your **Destination Folder** (where your structured library lives).

### Step 2: Choose Frame Types to Sort
Check the frame types you want to move (Lights, Darks, Flats, Biases).

> 💡 **Pro Tip:** Even if you uncheck "Lights" to sort only morning flats, FITSSwitcher silently scans your lights in the background to ensure flats inherit the correct target names.

### Step 3: Define Folder Structure & Routing
Select your preferred folder path layout or choose a pre-built preset:

| Software / Workflow | Recommended Folder Layout |
| :--- | :--- |
| **Astro Pixel Processor (APP)** | `Target / Filter / Type` |
| **Siril (Scripts)** | `Target / Type` |
| **Comprehensive Mono** | `Target / Filter / Session / Type / Exposure` |

### Step 4: Configure Global Calibration Library (Optional)
Toggle **Route Darks/Biases to Global Library ON**. Calibration frames are camera- and exposure-dependent, not target-dependent. This sends them directly to a clean, reusable master directory:
* **Darks:** `Destination / Darks / [Camera] / [Exposure]`
* **Biases:** `Destination / Biases / [Camera]`

### Step 5: Review & Execute
1. Keep **Dry Run / Simulation Mode** enabled to generate a live preview of your
