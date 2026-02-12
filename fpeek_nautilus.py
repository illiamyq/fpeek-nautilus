#!/usr/bin/env python3
"""
fpeek - File Peek Nautilus Extension
Shows detailed file metadata in context menu
"""

import gi
gi.require_version('Nautilus', '4.1')
gi.require_version('Gtk', '4.0')

from gi.repository import Nautilus, GObject, Gtk, GdkPixbuf, Gio, GLib, Gdk
import os
import pwd
import grp
from datetime import datetime
import mimetypes
import hashlib
import subprocess
import json

try:
    import numpy as np
    from PIL import Image
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import io
    import base64
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
                file_hash = self.calculate_hash(filepath)
                if file_hash:
                    # Sreadable hash parts
                    hash_formatted = ' '.join([file_hash[i:i + 8] for i in range(0, len(file_hash), 8)])
                    metadata += f"""
───────────────────────
<b>SHA256 Hash:</b>
<span font_family='monospace' size='small'>{hash_formatted}</span>"""
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
                if IS_IMG:
                    try:
                        img = Image.open(filepath)
                        metadata += f"""
───────────────────────
<b>Image Info:</b>
  Dimensions: {img.width} x {img.height}
  Color Mode: {img.mode}
  Format: {img.format}"""
                    except Exception as e:
                        metadata += f"""
───────────────────────
<b>Image Info:</b> Error - {str(e)}"""
                else:
                    metadata += """
───────────────────────
<b>Image Analysis:</b> Install numpy and pillow"""
            if mime_type and (mime_type.startswith('audio/') or mime_type.startswith('video/')):
                try:
                    result = subprocess.run(
                        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        duration_sec = float(data.get('format', {}).get('duration', 0))
                        mins, secs = divmod(int(duration_sec), 60)
                        bitrate = int(data.get('format', {}).get('bit_rate', 0)) // 1000
                        video_info = None
                        audio_info = None
                        for stream in data.get('streams', []):
                            if stream.get('codec_type') == 'video' and not video_info:
                                video_info = stream
                            elif stream.get('codec_type') == 'audio' and not audio_info:
                                audio_info = stream
                        if mime_type.startswith('video/') and video_info:
                            width = video_info.get('width', 'N/A')
                            height = video_info.get('height', 'N/A')
                            fps = video_info.get('r_frame_rate', 'N/A')
                            if '/' in str(fps):
                                num, den = fps.split('/')
                                fps = f"{int(num) / int(den):.2f}"
                            video_codec = video_info.get('codec_name', 'N/A')
                            metadata += f"""
───────────────────────
<b>Video Info:</b>
  Duration: {mins}:{secs:02d}
  Resolution: {width}x{height}
  FPS: {fps}
  Video Codec: {video_codec}
  Bitrate: {bitrate} kbps"""
                            if audio_info:
                                audio_codec = audio_info.get('codec_name', 'N/A')
                                sample_rate = audio_info.get('sample_rate', 'N/A')
                                channels = audio_info.get('channels', 'N/A')
                                metadata += f"""
  Audio Codec: {audio_codec}
  Sample Rate: {sample_rate} Hz
  Channels: {channels}"""
                        elif mime_type.startswith('audio/') and audio_info:
                            audio_codec = audio_info.get('codec_name', 'N/A')
                            sample_rate = audio_info.get('sample_rate', 'N/A')
                            channels = audio_info.get('channels', 'N/A')
                            metadata += f"""
───────────────────────
<b>Audio Info:</b>
  Duration: {mins}:{secs:02d}
  Codec: {audio_codec}
  Bitrate: {bitrate} kbps
  Sample Rate: {sample_rate} Hz
  Channels: {channels}"""
                        tags = data.get('format', {}).get('tags', {})
                        if tags:
                            title = tags.get('title', tags.get('TITLE', 'Unknown'))
                            artist = tags.get('artist', tags.get('ARTIST', 'Unknown'))
                            if title != 'Unknown' or artist != 'Unknown':
                                metadata += f"""

<b>Tags:</b>
  Title: {title}
  Artist: {artist}"""
                except subprocess.TimeoutExpired:
                    metadata += """
───────────────────────
<b>Media Info:</b> Timeout reading file"""
                except FileNotFoundError:
                    metadata += """
───────────────────────
<b>Media Info:</b> Install ffmpeg"""
                except Exception as e:
                    metadata += f"""
───────────────────────
<b>Media Info:</b> Error - {str(e)}"""
        except Exception as e:
            metadata = f"<b>Error:</b> {str(e)}"
        dialog = Gtk.Window()
        dialog.set_title("File Peek")
        dialog.set_default_size(650, 500)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        label = Gtk.Label()
        label.set_markup(metadata)
        label.set_selectable(True)
        label.set_wrap(False)
        label.set_xalign(0)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(label)
        scrolled.set_vexpand(True)
        main_box.append(scrolled)
        if mime_type and mime_type.startswith('image/') and IS_IMG:
            spectrum_btn = Gtk.Button(label="Show DFT Frequency")
            spectrum_btn.connect('clicked', self.show_spectrum_window, filepath)
            main_box.append(spectrum_btn)
        copy_path_btn = Gtk.Button(label="Copy Path")
        copy_path_btn.connect('clicked', lambda w: self.copy_to_clipboard(filepath))
        main_box.append(copy_path_btn)
        close_btn = Gtk.Button(label="Close")
        close_btn.connect('clicked', lambda w: dialog.close())
        main_box.append(close_btn)
        dialog.set_child(main_box)
        dialog.present()

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def interpret_permissions(self, octal):
        perms = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']
        result = []
        for digit in octal:
            result.append(perms[int(digit)])
        perm_str = ''.join(result)
        if octal[2] in ['2', '3', '6', '7']:
            color = "#FF6B68"
            return f"<span foreground='{color}'>{perm_str}</span>"
        elif octal[1] in ['6', '7']:
            color = "#CC7832"
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

    def copy_to_clipboard(self, text):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

    def find_duplicates(self, filepath):
        try:
            file_hash = self.calculate_hash(filepath)
            directory = os.path.dirname(filepath)
            duplicates = []
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if full_path == filepath or os.path.isdir(full_path):
                    continue
                try:
                    if os.path.getsize(full_path) != os.path.getsize(filepath):
                        continue
                    other_hash = self.calculate_hash(full_path)
                    if other_hash == file_hash:
                        duplicates.append(filename)
                except (OSError, PermissionError):
                    continue
            return duplicates
        except Exception:
            return None

    def calculate_hash(self, filepath, algorithm='sha256'):
        hash_func = hashlib.new(algorithm)
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return None

    def dft_graph(self, filepath):
        if not IS_IMG:
            return None
        try:
            img = Image.open(filepath).convert('L')
            img_array = np.array(img)
            dft = np.fft.fft2(img_array)
            dft_shift = np.fft.fftshift(dft)
            magnitude = np.abs(dft_shift)
            avg_spectrum = np.mean(magnitude, axis=0)
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(avg_spectrum)
            ax.set_title('1D Frequency Spectrum')
            ax.set_xlabel('Frequency')
            ax.set_ylabel('Magnitude')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            return base64.b64encode(buf.read()).decode('utf-8')
        except:
            return None

    def show_spectrum_window(self, button, filepath):
        spectrum_b64 = self.dft_graph(filepath)
        if not spectrum_b64:
            return
        img_data = base64.b64decode(spectrum_b64)
        input_stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(img_data))
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream(input_stream, None)
        spectrum_win = Gtk.Window()
        spectrum_win.set_title("1D Frequency Plot")
        spectrum_win.set_default_size(700, 450)
        picture = Gtk.Picture.new_for_pixbuf(pixbuf)
        spectrum_win.set_child(picture)
        spectrum_win.present()