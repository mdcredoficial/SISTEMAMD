"""Private file storage with a local backend and Supabase Storage for hosting."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from urllib.parse import quote


class StorageError(RuntimeError):
    pass


def storage_backend() -> str:
    return os.getenv('STORAGE_BACKEND', 'local').strip().lower()


def storage_key(value: str | Path) -> str:
    """Convert old BASE_DIR paths and new upload names into safe bucket keys."""
    raw = str(value).replace('\\', '/').strip()
    if raw.startswith('uploads/'):
        raw = raw[len('uploads/'):]
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {'', '.', '..'} for part in path.parts):
        raise StorageError('Caminho de arquivo inválido.')
    return path.as_posix()


def _local_path(key: str) -> Path:
    upload_root = Path(os.getenv('LOCAL_DATA_DIR', Path(__file__).resolve().parent)).expanduser().resolve() / 'uploads'
    result = (upload_root / storage_key(key)).resolve()
    if result != upload_root and upload_root not in result.parents:
        raise StorageError('Caminho de arquivo inválido.')
    return result


def _supabase_config() -> tuple[str, str, str]:
    project_url = os.getenv('SUPABASE_URL', '').rstrip('/')
    api_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', '')
    if not project_url or not api_key or not bucket:
        raise StorageError('Configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e SUPABASE_STORAGE_BUCKET.')
    return project_url, api_key, bucket


def _remote_url(key: str) -> tuple[str, dict[str, str]]:
    project_url, api_key, bucket = _supabase_config()
    encoded_key = quote(storage_key(key), safe='/')
    encoded_bucket = quote(bucket, safe='')
    return (
        f'{project_url}/storage/v1/object/{encoded_bucket}/{encoded_key}',
        {'apikey': api_key, 'Authorization': f'Bearer {api_key}'},
    )


def storage_save(file_storage, key: str) -> str:
    key = storage_key(key)
    if storage_backend() == 'local':
        target = _local_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        file_storage.save(target)
        return key
    if storage_backend() != 'supabase':
        raise StorageError('STORAGE_BACKEND deve ser local ou supabase.')
    import requests

    url, headers = _remote_url(key)
    headers.update({'Content-Type': file_storage.mimetype or 'application/octet-stream', 'x-upsert': 'true'})
    file_storage.stream.seek(0)
    response = requests.post(url, headers=headers, data=file_storage.stream, timeout=30)
    if response.status_code not in {200, 201}:
        raise StorageError(f'Falha ao salvar arquivo no armazenamento remoto ({response.status_code}).')
    return key


def storage_write_bytes(key: str, content: bytes, content_type: str = 'application/octet-stream') -> str:
    key = storage_key(key)
    if storage_backend() == 'local':
        target = _local_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key
    if storage_backend() != 'supabase':
        raise StorageError('STORAGE_BACKEND deve ser local ou supabase.')
    import requests

    url, headers = _remote_url(key)
    headers.update({'Content-Type': content_type, 'x-upsert': 'true'})
    response = requests.post(url, headers=headers, data=content, timeout=30)
    if response.status_code not in {200, 201}:
        raise StorageError(f'Falha ao salvar arquivo no armazenamento remoto ({response.status_code}).')
    return key


def _is_missing_object(response) -> bool:
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    return str(payload.get('statusCode', '')) == '404' or payload.get('code') == 'NoSuchKey'


def storage_get(key: str) -> bytes:
    if storage_backend() == 'local':
        return _local_path(key).read_bytes()
    import requests

    url, headers = _remote_url(key)
    response = requests.get(url, headers=headers, timeout=30)
    if _is_missing_object(response):
        raise FileNotFoundError(key)
    if response.status_code != 200:
        raise StorageError(f'Falha ao ler arquivo do armazenamento remoto ({response.status_code}).')
    return response.content


def storage_exists(key: str) -> bool:
    if storage_backend() == 'local':
        return _local_path(key).is_file()
    import requests

    url, headers = _remote_url(key)
    response = requests.get(url, headers=headers, stream=True, timeout=15)
    is_missing = _is_missing_object(response)
    response.close()
    if is_missing:
        return False
    if response.status_code != 200:
        raise StorageError(f'Falha ao verificar arquivo no armazenamento remoto ({response.status_code}).')
    return True


def storage_delete(key: str) -> None:
    key = storage_key(key)
    if storage_backend() == 'local':
        _local_path(key).unlink(missing_ok=True)
        return
    if not storage_exists(key):
        return
    import requests

    project_url, api_key, bucket = _supabase_config()
    url = f"{project_url}/storage/v1/object/{quote(bucket, safe='')}"
    response = requests.delete(
        url,
        headers={'apikey': api_key, 'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'prefixes': [key]},
        timeout=30,
    )
    if response.status_code not in {200, 204}:
        raise StorageError(f'Falha ao excluir arquivo do armazenamento remoto ({response.status_code}).')
