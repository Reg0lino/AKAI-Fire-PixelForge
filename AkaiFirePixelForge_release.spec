# PixelForge_for_Akai_Fire_release.spec
# For final distribution - hides console window.
# Creates a FOLDER bundle in dist/PixelForge for Akai Fire/

import os
import sys

def get_rtmidi_binary_info():
    try:
        import rtmidi
        import inspect
        rtmidi_package_path = os.path.dirname(inspect.getfile(rtmidi))
        found_binary_path = None
        for item_name in os.listdir(rtmidi_package_path):
            if item_name.startswith('_rtmidi.') and \
               (item_name.endswith('.pyd') or item_name.endswith('.so') or item_name.endswith('.dylib')):
                found_binary_path = os.path.join(rtmidi_package_path, item_name)
                print(f"INFO Spec (Release): Found rtmidi binary: {found_binary_path}")
                break
        if found_binary_path:
            return (found_binary_path, 'rtmidi') 
        else:
            print("WARNING Spec (Release): Could not automatically find _rtmidi binary.")
            return None
    except Exception as e:
        print(f"ERROR Spec (Release): Exception finding rtmidi binary: {e}")
        return None

binaries_to_bundle = []
rtmidi_info = get_rtmidi_binary_info()
if rtmidi_info:
    binaries_to_bundle.append(rtmidi_info)
else:
    print("CRITICAL Spec (Release): python-rtmidi binary not found. MIDI will likely fail.")

project_root = SPECPATH

datas_to_bundle = [
    (os.path.join(project_root, 'resources'), 'resources'),
    (os.path.join(project_root, 'presets'), 'presets'),
    (os.path.join(project_root, 'images'), 'images'),
]

# --- UPDATED for v2.0.0 ---
hidden_imports_list = [
    # Core Dependencies
    'mido.backends.rtmidi',
    'rtmidi',
    'pyaudiowpatch',
    'appdirs',
    'mss',
    'mss.windows',
    'mss.darwin',
    'mss.linux',
    'numpy',
    'numpy.core._dtype_ctypes',
    'packaging',
    'colorsys',
    'requests',
    'resources_rc',
    # PyQt6 Modules
    'PyQt6.sip',
    'PyQt6.QtNetwork',
    'PyQt6.QtGui',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    # Pillow Modules
    'PIL',
    'PIL._tkinter_finder',
    'PIL.ImageFont',
    'PIL.ImageDraw',
    'PIL.ImageEnhance',
    'PIL.ImageOps',
    'PIL.ImageSequence',
    'PIL.ImageColor',
    'PIL.ImageQt',
    # Our Project's Modules (made exhaustive for safety)
    'utils',
    'forge',
    'hardware.akai_fire_controller',
    'managers.oled_display_manager',
    'managers.hardware_input_manager',
    'managers.audio_visualizer_manager',
    'managers.color_fx_utils',
    'oled_utils.oled_renderer',
    'oled_utils.image_processing',
    'features.screen_sampler_core',
    'features.screen_sampler_thread',
    'features.gif_processing_engine',
    'animator.model',
    'animator.timeline_widget',
    'animator.controls_widget',
    'gui.main_window',
    'gui.animator_manager_widget',
    'gui.color_picker_manager',
    'gui.static_layouts_manager',
    'gui.interactive_pad_grid',
    'gui.screen_sampler_manager',
    'gui.screen_sampler_ui_manager',
    'gui.capture_preview_dialog',
    'gui.set_max_frames_dialog',
    'gui.gif_export_dialog',
    'gui.gif_import_dialog',
    'gui.gif_player_dialog',
    'gui.gif_region_selector',
    'gui.pad_preview_widget',
    'gui.oled_gif_export_dialog',
    'gui.monitor_view_widget',
    'gui.oled_customizer_dialog',
    'gui.app_guide_dialog',
    'gui.doom_instructions_dialog',
    'gui.audio_visualizer_ui_manager',
    'gui.visualizer_settings_dialog',
    'doom_feature.doom_game_controller',
]

a = Analysis(
    ['forge.py'], 
    pathex=[project_root],   
    binaries=binaries_to_bundle,
    datas=datas_to_bundle,
    hiddenimports=hidden_imports_list,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False, 
    cipher=None,
    noarchive=False 
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],  
    exclude_binaries=True, 
    name='PixelForge for Akai Fire',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, 
    upx=False,   
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True, 
    argv_emulation=False,
    target_arch=None, 
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'resources', 'icons', 'app_icon.ico')
)

coll = COLLECT(
    exe,       
    a.binaries, 
    a.zipfiles, 
    a.datas,    
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PixelForge for Akai Fire'
)