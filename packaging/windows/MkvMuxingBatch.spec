# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path


project_root = Path(SPECPATH).parents[1]
resources_root = project_root / "Resources"


def collect_files(source, destination):
    files = []
    for file_path in source.rglob("*"):
        if file_path.is_file():
            relative_parent = file_path.relative_to(source).parent
            files.append((str(file_path), str(Path(destination) / relative_parent)))
    return files


datas = []
for directory_name in ("Fonts", "Icons", "Languages"):
    datas.extend(collect_files(resources_root / directory_name, f"Resources/{directory_name}"))

mkvtoolnix_bundle = os.environ.get("MKVTOOLNIX_BUNDLE_DIR")
if not mkvtoolnix_bundle:
    raise SystemExit(
        "MKVTOOLNIX_BUNDLE_DIR is required. Run packaging/windows/build_release.ps1."
    )
mkvtoolnix_bundle = Path(mkvtoolnix_bundle).resolve()
for required_name in ("mkvmerge.exe", "mkvpropedit.exe", "PROVENANCE.json"):
    if not (mkvtoolnix_bundle / required_name).is_file():
        raise SystemExit(f"Verified MKVToolNix bundle is missing {required_name}")
datas.extend(collect_files(mkvtoolnix_bundle, "Resources/Tools/Windows64"))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=["comtypes.client"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MKV Muxing Batch GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    version=str(Path(SPECPATH) / "VersionFile.txt"),
    icon=str(resources_root / "Icons" / "App.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MKV Muxing Batch GUI",
)
