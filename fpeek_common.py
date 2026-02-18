#!/usr/bin/env python3
import os
import json
import hashlib
import subprocess
from datetime import datetime


def calculate_hash(filepath, algorithm='sha256'):
    try:
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, PermissionError) as e:
        return f"Error: {str(e)}"
    except Exception:
        return None


def get_media_metadata(filepath):
    if not os.path.isfile(filepath):
        return None

    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', filepath],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    except Exception:
        pass
    return None


def get_mime_type(filepath):
    """Get MIME type"""
    if os.path.isdir(filepath):
        return 'inode/directory'

    try:
        result = subprocess.run(
            ['file', '--mime-type', '-b', filepath],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'


def format_size(size):
    if size is None or size < 0:
        return "Unknown"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def get_file_metadata(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Path does not exist: {filepath}")

    try:
        stat = os.stat(filepath)
    except PermissionError:
        raise PermissionError(f"Permission denied: {filepath}")

    metadata = {
        'filename': os.path.basename(filepath),
        'filepath': filepath,
        'is_directory': os.path.isdir(filepath),
        'size_bytes': stat.st_size,
        'size_human': format_size(stat.st_size),
        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
        'permissions': oct(stat.st_mode)[-3:],
        'owner_uid': stat.st_uid,
        'group_gid': stat.st_gid,
        'mime_type': get_mime_type(filepath),
        'extension': os.path.splitext(filepath)[1] if os.path.isfile(filepath) else '',
    }

    return metadata