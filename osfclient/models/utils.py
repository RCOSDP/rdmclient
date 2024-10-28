from typing import Any, AsyncIterable


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
