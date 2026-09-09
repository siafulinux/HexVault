# HexVault | Digital File Recovery

![HexVault Banner](assets/banner.png)

<p align="center">
  <img src="assets/icon.png" alt="HexVault Logo" width="96" height="96">
</p>

<p align="center">
  <b>A modern, user-friendly Linux GUI for raw file carving powered by PhotoRec.</b>
</p>

<p align="center">
  Recover deleted files from unallocated disk space through a clean, guided desktop interface.
</p>

<p align="center">
  <a href="#-features">
    <img src="https://img.shields.io/badge/Platform-Linux-orange.svg" alt="Platform">
  </a>
  <a href="#-license">
    <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python">
  </a>
  <a href="https://www.cgsecurity.org/wiki/PhotoRec">
    <img src="https://img.shields.io/badge/Backend-PhotoRec-red.svg" alt="PhotoRec">
  </a>
</p>

---

## 🛠️ Overview

**HexVault** is a modern Linux desktop application for recovering deleted files from storage media using the powerful **PhotoRec** file-carving engine.

Instead of requiring users to navigate PhotoRec's interactive terminal interface, HexVault provides a clean, guided graphical workflow for selecting a storage device, choosing file types, configuring recovery filters, and monitoring the recovery process.

HexVault is designed to make raw file carving more approachable while retaining the underlying recovery capabilities of PhotoRec.

> **Important:** HexVault performs raw file carving. Recovered files may not retain their original filenames, directory structure, timestamps, or other filesystem metadata.

---

## ✨ Features

### 💾 Drive & Partition Management

- **Disk & Partition Auto-Discovery**
  - Detects physical drives and partitions using `lsblk`.
  - Displays filesystem information and mount status.
  - Uses `findmnt` to determine active mount points.

- **Automatic Unmounting**
  - Automatically unmounts the selected target partition before recovery.
  - Helps prevent filesystem activity from interfering with the carving process.
  - Attempts to restore the previous mount state when recovery is complete.

- **Destination Selection**
  - Choose where recovered files will be stored.
  - Keeps recovered data separate from the source device.

### 🎯 Targeted File Recovery

- **Free-Space Carving**
  - Recovery is focused on unallocated/free disk space.
  - Helps avoid unnecessarily processing existing active filesystem data.
  - Can significantly reduce scan time compared with scanning an entire partition.

- **File Type Selection**
  - Select individual file extensions instead of being limited to broad categories.
  - Enable or disable specific formats before beginning recovery.

- **File Categories**
  - 📷 Images
  - 🎬 Video
  - 🎵 Audio
  - 📄 Documents
  - 📦 Archives
  - 🗄️ Databases

### 🔍 Recovery Filtering

- **Minimum File Size**
  - Ignore extremely small carved files that are unlikely to be useful.

- **Image Dimension Filtering**
  - Set minimum pixel dimensions for recovered images.
  - Helps eliminate thumbnails, icons, previews, and other unwanted image fragments.

- **Post-Carving Classification**
  - Recovered files are automatically organized into appropriate category folders.

### 📊 Live Recovery Monitoring

- Real-time recovery progress.
- Live PhotoRec output monitoring.
- Live list of carved files.
- Recovery statistics.
- Detailed application logging.
- Automatic generation of a CSV recovery inventory.

The recovery inventory is saved as:

```text
PhotoRec_Recovery_Inventory.csv
```

The inventory can be opened in spreadsheet applications or processed with scripts for additional analysis.

### ⏯️ Pause & Resume

Long recovery operations can be temporarily suspended without terminating the recovery process.

HexVault uses:

```text
SIGSTOP
SIGCONT
```

to pause and resume the underlying recovery process.

This is useful when a recovery operation is running for an extended period and system resources are temporarily needed elsewhere.

### 🎨 Adaptive Interface

- Dark mode.
- Light mode.
- Automatic system-theme detection.
- Responsive Tkinter interface.
- Designed for Linux desktop environments.

### ⌨️ Keyboard Shortcuts

Common operations can be performed without reaching for the mouse.

| Shortcut | Action |
|---|---|
| `Ctrl + Enter` | Start recovery |
| `Space` | Pause / Resume recovery |
| `Ctrl + Q` | Exit application |
| `Ctrl + W` | Exit application |

---

## 📋 Prerequisites

HexVault requires:

- **Python 3**
- **Tkinter**
- **Pillow**
- **PhotoRec / TestDisk**
- **udisks2**
- A Linux desktop environment capable of running Tkinter applications
- `pkexec` / PolicyKit for privileged operations

### Debian / Ubuntu / Linux Mint / Parrot OS

```bash
sudo apt update
sudo apt install python3 python3-tk python3-pil python3-pil.imagetk testdisk udisks2
```

### Fedora

```bash
sudo dnf install python3 python3-tkinter python3-pillow testdisk udisks2
```

### Arch Linux

```bash
sudo pacman -S python python-pillow testdisk udisks2
```

---

## 🚀 Installation

Clone the repository and run the included installer.

### Clone the Repository

```bash
git clone https://github.com/your-username/HexVault.git
cd HexVault
```

> Replace `your-username` with the GitHub account that hosts the HexVault repository.

### Install

Make the installer scripts executable:

```bash
chmod +x install.sh uninstall.sh
```

Run the installer:

```bash
sudo ./install.sh
```

The installer will:

- Install the HexVault launcher to `/usr/local/bin/hexvault`
- Install the application to `/opt/hexvault`
- Install application icons
- Install the desktop entry
- Register HexVault with the Linux desktop application menu

Once installed, HexVault can be launched with:

```bash
hexvault
```

---

## 📁 Custom Installation Paths

The installer supports custom installation locations.

### Custom Launcher Location

```bash
sudo ./install.sh --bin-dir /usr/bin
```

### Custom Application Directory

```bash
sudo ./install.sh --app-dir /custom/location/hexvault
```

Both options can be used together if desired:

```bash
sudo ./install.sh \
  --bin-dir /usr/bin \
  --app-dir /opt/custom/hexvault
```

---

## 🖥️ Usage

After installation, HexVault can be launched from your desktop application's menu or from a terminal.

### Launch from Terminal

```bash
hexvault
```

Depending on your desktop environment, HexVault may appear under categories such as:

- **System**
- **Utilities**
- **Accessories**

---

# 🧭 Guided Recovery Workflow

HexVault uses a simple three-stage recovery workflow.

## 1. 💾 Setup & Drives

Select the storage device and partition you want to examine.

HexVault displays information about the selected storage device, including filesystem and mount information.

You can then choose the destination directory where recovered files will be stored.

### Typical workflow

```text
Select Drive
     ↓
Select Partition
     ↓
Review Filesystem Information
     ↓
Choose Recovery Destination
```

HexVault handles the necessary unmounting of the target partition before the carving operation begins.

---

## 2. 🔍 File Types & Filters

Select the file types you want PhotoRec to search for.

Rather than enabling an entire category, individual extensions can be selected or deselected.

For example, an image recovery can be limited to formats such as:

```text
.jpg
.jpeg
.png
.gif
.webp
.tiff
```

Additional filtering options can be configured to reduce unwanted recovery results.

### File Size Filtering

Set a minimum file size to eliminate very small fragments and files that are unlikely to be useful.

### Image Dimension Filtering

For image recovery, minimum width and height requirements can be specified.

For example:

```text
Minimum Width: 800 px
Minimum Height: 600 px
```

This can help eliminate:

- Thumbnail images
- Icons
- Preview images
- Small cached graphics
- Other low-resolution fragments

---

## 3. ⚡ Execution & Monitoring

Start the recovery process by clicking **Start Recovery** or pressing:

```text
Ctrl + Enter
```

HexVault will request administrator authorization when required.

Once recovery begins, the interface provides live information about the operation, including:

- Recovery progress
- Current activity
- Carved files
- Application logs
- Recovery statistics

Long-running operations can be temporarily paused using:

```text
Space
```

Pressing `Space` again resumes the recovery process.

---

## 📂 Recovered File Organization

Recovered files are automatically organized into category-based directories.

A typical recovery directory may look like:

```text
Recovery/
├── Images/
├── Video/
├── Audio/
├── Documents/
├── Archives/
├── Databases/
└── PhotoRec_Recovery_Inventory.csv
```

This keeps large recovery operations easier to navigate and makes it simpler to locate specific types of recovered data.

---

## 📊 Recovery Inventory

HexVault generates a CSV inventory containing information about recovered files.

The default filename is:

```text
PhotoRec_Recovery_Inventory.csv
```

This inventory can be used to:

- Review recovered files.
- Search recovery results.
- Sort files by category.
- Import results into spreadsheet software.
- Perform additional analysis with scripts.
- Maintain a record of the recovery operation.

---

## ⚠️ Recovery Considerations

HexVault is designed around **raw file carving**, which has some inherent limitations.

Because PhotoRec searches for recognizable file structures rather than relying exclusively on the filesystem directory structure:

- Original filenames may not be recoverable.
- Original directory paths may not be recoverable.
- Filesystem metadata may not be preserved.
- Fragmented files may be partially recovered or corrupted.
- Some recovered files may be incomplete.
- Files overwritten by new data generally cannot be recovered through carving.

### Protect the Source Drive

For the best chance of recovery, avoid writing new data to the drive being recovered.

Ideally:

```text
Source Drive
     │
     │  Read / Carve
     ▼
HexVault
     │
     │  Write recovered files
     ▼
Separate Destination Drive
```

**Never use the source drive as the recovery destination when avoidable.**

---

## 🔐 Privileged Operations

HexVault uses **PolicyKit (`pkexec`)** to perform operations that require elevated privileges.

The application is designed around a privileged execution interlock so that administrative authorization is requested when required rather than requiring the entire graphical application to be launched as root.

This helps keep the normal GUI process running under the user's desktop session while allowing specific storage operations to obtain the privileges they require.

---

## 🧩 How It Works

At a high level, HexVault acts as a graphical orchestration layer around PhotoRec.

```text
┌──────────────────────┐
│      HexVault GUI    │
│       Tkinter        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Drive / Partition    │
│ Discovery            │
│ lsblk / findmnt      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Privileged Storage   │
│ Operations           │
│ pkexec / udisks2     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      PhotoRec        │
│   File Carving       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Post-Recovery        │
│ Filtering & Routing  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Organized Recovery   │
│ Directory + CSV      │
└──────────────────────┘
```

---

## 📁 Project Structure

A typical HexVault installation contains components similar to:

```text
HexVault/
├── assets/
│   ├── banner.png
│   └── icon.png
│
├── install.sh
├── uninstall.sh
├── hexvault.py
├── LICENSE
└── README.md
```

The exact structure may change as the project develops.

---

## 🗑️ Uninstallation

To remove HexVault and clean up its system launcher, desktop entry, icons, and application files, run:

```bash
sudo ./uninstall.sh
```

If you installed HexVault using custom paths, provide the corresponding options supported by your installer.

---

## 🐛 Troubleshooting

### PhotoRec Not Found

Verify that TestDisk / PhotoRec is installed:

```bash
which photorec
```

If nothing is returned, install the `testdisk` package for your distribution.

### Tkinter Not Found

Verify Tkinter is available:

```bash
python3 -m tkinter
```

A small Tkinter test window should appear.

On Debian-based systems, install it with:

```bash
sudo apt install python3-tk
```

### Pillow Not Found

Verify Pillow:

```bash
python3 -c "from PIL import Image; print('Pillow OK')"
```

If necessary, install the distribution package:

```bash
sudo apt install python3-pil python3-pil.imagetk
```

### Permission / PolicyKit Problems

Verify that `pkexec` is available:

```bash
which pkexec
```

On Debian-based systems:

```bash
sudo apt install policykit-1
```

The exact PolicyKit package may vary between Linux distributions.

---

## 🤝 Contributing

Contributions, bug reports, feature requests, and improvements are welcome.

Before submitting a change, please consider:

1. Testing the change on a real Linux system.
2. Avoiding destructive operations on source storage.
3. Keeping recovery operations safe and predictable.
4. Preserving compatibility with supported Linux distributions.
5. Documenting significant behavioral changes.

If you're submitting a pull request, please include a clear description of what changed and why.

---

## 📜 License

HexVault is released under the:

**GNU General Public License v3.0 (GPLv3)**

See the [`LICENSE`](LICENSE) file for complete license details.

---

## 🧙 Attribution

**HexVault** is an independent graphical front-end created by **Siafu Linux**.

HexVault uses **PhotoRec**, part of the TestDisk project, as its underlying file-carving engine.

PhotoRec is developed by **Christophe GRENIER** and distributed as part of the **CGSecurity TestDisk project**.

- [CGSecurity](https://www.cgsecurity.org/)
- [TestDisk / PhotoRec](https://www.cgsecurity.org/wiki/PhotoRec)

HexVault is not affiliated with or endorsed by CGSecurity or Christophe GRENIER.

---

## ⭐ Support the Project

If HexVault helps you recover important files or makes PhotoRec easier to use, consider giving the project a ⭐ on GitHub.

Bug reports, feature ideas, and constructive feedback are also welcome.

---

<p align="center">
  <b>HexVault</b><br>
  <i>Turning raw disk fragments into recovered files.</i>
</p>
