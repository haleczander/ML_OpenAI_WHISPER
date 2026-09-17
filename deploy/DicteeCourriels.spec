from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


project_root = Path(SPECPATH).parent.resolve()
ffmpeg_dir = project_root / "vendor" / "ffmpeg" / "bin"

datas = [(str(project_root / "static"), "static")]
datas += collect_data_files("whisper")

binaries = [
    (str(ffmpeg_dir / "ffmpeg.exe"), "vendor/ffmpeg/bin"),
    (str(ffmpeg_dir / "ffprobe.exe"), "vendor/ffmpeg/bin"),
]

a = Analysis(
    [str(project_root / "server.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
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
    name="DicteeCourriels",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DicteeCourriels",
)
