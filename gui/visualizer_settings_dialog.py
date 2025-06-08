# AKAI_Fire_RGB_Controller/gui/visualizer_settings_dialog.py
import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QTabWidget, QWidget,
    QPushButton, QSlider, QGridLayout, QColorDialog, QListWidget, QListWidgetItem,
    QLineEdit, QInputDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QGroupBox
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
        self.all_settings = {}  # This will be the working copy

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
                "classic_spectrum_bars": {"band_colors": list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX), "sensitivity": self.DEFAULT_SENSITIVITY_SLIDER, "smoothing": self.DEFAULT_SMOOTHING_SLIDER},
                "pulse_wave_matrix": {"palette": [QColor("cyan").name(), QColor("magenta").name(), QColor("yellow").name()], "pulse_speed": 50},
                "dual_vu_spectrum": {"vu_low_color": QColor("green").name(), "bass_spectrum_color": QColor("red").name()}
            }

        self.setWindowTitle("⚙️ Visualizer Settings")
        self.setMinimumSize(800, 520)

        # Initialize all UI attributes to None first
        self.sb_sensitivity_slider, self.sb_sensitivity_label = None, None
        self.sb_smoothing_slider, self.sb_smoothing_label = None, None
        self.sb_color_buttons, self.sb_reset_button = [], None
        self.profile_list_widget, self.profile_name_edit = None, None
        self.load_profile_button, self.save_profile_button, self.delete_profile_button = None, None, None
        self.prefab_rainbow_button, self.prefab_fire_ice_button = None, None
        self.prefab_synthwave_button, self.prefab_forest_button, self.prefab_ocean_sunset_button = None, None, None

        self.color_profiles = {}
        self._init_ui()
        self._load_color_profiles()       # Load profiles before populating UI
        self._populate_ui_from_settings()  # Populate UI based on self.all_settings
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

        pm_page = QWidget()
        pm_layout = QVBoxLayout(pm_page)
        pm_layout.addWidget(QLabel("Pulse Wave Matrix Settings (WIP)"))
        self.tab_widget.addTab(pm_page, "🌊 Pulse Wave")
        pm_page.setProperty("mode_key", "pulse_wave_matrix")

        dv_page = QWidget()
        dv_layout = QVBoxLayout(dv_page)
        dv_layout.addWidget(QLabel("Dual VU & Spectrum Settings (WIP)"))
        self.tab_widget.addTab(dv_page, "🎶 Dual VU")
        dv_page.setProperty("mode_key", "dual_vu_spectrum")

        # MODIFIED: Only OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "OK")  # Simpler text
        # OK will apply and accept
        buttons.accepted.connect(self._apply_all_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def _populate_ui_from_settings(self):
        # ... (population of sb_sensitivity_slider, sb_smoothing_slider, sb_color_buttons)
        sb_settings = self.all_settings.get("classic_spectrum_bars", {})
        if self.sb_sensitivity_slider:
            slider_val = sb_settings.get(
                "sensitivity", self.DEFAULT_SENSITIVITY_SLIDER)
            self.sb_sensitivity_slider.setValue(slider_val)
            self._update_sb_sensitivity_label(slider_val)
        if self.sb_smoothing_slider:
            slider_val = sb_settings.get(
                "smoothing", self.DEFAULT_SMOOTHING_SLIDER)
            self.sb_smoothing_slider.setValue(slider_val)
            self._update_sb_smoothing_label(slider_val)

        sb_colors_data = sb_settings.get(
            "band_colors", list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX))
        if hasattr(self, 'sb_color_buttons'):
            for i, button in enumerate(self.sb_color_buttons):
                if i < len(sb_colors_data):
                    button.setColor(QColor(sb_colors_data[i]))
                else:
                    button.setColor(QColor(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(
                        self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))

        # --- MODIFIED ---
        print(
            "VSD DEBUG (_populate_ui_from_settings): Calling _update_profile_list_widget()")
        if hasattr(self, 'profile_list_widget') and self.profile_list_widget is not None:
            self._update_profile_list_widget()
        else:
            print("VSD ERROR (_populate_ui_from_settings): self.profile_list_widget is None or does not exist when trying to update.")
        # --- END MODIFIED ---


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
            self._on_sb_sensitivity_changed)  # Connect to new handler
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
            self._on_sb_smoothing_changed)  # Connect to new handler
        smoothing_layout.addWidget(self.sb_smoothing_slider, 1)
        self.sb_smoothing_label = QLabel("")
        self.sb_smoothing_label.setMinimumWidth(50)
        smoothing_layout.addWidget(self.sb_smoothing_label)
        general_layout.addLayout(smoothing_layout)
        left_panel_layout.addWidget(general_group)

        colors_group_box = QGroupBox("Bar Color Customization")
        colors_group_layout = QVBoxLayout(colors_group_box)
        colors_grid_layout = QGridLayout()
        colors_grid_layout.setHorizontalSpacing(15)
        colors_grid_layout.setVerticalSpacing(8)
        self.sb_color_buttons = []
        for i in range(DIALOG_NUMBER_OF_SPECTRUM_BARS):
            r, c_label = divmod(i, 2)
            c_btn = c_label + 1  # 2 color pickers per row (label+button)
            label = QLabel(f"Bar {i + 1}:")
            label.setAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)
            color_button = ColorGradientButton(parent=self)
            color_button.setProperty("band_index", i)
            color_button.clicked.connect(
                lambda checked=False, btn=color_button: self._on_dialog_sb_color_button_clicked(btn))
            self.sb_color_buttons.append(color_button)
            # Span label over its own cell
            colors_grid_layout.addWidget(label, r, c_label * 2)
            colors_grid_layout.addWidget(
                color_button, r, c_btn * 2 - 1)  # Button in next cell
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
        for i, button in enumerate(self.sb_color_buttons):
            button.setColor(QColor(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(
                self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))
        sb_settings = self.all_settings.setdefault("classic_spectrum_bars", {})
        sb_settings["band_colors"] = list(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)
        sb_settings["sensitivity"] = self.DEFAULT_SENSITIVITY_SLIDER
        sb_settings["smoothing"] = self.DEFAULT_SMOOTHING_SLIDER

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

    def _collect_settings_from_all_tabs(self) -> dict:
        # This method now primarily reads from self.all_settings, which should be kept live.
        # However, for robustness, it can re-collect from UI, especially for not-yet-live elements.
        for i in range(self.tab_widget.count()):
            page = self.tab_widget.widget(i)
            mode_key = page.property("mode_key")
            if not mode_key:
                continue

            # For classic_spectrum_bars, self.all_settings is already live.
            # For other modes (when implemented), if their UI changes don't instantly update
            # self.all_settings[mode_key], this is where they'd be collected.
            if mode_key == "classic_spectrum_bars":
                # Ensure self.all_settings is current if direct UI elements were missed by live updates
                if hasattr(self, 'sb_color_buttons') and self.sb_color_buttons:
                    self.all_settings[mode_key]["band_colors"] = [
                        btn.getColor().name() for btn in self.sb_color_buttons]
                if hasattr(self, 'sb_sensitivity_slider') and self.sb_sensitivity_slider:
                    self.all_settings[mode_key]["sensitivity"] = self.sb_sensitivity_slider.value(
                    )
                if hasattr(self, 'sb_smoothing_slider') and self.sb_smoothing_slider:
                    self.all_settings[mode_key]["smoothing"] = self.sb_smoothing_slider.value(
                    )
            # TODO: Collect for other modes if their UI doesn't live-update self.all_settings[mode_key]
        return self.all_settings.copy()  # Return a copy

    def _apply_all_settings(self):  # Called by OK button
        final_settings_to_emit = self._collect_settings_from_all_tabs()
        self.all_settings_applied.emit(final_settings_to_emit)
        self._save_color_profiles()  # Save named profiles if any changes

    def _apply_all_and_accept(self):
        self._apply_all_settings()
        self.accept()

    def _load_selected_profile_to_current_mode_tab(self):
        active_mode_key = "classic_spectrum_bars"  # Context is this tab
        if not self.profile_list_widget:
            return
        selected = self.profile_list_widget.selectedItems()
        if not selected:
            # QMessageBox.information(self, "Load", "Select a palette.")
            return

        profile_name = selected[0].text()
        profile_all_modes_data = self.color_profiles.get(profile_name)

        if profile_all_modes_data and active_mode_key in profile_all_modes_data:
            settings_to_load = profile_all_modes_data[active_mode_key]
            # Update working copy
            self.all_settings[active_mode_key] = settings_to_load.copy()
            if "band_colors" in self.all_settings[active_mode_key]:
                self.all_settings[active_mode_key]["band_colors"] = list(
                    self.all_settings[active_mode_key]["band_colors"])

            # Update UI for classic_spectrum_bars
            if self.sb_sensitivity_slider:
                self.sb_sensitivity_slider.setValue(settings_to_load.get(
                    "sensitivity", self.DEFAULT_SENSITIVITY_SLIDER))
            if self.sb_smoothing_slider:
                self.sb_smoothing_slider.setValue(settings_to_load.get(
                    "smoothing", self.DEFAULT_SMOOTHING_SLIDER))
            colors = settings_to_load.get("band_colors", [])
            for i, btn in enumerate(self.sb_color_buttons):
                btn.setColor(QColor(colors[i] if i < len(
                    colors) else self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))
            # QMessageBox.information(
            #     self, "Loaded", f"'{profile_name}' loaded.")
        else:
            QMessageBox.warning(self, "Load Error",
                                f"'{profile_name}' invalid for Spectrum Bars.")

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
        active_mode_key = "classic_spectrum_bars"  # Context is this tab
        if active_mode_key not in self.PREFAB_PALETTES or prefab_key not in self.PREFAB_PALETTES[active_mode_key]:
            QMessageBox.warning(self, "Prefab Error",
                                f"Prefab '{prefab_key}' not found.")
            return

        settings_to_load = self.PREFAB_PALETTES[active_mode_key][prefab_key]
        # Update working copy
        self.all_settings[active_mode_key] = settings_to_load.copy()
        if "band_colors" in self.all_settings[active_mode_key]:
            self.all_settings[active_mode_key]["band_colors"] = list(
                self.all_settings[active_mode_key]["band_colors"])

        # Update UI for classic_spectrum_bars
        if self.sb_sensitivity_slider:
            self.sb_sensitivity_slider.setValue(settings_to_load.get(
                "sensitivity", self.DEFAULT_SENSITIVITY_SLIDER))
        if self.sb_smoothing_slider:
            self.sb_smoothing_slider.setValue(settings_to_load.get(
                "smoothing", self.DEFAULT_SMOOTHING_SLIDER))
        colors = settings_to_load.get("band_colors", [])
        for i, btn in enumerate(self.sb_color_buttons):
            btn.setColor(QColor(colors[i] if i < len(
                colors) else self.DEFAULT_SPECTRUM_BAR_COLORS_HEX[i % len(self.DEFAULT_SPECTRUM_BAR_COLORS_HEX)]))
        # QMessageBox.information(self, "Prefab Loaded",
        #                         f"Prefab '{prefab_key}' loaded.")
