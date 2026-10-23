"""Upload a local uploads/ directory to a private Supabase Storage bucket.

This script only transfers files when --upload is passed. It does not publish
the app or make the bucket public.
"""

from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from storage import storage_backend, storage_write_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('uploads_dir', type=Path, help='Pasta local uploads/')
    parser.add_argument('--upload', action='store_true', help='Confirma a transferência para o bucket Supabase configurado')
    args = parser.parse_args()
    if not args.upload:
        parser.error('Este script apenas lista arquivos. Acrescente --upload para transferi-los.')
    if storage_backend() != 'supabase':
        parser.error('Defina STORAGE_BACKEND=supabase e configure as variáveis SUPABASE_* no ambiente.')
    root = args.uploads_dir.expanduser().resolve()
    if not root.is_dir():
        parser.error(f'Pasta não encontrada: {root}')
    files = sorted(path for path in root.rglob('*') if path.is_file())
    for path in files:
        key = path.relative_to(root).as_posix()
        mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        storage_write_bytes(key, path.read_bytes(), mime)
        print(f'Enviado: {key}')
    print(f'Transferência concluída: {len(files)} arquivo(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
