import os
from PyInstaller.utils.hooks import collect_data_files

# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Inclui TODOS os arquivos da pasta Resources
resources_files = collect_data_files('Resources', include_py_files=False)

a = Analysis(
    ['Main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Face Recognition
        (
            r'C:\Users\yago_\AppData\Local\Programs\Python\Python311\Lib\site-packages\face_recognition_models\models\*.dat',
            'face_recognition_models/models'
        ),

        # Inclui TODA a pasta Resources
        # Tree('Resources', prefix='Resources'),

        # Ou especifique manualmente:
         ('Resources/background.png', 'Resources'),
         ('Resources/Modes/1.png', 'Resources/Modes'),
         ('Resources/Modes/2.png', 'Resources/Modes'),
         ('Resources/Modes/3.png', 'Resources/Modes'),
         ('Resources/Modes/4.png', 'Resources/Modes')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
