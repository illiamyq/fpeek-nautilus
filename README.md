# fpeek 🔍

Quick file metadata viewer for GNOME Files (Nautilus).
Right-click any file → **File Peek** → see readable metadata instantly. The plan is to adjust and build features for DCT/DFT conversion, spectral analysis of discrete signals (images/audio).

## Install
```bash
git clone https://github.com/illiamyq/fpeek-nautilus-ext.git
cd fpeek-nautilus-ext
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

## Roadmap

- Audio/video metadata (duration, codec, bitrate)
- file hash calculator (MD5, SHA256)
- git file status 
- duplicate file finder
- custom metadata tags/notes
- preview
- mass export of metadata to archive 
- SETTINGS

## Requirements

- Nautilus 43+
- Python 3.8+
- `nautilus-python`


## **Example Output (Improved)**
```
Path: /home/usr/scripts
Type: Directory
Size: 102.0 B
Owner: usr:usr
Permissions: 755 (rwxr-xr-x)
Modified: 2025-12-28 18:16:28 (1mo ago)
Inode: 266376
```
