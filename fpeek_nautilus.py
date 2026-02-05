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
            label='🔍',
            tip='fpeek metadata'
        )
        item.connect('activate', self.on_show_metadata, file)

        return [item]

    def on_show_metadata(self, menu, file):
        filepath = file.get_location().get_path()

        try:
            stat = os.stat(filepath)

            # Get human-readable owner/group
            try:
                owner_name = pwd.getpwuid(stat.st_uid).pw_name
            except KeyError:
                owner_name = str(stat.st_uid)

            try:
                group_name = grp.getgrgid(stat.st_gid).gr_name
            except KeyError:
                group_name = str(stat.st_gid)

            # Interpret permissions
            perms_octal = oct(stat.st_mode)[-3:]
            perms_human = self.interpret_permissions(perms_octal)

            # File type
            if os.path.isdir(filepath):
                file_type = "Directory"
            elif os.path.islink(filepath):
                file_type = "Symbolic Link"
            else:
                mime_type = mimetypes.guess_type(filepath)[0]
                if mime_type:
                    file_type = mime_type.split('/')[0].capitalize()
                else:
                    file_type = "File"

            # Build metadata text
            metadata = f"""<b>Path:</b> {filepath}

<b>Type:</b> {file_type}

<b>Size:</b> {self.format_size(stat.st_size)}

<b>Owner:</b> {owner_name}:{group_name}

<b>Permissions:</b> {perms_octal} ({perms_human})

<b>Modified:</b> {self.format_time_ago(stat.st_mtime)}

<b>Inode:</b> {stat.st_ino}"""

        except Exception as e:
            metadata = f"<b>Error:</b> {str(e)}"

        # Create dialog
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
            ago = f"{diff.seconds // 60}m ago"
            color = "#6897BB"
        else:
            ago = "just now"
            color = "#6897BB"

        return f"{formatted} (<span foreground='{color}'>{ago}</span>)"
