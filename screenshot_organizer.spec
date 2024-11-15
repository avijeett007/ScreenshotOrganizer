# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect hidden imports
hidden_imports = [
    'PIL',
    'together',
    'requests',
    'pystray',
    'webbrowser',
    'platform',
    'json',
    'logging',
    'traceback',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets'
]

# Collect data files
datas = []
datas += collect_data_files('together')

# Platform-specific settings
if sys.platform == 'darwin':  # macOS
    icon_file = 'icon.icns'
elif sys.platform == 'win32':  # Windows
    icon_file = 'icon.ico'
else:  # Linux
    icon_file = 'icon.png'

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ScreenshotOrganizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScreenshotOrganizer',
)

# macOS specific
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='ScreenshotOrganizer.app',
        icon=icon_file,
        bundle_identifier='com.kno2gether.screenshotorganizer',
        version='1.0.0',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
