#!/usr/bin/env python3
"""Safely extract a verified Git archive into an empty staging directory."""

import hashlib
from pathlib import Path
import sys
import shutil
import tempfile
import tarfile

archive, destination, expected = sys.argv[1:]
try:
    if not hasattr(tarfile, 'data_filter'):
        raise ValueError('Safe extraction requires Python 3.11.8+ or 3.12+')
    with tempfile.TemporaryFile() as stream:
        with Path(archive).open('rb') as source:
            shutil.copyfileobj(source, stream)
        stream.seek(0)
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise ValueError('Archive changed before extraction')
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode='r:gz') as source:
            source.extractall(destination, filter='data')
except (OSError, ValueError, tarfile.TarError) as error:
    sys.exit(f'Git archive extraction failed: {error}')
