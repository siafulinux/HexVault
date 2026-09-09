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

Instead of requiring users to navigate PhotoRec's interactive terminal interface, HexVault provides a clean, guided graphical workflow for selecting a storage device, selecting a partition, choosing recovery modes, filtering file types, configuring recovery options, and monitoring the recovery process.

HexVault is designed to make raw file carving more approachable while retaining the underlying recovery capabilities of PhotoRec.

The application provides both **broad recovery** and **targeted recovery** workflows, allowing users to recover an entire partition, search unallocated space, or limit recovery to selected filesystem directories when appropriate.

> **Important:** HexVault performs raw file carving. Recovered files may not retain their original filenames, directory structure, timestamps, or other filesystem metadata.

---

# ✨ Features

## 💾 Drive & Partition Management

### Disk & Partition Auto-Discovery

* Detects physical drives and partitions using `lsblk`.
* Displays device names, sizes, filesystems, and mount information.
* Uses `findmnt` to determine active mount points.
* Presents storage devices through a guided graphical interface.
* Helps distinguish physical drives from individual partitions.

### Partition Selection

* Select the specific partition to examine.
* Review filesystem and device information before recovery.
* Supports recovery workflows targeting individual partitions rather than requiring an entire physical disk.

### Automatic Unmounting

* Automatically unmounts the selected target partition when required.
* Helps prevent filesystem activity from interfering with recovery.
* Attempts to restore the previous mount state after recovery completes.
* Uses Linux storage-management tools rather than requiring the entire GUI to run as root.

### Read-Only Mounting

When appropriate, HexVault can work with source data in a read-only manner to reduce unnecessary writes to the recovery source.

This is particularly useful when inspecting an existing filesystem before beginning a carving operation.

### Destination Selection

* Choose where recovered files will be stored.
* Provides a graphical recovery-location selector.
* Keeps recovered data separate from the source device.
* Supports creating a new destination directory from the recovery-location interface.

> **Best practice:** Always recover files to a different physical storage device when possible.

---

# 🎯 Recovery Modes

HexVault supports multiple approaches to file recovery depending on what the user is trying to accomplish.

## 🗑️ Deleted File / Free-Space Recovery

Recovery can be focused on unallocated/free disk space.

This is useful when attempting to recover files that were deleted while leaving the existing filesystem intact.

Advantages include:

* Avoids unnecessarily processing active filesystem data.
* Can significantly reduce scan time.
* Reduces the amount of irrelevant recovery output.
* Helps focus the recovery operation on deleted data.

## 💽 Whole-Partition Recovery

HexVault can also perform a broader scan of the selected partition.

This is useful when:

* Filesystem metadata is damaged.
* Deleted-file recovery from free space is insufficient.
* The desired files may exist outside conventional free-space regions.
* A more comprehensive carving operation is required.

Because this mode can process substantially more data, recovery may take considerably longer.

## 📁 Existing Folder / Targeted Recovery

HexVault can optionally target specific directories instead of requiring an entire partition to be processed.

This provides a more focused workflow when the user knows approximately where the desired data was located.

A folder-selection interface allows directories to be selected individually rather than forcing the user to scan the entire filesystem.

Example:

```text
/home/user/
├── Documents/        ✓
├── Downloads/        ✓
├── Pictures/         ✓
├── Videos/           ✗
└── Music/            ✗
```

This can reduce unnecessary processing and make targeted recovery more practical.

> **Note:** Targeted directory recovery and raw carving have different characteristics. PhotoRec's ability to recover data depends on the selected recovery mode and the state of the filesystem.

---

# 🎯 Targeted File Recovery

## File Type Selection

HexVault provides detailed file-type controls instead of limiting users to broad categories.

Individual file extensions can be enabled or disabled before recovery.

For example, an image recovery can be restricted to:

```text
.jpg
.jpeg
.png
.webp
.tiff
```

while unwanted formats such as:

```text
.gif
.bmp
.ico
```

can be disabled.

This allows recovery operations to be tailored to the actual files being sought.

## File Type Categories

File formats are organized into practical categories:

* 📷 **Images**
* 🎬 **Video**
* 🎵 **Audio**
* 📄 **Documents**
* 📦 **Archives**
* 🗄️ **Databases**
* 💿 **Virtual Machines**

Each category provides controls for selecting or deselecting supported extensions.

### Category Select All

Each file-type category provides a convenient **Select All** control.

This allows users to:

* Enable all formats within a category.
* Quickly disable all formats.
* Then manually select only the extensions they actually need.

This is especially useful when performing focused recovery instead of scanning for every file format supported by PhotoRec.

---

# 🔍 Recovery Filtering

## Minimum File Size

HexVault can ignore extremely small carved files that are unlikely to be useful.

For example:

```text
Minimum File Size: 100 KB
```

can help reduce output containing tiny fragments and insignificant files.

The exact value can be adjusted depending on the recovery task.

## Image Dimension Filtering

Image recovery can be filtered using minimum pixel dimensions.

Example:

```text
Minimum Width: 800 px
Minimum Height: 600 px
```

This can help eliminate:

* Thumbnail images
* Icons
* Preview images
* Small cached graphics
* Web thumbnails
* Other low-resolution fragments

The feature is particularly useful when a drive contains large numbers of small image files.

## Post-Carving Classification

Recovered files are automatically analyzed and routed into appropriate category directories.

This makes large PhotoRec recovery operations significantly easier to navigate.

---

# 📂 Recovery Organization

Recovered files are organized into category-based directories rather than leaving the user with one large collection of mixed files.

A typical recovery directory may look like:

```text
Recovery/
├── Images/
├── Video/
├── Audio/
├── Documents/
├── Archives/
├── Databases/
├── Virtual Machines/
└── PhotoRec_Recovery_Inventory.csv
```

This organization makes it easier to locate useful results after a large carving operation.

---

# 📊 Live Recovery Monitoring

HexVault provides live feedback while recovery is running.

The interface can display:

* Real-time recovery progress.
* Live PhotoRec output.
* Current recovery activity.
* Carved-file information.
* Recovery statistics.
* Application logs.
* Recovery status.
* Generated recovery inventory information.

This allows users to monitor long-running operations without interacting with PhotoRec's terminal interface.

## Recovery Inventory

HexVault automatically generates a CSV inventory of recovered files.

The default filename is:

```text
PhotoRec_Recovery_Inventory.csv
```

The inventory can be opened using spreadsheet software or processed programmatically.

It can be used to:

* Review recovered files.
* Search recovery results.
* Sort files by category.
* Track recovered file paths.
* Import results into spreadsheet software.
* Perform additional analysis with scripts.
* Maintain a record of the recovery operation.

---

# ⏯️ Pause & Resume

Long recovery operations can be temporarily suspended without terminating the recovery process.

HexVault uses:

```text
SIGSTOP
SIGCONT
```

to pause and resume the underlying recovery process.

This is useful when a recovery operation is running for an extended period and system resources are temporarily needed elsewhere.

For example:

```text
Recovery Running
      │
      ▼
   Pause
      │
      ▼
SIGSTOP → PhotoRec suspended
      │
      ▼
   Resume
      │
      ▼
SIGCONT → PhotoRec continues
```

Pausing does not intentionally terminate the recovery process.

---

# 🎨 Adaptive Interface

HexVault is designed as a desktop application rather than a terminal wrapper.

Features include:

* Dark mode.
* Light mode.
* Automatic system-theme detection.
* Responsive Tkinter interface.
* Scrollable recovery controls.
* Scrollable file-type lists.
* Independent scrolling areas where appropriate.
* Guided recovery workflow.
* Graphical file and directory selection.
* Linux desktop integration.

The interface is designed to remain usable on different Linux desktop environments and screen sizes.

---

# 🖱️ Recovery Location Selector

The recovery destination can be selected through a graphical directory browser.

The location interface provides common navigation controls, including:

* Navigate into folders.
* Navigate to the parent directory.
* Create a new folder.
* Select the current directory as the recovery destination.

This avoids requiring users to manually enter complicated filesystem paths.

---

# ⌨️ Keyboard Shortcuts

Common operations can be performed without reaching for the mouse.

| Shortcut       | Action                  |
| -------------- | ----------------------- |
| `Ctrl + Enter` | Start recovery          |
| `Space`        | Pause / Resume recovery |
| `Ctrl + Q`     | Exit application        |
| `Ctrl + W`     | Exit application        |

---

# 🧭 Guided Recovery Workflow

HexVault uses a guided recovery workflow designed to take the user from storage selection through recovery monitoring without requiring direct interaction with PhotoRec's terminal UI.

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

If necessary, HexVault handles unmounting of the target partition before the carving operation begins.

---

## 2. 🎯 Recovery Mode

Choose the recovery approach appropriate for the situation.

Possible workflows include:

```text
Free Space
    │
    ├── Recover deleted data from unallocated space
    │
Whole Partition
    │
    └── Perform broader raw carving
    │
Targeted Folders
    │
    └── Focus recovery on selected filesystem directories
```

The appropriate mode depends on the condition of the filesystem and what data is being sought.

---

## 3. 📁 Select Folders

When using targeted recovery, HexVault provides a graphical folder-selection interface.

Users can select individual directories rather than automatically processing the entire filesystem.

Selected folders are shown separately from the directory tree, making it easier to review the current selection before starting recovery.

---

## 4. 🔍 File Types & Filters

Select the file types you want PhotoRec to search for.

Individual extensions can be selected or deselected.

For example:

```text
Images
├── .jpg       ✓
├── .jpeg      ✓
├── .png       ✓
├── .webp      ✓
├── .gif       ✗
└── .ico       ✗
```

Categories provide **Select All** controls for quickly configuring groups of formats.

### File Size Filtering

Set a minimum file size to eliminate very small fragments and files that are unlikely to be useful.

### Image Dimension Filtering

For image recovery, minimum width and height requirements can be specified.

Example:

```text
Minimum Width: 800 px
Minimum Height: 600 px
```

---

## 5. ⚡ Execution & Monitoring

Start the recovery process by clicking **Recover Deleted Files** or pressing:

```text
Ctrl + Enter
```

HexVault will request administrator authorization when required.

Once recovery begins, the interface provides live information about the operation, including:

* Recovery progress.
* Current activity.
* Carved files.
* Application logs.
* Recovery statistics.
* Recovery inventory information.

Long-running operations can be temporarily paused using:

```text
Space
```

Pressing `Space` again resumes the recovery process.

The recovery process can also be stopped using the **Stop Recovery** control.

The application can be closed using the **Exit** control when appropriate.

---

# 📂 Recovered File Organization

Recovered files are automatically organized into category-based directories.

A typical recovery directory may look like:

```text
Recovery/
├── Images/
│   ├── jpg/
│   ├── png/
│   └── webp/
├── Video/
├── Audio/
├── Documents/
├── Archives/
├── Databases/
├── Virtual Machines/
└── PhotoRec_Recovery_Inventory.csv
```

The exact directory structure depends on the selected recovery types and classification behavior.

---

# 📊 Recovery Inventory

HexVault generates a CSV inventory containing information about recovered files.

The default filename is:

```text
PhotoRec_Recovery_Inventory.csv
```

This inventory can be used to:

* Review recovered files.
* Search recovery results.
* Sort files by category.
* Import results into spreadsheet software.
* Perform additional analysis with scripts.
* Maintain a record of the recovery operation.

The inventory is particularly useful when recovering thousands of files and manually inspecting the recovery directory would be impractical.

---

# 🔐 Privileged Operations

HexVault uses **PolicyKit (`pkexec`)** to perform operations that require elevated privileges.

The application is designed around a privileged execution interlock so that administrative authorization is requested when required rather than requiring the entire graphical application to be launched as root.

This helps keep the normal GUI process running under the user's desktop session while allowing specific storage operations to obtain the privileges they require.

This design also helps avoid creating recovered files owned by `root` simply because the graphical application itself was launched with `sudo`.

---

# 🧩 How It Works

At a high level, HexVault acts as a graphical orchestration layer around PhotoRec and Linux storage utilities.

```text
┌──────────────────────────┐
│       HexVault GUI       │
│          Tkinter         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Drive / Partition        │
│ Discovery                │
│ lsblk / findmnt          │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Recovery Configuration   │
│                          │
│ • Recovery Mode          │
│ • Folder Selection       │
│ • File Types             │
│ • File Filters           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Privileged Storage       │
│ Operations               │
│ pkexec / udisks2         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│        PhotoRec          │
│      File Carving        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Post-Recovery Processing │
│                          │
│ • File Classification    │
│ • Size Filtering         │
│ • Image Filtering        │
│ • Inventory Generation   │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Organized Recovery       │
│ Directory + CSV          │
└──────────────────────────┘
```

---

# 🧱 Technology Stack

HexVault is built around established Linux and open-source technologies.

| Component            | Purpose                                       |
| -------------------- | --------------------------------------------- |
| Python 3             | Application logic                             |
| Tkinter              | Graphical user interface                      |
| Pillow               | Image processing and image-related operations |
| PhotoRec             | Raw file-carving engine                       |
| TestDisk             | PhotoRec distribution package                 |
| `lsblk`              | Drive and partition discovery                 |
| `findmnt`            | Mount-point detection                         |
| `udisks2`            | Linux storage management                      |
| PolicyKit / `pkexec` | Privileged operations                         |
| CSV                  | Recovery inventory generation                 |

---

# 📋 Prerequisites

HexVault requires:

* **Python 3**
* **Tkinter**
* **Pillow**
* **PhotoRec / TestDisk**
* **udisks2**
* A Linux desktop environment capable of running Tkinter applications
* `pkexec` / PolicyKit for privileged operations

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

# 🚀 Installation

Clone the repository and run the included installer.

## Clone the Repository

```bash
git clone https://github.com/your-username/HexVault.git
cd HexVault
```

> Replace `your-username` with the GitHub account that hosts the HexVault repository.

## Install

Make the installer scripts executable:

```bash
chmod +x install.sh uninstall.sh
```

Run the installer:

```bash
sudo ./install.sh
```

The installer will:

* Install the HexVault launcher to `/usr/local/bin/hexvault`
* Install the application to `/opt/hexvault`
* Install application icons
* Install the desktop entry
* Register HexVault with the Linux desktop application menu

Once installed, HexVault can be launched with:

```bash
hexvault
```

---

# 📁 Custom Installation Paths

The installer supports custom installation locations.

## Custom Launcher Location

```bash
sudo ./install.sh --bin-dir /usr/bin
```

## Custom Application Directory

```bash
sudo ./install.sh --app-dir /custom/location/hexvault
```

Both options can be used together:

```bash
sudo ./install.sh \
  --bin-dir /usr/bin \
  --app-dir /opt/custom/hexvault
```

---

# 🖥️ Usage

After installation, HexVault can be launched from your desktop application's menu or from a terminal.

## Launch from Terminal

```bash
hexvault
```

Depending on your desktop environment, HexVault may appear under categories such as:

* **System**
* **Utilities**
* **Accessories**

---

# ⚠️ Recovery Considerations

HexVault is designed around **raw file carving**, which has inherent limitations.

Because PhotoRec searches for recognizable file structures rather than relying exclusively on filesystem directory structures:

* Original filenames may not be recoverable.
* Original directory paths may not be recoverable.
* Filesystem metadata may not be preserved.
* Fragmented files may be partially recovered or corrupted.
* Some recovered files may be incomplete.
* Files overwritten by new data generally cannot be recovered through carving.
* Recovered files may contain duplicate or partially valid data.
* Recovery results should be manually verified when the data is important.

## Protect the Source Drive

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

For particularly important evidence or irreplaceable data, creating a forensic image of the source before recovery is preferable to repeatedly operating on the original media.

---

# 🛡️ Recovery Safety

HexVault is designed to minimize unnecessary writes to the recovery source.

Recommended practice:

1. Stop using the source drive as soon as possible.
2. Do not install software onto the source drive.
3. Do not save recovered files to the source drive.
4. Avoid modifying the filesystem before recovery.
5. Use a separate destination drive for recovered data.
6. For critical data, consider working from a disk image rather than the original device.

The less additional activity performed on the source storage, the better the chance that deleted data remains recoverable.

---

# 📁 Project Structure

A typical HexVault source tree contains components similar to:

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

# 🗑️ Uninstallation

To remove HexVault and clean up its system launcher, desktop entry, icons, and application files, run:

```bash
sudo ./uninstall.sh
```

If you installed HexVault using custom paths, provide the corresponding options supported by your installer.

---

# 🐛 Troubleshooting

## PhotoRec Not Found

Verify that TestDisk / PhotoRec is installed:

```bash
which photorec
```

If nothing is returned, install the `testdisk` package for your distribution.

---

## Tkinter Not Found

Verify Tkinter is available:

```bash
python3 -m tkinter
```

A small Tkinter test window should appear.

On Debian-based systems, install it with:

```bash
sudo apt install python3-tk
```

---

## Pillow Not Found

Verify Pillow:

```bash
python3 -c "from PIL import Image; print('Pillow OK')"
```

If necessary, install the distribution package:

```bash
sudo apt install python3-pil python3-pil.imagetk
```

---

## Permission / PolicyKit Problems

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

## Recovery Destination Permission Problems

If HexVault reports a permission error while preparing or clearing a recovery workspace, verify that the workspace is accessible to the user and that previous recovery runs did not leave behind files owned by another account.

For example:

```bash
ls -la /tmp/hexvault/
```

If a previous recovery was incorrectly run as `root`, files may need to have their ownership corrected before another recovery can begin.

Avoid routinely launching the entire GUI with:

```bash
sudo hexvault
```

HexVault is designed to request elevated privileges only for operations that require them.

---

# 🤝 Contributing

Contributions, bug reports, feature requests, and improvements are welcome.

Before submitting a change, please consider:

1. Testing the change on a real Linux system.
2. Avoiding destructive operations on source storage.
3. Keeping recovery operations safe and predictable.
4. Preserving compatibility with supported Linux distributions.
5. Documenting significant behavioral changes.
6. Testing both normal-user and privileged workflows.
7. Testing recovery against disposable or test media whenever possible.

If you're submitting a pull request, please include a clear description of what changed and why.

---

# 📜 License

HexVault is released under the:

**GNU General Public License v3.0 (GPLv3)**

See the [`LICENSE`](LICENSE) file for complete license details.

---

# 🧙 Attribution

**HexVault** is an independent graphical front-end created by **Siafu Linux**.

HexVault uses **PhotoRec**, part of the TestDisk project, as its underlying file-carving engine.

PhotoRec is developed by **Christophe GRENIER** and distributed as part of the **CGSecurity TestDisk project**.

* [CGSecurity](https://www.cgsecurity.org/)
* [TestDisk / PhotoRec](https://www.cgsecurity.org/wiki/PhotoRec)

HexVault is not affiliated with or endorsed by CGSecurity or Christophe GRENIER.

---

# ⭐ Support the Project

If HexVault helps you recover important files or makes PhotoRec easier to use, consider giving the project a ⭐ on GitHub.

Bug reports, feature ideas, and constructive feedback are also welcome.

---

<p align="center">
  <b>HexVault</b><br>
  <i>Turning raw disk fragments into recovered files.</i>
</p>
