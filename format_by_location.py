"""
Name Cierra B.
Date: 10/06/2025

This is for EPA Daily & Hourly PM2.5, PM10. NO2 Data: https://aqs.epa.gov/aqsweb/airdata/download_files.html#AQI

This  script reshapes cleaned air-quality data (from PM₂.₅, PM₁₀, and NO₂ CSVs) into a wide, comparison-friendly format where each pollutant occupies its own column (e.g., Pollutant A (NO₂), Pollutant B (PM₂.₅), Pollutant C (PM₁₀)).
It groups the data by location and date—using coordinates, site number, or region fields—and outputs either a single wide CSV or an Excel workbook with one sheet per location (similar to your “Philadelphia” and “Iowa” tabs).

Key Features
    - Pivot by pollutant: Converts “Pollutant Name” rows into side-by-side columns for easy comparison.
    - Automatic grouping: Groups by State, County, City, Site Num, Latitude, Longitude, and Date.
    - Value selection: Lets you choose which numeric metric (e.g., Arithmetic Mean or 1st Max Value) becomes the pollutant value.
    - Flexible column labels: Option to label columns as
        - Pollutant A (NO₂), Pollutant B (PM₂.₅) …, or
        - use the pollutant names directly (NO₂, PM₂.₅, PM₁₀).
    - Output options:
        - Export a single combined CSV file, or
        - Export an Excel workbook with one sheet per location.
    - User-friendly interface: Uses simple GUI dialogs to select input/output files, column names, and export options—no command-line input required.
        Example Output
        Date    Pollutant A (NO₂)   Pollutant B (PM₂.₅) Pollutant C (PM₁₀)  State   City    Latitude    Longitude
        2025-01-10  15.2    9.81    23.4    Maryland    Baltimore   39.290  −76.610

        MUST HAVE PANDAS AND OPENPYXL INSTALLED
        pip install openpyxl
        pip install pandas

"""
import os
import pandas as pd
from tkinter import Tk, filedialog, simpledialog, messagebox

# ---------- helpers ----------
def pick_file():
    Tk().withdraw()
    f = filedialog.askopenfilename(title="Select cleaned/combined CSV", filetypes=[("CSV files","*.csv")])
    return f

def pick_folder():
    Tk().withdraw()
    d = filedialog.askdirectory(title="Select output folder")
    return d

def coalesce_cols(df, candidates, default=None):
    for c in candidates:
        if c in df.columns:
            return c
    return default

def make_pollutant_labels(unique_pollutants, use_abc=True):
    """
    Build a mapping from pollutant name -> column label.
    If use_abc is True, label as Pollutant A/B/C (NO2) etc.
    Otherwise, label as NO2, PM2.5, PM10 directly.
    """
    labels = {}
    abc = ["A","B","C","D","E","F","G","H"]
    for i, p in enumerate(sorted(unique_pollutants)):
        if use_abc:
            key = f"Pollutant {abc[i]} ({p})"
        else:
            key = p
        labels[p] = key
    return labels

# ---------- main process ----------
def main():
    messagebox.showinfo("Wide Maker", "Select your cleaned/combined pollutant CSV.")
    in_file = pick_file()
    if not in_file:
        messagebox.showwarning("No file", "No input selected.")
        return

    out_dir = pick_folder()
    if not out_dir:
        messagebox.showwarning("No folder", "No output folder selected.")
        return

    # Load
    df = pd.read_csv(in_file)

    # Basic column detection
    date_col = coalesce_cols(df, ["Date", "Date Local", "Date Observed", "Date GMT"], default=None)
    if date_col is None:
        date_col = simpledialog.askstring("Date Column", "Enter the date column name (e.g., Date or Date Local):")
        if not date_col or date_col not in df.columns:
            messagebox.showerror("Missing date", "Could not find the date column.")
            return

    # Normalize date
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    # Choose the value column to pivot (default Arithmetic Mean)
    value_col = "Arithmetic Mean" if "Arithmetic Mean" in df.columns else None
    if value_col is None:
        value_col = simpledialog.askstring(
            "Value Column",
            "Enter the numeric column to pivot (e.g., Arithmetic Mean, 1st Max Value):"
        )
        if not value_col or value_col not in df.columns:
            messagebox.showerror("Missing value", "Could not find the value column.")
            return

    # Identify location columns (coordinates & common AQS fields)
    lat_col  = coalesce_cols(df, ["Latitude", "Site Latitude", "Lat"], default=None)
    lon_col  = coalesce_cols(df, ["Longitude", "Site Longitude", "Lon", "Long"], default=None)
    state_c  = coalesce_cols(df, ["State Name", "State"], default=None)
    county_c = coalesce_cols(df, ["County Name", "County"], default=None)
    city_c   = coalesce_cols(df, ["City Name", "City"], default=None)
    site_num = coalesce_cols(df, ["Site Num", "Site Number"], default=None)

    index_cols = [c for c in [state_c, county_c, city_c, site_num, lat_col, lon_col, date_col] if c]

    # Ensure we have pollutant name
    if "Pollutant Name" not in df.columns:
        messagebox.showerror("Missing", "Input must have a 'Pollutant Name' column (from your cleaner).")
        return

    # Round numeric values to 3 decimals
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").round(3)

    # Pivot: index = location + date; columns = Pollutant Name; values = chosen value
    wide = df.pivot_table(
        index=index_cols,
        columns="Pollutant Name",
        values=value_col,
        aggfunc="mean"  # if duplicates same day/site, take mean
    ).reset_index()

    # Decide column labels style
    label_style = simpledialog.askstring(
        "Column Labels",
        "Type 'ABC' to label as Pollutant A/B/C (NO2), or 'NAME' to use pollutant names (NO2, PM2.5):",
    )
    use_abc = (label_style or "").strip().upper() != "NAME"

    pollutants = [c for c in wide.columns if c not in index_cols]
    label_map = make_pollutant_labels(pollutants, use_abc=use_abc)
    wide = wide.rename(columns=label_map)

    # Reorder so Date + pollutant columns come first (like screenshot)
    pollutant_cols = [label_map[p] for p in pollutants]
    front = [date_col] + pollutant_cols
    remaining = [c for c in wide.columns if c not in front]
    ordered_cols = [c for c in front if c in wide.columns] + remaining
    wide = wide[ordered_cols]

    # Output choice: single CSV or Excel with one sheet per location
    export_mode = simpledialog.askstring(
        "Export Mode",
        "Type 'CSV' for a single wide CSV, or 'XLSX' for an Excel file with one sheet per location:"
    )
    export_mode = (export_mode or "CSV").strip().upper()

    base_name = os.path.splitext(os.path.basename(in_file))[0]
    if export_mode == "XLSX":
        # One sheet per (State/County/City/Site) combo; coordinates in sheet name when needed
        out_path = os.path.join(out_dir, f"{base_name}_wide_by_location.xlsx")
        try:
            import openpyxl  # noqa: F401
        except Exception:
            messagebox.showwarning("Dependency", "Install openpyxl to export Excel: pip install openpyxl")
            return

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            # Group by location fields except Date
            group_cols = [c for c in [state_c, county_c, city_c, site_num, lat_col, lon_col] if c]
            if not group_cols:
                # No location fields? just write one sheet
                wide.to_excel(writer, sheet_name="All", index=False)
            else:
                for keys, sub in wide.groupby(group_cols):
                    # Build safe sheet name
                    if not isinstance(keys, tuple):
                        keys = (keys,)
                    name_parts = [str(k) for k in keys if pd.notna(k)]
                    sheet_name = "-".join(name_parts)[:31] if name_parts else "Sheet1"
                    sub.to_excel(writer, sheet_name=sheet_name or "Sheet1", index=False)

        messagebox.showinfo("Done", f"Saved Excel workbook:\n{out_path}")
    else:
        out_path = os.path.join(out_dir, f"{base_name}_wide.csv")
        wide.to_csv(out_path, index=False)
        messagebox.showinfo("Done", f"Saved CSV:\n{out_path}")

if __name__ == "__main__":
    main()
