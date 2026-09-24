FITSSwitcher v1.0.2 🌌

​FITSSwitcher is a smart, automated FITS file router and organizer designed specifically for amateur astrophotographers.

​If you use an ASIAIR, N.I.N.A., or similar capture software, you know the struggle: a messy hard drive full of dumped FITS files, morning flat frames with missing "Unknown" targets, and calibration frames mixed in with light frames. FITSSwitcher takes your raw intake folder and perfectly organizes it into a master directory ready for stacking in Astro Pixel Processor (APP), Siril, or PixInsight.

​✨ Key Features

​Chronological Session Mapping (S1, S2, S3): Uses a 12-hour astronomical offset so your overnight lights and morning flats automatically pair together into the exact same logical session. 

​Session Persistence: Never overwrite your historical data. FITSSwitcher scans your destination folder using smart regex and continues numbering exactly where you left off (e.g., automatically starting at S4 if S3 already exists). 

​Target Auto-Inheritance for Flats: Capture software often forgets to name the target for morning flats. FITSSwitcher acts as a detective, matches your "Unknown" flats to the lights taken on the same astronomical night, and automatically routes them to the correct target folder.

​Smart Global Calibration Routing: Route your Darks and Biases into a master global calibration library (e.g., Darks/ASI533MM/300s) while keeping your Lights and Flats neatly organized by target and session. 

​Granular Sorting Control: Choose exactly which frame types to move. Want to just organize today's Flats without touching your master folder of Lights? Just uncheck the boxes.

​Filter Counter: A built-in scanning tool to tally your total valid exposures per target and frame type, automatically sorting results into standard LRGB / SHO priority.

​Auto-Update Checker: The app silently checks GitHub for new releases on launch and will prompt you if a newer version of FITSSwitcher is available to download.

​📖 How to Use the FITS Sorter

​Step 1 & 2: Set Your Folders

​Select your Incoming FITS Folder (where your capture software dumped the files) and your Destination Folder (where you want your clean, organized library to live).

​Step 3: Select Frame Types to Sort

​Choose exactly what you want to move using the checkboxes.

​Pro Tip: Even if you uncheck "Lights" to only sort your morning Flats, FITSSwitcher will still silently scan your Lights in the background. This ensures your Flats inherit the correct target names before they are moved.

​Step 4: Define Folder Structure

​Use the dropdowns to build your ideal folder path, or use one of the built-in presets:

​Astro Pixel Processor (APP): Target / Filter / Type 

​Siril (Scripts): Target / Type 

​Comprehensive Mono: Target / Filter / Session / Type / Exposure 

​You can save your custom dropdown arrangement as a new preset by clicking Save Setup.

​Step 5: Global Calibration Library (Highly Recommended)

​Toggle Route Darks/Biases to Global Library ON.

Darks and Biases are temperature and exposure-dependent, not target-dependent. This toggle ignores your custom dropdowns for these specific frames and sends them to a clean, reusable master folder:

​Darks: Destination / Darks / [Camera] / [Exposure] 

​Biases: Destination / Biases / [Camera] 

​Step 6: Preview & Execute

​Toggle Dry Run / Simulation Mode ON.

​The Preview Generated Folders text box will populate with a live look at exactly what your destination directory will look like, alongside a log of any Auto-Inherited flat frames.

​If everything looks perfect, turn off Dry Run and click Sort Images.

​Made a mistake? Click Undo Last Sort to safely send the files right back to your incoming folder.

​📊 Using the Filter Counter Tab

​Shooting complex mono projects means tracking exactly how much LRGB and narrowband data you have collected.

​Navigate to the Filter Counter tab.

​Select your master destination folder (or any folder containing FITS files).

​Click Scan & Count Filters.

​The tool will parse your entire directory and provide a clean text breakdown of every valid frame, grouped by Target and Type. Filters are automatically sorted into their logical astronomical order (L, R, G, B, S, H, O) rather than alphabetically.

​⚙️ Technical Details: How "Sessions" Work

​Astro-imaging does not follow standard calendar dates. If you shoot the Pacman Nebula until 4:00 AM and shoot your flats at 9:00 AM, a standard calendar sort will split those files into two different days.

​FITSSwitcher subtracts 12 hours from every DATE-OBS timestamp in your FITS headers. This means a 2:00 AM light frame and a 9:00 AM flat frame mathematically register as the same "astronomical night". When sorted, they are both assigned to S1, ensuring your stacking software pairs the correct calibration frames with the correct light frames effortlessly.

