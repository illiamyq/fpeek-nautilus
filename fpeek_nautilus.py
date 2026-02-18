#!/usr/bin/env python3
"""
fpeek - File Peek Nautilus Extension
Shows detailed file metadata in context menu
"""

import gi
gi.require_version('Nautilus', '4.1')

from gi.repository import Nautilus, GObject
import os
import subprocess
from fpeek_common import get_file_metadata, format_size, get_media_metadata


class FpeekExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def get_file_items(self, files):
        if len(files) != 1:
            return []

        file_info = files[0]

        item = Nautilus.MenuItem(
            name='FpeekExtension::QuickPeek',
            label='Quick Peek',
            tip='Quick preview of file/directory metadata'
        )
        item.connect('activate', self.on_peek_click, file_info)

        return [item]

    def count_directory_contents(self, dirpath):
        total_files = 0
        total_dirs = 0
        total_size = 0

        try:
            for root, dirs, files in os.walk(dirpath):
                total_dirs += len(dirs)
                total_files += len(files)

                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        total_size += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass

        return total_files, total_dirs, total_size

    def peek_directory(self, dirpath):
        try:
            stat = os.stat(dirpath)
            preview = f"Directory: {os.path.basename(dirpath)}\n\n"
            num_files, num_dirs, total_size = self.count_directory_contents(dirpath)
            preview += f"Files: {num_files}\n"
            preview += f"Subdirectories: {num_dirs}\n"
            preview += f"Total Size: {format_size(total_size)}\n"
            preview += f"Permissions: {oct(stat.st_mode)[-3:]}\n"
            return preview
        except Exception as e:
            return f"Error reading directory: {str(e)}"

    def peek_file(self, filepath):
        try:
            metadata = get_file_metadata(filepath)
            media_info = get_media_metadata(filepath)

            preview = f"File: {metadata['filename']}\n\n"
            preview += f"Size: {metadata['size_human']}\n"
            preview += f"Type: {metadata['mime_type']}\n"
            preview += f"Modified: {metadata['modified']}\n"
            preview += f"Permissions: {metadata['permissions']}\n"

            if media_info and 'format' in media_info:
                fmt = media_info['format']
                if 'duration' in fmt:
                    duration = float(fmt['duration'])
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    preview += f"\nDuration: {minutes}m {seconds}s\n"

                if 'bit_rate' in fmt:
                    bitrate = int(fmt['bit_rate']) / 1000
                    preview += f"Bitrate: {bitrate:.0f} kb/s\n"

            return preview

        except Exception as e:
            return f"Error reading file: {str(e)}"

    def on_peek_click(self, menu, file_info):
        file_path = file_info.get_location().get_path()

        if not os.path.exists(file_path):
            subprocess.run([
                'notify-send',
                'Quick Peek Error',
                'File or directory not found',
                '-u', 'critical'
            ])
            return

        if os.path.isdir(file_path):
            preview = self.peek_directory(file_path)
        else:
            preview = self.peek_file(file_path)

        subprocess.run([
            'notify-send',
            'Quick Peek',
            preview,
            '-t', '8000'
        ])