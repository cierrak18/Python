"""
Name Cierra Britt
Date: 10/06/2025

This is for EPA Daily & Hourly PM2.5, PM10. NO2 Data: https://aqs.epa.gov/aqsweb/airdata/download_files.html#AQI

Summary: 
Pollution Data Cleaner (GUI Version)
The Pollution Data Cleaner is a Python-based graphical user interface (GUI) tool designed to automate the cleaning, merging, and filtering of air quality datasets (PM₂.₅, PM₁₀, and NO₂). It streamlines the process of preparing both daily and hourly pollutant data for further analysis or visualization.

Core Functionality
1. Interactive GUI Workflow:
    Users are guided through a series of prompts (via pop-up windows) to specify:
        - How many CSV files they want to process
        - Whether the data is daily or hourly
        - Whether to combine multiple files into a single dataset
        - The pollutant type (e.g., PM2.5, PM10, NO2)
        - Optional filters (by state, city, county, site, or geographic coordinates)
2. Data Cleaning:
    The script removes redundant or low-information fields such as Pollutant Standard, Date Last Change, Event Type, AQI, CBSA, and Datum. It then automatically:
        - Adds a Pollutant Name column to identify the dataset source
        - Generates a Sample ID for each record (e.g., PM25-0001, NO2-0001)
        - Standardizes and rounds numeric fields (e.g., Arithmetic Mean, 1st Max Value) to three decimal places
3. Filtering:
    Users can choose to extract specific records based on:
        - State Name (e.g., “Maryland”)
        - City Name (e.g., “Baltimore”)
        - County Name
        - Site Number
        - Coordinates (latitude and longitude pairs)
4. Automated Export & File Naming:
    Once cleaned, the data is exported as a CSV file named according to its type and pollutant, for example:
        - daily_PM25_cleaned.csv
        - hourly_NO2_cleaned.csv
The file is saved to a user-selected output folder.

"""
import pandas as pd
import os
from tkinter import Tk, filedialog, simpledialog, messagebox
import sys

# -------------------------------
# CONFIG
# -------------------------------
DROP_COLS = [
    'Pollutant Standard', 'Date Last Change', 'Event Type',
    'AQI', 'CBSA', 'Datum'
]
FILTER_MAP = {
    'state': 'State Name',
    'city': 'City Name',
    'county': 'County Name',
    'site': 'Site Num',
    'coordinates': ['Latitude', 'Longitude']
}
POLLUTANT_PREFIX = {'PM2.5': 'PM25', 'PM10': 'PM10', 'NO2': 'NO2', 'Unknown': 'UNKNOWN'}

# -------------------------------
# FILE DIALOGS
# -------------------------------
def select_files():
    Tk().withdraw()
    files = filedialog.askopenfilenames(
        title="Select daily or hourly CSV file(s)",
        filetypes=[("CSV files", "*.csv")]
    )
    return list(files)

def choose_output_directory():
    Tk().withdraw()
    return filedialog.askdirectory(title="Select output folder")

# -------------------------------
# POLLUTANT FROM FILENAME (no regex)
# -------------------------------
def pollutant_from_filename(path: str) -> str:
    name = os.path.basename(path).lower()
    if "pm2.5" in name or "pm25" in name: return "PM2.5"
    if "pm10"  in name:                    return "PM10"
    if "no2"   in name:                    return "NO2"
    return "Unknown"

def ask_pollutant_for_file(path: str) -> str:
    # Fallback prompt if filename doesn’t indicate pollutant
    msg = f"Could not detect pollutant from file name:\n\n{os.path.basename(path)}\n\nEnter one of: PM2.5, PM10, NO2"
    p = simpledialog.askstring("Pollutant?", msg)
    if not p: return "Unknown"
    p = p.strip().upper().replace(" ", "")
    if p in ("PM2.5","PM25"): return "PM2.5"
    if p == "PM10":           return "PM10"
    if p == "NO2":            return "NO2"
    return "Unknown"

# -------------------------------
# CLEAN + LABEL (per file)
# -------------------------------
def clean_and_label_dataframe(df: pd.DataFrame, pollutant: str) -> pd.DataFrame:
    # remove low-value cols
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors='ignore')

    # Sample ID + Pollutant Name first
    prefix = POLLUTANT_PREFIX.get(pollutant, "UNKNOWN")
    df.insert(0, "Sample ID", [f"{prefix}-{i:04d}" for i in range(1, len(df)+1)])
    df.insert(1, "Pollutant Name", pollutant)

    # Round key numeric columns if present
    for col in ['Arithmetic Mean', '1st Max Value', '1st Max Daily Value']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(3)

    # Ensure column order: Sample ID, Pollutant Name, then rest
    cols = ["Sample ID", "Pollutant Name"] + [c for c in df.columns if c not in ("Sample ID","Pollutant Name")]
    return df[cols]

# -------------------------------
# FILTERING
# -------------------------------
def filter_data(df, keyword_type, keyword):
    kt = (keyword_type or "").strip().lower()
    if kt == "coordinates":
        try:
            lat_str, lon_str = [x.strip() for x in keyword.split(",")]
            lat, lon = float(lat_str), float(lon_str)
            return df[(df["Latitude"].round(3) == round(lat, 3)) &
                      (df["Longitude"].round(3) == round(lon, 3))]
        except Exception:
            messagebox.showerror("Error", "Invalid coordinate format. Use: 39.290, -76.610")
            return df
    else:
        col = FILTER_MAP.get(kt)
        if isinstance(col, str) and col in df.columns:
            return df[df[col].astype(str).str.contains(keyword, case=False, na=False)]
        return df

# -------------------------------
# EXPORT
# -------------------------------
def export_cleaned(df, frequency, out_dir):
    pollutants = df["Pollutant Name"].dropna().unique().tolist()
    pollutants_str = "_".join([p.replace(".", "").replace(" ", "") for p in pollutants]) if pollutants else "Unknown"
    filename = f"{frequency.lower()}_{pollutants_str}_cleaned.csv"
    out_path = os.path.join(out_dir, filename)
    df.to_csv(out_path, index=False)
    messagebox.showinfo("Success", f"✅ Exported file:\n{out_path}")

# -------------------------------
# MAIN
# -------------------------------
def main():
    messagebox.showinfo("Pollution Data Cleaner", "Welcome! Select your pollutant data CSV file(s).")

    files = select_files()
    if not files:
        messagebox.showwarning("No Files", "No files selected. Exiting.")
        sys.exit()

    frequency = simpledialog.askstring("Data Frequency", "Is your data DAILY or HOURLY?")
    if not frequency:
        messagebox.showwarning("Missing Input", "No frequency entered. Exiting.")
        sys.exit()
    frequency = frequency.strip().lower()

    combine = messagebox.askyesno("Combine Files", f"You selected {len(files)} file(s). Combine them into one?")

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)

            pollutant = pollutant_from_filename(f)
            if pollutant == "Unknown":
                pollutant = ask_pollutant_for_file(f)

            cleaned = clean_and_label_dataframe(df, pollutant)
            frames.append(cleaned)
        except Exception as e:
            messagebox.showerror("Error Reading File", f"Failed to read {f}.\nError: {e}")

    final_df = pd.concat(frames, ignore_index=True) if combine else frames[0]

    # Optional filter
    if messagebox.askyesno("Filter", "Filter by state, city, county, site, or coordinates?"):
        kt = simpledialog.askstring("Filter Type", "Enter: state, city, county, site, or coordinates")
        kw = simpledialog.askstring("Keyword", "e.g., Maryland, Baltimore, 39.290, -76.610")
        if kt and kw:
            final_df = filter_data(final_df, kt, kw)

    out_dir = choose_output_directory()
    if not out_dir:
        messagebox.showwarning("No Output Folder", "No output folder selected. Exiting.")
        sys.exit()

    export_cleaned(final_df, frequency, out_dir)
    messagebox.showinfo("Done", "✅ Cleaning and combining completed successfully!")

if __name__ == "__main__":
    main()
