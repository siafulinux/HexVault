#!/usr/bin/env python3

"""
HexVault | Digital File Recovery
=================================

Lightweight Tkinter frontend for PhotoRec on Linux.

Design goals: 
- Deleted-file recovery only: PhotoRec FREE SPACE mode is hard-coded.
- One authorization prompt per recovery job.
- Mounted and unmounted source partitions are supported.
- Mounted source partitions are unmounted by the single privileged helper.
- Tabbed layout for organized configuration and monitoring.
- Process pause / resume support (SIGSTOP / SIGCONT via privileged helper).
- Clean, informative status logs explaining file carving & staging pipelines.
- Standalone execution with zero third-party Python dependencies.
"""

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


APP_NAME = "HexVault"
APP_TITLE = "HexVault | Digital File Recovery"

DEFAULT_RECOVERY_DIR = os.path.expanduser("~/hexvault")
HEXVAULT_RUNTIME_DIR = "/tmp/hexvault"


# ---------------------------------------------------------------------------
# Path Helper for Assets
# ---------------------------------------------------------------------------

def get_asset_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "assets", filename),
        os.path.join(script_dir, filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


# ---------------------------------------------------------------------------
# Custom Colored Checkbutton for Selection Indication
# ---------------------------------------------------------------------------

class CustomCheckbutton(tk.Canvas):
    def __init__(self, parent, text, variable, command=None, bg_color="#202124", fg_color="#eeeeee", width=110, **kwargs):
        super().__init__(parent, height=24, width=width, bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        self.variable = variable
        self.command = command
        self.text = text
        self.bg_color = bg_color
        self.fg_color = fg_color

        self.box_size = 14
        self.margin = 4

        self.bind("<Button-1>", self._toggle)

        # Trace variable changes to re-draw when updated programmatically
        self.var_trace = self.variable.trace_add("write", lambda *args: self.redraw())
        self.redraw()

    def set_colors(self, bg_color, fg_color):
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.configure(bg=bg_color)
        self.redraw()

    def _toggle(self, event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def redraw(self):
        self.delete("all")
        is_selected = self.variable.get()

        outline_color = "#ff3333" if is_selected else self.fg_color
        fill_color = "#ff3333" if is_selected else self.bg_color

        x0 = self.margin
        y0 = (24 - self.box_size) // 2
        x1 = x0 + self.box_size
        y1 = y0 + self.box_size

        self.create_rectangle(x0, y0, x1, y1, outline=outline_color, fill=fill_color, width=2)

        if is_selected:
            self.create_line(x0 + 3, y0 + 7, x0 + 6, y0 + 10, fill="#ffffff", width=2)
            self.create_line(x0 + 6, y0 + 10, x0 + 11, y0 + 3, fill="#ffffff", width=2)

        self.create_text(x1 + 8, 12, text=self.text, anchor="w", fill=self.fg_color, font=("TkDefaultFont", 9))


# ---------------------------------------------------------------------------
# File types -> PhotoRec file families
# ---------------------------------------------------------------------------

FILE_TYPES = {
    "Images": {
        "jpg": "jpg",
        "jpeg": "jpg",
        "png": "png",
        "gif": "gif",
        "bmp": "bmp",
        "tif": "tif",
        "tiff": "tif",
        "cr2": "tif",
        "crw": "crw",
        "nef": "tif",
        "orf": "orf",
        "raf": "raf",
        "pef": "tif",
        "dcr": "tif",
        "sr2": "tif",
        "x3f": "x3f",
    },
    "Video": {
        "mp4": "mov",
        "mov": "mov",
        "m4v": "mov",
        "3gp": "mov",
        "mpg": "mpg",
        "mpeg": "mpg",
        "m2ts": "m2ts",
        "mts": "m2ts",
        "avi": "riff",
        "flv": "flv",
        "wmv": "asf",
        "asf": "asf",
    },
    "Audio": {
        "mp3": "mp3",
        "wav": "riff",
        "wma": "asf",
        "ogg": "ogg",
        "flac": "flac",
        "m4a": "mov",
    },
    "Documents": {
        "pdf": "pdf",
        "doc": "doc",
        "docx": "zip",
        "xls": "doc",
        "xlsx": "zip",
        "ppt": "doc",
        "pptx": "zip",
        "txt": "txt",
        "rtf": "rtf",
        "html": "txt",
        "htm": "txt",
    },
    "Archives": {
        "zip": "zip",
        "rar": "rar",
        "7z": "7z",
        "tar": "tar",
        "gz": "gz",
        "bz2": "bz2",
        "xz": "xz",
        "iso": "iso",
    },
    "Databases": {
        "sqlite": "sqlite",
        "sqlite3": "sqlite",
    },
}


DEFAULT_SELECTED = {
    "jpg", "jpeg", "png", "bmp", "tif",
    "mp4", "mov", "avi", "mpg", "mpeg",
    "mp3", "wav", "wma",
    "pdf", "doc", "docx", "txt", "xls", "xlsx", "ppt", "pptx",
    "zip", "rar", "7z",
    "sqlite",
}


CATEGORY_DIRS = {
    "Images": "images",
    "Video": "video",
    "Audio": "audio",
    "Documents": "documents",
    "Archives": "archives",
    "Databases": "databases",
}

DEFAULT_MIN_SIZE = {
    "Images": "100 KB",
    "Video": "1 MB",
    "Audio": "100 KB",
    "Documents": "10 KB",
    "Archives": "10 KB",
    "Databases": "10 KB",
}

SIZE_CHOICES = [
    "No minimum", "1 KB", "5 KB", "10 KB", "25 KB", "50 KB", "100 KB",
    "250 KB", "500 KB", "1 MB", "2 MB", "5 MB", "10 MB", "25 MB", "50 MB",
    "100 MB", "250 MB", "500 MB", "1 GB",
]

DEFAULT_MIN_DIMENSIONS = "No minimum"

DIMENSION_CHOICES = [
    "No minimum", "160x120", "200x200", "320x240", "640x480", "800x600",
    "1024x768", "1280x720", "1920x1080",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def human_size(value):
    try:
        size = float(value)
    except Exception:
        return str(value)

    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return str(value)

def format_time(seconds):
    try:
        seconds = int(seconds)
    except ValueError:
        return "Calculating..."
        
    if seconds < 0 or seconds > 864000:
        return "Calculating..."
        
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    
    if hours > 0:
        return f"{hours}h {mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"

def run_command(command, timeout=5):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.returncode, result.stdout, result.stderr)
    except Exception as exc:
        return (-1, "", str(exc))


def command_exists(name):
    return shutil.which(name) is not None


def find_photorec():
    candidates = [
        shutil.which("photorec"),
        shutil.which("photorec_static"),
    ]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        os.path.join(script_dir, "photorec"),
        os.path.join(script_dir, "photorec_static"),
    ])

    for candidate in candidates:
        if (
            candidate
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            return os.path.abspath(candidate)
    return None


def photorec_version(path):
    if not path:
        return "Not found"
    code, stdout, stderr = run_command([path, "/version"], timeout=3)
    text = (stdout + "\n" + stderr).strip()
    match = re.search(r"PhotoRec\s+([\d.]+)", text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"


def discover_disks():
    if not command_exists("lsblk"):
        raise RuntimeError("The 'lsblk' command was not found.")

    code, stdout, stderr = run_command(
        ["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,PATH"],
        timeout=5,
    )

    if code != 0:
        raise RuntimeError(stderr.strip() or "lsblk failed.")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse lsblk output: {exc}")

    disks = []
    for item in data.get("blockdevices", []):
        if item.get("type") != "disk":
            continue

        path = item.get("path") or f"/dev/{item.get('name', '')}"
        try:
            size = int(item.get("size") or 0)
        except Exception:
            size = 0

        if size <= 0:
            continue

        partitions = []
        for child in (item.get("children") or []):
            if child.get("type") != "part":
                continue

            child_path = child.get("path") or f"/dev/{child.get('name', '')}"
            try:
                child_size = int(child.get("size") or 0)
            except Exception:
                child_size = 0

            mounts = child.get("mountpoints") or []
            if isinstance(mounts, str):
                mounts = [mounts]
            mounts = [m for m in mounts if m]

            partitions.append({
                "name": child.get("name", ""),
                "path": child_path,
                "size": child_size,
                "fstype": child.get("fstype") or "",
                "label": child.get("label") or "",
                "mountpoints": mounts,
            })

        disks.append({
            "name": item.get("name", ""),
            "path": path,
            "size": size,
            "partitions": partitions,
        })

    return disks


def shell_escape(value):
    if not any(ch in value for ch in (" ", "\t", "\n", "'", '"', "$", "`", "\\")):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def get_actual_user_ids():
    uid = None
    gid = None

    for env_name in ("SUDO_UID", "PKEXEC_UID"):
        value = os.environ.get(env_name)
        if value:
            try:
                candidate = int(value)
                if candidate > 0:
                    uid = candidate
                    break
            except ValueError:
                pass

    if uid is None and os.geteuid() != 0:
        uid = os.getuid()

    for env_name in ("SUDO_GID",):
        value = os.environ.get(env_name)
        if value:
            try:
                candidate = int(value)
                if candidate >= 0:
                    gid = candidate
                    break
            except ValueError:
                pass

    if uid is None:
        uid = os.getuid()

    if gid is None:
        try:
            import pwd
            gid = pwd.getpwuid(uid).pw_gid
        except Exception:
            gid = os.getgid()

    return (uid, gid)


# ---------------------------------------------------------------------------
# Privileged Helper Template
# ---------------------------------------------------------------------------

ROOT_HELPER_SOURCE = r'''#!/usr/bin/env python3
import csv
import json
import os
import signal
import subprocess
import sys
import time
import shutil
import ctypes

STOP_REQUESTED = False
PAUSED = False
CURRENT_PHOTOREC = None


def arm_parent_death_signal():
    if sys.platform != "linux":
        return
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        PR_SET_PDEATHSIG = 1
        if libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0) != 0:
            return
        if os.getppid() == 1:
            os.kill(os.getpid(), signal.SIGTERM)
    except Exception:
        pass


def emit(text):
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:
        pass


def stop_signal(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True
    proc = CURRENT_PHOTOREC
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass


def requested_stop(stop_file):
    return STOP_REQUESTED or os.path.exists(stop_file)


def mountpoints(device):
    try:
        result = subprocess.run(
            ["findmnt", "-rn", "-S", device, "-o", "TARGET"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [x.strip() for x in result.stdout.splitlines() if x.strip()]


def get_partition_stats(device):
    try:
        result = subprocess.run(
            ["lsblk", "-b", "-n", "-o", "SIZE,FSTYPE", device],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            size = int(parts[0])
            fstype = parts[1] if len(parts) > 1 else ""
            
            free_bytes = size
            df_res = subprocess.run(
                ["df", "-B1", device],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=5,
            )
            if df_res.returncode == 0:
                lines = df_res.stdout.strip().splitlines()
                if len(lines) >= 2:
                    fields = lines[1].split()
                    if len(fields) >= 4:
                        try:
                            free_bytes = int(fields[3])
                        except ValueError:
                            pass
            return size, free_bytes, fstype
    except Exception:
        pass
    return 0, 0, ""


def unmount_device(device):
    mounts = mountpoints(device)
    if not mounts:
        emit("SOURCE_ALREADY_UNMOUNTED\n")
        return (True, [])

    emit("SOURCE_MOUNTS " + json.dumps(mounts) + "\n")
    emit("UNMOUNT_START\n")

    commands = []
    if os.path.exists("/usr/bin/udisksctl"):
        commands.append(["/usr/bin/udisksctl", "unmount", "-b", device])
    commands.append(["/bin/umount", device])

    last_error = ""
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=30,
            )
        except Exception as exc:
            last_error = str(exc)
            continue

        if result.returncode == 0:
            time.sleep(1)
            remaining = mountpoints(device)
            if not remaining:
                emit("UNMOUNT_OK\n")
                return (True, mounts)

        last_error = result.stderr.strip() or f"command exited with {result.returncode}"

    emit("UNMOUNT_FAILED " + last_error.replace("\n", " ") + "\n")
    return (False, mounts)


def remount_device(device):
    if not os.path.exists("/usr/bin/udisksctl"):
        emit("REMOUNT_UNAVAILABLE\n")
        return False

    emit("REMOUNT_START\n")
    try:
        result = subprocess.run(
            ["/usr/bin/udisksctl", "mount", "-b", device],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
    except Exception as exc:
        emit("REMOUNT_FAILED " + str(exc).replace("\n", " ") + "\n")
        return False

    time.sleep(1)
    if mountpoints(device):
        emit("REMOUNT_OK\n")
        return True

    error = result.stderr.strip() or "mount not confirmed"
    emit("REMOUNT_FAILED " + error.replace("\n", " ") + "\n")
    return False


def snapshot_files(path):
    found = set()
    if not os.path.isdir(path):
        return found
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                found.add(os.path.relpath(os.path.join(root, name), path))
            except Exception:
                pass
    return found


def count_files(path):
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, dirs, files in os.walk(path):
        total += len(files)
    return total


def parse_size_value(value):
    if not value:
        return 0
    text = str(value).strip().lower()
    if text in ("no minimum", "none", "0"):
        return 0

    import re
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(b|kb|mb|gb|tb)?$", text)
    if not match:
        return 0

    number = float(match.group(1))
    unit = match.group(2) or "b"
    return int(number * {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}[unit])


def parse_dimensions(value):
    if not value:
        return None
    text = str(value).strip().lower()
    if text in ("no minimum", "none", "0"):
        return None

    import re
    match = re.match(r"^([0-9]+)\s*x\s*([0-9]+)$", text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def jpeg_dimensions(path):
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            if f.read(1) != b"\xff":
                continue
            marker = f.read(1)
            if not marker:
                return None
            while marker == b"\xff":
                marker = f.read(1)
            if marker in (b"\xd8", b"\xd9", b"\x00"):
                continue
            data = f.read(2)
            if len(data) != 2:
                return None
            length = int.from_bytes(data, "big")
            if length < 2:
                return None
            code = marker[0]
            if (
                (0xC0 <= code <= 0xC3)
                or (0xC5 <= code <= 0xC7)
                or (0xC9 <= code <= 0xCB)
                or (0xCD <= code <= 0xCF)
            ):
                data = f.read(5)
                if len(data) != 5:
                    return None
                return (
                    int.from_bytes(data[3:5], "big"),
                    int.from_bytes(data[1:3], "big"),
                )
            f.seek(length - 2, 1)


def png_dimensions(path):
    with open(path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        data = f.read(8)
        if len(data) != 8 or data[4:8] != b"IHDR":
            return None
        if int.from_bytes(data[:4], "big") < 8:
            return None
        data = f.read(8)
        if len(data) != 8:
            return None
        return (
            int.from_bytes(data[:4], "big"),
            int.from_bytes(data[4:8], "big"),
        )


def bmp_dimensions(path):
    with open(path, "rb") as f:
        if f.read(2) != b"BM":
            return None
        f.seek(18)
        data = f.read(8)
        if len(data) != 8:
            return None
        return (
            abs(int.from_bytes(data[:4], "little", signed=True)),
            abs(int.from_bytes(data[4:8], "little", signed=True)),
        )


def tiff_dimensions(path):
    import struct
    with open(path, "rb") as f:
        order = f.read(2)
        if order == b"II":
            endian = "<"
        elif order == b"MM":
            endian = ">"
        else:
            return None

        if f.read(2) != struct.pack(endian + "H", 42):
            return None

        data = f.read(4)
        if len(data) != 4:
            return None

        offset = struct.unpack(endian + "I", data)[0]
        f.seek(offset)
        data = f.read(2)
        if len(data) != 2:
            return None

        count = struct.unpack(endian + "H", data)[0]
        width = None
        height = None
        sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8}

        for _ in range(count):
            entry = f.read(12)
            if len(entry) != 12:
                return None
            tag, typ, num, value = struct.unpack(endian + "HHII", entry)
            if tag not in (256, 257) or typ not in sizes:
                continue

            total = sizes[typ] * num
            if total <= 4:
                raw = struct.pack(endian + "I", value)[:total]
            else:
                pos = f.tell()
                f.seek(value)
                raw = f.read(total)
                f.seek(pos)

            if typ == 3 and len(raw) >= 2:
                val = struct.unpack(endian + "H", raw[:2])[0]
            elif typ == 4 and len(raw) >= 4:
                val = struct.unpack(endian + "I", raw[:4])[0]
            else:
                continue

            if tag == 256:
                width = val
            else:
                height = val

        return (int(width), int(height)) if width and height else None


def image_dimensions(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".jpg", ".jpeg"):
            return jpeg_dimensions(path)
        if ext == ".png":
            return png_dimensions(path)
        if ext == ".bmp":
            return bmp_dimensions(path)
        if ext in (".tif", ".tiff"):
            return tiff_dimensions(path)
    except Exception:
        return None
    return None


def filter_files(category_dir, category, min_size, min_dimensions, before_files):
    minimum = parse_size_value(min_size)
    dimensions = parse_dimensions(min_dimensions) if category == "Images" else None

    kept = 0
    discarded = 0
    reasons = {"size": 0, "dimensions": 0, "unreadable_dimensions": 0}

    for root, dirs, files in os.walk(category_dir):
        for name in files:
            full = os.path.join(root, name)
            try:
                rel = os.path.relpath(full, category_dir)
                if rel in before_files:
                    continue
                size = os.path.getsize(full)
            except Exception:
                continue

            if minimum and size < minimum:
                try:
                    os.remove(full)
                    discarded += 1
                    reasons["size"] += 1
                except Exception:
                    pass
                continue

            if dimensions:
                dims = image_dimensions(full)
                if dims is not None and (dims[0] < dimensions[0] or dims[1] < dimensions[1]):
                    try:
                        os.remove(full)
                        discarded += 1
                        reasons["dimensions"] += 1
                    except Exception:
                        pass
                    continue
                if dims is None:
                    reasons["unreadable_dimensions"] += 1

            kept += 1

    return (kept, discarded, reasons)


def build_command(photorec, source, photo_destination, log_path, families, fstype):
    sequence = ["partition_none", "fileopt", "everything", "disable"]
    for family in families:
        sequence.extend([family, "enable"])
    
    sequence.append("search")
    
    if fstype and fstype.lower() in ("ext2", "ext3", "ext4"):
        sequence.append("ext2")
    else:
        sequence.append("other")
        
    sequence.append("freespace")

    return [
        photorec,
        "/log",
        "/logname",
        log_path,
        "/d",
        photo_destination,
        "/cmd",
        source,
        ",".join(sequence),
    ]


def run_photorec(command, log_path, stop_file, pause_file, raw_dir, source, total_scan_bytes, file_type_multiplier):
    global CURRENT_PHOTOREC, PAUSED

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        log_handle = open(log_path, "ab", buffering=0)
    except Exception as exc:
        emit("SCAN_ERROR " + json.dumps(str(exc)) + "\n")
        return (-1, False, 0, 0)

    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )
    except Exception as exc:
        log_handle.close()
        emit("SCAN_ERROR " + json.dumps(str(exc)) + "\n")
        return (-1, False, 0, 0)

    CURRENT_PHOTOREC = proc

    started = time.monotonic()
    before = count_files(raw_dir)
    stopped = False
    stop_sent = False

    last_report = 0.0
    last_live_path = None
    last_live_size = None

    try:
        while proc.poll() is None:
            now = time.monotonic()

            pause_exists = os.path.exists(pause_file)
            if pause_exists and not PAUSED:
                PAUSED = True
                try:
                    os.killpg(proc.pid, signal.SIGSTOP)
                except Exception:
                    pass
                emit("SCAN_PAUSED\n")
            elif not pause_exists and PAUSED:
                PAUSED = False
                try:
                    os.killpg(proc.pid, signal.SIGCONT)
                except Exception:
                    pass
                emit("SCAN_RESUMED\n")

            if requested_stop(stop_file) and not stop_sent:
                stopped = True
                stop_sent = True
                emit("PHOTOREC_STOPPING " + json.dumps({"elapsed": int(now - started)}) + "\n")
                if PAUSED:
                    try:
                        os.killpg(proc.pid, signal.SIGCONT)
                    except Exception:
                        pass
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass

            if not PAUSED and (now - last_report >= 0.5):
                elapsed_sec = max(1.0, now - started)
                current = count_files(raw_dir)
                
                scanned_bytes = 0
                try:
                    if os.path.exists(log_path):
                        scanned_bytes = os.path.getsize(log_path) * 250 * file_type_multiplier
                except Exception:
                    pass
                
                if scanned_bytes <= 0:
                    scanned_bytes = int(elapsed_sec * 25 * 1024 * 1024)

                if total_scan_bytes > 0:
                    progress_pct = min(99.0, (float(scanned_bytes) / float(total_scan_bytes)) * 100.0)
                else:
                    progress_pct = min(95.0, (elapsed_sec / 120.0) * 100.0)

                bytes_per_sec = float(scanned_bytes) / elapsed_sec if elapsed_sec > 0 else 1.0
                remaining_bytes = max(0, total_scan_bytes - scanned_bytes)
                eta_seconds = int(remaining_bytes / bytes_per_sec) if bytes_per_sec > 0 else 0

                emit(
                    "PROGRESS "
                    + json.dumps({
                        "category": "Recovery scan",
                        "elapsed": int(elapsed_sec),
                        "percent": round(progress_pct, 1),
                        "eta": eta_seconds,
                        "files": current,
                        "new_files": max(0, current - before),
                    })
                    + "\n"
                )

                newest = None
                newest_mtime = -1
                for root, dirs, files in os.walk(raw_dir):
                    for name in files:
                        full = os.path.join(root, name)
                        try:
                            mtime = os.path.getmtime(full)
                            if mtime > newest_mtime:
                                newest_mtime = mtime
                                newest = full
                        except OSError:
                            pass

                if newest:
                    try:
                        newest_size = os.path.getsize(newest)
                    except OSError:
                        newest_size = 0

                    if newest != last_live_path or newest_size != last_live_size:
                        emit(
                            "LIVE_FILE "
                            + json.dumps({
                                "filename": os.path.basename(newest),
                                "path": newest,
                                "size": newest_size,
                                "source": source,
                                "elapsed": int(now - started),
                            })
                            + "\n"
                        )
                        last_live_path = newest
                        last_live_size = newest_size

                last_report = now

            time.sleep(0.25)

        try:
            return_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            return_code = proc.wait(timeout=5)

    finally:
        CURRENT_PHOTOREC = None
        log_handle.close()

    elapsed = int(time.monotonic() - started)
    raw_new_files = max(0, count_files(raw_dir) - before)

    emit(
        "SCAN_DONE "
        + json.dumps({
            "exit_code": return_code,
            "stopped": stopped,
            "elapsed": elapsed,
            "raw_new_files": raw_new_files,
            "log_path": log_path,
        })
        + "\n"
    )

    return (return_code, stopped, elapsed, raw_new_files)


def detect_archive_kind(path):
    try:
        with open(path, "rb") as handle:
            head = handle.read(16)
            if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06") or head.startswith(b"PK\x07\x08"):
                return "zip"
            if head.startswith(b"7z\xbc\xaf'\x1c"):
                return "7z"
            if head.startswith(b"Rar!\x1a\x07"):
                return "rar"
            if head.startswith(b"\x1f\x8b"):
                return "gz"
            if head.startswith(b"BZh"):
                return "bz2"
            if head.startswith(b"\xfd7zXZ\x00"):
                return "xz"

            handle.seek(32769)
            if handle.read(5) == b"CD001":
                return "iso"

            handle.seek(257)
            if handle.read(5) == b"ustar":
                return "tar"
    except (OSError, ValueError):
        pass
    return None


def zip_looks_like_document(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" in names:
                if any(name.startswith("word/") for name in names):
                    return "docx"
                if any(name.startswith("xl/") for name in names):
                    return "xlsx"
                if any(name.startswith("ppt/") for name in names):
                    return "pptx"

            if "mimetype" in names:
                try:
                    mimetype = archive.read("mimetype", pwd=None)[:100]
                except Exception:
                    mimetype = b""
                if mimetype == b"application/vnd.oasis.opendocument.text":
                    return "odt"
                if mimetype == b"application/vnd.oasis.opendocument.spreadsheet":
                    return "ods"
                if mimetype == b"application/vnd.oasis.opendocument.presentation":
                    return "odp"
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError):
        pass
    return None


def classify_recovered_file(path, selected_extensions, extension_categories):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    archive_extensions = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso"}

    if ext in archive_extensions:
        return (extension_categories.get(ext), ext)

    office_extensions = {"docx", "xlsx", "pptx"}
    if ext in office_extensions:
        return (extension_categories.get(ext), ext)

    detected = detect_archive_kind(path)

    if detected == "zip":
        document_ext = zip_looks_like_document(path)
        if document_ext and document_ext in selected_extensions:
            return (extension_categories.get(document_ext), document_ext)
        if "zip" in selected_extensions:
            return (extension_categories.get("zip"), "zip")

    elif detected in {"rar", "7z", "tar", "gz", "bz2", "xz", "iso"}:
        if detected in selected_extensions:
            return (extension_categories.get(detected), detected)

    if ext == "jpg" and "jpg" not in selected_extensions and "jpeg" in selected_extensions:
        return (extension_categories.get("jpeg"), "jpeg")
    if ext == "jpeg" and "jpeg" not in selected_extensions and "jpg" in selected_extensions:
        return (extension_categories.get("jpg"), "jpg")

    if ext in selected_extensions:
        return (extension_categories.get(ext), ext)

    return (None, ext)


def iter_new_files(raw_dir, before_files):
    result = []
    if not os.path.isdir(raw_dir):
        return result
    for root, dirs, files in os.walk(raw_dir):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, raw_dir)
            if rel not in before_files:
                result.append(full)
    return result


def restore_workspace_ownership(runtime_dir, uid, gid):
    try:
        subprocess.run(
            ["chown", "-R", f"{uid}:{gid}", runtime_dir],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
    except Exception:
        pass


def safe_duplicate_target(category_dir, original_name):
    stem, suffix = os.path.splitext(original_name)
    counter = 2
    while True:
        candidate = os.path.join(category_dir, f"{stem}_{counter}{suffix}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def wait_for_duplicate_decision(runtime_dir, source_path, target_path, stop_file):
    request_file = os.path.join(runtime_dir, "duplicate_request.json")
    response_file = os.path.join(runtime_dir, "duplicate_response.json")

    try:
        if os.path.exists(request_file):
            os.remove(request_file)
        if os.path.exists(response_file):
            os.remove(response_file)
    except OSError:
        pass

    request = {
        "source": source_path,
        "target": target_path,
        "filename": os.path.basename(target_path),
        "source_size": os.path.getsize(source_path) if os.path.exists(source_path) else 0,
        "target_size": os.path.getsize(target_path) if os.path.exists(target_path) else 0,
    }

    try:
        temp_request = request_file + ".tmp"
        with open(temp_request, "w", encoding="utf-8") as handle:
            json.dump(request, handle)
        os.replace(temp_request, request_file)
    except OSError as exc:
        emit("WARNING " + json.dumps(f"Could not create duplicate decision request: {exc}") + "\n")
        return "keep_existing"

    emit("DUPLICATE_REQUEST " + json.dumps(request) + "\n")

    try:
        while not requested_stop(stop_file):
            if os.path.exists(response_file):
                try:
                    with open(response_file, "r", encoding="utf-8") as handle:
                        response = json.load(handle)
                    decision = response.get("decision", "keep_existing")
                    if decision in ("keep_existing", "overwrite", "keep_both"):
                        return decision
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
            time.sleep(0.2)
    finally:
        for path in (request_file, response_file):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    return "keep_existing"


def main():
    if os.geteuid() != 0:
        emit("ERROR helper_not_root\n")
        return 10

    if len(sys.argv) != 2:
        emit("ERROR missing_configuration\n")
        return 11

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as handle:
            cfg = json.load(handle)
    except Exception as exc:
        emit("ERROR " + json.dumps(f"Could not read configuration: {exc}") + "\n")
        return 12

    source = cfg["source"]
    fstype = cfg.get("fstype", "")
    destination = cfg["destination"]
    duplicate_handling = cfg.get("duplicate_handling", "Keep existing")
    photorec = cfg["photorec"]
    categories = cfg["categories"]
    category_dirs = cfg["category_dirs"]
    filters = cfg.get("filters", {})
    stop_file = cfg["stop_file"]
    pause_file = cfg.get("pause_file", os.path.join(cfg["runtime_dir"], "PAUSE"))
    runtime_dir = cfg["runtime_dir"]
    log_dir = cfg["log_dir"]
    uid = int(cfg["uid"])
    gid = int(cfg["gid"])

    selected_extensions = set(cfg.get("selected_extensions", []))
    extension_categories = cfg.get("extension_categories", {})
    families_by_category = cfg.get("families", {})

    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    arm_parent_death_signal()

    emit("JOB_START " + json.dumps({"source": source, "destination": destination, "categories": categories}) + "\n")

    os.makedirs(destination, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    original_mounts = mountpoints(source)
    unmounted_by_us = False

    total_size, free_bytes, detected_fstype = get_partition_stats(source)
    if not fstype:
        fstype = detected_fstype

    if original_mounts:
        ok, _ = unmount_device(source)
        if not ok:
            emit(
                "ERROR "
                + json.dumps(
                    "The source partition could not be unmounted. "
                    "PhotoRec was not started."
                )
                + "\n"
            )
            return 21
        unmounted_by_us = True
    else:
        emit("SOURCE_ALREADY_UNMOUNTED\n")

    all_families = []
    for category in categories:
        for family in families_by_category.get(category, []):
            if family not in all_families:
                all_families.append(family)

    raw_dir = os.path.join(runtime_dir, "raw")
    raw_base = os.path.join(raw_dir, "recup_dir")
    os.makedirs(raw_dir, exist_ok=True)

    before_raw = snapshot_files(raw_dir)
    log_path = os.path.join(log_dir, "photorec_scan.log")

    emit(
        "SCAN_START "
        + json.dumps({
            "categories": categories,
            "families": all_families,
            "output": raw_base,
            "log_path": log_path,
        })
        + "\n"
    )

    type_count = len(selected_extensions)
    if type_count <= 3:
        file_type_multiplier = 0.8
    elif type_count <= 8:
        file_type_multiplier = 1.0
    else:
        file_type_multiplier = 1.35

    total_scan_bytes = free_bytes if free_bytes > 0 else (total_size if total_size > 0 else 1024**3)

    scan_code, stopped, elapsed, raw_new_files = run_photorec(
        build_command(photorec, source, raw_base, log_path, all_families, fstype),
        log_path,
        stop_file,
        pause_file,
        raw_dir,
        source,
        total_scan_bytes,
        file_type_multiplier,
    )

    before_category_files = {}
    for category in categories:
        category_dir = os.path.join(destination, category_dirs[category])
        os.makedirs(category_dir, exist_ok=True)
        before_category_files[category] = snapshot_files(category_dir)

    moved = {category: 0 for category in categories}
    routing_discarded = 0
    duplicate_kept_existing = 0
    duplicate_overwritten = 0
    duplicate_kept_both = 0
    duplicate_asked = 0
    inventory_rows = []

    raw_files_list = iter_new_files(raw_dir, before_raw)
    total_raw_files = len(raw_files_list)

    emit("ROUTING_START " + json.dumps({"raw_files": total_raw_files, "destination": destination}) + "\n")

    for index, full in enumerate(raw_files_list, 1):
        if index == 1 or index % 5 == 0 or index == total_raw_files:
            pct = 90.0 + (float(index) / float(max(1, total_raw_files))) * 9.0
            emit(
                "ROUTING_PROGRESS "
                + json.dumps({
                    "current": index,
                    "total": total_raw_files,
                    "percent": round(pct, 1),
                    "filename": os.path.basename(full),
                })
                + "\n"
            )

        category, classified_ext = classify_recovered_file(
            full,
            selected_extensions,
            extension_categories,
        )

        if not category or category not in categories or classified_ext not in selected_extensions:
            try:
                os.remove(full)
            except Exception:
                pass
            routing_discarded += 1
            continue

        category_dir = os.path.join(destination, category_dirs[category])
        original_name = os.path.basename(full)
        target = os.path.join(category_dir, original_name)
        decision = None

        if os.path.exists(target):
            decision = {
                "Keep existing": "keep_existing",
                "Overwrite existing": "overwrite",
                "Keep both": "keep_both",
                "Ask each time": "ask",
            }.get(duplicate_handling, "keep_both")

            if decision == "ask":
                duplicate_asked += 1
                decision = wait_for_duplicate_decision(runtime_dir, full, target, stop_file)
                if requested_stop(stop_file):
                    try:
                        os.remove(full)
                    except OSError:
                        pass
                    routing_discarded += 1
                    break

            if decision == "keep_existing":
                try:
                    os.remove(full)
                except OSError:
                    pass
                duplicate_kept_existing += 1
                routing_discarded += 1
                emit("DUPLICATE_RESOLVED " + json.dumps({"action": "kept_existing", "filename": original_name}) + "\n")
                continue

            if decision == "overwrite":
                duplicate_overwritten += 1
            elif decision == "keep_both":
                target = safe_duplicate_target(category_dir, original_name)
                duplicate_kept_both += 1

        try:
            file_size = os.path.getsize(full)
        except Exception:
            file_size = 0

        try:
            if os.path.exists(target) and decision == "overwrite":
                try:
                    os.replace(full, target)
                except OSError:
                    os.remove(target)
                    shutil.move(full, target)
            else:
                shutil.move(full, target)
            moved[category] += 1
            inventory_rows.append({
                "category": category,
                "filename": os.path.basename(target),
                "destination_path": os.path.abspath(target),
                "source_device": source,
                "photorec_staging_path": os.path.abspath(full),
                "size_bytes": file_size,
                "recovered_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            })
        except Exception:
            routing_discarded += 1

    inventory_path = os.path.join(destination, "PhotoRec_Recovery_Inventory.csv")
    try:
        with open(inventory_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "category", "filename", "destination_path",
                    "source_device", "photorec_staging_path",
                    "size_bytes", "recovered_at",
                ],
            )
            writer.writeheader()
            writer.writerows(inventory_rows)
    except Exception as exc:
        inventory_path = ""
        emit("WARNING " + json.dumps(f"Could not write recovery inventory: {exc}") + "\n")

    results = []
    total_kept = 0
    total_discarded = routing_discarded
    
    for category in categories:
        category_dir = os.path.join(destination, category_dirs[category])
        category_filter = filters.get(category, {})

        kept, discarded, reasons = filter_files(
            category_dir,
            category,
            category_filter.get("min_size", "No minimum"),
            category_filter.get("min_dimensions", "No minimum"),
            before_category_files[category],
        )
        
        total_kept += kept
        total_discarded += discarded

        item = {
            "category": category,
            "status": (
                "STOPPED" if stopped
                else "COMPLETED" if scan_code == 0
                else "FAILED"
            ),
            "exit_code": scan_code,
            "stopped": stopped,
            "elapsed": elapsed,
            "raw_new_files": moved[category],
            "new_files": kept,
            "discarded": discarded,
            "routing_discarded": routing_discarded,
            "discard_reasons": reasons,
            "output": category_dir,
            "log_path": log_path,
        }
        results.append(item)
        emit("CATEGORY_DONE " + json.dumps(item) + "\n")

    try:
        for root, dirs, files in os.walk(raw_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    pass
    except Exception:
        pass

    remounted = remount_device(source) if unmounted_by_us else False
    ownership_failures = []

    for category in categories:
        target = os.path.join(destination, category_dirs[category])
        try:
            result = subprocess.run(
                ["chown", "-R", f"{uid}:{gid}", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=120,
            )
            if result.returncode != 0:
                ownership_failures.append({
                    "category": category,
                    "error": result.stderr.strip() or f"chown exited with {result.returncode}",
                })
                continue

            try:
                stat = os.stat(target)
                if stat.st_uid != uid or stat.st_gid != gid:
                    ownership_failures.append({
                        "category": category,
                        "error": f"verified owner is {stat.st_uid}:{stat.st_gid}, expected {uid}:{gid}",
                    })
            except Exception as exc:
                ownership_failures.append({
                    "category": category,
                    "error": f"ownership verification failed: {exc}",
                })

        except Exception as exc:
            ownership_failures.append({"category": category, "error": str(exc)})

    restore_workspace_ownership(runtime_dir, uid, gid)

    overall_status = (
        "stopped" if stopped
        else "failed" if scan_code != 0
        else "completed"
    )

    emit(
        "JOB_REPORT "
        + json.dumps({
            "overall_status": overall_status,
            "results": results,
            "remounted": remounted,
            "raw_new_files": raw_new_files,
            "routing_discarded": routing_discarded,
            "duplicate_kept_existing": duplicate_kept_existing,
            "duplicate_overwritten": duplicate_overwritten,
            "duplicate_kept_both": duplicate_kept_both,
            "duplicate_asked": duplicate_asked,
            "duplicate_handling": duplicate_handling,
            "total_kept": total_kept,
            "total_discarded": total_discarded,
            "scan_elapsed": elapsed,
            "log_path": log_path,
            "inventory_path": inventory_path,
            "inventory_count": len(inventory_rows),
            "owner_uid": uid,
            "owner_gid": gid,
            "ownership_failures": ownership_failures,
        })
        + "\n"
    )

    return 0 if scan_code == 0 else 22


if __name__ == "__main__":
    sys.exit(main())
'''


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------

LIGHT_THEME = {
    "bg": "#f4f4f4",
    "panel": "#ffffff",
    "fg": "#202020",
    "muted": "#555555",
    "entry": "#ffffff",
    "select": "#d9e8ff",
    "button": "#eeeeee",
    "border": "#c8c8c8",
    "insert": "#202020",
}

DARK_THEME = {
    "bg": "#202124",
    "panel": "#292a2d",
    "fg": "#eeeeee",
    "muted": "#b7b7b7",
    "entry": "#303134",
    "select": "#3d5f86",
    "button": "#34363a",
    "border": "#55585d",
    "insert": "#ffffff",
}


def detect_system_theme():
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
        value = result.stdout.strip().lower()
        if "prefer-dark" in value:
            return "dark"
        if "prefer-light" in value:
            return "light"
    except Exception:
        pass

    kdeglobals = os.path.expanduser("~/.config/kdeglobals")
    try:
        with open(kdeglobals, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                stripped = line.strip().lower()
                if stripped.startswith("colorscheme="):
                    scheme = stripped.split("=", 1)[1].strip()
                    if "dark" in scheme or "breeze dark" in scheme:
                        return "dark"
                    if "light" in scheme or "breeze" in scheme:
                        return "light"
    except Exception:
        pass

    for key in ("GTK_THEME", "QT_STYLE_OVERRIDE"):
        value = os.environ.get(key, "").lower()
        if "dark" in value:
            return "dark"
        if "light" in value:
            return "light"

    return "light"


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class PhotoRecGUI(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)

        # Size the main window around the Setup and File Types tabs.
        # The File Types tab gets enough vertical space to show the
        # categories and their controls on a normal desktop.
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        preferred_w = min(920, max(820, screen_w - 80))
        preferred_h = min(980, max(820, screen_h - 80))

        self.geometry(f"{preferred_w}x{preferred_h}")
        self.minsize(800, 760)

        # Center the window on the screen.
        self.update_idletasks()
        x = max(0, (screen_w - preferred_w) // 2)
        y = max(0, (screen_h - preferred_h) // 2)
        self.geometry(f"{preferred_w}x{preferred_h}+{x}+{y}")

        icon_path = get_asset_path("icon.png")
        if icon_path:
            try:
                self.icon_img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self.icon_img)
            except Exception:
                pass

        self.photorec = find_photorec()
        self.photorec_ver = "Detecting..."

        self.disks = []
        self.partition_map = {}
        self.source_disk = None
        self.source_partition = None

        self.type_vars = {}
        self.type_widgets = []
        self.filter_vars = {}
        self.dimension_vars = {}

        self.updating_filters = False
        self.banner_timer = None

        try:
            os.makedirs(DEFAULT_RECOVERY_DIR, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Recovery directory error", f"Could not create default directory:\n{exc}")

        self.destination_var = tk.StringVar(value=DEFAULT_RECOVERY_DIR)
        self.destination_preview_var = tk.StringVar()
        self.appearance_var = tk.StringVar(value="System")
        self.duplicate_handling_var = tk.StringVar(value="Keep existing")

        saved = self.load_user_settings()
        if "appearance" in saved:
            self.appearance_var.set(saved["appearance"])
        if "destination" in saved and os.path.isdir(saved["destination"]):
            self.destination_var.set(saved["destination"])
        if saved.get("duplicate_handling") in ("Keep existing", "Overwrite existing", "Keep both", "Ask each time"):
            self.duplicate_handling_var.set(saved["duplicate_handling"])

        self.running = False
        self.paused = False
        self.process = None

        self.runtime_dir = None
        self.helper_config_path = None
        self.helper_script_path = None
        self.stop_file = None
        self.pause_file = None
        self.log_dir = None

        self.current_theme_name = None

        self.configure_styles()
        self.build_scrollable_container()
        self.build_interface()
        self.update_destination_preview()
        self.apply_theme(self.appearance_var.get())
        self.bind_keyboard_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.after(50, self.initial_load)

    def get_settings_path(self):
        config_dir = os.path.expanduser("~/.config/hexvault")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "settings.json")

    def load_user_settings(self):
        settings_path = self.get_settings_path()
        if not os.path.exists(settings_path):
            return {}
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_user_settings(self):
        filters_saved = {
            cat: var.get() for cat, var in self.filter_vars.items()
        }
        settings = {
            "appearance": self.appearance_var.get(),
            "destination": self.destination_var.get(),
            "duplicate_handling": self.duplicate_handling_var.get(),
            "selected_extensions": self.selected_extensions(),
            "filters": filters_saved,
        }
        try:
            with open(self.get_settings_path(), "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass

    def reset_to_defaults(self):
        for ext, var in self.type_vars.items():
            var.set(ext in DEFAULT_SELECTED)
        for cat, var in self.filter_vars.items():
            if cat in DEFAULT_MIN_SIZE:
                var.set(DEFAULT_MIN_SIZE[cat])
        for cat, var in self.dimension_vars.items():
            var.set(DEFAULT_MIN_DIMENSIONS)
        self.update_destination_preview()

    def bind_keyboard_shortcuts(self):
        self.bind_all("<Control-q>", lambda e: self.exit_app())
        self.bind_all("<Control-w>", lambda e: self.exit_app())
        self.bind_all("<Control-Return>", lambda e: self.start_recovery() if not self.running else None)
        self.bind_all("<space>", lambda e: self.toggle_pause() if self.running else None)

    def initial_load(self):
        def _get_version():
            self.photorec_ver = photorec_version(self.photorec)
            if hasattr(self, "engine_status_label"):
                if self.photorec:
                    status = f"PhotoRec binary: {self.photorec} (v{self.photorec_ver})\nMode: FREE SPACE ONLY"
                else:
                    status = "PhotoRec was not found. Please install TestDisk / PhotoRec."
                self.after(0, lambda: self.engine_status_label.config(text=status))

        threading.Thread(target=_get_version, daemon=True).start()
        self.refresh_devices()

    def build_scrollable_container(self):
        self.main_canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.main_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview)
        self.main_container = ttk.Frame(self.main_canvas)

        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_window_id = self.main_canvas.create_window((0, 0), window=self.main_container, anchor="nw")

        def _on_main_configure(event):
            self.main_canvas.itemconfig(self.main_window_id, width=event.width)
            _check_scrollbar_needed()

        def _check_scrollbar_needed(event=None):
            self.main_container.update_idletasks()
            content_height = self.main_container.winfo_reqheight()
            canvas_height = self.main_canvas.winfo_height()

            self.main_canvas.configure(scrollregion=(0, 0, event.width if event else self.main_canvas.winfo_width(), content_height))

            if content_height > canvas_height and canvas_height > 100:
                if not self.main_scrollbar.winfo_ismapped():
                    self.main_scrollbar.pack(side="right", fill="y")
            else:
                if self.main_scrollbar.winfo_ismapped():
                    self.main_scrollbar.pack_forget()

        def _on_main_mousewheel(event):
            if self.main_scrollbar.winfo_ismapped():
                if event.num == 4:
                    self.main_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.main_canvas.yview_scroll(1, "units")
                elif event.delta:
                    self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_main_mousewheel, add="+")
            widget.bind("<Button-4>", _on_main_mousewheel, add="+")
            widget.bind("<Button-5>", _on_main_mousewheel, add="+")
            for child in widget.winfo_children():
                if getattr(child, "types_canvas", None) is None:
                    _bind_mousewheel(child)

        self._bind_main_mousewheel = _bind_mousewheel
        self.main_canvas.bind("<Configure>", _on_main_configure)
        self.main_container.bind("<Configure>", _check_scrollbar_needed)
        self.bind("<Configure>", _check_scrollbar_needed)

    def configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("Title.TLabel", font=("TkDefaultFont", 16, "bold"))
        self.style.configure("H2.TLabel", font=("TkDefaultFont", 13, "bold"))
        self.style.configure("H3.TLabel", font=("TkDefaultFont", 10, "bold"))
        self.style.configure("Big.TButton", padding=(10, 6))

    def effective_theme(self, selection):
        if selection == "System":
            return detect_system_theme()
        return "dark" if selection == "Dark" else "light"

    def apply_theme(self, selection=None, update_selector=True):
        if selection is None:
            selection = self.appearance_var.get()

        theme_name = self.effective_theme(selection)
        colors = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        self.current_theme_name = theme_name

        self.style.configure(".", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("Title.TLabel", background=colors["bg"], foreground=colors["fg"], font=("TkDefaultFont", 16, "bold"))
        self.style.configure("H2.TLabel", background=colors["bg"], foreground=colors["fg"], font=("TkDefaultFont", 13, "bold"))
        self.style.configure("H3.TLabel", background=colors["bg"], foreground=colors["fg"], font=("TkDefaultFont", 10, "bold"))

        self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TButton", background=colors["button"], foreground=colors["fg"])
        self.style.map("TButton", background=[("active", colors["select"]), ("pressed", colors["select"])], foreground=[("disabled", colors["muted"])])

        self.style.configure("TCombobox", fieldbackground=colors["entry"], background=colors["button"], foreground=colors["fg"], arrowcolor=colors["fg"])
        self.style.map("TCombobox", fieldbackground=[("readonly", colors["entry"])], foreground=[("readonly", colors["fg"])], selectbackground=[("readonly", colors["select"])], selectforeground=[("readonly", colors["fg"])])

        self.style.configure("TNotebook", background=colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=colors["button"], foreground=colors["fg"], padding=(12, 6), font=("TkDefaultFont", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", colors["select"])], foreground=[("selected", colors["fg"])])

        self.style.configure("HexVault.Treeview", background=colors["panel"], foreground=colors["fg"], fieldbackground=colors["panel"], borderwidth=0)
        self.style.configure("HexVault.Treeview.Item", foreground=colors["fg"], background=colors["panel"])
        self.style.map("HexVault.Treeview", background=[("selected", colors["select"])], foreground=[("selected", colors["fg"])])

        self.configure(bg=colors["bg"])

        if hasattr(self, "main_canvas"):
            self.main_canvas.configure(bg=colors["bg"])

        if hasattr(self, "types_canvas"):
            self.types_canvas.configure(bg=colors["bg"])

        for cb in getattr(self, "type_widgets", []):
            cb.set_colors(colors["bg"], colors["fg"])

        if hasattr(self, "output"):
            self.output.configure(
                background=colors["panel"],
                foreground=colors["fg"],
                insertbackground=colors["insert"],
                selectbackground=colors["select"],
                selectforeground=colors["fg"],
            )

        if update_selector and hasattr(self, "appearance_var"):
            self.appearance_var.set(selection)

    def build_interface(self):
        banner_path = get_asset_path("banner.png")
        if banner_path:
            try:
                from PIL import Image, ImageTk

                self.raw_banner = Image.open(banner_path)

                def delayed_banner_resize(width):
                    if width > 100:
                        new_width = width
                        w_percent = new_width / float(self.raw_banner.size[0])
                        new_height = int(float(self.raw_banner.size[1]) * float(w_percent))
                        
                        if new_height > 120:
                            new_height = 120

                        resized = self.raw_banner.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        self.banner_img = ImageTk.PhotoImage(resized)
                        self.banner_label.config(image=self.banner_img)

                def on_root_resize(event):
                    if event.widget == self:
                        if self.banner_timer is not None:
                            self.after_cancel(self.banner_timer)
                        self.banner_timer = self.after(100, lambda: delayed_banner_resize(self.winfo_width()))

                self.banner_label = ttk.Label(self.main_container)
                self.banner_label.pack(fill="x", side="top", pady=(0, 2))
                self.bind("<Configure>", on_root_resize, add="+")

            except Exception as e:
                print(f"Could not load header banner: {e}")

        header = ttk.Frame(self.main_container, padding=(12, 2, 12, 2))
        header.pack(fill="x")

        title_box = ttk.Frame(header)
        title_box.pack(side="left")

        ttk.Label(title_box, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Digital File Recovery", font=("TkDefaultFont", 9)).pack(anchor="w")

        app_frame = ttk.Frame(header)
        app_frame.pack(side="right")

        ttk.Label(app_frame, text="Theme: ").pack(side="left")
        self.appearance_combo = ttk.Combobox(
            app_frame,
            textvariable=self.appearance_var,
            values=["System", "Light", "Dark"],
            state="readonly",
            width=9,
        )
        self.appearance_combo.pack(side="left", padx=(0, 10))
        self.appearance_combo.bind("<<ComboboxSelected>>", self.appearance_changed)

        ttk.Button(app_frame, text="Exit", command=self.exit_app).pack(side="right")

        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self.tab_setup = ttk.Frame(self.notebook, padding=12)
        self.tab_types = ttk.Frame(self.notebook, padding=12)
        self.tab_status = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_setup, text=" Setup & Drives ")
        self.notebook.add(self.tab_types, text=" File Types & Filters ")
        self.notebook.add(self.tab_status, text=" Recovery Status & Log ")

        self.build_setup_tab()
        self.build_types_tab()
        self.build_status_tab()

        self._bind_main_mousewheel(self.main_container)

    def build_setup_tab(self):
        ttk.Label(self.tab_setup, text="1. Engine & Source Partition", style="H2.TLabel").pack(anchor="w", pady=(0, 6))

        if self.photorec:
            status = f"PhotoRec binary: {self.photorec} (v{self.photorec_ver})\nMode: FREE SPACE ONLY"
        else:
            status = "PhotoRec was not found. Please install TestDisk / PhotoRec."

        self.engine_status_label = ttk.Label(self.tab_setup, text=status, wraplength=720)
        self.engine_status_label.pack(anchor="w", pady=(0, 10))

        ttk.Separator(self.tab_setup, orient="horizontal").pack(fill="x", pady=6)

        ttk.Label(self.tab_setup, text="Select Target Drive", style="H3.TLabel").pack(anchor="w", pady=(4, 2))
        self.disk_var = tk.StringVar()
        self.disk_combo = ttk.Combobox(self.tab_setup, textvariable=self.disk_var, state="readonly")
        self.disk_combo.pack(fill="x", pady=(0, 8))
        self.disk_combo.bind("<<ComboboxSelected>>", self.disk_changed)

        ttk.Label(self.tab_setup, text="Select Target Partition", style="H3.TLabel").pack(anchor="w", pady=(4, 2))
        self.partition_var = tk.StringVar()
        self.partition_combo = ttk.Combobox(self.tab_setup, textvariable=self.partition_var, state="readonly")
        self.partition_combo.pack(fill="x", pady=(0, 6))
        self.partition_combo.bind("<<ComboboxSelected>>", self.partition_changed)

        self.source_info = ttk.Label(self.tab_setup, text="", wraplength=720)
        self.source_info.pack(anchor="w", pady=(2, 6))

        ttk.Button(self.tab_setup, text="Refresh Drive List", command=self.refresh_devices).pack(anchor="w", pady=(0, 10))

        ttk.Separator(self.tab_setup, orient="horizontal").pack(fill="x", pady=6)

        ttk.Label(self.tab_setup, text="2. Recovery Destination Folder", style="H2.TLabel").pack(anchor="w", pady=(4, 4))
        dest_row = ttk.Frame(self.tab_setup)
        dest_row.pack(fill="x", pady=(0, 4))

        self.destination_label = ttk.Label(dest_row, text=os.path.abspath(self.destination_var.get()), padding=5, relief="solid")
        self.destination_label.pack(side="left", fill="x", expand=True)

        ttk.Button(dest_row, text="Browse Folder...", command=self.choose_destination).pack(side="left", padx=(8, 0))

        self.destination_preview = ttk.Label(self.tab_setup, text="", wraplength=720)
        self.destination_preview.pack(anchor="w")

        duplicate_frame = ttk.LabelFrame(self.tab_setup, text="Duplicate File Handling", padding=8)
        duplicate_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(
            duplicate_frame,
            text="When a recovered file has the same filename as a file already in the destination:"
        ).pack(anchor="w", pady=(0, 5))

        duplicate_row = ttk.Frame(duplicate_frame)
        duplicate_row.pack(fill="x")
        self.duplicate_combo = ttk.Combobox(
            duplicate_row,
            textvariable=self.duplicate_handling_var,
            values=["Keep existing", "Overwrite existing", "Keep both", "Ask each time"],
            state="readonly",
            width=22,
        )
        self.duplicate_combo.pack(side="left")
        ttk.Label(
            duplicate_row,
            text="  Keep both adds _2, _3, etc. to the recovered filename."
        ).pack(side="left", padx=(8, 0))

        self.duplicate_help = ttk.Label(
            duplicate_frame,
            text="Keep existing is the safest recovery default because it never replaces a file already in the destination."
        )
        self.duplicate_help.pack(anchor="w", pady=(5, 0))

        nav_row = ttk.Frame(self.tab_setup)
        nav_row.pack(fill="x", side="bottom", pady=(10, 0))
        ttk.Button(nav_row, text="Next →", style="Big.TButton", command=lambda: self.notebook.select(self.tab_types)).pack(side="right")

    def build_types_tab(self):
        header_row = ttk.Frame(self.tab_types)
        header_row.pack(fill="x", pady=(0, 6))

        ttk.Label(header_row, text="3. File Types & Post-Carving Filters", style="H2.TLabel").pack(side="left")
        ttk.Button(header_row, text="Reset to Defaults", command=self.reset_to_defaults).pack(side="right")

        scroll_wrapper = ttk.Frame(self.tab_types)
        scroll_wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_wrapper, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(scroll_wrapper, orient="vertical", command=canvas.yview)
        scroll_content = ttk.Frame(canvas)

        self.types_canvas = canvas

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        window_id = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _update_scroll_region(event=None):
            scroll_content.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
            _update_scroll_region()

        canvas.bind("<Configure>", _on_canvas_configure)
        scroll_content.bind("<Configure>", _update_scroll_region)

        def _on_types_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            elif event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_types_mousewheel, add="+")
            widget.bind("<Button-4>", _on_types_mousewheel, add="+")
            widget.bind("<Button-5>", _on_types_mousewheel, add="+")
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        self.type_container = scroll_content
        self.build_type_controls()
        _bind_mousewheel(scroll_content)

        nav_row = ttk.Frame(self.tab_types)
        nav_row.pack(fill="x", side="bottom", pady=(10, 0))

        ttk.Button(nav_row, text="← Previous", style="Big.TButton", command=lambda: self.notebook.select(self.tab_setup)).pack(side="left")
        ttk.Button(nav_row, text="Next →", style="Big.TButton", command=lambda: self.notebook.select(self.tab_status)).pack(side="right")

    def build_status_tab(self):
        ttk.Label(self.tab_status, text="4. Execution & Monitoring", style="H2.TLabel").pack(anchor="w", pady=(0, 4))

        self.current_category_var = tk.StringVar(value="Status: Ready")
        ttk.Label(self.tab_status, textvariable=self.current_category_var, style="H3.TLabel").pack(anchor="w")

        self.current_progress_var = tk.StringVar(value="No recovery in progress.")
        ttk.Label(self.tab_status, textvariable=self.current_progress_var, wraplength=720).pack(anchor="w", pady=(2, 4))

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(self.tab_status, orient="horizontal", length=720, mode="determinate", variable=self.progress_var)
        self.progress.pack(fill="x", pady=(0, 8))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self.tab_status, textvariable=self.status_var, font=("TkDefaultFont", 9, "italic")).pack(anchor="w", pady=(0, 6))

        ttk.Label(self.tab_status, text="Recovery Output / Event Log", style="H3.TLabel").pack(anchor="w", pady=(4, 2))

        output_frame = ttk.Frame(self.tab_status)
        output_frame.pack(fill="both", expand=True)

        self.output = tk.Text(
            output_frame,
            height=10,
            wrap="word",
            font=("TkFixedFont", 9),
            relief="flat",
            borderwidth=1,
        )
        self.output.pack(side="left", fill="both", expand=True)

        out_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        out_scroll.pack(side="right", fill="y")
        self.output.configure(yscrollcommand=out_scroll.set)

        nav_row = ttk.Frame(self.tab_status)
        nav_row.pack(fill="x", side="bottom", pady=(10, 0))

        ttk.Button(nav_row, text="← Previous", style="Big.TButton", command=lambda: self.notebook.select(self.tab_types)).pack(side="left")

        self.recover_button = ttk.Button(nav_row, text="Start Recovery", style="Big.TButton", command=self.start_recovery)
        self.recover_button.pack(side="right", padx=(4, 0))

        self.stop_button = ttk.Button(nav_row, text="Stop Scan", style="Big.TButton", command=self.stop_recovery, state="disabled")
        self.stop_button.pack(side="right", padx=(4, 0))

        self.pause_button = ttk.Button(nav_row, text="Pause Scan", style="Big.TButton", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="right", padx=(4, 0))

        self.preview_button = ttk.Button(nav_row, text="Preview Cmd", style="Big.TButton", command=self.show_command_preview)
        self.preview_button.pack(side="right", padx=(4, 0))

    def _on_image_size_changed(self, event=None):
        if self.updating_filters:
            return
        if "Images" in self.dimension_vars:
            self.updating_filters = True
            self.dimension_vars["Images"].set("No minimum")
            self.updating_filters = False

    def _on_image_dim_changed(self, event=None):
        if self.updating_filters:
            return
        if "Images" in self.filter_vars:
            self.updating_filters = True
            self.filter_vars["Images"].set("No minimum")
            self.updating_filters = False

    def build_type_controls(self):
        for widget in self.type_container.winfo_children():
            widget.destroy()

        self.type_vars.clear()
        self.type_widgets.clear()
        self.filter_vars.clear()
        self.dimension_vars.clear()

        colors = DARK_THEME if self.effective_theme(self.appearance_var.get()) == "dark" else LIGHT_THEME
        saved = self.load_user_settings()
        saved_exts = set(saved.get("selected_extensions", DEFAULT_SELECTED))
        saved_filters = saved.get("filters", {})

        for category, mapping in FILE_TYPES.items():
            category_frame = ttk.Frame(self.type_container, padding=(0, 4, 0, 6))
            category_frame.pack(fill="x", expand=True)

            header = ttk.Frame(category_frame)
            header.pack(fill="x", pady=(0, 4))

            ttk.Label(header, text=category, style="H3.TLabel").pack(side="left")
            ttk.Button(header, text="Select All", command=lambda c=category: self.set_category(c, True)).pack(side="right")
            ttk.Button(header, text="Deselect All", command=lambda c=category: self.set_category(c, False)).pack(side="right", padx=(0, 4))

            grid = ttk.Frame(category_frame)
            grid.pack(fill="x", expand=True)

            extensions = list(mapping.keys())
            for index, extension in enumerate(extensions):
                var = tk.BooleanVar(value=(extension in saved_exts))
                self.type_vars[extension] = var

                cb = CustomCheckbutton(
                    grid,
                    text=f".{extension}",
                    variable=var,
                    command=self.update_destination_preview,
                    bg_color=colors["bg"],
                    fg_color=colors["fg"],
                    width=100,
                )
                cb.grid(row=index // 4, column=index % 4, sticky="w", padx=(0, 8), pady=2)
                self.type_widgets.append(cb)

            for col in range(4):
                grid.columnconfigure(col, weight=1, uniform="type_cols")

            filter_row = ttk.Frame(category_frame)
            filter_row.pack(fill="x", pady=(4, 0))

            ttk.Label(filter_row, text="Min Size: ").pack(side="left")
            default_size = saved_filters.get(category, DEFAULT_MIN_SIZE[category])
            size_var = tk.StringVar(value=default_size)
            self.filter_vars[category] = size_var
            size_combo = ttk.Combobox(filter_row, textvariable=size_var, values=SIZE_CHOICES, state="readonly", width=12)
            size_combo.pack(side="left", padx=(4, 12))

            if category == "Images":
                size_combo.bind("<<ComboboxSelected>>", self._on_image_size_changed)

                ttk.Label(filter_row, text="Min Dimensions: ").pack(side="left")
                dim_var = tk.StringVar(value=DEFAULT_MIN_DIMENSIONS)
                self.dimension_vars[category] = dim_var
                dim_combo = ttk.Combobox(filter_row, textvariable=dim_var, values=DIMENSION_CHOICES, state="readonly", width=12)
                dim_combo.pack(side="left", padx=(4, 0))
                dim_combo.bind("<<ComboboxSelected>>", self._on_image_dim_changed)

            ttk.Separator(self.type_container, orient="horizontal").pack(fill="x", pady=4)

    def set_category(self, category, state):
        for ext in FILE_TYPES[category]:
            self.type_vars[ext].set(state)
        self.update_destination_preview()

    def selected_extensions(self):
        return [ext for ext, var in self.type_vars.items() if var.get()]

    def selected_categories(self):
        selected = set(self.selected_extensions())
        return [cat for cat, mapping in FILE_TYPES.items() if any(ext in selected for ext in mapping)]

    def families_for_category(self, category):
        families = []
        for ext in FILE_TYPES[category]:
            if self.type_vars.get(ext) and self.type_vars[ext].get():
                family = FILE_TYPES[category][ext]
                if family not in families:
                    families.append(family)
        return families

    def refresh_devices(self):
        def _scan():
            try:
                disks = discover_disks()
                self.after(0, self._apply_devices, disks, None)
            except Exception as exc:
                self.after(0, self._apply_devices, [], str(exc))

        threading.Thread(target=_scan, daemon=True).start()

    def _apply_devices(self, disks, error=None):
        if error:
            messagebox.showerror("Drive Detection Error", error)
            return

        self.disks = disks
        values = [f"{disk['path']} ({human_size(disk['size'])})" for disk in self.disks]
        self.disk_combo["values"] = values

        if values:
            self.disk_combo.current(0)
            self.disk_changed()
            self.status_var.set(f"Found {len(values)} physical disk(s).")
        else:
            self.disk_var.set("")
            self.partition_var.set("")
            self.partition_combo["values"] = []
            self.source_partition = None
            self.status_var.set("No physical drives detected.")

    def disk_changed(self, event=None):
        idx = self.disk_combo.current()
        if idx < 0 or idx >= len(self.disks):
            return

        self.source_disk = self.disks[idx]
        self.partition_map.clear()
        values = []

        for part in self.source_disk["partitions"]:
            mounted = "MOUNTED" if part["mountpoints"] else "unmounted"
            label = f"{part['path']} ({human_size(part['size'])}, {part['fstype'] or 'raw'}, {mounted})"
            if part["label"]:
                label += f" [{part['label']}]"
            values.append(label)
            self.partition_map[label] = part

        self.partition_combo["values"] = values
        if values:
            self.partition_combo.current(0)
            self.partition_changed()
        else:
            self.partition_var.set("")
            self.source_partition = None
            self.source_info.config(text="No valid partitions on selected disk.")

    def partition_changed(self, event=None):
        selected = self.partition_var.get()
        partition = self.partition_map.get(selected)
        if not partition:
            return

        self.source_partition = partition
        info = [
            f"Device: {partition['path']}",
            f"Size: {human_size(partition['size'])}",
            f"Filesystem: {partition['fstype'] or 'unknown'}",
        ]

        if partition["mountpoints"]:
            info.append(f"Mounted at: {', '.join(partition['mountpoints'])} (Auto-unmount active)")
        else:
            info.append("Status: Unmounted")

        self.source_info.config(text=" • ".join(info))

    def selected_partition(self):
        return self.source_partition["path"] if self.source_partition else None

    def choose_destination(self):
        colors = DARK_THEME if self.effective_theme(self.appearance_var.get()) == "dark" else LIGHT_THEME

        # Browse Folder opens at the currently selected destination.
        # The application itself defaults to ~/hexvault when first opened.
        initial_path = os.path.abspath(
            os.path.expanduser(self.destination_var.get().strip() or DEFAULT_RECOVERY_DIR)
        )
        if not os.path.isdir(initial_path):
            initial_path = os.path.abspath(os.path.expanduser(DEFAULT_RECOVERY_DIR))
        try:
            os.makedirs(initial_path, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "Recovery directory error",
                f"Could not create the default recovery directory:\n{exc}",
                parent=self,
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Choose Recovery Directory")
        dialog.geometry("820x560")
        dialog.minsize(700, 460)
        dialog.configure(bg=colors["bg"])
        dialog.transient(self)
        dialog.grab_set()

        selected_path = {"value": None}
        current_path = {"value": initial_path}

        header = ttk.Frame(dialog)
        header.pack(fill="x", padx=12, pady=(12, 8))

        ttk.Label(
            header,
            text="Choose Recovery Directory",
            style="H2.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Choose the folder where recovered files will be saved. "
                 "Existing files and folders are shown in the current directory.",
            wraplength=780,
        ).pack(anchor="w", pady=(3, 8))

        location_row = ttk.Frame(header)
        location_row.pack(fill="x")

        path_var = tk.StringVar(value=initial_path)

        ttk.Button(
            location_row,
            text="↑",
            width=3,
            command=lambda: navigate_parent(),
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            location_row,
            text="New Folder",
            command=lambda: create_folder(),
        ).pack(side="left", padx=(0, 8))

        ttk.Entry(
            location_row,
            textvariable=path_var,
            state="readonly",
        ).pack(side="left", fill="x", expand=True)

        browser = ttk.Frame(dialog)
        browser.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        folder_frame = ttk.LabelFrame(browser, text="Folders", padding=6)
        folder_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        contents_frame = ttk.LabelFrame(browser, text="Contents", padding=6)
        contents_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        folder_tree_wrap = ttk.Frame(folder_frame)
        folder_tree_wrap.pack(fill="both", expand=True)

        folder_tree = ttk.Treeview(
            folder_tree_wrap,
            columns=("name", "kind"),
            show="headings",
            selectmode="browse",
            style="HexVault.Treeview",
        )
        folder_tree.heading("name", text="Folder")
        folder_tree.heading("kind", text="Type")
        folder_tree.column("name", width=245, anchor="w")
        folder_tree.column("kind", width=70, anchor="center")
        folder_tree.pack(side="left", fill="both", expand=True)

        folder_scroll = ttk.Scrollbar(
            folder_tree_wrap,
            orient="vertical",
            command=folder_tree.yview,
        )
        folder_scroll.pack(side="right", fill="y")
        folder_tree.configure(yscrollcommand=folder_scroll.set)

        contents_tree_wrap = ttk.Frame(contents_frame)
        contents_tree_wrap.pack(fill="both", expand=True)

        contents_tree = ttk.Treeview(
            contents_tree_wrap,
            columns=("name", "type", "size"),
            show="headings",
            selectmode="browse",
            style="HexVault.Treeview",
        )
        contents_tree.heading("name", text="Name")
        contents_tree.heading("type", text="Type")
        contents_tree.heading("size", text="Size")
        contents_tree.column("name", width=255, anchor="w")
        contents_tree.column("type", width=90, anchor="center")
        contents_tree.column("size", width=90, anchor="e")
        contents_tree.pack(side="left", fill="both", expand=True)

        contents_scroll = ttk.Scrollbar(
            contents_tree_wrap,
            orient="vertical",
            command=contents_tree.yview,
        )
        contents_scroll.pack(side="right", fill="y")
        contents_tree.configure(yscrollcommand=contents_scroll.set)

        folder_paths = {}
        content_paths = {}

        def format_file_size(size):
            try:
                size = int(size)
            except (TypeError, ValueError):
                return ""

            units = ("B", "KB", "MB", "GB", "TB")
            value = float(size)
            for unit in units:
                if value < 1024 or unit == units[-1]:
                    if unit == "B":
                        return f"{int(value)} B"
                    return f"{value:.1f} {unit}"
                value /= 1024
            return ""

        def populate_contents(directory):
            directory = os.path.abspath(os.path.expanduser(directory))

            for item in contents_tree.get_children():
                contents_tree.delete(item)
            content_paths.clear()

            try:
                entries = list(os.scandir(directory))
            except OSError:
                return

            entries.sort(
                key=lambda entry: (
                    not entry.is_dir(follow_symlinks=False),
                    entry.name.lower(),
                )
            )

            for entry in entries:
                if entry.name.startswith("."):
                    continue

                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    continue

                full_path = os.path.abspath(entry.path)

                if is_dir:
                    item_id = contents_tree.insert(
                        "",
                        "end",
                        values=(f"📁 {entry.name}", "Folder", ""),
                    )
                else:
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0

                    suffix = os.path.splitext(entry.name)[1].lower()
                    file_type = suffix[1:].upper() if suffix else "File"

                    item_id = contents_tree.insert(
                        "",
                        "end",
                        values=(entry.name, file_type, format_file_size(size)),
                    )

                content_paths[item_id] = full_path

        def populate_folders(directory):
            directory = os.path.abspath(os.path.expanduser(directory))

            for item in folder_tree.get_children():
                folder_tree.delete(item)
            folder_paths.clear()

            parent = os.path.dirname(directory)
            if parent != directory and os.path.isdir(parent):
                item_id = folder_tree.insert("", "end", values=("..", "Parent"))
                folder_paths[item_id] = parent

            try:
                entries = list(os.scandir(directory))
            except OSError:
                return

            entries.sort(key=lambda entry: entry.name.lower())

            for entry in entries:
                if entry.name.startswith("."):
                    continue

                try:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue

                full_path = os.path.abspath(entry.path)
                item_id = folder_tree.insert(
                    "",
                    "end",
                    values=(f"📁 {entry.name}", "Folder"),
                )
                folder_paths[item_id] = full_path

        def update_selected_label():
            selected_label_var.set(f"Selected folder: {current_path['value']}")

        def refresh_browser(directory):
            directory = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(directory):
                return

            current_path["value"] = directory
            path_var.set(directory)
            populate_folders(directory)
            populate_contents(directory)
            update_selected_label()

        def navigate_parent():
            current = current_path["value"]
            parent = os.path.dirname(current)
            if parent and parent != current:
                refresh_browser(parent)

        def create_folder():
            current = current_path["value"]
            if not os.path.isdir(current):
                return

            new_name = simpledialog.askstring(
                "New Folder",
                "Folder name:",
                parent=dialog,
            )
            if not new_name:
                return

            new_name = new_name.strip()
            if not new_name or new_name in (".", "..") or "/" in new_name or "\\" in new_name:
                messagebox.showwarning(
                    "Invalid folder name",
                    "Please enter a valid folder name.",
                    parent=dialog,
                )
                return

            target_dir = os.path.join(current, new_name)
            try:
                os.makedirs(target_dir, exist_ok=False)
            except FileExistsError:
                messagebox.showinfo(
                    "Folder already exists",
                    f"The folder '{new_name}' already exists.",
                    parent=dialog,
                )
                refresh_browser(target_dir)
                return
            except OSError as exc:
                messagebox.showerror(
                    "Could not create folder",
                    f"Could not create the folder:\n{exc}",
                    parent=dialog,
                )
                return

            refresh_browser(target_dir)

        def folder_double_click(event=None):
            selection = folder_tree.selection()
            if not selection:
                return
            directory = folder_paths.get(selection[0])
            if directory:
                refresh_browser(directory)

        def content_double_click(event=None):
            selection = contents_tree.selection()
            if not selection:
                return
            path = content_paths.get(selection[0])
            if path and os.path.isdir(path):
                refresh_browser(path)

        folder_tree.bind("<Double-1>", folder_double_click)
        folder_tree.bind("<Return>", folder_double_click)
        contents_tree.bind("<Double-1>", content_double_click)

        footer = ttk.Frame(dialog)
        footer.pack(fill="x", padx=12, pady=(0, 12))

        selected_label_var = tk.StringVar(value=f"Selected folder: {initial_path}")
        ttk.Label(
            footer,
            textvariable=selected_label_var,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        def confirm():
            selected_path["value"] = current_path["value"]
            dialog.destroy()

        ttk.Button(
            footer,
            text="Cancel",
            command=dialog.destroy,
        ).pack(side="right", padx=(8, 0))

        ttk.Button(
            footer,
            text="Select This Folder",
            style="Big.TButton",
            command=confirm,
        ).pack(side="right")

        refresh_browser(initial_path)

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Escape>", lambda event: dialog.destroy())

        self.wait_window(dialog)

        if selected_path["value"]:
            self.destination_var.set(selected_path["value"])
            self.update_destination_preview()

    def update_destination_preview(self):
        dest = self.destination_var.get().strip()
        self.destination_label.config(text=dest)
        self.destination_preview_var.set(f"Destination: {dest}")

    def appearance_changed(self, event=None):
        self.apply_theme(self.appearance_var.get())

    def build_preview_commands(self):
        source = self.selected_partition()
        if not source:
            return []
        
        fstype = self.source_partition.get("fstype", "") if self.source_partition else ""
        categories = self.selected_categories()
        families = []
        for cat in categories:
            for fam in self.families_for_category(cat):
                if fam not in families:
                    families.append(fam)
        
        sequence = ["partition_none", "fileopt", "everything", "disable"]
        for fam in families:
            sequence.extend([fam, "enable"])
        
        sequence.append("search")
        
        if fstype and fstype.lower() in ("ext2", "ext3", "ext4"):
            sequence.append("ext2")
        else:
            sequence.append("other")
            
        sequence.append("freespace")
        
        preview_dir = self.runtime_dir if self.runtime_dir and os.path.exists(self.runtime_dir) else HEXVAULT_RUNTIME_DIR
        raw_base = os.path.join(preview_dir, "raw", "recup_dir")
        log_path = os.path.join(preview_dir, "logs", "photorec_scan.log")

        cmd = [
            self.photorec,
            "/log", "/logname", log_path,
            "/d", raw_base,
            "/cmd", source,
            ",".join(sequence),
        ]
        return [" ".join(shell_escape(p) for p in cmd)]

    def show_command_preview(self):
        cmds = self.build_preview_commands()
        if not cmds:
            messagebox.showinfo("Preview", "No partition selected or invalid parameters.", parent=self)
            return

        colors = DARK_THEME if self.effective_theme(self.appearance_var.get()) == "dark" else LIGHT_THEME
        top = tk.Toplevel(self)
        top.title("HexVault | Command Preview")
        top.geometry("720x360")
        top.configure(bg=colors["bg"])

        txt = tk.Text(top, wrap="word", font=("TkFixedFont", 9), bg=colors["panel"], fg=colors["fg"], relief="flat")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("end", cmds[0])
        txt.configure(state="disabled")

    def validate(self):
        if not self.photorec:
            messagebox.showerror("Error", "PhotoRec executable was not found.", parent=self)
            return False
        if not self.selected_partition():
            messagebox.showwarning("Warning", "Please select a source partition.", parent=self)
            return False
        if not self.selected_extensions():
            messagebox.showwarning("Warning", "Please select at least one file extension.", parent=self)
            return False
        destination = os.path.abspath(os.path.expanduser(self.destination_var.get().strip() or DEFAULT_RECOVERY_DIR))
        if not destination:
            messagebox.showwarning("Warning", "Please select a recovery destination.", parent=self)
            return False
        return True

    def prepare_helper_files(self):
        os.makedirs(HEXVAULT_RUNTIME_DIR, exist_ok=True)
        try:
            self.runtime_dir = tempfile.mkdtemp(prefix="job-", dir=HEXVAULT_RUNTIME_DIR)
        except OSError as exc:
            raise RuntimeError(f"Could not create workspace: {exc}")

        os.makedirs(os.path.join(self.runtime_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.runtime_dir, "raw"), exist_ok=True)

        helper_script = os.path.join(self.runtime_dir, "hexvault_helper.py")
        config_path = os.path.join(self.runtime_dir, "config.json")
        stop_file = os.path.join(self.runtime_dir, "STOP")
        pause_file = os.path.join(self.runtime_dir, "PAUSE")
        log_dir = os.path.join(self.runtime_dir, "logs")

        uid, gid = get_actual_user_ids()
        categories = self.selected_categories()
        families_by_category = {cat: self.families_for_category(cat) for cat in categories}

        extension_categories = {}
        for cat, mapping in FILE_TYPES.items():
            for ext in mapping:
                extension_categories[ext] = cat

        filters = {
            cat: {
                "min_size": self.filter_vars.get(cat, tk.StringVar(value="No minimum")).get(),
                "min_dimensions": self.dimension_vars.get(cat, tk.StringVar(value="No minimum")).get() if cat == "Images" else "No minimum",
            }
            for cat in categories
        }

        config = {
            "runtime_dir": self.runtime_dir,
            "destination": self.destination_var.get().strip(),
            "duplicate_handling": self.duplicate_handling_var.get(),
            "source": self.selected_partition(),
            "fstype": self.source_partition.get("fstype", "") if self.source_partition else "",
            "selected_extensions": self.selected_extensions(),
            "categories": categories,
            "category_dirs": CATEGORY_DIRS,
            "families": families_by_category,
            "extension_categories": extension_categories,
            "filters": filters,
            "photorec": self.photorec,
            "stop_file": stop_file,
            "pause_file": pause_file,
            "log_dir": log_dir,
            "uid": uid,
            "gid": gid,
        }

        with open(config_path, "w", encoding="utf-8") as h:
            json.dump(config, h, indent=2)

        with open(helper_script, "w", encoding="utf-8") as h:
            h.write(ROOT_HELPER_SOURCE)

        self.helper_script_path = helper_script
        self.helper_config_path = config_path
        self.stop_file = stop_file
        self.pause_file = pause_file
        self.log_dir = log_dir

    def cleanup_runtime_directory(self):
        if self.runtime_dir and os.path.exists(self.runtime_dir):
            try:
                shutil.rmtree(self.runtime_dir)
            except OSError:
                pass
        self.runtime_dir = None

    def start_recovery(self):
        if self.running or not self.validate():
            return

        try:
            self.save_user_settings()
            self.prepare_helper_files()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to initialize helper workspace:\n{exc}", parent=self)
            return

        self.running = True
        self.paused = False

        self.recover_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause Scan")
        self.stop_button.configure(state="normal")

        self.notebook.select(self.tab_status)
        self.status_var.set("Initializing privileged recovery engine...")
        self.progress_var.set(0.0)

        self.output_clear()
        self.output_insert_line("=== HexVault Recovery Job Started ===")

        threading.Thread(target=self.recovery_worker, daemon=True).start()

    def toggle_pause(self):
        if not self.running or not self.pause_file:
            return

        def _do_pause():
            if not self.paused:
                try:
                    with open(self.pause_file, "w", encoding="utf-8") as h:
                        h.write("PAUSE\n")
                    self.paused = True
                    self.after(0, lambda: self.pause_button.configure(text="Resume Scan"))
                    self.after(0, lambda: self.status_var.set("Pause requested..."))
                except OSError:
                    pass
            else:
                try:
                    if os.path.exists(self.pause_file):
                        os.remove(self.pause_file)
                    self.paused = False
                    self.after(0, lambda: self.pause_button.configure(text="Pause Scan"))
                    self.after(0, lambda: self.status_var.set("Resuming scan..."))
                except OSError:
                    pass

        threading.Thread(target=_do_pause, daemon=True).start()

    def stop_recovery(self):
        if not self.running or not self.stop_file:
            return

        def _do_stop():
            self.after(0, lambda: self.status_var.set("Stop requested..."))
            try:
                with open(self.stop_file, "w", encoding="utf-8") as h:
                    h.write("STOP\n")
            except OSError:
                pass

        threading.Thread(target=_do_stop, daemon=True).start()

    def recovery_worker(self):
        try:
            cmd = ["pkexec", sys.executable, self.helper_script_path, self.helper_config_path]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.process = proc

            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                self.after(0, self.parse_and_format_log, line.rstrip())

            proc.stdout.close()
            code = proc.wait()
            self.after(0, self.recovery_done, code)
        except Exception as exc:
            self.after(0, self.output_insert_line, f"[ERROR] Execution failed: {exc}")
            self.after(0, self.recovery_done, -1)

    def recovery_done(self, code):
        self.running = False
        self.paused = False
        self.progress_var.set(100.0)

        self.recover_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pause Scan")
        self.stop_button.configure(state="disabled")

        if code == 0:
            self.status_var.set("Recovery job complete.")
            self.current_category_var.set("Status: Completed")
            self.output_insert_line("\n=== Recovery Job Successfully Completed ===")
        else:
            self.status_var.set(f"Recovery stopped or exited with code {code}.")
            self.current_category_var.set("Status: Stopped / Failed")
            self.output_insert_line(f"\n=== Recovery Job Terminated (Exit Code: {code}) ===")

        self.cleanup_runtime_directory()

    def parse_and_format_log(self, line):
        if not line:
            return

        parts = line.split(" ", 1)
        token = parts[0]
        payload_str = parts[1] if len(parts) > 1 else ""

        try:
            payload = json.loads(payload_str) if payload_str.startswith(("{", "[")) else payload_str
        except json.JSONDecodeError:
            payload = payload_str

        if token == "JOB_START":
            self.output_insert_line(f"[JOB START] Target: {payload.get('source')} -> {payload.get('destination')}")
            self.output_insert_line(f"[JOB START] Active Categories: {', '.join(payload.get('categories', []))}")

        elif token == "SCAN_START":
            self.output_insert_line(f"[SCAN ENGINE] Active file families: {', '.join(payload.get('families', []))}")
            self.output_insert_line(f"[SCAN ENGINE] Carving unallocated space. Raw files are temporarily staged in {self.runtime_dir or HEXVAULT_RUNTIME_DIR}/raw")

        elif token == "SCAN_PAUSED":
            self.status_var.set("Scan process PAUSED.")
            self.output_insert_line("[STATUS] PhotoRec engine execution suspended (SIGSTOP).")

        elif token == "SCAN_RESUMED":
            self.status_var.set("Scan process RESUMED.")
            self.output_insert_line("[STATUS] PhotoRec engine execution resumed (SIGCONT).")

        elif token == "PROGRESS":
            pct = payload.get("percent", 0.0)
            eta = payload.get("eta", 0)
            files = payload.get("files", 0)
            self.progress_var.set(pct)
            formatted_eta = format_time(eta)
            self.current_progress_var.set(f"Scan Progress: {pct:.1f}% | Est. Time Remaining: {formatted_eta} | Files Found: {files}")

        elif token == "LIVE_FILE":
            fn = payload.get("filename")
            sz = human_size(payload.get("size", 0))
            self.output_insert_line(f"  • [FOUND] '{fn}' ({sz}) staged. Awaiting post-scan size/type filtering.")

        elif token == "ROUTING_START":
            raw_count = payload.get("raw_files", 0)
            dest = payload.get("destination", "")
            self.progress_var.set(90.0)
            self.current_progress_var.set(f"Post-Processing: Analyzing {raw_count} raw files...")
            self.output_insert_line(f"\n[POST-PROCESSING] Analyzing {raw_count} raw file(s) from buffer...")
            self.output_insert_line(f"[POST-PROCESSING] Sorting, checking headers, and applying size/dimension filters -> {dest}")

        elif token == "ROUTING_PROGRESS":
            curr = payload.get("current", 0)
            total = payload.get("total", 0)
            pct = payload.get("percent", 90.0)
            fn = payload.get("filename", "")
            self.progress_var.set(pct)
            self.current_progress_var.set(f"Sorting & Moving: [{curr}/{total}] ({pct:.1f}%) — {fn}")
            self.output_insert_line(f"  • [SORTING] Processing file {curr} of {total}: '{fn}'")

        elif token == "DUPLICATE_REQUEST":
            filename = payload.get("filename", "unknown")
            source_size = human_size(payload.get("source_size", 0))
            target_size = human_size(payload.get("target_size", 0))

            choice = messagebox.askyesnocancel(
                "Duplicate File Detected",
                f"A file named '{filename}' already exists in the destination.\n\n"
                f"Existing file: {target_size}\n"
                f"Recovered file: {source_size}\n\n"
                "Yes = overwrite existing\n"
                "No = keep both files\n"
                "Cancel = keep existing file",
                parent=self,
            )

            decision = "overwrite" if choice is True else "keep_both" if choice is False else "keep_existing"
            response_file = os.path.join(self.runtime_dir or "", "duplicate_response.json")
            try:
                with open(response_file, "w", encoding="utf-8") as handle:
                    json.dump({"decision": decision}, handle)
            except OSError as exc:
                self.output_insert_line(f"[WARNING] Could not answer duplicate prompt: {exc}")

        elif token == "DUPLICATE_RESOLVED":
            action = payload.get("action", "")
            filename = payload.get("filename", "")
            labels = {
                "kept_existing": "kept the existing destination file",
            }
            if action in labels:
                self.output_insert_line(f"  • [DUPLICATE] '{filename}' {labels[action]}.")

        elif token == "CATEGORY_DONE":
            cat = payload.get("category")
            kept = payload.get("new_files", 0)
            disc = payload.get("discarded", 0)
            routing_disc = payload.get("routing_discarded", 0)
            self.output_insert_line(f"[CATEGORY COMPLETE] {cat}: Moved {kept} valid file(s) to destination ({disc} discarded by size/dimension filters; {routing_disc} routing discard(s), including duplicate handling).")

        elif token == "JOB_REPORT":
            self.progress_var.set(100.0)
            self.output_insert_line("\n--- Final Recovery Report ---")
            self.output_insert_line(f"Overall Status: {payload.get('overall_status', 'unknown').upper()}")
            self.output_insert_line(f"Total Raw Files Found: {payload.get('raw_new_files', 0)}")
            self.output_insert_line(f"Total Files Restored (Passed Filters): {payload.get('total_kept', 0)}")
            self.output_insert_line(f"Total Files Discarded (Failed Filters): {payload.get('total_discarded', 0)}")
            self.output_insert_line(f"Duplicate Handling: {payload.get('duplicate_handling', self.duplicate_handling_var.get())}")
            self.output_insert_line(f"Duplicates Kept Existing: {payload.get('duplicate_kept_existing', 0)} | Overwritten: {payload.get('duplicate_overwritten', 0)} | Kept Both: {payload.get('duplicate_kept_both', 0)} | Asked: {payload.get('duplicate_asked', 0)}")
            scan_elapsed = payload.get('scan_elapsed', 0)
            self.output_insert_line(f"Total Scan Time: {format_time(scan_elapsed)}")
            if payload.get("inventory_path"):
                self.output_insert_line(f"Inventory Manifest Written: {payload.get('inventory_path')}")

        elif token in ("ERROR", "WARNING"):
            self.output_insert_line(f"[{token}] {payload}")

        else:
            self.output_insert_line(line)

    def output_clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def output_insert_line(self, text):
        try:
            self.output.configure(state="normal")
            self.output.insert("end", text + "\n")
            self.output.see("end")
            self.output.configure(state="disabled")
        except tk.TclError:
            pass

    def exit_app(self):
        if self.running:
            if not messagebox.askyesno("Exit HexVault", "A recovery operation is in progress. Stop scan and exit?"):
                return
            self.stop_recovery()
        self.save_user_settings()
        self.cleanup_runtime_directory()
        self.destroy()


def main():
    app = PhotoRecGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
