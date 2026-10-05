"""Repo files: metadata for siblings, tree and resolve, and the bytes served.

Recorded values from the seed are served verbatim. What the fixtures do not give is derived
deterministically from **stub bytes** (out-of-scope.md: real file serving is out of the slice),
using the same derivations HF's recorded values satisfy, so oids, sizes, ETags and the bytes served
agree with each other:
- a file's `oid` (and its resolve `ETag`) is the git blob sha1 of its content [verified on the
  three recorded files, 2026-10-05-clone-seed-reads.json];
- an LFS file's `oid` is the git blob sha1 of its LFS pointer, whose length is `pointerSize`
  [verified on the recorded pytorch_model.bin: 135 bytes, oid 05cfb29b…].
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass

MASK = "*" * 64
CHUNK = 1 << 20


def git_blob_oid(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def lfs_pointer(sha256: str, size: int) -> bytes:
    return f"version https://git-lfs.github.com/spec/v1\noid sha256:{sha256}\nsize {size}\n".encode()


def _stub_pattern(repo_id: str, path: str) -> bytes:
    return f"clone stub: {repo_id}/{path}\n".encode()


def stub_chunks(repo_id: str, path: str, size: int) -> Iterator[bytes]:
    """`size` bytes of a repeated, file-specific pattern, in chunks."""
    pattern = _stub_pattern(repo_id, path)
    block = pattern * max(1, CHUNK // len(pattern))
    remaining = size
    while remaining > 0:
        piece = block[: min(remaining, len(block))]
        remaining -= len(piece)
        yield piece


HASH_UP_TO = 8 << 20  # bigger stubs are not hashed at load time


def _hash_stub(algo: str, repo_id: str, path: str, size: int) -> str:
    """The hash of the stub content (git blob sha1, or sha256 for LFS). Stubs above HASH_UP_TO get
    a hash of their description instead, so loading a seed with multi-GB declared files stays
    instant; their oid then does not match the served bytes (stub files only)."""
    h = hashlib.new(algo)
    if size > HASH_UP_TO:
        h.update(f"clone stub {repo_id}/{path} {size}".encode())
        return h.hexdigest()
    if algo == "sha1":
        h.update(b"blob %d\x00" % size)
    for chunk in stub_chunks(repo_id, path, size):
        h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class FileMeta:
    path: str
    oid: str  # git blob sha1 of the content (or of the LFS pointer)
    size: int  # served size (the LFS object's size for LFS files)
    text: bytes | None  # recorded content, if any; stub bytes otherwise
    lfs_oid: str | None = None  # sha256 of the LFS object
    lfs_pointer_size: int | None = None
    xet_hash: str | None = None

    @property
    def is_lfs(self) -> bool:
        return self.lfs_oid is not None


def file_meta(repo_id: str, path: str, entry: dict) -> FileMeta:
    """Normalise one seed `files` entry (docs/system.md seed format)."""
    if "text" in entry:
        data = entry["text"].encode()
        return FileMeta(path, entry.get("oid") or git_blob_oid(data), len(data), data)
    default_size = len(_stub_pattern(repo_id, path))
    lfs = entry.get("lfs")
    if lfs:
        lfs = lfs if isinstance(lfs, dict) else {}
        size = lfs.get("size", entry.get("size", default_size))
        sha256 = lfs.get("oid") or _hash_stub("sha256", repo_id, path, size)
        pointer = lfs_pointer(sha256, size)
        # Provisional: a synthesised xet hash (the recorded tree carries one per LFS file).
        xet = entry.get("xetHash") or hashlib.sha256(b"xet:" + sha256.encode()).hexdigest()
        return FileMeta(path, entry.get("oid") or git_blob_oid(pointer), size, None,
                        sha256, lfs.get("pointerSize", len(pointer)), xet)
    size = entry.get("size", default_size)
    return FileMeta(path, entry.get("oid") or _hash_stub("sha1", repo_id, path, size), size, None)


def content_chunks(repo_id: str, meta: FileMeta) -> Iterator[bytes]:
    if meta.text is not None:
        yield meta.text
    else:
        yield from stub_chunks(repo_id, meta.path, meta.size)


class RepoFiles:
    """The file index of one repo: files by path plus the directories their paths imply."""

    def __init__(self, repo_id: str, files: dict[str, dict], dirs: dict[str, dict] | None = None):
        self.repo_id = repo_id
        self.files = {path: file_meta(repo_id, path, entry) for path, entry in files.items()}
        self._dir_oids = {path: d["oid"] for path, d in (dirs or {}).items() if "oid" in d}
        self.dirs = {"/".join(p.split("/")[:i]) for p in self.files for i in range(1, p.count("/") + 1)}

    def siblings(self) -> list[dict]:
        # Sorted by path, byte order [OBS: the 1018 recorded siblings are sorted].
        return [{"rfilename": p} for p in sorted(self.files)]

    def dir_oid(self, path: str) -> str:
        return self._dir_oids.get(path) or hashlib.sha1(f"clone tree {self.repo_id}/{path}".encode()).hexdigest()

    def tree(self, path: str, *, recursive: bool, mask_lfs: bool) -> list[dict] | None:
        """Entries under `path` ("" = root); None if `path` is not a directory.

        Order [OBS tree-main]: directories first, then files, each sorted by path.
        Provisional: a recursive listing applies the same rule to every depth, unpaginated.
        ACC-9 [OBS tree-masking]: with `mask_lfs` (callers without access) the LFS sha256 and the
        xet hash become 64 `*`; the git oid and sizes are never masked.
        """
        if path and path not in self.dirs:
            return None
        prefix = f"{path}/" if path else ""

        def under(p: str) -> bool:
            return p.startswith(prefix) and (recursive or "/" not in p[len(prefix):])

        out: list[dict] = [{"type": "directory", "oid": self.dir_oid(d), "size": 0, "path": d}
                           for d in sorted(d for d in self.dirs if under(d))]
        for p in sorted(p for p in self.files if under(p)):
            meta = self.files[p]
            entry: dict = {"type": "file", "oid": meta.oid, "size": meta.size}
            if meta.is_lfs:
                entry["lfs"] = {"oid": MASK if mask_lfs else meta.lfs_oid, "size": meta.size,
                                "pointerSize": meta.lfs_pointer_size}
                entry["xetHash"] = MASK if mask_lfs else meta.xet_hash
            entry["path"] = p
            out.append(entry)
        return out
