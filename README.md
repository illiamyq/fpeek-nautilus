# fpeek nautilus

Quick file metadata viewer for GNOME Files (Nautilus).
Right-click any file → **File Peek** → see readable metadata instantly. The plan is to adjust and build features for DCT/DFT conversion, spectral analysis of discrete signals (images/audio).

## Install
```bash
git clone https://github.com/illiamyq/fpeek-nautilus.git
cd fpeek-nautilus
./install.sh
```

Restart Nautilus:
```bash
killall nautilus && nautilus &
```

## Uninstall
```bash
rm ~/.local/share/nautilus-python/extensions/fpeek_nautilus.py
killall nautilus
```

## Implemented

- basic DFT analysis for images
- file hash calculator (MD5, SHA256)
- duplicate file finder
- mass export/share of metadata to archive

##  Posible enhancements

- custom metadata tags/notes
- lower level adjustments
- preferences file for basic directory/file analysis settings. Script to handle preferences

## Requirements

- Nautilus 43+
- Python 3.8+
- `nautilus-python`


## **Example Output **
```
Path: /home/usr/scripts
Type: Directory
Size: 102.0 B
Owner: usr:usr
Permissions: 755 (rwxr-xr-x)
Modified: 2025-12-28 18:16:28 (1mo ago)
Inode: 266376
```
