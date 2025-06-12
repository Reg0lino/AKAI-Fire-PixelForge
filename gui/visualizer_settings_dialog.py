# AKAI_Fire_RGB_Controller/gui/visualizer_settings_dialog.py

# TODO hardware inputs like knobs for brightness and speed as well as a dedicated start button
# TODO make sure the signals dont fuck up and override eachother, (knob 1 glb brightness)


import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QTabWidget, QWidget,
    QPushButton, QSlider, QGridLayout, QColorDialog, QListWidget, QListWidgetItem,
    QLineEdit, QInputDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QGroupBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QIcon

# --- Project-specific Imports for get_resource_path ---
try:
    from ..utils import get_resource_path
except ImportError:
    try:
        from utils import get_resource_path
    except ImportError:
        def get_resource_path(relative_path):  # Basic fallback
            print("VSD WARNING: Using basic fallback get_resource_path.")
            return relative_path
# --- End Project-specific Imports ---

DIALOG_NUMBER_OF_SPECTRUM_BARS = 8
COLOR_PROFILE_CONFIG_FILENAME = "visualizer_color_profiles.json"


class ColorGradientButton(QPushButton):
    def __init__(self, initial_color=QColor("gray"), parent=None):
        super().__init__(parent)
        self._bar_color = QColor(initial_color)
        self.setFixedSize(28, 22)
        self.setToolTip("Click to change color")

    def setColor(self, color: QColor):
        if self._bar_color != color:
            self._bar_color = QColor(color)
            self.update()

    def getColor(self) -> QColor:
        return QColor(self._bar_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        start_point_f = QPointF(rect.topLeft())
        end_point_f = QPointF(rect.bottomLeft())
        gradient = QLinearGradient(start_point_f, end_point_f)
        gradient.setColorAt(0, self._bar_color)
        gradient.setColorAt(1, self._bar_color.darker(180))
        painter.fillRect(rect, gradient)
        painter.setPen(QColor(50, 50, 50))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))


class VisualizerSettingsDialog(QDialog):
    all_settings_applied = pyqtSignal(dict)

    DEFAULT_SPECTRUM_BAR_COLORS_HEX = [
        QColor(Qt.GlobalColor.red).name(), QColor(Qt.GlobalColor.yellow).name(), QColor(
            Qt.GlobalColor.green).name(), QColor(Qt.GlobalColor.cyan).name(),
        QColor(Qt.GlobalColor.blue).name(), QColor(
            Qt.GlobalColor.magenta).name(), "#FFA500",  # Orange
        "#800080"  # Purple
    ]
    DEFAULT_SENSITIVITY_SLIDER = 50
    DEFAULT_SMOOTHING_SLIDER = 20

    PREFAB_PALETTES = {
        "classic_spectrum_bars": {
            "rainbow": {"band_colors": ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3", "#FF00FF"], "sensitivity": 50, "smoothing": 20, "grow_downwards": False},
            "fire_ice": {"band_colors": ["#FF4500", "#FF8C00", "#FFD700", "#FFFFE0", "#ADD8E6", "#87CEFA", "#4682B4", "#00008B"], "sensitivity": 55, "smoothing": 25, "grow_downwards": False},
            "synthwave": {"band_colors": ["#F92672", "#FD971F", "#E6DB74", "#A6E22E", "#66D9EF", "#AE81FF", "#CC66FF", "#FF00FF"], "sensitivity": 60, "smoothing": 15, "grow_downwards": False},
            "forest": {"band_colors": ["#228B22", "#3CB371", "#8FBC8F", "#556B2F", "#006400", "#90EE90", "#32CD32", "#008000"], "sensitivity": 45, "smoothing": 30, "grow_downwards": True},
            "ocean_sunset": {"band_colors": ["#FF4E50", "#FC913A", "#F9D423", "#EDE574", "#E1F5C4", "#ADD8E6", "#87CEEB", "#4682B4"], "sensitivity": 50, "smoothing": 22, "grow_downwards": False},
            # --- NEW PREFABS ADDED ---
            "doom_inferno": {
                "band_colors": ["#AA0000", "#D43500", "#FF6B00", "#5C2800", "#FFCC00", "#A0A0A0", "#606060", "#FF0000"],
                "sensitivity": 65, "smoothing": 10, "grow_downwards": False
            },
            "grayscale": {
                "band_colors": ["#FFFFFF", "#E0E0E0", "#C0C0C0", "#A0A0A0", "#808080", "#606060", "#404040", "#202020"],
                "sensitivity": 50, "smoothing": 20, "grow_downwards": False
            },
            "cool_blues": {
                "band_colors": ["#E0FFFF", "#B0E0E6", "#ADD8E6", "#87CEEB", "#6495ED", "#4169E1", "#0000CD", "#00008B"],
                "sensitivity": 50, "smoothing": 25, "grow_downwards": True
            },
            "matrix_code": {
                "band_colors": ["#33FF33", "#22DD22", "#11BB11", "#00AA00", "#008800", "#006600", "#004400", "#002200"],
                "sensitivity": 60, "smoothing": 10, "grow_downwards": True
            },
            "retro_sunset": {
                "band_colors": ["#FF4E50", "#FC913A", "#F9D423", "#FF8C00", "#E75A7C", "#734B5E", "#4A2C40", "#2C1B3E"],
                "sensitivity": 55, "smoothing": 20, "grow_downwards": False
            },
            "emerald_depths": {
                "band_colors": ["#50C878", "#2E8B57", "#3CB371", "#008080", "#20B2AA", "#48D1CC", "#AFEEEE", "#7FFFD4"],
                "sensitivity": 48, "smoothing": 30, "grow_downwards": False
            },
            "pastel_dreams": {
                "band_colors": ["#FFB6C1", "#FFDAB9", "#FFFFE0", "#E0FFFF", "#ADD8E6", "#D8BFD8", "#F0E68C", "#98FB98"],
                "sensitivity": 40, "smoothing": 35, "grow_downwards": False
            },
            "cyberpunk_neon": {
                "band_colors": ["#FF00FF", "#00FFFF", "#FFFF00", "#00FF00", "#FF4500", "#7D00FF", "#FF1493", "#1E90FF"],
                "sensitivity": 70, "smoothing": 5, "grow_downwards": True
            }
        },
        # "pulse_wave_matrix": {"rainbow": {"palette": ["#FF0000", "#FFFF00", "#0000FF"], "pulse_speed": 50}} # Example for other modes
    }

    def __init__(self, current_mode_key: str, all_current_settings: dict | None, config_save_path_func, parent=None):
        print(f"VSD TRACE: __init__ ENTERED. ID: {id(self)}") # DIAGNOSTIC
        super().__init__(parent)
        self.current_mode_key_on_open = current_mode_key
        self.config_save_path_func = config_save_path_func
        self.all_settings = {} # This will be the dialog's working copy of settings (UI Scale)
        if isinstance(all_current_settings, dict):
            for mode_key_iter, settings_val in all_current_settings.items():
                if isinstance(settings_val, dict):
                    self.all_settings[mode_key_iter] = settings_val.copy()
                    for list_key in ["band_colors", "palette", "spectrum_band_colors"]:
                        if list_key in self.all_settings[mode_key_iter] and \
                            isinstance(self.all_settings[mode_key_iter][list_key], list):
                            self.all_settings[mode_key_iter][list_key] = list(
                                self.all_settings[mode_key_iter][list_key])
                else:
                    self.all_settings[mode_key_iter] = settings_val
        else:
            self.all_settings = {}
        csb_defaults_ui = {
            "band_colors": list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX),
            "sensitivity": self.DEFAULT_SENSITIVITY_SLIDER,
            "smoothing": self.DEFAULT_SMOOTHING_SLIDER,
            "grow_downwards": False
        }
        current_csb_settings = self.all_settings.get("classic_spectrum_bars", {})
        self.all_settings["classic_spectrum_bars"] = {
            k: current_csb_settings.get(k, v) for k, v in csb_defaults_ui.items()
        }
        self.all_settings["classic_spectrum_bars"]["band_colors"] = list(self.all_settings["classic_spectrum_bars"]["band_colors"])
        pw_defaults_ui = {
            "color": QColor("cyan").name(),
            "speed": 50,
            "brightness_sensitivity": 75
        }
        current_pw_settings = self.all_settings.get("pulse_wave_matrix", {})
        self.all_settings["pulse_wave_matrix"] = {
            k: current_pw_settings.get(k, v) for k, v in pw_defaults_ui.items()
        }
        self.all_settings["pulse_wave_matrix"]["speed"] = int(self.all_settings["pulse_wave_matrix"]["speed"])
        self.all_settings["pulse_wave_matrix"]["brightness_sensitivity"] = int(self.all_settings["pulse_wave_matrix"]["brightness_sensitivity"])
        dvu_defaults_ui = {
            "vu_low_color": QColor(Qt.GlobalColor.green).name(),
            "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(),
            "vu_high_color": QColor(Qt.GlobalColor.red).name(),
            "vu_threshold_mid": 60,
            "vu_threshold_high": 85,
            "vu_falloff_speed": 50,
            "spectrum_band_colors": [QColor(Qt.GlobalColor.cyan).name()] * 5,
            "spectrum_sensitivity": 50,
            "spectrum_smoothing": 20,
            "spectrum_grow_downwards": False
        }
        current_dvu_settings = self.all_settings.get("dual_vu_spectrum", {})
        self.all_settings["dual_vu_spectrum"] = {
            k: current_dvu_settings.get(k,v) for k,v in dvu_defaults_ui.items()
        }
        self.all_settings["dual_vu_spectrum"]["spectrum_band_colors"] = list(self.all_settings["dual_vu_spectrum"]["spectrum_band_colors"])
        for key_dvu_slider in ["vu_threshold_mid", "vu_threshold_high", "vu_falloff_speed", "spectrum_sensitivity", "spectrum_smoothing"]:
            self.all_settings["dual_vu_spectrum"][key_dvu_slider] = int(self.all_settings["dual_vu_spectrum"][key_dvu_slider])
        self.all_settings["dual_vu_spectrum"]["spectrum_grow_downwards"] = bool(self.all_settings["dual_vu_spectrum"]["spectrum_grow_downwards"])
        self.setWindowTitle("⚙️ Visualizer Settings")
        self.setMinimumSize(800, 650)
        self.sb_sensitivity_slider: QSlider | None = None
        self.sb_sensitivity_label: QLabel | None = None
        self.sb_smoothing_slider: QSlider | None = None
        self.sb_smoothing_label: QLabel | None = None
        self.sb_color_buttons: list[ColorGradientButton] = []
        self.sb_reset_button: QPushButton | None = None
        self.sb_grow_downwards_checkbox: QCheckBox | None = None
        self.sb_palette_combobox: QComboBox | None = None
        self.sb_load_palette_button: QPushButton | None = None
        self.sb_profile_name_edit: QLineEdit | None = None
        self.sb_save_profile_button: QPushButton | None = None
        self.sb_delete_palette_button: QPushButton | None = None
        self.pw_color_button: ColorGradientButton | None = None
        self.pw_speed_slider: QSlider | None = None
        self.pw_speed_label: QLabel | None = None
        self.pw_brightness_sensitivity_slider: QSlider | None = None
        self.pw_brightness_sensitivity_label: QLabel | None = None
        self.dvu_low_color_button: ColorGradientButton | None = None
        self.dvu_mid_color_button: ColorGradientButton | None = None
        self.dvu_high_color_button: ColorGradientButton | None = None
        self.dvu_threshold_mid_slider: QSlider | None = None
        self.dvu_threshold_mid_label: QLabel | None = None
        self.dvu_threshold_high_slider: QSlider | None = None
        self.dvu_threshold_high_label: QLabel | None = None
        self.dvu_falloff_speed_slider: QSlider | None = None
        self.dvu_falloff_speed_label: QLabel | None = None
        self.dvu_spectrum_color_buttons: list[ColorGradientButton] = []
        self.dvu_spectrum_sensitivity_slider: QSlider | None = None
        self.dvu_spectrum_sensitivity_label: QLabel | None = None
        self.dvu_spectrum_smoothing_slider: QSlider | None = None
        self.dvu_spectrum_smoothing_label: QLabel | None = None
        self.dvu_spectrum_grow_downwards_checkbox: QCheckBox | None = None
        self.dvu_scheme_combobox: QComboBox | None = None
        self.dvu_load_scheme_button: QPushButton | None = None
        self.dvu_scheme_name_edit: QLineEdit | None = None
        self.dvu_save_scheme_button: QPushButton | None = None
        self.dvu_delete_scheme_button: QPushButton | None = None
        self.dvu_reset_settings_button: QPushButton | None = None
        self._last_saved_sb_palette_name: str | None = None # For internal use
        self._last_saved_dvu_scheme_name: str | None = None # For internal use
        self.color_profiles = {}
        
        self._init_ui()
        self._load_color_profiles()
        self._populate_ui_from_settings()
        self._select_initial_tab()
        print(f"VSD TRACE: __init__ EXITED. ID: {id(self)}") # DIAGNOSTIC

    def _get_color_profile_filepath(self) -> str:
        filepath = self.config_save_path_func(COLOR_PROFILE_CONFIG_FILENAME)
        # print(f"VSD DEBUG (_get_color_profile_filepath): Path for profiles JSON is: {filepath}") # Keep for debug if needed
        return filepath

    def _load_color_profiles(self):
        filepath = self._get_color_profile_filepath()
        # print(f"VSD DEBUG (_load_color_profiles): Attempting to load from: {filepath}")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Expecting format: {"profiles": {"ProfileName1": {"classic_spectrum_bars": {...}, "pulse_wave_matrix":{...}}, "ProfileName2": ...}}
                if isinstance(data, dict) and "profiles" in data and isinstance(data["profiles"], dict):
                    self.color_profiles = data["profiles"]
                    # print(f"VSD DEBUG (_load_color_profiles): Loaded profiles data: {self.color_profiles}")
                else:
                    # print(f"VSD WARNING (_load_color_profiles): JSON format incorrect. Expected 'profiles' key with dict value.")
                    self.color_profiles = {}
            except Exception as e:
                print(
                    f"VSD ERROR (_load_color_profiles): Error loading json: {e}")
                self.color_profiles = {}
        else:
            # print(f"VSD DEBUG (_load_color_profiles): File not found at {filepath}. Profiles empty.")
            self.color_profiles = {}

    def _save_color_profiles(self):
        filepath = self._get_color_profile_filepath()
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({"profiles": self.color_profiles}, f, indent=4)
            # print(f"VSD INFO (_save_color_profiles): Profiles saved to {filepath}")
        except Exception as e:
            QMessageBox.warning(self, "Profile Save Error",
                                f"Could not save profiles: {e}")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        sb_page = self._create_spectrum_bars_settings_tab()
        self.tab_widget.addTab(sb_page, "📊 Spectrum Bars")
        sb_page.setProperty("mode_key", "classic_spectrum_bars")
        pm_page = self._create_pulse_wave_settings_tab()
        self.tab_widget.addTab(pm_page, "🌊 Pulse Wave")
        pm_page.setProperty("mode_key", "pulse_wave_matrix")
        dv_page = self._create_dual_vu_settings_tab()
        self.tab_widget.addTab(dv_page, "🎶 Dual VU")
        dv_page.setProperty("mode_key", "dual_vu_spectrum")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        buttons.accepted.connect(self._apply_all_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def _populate_ui_from_settings(self):
        # --- Spectrum Bars Settings ---
        sb_settings = self.all_settings.get("classic_spectrum_bars", {})
        if self.sb_sensitivity_slider:
            slider_val_sens = sb_settings.get("sensitivity", self.DEFAULT_SENSITIVITY_SLIDER)
            self.sb_sensitivity_slider.setValue(slider_val_sens)
            self._update_sb_sensitivity_label(slider_val_sens)
        if self.sb_smoothing_slider:
            slider_val_smooth = sb_settings.get("smoothing", self.DEFAULT_SMOOTHING_SLIDER)
            self.sb_smoothing_slider.setValue(slider_val_smooth)
            self._update_sb_smoothing_label(slider_val_smooth)
        if self.sb_grow_downwards_checkbox:
            grow_down = sb_settings.get("grow_downwards", False)
            self.sb_grow_downwards_checkbox.setChecked(grow_down)
        sb_colors_data = sb_settings.get("band_colors", list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX))
        if hasattr(self, 'sb_color_buttons'):
            for i, button in enumerate(self.sb_color_buttons):
                if i < len(sb_colors_data):
                    button.setColor(QColor(sb_colors_data[i]))
                else:
                    button.setColor(QColor(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))
        if hasattr(self, 'sb_palette_combobox') and self.sb_palette_combobox is not None:
            print(f"VSD TRACE (_populate_ui_from_settings): Preparing to call _update_sb_palette_combobox. self.sb_palette_combobox IS: {self.sb_palette_combobox}")
            self._update_sb_palette_combobox()
        else:
            print("VSD ERROR (_populate_ui_from_settings): self.sb_palette_combobox is None or does not exist before calling update.")
        # --- Pulse Wave Settings ---
        pw_settings = self.all_settings.get("pulse_wave_matrix", {})
        if self.pw_color_button:
            self.pw_color_button.setColor(QColor(pw_settings.get("color", QColor("cyan").name())))
        if self.pw_speed_slider:
            speed_val = int(pw_settings.get("speed", 50))
            self.pw_speed_slider.setValue(speed_val)
            self._on_pw_speed_changed(speed_val)
        if self.pw_brightness_sensitivity_slider:
            bs_val = int(pw_settings.get("brightness_sensitivity", 75))
            self.pw_brightness_sensitivity_slider.setValue(bs_val)
            self._on_pw_brightness_sensitivity_changed(bs_val)
        # --- Dual VU Settings ---
        dvu_settings = self.all_settings.get("dual_vu_spectrum", {})
        if self.dvu_low_color_button: self.dvu_low_color_button.setColor(QColor(dvu_settings.get("vu_low_color", QColor(Qt.GlobalColor.green).name())))
        if self.dvu_mid_color_button: self.dvu_mid_color_button.setColor(QColor(dvu_settings.get("vu_mid_color", QColor(Qt.GlobalColor.yellow).name())))
        if self.dvu_high_color_button: self.dvu_high_color_button.setColor(QColor(dvu_settings.get("vu_high_color", QColor(Qt.GlobalColor.red).name())))
        if self.dvu_threshold_mid_slider:
            mid_thresh_val = int(dvu_settings.get("vu_threshold_mid", 60))
            self.dvu_threshold_mid_slider.setValue(mid_thresh_val)
            self._on_dvu_threshold_mid_changed(mid_thresh_val)
        if self.dvu_threshold_high_slider:
            high_thresh_val = int(dvu_settings.get("vu_threshold_high", 85))
            self.dvu_threshold_high_slider.setValue(high_thresh_val)
            self._on_dvu_threshold_high_changed(high_thresh_val)
        if self.dvu_falloff_speed_slider:
            falloff_val = int(dvu_settings.get("vu_falloff_speed", 50))
            self.dvu_falloff_speed_slider.setValue(falloff_val)
            self._on_dvu_falloff_speed_changed(falloff_val)
        dvu_spectrum_colors_data = dvu_settings.get("spectrum_band_colors", [QColor(Qt.GlobalColor.cyan).name()] * 5)
        if hasattr(self, 'dvu_spectrum_color_buttons'):
            for i, button in enumerate(self.dvu_spectrum_color_buttons):
                if i < len(dvu_spectrum_colors_data):
                    button.setColor(QColor(dvu_spectrum_colors_data[i]))
                else:
                    button.setColor(QColor(Qt.GlobalColor.gray))
        if self.dvu_spectrum_sensitivity_slider:
            sens_val = int(dvu_settings.get("spectrum_sensitivity", 50))
            self.dvu_spectrum_sensitivity_slider.setValue(sens_val)
            self._on_dvu_spectrum_sensitivity_changed(sens_val)
        
        if self.dvu_spectrum_smoothing_slider:
            smooth_val = int(dvu_settings.get("spectrum_smoothing", 20))
            self.dvu_spectrum_smoothing_slider.setValue(smooth_val)
            self._on_dvu_spectrum_smoothing_changed(smooth_val)
        if self.dvu_spectrum_grow_downwards_checkbox:
            grow_down_spec = dvu_settings.get("spectrum_grow_downwards", False)
            self.dvu_spectrum_grow_downwards_checkbox.setChecked(grow_down_spec)
        # --- CRITICAL CHECK FOR DVU COMBOBOX ---
        if hasattr(self, 'dvu_scheme_combobox') and self.dvu_scheme_combobox is not None:
            print(f"VSD TRACE (_populate_ui_from_settings): Preparing to call _update_dvu_scheme_combobox. self.dvu_scheme_combobox IS: {self.dvu_scheme_combobox} (ID: {id(self.dvu_scheme_combobox)})")
            self._update_dvu_scheme_combobox()
        else:
            print(f"VSD ERROR (_populate_ui_from_settings): self.dvu_scheme_combobox IS STILL None or does not exist before calling update. self ID: {id(self)}")

    def _select_initial_tab(self):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).property("mode_key") == self.current_mode_key_on_open:
                self.tab_widget.setCurrentIndex(i)
                return
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)

    def _create_spectrum_bars_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        page_main_layout = QVBoxLayout(page_widget)
        page_main_layout.setSpacing(10)
        page_main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        description_label = QLabel(
            "Configure 8 vertical bars that react to different audio frequencies. Customize colors, responsiveness, and direction.")
        description_label.setWordWrap(True)
        page_main_layout.addWidget(description_label)
        page_main_layout.addWidget(
            QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken))
        general_group = QGroupBox("General Settings")
        general_layout_grid = QGridLayout(general_group)
        row = 0
        general_layout_grid.addWidget(
            QLabel("Sensitivity:"), row, 0, Qt.AlignmentFlag.AlignRight)
        self.sb_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sb_sensitivity_slider.setRange(0, 100)
        self.sb_sensitivity_slider.setToolTip(
            "Adjusts the overall height responsiveness of the bars to audio.")
        self.sb_sensitivity_slider.valueChanged.connect(
            self._on_sb_sensitivity_changed)
        general_layout_grid.addWidget(self.sb_sensitivity_slider, row, 1)
        self.sb_sensitivity_label = QLabel("")
        self.sb_sensitivity_label.setMinimumWidth(45)
        general_layout_grid.addWidget(self.sb_sensitivity_label, row, 2)
        row += 1
        general_layout_grid.addWidget(
            QLabel("Smoothing Factor:"), row, 0, Qt.AlignmentFlag.AlignRight)
        self.sb_smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.sb_smoothing_slider.setRange(0, 99)
        self.sb_smoothing_slider.setToolTip(
            "Controls how quickly the bars react to changes in audio levels (higher = smoother, slower).")
        self.sb_smoothing_slider.valueChanged.connect(
            self._on_sb_smoothing_changed)
        general_layout_grid.addWidget(self.sb_smoothing_slider, row, 1)
        self.sb_smoothing_label = QLabel("")
        self.sb_smoothing_label.setMinimumWidth(45)
        general_layout_grid.addWidget(self.sb_smoothing_label, row, 2)
        row += 1
        self.sb_grow_downwards_checkbox = QCheckBox(
            "Grow Bars Downwards (from top)")
        self.sb_grow_downwards_checkbox.setToolTip(
            "If checked, bars grow from top down. Default is bottom up.")
        self.sb_grow_downwards_checkbox.stateChanged.connect(
            self._on_sb_grow_downwards_changed)
        general_layout_grid.addWidget(
            self.sb_grow_downwards_checkbox, row, 0, 1, 3)
        general_layout_grid.setColumnStretch(1, 1)
        page_main_layout.addWidget(general_group)
        colors_group_box = QGroupBox("Bar Colors (1-8)")
        colors_group_box.setToolTip(
            "Click each colored square to change the base color for the corresponding spectrum bar.")
        colors_main_layout = QVBoxLayout(colors_group_box)
        colors_buttons_layout = QHBoxLayout()
        colors_buttons_layout.setSpacing(6)
        self.sb_color_buttons = []
        for i in range(DIALOG_NUMBER_OF_SPECTRUM_BARS):
            color_button = ColorGradientButton(parent=self)
            color_button.setProperty("band_index", i)
            color_button.setToolTip(f"Click to change color for Bar {i+1}")
            color_button.clicked.connect(
                lambda checked=False, btn=color_button: self._on_dialog_sb_color_button_clicked(btn))
            self.sb_color_buttons.append(color_button)
            colors_buttons_layout.addWidget(color_button)
        colors_buttons_layout.addStretch(1)
        colors_main_layout.addLayout(colors_buttons_layout)
        page_main_layout.addWidget(colors_group_box)
        palette_group = QGroupBox("Palette Management")
        palette_layout_grid = QGridLayout(palette_group)
        row = 0
        palette_layout_grid.addWidget(
            QLabel("Preset:"), row, 0, Qt.AlignmentFlag.AlignRight)
        self.sb_palette_combobox = QComboBox()
        self.sb_palette_combobox.setToolTip(
            "Select a saved user palette or a built-in prefab palette.")
        self.sb_palette_combobox.currentIndexChanged.connect(
            self._on_sb_palette_combobox_changed)  # Connect here
        palette_layout_grid.addWidget(self.sb_palette_combobox, row, 1, 1, 2)
        self.sb_load_palette_button = QPushButton("⤵️ Load Selected")
        self.sb_load_palette_button.setToolTip(
            "Load the settings from the selected preset above.")
        try:
            self.sb_load_palette_button.setIcon(
                QIcon(get_resource_path("resources/icons/load.png")))
        except:
            pass
        self.sb_load_palette_button.clicked.connect(
            self._load_selected_sb_palette_from_combobox)
        palette_layout_grid.addWidget(self.sb_load_palette_button, row, 3)
        row += 1
        palette_layout_grid.addWidget(
            QLabel("Save Current As:"), row, 0, Qt.AlignmentFlag.AlignRight)
        self.sb_profile_name_edit = QLineEdit()
        self.sb_profile_name_edit.setPlaceholderText(
            "Enter new palette name...")
        self.sb_profile_name_edit.setToolTip(
            "Enter a name to save the current bar colors and settings as a new user palette.")
        palette_layout_grid.addWidget(self.sb_profile_name_edit, row, 1, 1, 2)
        self.sb_save_profile_button = QPushButton("💾 Save New")
        self.sb_save_profile_button.setToolTip(
            "Save the current bar settings with the name entered above.")
        try:
            self.sb_save_profile_button.setIcon(
                QIcon(get_resource_path("resources/icons/save.png")))
        except:
            pass
        self.sb_save_profile_button.clicked.connect(
            self._save_sb_current_as_profile)
        palette_layout_grid.addWidget(self.sb_save_profile_button, row, 3)
        row += 1
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.addStretch(1)
        self.sb_delete_palette_button = QPushButton(
            "🗑️ Delete Selected Preset")
        self.sb_delete_palette_button.setToolTip(
            "Delete the user preset selected in the 'Preset' dropdown above (Prefabs cannot be deleted).")
        try:
            self.sb_delete_palette_button.setIcon(
                QIcon(get_resource_path("resources/icons/delete.png")))
        except:
            pass
        self.sb_delete_palette_button.clicked.connect(
            self._delete_selected_sb_palette_from_combobox)
        action_buttons_layout.addWidget(self.sb_delete_palette_button)
        self.sb_reset_button = QPushButton("↺ Reset Current Bar Settings")
        self.sb_reset_button.setToolTip(
            "Reset all settings on this tab (colors, sensitivity, smoothing, direction) to application defaults.")
        self.sb_reset_button.clicked.connect(
            self._reset_spectrum_bars_settings_to_defaults)
        action_buttons_layout.addWidget(self.sb_reset_button)
        action_buttons_layout.addStretch(1)
        palette_layout_grid.addLayout(action_buttons_layout, row, 0, 1, 4)
        palette_layout_grid.setColumnStretch(1, 1)
        palette_layout_grid.setColumnStretch(2, 1)
        page_main_layout.addWidget(palette_group)
        page_main_layout.addStretch(1)
        return page_widget

    def _on_sb_grow_downwards_changed(self, state):
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["grow_downwards"] = bool(
            state == Qt.CheckState.Checked.value)

    def _on_sb_sensitivity_changed(self, value):
        self._update_sb_sensitivity_label(value)
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["sensitivity"] = value

    def _on_sb_smoothing_changed(self, value):
        self._update_sb_smoothing_label(value)
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["smoothing"] = value

    def _update_sb_sensitivity_label(self, value):
        if self.sb_sensitivity_label:
            self.sb_sensitivity_label.setText(f"{value / 50.0:.2f}x")

    def _update_sb_smoothing_label(self, value):
        if self.sb_smoothing_label:
            self.sb_smoothing_label.setText(f"{value / 100.0:.2f}")

    def _on_dialog_sb_color_button_clicked(self, button_clicked: ColorGradientButton):
        band_index = button_clicked.property("band_index")
        current_color_q = button_clicked.getColor()
        new_color = QColorDialog.getColor(
            current_color_q, self, f"Select Color for Bar {band_index + 1}")
        if new_color.isValid():
            button_clicked.setColor(new_color)
            sb_settings = self.all_settings.setdefault(
                "classic_spectrum_bars", {})
            # Ensure band_colors exists and is a list
            colors = sb_settings.get("band_colors", list(
                self.DEFAULT_SPECTRUM_BAR_COLORS_HEX))
            if not isinstance(colors, list):
                colors = list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)
            while len(colors) <= band_index:  # Pad list if necessary
                colors.append(QColor("grey").name())
            colors[band_index] = new_color.name()
            sb_settings["band_colors"] = colors

    def _reset_spectrum_bars_settings_to_defaults(self):
        # Update working copy first
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["band_colors"] = list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)
        sb_settings["sensitivity"] = self.DEFAULT_SENSITIVITY_SLIDER
        sb_settings["smoothing"] = self.DEFAULT_SMOOTHING_SLIDER
        sb_settings["grow_downwards"] = False  # Default for grow_downwards
        # Then update UI from this working copy
        if self.sb_sensitivity_slider:
            self.sb_sensitivity_slider.setValue(sb_settings["sensitivity"])
        if self.sb_smoothing_slider:
            self.sb_smoothing_slider.setValue(sb_settings["smoothing"])
        if self.sb_grow_downwards_checkbox:
            self.sb_grow_downwards_checkbox.setChecked(
                sb_settings["grow_downwards"])
        for i, button in enumerate(self.sb_color_buttons):
            button.setColor(
                QColor(sb_settings["band_colors"][i % len(sb_settings["band_colors"])]))

    def _update_sb_palette_combobox(self):
        # print("VSD TRACE: _update_sb_palette_combobox called") # For tracing
        if not hasattr(self, 'sb_palette_combobox') or self.sb_palette_combobox is None:
            print(
                "VSD ERROR (_update_sb_palette_combobox): self.sb_palette_combobox is None.")
            return
        self.sb_palette_combobox.blockSignals(True)
        current_selection_text = self.sb_palette_combobox.currentText()
        self.sb_palette_combobox.clear()
        user_profile_count = 0
        # Filter profiles that are relevant for "classic_spectrum_bars"
        user_sb_profiles = {
            name: data["classic_spectrum_bars"]
            for name, data in self.color_profiles.items()
            if isinstance(data, dict) and "classic_spectrum_bars" in data
        }
        sorted_user_profile_names = sorted(user_sb_profiles.keys())
        if sorted_user_profile_names:
            self.sb_palette_combobox.addItem("--- My Saved Palettes ---")
            self.sb_palette_combobox.model().item(
                self.sb_palette_combobox.count()-1).setEnabled(False)
            for profile_name in sorted_user_profile_names:
                self.sb_palette_combobox.addItem(f"{profile_name} (User)", userData={
                                                "name": profile_name, "type": "user_sb"})
                user_profile_count += 1

        # Add Prefab Palettes for classic_spectrum_bars
        prefabs_sb = self.PREFAB_PALETTES.get("classic_spectrum_bars", {})
        if prefabs_sb:
            if user_profile_count > 0:
                self.sb_palette_combobox.insertSeparator(
                    self.sb_palette_combobox.count())
            else:
                self.sb_palette_combobox.addItem("--- Prefab Palettes ---")
                self.sb_palette_combobox.model().item(
                    self.sb_palette_combobox.count()-1).setEnabled(False)
            for prefab_key, prefab_data in prefabs_sb.items():
                display_name = prefab_key.replace("_", " ").title()
                self.sb_palette_combobox.addItem(f"{display_name} (Prefab)", userData={
                                                "key": prefab_key, "type": "prefab_sb"})
        if self.sb_palette_combobox.count() == 0 or \
            (self.sb_palette_combobox.count() == 1 and not self.sb_palette_combobox.itemData(0)):
            self.sb_palette_combobox.clear()
            self.sb_palette_combobox.addItem("No palettes available")
            self.sb_palette_combobox.model().item(0).setEnabled(False)
        idx_to_restore = self.sb_palette_combobox.findText(
            current_selection_text)
        if idx_to_restore != -1:
            self.sb_palette_combobox.setCurrentIndex(idx_to_restore)
        elif self.sb_palette_combobox.count() > 0:
            for i in range(self.sb_palette_combobox.count()):
                if self.sb_palette_combobox.model().item(i).isEnabled():
                    self.sb_palette_combobox.setCurrentIndex(i)
                    break
        self.sb_palette_combobox.blockSignals(False)
        # Update button states based on new selection
        self._on_sb_palette_combobox_changed()

    def _collect_settings_from_all_tabs(self) -> dict:
        # This method ensures self.all_settings (the dialog's working copy)
        # is up-to-date with the current state of all UI controls before emitting.
        # Classic Spectrum Bars
        current_sb_settings = self.all_settings.setdefault(
            "classic_spectrum_bars", {})
        if hasattr(self, 'sb_color_buttons') and self.sb_color_buttons:
            current_sb_settings["band_colors"] = [
                btn.getColor().name() for btn in self.sb_color_buttons]
        if hasattr(self, 'sb_sensitivity_slider') and self.sb_sensitivity_slider:
            current_sb_settings["sensitivity"] = self.sb_sensitivity_slider.value()
        if hasattr(self, 'sb_smoothing_slider') and self.sb_smoothing_slider:
            current_sb_settings["smoothing"] = self.sb_smoothing_slider.value()
        if hasattr(self, 'sb_grow_downwards_checkbox') and self.sb_grow_downwards_checkbox:
            current_sb_settings["grow_downwards"] = self.sb_grow_downwards_checkbox.isChecked()
        # Pulse Wave
        current_pw_settings = self.all_settings.setdefault(
            "pulse_wave_matrix", {})
        if hasattr(self, 'pw_color_button') and self.pw_color_button:
            current_pw_settings["color"] = self.pw_color_button.getColor().name()
        if hasattr(self, 'pw_speed_slider') and self.pw_speed_slider:
            current_pw_settings["speed"] = self.pw_speed_slider.value()
        if hasattr(self, 'pw_brightness_sensitivity_slider') and self.pw_brightness_sensitivity_slider:
            current_pw_settings["brightness_sensitivity"] = self.pw_brightness_sensitivity_slider.value()
        # Dual VU Spectrum
        current_dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        # VU Part
        if hasattr(self, 'dvu_low_color_button') and self.dvu_low_color_button:
            current_dvu_settings["vu_low_color"] = self.dvu_low_color_button.getColor().name()
        if hasattr(self, 'dvu_mid_color_button') and self.dvu_mid_color_button:
            current_dvu_settings["vu_mid_color"] = self.dvu_mid_color_button.getColor().name()
        if hasattr(self, 'dvu_high_color_button') and self.dvu_high_color_button:
            current_dvu_settings["vu_high_color"] = self.dvu_high_color_button.getColor().name()
        if hasattr(self, 'dvu_threshold_mid_slider') and self.dvu_threshold_mid_slider:
            current_dvu_settings["vu_threshold_mid"] = self.dvu_threshold_mid_slider.value()
        if hasattr(self, 'dvu_threshold_high_slider') and self.dvu_threshold_high_slider:
            current_dvu_settings["vu_threshold_high"] = self.dvu_threshold_high_slider.value()
        if hasattr(self, 'dvu_falloff_speed_slider') and self.dvu_falloff_speed_slider:
            current_dvu_settings["vu_falloff_speed"] = self.dvu_falloff_speed_slider.value()
        # Central Spectrum Part
        if hasattr(self, 'dvu_spectrum_color_buttons') and self.dvu_spectrum_color_buttons:
            current_dvu_settings["spectrum_band_colors"] = [btn.getColor().name() for btn in self.dvu_spectrum_color_buttons]
        if hasattr(self, 'dvu_spectrum_sensitivity_slider') and self.dvu_spectrum_sensitivity_slider:
            current_dvu_settings["spectrum_sensitivity"] = self.dvu_spectrum_sensitivity_slider.value()
        if hasattr(self, 'dvu_spectrum_smoothing_slider') and self.dvu_spectrum_smoothing_slider:
            current_dvu_settings["spectrum_smoothing"] = self.dvu_spectrum_smoothing_slider.value()
        if hasattr(self, 'dvu_spectrum_grow_downwards_checkbox') and self.dvu_spectrum_grow_downwards_checkbox:
            current_dvu_settings["spectrum_grow_downwards"] = self.dvu_spectrum_grow_downwards_checkbox.isChecked()
        # Deep copy self.all_settings to ensure the emitted dictionary is independent
        final_settings_to_emit = {}
        for mode_key, mode_data in self.all_settings.items():
            final_settings_to_emit[mode_key] = mode_data.copy()
            # Ensure lists are copied
            for list_key_collection in [["band_colors", "palette"], ["spectrum_band_colors"]]:
                for list_key in list_key_collection:
                    if list_key in final_settings_to_emit[mode_key] and \
                        isinstance(final_settings_to_emit[mode_key][list_key], list):
                        final_settings_to_emit[mode_key][list_key] = list(
                            final_settings_to_emit[mode_key][list_key])
        return final_settings_to_emit

    def _apply_all_settings(self):
        final_settings_to_emit = self._collect_settings_from_all_tabs()
        self.all_settings_applied.emit(final_settings_to_emit)
        self._save_color_profiles()  # Save any changes to user profiles

    def _apply_all_and_accept(self):
        self._apply_all_settings()
        self.accept()

    def _on_sb_palette_combobox_changed(self):
        print(f"VSD TRACE: _on_sb_palette_combobox_changed called.")
        if not (hasattr(self, 'sb_palette_combobox') and self.sb_palette_combobox and
                hasattr(self, 'sb_delete_palette_button') and self.sb_delete_palette_button and
                hasattr(self, 'sb_load_palette_button') and self.sb_load_palette_button):
            print(
                "VSD WARN: Combobox or buttons not fully initialized for _on_sb_palette_combobox_changed.")
            return
        selected_data = self.sb_palette_combobox.currentData()
        print(f"  Selected data: {selected_data}")
        can_delete = False
        if selected_data and isinstance(selected_data, dict) and selected_data.get("type") == "user_sb":
            can_delete = True
        self.sb_delete_palette_button.setEnabled(can_delete)
        print(f"  Delete button enabled: {can_delete}")
        can_load = False
        if selected_data and isinstance(selected_data, dict) and selected_data.get("type") in ["user_sb", "prefab_sb"]:
            can_load = True
        self.sb_load_palette_button.setEnabled(can_load)
        print(f"  Load button enabled: {can_load}")

    def _load_selected_sb_palette_from_combobox(self):
        print("VSD TRACE: _load_selected_sb_palette_from_combobox called.")
        if not hasattr(self, 'sb_palette_combobox') or not self.sb_palette_combobox:
            print("  Load failed: sb_palette_combobox not found.")
            return
        selected_item_data = self.sb_palette_combobox.currentData()
        print(f"  Selected item data from combobox: {selected_item_data}")
        if not selected_item_data or not isinstance(selected_item_data, dict):
            print("  Load failed: No valid data in selected combobox item.")
            return
        profile_type = selected_item_data.get("type")
        active_mode_key = "classic_spectrum_bars"
        settings_to_apply = None
        if profile_type == "user_sb":  # Specifically for Spectrum Bars user profiles
            profile_name = selected_item_data.get("name")
            print(f"  Loading USER_SB profile: '{profile_name}'")
            if profile_name and profile_name in self.color_profiles:
                # User profiles are now structured: self.color_profiles[profile_name][mode_key]
                if active_mode_key in self.color_profiles[profile_name]:
                    settings_to_apply = self.color_profiles[profile_name][active_mode_key]
                    print(
                        f"    Found settings for '{profile_name}' under '{active_mode_key}': {settings_to_apply}")
                else:
                    QMessageBox.warning(
                        self, "Load Error", f"Profile '{profile_name}' does not contain settings for Spectrum Bars.")
                    return
            else:
                QMessageBox.warning(
                    self, "Load Error", f"Could not find user profile: {profile_name}")
                return
        elif profile_type == "prefab_sb":  # Specifically for Spectrum Bars prefab profiles
            prefab_key = selected_item_data.get("key")
            print(f"  Loading PREFAB_SB profile with key: '{prefab_key}'")
            if prefab_key and active_mode_key in self.PREFAB_PALETTES and prefab_key in self.PREFAB_PALETTES[active_mode_key]:
                settings_to_apply = self.PREFAB_PALETTES[active_mode_key][prefab_key]
                print(
                    f"    Found prefab settings for '{prefab_key}': {settings_to_apply}")
            else:
                QMessageBox.warning(self, "Load Error",
                                    f"Could not find prefab: {prefab_key}")
                return
        else:
            print(f"  Load failed: Invalid profile_type '{profile_type}'.")
            return
        if settings_to_apply:
            print(
                f"  Applying settings to dialog's working copy and UI: {settings_to_apply}")
            # Ensure it's a copy before modifying
            loaded_settings_copy = settings_to_apply.copy()
            # --- CRITICAL: Ensure all expected keys exist in loaded_settings_copy before applying to UI ---
            # Use defaults from csb_defaults_ui if keys are missing in the loaded profile
            csb_defaults_ui = {
                "band_colors": list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX),
                "sensitivity": self.DEFAULT_SENSITIVITY_SLIDER,
                "smoothing": self.DEFAULT_SMOOTHING_SLIDER,
                "grow_downwards": False
            }
            for key, default_value in csb_defaults_ui.items():
                loaded_settings_copy.setdefault(key, default_value)
            # Ensure band_colors is a list (it should be from prefabs/saved profiles)
            if "band_colors" in loaded_settings_copy and isinstance(loaded_settings_copy["band_colors"], list):
                loaded_settings_copy["band_colors"] = list(
                    loaded_settings_copy["band_colors"])
            else:  # Fallback if band_colors somehow missing or wrong type
                loaded_settings_copy["band_colors"] = list(
                    csb_defaults_ui["band_colors"])
            # Update the dialog's working copy
            self.all_settings[active_mode_key] = loaded_settings_copy
            print(
                f"    Dialog's self.all_settings['{active_mode_key}'] updated to: {self.all_settings[active_mode_key]}")
            # Update UI elements from the newly loaded settings in self.all_settings[active_mode_key]
            # (which is now loaded_settings_copy)
            if self.sb_sensitivity_slider:
                sens_val = self.all_settings[active_mode_key].get(
                    "sensitivity")
                self.sb_sensitivity_slider.setValue(sens_val)
                print(f"    Sensitivity slider set to: {sens_val}")
            if self.sb_smoothing_slider:
                smooth_val = self.all_settings[active_mode_key].get(
                    "smoothing")
                self.sb_smoothing_slider.setValue(smooth_val)
                print(f"    Smoothing slider set to: {smooth_val}")
            if self.sb_grow_downwards_checkbox:
                grow_val = self.all_settings[active_mode_key].get(
                    "grow_downwards")
                self.sb_grow_downwards_checkbox.setChecked(grow_val)
                print(f"    Grow downwards checkbox set to: {grow_val}")
            loaded_colors_for_ui = self.all_settings[active_mode_key].get(
                "band_colors")
            print(f"    Applying band colors: {loaded_colors_for_ui}")
            for i, btn in enumerate(self.sb_color_buttons):
                color_to_set = QColor(loaded_colors_for_ui[i]) if i < len(loaded_colors_for_ui) else QColor(
                    self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)])
                btn.setColor(color_to_set)
                # print(f"      Bar {i} color set to: {color_to_set.name()}")
            print(
                f"  VSD INFO: Loaded preset '{self.sb_palette_combobox.currentText()}' to Spectrum Bars tab.")
        else:
            print("  Load failed: settings_to_apply was None.")

    def _save_sb_current_as_profile(self):
        active_mode_key = "classic_spectrum_bars"
        if not hasattr(self, 'sb_profile_name_edit') or not self.sb_profile_name_edit:
            return
        name = self.sb_profile_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Palette Error",
                                "Please enter a name for the palette.")
            return
        # Check for overwrite
        if name in self.color_profiles and active_mode_key in self.color_profiles[name]:
            if QMessageBox.question(self, "Overwrite Palette?",
                                    f"A palette named '{name}' already exists for Spectrum Bars. Overwrite it?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                return
        # Collect current settings from UI elements for Spectrum Bars
        current_sb_settings_from_ui = {
            "band_colors": [btn.getColor().name() for btn in self.sb_color_buttons],
            "sensitivity": self.sb_sensitivity_slider.value() if self.sb_sensitivity_slider else self.DEFAULT_SENSITIVITY_SLIDER,
            "smoothing": self.sb_smoothing_slider.value() if self.sb_smoothing_slider else self.DEFAULT_SMOOTHING_SLIDER,
            "grow_downwards": self.sb_grow_downwards_checkbox.isChecked() if self.sb_grow_downwards_checkbox else False
        }
        # Update self.all_settings (dialog's working copy) for this mode
        self.all_settings[active_mode_key] = current_sb_settings_from_ui.copy()
        # Update self.color_profiles (which is saved to JSON)
        if name not in self.color_profiles:  # If profile name doesn't exist at all
            self.color_profiles[name] = {}
        # If profile name exists but isn't a dict (corruption?)
        elif not isinstance(self.color_profiles[name], dict):
            self.color_profiles[name] = {}
        # Save a copy of the settings for the specific mode under this profile name
        self.color_profiles[name][active_mode_key] = current_sb_settings_from_ui.copy(
        )
        self._save_color_profiles()
        self._update_sb_palette_combobox()
        idx_new = self.sb_palette_combobox.findText(f"{name} (User)")
        if idx_new != -1:
            self.sb_palette_combobox.setCurrentIndex(idx_new)
        self.sb_profile_name_edit.clear()
        # print(f"VSD INFO: Palette '{name}' for Spectrum Bars saved.")

    def _delete_selected_sb_palette_from_combobox(self):
        if not hasattr(self, 'sb_palette_combobox') or not self.sb_palette_combobox:
            return
        selected_item_data = self.sb_palette_combobox.currentData()
        if not selected_item_data or not isinstance(selected_item_data, dict) or selected_item_data.get("type") != "user_sb":
            QMessageBox.information(
                self, "Delete Palette", "Please select a user-saved Spectrum Bars palette to delete.")
            return
        profile_name = selected_item_data.get("name")
        display_text = self.sb_palette_combobox.currentText()
        active_mode_key = "classic_spectrum_bars"
        if QMessageBox.question(self, "Confirm Deletion",
                                f"Are you sure you want to delete the Spectrum Bars palette: '{display_text}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if profile_name in self.color_profiles and isinstance(self.color_profiles[profile_name], dict) and \
                active_mode_key in self.color_profiles[profile_name]:
                # Delete settings for this mode
                del self.color_profiles[profile_name][active_mode_key]
                # If the profile now contains no settings for any mode, delete the profile name itself
                if not self.color_profiles[profile_name]:
                    del self.color_profiles[profile_name]
                self._save_color_profiles()
                self._update_sb_palette_combobox()
                # print(f"VSD INFO: Palette '{profile_name}' (Spectrum Bars part) deleted.")
            else:
                QMessageBox.warning(
                    self, "Delete Error", f"Spectrum Bars palette '{profile_name}' not found in records.")

    def _update_profile_list_widget(self):
        # This method is OBSOLETE for Spectrum Bars tab. It was for QListWidget.
        # If called, it means there's a logic error.
        print("VSD WARNING: OBSOLETE _update_profile_list_widget CALLED! Should use _update_sb_palette_combobox.")
        pass

    def _load_selected_profile_from_list(self):
        # This method is OBSOLETE for Spectrum Bars tab.
        print("VSD WARNING: OBSOLETE _load_selected_profile_from_list CALLED!")
        pass

    def _create_pulse_wave_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setSpacing(10)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        description_label = QLabel(
            "Configure a sweeping pulse of color across the grid. Adjust its color, speed, and how its brightness reacts to audio.")
        description_label.setWordWrap(True)
        page_layout.addWidget(description_label)
        page_layout.addWidget(
            QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken))
        basic_settings_group = QGroupBox("Pulse Wave Settings")
        basic_settings_layout = QGridLayout(basic_settings_group)
        basic_settings_layout.addWidget(
            QLabel("Pulse Color:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_color_button = ColorGradientButton(parent=self)
        self.pw_color_button.clicked.connect(self._on_pw_color_changed)
        basic_settings_layout.addWidget(self.pw_color_button, 0, 1)
        basic_settings_layout.addWidget(
            QLabel("Base Pulse Speed:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.pw_speed_slider.setRange(0, 100)
        self.pw_speed_slider.valueChanged.connect(self._on_pw_speed_changed)
        basic_settings_layout.addWidget(self.pw_speed_slider, 1, 1)
        self.pw_speed_label = QLabel("50")
        self.pw_speed_label.setMinimumWidth(30)
        basic_settings_layout.addWidget(self.pw_speed_label, 1, 2)
        basic_settings_layout.addWidget(
            QLabel("Brightness Sensitivity (Audio):"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_brightness_sensitivity_slider = QSlider(
            Qt.Orientation.Horizontal)
        self.pw_brightness_sensitivity_slider.setRange(0, 100)
        self.pw_brightness_sensitivity_slider.valueChanged.connect(
            self._on_pw_brightness_sensitivity_changed)
        basic_settings_layout.addWidget(
            self.pw_brightness_sensitivity_slider, 2, 1)
        self.pw_brightness_sensitivity_label = QLabel("1.0x")
        self.pw_brightness_sensitivity_label.setMinimumWidth(40)
        basic_settings_layout.addWidget(
            self.pw_brightness_sensitivity_label, 2, 2)
        basic_settings_layout.setColumnStretch(1, 1)
        page_layout.addWidget(basic_settings_group)
        page_layout.addStretch(1)
        return page_widget

    def _on_pw_color_changed(self):
        if not self.pw_color_button:
            return
        current_color_q = self.pw_color_button.getColor()
        new_color = QColorDialog.getColor(
            current_color_q, self, "Select Pulse Color")
        if new_color.isValid():
            self.pw_color_button.setColor(new_color)
            pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
            pw_settings["color"] = new_color.name()

    def _on_pw_speed_changed(self, value):
        if self.pw_speed_label:
            self.pw_speed_label.setText(f"{value}")
        pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
        pw_settings["speed"] = value

    def _on_pw_brightness_sensitivity_changed(self, value):
        if self.pw_brightness_sensitivity_label:
            factor = value / 50.0
            self.pw_brightness_sensitivity_label.setText(f"{factor:.1f}x")
        pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
        pw_settings["brightness_sensitivity"] = value

    def _create_dual_vu_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setSpacing(10)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        description_label = QLabel("Configure two VU meters on the edges and a central spectrum display. Customize colors and behaviors for each.")
        description_label.setWordWrap(True)
        page_layout.addWidget(description_label)
        page_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken))
        vu_settings_group = QGroupBox("VU Meter Appearance (Mono-Driven)")
        vu_settings_layout = QGridLayout(vu_settings_group)
        vu_settings_layout.setColumnStretch(1, 1)
        vu_settings_layout.addWidget(QLabel("Low Color:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_low_color_button = ColorGradientButton(parent=self)
        self.dvu_low_color_button.clicked.connect(lambda: self._on_dvu_color_changed("low"))
        vu_settings_layout.addWidget(self.dvu_low_color_button, 0, 1)
        vu_settings_layout.addWidget(QLabel("Mid Color:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_mid_color_button = ColorGradientButton(parent=self)
        self.dvu_mid_color_button.clicked.connect(lambda: self._on_dvu_color_changed("mid"))
        vu_settings_layout.addWidget(self.dvu_mid_color_button, 1, 1)
        vu_settings_layout.addWidget(QLabel("High Color:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_high_color_button = ColorGradientButton(parent=self)
        self.dvu_high_color_button.clicked.connect(lambda: self._on_dvu_color_changed("high"))
        vu_settings_layout.addWidget(self.dvu_high_color_button, 2, 1)
        vu_settings_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed), 3, 0, 1, 3)
        vu_settings_layout.addWidget(QLabel("Mid Threshold (%):"), 4, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_threshold_mid_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_threshold_mid_slider.setRange(0, 100)
        self.dvu_threshold_mid_slider.valueChanged.connect(self._on_dvu_threshold_mid_changed)
        vu_settings_layout.addWidget(self.dvu_threshold_mid_slider, 4, 1)
        self.dvu_threshold_mid_label = QLabel("60%")
        self.dvu_threshold_mid_label.setMinimumWidth(40)
        vu_settings_layout.addWidget(self.dvu_threshold_mid_label, 4, 2)
        vu_settings_layout.addWidget(QLabel("High Threshold (%):"), 5, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_threshold_high_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_threshold_high_slider.setRange(0, 100)
        self.dvu_threshold_high_slider.valueChanged.connect(self._on_dvu_threshold_high_changed)
        vu_settings_layout.addWidget(self.dvu_threshold_high_slider, 5, 1)
        self.dvu_threshold_high_label = QLabel("85%")
        self.dvu_threshold_high_label.setMinimumWidth(40)
        vu_settings_layout.addWidget(self.dvu_threshold_high_label, 5, 2)
        vu_settings_layout.addWidget(QLabel("Falloff Speed:"), 6, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_falloff_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_falloff_speed_slider.setRange(0, 100)
        self.dvu_falloff_speed_slider.valueChanged.connect(self._on_dvu_falloff_speed_changed)
        vu_settings_layout.addWidget(self.dvu_falloff_speed_slider, 6, 1)
        self.dvu_falloff_speed_label = QLabel("50")
        self.dvu_falloff_speed_label.setMinimumWidth(40)
        vu_settings_layout.addWidget(self.dvu_falloff_speed_label, 6, 2)
        page_layout.addWidget(vu_settings_group)
        spectrum_group = QGroupBox("Central Spectrum Settings (5 Bands)")
        spectrum_main_layout = QVBoxLayout(spectrum_group)
        spec_colors_label = QLabel("Band Colors (1-5):")
        spectrum_main_layout.addWidget(spec_colors_label)
        spec_colors_buttons_layout = QHBoxLayout()
        spec_colors_buttons_layout.setSpacing(6)
        self.dvu_spectrum_color_buttons = []
        for i in range(5):
            color_button = ColorGradientButton(parent=self)
            color_button.setProperty("band_index_dvu_spec", i)
            color_button.setToolTip(f"Click to change color for Central Spectrum Band {i+1}")
            color_button.clicked.connect(lambda checked=False, btn=color_button: self._on_dvu_spectrum_color_button_clicked(btn))
            self.dvu_spectrum_color_buttons.append(color_button)
            spec_colors_buttons_layout.addWidget(color_button)
        spec_colors_buttons_layout.addStretch(1)
        spectrum_main_layout.addLayout(spec_colors_buttons_layout)
        spectrum_main_layout.addSpacing(10)
        spec_params_layout_grid = QGridLayout()
        spec_row = 0
        spec_params_layout_grid.addWidget(QLabel("Sensitivity:"), spec_row, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_spectrum_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_spectrum_sensitivity_slider.setRange(0, 100)
        self.dvu_spectrum_sensitivity_slider.valueChanged.connect(self._on_dvu_spectrum_sensitivity_changed)
        spec_params_layout_grid.addWidget(self.dvu_spectrum_sensitivity_slider, spec_row, 1)
        self.dvu_spectrum_sensitivity_label = QLabel("1.00x")
        self.dvu_spectrum_sensitivity_label.setMinimumWidth(45)
        spec_params_layout_grid.addWidget(self.dvu_spectrum_sensitivity_label, spec_row, 2)
        spec_row += 1
        spec_params_layout_grid.addWidget(QLabel("Smoothing Factor:"), spec_row, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_spectrum_smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_spectrum_smoothing_slider.setRange(0, 99)
        self.dvu_spectrum_smoothing_slider.valueChanged.connect(self._on_dvu_spectrum_smoothing_changed)
        spec_params_layout_grid.addWidget(self.dvu_spectrum_smoothing_slider, spec_row, 1)
        self.dvu_spectrum_smoothing_label = QLabel("0.20")
        self.dvu_spectrum_smoothing_label.setMinimumWidth(45)
        spec_params_layout_grid.addWidget(self.dvu_spectrum_smoothing_label, spec_row, 2)
        spec_row += 1
        self.dvu_spectrum_grow_downwards_checkbox = QCheckBox("Grow Bars Downwards (from top)")
        self.dvu_spectrum_grow_downwards_checkbox.setToolTip("If checked, central spectrum bars grow from top down.")
        self.dvu_spectrum_grow_downwards_checkbox.stateChanged.connect(self._on_dvu_spectrum_grow_downwards_changed)
        spec_params_layout_grid.addWidget(self.dvu_spectrum_grow_downwards_checkbox, spec_row, 0, 1, 3)
        spec_params_layout_grid.setColumnStretch(1,1)
        spectrum_main_layout.addLayout(spec_params_layout_grid)
        page_layout.addWidget(spectrum_group)
        scheme_palette_group = QGroupBox("Scheme Palette Management")
        scheme_palette_layout_grid = QGridLayout(scheme_palette_group)
        pr_row = 0
        scheme_palette_layout_grid.addWidget(QLabel("Scheme Preset:"), pr_row, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_scheme_combobox = QComboBox()
        print(f"VSD TRACE (_create_dual_vu_settings_tab): self.dvu_scheme_combobox CREATED (ID: {id(self.dvu_scheme_combobox)})") # DIAGNOSTIC
        self.dvu_scheme_combobox.setToolTip("Select a saved user scheme or a built-in prefab scheme.")
        self.dvu_scheme_combobox.currentIndexChanged.connect(self._on_dvu_scheme_combobox_changed)
        scheme_palette_layout_grid.addWidget(self.dvu_scheme_combobox, pr_row, 1, 1, 2)
        self.dvu_load_scheme_button = QPushButton("⤵️ Load Selected")
        try: self.dvu_load_scheme_button.setIcon(QIcon(get_resource_path("resources/icons/load.png")))
        except: pass
        self.dvu_load_scheme_button.clicked.connect(self._load_selected_dvu_scheme_from_combobox)
        scheme_palette_layout_grid.addWidget(self.dvu_load_scheme_button, pr_row, 3)
        pr_row += 1
        scheme_palette_layout_grid.addWidget(QLabel("Save Current As:"), pr_row, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_scheme_name_edit = QLineEdit()
        self.dvu_scheme_name_edit.setPlaceholderText("Enter new scheme name...")
        scheme_palette_layout_grid.addWidget(self.dvu_scheme_name_edit, pr_row, 1, 1, 2)
        self.dvu_save_scheme_button = QPushButton("💾 Save New")
        try: self.dvu_save_scheme_button.setIcon(QIcon(get_resource_path("resources/icons/save.png")))
        except: pass
        self.dvu_save_scheme_button.clicked.connect(self._save_dvu_current_as_scheme)
        scheme_palette_layout_grid.addWidget(self.dvu_save_scheme_button, pr_row, 3)
        pr_row += 1
        dvu_action_buttons_layout = QHBoxLayout()
        dvu_action_buttons_layout.addStretch(1)
        self.dvu_delete_scheme_button = QPushButton("🗑️ Delete Selected Scheme")
        try: self.dvu_delete_scheme_button.setIcon(QIcon(get_resource_path("resources/icons/delete.png")))
        except: pass
        self.dvu_delete_scheme_button.clicked.connect(self._delete_selected_dvu_scheme_from_combobox)
        dvu_action_buttons_layout.addWidget(self.dvu_delete_scheme_button)
        self.dvu_reset_settings_button = QPushButton("↺ Reset Dual VU Settings")
        self.dvu_reset_settings_button.clicked.connect(self._reset_dvu_settings_to_defaults)
        dvu_action_buttons_layout.addWidget(self.dvu_reset_settings_button)
        dvu_action_buttons_layout.addStretch(1)
        scheme_palette_layout_grid.addLayout(dvu_action_buttons_layout, pr_row, 0, 1, 4)
        scheme_palette_layout_grid.setColumnStretch(1, 1)
        scheme_palette_layout_grid.setColumnStretch(2, 1)
        page_layout.addWidget(scheme_palette_group)
        page_layout.addStretch(1)
        return page_widget

    def _on_dvu_spectrum_color_button_clicked(self, button_clicked: ColorGradientButton):
        band_index = button_clicked.property("band_index_dvu_spec")
        current_color_q = button_clicked.getColor()
        new_color = QColorDialog.getColor(
            current_color_q, self, f"Select Color for Central Spectrum Band {band_index + 1}")
        if new_color.isValid():
            button_clicked.setColor(new_color)
            dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
            colors = dvu_settings.get("spectrum_band_colors", [
                                      QColor(Qt.GlobalColor.cyan).name()] * 5)
            if not isinstance(colors, list) or len(colors) != 5:
                colors = [QColor(Qt.GlobalColor.cyan).name()] * 5
            colors[band_index] = new_color.name()
            dvu_settings["spectrum_band_colors"] = colors

    def _on_dvu_spectrum_sensitivity_changed(self, value):
        if self.dvu_spectrum_sensitivity_label:
            self.dvu_spectrum_sensitivity_label.setText(f"{value / 50.0:.2f}x")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["spectrum_sensitivity"] = value

    def _on_dvu_spectrum_smoothing_changed(self, value):
        if self.dvu_spectrum_smoothing_label:
            self.dvu_spectrum_smoothing_label.setText(f"{value / 100.0:.2f}")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["spectrum_smoothing"] = value

    def _on_dvu_spectrum_grow_downwards_changed(self, state):
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["spectrum_grow_downwards"] = bool(
            state == Qt.CheckState.Checked.value)

    def _update_dvu_scheme_combobox(self):
        print(f"VSD TRACE: _update_dvu_scheme_combobox ENTERED. Current self ID: {id(self)}")
        dvu_combo_attr = getattr(self, 'dvu_scheme_combobox', 'ATTRIBUTE_DOES_NOT_EXIST')
        if dvu_combo_attr == 'ATTRIBUTE_DOES_NOT_EXIST':
            print(f"  VSD TRACE (_update_dvu_scheme_combobox): self.dvu_scheme_combobox attribute DOES NOT EXIST on self (ID: {id(self)}). Returning.")
            return
        elif self.dvu_scheme_combobox is None: # This refers to the attribute value after getattr confirmed existence
            print(f"  VSD TRACE (_update_dvu_scheme_combobox): self.dvu_scheme_combobox IS None on self (ID: {id(self)}). Returning.")
            return
        else:
            print(f"  VSD TRACE (_update_dvu_scheme_combobox): self.dvu_scheme_combobox EXISTS and is NOT None. Object: {self.dvu_scheme_combobox} (ID: {id(self.dvu_scheme_combobox)})")
        self.dvu_scheme_combobox.blockSignals(True)
        name_to_select_after_rebuild = getattr(self, '_last_saved_dvu_scheme_name', None)
        type_to_select_after_rebuild = "user_dvu" if name_to_select_after_rebuild else None
        if not name_to_select_after_rebuild: 
            previously_selected_data = self.dvu_scheme_combobox.currentData()
            if previously_selected_data:
                if previously_selected_data.get("type") == "user_dvu":
                    name_to_select_after_rebuild = previously_selected_data.get("name")
                    type_to_select_after_rebuild = "user_dvu"
                elif previously_selected_data.get("type") == "prefab_dvu":
                    name_to_select_after_rebuild = previously_selected_data.get("key")
                    type_to_select_after_rebuild = "prefab_dvu"
        self.dvu_scheme_combobox.clear()
        user_profile_count = 0
        user_dvu_profiles = {
            name: data["dual_vu_spectrum"]
            for name, data in self.color_profiles.items()
            if isinstance(data, dict) and "dual_vu_spectrum" in data
        }
        sorted_user_profile_names = sorted(user_dvu_profiles.keys())
        if sorted_user_profile_names:
            self.dvu_scheme_combobox.addItem("--- My Saved Schemes ---")
            self.dvu_scheme_combobox.model().item(self.dvu_scheme_combobox.count()-1).setEnabled(False)
            for profile_name in sorted_user_profile_names:
                self.dvu_scheme_combobox.addItem(f"{profile_name} (User)", userData={"name": profile_name, "type": "user_dvu"})
                user_profile_count += 1
        prefabs_dvu = self.PREFAB_PALETTES.get("dual_vu_spectrum", {})
        if prefabs_dvu:
            if user_profile_count > 0: self.dvu_scheme_combobox.insertSeparator(self.dvu_scheme_combobox.count())
            else:
                self.dvu_scheme_combobox.addItem("--- Prefab Schemes ---")
                self.dvu_scheme_combobox.model().item(self.dvu_scheme_combobox.count()-1).setEnabled(False)
            for prefab_key, _ in prefabs_dvu.items():
                display_name = prefab_key.replace("_", " ").title()
                self.dvu_scheme_combobox.addItem(f"{display_name} (Prefab)", userData={"key": prefab_key, "type": "prefab_dvu"})
        if self.dvu_scheme_combobox.count() == 0 or \
            (self.dvu_scheme_combobox.count() == 1 and not self.dvu_scheme_combobox.itemData(0)):
            self.dvu_scheme_combobox.clear()
            self.dvu_scheme_combobox.addItem("No schemes available")
            self.dvu_scheme_combobox.model().item(0).setEnabled(False)
        final_idx_to_select = -1
        if name_to_select_after_rebuild and type_to_select_after_rebuild:
            for i in range(self.dvu_scheme_combobox.count()):
                item_data = self.dvu_scheme_combobox.itemData(i)
                if item_data and item_data.get("type") == type_to_select_after_rebuild:
                    current_item_name_or_key = item_data.get("name") if type_to_select_after_rebuild == "user_dvu" else item_data.get("key")
                    if current_item_name_or_key == name_to_select_after_rebuild:
                        final_idx_to_select = i
                        break
        if final_idx_to_select != -1:
            self.dvu_scheme_combobox.setCurrentIndex(final_idx_to_select)
        elif self.dvu_scheme_combobox.count() > 0:
            for i in range(self.dvu_scheme_combobox.count()):
                if self.dvu_scheme_combobox.model().item(i).isEnabled():
                    self.dvu_scheme_combobox.setCurrentIndex(i)
                    break
        self.dvu_scheme_combobox.blockSignals(False)
        self._on_dvu_scheme_combobox_changed() # This will also print its own trace
        print(f"VSD TRACE: _update_dvu_scheme_combobox EXITED. Current self ID: {id(self)}")

    def _on_dvu_scheme_combobox_changed(self):
        print(f"VSD TRACE: _on_dvu_scheme_combobox_changed called.")
        if not (hasattr(self, 'dvu_scheme_combobox') and self.dvu_scheme_combobox and
                hasattr(self, 'dvu_delete_scheme_button') and self.dvu_delete_scheme_button and
                hasattr(self, 'dvu_load_scheme_button') and self.dvu_load_scheme_button):
            print("VSD WARN: DVU Combobox or buttons not fully initialized.")
            return
        selected_data = self.dvu_scheme_combobox.currentData()
        print(f"  DVU Selected data: {selected_data}")
        can_delete = bool(selected_data and isinstance(
            selected_data, dict) and selected_data.get("type") == "user_dvu")
        self.dvu_delete_scheme_button.setEnabled(can_delete)
        print(f"  DVU Delete button enabled: {can_delete}")
        can_load = bool(selected_data and isinstance(
            selected_data, dict) and selected_data.get("type") in ["user_dvu", "prefab_dvu"])
        self.dvu_load_scheme_button.setEnabled(can_load)
        print(f"  DVU Load button enabled: {can_load}")

    def _load_selected_dvu_scheme_from_combobox(self):
        # Similar to _load_selected_sb_palette_from_combobox but for "dual_vu_spectrum"
        print("VSD TRACE: _load_selected_dvu_scheme_from_combobox called.")
        if not (hasattr(self, 'dvu_scheme_combobox') and self.dvu_scheme_combobox):
            return
        selected_item_data = self.dvu_scheme_combobox.currentData()
        if not (selected_item_data and isinstance(selected_item_data, dict)):
            return
        profile_type = selected_item_data.get("type")
        active_mode_key = "dual_vu_spectrum"
        settings_to_apply = None
        if profile_type == "user_dvu":
            profile_name = selected_item_data.get("name")
            if profile_name and profile_name in self.color_profiles and active_mode_key in self.color_profiles[profile_name]:
                settings_to_apply = self.color_profiles[profile_name][active_mode_key]
            else:
                QMessageBox.warning(
                    self, "Load Error", f"User scheme '{profile_name}' not found or invalid.")
                return
        elif profile_type == "prefab_dvu":
            prefab_key = selected_item_data.get("key")
            if prefab_key and active_mode_key in self.PREFAB_PALETTES and prefab_key in self.PREFAB_PALETTES[active_mode_key]:
                settings_to_apply = self.PREFAB_PALETTES[active_mode_key][prefab_key]
            else:
                QMessageBox.warning(self, "Load Error",
                                    f"Prefab scheme '{prefab_key}' not found.")
                return
        else:
            return
        if settings_to_apply:
            loaded_settings_copy = settings_to_apply.copy()
            dvu_defaults_ui = {  # Ensure all keys exist, especially for older profiles
                "vu_low_color": QColor(Qt.GlobalColor.green).name(), "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(), "vu_high_color": QColor(Qt.GlobalColor.red).name(),
                "vu_threshold_mid": 60, "vu_threshold_high": 85, "vu_falloff_speed": 50,
                "spectrum_band_colors": [QColor(Qt.GlobalColor.cyan).name()] * 5,
                "spectrum_sensitivity": 50, "spectrum_smoothing": 20, "spectrum_grow_downwards": False
            }
            for key, default_value in dvu_defaults_ui.items():
                loaded_settings_copy.setdefault(key, default_value)
            if "spectrum_band_colors" in loaded_settings_copy:  # Ensure list is copied
                loaded_settings_copy["spectrum_band_colors"] = list(
                    loaded_settings_copy["spectrum_band_colors"])

            self.all_settings[active_mode_key] = loaded_settings_copy
            self._populate_ui_from_settings()  # Re-populate the whole tab, this is simplest
            print(
                f"VSD INFO: Loaded scheme '{self.dvu_scheme_combobox.currentText()}' to Dual VU tab.")

    def _save_dvu_current_as_scheme(self):
        active_mode_key = "dual_vu_spectrum"
        if not (hasattr(self, 'dvu_scheme_name_edit') and self.dvu_scheme_name_edit):
            return

        name = self.dvu_scheme_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Scheme Error",
                                "Please enter a name for the scheme.")
            return

        if name in self.color_profiles and active_mode_key in self.color_profiles.get(name, {}):
            if QMessageBox.question(self, "Overwrite Scheme?", f"Scheme '{name}' already exists for Dual VU. Overwrite it?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                return

        # Collect current settings from ALL UI elements on the "dual_vu_spectrum" tab
        current_dvu_settings_from_ui = {
            "vu_low_color": self.dvu_low_color_button.getColor().name() if self.dvu_low_color_button else QColor(Qt.GlobalColor.green).name(),
            "vu_mid_color": self.dvu_mid_color_button.getColor().name() if self.dvu_mid_color_button else QColor(Qt.GlobalColor.yellow).name(),
            "vu_high_color": self.dvu_high_color_button.getColor().name() if self.dvu_high_color_button else QColor(Qt.GlobalColor.red).name(),
            "vu_threshold_mid": self.dvu_threshold_mid_slider.value() if self.dvu_threshold_mid_slider else 60,
            "vu_threshold_high": self.dvu_threshold_high_slider.value() if self.dvu_threshold_high_slider else 85,
            "vu_falloff_speed": self.dvu_falloff_speed_slider.value() if self.dvu_falloff_speed_slider else 50,
            "spectrum_band_colors": [btn.getColor().name() for btn in self.dvu_spectrum_color_buttons] if self.dvu_spectrum_color_buttons else [QColor(Qt.GlobalColor.cyan).name()] * 5,
            "spectrum_sensitivity": self.dvu_spectrum_sensitivity_slider.value() if self.dvu_spectrum_sensitivity_slider else 50,
            "spectrum_smoothing": self.dvu_spectrum_smoothing_slider.value() if self.dvu_spectrum_smoothing_slider else 20,
            "spectrum_grow_downwards": self.dvu_spectrum_grow_downwards_checkbox.isChecked() if self.dvu_spectrum_grow_downwards_checkbox else False
        }

        # Update self.all_settings (dialog's working copy) for this mode
        self.all_settings[active_mode_key] = current_dvu_settings_from_ui.copy()

        # Update self.color_profiles (which is saved to JSON)
        if name not in self.color_profiles:
            self.color_profiles[name] = {}
        # Ensure it's a dict if name exists
        elif not isinstance(self.color_profiles.get(name), dict):
            self.color_profiles[name] = {}

        self.color_profiles[name][active_mode_key] = current_dvu_settings_from_ui.copy(
        )

        self._save_color_profiles()  # Save all profiles to JSON

        # --- CRITICAL CHANGE HERE ---
        # Store the name of the profile we just saved so _update_dvu_scheme_combobox can select it.
        self._last_saved_dvu_scheme_name = name
        self._update_dvu_scheme_combobox()  # Refresh ComboBox
        self._last_saved_dvu_scheme_name = None  # Clear the temp variable

        self.dvu_scheme_name_edit.clear()
        print(f"VSD INFO: Scheme '{name}' for Dual VU & Spectrum saved.")

    def _delete_selected_dvu_scheme_from_combobox(self):
        # Similar to _delete_selected_sb_palette_from_combobox
        if not (hasattr(self, 'dvu_scheme_combobox') and self.dvu_scheme_combobox):
            return

        selected_item_data = self.dvu_scheme_combobox.currentData()
        if not (selected_item_data and isinstance(selected_item_data, dict) and selected_item_data.get("type") == "user_dvu"):
            QMessageBox.information(
                self, "Delete Scheme", "Please select a user-saved Dual VU scheme to delete.")
            return

        profile_name = selected_item_data.get("name")
        display_text = self.dvu_scheme_combobox.currentText()
        active_mode_key = "dual_vu_spectrum"

        if QMessageBox.question(self, "Confirm Deletion", f"Delete scheme: '{display_text}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if profile_name in self.color_profiles and isinstance(self.color_profiles[profile_name], dict) and \
               active_mode_key in self.color_profiles[profile_name]:
                del self.color_profiles[profile_name][active_mode_key]
                if not self.color_profiles[profile_name]:
                    del self.color_profiles[profile_name]
                self._save_color_profiles()
                self._update_dvu_scheme_combobox()
                print(
                    f"VSD INFO: Scheme '{profile_name}' (Dual VU part) deleted.")
            else:
                QMessageBox.warning(self, "Delete Error",
                                    f"Scheme '{profile_name}' not found.")

    def _reset_dvu_settings_to_defaults(self):
        # Resets all settings on the "Dual VU & Spectrum" tab to application defaults
        dvu_defaults_ui = {
            "vu_low_color": QColor(Qt.GlobalColor.green).name(), "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(), "vu_high_color": QColor(Qt.GlobalColor.red).name(),
            "vu_threshold_mid": 60, "vu_threshold_high": 85, "vu_falloff_speed": 50,
            "spectrum_band_colors": [QColor(Qt.GlobalColor.cyan).name()] * 5,
            "spectrum_sensitivity": 50, "spectrum_smoothing": 20, "spectrum_grow_downwards": False
        }
        self.all_settings["dual_vu_spectrum"] = dvu_defaults_ui.copy()
        self.all_settings["dual_vu_spectrum"]["spectrum_band_colors"] = list(
            self.all_settings["dual_vu_spectrum"]["spectrum_band_colors"])

        # Re-populate the UI for this tab from the reset self.all_settings
        self._populate_ui_from_settings()  # This will refresh the current tab
        print("VSD INFO: Dual VU & Spectrum settings reset to defaults.")

    def _on_dvu_color_changed(self, color_type: str):
        button_to_update: ColorGradientButton | None = None
        setting_key: str = ""
        if color_type == "low":
            button_to_update, setting_key = self.dvu_low_color_button, "vu_low_color"
        elif color_type == "mid":
            button_to_update, setting_key = self.dvu_mid_color_button, "vu_mid_color"
        elif color_type == "high":
            button_to_update, setting_key = self.dvu_high_color_button, "vu_high_color"
        if not button_to_update or not setting_key:
            return

        current_color_q = button_to_update.getColor()
        new_color = QColorDialog.getColor(
            current_color_q, self, f"Select VU {color_type.capitalize()} Color")
        if new_color.isValid():
            button_to_update.setColor(new_color)
            dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
            dvu_settings[setting_key] = new_color.name()

    def _on_dvu_threshold_mid_changed(self, value):
        if self.dvu_threshold_mid_label:
            self.dvu_threshold_mid_label.setText(f"{value}%")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_threshold_mid"] = value
        if self.dvu_threshold_high_slider and value > self.dvu_threshold_high_slider.value():
            self.dvu_threshold_high_slider.setValue(value)

    def _on_dvu_threshold_high_changed(self, value):
        if self.dvu_threshold_high_label:
            self.dvu_threshold_high_label.setText(f"{value}%")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_threshold_high"] = value
        if self.dvu_threshold_mid_slider and value < self.dvu_threshold_mid_slider.value():
            self.dvu_threshold_mid_slider.setValue(value)

    def _on_dvu_falloff_speed_changed(self, value):
        if self.dvu_falloff_speed_label:
            self.dvu_falloff_speed_label.setText(f"{value}")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_falloff_speed"] = value
