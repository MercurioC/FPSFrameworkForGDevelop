"""
OBJ to JSON Converter - v0.0.1

This program converts a 3D model in .obj format into a structured JSON format.
It extracts vertex data from the .obj file, calculates the bounding box, 
center, and formats the output as JSON for use in external applications.

Features:
- GUI for selecting .obj files and specifying output paths.
- Computes width, height, depth, and centroid.
- Allows setting a custom name and layer.
- Provides an option to lock objects in the editor.
- Log window for tracking process status.
"""

import json
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import datetime

VERSION = "v0.0.1"

generated_json_content = None

def obj_to_json(obj_path, json_path, name, layer, lock):
    """Parses the .obj file and converts its data into a JSON format."""
    global generated_json_content
    vertices, instances = [], []
    try:
        with open(obj_path, 'r') as file:
            vertices = [list(map(float, line.split()[1:4])) for line in file if line.startswith('v ')]
        for i in range(0, len(vertices), 8):
            brush = np.array(vertices[i:i+8])
            if len(brush) < 8:
                log_message("Warning: Incomplete brush detected, skipping.")
                continue
            min_vals, max_vals = brush.min(axis=0), brush.max(axis=0)
            center = (min_vals + max_vals) / 2
            width, depth, height = max_vals - min_vals
            instance = {
                "name": name, "persistentUuid": str(uuid.uuid4()), "customSize": True,
                "x": center[0], "y": center[2], "z": center[1], "width": width,
                "height": height, "depth": depth, "layer": layer,
                "rotationX": 0, "rotationY": 0, "angle": 0, "zOrder": 1,
                "numberProperties": [], "stringProperties": [], "initialVariables": []
            }
            if lock:
                instance["locked"] = True
            instances.append(instance)
        generated_json_content = {"instances": instances}
        with open(json_path, 'w') as file:
            json.dump(generated_json_content, file, indent=4)
        log_message(f"JSON saved to {json_path}")
        copy_button.config(state=tk.NORMAL)
        messagebox.showinfo("Success", f"JSON file saved to:\n{json_path}")
    except Exception as e:
        log_message(f"Error: {e}")
        messagebox.showerror("Error", str(e))

def select_file():
    """Opens a file dialog to select an .obj file and sets the output path automatically."""
    path = filedialog.askopenfilename(title="Select .obj File", filetypes=[("OBJ Files", "*.obj")])
    if path:
        obj_path.set(path)
        json_path.set(path.rsplit('.', 1)[0] + ".json")

def log_message(msg):
    """Logs messages in the GUI log window."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
    log_text.see(tk.END)

def convert():
    """Triggers the conversion process and validates input fields."""
    obj, json_f, name, layer, lock = obj_path.get(), json_path.get(), name_var.get() or "model_collision", layer_var.get() or "", lock_var.get()
    if not obj or not json_f:
        log_message("Warning: Missing file paths.")
        messagebox.showwarning("Warning", "Select input and output file paths.")
        return
    log_message(f"Converting {obj}...")
    obj_to_json(obj, json_f, name, layer, lock)

def copy_json():
    """Copies the generated JSON content to the clipboard."""
    if generated_json_content:
        app.clipboard_clear()
        app.clipboard_append(json.dumps(generated_json_content, indent=4))
        app.update()
        log_message("JSON copied to clipboard.")

# GUI Setup
app = tk.Tk()
app.title(f"OBJ to JSON Converter - {VERSION}")

# Variables
obj_path, json_path, name_var, layer_var, lock_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.BooleanVar()

# GUI Elements
tk.Label(app, text="Select .obj File:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
tk.Entry(app, textvariable=obj_path, width=50).grid(row=0, column=1, padx=10, pady=5)
tk.Button(app, text="Browse", command=select_file).grid(row=0, column=2, padx=10, pady=5)

tk.Label(app, text="Output .json Path:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
tk.Entry(app, textvariable=json_path, width=50).grid(row=1, column=1, padx=10, pady=5)

tk.Label(app, text="Name:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
tk.Entry(app, textvariable=name_var, width=50).grid(row=2, column=1, padx=10, pady=5)

tk.Label(app, text="Layer:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
tk.Entry(app, textvariable=layer_var, width=50).grid(row=3, column=1, padx=10, pady=5)

tk.Checkbutton(app, text="Lock Objects in Editor", variable=lock_var).grid(row=4, column=1, sticky="w", padx=10, pady=5)

tk.Button(app, text="Convert", command=convert, width=20).grid(row=5, column=0, columnspan=3, pady=10)

copy_button = tk.Button(app, text="Copy JSON to Clipboard", command=copy_json, width=20, state=tk.DISABLED)
copy_button.grid(row=6, column=0, columnspan=3, pady=10)

# Log Window
tk.Label(app, text="Log:").grid(row=7, column=0, padx=10, pady=5, sticky="nw")
log_text = tk.Text(app, height=10, width=80)
log_text.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

app.mainloop()
