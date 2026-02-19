#!/usr/bin/env python3
import gi
gi.require_version('Nautilus', '4.1')
gi.require_version('Gtk', '4.0')

from gi.repository import Nautilus, GObject, Gtk, GdkPixbuf, Gio, GLib
import os
import json
from datetime import datetime
import subprocess
import tempfile
from fpeek_common import get_file_metadata, calculate_hash, get_media_metadata, format_size


class FpeekAnalysisExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def get_file_items(self, files):
        if len(files) != 1:
            return []

        file_info = files[0]

        item = Nautilus.MenuItem(
            name='FpeekAnalysisExtension::FullAnalysis',
            label='Full Analysis',
            tip='Detailed analysis with graphs and archive options'
        )
        item.connect('activate', self.on_analysis_click, file_info)

        return [item]

    def on_analysis_click(self, menu, file_info):
        file_path = file_info.get_location().get_path()

        if not os.path.exists(file_path):
            return

        if os.path.isdir(file_path):
            self.show_directory_analysis(file_path)
        else:
            self.show_file_analysis(file_path)

    def show_file_analysis(self, filepath):
        dialog = Gtk.Window()
        dialog.set_title("Full Analysis")
        dialog.set_default_size(700, 600)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)

        metadata = get_file_metadata(filepath)
        media_info = get_media_metadata(filepath)

        content = f"<b>File:</b> {metadata['filename']}\n"
        content += f"<b>Path:</b> {metadata['filepath']}\n"
        content += f"<b>Size:</b> {metadata['size_human']} ({metadata['size_bytes']} bytes)\n"
        content += f"<b>Type:</b> {metadata['mime_type']}\n\n"
        content += f"<b>Created:</b> {metadata['created']}\n"
        content += f"<b>Modified:</b> {metadata['modified']}\n"
        content += f"<b>Accessed:</b> {metadata['accessed']}\n\n"
        content += f"<b>Permissions:</b> {metadata['permissions']}\n"
        content += f"<b>Owner UID:</b> {metadata['owner_uid']}\n"
        content += f"<b>Group GID:</b> {metadata['group_gid']}\n"

        if media_info and 'format' in media_info:
            content += "\n<b>=== MEDIA INFO ===</b>\n\n"
            fmt = media_info['format']
            if 'duration' in fmt:
                duration = float(fmt['duration'])
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                content += f"<b>Duration:</b> {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            if 'bit_rate' in fmt:
                bitrate = int(fmt['bit_rate']) / 1000
                content += f"<b>Bitrate:</b> {bitrate:.2f} kb/s\n"

            for stream in media_info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    content += f"\n<b>Video:</b> {stream.get('codec_name', 'unknown')}\n"
                    if 'width' in stream and 'height' in stream:
                        content += f"<b>Resolution:</b> {stream['width']}x{stream['height']}\n"
                    if 'r_frame_rate' in stream:
                        content += f"<b>FPS:</b> {stream['r_frame_rate']}\n"
                elif stream.get('codec_type') == 'audio':
                    content += f"\n<b>Audio:</b> {stream.get('codec_name', 'unknown')}\n"
                    if 'sample_rate' in stream:
                        content += f"<b>Sample Rate:</b> {stream['sample_rate']} Hz\n"
                    if 'channels' in stream:
                        content += f"<b>Channels:</b> {stream['channels']}\n"

        label = Gtk.Label()
        label.set_markup(content)
        label.set_selectable(True)
        label.set_wrap(True)
        label.set_xalign(0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(label)
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        graph_btn = Gtk.Button(label="Generate Graph")
        graph_btn.connect('clicked', lambda w: self.on_generate_graph(filepath))
        button_box.append(graph_btn)

        archive_btn = Gtk.Button(label="Generate Archive")
        archive_btn.connect('clicked', lambda w: self.on_generate_archive(filepath))
        button_box.append(archive_btn)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect('clicked', lambda w: dialog.close())
        button_box.append(close_btn)

        main_box.append(button_box)
        dialog.set_child(main_box)
        dialog.present()

    def show_directory_analysis(self, dirpath):
        dialog = Gtk.Window()
        dialog.set_title("Directory Analysis")
        dialog.set_default_size(600, 500)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)

        total_files = 0
        total_dirs = 0
        total_size = 0

        for root, dirs, files in os.walk(dirpath):
            total_dirs += len(dirs)
            total_files += len(files)
            for filename in files:
                try:
                    total_size += os.path.getsize(os.path.join(root, filename))
                except:
                    pass

        content = f"<b>Directory:</b> {os.path.basename(dirpath)}\n"
        content += f"<b>Path:</b> {dirpath}\n\n"
        content += f"<b>Total Files:</b> {total_files}\n"
        content += f"<b>Total Subdirectories:</b> {total_dirs}\n"
        content += f"<b>Total Size:</b> {format_size(total_size)}\n"

        label = Gtk.Label()
        label.set_markup(content)
        label.set_selectable(True)
        label.set_wrap(True)
        label.set_xalign(0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(label)
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        archive_btn = Gtk.Button(label="Generate Archive")
        archive_btn.connect('clicked', lambda w: self.on_generate_archive(dirpath))
        button_box.append(archive_btn)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect('clicked', lambda w: dialog.close())
        button_box.append(close_btn)

        main_box.append(button_box)
        dialog.set_child(main_box)
        dialog.present()

    def on_generate_graph(self, filepath):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            mime_type = get_file_metadata(filepath).get('mime_type', '')

            if mime_type.startswith('image/'):
                from PIL import Image
                img = Image.open(filepath)
                img_array = np.array(img)

                fig, axes = plt.subplots(1, 3, figsize=(12, 4))
                fig.suptitle('Image Analysis')

                if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                    colors = ['red', 'green', 'blue']
                    for i, (ax, color) in enumerate(zip(axes, colors)):
                        ax.hist(img_array[:,:,i].ravel(), bins=256, color=color, alpha=0.7)
                        ax.set_title(f'{color.capitalize()} Channel')
                        ax.set_xlabel('Pixel Value')
                        ax.set_ylabel('Frequency')
                else:
                    axes[1].hist(img_array.ravel(), bins=256, color='gray')
                    axes[1].set_title('Grayscale Histogram')
                    axes[0].axis('off')
                    axes[2].axis('off')

                plt.tight_layout()
                output_path = filepath + '_graph.png'
                plt.savefig(output_path, dpi=100, bbox_inches='tight')
                plt.close()

                subprocess.run(['notify-send', 'Graph Generated', f'Saved to: {os.path.basename(output_path)}'])

            elif mime_type.startswith('audio/') or mime_type.startswith('video/'):
                result = subprocess.run([
                    'ffmpeg', '-i', filepath, '-ac', '1', '-ar', '8000',
                    '-f', 's16le', '-'
                ], capture_output=True, timeout=30)

                if result.returncode == 0:
                    audio_data = np.frombuffer(result.stdout, dtype=np.int16)
                    step = max(1, len(audio_data) // 10000)
                    audio_data = audio_data[::step]

                    fig, ax = plt.subplots(figsize=(12, 4))
                    time = np.arange(len(audio_data)) / 8000 * step
                    ax.plot(time, audio_data, linewidth=0.5)
                    ax.set_title('Audio Waveform')
                    ax.set_xlabel('Time (seconds)')
                    ax.set_ylabel('Amplitude')
                    ax.grid(True, alpha=0.3)

                    plt.tight_layout()
                    output_path = filepath + '_waveform.png'
                    plt.savefig(output_path, dpi=100, bbox_inches='tight')
                    plt.close()

                    subprocess.run(['notify-send', 'Graph Generated', f'Saved to: {os.path.basename(output_path)}'])
            else:
                subprocess.run(['notify-send', 'Graph Error', 'File type not supported for graphs'])

        except Exception as e:
            subprocess.run(['notify-send', 'Graph Error', str(e), '-u', 'critical'])

    def on_generate_archive(self, path):
        try:
            if os.path.isfile(path):
                file_size = os.path.getsize(path)
                max_file_size = 100 * 1024 * 1024 # 60 * 1024 * 1024

                if file_size > max_file_size:
                    subprocess.run([
                        'notify-send',
                        'Archive Error',
                        f'File too large ({format_size(file_size)}). Maximum size: 100 MB - ! can adjust fpeek_analysis line 255',
                        '-u', 'critical'
                    ])
                    return

                metadata = get_file_metadata(path)
                metadata['checksums'] = {
                    'md5': calculate_hash(path, 'md5'),
                    'sha256': calculate_hash(path, 'sha256'),
                }
                media_info = get_media_metadata(path)
                if media_info:
                    metadata['media'] = media_info

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_name = os.path.splitext(os.path.basename(path))[0]
                archive_path = os.path.join(os.path.dirname(path), f"{base_name}_metadata_{timestamp}.json")

                with open(archive_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                subprocess.run(['notify-send', 'Archive Created', f'Saved to: {os.path.basename(archive_path)}'])

            else:
                total_files = 0
                max_files = 1000

                for root, dirs, files in os.walk(path):
                    total_files += len(files)
                    if total_files > max_files:
                        subprocess.run([
                            'notify-send',
                            'Archive Error',
                            f'Too many files (>{max_files}). Dir too large to archive - adjust in fpeek_analysis line 294.',
                            '-u', 'critical'
                        ])
                        return

                if total_files == 0:
                    subprocess.run([
                        'notify-send',
                        'Archive Error',
                        'No files found in directory',
                        '-u', 'critical'
                    ])
                    return

                metadata = {
                    'directory': path,
                    'generated': datetime.now().isoformat(),
                    'files': []
                }

                for root, dirs, files in os.walk(path):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        try:
                            file_meta = get_file_metadata(filepath)
                            file_meta['relative_path'] = os.path.relpath(filepath, path)
                            file_meta['checksums'] = {
                                'md5': calculate_hash(filepath, 'md5'),
                                'sha256': calculate_hash(filepath, 'sha256'),
                            }
                            metadata['files'].append(file_meta)
                        except:
                            pass

                metadata['summary'] = {
                    'total_files': len(metadata['files']),
                    'total_size_bytes': sum(f.get('size_bytes', 0) for f in metadata['files']),
                }
                metadata['summary']['total_size_human'] = format_size(
                    metadata['summary']['total_size_bytes']
                )

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dir_name = os.path.basename(path.rstrip('/'))
                archive_path = os.path.join(path, f"{dir_name}_archive_{timestamp}.json")

                with open(archive_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                subprocess.run(['notify-send', 'Archive Created', f"{len(metadata['files'])} files archived"])

        except Exception as e:
            subprocess.run(['notify-send', 'Archive Error', str(e), '-u', 'critical'])