"""Decoder for Avon's SKIT container (written from the format description in
skijack's export.py docstring, not from Avon's or skijack's code):

    b"SKIT", version byte 1, three zero bytes, a 4-byte little-endian atom-table
    length (must be 0 here), an 8-byte little-endian bit count, then the bits,
    least significant first within each byte, in prefix order:
    00 = S, 01 = K, 10 = I, 11 = application (function, then argument).

Returns a mini term (str atoms, (fn, arg) tuples). Iterative.
"""

from __future__ import annotations

from pathlib import Path


def decode(data: bytes):
    if data[:4] != b"SKIT" or data[4] != 1:
        raise ValueError("not a SKIT v1 container")
    if int.from_bytes(data[8:12], "little") != 0:
        raise ValueError("SKIT atom tables are not supported")
    nbits = int.from_bytes(data[12:20], "little")
    body = data[20:]
    if len(body) * 8 < nbits:
        raise ValueError("SKIT body shorter than its bit count")

    def bit(i):
        return (body[i // 8] >> (i % 8)) & 1

    pos = 0
    # Each frame: [fn or None]; an application waits for two children.
    stack = []
    result = None
    while pos < nbits:
        a, b = bit(pos), bit(pos + 1)
        pos += 2
        if (a, b) == (1, 1):
            stack.append([None])
            continue
        node = {(0, 0): "S", (0, 1): "K", (1, 0): "I"}[(a, b)]
        while True:
            if not stack:
                result = node
                break
            fr = stack[-1]
            if fr[0] is None:
                fr[0] = node
                break
            stack.pop()
            node = (fr[0], node)
        if result is not None:
            break
    if result is None or stack or pos != nbits:
        raise ValueError("malformed SKIT bitstring")
    return result


def read(path) -> object:
    return decode(Path(path).read_bytes())
