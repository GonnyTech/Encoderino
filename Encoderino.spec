from pathlib import Path

project_root = Path(SPECPATH)

analysis = Analysis(
    ["gui/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ("firmware", "firmware"),
        ("tools/arduino-cli", "tools/arduino-cli"),
    ],
    hiddenimports=["pystray._win32"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Encoderino",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="Encoderino",
)
