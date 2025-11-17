block_cipher = None

a = Analysis(
    ['gui_tarefas.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('mcp_tarefas_factorial.py', '.'),  # Inclui o módulo
    ],
    hiddenimports=[
        'mcp_tarefas_factorial',
        'google.oauth2.credentials',
        'googleapiclient.discovery',
        'google.auth.transport.requests',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ProcessadorTarefas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)