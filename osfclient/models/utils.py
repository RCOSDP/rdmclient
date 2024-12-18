from typing import Any, AsyncIterable, Dict
from urllib.parse import urlparse, parse_qs


DEFAULT_UPLOAD_BLOCK_SIZE = 1024 * 1024 * 128  # 128 MB


async def chunked_bytes_iterator(
    content: Any,
    chunk_size=DEFAULT_UPLOAD_BLOCK_SIZE
) -> AsyncIterable[bytes]:
    """Yield chunks of bytes from an asynchronous file-like object."""
    if not hasattr(content, 'read'):
        raise ValueError('content must have a read method')
    while True:
        chunk = await content.read(chunk_size)
        if len(chunk) == 0:
            break
        yield chunk

def merge_query_params(url: str, params: Dict[str, str]) -> Dict[str, str]:
    """Merge query parameters into a new dictionary with the existing query parameters of a URL."""
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    new_query = dict([(k, v[0]) for k, v in query.items()])
    new_query.update(params)
    return new_query
