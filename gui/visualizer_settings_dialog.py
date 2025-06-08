# AKAI_Fire_RGB_Controller/gui/visualizer_settings_dialog.py
import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QTabWidget, QWidget,
    QPushButton, QSlider, QGridLayout, QColorDialog, QListWidget, QListWidgetItem,
    QLineEdit, QInputDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QGroupBox, QCheckBox
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
        def get_resource_path(relative_path):
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
            Qt.GlobalColor.magenta).name(), QColor("#FFA500").name(),
        QColor("#800080").name()
    ]
    DEFAULT_SENSITIVITY_SLIDER = 50
    DEFAULT_SMOOTHING_SLIDER = 20

    PREFAB_PALETTES = {
        "classic_spectrum_bars": {
            "rainbow": {"band_colors": ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3", "#FF00FF"], "sensitivity": 50, "smoothing": 20},
            "fire_ice": {"band_colors": ["#FF4500", "#FF8C00", "#FFD700", "#FFFFE0", "#ADD8E6", "#87CEFA", "#4682B4", "#00008B"], "sensitivity": 55, "smoothing": 25},
            "synthwave": {"band_colors": ["#F92672", "#FD971F", "#E6DB74", "#A6E22E", "#66D9EF", "#AE81FF", "#CC66FF", "#FF00FF"], "sensitivity": 60, "smoothing": 15},
            "forest": {"band_colors": ["#228B22", "#3CB371", "#8FBC8F", "#556B2F", "#006400", "#90EE90", "#32CD32", "#008000"], "sensitivity": 45, "smoothing": 30},
            "ocean_sunset": {"band_colors": ["#FF4E50", "#FC913A", "#F9D423", "#EDE574", "#E1F5C4", "#ADD8E6", "#87CEEB", "#4682B4"], "sensitivity": 50, "smoothing": 22}
        },
        "pulse_wave_matrix": {"rainbow": {"palette": ["#FF0000", "#FFFF00", "#0000FF"], "pulse_speed": 50}}
    }


    def __init__(self, current_mode_key: str, all_current_settings: dict | None, config_save_path_func, parent=None):
        super().__init__(parent)
        self.current_mode_key_on_open = current_mode_key
        self.config_save_path_func = config_save_path_func
        self.all_settings = {}

        if isinstance(all_current_settings, dict):
            for mode_key_iter, settings_val in all_current_settings.items():
                if isinstance(settings_val, dict):
                    self.all_settings[mode_key_iter] = settings_val.copy()
                    for list_key in ["band_colors", "palette"]:
                        if list_key in self.all_settings[mode_key_iter] and \
                           isinstance(self.all_settings[mode_key_iter][list_key], list):
                            self.all_settings[mode_key_iter][list_key] = list(
                                self.all_settings[mode_key_iter][list_key])
                else:
                    self.all_settings[mode_key_iter] = settings_val
        else:
            self.all_settings = {
                "classic_spectrum_bars": {
                    "band_colors": list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX),
                    "sensitivity": self.DEFAULT_SENSITIVITY_SLIDER,
                    "smoothing": self.DEFAULT_SMOOTHING_SLIDER,
                    "grow_downwards": False
                },
                "pulse_wave_matrix": {
                    "color": QColor("cyan").name(),
                    "speed": 50,
                    "brightness_sensitivity": 75
                },
                "dual_vu_spectrum": {  # ADDED Default for Dual VU
                    "vu_low_color": QColor(Qt.GlobalColor.green).name(),
                    "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(),
                    "vu_high_color": QColor(Qt.GlobalColor.red).name(),
                    "vu_threshold_mid": 60,  # UI Scale 0-100 (%)
                    "vu_threshold_high": 85,  # UI Scale 0-100 (%)
                    "vu_falloff_speed": 50  # UI Scale 0-100
                }
            }

        # Ensure classic_spectrum_bars has its keys
        csb_defaults = {
            "band_colors": list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX),
            "sensitivity": self.DEFAULT_SENSITIVITY_SLIDER,
            "smoothing": self.DEFAULT_SMOOTHING_SLIDER,
            "grow_downwards": False
        }
        if "classic_spectrum_bars" not in self.all_settings:
            self.all_settings["classic_spectrum_bars"] = csb_defaults
        else:
            for key, val in csb_defaults.items():
                self.all_settings["classic_spectrum_bars"].setdefault(key, val)

        # Ensure pulse_wave_matrix has its keys
        pw_defaults = {
            "color": QColor("cyan").name(),
            "speed": 50,
            "brightness_sensitivity": 75
        }
        if "pulse_wave_matrix" not in self.all_settings:
            self.all_settings["pulse_wave_matrix"] = pw_defaults
        else:
            for key, val in pw_defaults.items():
                self.all_settings["pulse_wave_matrix"].setdefault(key, val)
            # Ensure speed and brightness_sensitivity are integers (UI scale)
            current_speed = self.all_settings["pulse_wave_matrix"].get(
                "speed", 50)
            self.all_settings["pulse_wave_matrix"]["speed"] = int(
                current_speed) if isinstance(current_speed, (int, float)) else 50
            current_bs = self.all_settings["pulse_wave_matrix"].get(
                "brightness_sensitivity", 75)
            self.all_settings["pulse_wave_matrix"]["brightness_sensitivity"] = int(
                current_bs) if isinstance(current_bs, (int, float)) else 75

        # Ensure dual_vu_spectrum has its keys
        dvu_defaults = {
            "vu_low_color": QColor(Qt.GlobalColor.green).name(),
            "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(),
            "vu_high_color": QColor(Qt.GlobalColor.red).name(),
            "vu_threshold_mid": 60,
            "vu_threshold_high": 85,
            "vu_falloff_speed": 50
        }
        if "dual_vu_spectrum" not in self.all_settings:
            self.all_settings["dual_vu_spectrum"] = dvu_defaults
        else:
            for key, val in dvu_defaults.items():
                self.all_settings["dual_vu_spectrum"].setdefault(key, val)
            # Ensure sliders are integers
            for key in ["vu_threshold_mid", "vu_threshold_high", "vu_falloff_speed"]:
                current_val = self.all_settings["dual_vu_spectrum"].get(
                    key, dvu_defaults[key])
                self.all_settings["dual_vu_spectrum"][key] = int(current_val) if isinstance(
                    current_val, (int, float)) else dvu_defaults[key]

        self.setWindowTitle("⚙️ Visualizer Settings")
        # Consider increasing min height slightly if tabs get crowded
        self.setMinimumSize(800, 520)

        # Classic Spectrum Bars UI elements
        self.sb_sensitivity_slider, self.sb_sensitivity_label = None, None
        self.sb_smoothing_slider, self.sb_smoothing_label = None, None
        self.sb_color_buttons, self.sb_reset_button = [], None
        self.sb_grow_downwards_checkbox = None

        # Pulse Wave UI elements
        self.pw_color_button: ColorGradientButton | None = None
        self.pw_speed_slider: QSlider | None = None
        self.pw_speed_label: QLabel | None = None
        self.pw_brightness_sensitivity_slider: QSlider | None = None
        self.pw_brightness_sensitivity_label: QLabel | None = None

        # --- ADDED: Dual VU UI elements ---
        self.dvu_low_color_button: ColorGradientButton | None = None
        self.dvu_mid_color_button: ColorGradientButton | None = None
        self.dvu_high_color_button: ColorGradientButton | None = None
        self.dvu_threshold_mid_slider: QSlider | None = None
        self.dvu_threshold_mid_label: QLabel | None = None
        self.dvu_threshold_high_slider: QSlider | None = None
        self.dvu_threshold_high_label: QLabel | None = None
        self.dvu_falloff_speed_slider: QSlider | None = None
        self.dvu_falloff_speed_label: QLabel | None = None
        # (Spectrum part UI elements for this tab will be added later)
        # --- END ADD ---

        # Common palette management UI elements (if applicable per tab)
        # These are specific to Spectrum Bars tab for now
        self.profile_list_widget, self.profile_name_edit = None, None
        self.load_profile_button, self.save_profile_button, self.delete_profile_button = None, None, None
        self.prefab_rainbow_button, self.prefab_fire_ice_button = None, None
        self.prefab_synthwave_button, self.prefab_forest_button, self.prefab_ocean_sunset_button = None, None, None

        self.color_profiles = {}  # This might need to be per-mode if profiles are mode-specific
        self._init_ui()
        self._load_color_profiles()  # Load shared profiles for now
        self._populate_ui_from_settings()
        self._select_initial_tab()

    def _get_color_profile_filepath(self) -> str:
        # --- ADDED PRINT ---
        filepath = self.config_save_path_func(COLOR_PROFILE_CONFIG_FILENAME)
        print(
            f"VSD DEBUG (_get_color_profile_filepath): Path for profiles JSON is: {filepath}")
        # --- END PRINT ---
        return filepath

    def _load_color_profiles(self):
        filepath = self._get_color_profile_filepath()  # This will now print the path
        # DIAGNOSTIC
        print(
            f"VSD DEBUG (_load_color_profiles): Attempting to load from: {filepath}")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    self.color_profiles = data.get("profiles", {})
                    # DIAGNOSTIC
                    print(
                        f"VSD DEBUG (_load_color_profiles): Loaded profiles data: {self.color_profiles}")
            except Exception as e:
                print(
                    f"VSD ERROR (_load_color_profiles): Error loading json: {e}")
                self.color_profiles = {}
        else:
            # DIAGNOSTIC
            print(
                f"VSD DEBUG (_load_color_profiles): File not found at {filepath}. Profiles empty.")
            self.color_profiles = {}
        # _update_profile_list_widget() is called by _populate_ui_from_settings later

    def _save_color_profiles(self):
        filepath = self._get_color_profile_filepath()
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump({"profiles": self.color_profiles}, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Profile Save Error",
                                f"Could not save: {e}")



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

        # --- ADDED: Create and add Dual VU Tab ---
        dv_page = self._create_dual_vu_settings_tab() # Call new method
        self.tab_widget.addTab(dv_page, "🎶 Dual VU")
        dv_page.setProperty("mode_key", "dual_vu_spectrum")
        # --- END ADD ---

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        buttons.accepted.connect(self._apply_all_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)


    def _populate_ui_from_settings(self):
        # Spectrum Bars Settings
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
                if i < len(sb_colors_data): button.setColor(QColor(sb_colors_data[i]))
                else: button.setColor(QColor(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))

        # Pulse Wave Settings
        pw_settings = self.all_settings.get("pulse_wave_matrix", {})
        if self.pw_color_button:
            self.pw_color_button.setColor(QColor(pw_settings.get("color", QColor("cyan").name())))
        if self.pw_speed_slider:
            speed_val = pw_settings.get("speed", 50)
            self.pw_speed_slider.setValue(speed_val)
            self._on_pw_speed_changed(speed_val) 
        if self.pw_brightness_sensitivity_slider:
            bs_val = pw_settings.get("brightness_sensitivity", 75)
            self.pw_brightness_sensitivity_slider.setValue(bs_val)
            self._on_pw_brightness_sensitivity_changed(bs_val)

        # --- ADDED: Populate Dual VU Settings ---
        dvu_settings = self.all_settings.get("dual_vu_spectrum", {})
        if self.dvu_low_color_button:
            self.dvu_low_color_button.setColor(QColor(dvu_settings.get("vu_low_color", QColor(Qt.GlobalColor.green).name())))
        if self.dvu_mid_color_button:
            self.dvu_mid_color_button.setColor(QColor(dvu_settings.get("vu_mid_color", QColor(Qt.GlobalColor.yellow).name())))
        if self.dvu_high_color_button:
            self.dvu_high_color_button.setColor(QColor(dvu_settings.get("vu_high_color", QColor(Qt.GlobalColor.red).name())))
        
        if self.dvu_threshold_mid_slider:
            mid_thresh_val = dvu_settings.get("vu_threshold_mid", 60)
            self.dvu_threshold_mid_slider.setValue(mid_thresh_val)
            self._on_dvu_threshold_mid_changed(mid_thresh_val)
        if self.dvu_threshold_high_slider:
            high_thresh_val = dvu_settings.get("vu_threshold_high", 85)
            self.dvu_threshold_high_slider.setValue(high_thresh_val)
            self._on_dvu_threshold_high_changed(high_thresh_val)
        if self.dvu_falloff_speed_slider:
            falloff_val = dvu_settings.get("vu_falloff_speed", 50)
            self.dvu_falloff_speed_slider.setValue(falloff_val)
            self._on_dvu_falloff_speed_changed(falloff_val)
        # --- END ADD ---
            
        if hasattr(self, 'profile_list_widget') and self.profile_list_widget is not None: # This is still SpectrumBar specific
            self._update_profile_list_widget()
        # else:
            # print("VSD ERROR (_populate_ui_from_settings): self.profile_list_widget is None or does not exist.")



    def _select_initial_tab(self):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).property("mode_key") == self.current_mode_key_on_open:
                self.tab_widget.setCurrentIndex(i)
                return
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)

    def _create_spectrum_bars_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        page_main_layout = QHBoxLayout(page_widget)
        page_main_layout.setSpacing(15)

        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.addWidget(
            QLabel("Customize colors and responsiveness for the 8 spectrum bars."))
        left_panel_layout.addWidget(
            QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken))

        general_group = QGroupBox("General Visualizer Settings")
        general_layout = QVBoxLayout(general_group)

        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Sensitivity:"))
        self.sb_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sb_sensitivity_slider.setRange(0, 100)
        self.sb_sensitivity_slider.valueChanged.connect(
            self._on_sb_sensitivity_changed)
        sensitivity_layout.addWidget(self.sb_sensitivity_slider, 1)
        self.sb_sensitivity_label = QLabel("")
        self.sb_sensitivity_label.setMinimumWidth(50)
        sensitivity_layout.addWidget(self.sb_sensitivity_label)
        general_layout.addLayout(sensitivity_layout)

        smoothing_layout = QHBoxLayout()
        smoothing_layout.addWidget(QLabel("Smoothing Factor:"))
        self.sb_smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.sb_smoothing_slider.setRange(0, 99)
        self.sb_smoothing_slider.valueChanged.connect(
            self._on_sb_smoothing_changed)
        smoothing_layout.addWidget(self.sb_smoothing_slider, 1)
        self.sb_smoothing_label = QLabel("")
        self.sb_smoothing_label.setMinimumWidth(50)
        smoothing_layout.addWidget(self.sb_smoothing_label)
        general_layout.addLayout(smoothing_layout)

        # --- ADDED: Grow Downwards Checkbox ---
        self.sb_grow_downwards_checkbox = QCheckBox(
            "Grow Bars Downwards (from top)")
        self.sb_grow_downwards_checkbox.setToolTip(
            "If checked, bars will grow from the top row downwards. Default is upwards from bottom row."
        )
        self.sb_grow_downwards_checkbox.stateChanged.connect(
            self._on_sb_grow_downwards_changed  # New slot to connect
        )
        general_layout.addWidget(self.sb_grow_downwards_checkbox)
        # --- END ADD ---

        left_panel_layout.addWidget(general_group)

        colors_group_box = QGroupBox("Bar Color Customization")
        colors_group_layout = QVBoxLayout(colors_group_box)
        colors_grid_layout = QGridLayout()
        colors_grid_layout.setHorizontalSpacing(15)
        colors_grid_layout.setVerticalSpacing(8)
        self.sb_color_buttons = []
        for i in range(DIALOG_NUMBER_OF_SPECTRUM_BARS):
            r, c_label = divmod(i, 2)
            c_btn = c_label + 1
            label = QLabel(f"Bar {i + 1}:")
            label.setAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)
            color_button = ColorGradientButton(parent=self)
            color_button.setProperty("band_index", i)
            color_button.clicked.connect(
                lambda checked=False, btn=color_button: self._on_dialog_sb_color_button_clicked(btn))
            self.sb_color_buttons.append(color_button)
            colors_grid_layout.addWidget(label, r, c_label * 2)
            colors_grid_layout.addWidget(
                color_button, r, c_btn * 2 - 1)
        colors_group_layout.addLayout(colors_grid_layout)

        reset_button_layout = QHBoxLayout()
        reset_button_layout.addStretch(1)
        self.sb_reset_button = QPushButton("↺ Reset Bar Settings")
        self.sb_reset_button.clicked.connect(
            self._reset_spectrum_bars_settings_to_defaults)
        reset_button_layout.addWidget(self.sb_reset_button)
        reset_button_layout.addStretch(1)
        colors_group_layout.addSpacing(10)
        colors_group_layout.addLayout(reset_button_layout)
        left_panel_layout.addWidget(colors_group_box)
        left_panel_layout.addStretch(1)
        page_main_layout.addWidget(left_panel_widget, 1)

        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        user_profiles_group = QGroupBox("My Saved Palettes")
        user_profiles_layout = QVBoxLayout(user_profiles_group)
        self.profile_list_widget = QListWidget()
        user_profiles_layout.addWidget(self.profile_list_widget, 1)
        profile_actions_layout = QHBoxLayout()
        self.load_profile_button = QPushButton("⤵️ Load")
        try:
            self.load_profile_button.setIcon(
                QIcon(get_resource_path("resources/icons/load.png")))
        except:
            pass
        self.load_profile_button.clicked.connect(
            self._load_selected_profile_to_current_mode_tab)
        profile_actions_layout.addWidget(self.load_profile_button)
        self.delete_profile_button = QPushButton("🗑️ Delete")
        try:
            self.delete_profile_button.setIcon(
                QIcon(get_resource_path("resources/icons/delete.png")))
        except:
            pass
        self.delete_profile_button.clicked.connect(
            self._delete_selected_profile)
        profile_actions_layout.addWidget(self.delete_profile_button)
        user_profiles_layout.addLayout(profile_actions_layout)
        right_panel_layout.addWidget(user_profiles_group)

        save_group = QGroupBox("Save Current Settings")
        save_layout = QVBoxLayout(save_group)
        save_layout.addWidget(QLabel("Palette Name:"))
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Enter new palette name...")
        save_layout.addWidget(self.profile_name_edit)
        self.save_profile_button = QPushButton("💾 Save New")
        try:
            self.save_profile_button.setIcon(
                QIcon(get_resource_path("resources/icons/save.png")))
        except:
            pass
        self.save_profile_button.clicked.connect(
            self._save_current_mode_colors_as_profile)
        save_layout.addWidget(self.save_profile_button)
        right_panel_layout.addWidget(save_group)

        prefab_group = QGroupBox("Prefab Palettes")
        prefab_layout = QVBoxLayout(prefab_group)
        prefab_layout.addWidget(QLabel("Click to load:"))
        buttons_data = [("rainbow", "🌈 Rainbow"), ("fire_ice", "🔥❄️ Fire & Ice"), ("synthwave", "🔮 Synthwave"),
                        ("forest", "🌲 Forest"), ("ocean_sunset", "🌅 Sunset")]
        for key, text in buttons_data:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked=False,
                                k=key: self._apply_prefab_palette(k))
            setattr(self, f"prefab_{key}_button", btn)
            prefab_layout.addWidget(btn)
        prefab_layout.addStretch(1)
        right_panel_layout.addWidget(prefab_group, 1)
        right_panel_layout.addStretch(1)
        page_main_layout.addWidget(right_panel_widget, 1)
        return page_widget

   # --- ADDED: _on_sb_grow_downwards_changed ---
    def _on_sb_grow_downwards_changed(self, state):
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["grow_downwards"] = bool(
            state == Qt.CheckState.Checked.value)


    # NEW slot for live internal update
    def _on_sb_sensitivity_changed(self, value):
        self._update_sb_sensitivity_label(value)
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["sensitivity"] = value

    # NEW slot for live internal update
    def _on_sb_smoothing_changed(self, value):
        self._update_sb_smoothing_label(value)
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["smoothing"] = value

    def _update_sb_sensitivity_label(self, value):  # Just updates label now
        if self.sb_sensitivity_label:
            self.sb_sensitivity_label.setText(f"{value / 50.0:.2f}x")

    def _update_sb_smoothing_label(self, value):  # Just updates label now
        if self.sb_smoothing_label:
            self.sb_smoothing_label.setText(f"{value / 100.0:.2f}")

    def _on_dialog_sb_color_button_clicked(self, button_clicked: ColorGradientButton):
        band_index = button_clicked.property("band_index")
        new_color = QColorDialog.getColor(
            button_clicked.getColor(), self, f"Select Color for Bar {band_index + 1}")
        if new_color.isValid():
            button_clicked.setColor(new_color)
            sb_settings = self.all_settings.setdefault(
                "classic_spectrum_bars", {})
            colors = sb_settings.get("band_colors", list(
                self.DEFAULT_SPECTRUM_BAR_COLORS_HEX))
            while len(colors) <= band_index:
                colors.append(QColor("grey").name())
            colors[band_index] = new_color.name()
            sb_settings["band_colors"] = colors

    def _reset_spectrum_bars_settings_to_defaults(self):
        if self.sb_sensitivity_slider:
            self.sb_sensitivity_slider.setValue(
                self.DEFAULT_SENSITIVITY_SLIDER)
        if self.sb_smoothing_slider:
            self.sb_smoothing_slider.setValue(self.DEFAULT_SMOOTHING_SLIDER)

        # --- ADDED: Reset Grow Downwards Checkbox ---
        if self.sb_grow_downwards_checkbox:
            self.sb_grow_downwards_checkbox.setChecked(
                False)  # Default to grow upwards
        # --- END ADD ---

        for i, button in enumerate(self.sb_color_buttons):
            button.setColor(QColor(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(
                self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))

        # Update the working copy in self.all_settings
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["band_colors"] = list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)
        sb_settings["sensitivity"] = self.DEFAULT_SENSITIVITY_SLIDER
        sb_settings["smoothing"] = self.DEFAULT_SMOOTHING_SLIDER
        # Ensure it's set in the working copy
        sb_settings["grow_downwards"] = False



    def _update_profile_list_widget(self):
        # --- ADDED CHECK AND PRINT ---
        if not hasattr(self, 'profile_list_widget') or self.profile_list_widget is None:
            print(
                "VSD ERROR (_update_profile_list_widget): self.profile_list_widget is None. Cannot update.")
            return
        # --- END CHECK AND PRINT ---

        self.profile_list_widget.clear()
        # DIAGNOSTIC
        print(
            f"VSD DEBUG (_update_profile_list_widget): Updating profile list with keys from self.color_profiles: {list(self.color_profiles.keys())}")
        for profile_name in sorted(self.color_profiles.keys()):
            self.profile_list_widget.addItem(QListWidgetItem(profile_name))

# In class VisualizerSettingsDialog:

    def _collect_settings_from_all_tabs(self) -> dict:
        # Classic Spectrum Bars
        current_sb_settings = self.all_settings.setdefault(
            "classic_spectrum_bars", {})
        if hasattr(self, 'sb_color_buttons') and self.sb_color_buttons:
            current_sb_settings["band_colors"] = [
                btn.getColor().name() for btn in self.sb_color_buttons]
        if hasattr(self, 'sb_sensitivity_slider') and self.sb_sensitivity_slider:
            current_sb_settings["sensitivity"] = self.sb_sensitivity_slider.value(
            )
        if hasattr(self, 'sb_smoothing_slider') and self.sb_smoothing_slider:
            current_sb_settings["smoothing"] = self.sb_smoothing_slider.value()
        if hasattr(self, 'sb_grow_downwards_checkbox') and self.sb_grow_downwards_checkbox:
            current_sb_settings["grow_downwards"] = self.sb_grow_downwards_checkbox.isChecked(
            )

        # Pulse Wave
        current_pw_settings = self.all_settings.setdefault(
            "pulse_wave_matrix", {})
        if hasattr(self, 'pw_color_button') and self.pw_color_button:
            current_pw_settings["color"] = self.pw_color_button.getColor(
            ).name()
        if hasattr(self, 'pw_speed_slider') and self.pw_speed_slider:
            current_pw_settings["speed"] = self.pw_speed_slider.value()
        if hasattr(self, 'pw_brightness_sensitivity_slider') and self.pw_brightness_sensitivity_slider:
            current_pw_settings["brightness_sensitivity"] = self.pw_brightness_sensitivity_slider.value(
            )

        # --- ADDED: Collect Dual VU Settings ---
        current_dvu_settings = self.all_settings.setdefault(
            "dual_vu_spectrum", {})
        if hasattr(self, 'dvu_low_color_button') and self.dvu_low_color_button:
            current_dvu_settings["vu_low_color"] = self.dvu_low_color_button.getColor(
            ).name()
        if hasattr(self, 'dvu_mid_color_button') and self.dvu_mid_color_button:
            current_dvu_settings["vu_mid_color"] = self.dvu_mid_color_button.getColor(
            ).name()
        if hasattr(self, 'dvu_high_color_button') and self.dvu_high_color_button:
            current_dvu_settings["vu_high_color"] = self.dvu_high_color_button.getColor(
            ).name()
        if hasattr(self, 'dvu_threshold_mid_slider') and self.dvu_threshold_mid_slider:
            current_dvu_settings["vu_threshold_mid"] = self.dvu_threshold_mid_slider.value(
            )
        if hasattr(self, 'dvu_threshold_high_slider') and self.dvu_threshold_high_slider:
            current_dvu_settings["vu_threshold_high"] = self.dvu_threshold_high_slider.value(
            )
        if hasattr(self, 'dvu_falloff_speed_slider') and self.dvu_falloff_speed_slider:
            current_dvu_settings["vu_falloff_speed"] = self.dvu_falloff_speed_slider.value(
            )
        # --- END ADD ---

        final_settings_to_emit = {}
        for mode_key, mode_data in self.all_settings.items():
            final_settings_to_emit[mode_key] = mode_data.copy()
            # Ensure all potential list keys are handled
            for list_key_collection in [["band_colors", "palette"], ["spectrum_colors"]]:
                for list_key in list_key_collection:
                    if list_key in final_settings_to_emit[mode_key] and \
                        isinstance(final_settings_to_emit[mode_key][list_key], list):
                        final_settings_to_emit[mode_key][list_key] = list(
                            final_settings_to_emit[mode_key][list_key])

        return final_settings_to_emit

    def _apply_all_settings(self):  # Called by OK button
        final_settings_to_emit = self._collect_settings_from_all_tabs()
        self.all_settings_applied.emit(final_settings_to_emit)
        self._save_color_profiles()  # Save named profiles if any changes

    def _apply_all_and_accept(self):
        self._apply_all_settings()
        self.accept()

    def _load_selected_profile_to_current_mode_tab(self):
        active_mode_key = "classic_spectrum_bars"
        if not self.profile_list_widget:
            return
        selected = self.profile_list_widget.selectedItems()
        if not selected:
            return

        profile_name = selected[0].text()
        profile_all_modes_data = self.color_profiles.get(profile_name)

        if profile_all_modes_data and active_mode_key in profile_all_modes_data:
            settings_to_load = profile_all_modes_data[active_mode_key]

            # Update working copy directly - ensure it's a copy
            self.all_settings[active_mode_key] = settings_to_load.copy()
            # Ensure list is copied
            if "band_colors" in self.all_settings[active_mode_key]:
                self.all_settings[active_mode_key]["band_colors"] = list(
                    self.all_settings[active_mode_key]["band_colors"])

            # Update UI for classic_spectrum_bars from the newly loaded settings in self.all_settings
            if self.sb_sensitivity_slider:
                self.sb_sensitivity_slider.setValue(self.all_settings[active_mode_key].get(
                    "sensitivity", self.DEFAULT_SENSITIVITY_SLIDER))
            if self.sb_smoothing_slider:
                self.sb_smoothing_slider.setValue(self.all_settings[active_mode_key].get(
                    "smoothing", self.DEFAULT_SMOOTHING_SLIDER))

            # --- ADDED: Update Grow Downwards Checkbox from Profile ---
            if self.sb_grow_downwards_checkbox:
                self.sb_grow_downwards_checkbox.setChecked(
                    self.all_settings[active_mode_key].get("grow_downwards", False))
            # --- END ADD ---

            loaded_colors = self.all_settings[active_mode_key].get(
                "band_colors", [])
            for i, btn in enumerate(self.sb_color_buttons):
                btn.setColor(QColor(loaded_colors[i] if i < len(
                    loaded_colors) else self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))
        else:
            QMessageBox.warning(
                self, "Load Error", f"'{profile_name}' is invalid or not applicable for Spectrum Bars.")




    def _save_current_mode_colors_as_profile(self):
        active_mode_key = "classic_spectrum_bars"  # Context is this tab
        if not self.profile_name_edit:
            return

        name = self.profile_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Error", "Enter palette name.")
            return
        if name in self.color_profiles:
            if QMessageBox.question(self, "Overwrite?", f"'{name}' exists. Overwrite?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                return

        # Settings are already live in self.all_settings[active_mode_key] due to UI interaction updates
        settings_to_save = self.all_settings.get(active_mode_key, {}).copy()
        if not settings_to_save:
            QMessageBox.warning(self, "Save Error", "No settings to save.")
            return

        if name not in self.color_profiles:
            self.color_profiles[name] = {}
        self.color_profiles[name][active_mode_key] = settings_to_save

        self._save_color_profiles()
        self._update_profile_list_widget()  # Refresh list
        self.profile_name_edit.clear()
        # QMessageBox.information(self, "Saved", f"Palette '{name}' saved.")

    def _delete_selected_profile(self):
        if not self.profile_list_widget:
            return
        selected = self.profile_list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "Delete", "Select palette.")
            return
        name = selected[0].text()
        if QMessageBox.question(self, "Confirm", f"Delete '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if name in self.color_profiles:
                del self.color_profiles[name]
                self._save_color_profiles()
                self._update_profile_list_widget()  # Refresh list
                # QMessageBox.information(self, "Deleted", f"'{name}' deleted.")

    def _apply_prefab_palette(self, prefab_key: str):
        active_mode_key = "classic_spectrum_bars"
        if active_mode_key not in self.PREFAB_PALETTES or prefab_key not in self.PREFAB_PALETTES[active_mode_key]:
            QMessageBox.warning(
                self, "Prefab Error", f"Prefab '{prefab_key}' not found for Spectrum Bars.")
            return

        settings_to_load = self.PREFAB_PALETTES[active_mode_key][prefab_key]

        # Update working copy directly - ensure it's a copy
        self.all_settings[active_mode_key] = settings_to_load.copy()
        # Ensure list is copied
        if "band_colors" in self.all_settings[active_mode_key]:
            self.all_settings[active_mode_key]["band_colors"] = list(
                self.all_settings[active_mode_key]["band_colors"])

        # Prefabs might not have 'grow_downwards', so ensure a default if missing
        if "grow_downwards" not in self.all_settings[active_mode_key]:
            self.all_settings[active_mode_key]["grow_downwards"] = False

        # Update UI for classic_spectrum_bars from the newly loaded settings in self.all_settings
        if self.sb_sensitivity_slider:
            self.sb_sensitivity_slider.setValue(self.all_settings[active_mode_key].get(
                "sensitivity", self.DEFAULT_SENSITIVITY_SLIDER))
        if self.sb_smoothing_slider:
            self.sb_smoothing_slider.setValue(self.all_settings[active_mode_key].get(
                "smoothing", self.DEFAULT_SMOOTHING_SLIDER))

        # --- ADDED: Update Grow Downwards Checkbox from Prefab ---
        if self.sb_grow_downwards_checkbox:
            self.sb_grow_downwards_checkbox.setChecked(
                self.all_settings[active_mode_key].get("grow_downwards", False))
        # --- END ADD ---

        loaded_colors = self.all_settings[active_mode_key].get(
            "band_colors", [])
        for i, btn in enumerate(self.sb_color_buttons):
            btn.setColor(QColor(loaded_colors[i] if i < len(
                loaded_colors) else self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))

    def _create_pulse_wave_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        # Use QVBoxLayout for stacking groups
        page_layout = QVBoxLayout(page_widget)
        page_layout.setSpacing(10)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Basic Settings Group
        basic_settings_group = QGroupBox("Pulse Wave Basic Settings")
        # Use QGridLayout for label-slider pairs
        basic_settings_layout = QGridLayout(basic_settings_group)

        # Color Picker
        basic_settings_layout.addWidget(
            QLabel("Pulse Color:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_color_button = ColorGradientButton(parent=self)
        self.pw_color_button.clicked.connect(self._on_pw_color_changed)
        basic_settings_layout.addWidget(self.pw_color_button, 0, 1)

        # Pulse Speed Slider
        basic_settings_layout.addWidget(
            QLabel("Base Pulse Speed:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_speed_slider = QSlider(Qt.Orientation.Horizontal)
        # e.g., 0 = slowest, 100 = fastest
        self.pw_speed_slider.setRange(0, 100)
        self.pw_speed_slider.valueChanged.connect(self._on_pw_speed_changed)
        basic_settings_layout.addWidget(self.pw_speed_slider, 1, 1)
        self.pw_speed_label = QLabel("50")  # Initial value example
        self.pw_speed_label.setMinimumWidth(30)
        basic_settings_layout.addWidget(self.pw_speed_label, 1, 2)

        # Brightness Sensitivity Slider
        basic_settings_layout.addWidget(
            QLabel("Brightness Sensitivity (Audio):"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.pw_brightness_sensitivity_slider = QSlider(
            Qt.Orientation.Horizontal)
        # e.g., 0 = no audio reaction, 100 = full reaction
        self.pw_brightness_sensitivity_slider.setRange(0, 100)
        self.pw_brightness_sensitivity_slider.valueChanged.connect(
            self._on_pw_brightness_sensitivity_changed)
        basic_settings_layout.addWidget(
            self.pw_brightness_sensitivity_slider, 2, 1)
        self.pw_brightness_sensitivity_label = QLabel(
            "1.0x")  # Initial value example
        self.pw_brightness_sensitivity_label.setMinimumWidth(40)
        basic_settings_layout.addWidget(
            self.pw_brightness_sensitivity_label, 2, 2)

        # Set column stretch for the sliders to take more space
        basic_settings_layout.setColumnStretch(1, 1)

        page_layout.addWidget(basic_settings_group)
        page_layout.addStretch(1)  # Push settings to the top

        return page_widget

    # --- NEW: Slots for Pulse Wave UI changes ---
    def _on_pw_color_changed(self):
        if not self.pw_color_button:
            return
        new_color = QColorDialog.getColor(
            self.pw_color_button.getColor(), self, "Select Pulse Color")
        if new_color.isValid():
            self.pw_color_button.setColor(new_color)
            pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
            pw_settings["color"] = new_color.name()

    def _on_pw_speed_changed(self, value):
        if self.pw_speed_label:
            # Example: Map 0-100 slider to a speed factor or descriptive text
            self.pw_speed_label.setText(f"{value}")
        pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
        pw_settings["speed"] = value

    def _on_pw_brightness_sensitivity_changed(self, value):
        if self.pw_brightness_sensitivity_label:
            # Example: Map 0-100 slider to a factor (e.g., 0.0x to 2.0x)
            factor = value / 50.0
            self.pw_brightness_sensitivity_label.setText(f"{factor:.1f}x")
        pw_settings = self.all_settings.setdefault("pulse_wave_matrix", {})
        pw_settings["brightness_sensitivity"] = value

# In class VisualizerSettingsDialog:

    def _create_dual_vu_settings_tab(self) -> QWidget:
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setSpacing(10)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # VU Meter Settings Group
        vu_settings_group = QGroupBox("VU Meter Appearance (Mono-Driven)")
        vu_settings_layout = QGridLayout(vu_settings_group)
        vu_settings_layout.setColumnStretch(1, 1) # Slider column takes more space

        # VU Colors
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
        
        # Spacer row
        vu_settings_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed), 3, 0, 1, 3)


        # VU Thresholds
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

        # VU Falloff Speed
        vu_settings_layout.addWidget(QLabel("Falloff Speed:"), 6, 0, Qt.AlignmentFlag.AlignRight)
        self.dvu_falloff_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.dvu_falloff_speed_slider.setRange(0, 100) # Higher is faster falloff
        self.dvu_falloff_speed_slider.valueChanged.connect(self._on_dvu_falloff_speed_changed)
        vu_settings_layout.addWidget(self.dvu_falloff_speed_slider, 6, 1)
        self.dvu_falloff_speed_label = QLabel("50")
        self.dvu_falloff_speed_label.setMinimumWidth(40)
        vu_settings_layout.addWidget(self.dvu_falloff_speed_label, 6, 2)

        page_layout.addWidget(vu_settings_group)

        # Placeholder for Central Spectrum settings - to be added later
        spectrum_group = QGroupBox("Central Spectrum Settings (Coming Soon)")
        spectrum_layout = QVBoxLayout(spectrum_group)
        spectrum_layout.addWidget(QLabel("Controls for the central spectrum will appear here."))
        page_layout.addWidget(spectrum_group)
        
        # Placeholder for Palette Management for this mode - to be added later
        palette_group = QGroupBox("Palette Management (Coming Soon)")
        palette_layout = QVBoxLayout(palette_group)
        palette_layout.addWidget(QLabel("Profile saving/loading for Dual VU mode will appear here."))
        page_layout.addWidget(palette_group)


        page_layout.addStretch(1) # Push settings to the top
        return page_widget
    
# In class VisualizerSettingsDialog:

    def _on_dvu_color_changed(self, color_type: str):
        button_to_update: ColorGradientButton | None = None
        setting_key: str = ""

        if color_type == "low":
            button_to_update = self.dvu_low_color_button
            setting_key = "vu_low_color"
        elif color_type == "mid":
            button_to_update = self.dvu_mid_color_button
            setting_key = "vu_mid_color"
        elif color_type == "high":
            button_to_update = self.dvu_high_color_button
            setting_key = "vu_high_color"
        
        if not button_to_update or not setting_key:
            return

        new_color = QColorDialog.getColor(button_to_update.getColor(), self, f"Select VU {color_type.capitalize()} Color")
        if new_color.isValid():
            button_to_update.setColor(new_color)
            dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
            dvu_settings[setting_key] = new_color.name()

    def _on_dvu_threshold_mid_changed(self, value):
        if self.dvu_threshold_mid_label:
            self.dvu_threshold_mid_label.setText(f"{value}%")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_threshold_mid"] = value
        # Ensure high threshold is always >= mid threshold
        if self.dvu_threshold_high_slider and value > self.dvu_threshold_high_slider.value():
            self.dvu_threshold_high_slider.setValue(value)


    def _on_dvu_threshold_high_changed(self, value):
        if self.dvu_threshold_high_label:
            self.dvu_threshold_high_label.setText(f"{value}%")
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_threshold_high"] = value
        # Ensure mid threshold is always <= high threshold
        if self.dvu_threshold_mid_slider and value < self.dvu_threshold_mid_slider.value():
            self.dvu_threshold_mid_slider.setValue(value)

    def _on_dvu_falloff_speed_changed(self, value):
        if self.dvu_falloff_speed_label:
            self.dvu_falloff_speed_label.setText(f"{value}") # Higher value = faster falloff
        dvu_settings = self.all_settings.setdefault("dual_vu_spectrum", {})
        dvu_settings["vu_falloff_speed"] = value
        
