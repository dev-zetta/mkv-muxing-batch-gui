# Changelog

All notable changes to this maintained fork are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.7.2] - 2026-08-27

### Fixed

- Treat failed `mkvmerge` and `mkvpropedit` processes as failures instead of
  reporting successful jobs from a zero progress value.
- Validate that muxing created a non-empty output before replacing a source
  file. Replacement now uses an atomic move where supported and never removes
  the source before the completed output has been verified.
- Calculate and apply CRC filenames from the actual completed output path,
  including source-replacement jobs.
- Prevent queue items from being freed twice during large batches, avoiding
  intermittent crashes and stalled UI updates.
- Honor **Discard Old Chapters** and **Discard Old Attachments** independently
  when constructing `mkvmerge` commands.
- Clear stale Fast Mux state after `mkvpropedit` jobs so later queue items do
  not inherit the previous job's execution mode.

### Changed

- Prefer a current system MKVToolNix installation, with explicit
  `MKVTOOLNIX_PATH` and `MKVTOOLNIX_DIR` overrides, before considering bundled
  tools.
- Store application data in platform-appropriate user data directories, with
  `MKV_MUXING_BATCH_GUI_DATA_DIR` available for portable and test setups.
- Update and pin the supported runtime and build dependencies: PySide6 6.11.2,
  psutil 7.2.2, comtypes 1.4.16, and PyInstaller 6.22.2.
- Point application update, support, download, and source links at the active
  `dev-zetta/mkv-muxing-batch-gui` fork.

### Added

- Add a Linux PyInstaller one-folder build that uses the distribution's
  MKVToolNix package rather than obsolete bundled binaries.
- Add a full application `--smoke-test` mode for validating packaged builds.
- Add regression tests for process failures, safe replacement, CRC handling,
  queue cleanup, chapter and attachment options, Fast Mux state, tool
  discovery, and data-directory selection.
- Add a complete snapshot and severity triage of all 121 issues from the
  original repository in `docs/UPSTREAM_ISSUES.md`.

[2.7.2]: https://github.com/dev-zetta/mkv-muxing-batch-gui/releases/tag/2.7.2
