# External tools

This directory intentionally contains no executables or shared libraries.

- Windows release builds download the pinned MKVToolNix archive from
  `mkvtoolnix.download`, verify both the publisher checksum and the SHA-256
  recorded in `packaging/dependencies.json`, and stage only `mkvmerge.exe`,
  `mkvpropedit.exe`, and their notices before packaging.
- Linux builds use the distribution-provided MKVToolNix package.
- Source users may install MKVToolNix normally or set `MKVTOOLNIX_PATH` or
  `MKVTOOLNIX_DIR`.

See `docs/BINARY_AUDIT.md` for the inventory and provenance policy.
