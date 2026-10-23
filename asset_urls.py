"""Content-addressed local assets: changed files cannot reuse an old SW entry."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

STATIC_ROOT = Path(__file__).resolve().parent / 'static'


def workspace_id() -> str:
    """Identify this checkout without disclosing its local filesystem path."""
    return sha256(str(STATIC_ROOT.parent.resolve()).casefold().encode()).hexdigest()[:24]


@lru_cache(maxsize=256)
def _digest(path: Path, modified_ns: int, size: int) -> str:
    return sha256(path.read_bytes()).hexdigest()[:16]


def asset_url(url: str) -> str:
    if not url.startswith('/static/'):
        raise ValueError('Only local static assets can be fingerprinted')
    path = (STATIC_ROOT / url.removeprefix('/static/')).resolve()
    if not path.is_relative_to(STATIC_ROOT.resolve()):
        raise ValueError('Asset must stay within the static directory')
    stat = path.stat()
    return f'{url}?asset={_digest(path, stat.st_mtime_ns, stat.st_size)}'
