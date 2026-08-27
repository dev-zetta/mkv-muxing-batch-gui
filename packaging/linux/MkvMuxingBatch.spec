# -*- mode: python ; coding: utf-8 -*-
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

# Linux builds intentionally use a current system MKVToolNix. The binaries
# historically committed under Resources/Tools/Linux require obsolete shared
# libraries and do not produce a portable application on current distributions.
a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["comtypes"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="mkv-muxing-batch-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
