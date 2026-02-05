#!/usr/bin/env python3
"""
fpeek - File Peek Nautilus Extension
Shows detailed file metadata in context menu
"""

import gi
gi.require_version('Nautilus', '4.1')
gi.require_version('Gtk', '4.0')

from gi.repository import Nautilus, GObject, Gtk
import os
import pwd
import grp
from datetime import datetime
import mimetypes
import hashlib

try:
    import numpy as np
    from PIL import Image
    IS_IMG = True
except ImportError:
    IS_IMG = False

class FPeekExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def get_file_items(self, files):
        if len(files) != 1:
            return []

        file = files[0]

        if file.get_uri_scheme() != 'file':
            return []

        item = Nautilus.MenuItem(
            name='FPeekExtension::ShowMetadata',
            label='peek file metadata',
            tip='fpeek metadata',
        )
        item.connect('activate', self.on_show_metadata, file)

        return [item]

    def on_show_metadata(self, menu, file):
        filepath = file.get_location().get_path()

        try:
            stat = os.stat(filepath)
            try:
                owner_name = pwd.getpwuid(stat.st_uid).pw_name
            except KeyError:
                owner_name = str(stat.st_uid)

            try:
                group_name = grp.getgrgid(stat.st_gid).gr_name
            except KeyError:
                group_name = str(stat.st_gid)
            perms_octal = oct(stat.st_mode)[-3:]
            perms_human = self.interpret_permissions(perms_octal)

            mime_type = mimetypes.guess_type(filepath)[0]

            if os.path.isdir(filepath):
                file_type = "Directory"
            elif os.path.islink(filepath):
                file_type = "Symbolic Link"
            else:
                if mime_type:
                    file_type = mime_type.split('/')[0].capitalize()
                else:
                    file_type = "File"

            metadata = f"""<b>Path:</b> {filepath}

        <b>Type:</b> {file_type}
    
        <b>Size:</b> {self.format_size(stat.st_size)}
    
        <b>Owner:</b> {owner_name}:{group_name}
    
        <b>Permissions:</b> {perms_octal} ({perms_human})
    
        <b>Modified:</b> {self.format_time_ago(stat.st_mtime)}
    
        <b>Inode:</b> {stat.st_ino}"""

            if not os.path.isdir(filepath) and not os.path.islink(filepath):
                duplicates = self.find_duplicates(filepath)
                if duplicates:
                    dup_count = len(duplicates)
                    wasted_space = stat.st_size * dup_count
                    metadata += f"""
            ───────────────────────
            <b>Duplicates:</b> {dup_count} found in same directory
            <b>Wasted Space:</b> {self.format_size(wasted_space)}
            <b>Files:</b> {', '.join(duplicates[:5])}"""
                    if dup_count > 5:
                        metadata += f" (+{dup_count - 5} more)"


            if mime_type and mime_type.startswith('image/'):
                img_data = self.analyze_image(filepath)
                if img_data:
                    if 'error' in img_data:
                        metadata += f"\n\n<b>Image Analysis:</b> Error - {img_data['error']}"
                    else:
                        metadata += f"""
    ───────────────────────
    <b>Image Analysis:</b>
      Dimensions: {img_data['width']} x {img_data['height']}
      Color Mode: {img_data['mode']}
      Format: {img_data['format']}

    <b>Frequency Domain (DFT):</b>
      Mean Frequency: {img_data['mean_frequency']:.2f}
      Max Frequency: {img_data['max_frequency']:.2f}
      Sharpness: {img_data['sharpness']:.2f}%"""
                elif not IS_IMG:
                    metadata += "\n\n<b>Image Analysis:</b> Install numpy and pillow"

        except Exception as e:
            metadata = f"<b>Error:</b> {str(e)}"

        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text="File Peek"
        )
        dialog.set_property("secondary-text", "")
        dialog.set_property("secondary-use-markup", True)

        label = Gtk.Label()
        label.set_markup(metadata)
        label.set_selectable(True)
        label.set_wrap(False)  # updated + margin not fixed
        label.set_xalign(0)  # Left

        label.set_margin_start(20)
        label.set_margin_end(20)
        label.set_margin_top(10)
        label.set_margin_bottom(10)

        box = dialog.get_content_area()
        box.append(label)

        dialog.present()
        dialog.connect('response', lambda d, r: d.destroy())

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def interpret_permissions(self, octal):
        """octal permissions to rwx with colors"""
        perms = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']
        result = []
        for digit in octal:
            result.append(perms[int(digit)])
        perm_str = ''.join(result)

        if octal[2] in ['2', '3', '6', '7']:
            color = "#FF6B68"  # dangerous
            return f"<span foreground='{color}'>{perm_str}</span>"
        elif octal[1] in ['6', '7']:
            color = "#CC7832"  # caution
            return f"<span foreground='{color}'>{perm_str}</span>"
        else:
            return perm_str

    def format_time_ago(self, timestamp):
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        diff = now - dt

        formatted = dt.strftime('%Y-%m-%d %H:%M:%S')

        if diff.days > 365:
            ago = f"{diff.days // 365}y ago"
            color = "#999999"
        elif diff.days > 30:
            ago = f"{diff.days // 30}mo ago"
            color = "#CC7832"
        elif diff.days > 7:
            ago = f"{diff.days}d ago"
            color = "#6A8759"
        elif diff.days > 0:
            ago = f"{diff.days}d ago"
            color = "#6A8759"
        elif diff.seconds > 3600:
            ago = f"{diff.seconds // 3600}h ago"
            color = "#6897BB"
        elif diff.seconds > 60:
            ago = f"{diff.seconds // 60}min ago"
            color = "#6897BB"
        else:
            ago = "just now"
            color = "#6897BB"

        return f"{formatted} (<span foreground='{color}'>{ago}</span>)"

    def find_duplicates(self, filepath):
        try:
            file_hash = self.calculate_hash(filepath)
            directory = os.path.dirname(filepath)
            current_filename = os.path.basename(filepath)

            duplicates = []
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if full_path == filepath or os.path.isdir(full_path):
                    continue

                try:
                    # (size==size) filter
                    if os.path.getsize(full_path) != os.path.getsize(filepath):
                        continue
                    other_hash = self.calculate_hash(full_path)

                    if other_hash == file_hash:
                        duplicates.append(filename)
                except (OSError, PermissionError):
                    continue

            # duplicates.extend(self.search_home_duplicates(file_hash, filepath))

            return duplicates
        except Exception as e:
            return None

    def calculate_hash(self, filepath, algorithm='sha256'):
        """hash based search, read in chunks for large files"""
        hash_func = hashlib.new(algorithm)

        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return None

    # search from home
    # def search_home_duplicates(self, file_hash, original_path):

    #     return duplicates

    def analyze_image(self, filepath):
        """DFT TRANSFORM"""
        if not IS_IMG:
            return None

        try:
            img = Image.open(filepath)
            img_gray = img.convert('L')
            img_array = np.array(img_gray)

            dft = np.fft.fft2(img_array)
            dft_shift = np.fft.fftshift(dft)

            magnitude = np.abs(dft_shift)
            width, height = img.size
            mean_freq = np.mean(magnitude)
            max_freq = np.max(magnitude)

            center_y, center_x = magnitude.shape[0] // 2, magnitude.shape[1] // 2
            radius = min(center_y, center_x) // 3

            high_freq_mask = np.ones_like(magnitude, dtype=bool)
            y, x = np.ogrid[:magnitude.shape[0], :magnitude.shape[1]]
            mask = (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
            high_freq_mask[mask] = False

            high_freq_energy = np.sum(magnitude[high_freq_mask])
            total_energy = np.sum(magnitude)
            sharpness_ratio = (high_freq_energy / total_energy) * 100

            return {
                'width': width,
                'height': height,
                'mode': img.mode,
                'format': img.format,
                'mean_frequency': mean_freq,
                'max_frequency': max_freq,
                'sharpness': sharpness_ratio
            }
        except Exception as e:
            return {'error': str(e)}