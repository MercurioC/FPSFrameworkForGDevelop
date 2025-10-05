"""
OBJ to JSON Converter - v0.0.2 (no external dependencies)

This program converts a 3D model in .obj format into a structured JSON format.
It extracts vertex data from the .obj file, calculates the bounding box for
each "brush" (assumed groups of 8 vertex lines), computes center and size, and
formats the output as JSON for use in external applications (e.g., GDevelop).

Key improvements vs v0.0.1:
- Removed NumPy dependency (pure Python only) so double-clicking works even without numpy installed.
- Safer Tkinter usage (StringVar bound to the Tk app).
- Better error reporting (message boxes for common problems).
- More robust OBJ parsing with defensive checks and clearer logs.
"""

import json
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
import datetime
from pathlib import Path
import sys
import traceback

VERSION = "v0.0.2"

generated_json_content = None
app = None
log_text = None
copy_button = None

def log_message(msg: str) -> None:
    """Logs messages in the GUI log window (if available) and prints to stdout for debugging."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    try:
        if log_text is not None:
            log_text.insert(tk.END, line + "\n")
            log_text.see(tk.END)
    except Exception:
        # In case GUI isn't fully ready yet, just skip GUI logging
        pass
    print(line)


def parse_vertices_from_obj(obj_path: Path):
    """Return a list of 3D vertices from 'v ' lines in an OBJ file."""
    vertices = []
    with obj_path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            if raw.startswith("v "):
                parts = raw.split()
                if len(parts) >= 4:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        z = float(parts[3])
                        vertices.append([x, y, z])
                    except ValueError:
                        # Skip malformed vertex lines but keep going
                        log_message(f"Warning: Malformed vertex line skipped: {raw.strip()}")
                else:
                    log_message(f"Warning: Short vertex line skipped: {raw.strip()}")
    return vertices


def chunk_vertices_as_brushes(vertices, size=8):
    """
    Group vertices into chunks of 'size' (default 8) representing axis-aligned boxes.
    If the last chunk is shorter than 'size', it is ignored (with a warning).
    """
    brushes = []
    for i in range(0, len(vertices), size):
        chunk = vertices[i:i+size]
        if len(chunk) < size:
            log_message("Warning: Incomplete brush detected at end of file, skipping.")
            continue
        brushes.append(chunk)
    return brushes


def bbox_of_points(points):
    """Compute min, max, center and extents (width, height, depth) for a list of [x,y,z] points."""
    if not points:
        raise ValueError("No points supplied to bbox_of_points.")
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    min_z = min(p[2] for p in points)
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    max_z = max(p[2] for p in points)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0

    width  = max_x - min_x
    height = max_y - min_y
    depth  = max_z - min_z

    return (min_x, min_y, min_z), (max_x, max_y, max_z), (center_x, center_y, center_z), (width, height, depth)


def obj_to_json(obj_path: Path, json_path: Path, name: str, layer: str, lock: bool):
    """Parses the .obj file and converts its data into a JSON format."""
    global generated_json_content
    try:
        if not obj_path.exists():
            raise FileNotFoundError(f"Input file not found: {obj_path}")

        vertices = parse_vertices_from_obj(obj_path)
        if not vertices:
            raise ValueError("No vertices found in the OBJ file (no lines starting with 'v ').")

        brushes = chunk_vertices_as_brushes(vertices, size=8)
        if not brushes:
            raise ValueError(
                "No complete brushes were detected. The converter expects groups of 8 vertex lines per brush."
            )

        instances = []
        for brush in brushes:
            (_, _, _center, extents) = bbox_of_points(brush)
            center_x, center_y, center_z = _center
            width, height, depth = extents

            # Note the coordinate mapping kept from v0.0.1: y<-z, z<-y for the instance placement
            instance = {
                "name": name or "model_collision",
                "persistentUuid": str(uuid.uuid4()),
                "customSize": True,
                "x": center_x,
                "y": center_z,  # swap
                "z": center_y,  # swap
                "width": width,
                "height": height,
                "depth": depth,
                "layer": layer or "",
                "rotationX": 0,
                "rotationY": 0,
                "angle": 0,
                "zOrder": 1,
                "numberProperties": [],
                "stringProperties": [],
                "initialVariables": [],
            }
            if lock:
                instance["locked"] = True

            instances.append(instance)

        generated_json_content = {"instances": instances}

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(generated_json_content, f, indent=4)

        log_message(f"JSON saved to {json_path}")
        if copy_button is not None:
            copy_button.config(state=tk.NORMAL)
        messagebox.showinfo("Success", f"JSON file saved to:\n{json_path}")
    except Exception as e:
        log_message("Error: " + str(e))
        # Also dump traceback to stdout for debugging when launched from console
        traceback.print_exc()
        try:
            messagebox.showerror("Error", str(e))
        except Exception:
            # If Tk is not ready, print
            print("Fatal error (no messagebox):", e)


def select_file(obj_path_var: tk.StringVar, json_path_var: tk.StringVar):
    """Opens a file dialog to select an .obj file and sets the output path automatically."""
    path = filedialog.askopenfilename(title="Select .obj File", filetypes=[("OBJ Files", "*.obj")])
    if path:
        obj_path_var.set(path)
        json_path_var.set(str(Path(path).with_suffix(".json")))


def convert(obj_path_var, json_path_var, name_var, layer_var, lock_var):
    """Triggers the conversion process and validates input fields."""
    obj = obj_path_var.get().strip()
    json_f = json_path_var.get().strip()
    name = (name_var.get() or "model_collision").strip()
    layer = (layer_var.get() or "").strip()
    lock = bool(lock_var.get())

    if not obj or not json_f:
        log_message("Warning: Missing file paths.")
        messagebox.showwarning("Warning", "Select input and output file paths.")
        return

    log_message(f"Converting {obj}...")
    obj_to_json(Path(obj), Path(json_f), name, layer, lock)


def copy_json():
    """Copies the generated JSON content to the clipboard."""
    if generated_json_content:
        try:
            app.clipboard_clear()
            app.clipboard_append(json.dumps(generated_json_content, indent=4))
            app.update()
            log_message("JSON copied to clipboard.")
        except Exception as e:
            log_message(f"Clipboard error: {e}")
            messagebox.showerror("Clipboard error", str(e))
    else:
        messagebox.showinfo("Info", "No JSON generated yet.")


def main():
    global app, log_text, copy_button

    app = tk.Tk()
    app.title(f"OBJ to JSON Converter - {VERSION}")

    # Variables bound to this app
    obj_path_var = tk.StringVar(master=app)
    json_path_var = tk.StringVar(master=app)
    name_var = tk.StringVar(master=app, value="model_collision")
    layer_var = tk.StringVar(master=app, value="")
    lock_var = tk.BooleanVar(master=app, value=False)

    # GUI Elements
    tk.Label(app, text="Select .obj File:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(app, textvariable=obj_path_var, width=50).grid(row=0, column=1, padx=10, pady=5)
    tk.Button(app, text="Browse", command=lambda: select_file(obj_path_var, json_path_var)).grid(row=0, column=2, padx=10, pady=5)

    tk.Label(app, text="Output .json Path:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(app, textvariable=json_path_var, width=50).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(app, text="Name:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(app, textvariable=name_var, width=50).grid(row=2, column=1, padx=10, pady=5)

    tk.Label(app, text="Layer:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(app, textvariable=layer_var, width=50).grid(row=3, column=1, padx=10, pady=5)

    tk.Checkbutton(app, text="Lock Objects in Editor", variable=lock_var).grid(row=4, column=1, sticky="w", padx=10, pady=5)

    tk.Button(app, text="Convert", command=lambda: convert(obj_path_var, json_path_var, name_var, layer_var, lock_var), width=20).grid(row=5, column=0, columnspan=3, pady=10)

    copy_button = tk.Button(app, text="Copy JSON to Clipboard", command=copy_json, width=20, state=tk.DISABLED)
    copy_button.grid(row=6, column=0, columnspan=3, pady=10)

    # Log Window
    tk.Label(app, text="Log:").grid(row=7, column=0, padx=10, pady=5, sticky="nw")
    log_text = tk.Text(app, height=10, width=80)
    log_text.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

    # Initial note
    log_message("Ready. Note: this tool assumes every 8 vertex lines define a brush (axis-aligned box).")

    app.mainloop()


if __name__ == "__main__":
    # If launched by double-click, we still get friendly errors.
    try:
        main()
    except Exception as e:
        # Last-resort error dialog so the user isn't left with a silent crash.
        try:
            messagebox.showerror("Fatal Error", f"{e}\n\n{traceback.format_exc()}")
        except Exception:
            print("Fatal Error:", e)
            traceback.print_exc()
