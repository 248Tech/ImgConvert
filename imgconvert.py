"""ImgConvert - small local GUI to batch-convert images between formats."""

import base64
import os
import subprocess
import sys
import tempfile
import tkinter as tk
import winreg
from tkinter import filedialog, font, messagebox, ttk

from PIL import Image, ImageOps

import pillow_heif

pillow_heif.register_heif_opener()

# Public half of the self-signed cert this exe is signed with (no private key -
# safe to embed). "Trust This App" imports it into this Windows account's
# Trusted Root + Trusted Publishers stores so SmartScreen stops flagging any
# build signed with the matching private key, on this machine, going forward.
SIGNING_CERT_B64 = (
    "MIIDRDCCAiygAwIBAgIQMayp7qJWzJ9IfH+6kmORRTANBgkqhkiG9w0BAQsFADA6MRMwEQYDVQQKDApJbWdDb252ZXJ0MSMw"
    "IQYDVQQDDBpJbWdDb252ZXJ0IExvY2FsIFB1Ymxpc2hlcjAeFw0yNjA4MzExODU1MTFaFw0zNjA4MzExOTA1MTFaMDoxEzAR"
    "BgNVBAoMCkltZ0NvbnZlcnQxIzAhBgNVBAMMGkltZ0NvbnZlcnQgTG9jYWwgUHVibGlzaGVyMIIBIjANBgkqhkiG9w0BAQEF"
    "AAOCAQ8AMIIBCgKCAQEAu1vHHCeWbG9nHyGtAP0NXaieH15ZCvPHqhCDrbNh6a4wKB2e12bFefpdB/GyzgtHmejrem8ktXbk"
    "hDmVpRYlj9IKvIKfsg3pE7zNxO44u3TTGnQRuxNBfUp2hubi1s2rZUprAxxAjc/uX2IyN0tMq3VsxoUJXMrBSc60w+LA4WJ0"
    "NS9CHLbCs4NhygX5I+rw3+9EjNMh3MZTLACUI/Wjxj5qhv6ut7iZoXqBU/btZ+qvOrst30d8mI2LRhD9vyvcyaiLRLvB1HXx"
    "/Oh4vl+9Wm68y8vBKekD4JngDKyUJSlo8wC8d07vo+3tGRyc68PATs1ZUuNtZz7FHk+3vYIy0QIDAQABo0YwRDAOBgNVHQ8B"
    "Af8EBAMCB4AwEwYDVR0lBAwwCgYIKwYBBQUHAwMwHQYDVR0OBBYEFLqEQD3DmExz2hCJfk6IgyeZNAE3MA0GCSqGSIb3DQEB"
    "CwUAA4IBAQCz+n0HF2VpYuh/rgCmDhkoAn+ougR7p9JV6pBP/VrAaffodf/Onnk+TZ7hFcL6/aFuDrjWiZdzrfpnn0VGW/6T"
    "Jua7oOBpolDCPMD14KUVnkS+KEc75yXwYjbsWPbj1QTpIKnGwFLUxt9PiUHW6482xd8nJBk7Lj1+mi6zDT5/IQErfI614Mpf"
    "ANK1ov0BxTGfiDT55IsbShb5XvL4E1T4bnEWoV0X54PiyQeIZX5k1sgtyRyywUSZ/pRBMwwp+W9mGFTgHU6ErlehQetO2+wr"
    "FnxF447snVTIesU4F5x+MFFSd3EyZcIJecFUwAzR3QsxLJgWsqjCYHLs3Y9JD3yx"
)

NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def trust_signing_cert():
    """Import the bundled public cert into CurrentUser's Root + TrustedPublisher
    stores via certutil, so Windows stops flagging apps signed with it. Runs
    fully unattended (no cert-install UI prompt) since certutil -addstore is
    non-interactive. Returns (ok, message)."""
    cert_bytes = base64.b64decode(SIGNING_CERT_B64)
    with tempfile.NamedTemporaryFile(suffix=".cer", delete=False) as f:
        f.write(cert_bytes)
        cer_path = f.name

    try:
        for store in ("Root", "TrustedPublisher"):
            result = subprocess.run(
                ["certutil", "-user", "-addstore", store, cer_path],
                capture_output=True,
                text=True,
                creationflags=NO_WINDOW,
            )
            if result.returncode != 0:
                return False, f"certutil failed adding to {store}:\n{result.stdout}\n{result.stderr}"
        return True, "Trusted. Future launches of this app (and rebuilds signed with the same key) won't be flagged by Windows on this account."
    finally:
        os.unlink(cer_path)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False

SUPPORTED_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}

FORMAT_INFO = {
    "JPEG": {"ext": ".jpg", "pil_format": "JPEG"},
    "PNG": {"ext": ".png", "pil_format": "PNG"},
    "WEBP": {"ext": ".webp", "pil_format": "WEBP"},
    "GIF": {"ext": ".gif", "pil_format": "GIF"},
    "HEIC": {"ext": ".heic", "pil_format": "HEIF"},
    "TIFF": {"ext": ".tiff", "pil_format": "TIFF"},
}
FORMATS = list(FORMAT_INFO.keys())

CONTEXT_MENU_KEY = "ImgConvert"


def _self_command_prefix():
    """Command-line prefix that re-invokes this same app (frozen exe or dev script)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, os.path.abspath(__file__)]


def _delete_key_recursive(root, path):
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    with key:
        while True:
            try:
                subkey_name = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_key_recursive(root, f"{path}\\{subkey_name}")
    winreg.DeleteKey(root, path)


def install_context_menu():
    """Add a 'Convert To' submenu (one entry per format) to the Explorer right-click
    menu for supported image extensions. Writes under HKCU so no admin rights are
    needed. Each entry re-invokes this exe with --convert-to and outputs next to
    the source file."""
    prefix = " ".join(f'"{p}"' for p in _self_command_prefix())
    exe_for_icon = _self_command_prefix()[0]

    for ext in sorted(SUPPORTED_EXTS):
        base = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{CONTEXT_MENU_KEY}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "Convert To")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_for_icon}"')
            # Required so Explorer treats this as a cascading flyout rather than
            # trying to run the parent key itself as a command.
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")

        for i, fmt in enumerate(FORMATS, start=1):
            sub = f"{base}\\shell\\{i:02d}_{fmt}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub) as subkey:
                winreg.SetValueEx(subkey, None, 0, winreg.REG_SZ, fmt)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{sub}\\command") as cmdkey:
                winreg.SetValueEx(cmdkey, None, 0, winreg.REG_SZ, f'{prefix} --convert-to {fmt} "%1"')

    return True, f"Added 'Convert To' to the right-click menu for {len(SUPPORTED_EXTS)} image file types."


def uninstall_context_menu():
    for ext in sorted(SUPPORTED_EXTS):
        base = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{CONTEXT_MENU_KEY}"
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, base)
    return True, "Removed 'Convert To' from the right-click menu."


def cli_convert(argv):
    """Entry point when launched from the Explorer 'Convert To' menu:
    <exe> --convert-to FORMAT <file1> [file2 ...]. Converts each file into its
    own folder (same folder it was found in) and exits without opening the GUI."""
    idx = argv.index("--convert-to")
    target_format = argv[idx + 1].upper()
    file_paths = argv[idx + 2 :]

    errors = []
    if target_format not in FORMAT_INFO:
        errors.append(f"Unknown format: {target_format}")
    else:
        for path in file_paths:
            try:
                convert_file(path, os.path.dirname(path) or ".", target_format)
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

    if errors:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ImgConvert", "\n".join(errors))
        root.destroy()

# Formats with no (or limited) alpha support - flatten onto white/RGB first.
FLATTEN_FORMATS = {"JPEG"}
# Formats that need a palette-mode image rather than full RGB(A).
PALETTE_FORMATS = {"GIF"}


def collect_image_files(paths):
    files = []
    for path in paths:
        if os.path.isdir(path):
            for root, _dirs, names in os.walk(path):
                for name in names:
                    if os.path.splitext(name)[1].lower() in SUPPORTED_EXTS:
                        files.append(os.path.join(root, name))
        elif os.path.splitext(path)[1].lower() in SUPPORTED_EXTS:
            files.append(path)
    return files


def unique_destination(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"


def convert_file(src_path, out_dir, target_format):
    info = FORMAT_INFO[target_format]
    stem = os.path.splitext(os.path.basename(src_path))[0]
    dest_path = unique_destination(os.path.join(out_dir, stem + info["ext"]))

    img = Image.open(src_path)

    try:
        # Cameras/phones store rotation as an EXIF tag rather than rotating
        # pixels; bake it in now so the saved file looks right regardless of
        # whether the target format even supports EXIF.
        img = ImageOps.exif_transpose(img)
        if target_format in FLATTEN_FORMATS and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA").convert("RGB")
        elif target_format in PALETTE_FORMATS:
            img = img.convert("RGBA").convert("P", palette=Image.ADAPTIVE)
        else:
            img = img.convert(img.mode)
        img.save(dest_path, format=info["pil_format"])
    finally:
        img.close()

    return dest_path


PALETTES = {
    "dark": {
        "bg": "#1e1f22",
        "card_bg": "#2b2d31",
        "entry_bg": "#232428",
        "border": "#3f4147",
        "text_primary": "#e3e3e3",
        "text_muted": "#9aa0a6",
        "accent": "#4f8cff",
        "accent_active": "#3f74d1",
        "accent_disabled": "#375079",
    },
    "light": {
        "bg": "#f3f3f3",
        "card_bg": "#ffffff",
        "entry_bg": "#ffffff",
        "border": "#d6d6d6",
        "text_primary": "#1a1a1a",
        "text_muted": "#666666",
        "accent": "#2f6fed",
        "accent_active": "#2559c4",
        "accent_disabled": "#9db6f2",
    },
}


class ImgConvertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ImgConvert")
        self.root.geometry("600x560")
        self.root.minsize(520, 480)

        self.queued_files = []
        self.output_dir = tk.StringVar()
        self.theme_name = "dark"
        self.palette = PALETTES[self.theme_name]

        self._setup_style()
        self._build_ui()
        self._apply_theme()

    def _setup_style(self):
        style = ttk.Style(self.root)
        # "clam" is a fully themeable ttk theme - unlike "vista", it actually
        # honors custom colors, which native/OS themes mostly ignore. Needed
        # so the light/dark toggle can actually recolor every widget.
        style.theme_use("clam")

        base_font = font.nametofont("TkDefaultFont")
        base_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", base_font)

    def _apply_theme(self):
        p = self.palette
        style = ttk.Style(self.root)

        self.root.configure(bg=p["bg"])

        style.configure("TFrame", background=p["bg"])
        style.configure("Card.TFrame", background=p["card_bg"])
        style.configure("TLabel", background=p["bg"], foreground=p["text_primary"])
        style.configure("Muted.TLabel", background=p["bg"], foreground=p["text_muted"])
        style.configure(
            "Heading.TLabel",
            background=p["bg"],
            foreground=p["text_primary"],
            font=("Segoe UI Semibold", 15),
        )
        style.configure("Card.TLabel", background=p["card_bg"], foreground=p["text_primary"])

        style.configure(
            "TButton", padding=6, background=p["card_bg"], foreground=p["text_primary"], borderwidth=0
        )
        style.map("TButton", background=[("active", p["border"])])

        style.configure(
            "Accent.TButton",
            padding=8,
            font=("Segoe UI Semibold", 10),
            background=p["accent"],
            foreground="white",
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", p["accent_active"]), ("disabled", p["accent_disabled"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground=p["entry_bg"],
            background=p["entry_bg"],
            foreground=p["text_primary"],
            arrowcolor=p["text_primary"],
            borderwidth=0,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", p["entry_bg"])],
            foreground=[("readonly", p["text_primary"])],
        )
        self.root.option_add("*TCombobox*Listbox.background", p["entry_bg"])
        self.root.option_add("*TCombobox*Listbox.foreground", p["text_primary"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

        style.configure(
            "TEntry",
            fieldbackground=p["entry_bg"],
            foreground=p["text_primary"],
            insertcolor=p["text_primary"],
            borderwidth=0,
        )

        style.configure(
            "TProgressbar", thickness=10, background=p["accent"], troughcolor=p["entry_bg"], borderwidth=0
        )

        # Raw tk widgets (Listbox/Text/card Frames) don't use ttk styles, so
        # they need their colors set directly.
        self.drop_card.configure(bg=p["card_bg"], highlightbackground=p["border"])
        self.listbox.configure(
            bg=p["card_bg"], fg=p["text_primary"], selectbackground=p["accent"], selectforeground="white"
        )
        self.status_card.configure(bg=p["card_bg"], highlightbackground=p["border"])
        self.status.configure(bg=p["card_bg"], fg=p["text_primary"], insertbackground=p["text_primary"])

        self.theme_btn.configure(text=self._theme_btn_label())

    def _theme_btn_label(self):
        return "☀ Light mode" if self.theme_name == "dark" else "☾ Dark mode"

    def _toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.palette = PALETTES[self.theme_name]
        self._apply_theme()

    def _trust_app(self):
        ok, message = trust_signing_cert()
        if ok:
            messagebox.showinfo("Trust This App", message)
        else:
            messagebox.showerror("Trust This App", message)

    def _install_context_menu(self):
        try:
            ok, message = install_context_menu()
            messagebox.showinfo("Right-Click Menu", message)
        except OSError as exc:
            messagebox.showerror("Right-Click Menu", f"Failed to add menu: {exc}")

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="ImgConvert", style="Heading.TLabel").pack(side="left")
        self.theme_btn = ttk.Button(header, text="", command=self._toggle_theme)
        self.theme_btn.pack(side="right")
        ttk.Button(header, text="Trust This App", command=self._trust_app).pack(side="right", padx=(0, 6))
        ttk.Button(
            header, text="Add Right-Click Menu", command=self._install_context_menu
        ).pack(side="right", padx=(0, 6))

        ttk.Label(
            outer,
            text="Drag files/folders below, or use Add"
            if HAS_DND
            else "Use Add Files / Add Folder below",
            style="Muted.TLabel",
        ).pack(fill="x", pady=(10, 2))

        self.drop_card = tk.Frame(outer, highlightthickness=1)
        self.drop_card.pack(fill="both", expand=True, pady=(0, 10))

        self.listbox = tk.Listbox(
            self.drop_card,
            bd=0,
            highlightthickness=0,
            activestyle="none",
        )
        self.listbox.pack(fill="both", expand=True, padx=1, pady=1)

        if HAS_DND:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Add Files...", command=self._add_files).pack(side="left")
        ttk.Button(btn_frame, text="Add Folder...", command=self._add_folder).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Clear", command=self._clear).pack(side="left")

        ttk.Label(outer, text="Or paste a file/folder path", style="Muted.TLabel").pack(
            fill="x", pady=(10, 2)
        )
        path_frame = ttk.Frame(outer)
        path_frame.pack(fill="x")
        path_frame.columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        path_entry.grid(row=0, column=0, sticky="we")
        path_entry.bind("<Return>", self._add_path_from_entry)
        ttk.Button(path_frame, text="Add Path", command=self._add_path_from_entry).grid(
            row=0, column=1, padx=(6, 0)
        )

        options_frame = ttk.Frame(outer)
        options_frame.pack(fill="x", pady=(16, 0))
        options_frame.columnconfigure(1, weight=1)

        ttk.Label(options_frame, text="Convert to").grid(row=0, column=0, sticky="w")
        self.format_var = tk.StringVar(value=FORMATS[0])
        ttk.Combobox(
            options_frame, textvariable=self.format_var, values=FORMATS, state="readonly", width=10
        ).grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(options_frame, text="Output folder").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(options_frame, textvariable=self.output_dir).grid(
            row=1, column=1, sticky="we", padx=8, pady=(10, 0)
        )
        ttk.Button(options_frame, text="Browse...", command=self._pick_output_dir).grid(
            row=1, column=2, pady=(10, 0)
        )

        ttk.Button(outer, text="Convert", command=self._convert_all, style="Accent.TButton").pack(
            fill="x", pady=(16, 8)
        )

        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        self.status_card = tk.Frame(outer, highlightthickness=1)
        self.status_card.pack(fill="both", expand=False)
        self.status = tk.Text(
            self.status_card,
            height=6,
            state="disabled",
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=6,
        )
        self.status.pack(fill="both", expand=True, padx=1, pady=1)

    def _on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        self._add_paths(paths)

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select images")
        if paths:
            self._add_paths(paths)

    def _add_folder(self):
        path = filedialog.askdirectory(title="Select folder")
        if path:
            self._add_paths([path])

    def _add_paths(self, paths):
        new_files = collect_image_files(paths)
        added = 0
        for f in new_files:
            if f not in self.queued_files:
                self.queued_files.append(f)
                self.listbox.insert("end", f)
                added += 1

        if not self.output_dir.get() and self.queued_files:
            first_dir = os.path.dirname(self.queued_files[0])
            self.output_dir.set(os.path.join(first_dir, "converted"))

        self._log(f"Added {added} file(s). Queue: {len(self.queued_files)} file(s).")

    def _add_path_from_entry(self, event=None):
        path = self.path_var.get().strip().strip('"')
        if not path:
            return
        if not os.path.exists(path):
            self._log(f"Path not found: {path}")
            return
        self._add_paths([path])
        self.path_var.set("")

    def _clear(self):
        self.queued_files = []
        self.listbox.delete(0, "end")

    def _pick_output_dir(self):
        current = self.output_dir.get().strip()
        if current and os.path.isdir(current):
            initial_dir = current
        elif current and os.path.isdir(os.path.dirname(current)):
            initial_dir = os.path.dirname(current)
        elif self.queued_files:
            initial_dir = os.path.dirname(self.queued_files[0])
        else:
            initial_dir = os.getcwd()

        path = filedialog.askdirectory(title="Select output folder", initialdir=initial_dir)
        if path:
            self.output_dir.set(path)

    def _log(self, message):
        self.status.configure(state="normal")
        self.status.insert("end", message + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def _convert_all(self):
        if not self.queued_files:
            self._log("No files queued.")
            return

        out_dir = self.output_dir.get().strip()
        if not out_dir:
            self._log("Pick an output folder first.")
            return
        os.makedirs(out_dir, exist_ok=True)

        target_format = self.format_var.get()
        total = len(self.queued_files)
        ok_count = 0
        err_count = 0

        self.progress.configure(maximum=total, value=0)

        for i, src in enumerate(self.queued_files, start=1):
            try:
                dest = convert_file(src, out_dir, target_format)
                self._log(f"[{i}/{total}] OK: {os.path.basename(src)} -> {os.path.basename(dest)}")
                ok_count += 1
            except Exception as exc:
                self._log(f"[{i}/{total}] FAILED: {os.path.basename(src)} ({exc})")
                err_count += 1
            self.progress.configure(value=i)
            self.root.update_idletasks()

        self._log(f"Done. {ok_count} converted, {err_count} failed.")


def main():
    if "--convert-to" in sys.argv:
        cli_convert(sys.argv)
        return
    if "--install-context-menu" in sys.argv:
        install_context_menu()
        return
    if "--uninstall-context-menu" in sys.argv:
        uninstall_context_menu()
        return

    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    ImgConvertApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
