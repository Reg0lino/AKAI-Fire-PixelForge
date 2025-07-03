# AKAI_Fire_RGB_Controller/gui/static_layouts_manager.py
import os
import json
import glob
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QMessageBox, QInputDialog, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor # For validating color strings

PREFAB_STATIC_DIR_NAME = "prefab"
USER_STATIC_DIR_NAME = "user"
STATIC_BASE_SUBDIR = "static"

class StaticLayoutsManager(QGroupBox):
    apply_layout_data_requested = pyqtSignal(list)
    request_current_grid_colors = pyqtSignal()
    status_message_requested = pyqtSignal(str, int)

    def __init__(self, 
                user_static_layouts_path: str,
                prefab_static_layouts_path: str,
                parent: QWidget | None = None, # Keep parent if needed for QGroupBox
                group_box_title: str = "▦ Static Pad Layouts"):
        super().__init__(group_box_title, parent) # Pass parent to QGroupBox
        # self.presets_base_path = presets_base_path # Old way
        self.user_static_layouts_path = user_static_layouts_path
        self.prefab_static_layouts_path = prefab_static_layouts_path
        self.loaded_layouts = {} 
        self._init_ui()
        self.refresh_layouts_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.layouts_combo = QComboBox()
        self.layouts_combo.setPlaceholderText("--- Select Static Layout ---")
        layout.addWidget(self.layouts_combo)
        buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Layout")
        self.apply_button.clicked.connect(self._handle_apply_layout)
        self.save_button = QPushButton("Save Current As...")
        self.save_button.clicked.connect(self.request_current_grid_colors)
        self.delete_button = QPushButton("Delete Layout")
        self.delete_button.clicked.connect(self._handle_delete_layout)
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.delete_button)
        layout.addLayout(buttons_layout)
        self.layouts_combo.currentIndexChanged.connect(self._on_combo_selection_changed)

    def set_enabled_state(self, enabled: bool):
        """
        Updates the enabled state of the buttons based on the parent groupbox's
        state and the selection in the layouts combo box.
        The layouts_combo itself is enabled/disabled by the QGroupBox parent.
        """
        # The QComboBox (self.layouts_combo) will inherit its enabled state
        # directly from the QGroupBox (self). So, we do NOT set its enabled state here.
        is_list_populated = bool(
            self.loaded_layouts) and self.layouts_combo.count() > 1
        is_valid_selection = self.layouts_combo.currentIndex() > 0 and \
            self.layouts_combo.currentText() != "No static layouts found"
        # Apply button depends on:
        # 1. The overall groupbox being enabled (checked by self.isEnabled())
        # 2. A valid layout being selected
        self.apply_button.setEnabled(self.isEnabled() and is_valid_selection)
        # Save button depends on:
        # 1. The overall groupbox being enabled
        self.save_button.setEnabled(self.isEnabled())
        # Delete button depends on:
        # 1. The overall groupbox being enabled
        # 2. A valid layout being selected
        # 3. The selected layout being a "user" layout
        can_delete = False
        if self.isEnabled() and is_valid_selection:
            current_layout_name = self.layouts_combo.currentText()
            if current_layout_name in self.loaded_layouts:
                can_delete = self.loaded_layouts[current_layout_name].get(
                    "type") == "user"
        self.delete_button.setEnabled(can_delete)
        # Handle the "No static layouts found" display state.
        # This state should only be displayed if the list is truly empty (after refresh)
        # and the widget is enabled.
        if self.isEnabled() and not is_list_populated and \
            self.layouts_combo.itemText(0) != "No static layouts found":
            # Avoid triggering _on_combo_selection_changed prematurely
            self.layouts_combo.blockSignals(True)
            self.layouts_combo.clear()
            self.layouts_combo.addItem("No static layouts found")
            self.layouts_combo.blockSignals(False)
            # The QComboBox itself is enabled/disabled by the QGroupBox parent.
            # So, if self.isEnabled() is True but no layouts, it'll show "No static layouts found"
            # and still be clickable (but only to show the one disabled item).
            # This is standard Qt behavior.

    def _get_layouts_dir_path(self, layout_type="user") -> str:
        # This method now directly returns the full path passed during __init__
        if layout_type == "user":
            return self.user_static_layouts_path
        elif layout_type == "prefab":
            return self.prefab_static_layouts_path
        else:
            print(f"Warning: Unknown layout_type '{layout_type}' in StaticLayoutsManager. Defaulting to user path.")
            return self.user_static_layouts_path # Fallback

    def _sanitize_filename(self, name: str) -> str:
        name = re.sub(r'[^\w\s-]', '', name).strip(); name = re.sub(r'[-\s]+', '_', name)
        return name if name else "untitled_layout"

    def _is_valid_color_list(self, color_list) -> bool:
        """Checks if it's a list of 64 valid hex color strings."""
        if not (isinstance(color_list, list) and len(color_list) == 64):
            return False
        for item in color_list:
            if not isinstance(item, str) or not QColor(item).isValid():
                return False
        return True

    def refresh_layouts_list(self, select_name: str | None = None):
        self.layouts_combo.blockSignals(True)
        current_selection_text = self.layouts_combo.currentText()
        self.layouts_combo.clear()
        self.loaded_layouts.clear()
        self.layouts_combo.addItem("--- Select Static Layout ---")
        layout_sources = [
            ("prefab", self._get_layouts_dir_path("prefab"), "[Prefab] "),
            ("user", self._get_layouts_dir_path("user"), "")
        ]
        found_any = False
        for type_id, abs_dir, prefix in layout_sources:
            if not os.path.isdir(abs_dir): continue
            for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
                display_name = ""
                layout_format = None
                raw_name_from_file = filename_no_ext # Default raw name
                try:
                    with open(filepath, 'r') as f: data = json.load(f)
                    
                    if self._is_valid_color_list(data): # New format: direct list
                        layout_format = "list"
                        display_name = prefix + filename_no_ext.replace("_", " ").replace("-", " ")
                    elif isinstance(data, dict) and "colors" in data and self._is_valid_color_list(data["colors"]): # Old format
                        layout_format = "object"
                        raw_name_from_file = data.get("name", filename_no_ext) # Use name from JSON if available
                        display_name = prefix + raw_name_from_file.replace("_", " ").replace("-", " ")
                    else:
                        print(f"StaticLayoutsManager: Skipped malformed layout: {filepath}")
                        continue
                    if display_name:
                        self.loaded_layouts[display_name] = {"path": filepath, "type": type_id, "format": layout_format, "raw_name": raw_name_from_file}
                        found_any = True
                except json.JSONDecodeError:
                    print(f"StaticLayoutsManager: Skipped invalid JSON: {filepath}")
                except Exception as e:
                    print(f"StaticLayoutsManager: Error reading {filepath}: {e}")
        if found_any:
            sorted_keys = sorted(self.loaded_layouts.keys(), key=lambda k: (self.loaded_layouts[k]['type'] == 'prefab', k.lower()))
            self.layouts_combo.addItems(sorted_keys)
        # else: # "---Select Static Layout---" is already there
            # self.layouts_combo.addItem("No static layouts found") # This state handled by set_enabled_state
        target_select_idx = 0 # Default to "--- Select ---"
        if select_name:
            # If select_name is a raw_name, we need to find its display_name form
            # This logic assumes select_name passed is the raw_name (for user layouts)
            # or the display_name (for prefabs or if MainWindow passes display_name)
            temp_select_name = select_name
            is_select_name_raw = not select_name.startswith("[Prefab] ")
            if is_select_name_raw: # Try to find matching raw_name among user layouts
                found_match = False
                for dn, info in self.loaded_layouts.items():
                    if info['type'] == 'user' and info['raw_name'] == select_name:
                        temp_select_name = dn
                        found_match = True
                        break
            idx = self.layouts_combo.findText(temp_select_name)
            if idx != -1: target_select_idx = idx
        elif current_selection_text and current_selection_text not in ["--- Select Static Layout ---", "No static layouts found"]:
            idx = self.layouts_combo.findText(current_selection_text)
            if idx != -1: target_select_idx = idx
        if self.layouts_combo.count() > 0:
            self.layouts_combo.setCurrentIndex(target_select_idx)
        self.layouts_combo.blockSignals(False)
        self._on_combo_selection_changed(self.layouts_combo.currentIndex())

    def _on_combo_selection_changed(self, index: int):
        """
        Handles selection changes in the combo box. Recalculates button enabled states.
        """
        # Re-evaluate all button states based on the current selection and groupbox enabled state.
        self.set_enabled_state(self.isEnabled())

    def get_navigation_item_count(self) -> int:
        """Returns the number of actual items in the layouts combo box (excluding placeholder)."""
        if self.layouts_combo:
            count = 0
            for i in range(self.layouts_combo.count()):
                if self.layouts_combo.itemText(i) != "--- Select Static Layout ---" and \
                    self.layouts_combo.itemText(i) != "No static layouts found":
                    # A more robust way might be to check if itemData exists if you add it,
                    # or if the key exists in self.loaded_layouts.
                    # For now, checking against known placeholder/status texts.
                    # Or simply: if i > 0 and self.layouts_combo.itemText(i) != "No static layouts found": count +=1
                    # Assuming placeholder is always at index 0.
                    if i > 0 : # Index 0 is "--- Select ---" or "No layouts"
                        current_text = self.layouts_combo.itemText(i)
                        if current_text in self.loaded_layouts: # Check against known loaded layouts
                            count +=1
            return count
        return 0

    def get_navigation_item_text_at_logical_index(self, logical_index: int) -> str | None:
        """
        Returns the display text of the layout at the given logical_index.
        Logical_index is 0-based for actual layout items, skipping placeholder.
        """
        if self.layouts_combo:
            actual_combo_index = -1
            current_logical_idx = -1
            for i in range(self.layouts_combo.count()):
                # Consider actual items to be those in self.loaded_layouts
                current_text = self.layouts_combo.itemText(i)
                if current_text in self.loaded_layouts:
                    current_logical_idx += 1
                    if current_logical_idx == logical_index:
                        actual_combo_index = i
                        break
            
            if actual_combo_index != -1:
                return self.layouts_combo.itemText(actual_combo_index)
        return None

    def set_navigation_current_item_by_logical_index(self, logical_index: int) -> str | None:
        """
        Sets the current item in the layouts combo box by its logical index (0-based, skipping placeholders).
        """
        if self.layouts_combo:
            item_count = self.get_navigation_item_count()
            if item_count == 0:
                return None
            # Ensure the logical index wraps around correctly
            wrapped_logical_index = logical_index % item_count
            if wrapped_logical_index < 0:
                wrapped_logical_index += item_count
            actual_combo_index_to_set = -1
            current_logical_idx = -1
            for i in range(self.layouts_combo.count()):
                current_text = self.layouts_combo.itemText(i)
                if current_text in self.loaded_layouts:
                    current_logical_idx += 1
                    if current_logical_idx == wrapped_logical_index:
                        actual_combo_index_to_set = i
                        break
            if actual_combo_index_to_set != -1:
                if self.layouts_combo.currentIndex() != actual_combo_index_to_set:
                    self.layouts_combo.setCurrentIndex(
                        actual_combo_index_to_set)
                return self.layouts_combo.itemText(actual_combo_index_to_set)
        return None

    def trigger_navigation_current_item_action(self):
        """
        Triggers the action for the currently selected item in the layouts combo box,
        which is applying it.
        """
        print("SLM TRACE: trigger_navigation_current_item_action called.") # Optional
        # This reuses the logic from the "Apply Layout" button.
        if self.apply_button.isEnabled(): # Check if apply is possible
            self._handle_apply_layout()
        else: # Optional
            print("SLM TRACE: Apply button not enabled, no action taken.")

    def _handle_apply_layout(self):
        selected_display_name = self.layouts_combo.currentText()
        if not selected_display_name or selected_display_name not in self.loaded_layouts:
            self.status_message_requested.emit("No layout selected.", 2000); return
        layout_info = self.loaded_layouts[selected_display_name]
        filepath = layout_info["path"]
        try:
            with open(filepath, "r") as f: data = json.load(f)
            colors_hex = None
            if layout_info.get("format") == "list" or isinstance(data, list): # Prioritize format flag, fallback to type check
                if self._is_valid_color_list(data): colors_hex = data
            elif layout_info.get("format") == "object" or isinstance(data, dict):
                if "colors" in data and self._is_valid_color_list(data["colors"]):
                    colors_hex = data["colors"]
            if colors_hex:
                self.apply_layout_data_requested.emit(colors_hex)
                self.status_message_requested.emit(f"Layout '{selected_display_name}' applied.", 1500)
            else:
                QMessageBox.warning(self, "Load Error", f"Layout file '{os.path.basename(filepath)}' has an unsupported format or invalid color data.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Error loading '{os.path.basename(filepath)}': {e}")
            self.status_message_requested.emit(f"Error loading layout: {e}", 3000)

    def save_layout_with_colors(self, colors_hex: list): # Saves in NEW simple list format
        if not self._is_valid_color_list(colors_hex):
            QMessageBox.warning(self, "Save Error", "Invalid color data for saving."); return
        text, ok = QInputDialog.getText(self, "Save Static Layout As...", "Layout Name:")
        if not (ok and text): return
        raw_name = text.strip()
        if not raw_name: QMessageBox.warning(self, "Save Error", "Name cannot be empty."); return
        # Check for clashes with prefab names based on the raw name
        prefixed_raw_name_check = "[Prefab] " + raw_name.replace("_", " ").replace("-", " ")
        if prefixed_raw_name_check in self.loaded_layouts:
            QMessageBox.warning(self, "Save Error", f"Name '{raw_name}' conflicts with a Prefab layout."); return
        filename_base = self._sanitize_filename(raw_name)
        filename = f"{filename_base}.json"
        user_layouts_dir = self._get_layouts_dir_path("user")
        os.makedirs(user_layouts_dir, exist_ok=True)
        filepath = os.path.join(user_layouts_dir, filename)
        # Check if user layout with this raw_name (which becomes display name for user) already exists
        display_name_to_check = raw_name.replace("_", " ").replace("-", " ") # User layouts don't have prefix in self.loaded_layouts keys
        if os.path.exists(filepath): # Simpler check: just if file exists
            reply = QMessageBox.question(self, "Overwrite Confirmation",
                                        f"Layout file '{filename}' already exists. Overwrite?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return
        try:
            with open(filepath, "w") as f: json.dump(colors_hex, f, indent=4) # Save as simple list
            self.status_message_requested.emit(f"Layout '{raw_name}' saved.", 2000)
            self.refresh_layouts_list(select_name=display_name_to_check) # Select by display name form
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save to '{filepath}': {e}")

    def _handle_delete_layout(self):
        selected_display_name = self.layouts_combo.currentText()
        if not selected_display_name or selected_display_name not in self.loaded_layouts:
            self.status_message_requested.emit("No layout selected to delete.", 2000); return
        layout_info = self.loaded_layouts[selected_display_name]
        if layout_info["type"] != "user":
            QMessageBox.warning(self, "Delete Error", "Only user-saved layouts can be deleted."); return
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    f"Are you sure you want to delete '{selected_display_name}'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(layout_info["path"])
                self.status_message_requested.emit(f"Layout '{selected_display_name}' deleted.", 2000)
                self.refresh_layouts_list() 
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Could not delete layout file: {e}")