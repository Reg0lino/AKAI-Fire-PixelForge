# AKAI_Fire_RGB_Controller/gui/sequence_file_manager.py
import os
import json
import glob
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QMessageBox, QInputDialog, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt

# --- Module Level Constants ---
PREFAB_SEQUENCES_DIR_NAME = "prefab"
USER_SEQUENCES_DIR_NAME = "user"
SAMPLER_RECORDINGS_DIR_NAME = "sampler_recordings" 
SEQUENCES_BASE_SUBDIR = "sequences" 

class SequenceFileManager(QGroupBox):
    load_sequence_requested = pyqtSignal(str) 
    new_sequence_clicked = pyqtSignal()       
    save_sequence_as_requested = pyqtSignal() 
    # Emits: display_name, filepath, type_id (e.g., "user", "sampler", "prefab")
    delete_sequence_requested = pyqtSignal(str, str, str) 
    status_message_requested = pyqtSignal(str, int)

    def __init__(self, presets_base_path: str, parent: QWidget | None = None,
                 group_box_title: str = "🎞️ Animator Sequences"):
        super().__init__(group_box_title, parent)
        self.presets_base_path = presets_base_path
        # Stores {display_name_with_prefix: {"path": ..., "type": ..., "raw_name": ...}}
        self.loaded_sequences = {} 

        self._init_ui()
        self.refresh_sequences_list_and_select() # Initial population

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.sequences_combo = QComboBox()
        self.sequences_combo.setPlaceholderText("--- Select Sequence ---")
        self.sequences_combo.setObjectName("SequencesComboBox") # For potential styling
        layout.addWidget(self.sequences_combo)

        load_new_layout = QHBoxLayout()
        self.load_seq_button = QPushButton("📲 Load Selected")
        self.load_seq_button.setToolTip("Load the sequence selected in the dropdown.")
        self.load_seq_button.clicked.connect(self._handle_load_selected_button_clicked)
        load_new_layout.addWidget(self.load_seq_button)

        self.new_seq_button = QPushButton("✨ New Sequence")
        self.new_seq_button.setToolTip(f"Clear the animator and start a new blank sequence (Ctrl+N)")
        self.new_seq_button.setStatusTip(f"Clear the animator and start a new blank sequence (Shortcut: Ctrl+N).")
        self.new_seq_button.clicked.connect(self.new_sequence_clicked)
        load_new_layout.addWidget(self.new_seq_button)
        layout.addLayout(load_new_layout)
        
        save_delete_layout = QHBoxLayout()
        self.save_seq_button = QPushButton("💾 Save Seq As...")
        self.save_seq_button.setToolTip("Save the current animation sequence to a new file or overwrite an existing user file.")
        self.save_seq_button.clicked.connect(self.save_sequence_as_requested)
        save_delete_layout.addWidget(self.save_seq_button)
        
        self.delete_seq_button = QPushButton("🗑️ Delete Seq")
        self.delete_seq_button.setToolTip("Delete the selected user-saved or sampler-recorded sequence file.")
        self.delete_seq_button.clicked.connect(self._handle_delete_sequence)
        save_delete_layout.addWidget(self.delete_seq_button)
        layout.addLayout(save_delete_layout)
        
        self.sequences_combo.currentIndexChanged.connect(self._on_combo_selection_changed)
        self.set_enabled_state(False, False) # Initially disabled

    def _handle_load_selected_button_clicked(self):
        index = self.sequences_combo.currentIndex()
        if index > 0: # 0 is "--- Select Sequence ---" or "No sequences found"
            selected_display_name = self.sequences_combo.itemText(index)
            if selected_display_name != "No sequences found" and selected_display_name in self.loaded_sequences:
                seq_info = self.loaded_sequences[selected_display_name]
                self.load_sequence_requested.emit(seq_info["path"])
            else:
                self.status_message_requested.emit("Sequence info not found for selection.", 2000)
        else:
            self.status_message_requested.emit("No valid sequence selected to load.", 2000)

    def set_enabled_state(self, enabled: bool, has_active_frames: bool = False):
        is_list_populated = bool(self.loaded_sequences) and self.sequences_combo.count() > 1 
        
        self.sequences_combo.setEnabled(enabled and is_list_populated)
        self.new_seq_button.setEnabled(enabled)
        self.save_seq_button.setEnabled(enabled and has_active_frames)

        is_valid_item_selected_for_load_delete = False
        can_delete_selected_item = False

        current_idx = self.sequences_combo.currentIndex()
        if current_idx > 0:
            current_text = self.sequences_combo.itemText(current_idx)
            if current_text != "No sequences found" and current_text in self.loaded_sequences:
                is_valid_item_selected_for_load_delete = True
                seq_info = self.loaded_sequences[current_text]
                if seq_info.get("type") in ["user", "sampler"]:
                    can_delete_selected_item = True
        
        self.load_seq_button.setEnabled(enabled and is_valid_item_selected_for_load_delete)
        self.delete_seq_button.setEnabled(enabled and can_delete_selected_item)

        if enabled and not is_list_populated and self.sequences_combo.itemText(0) == "--- Select Sequence ---":
            self.sequences_combo.blockSignals(True)
            self.sequences_combo.clear()
            self.sequences_combo.addItem("No sequences found")
            self.sequences_combo.setEnabled(False)
            self.sequences_combo.blockSignals(False)


    def _sanitize_filename(self, name: str) -> str:
        name = str(name) # Ensure it's a string
        name = re.sub(r'[^\w\s-]', '', name).strip()
        name = re.sub(r'[-\s]+', '_', name)
        return name if name else "untitled_sequence"

    def load_all_sequences_metadata(self):
        self.loaded_sequences.clear()
        seq_sources = [
            ("sampler", SAMPLER_RECORDINGS_DIR_NAME, "[Sampler] "), 
            ("user", USER_SEQUENCES_DIR_NAME, ""), 
            ("prefab", PREFAB_SEQUENCES_DIR_NAME, "[Prefab] ")
        ]
        found_any = False
        for type_id, rel_dir_name, prefix in seq_sources:
            abs_dir = os.path.join(self.presets_base_path, SEQUENCES_BASE_SUBDIR, rel_dir_name)
            try: # Ensure directory exists, create if not
                os.makedirs(abs_dir, exist_ok=True)
            except OSError as e:
                print(f"SFM Error: Could not create directory {abs_dir}: {e}")
                continue # Skip this source if directory can't be made

            if not os.path.isdir(abs_dir): continue # Should not happen if makedirs worked
            
            for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                data = None 
                try:
                    with open(filepath, "r", encoding='utf-8') as f: 
                        data = json.load(f) 
                    
                    if not isinstance(data, dict) or \
                       "name" not in data or \
                       "frames" not in data or \
                       not isinstance(data.get("frames"), list):
                        print(f"SFM Info: Skipped malformed sequence (missing keys or frames not list): {filepath}")
                        continue 

                    raw_name_from_file = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                    display_name = prefix + str(raw_name_from_file).replace("_", " ").replace("-", " ")
                    
                    if display_name:
                        self.loaded_sequences[display_name] = {
                            "path": filepath, "type": type_id, "raw_name": raw_name_from_file
                        }
                        found_any = True
                except json.JSONDecodeError:
                    print(f"SFM Warning: JSONDecodeError for sequence file {filepath}. Skipping.")
                except Exception as e: 
                    print(f"SFM Error: General error processing sequence file {filepath}: {type(e).__name__} - {e}") 
        return found_any

    def _update_sequences_combo(self, active_sequence_raw_name: str = None, 
                                active_sequence_type: str = None, 
                                force_selection: bool = False):
        self.sequences_combo.blockSignals(True)
        current_text_before_clear = self.sequences_combo.currentText()
        self.sequences_combo.clear()
        self.sequences_combo.addItem("--- Select Sequence ---") # Placeholder first

        if not self.loaded_sequences:
            self.sequences_combo.addItem("No sequences found")
        else:
            # Sort: Prefabs, then Sampler, then User, then alphabetically within each group
            sorted_keys = sorted(
                self.loaded_sequences.keys(), 
                key=lambda k: (
                    0 if self.loaded_sequences[k]['type'] == 'prefab' else
                    1 if self.loaded_sequences[k]['type'] == 'sampler' else
                    2 if self.loaded_sequences[k]['type'] == 'user' else 3, 
                    k.lower() # Alphabetical within type
                )
            )
            self.sequences_combo.addItems(sorted_keys)

        target_select_idx = 0 
        text_to_find = None

        if force_selection and active_sequence_raw_name and active_sequence_raw_name != "New Sequence":
            prefix_to_use = ""
            if active_sequence_type == "prefab": prefix_to_use = "[Prefab] "
            elif active_sequence_type == "sampler": prefix_to_use = "[Sampler] "
            # For "user" type, raw_name is usually the same as the display name part (no prefix from this list)
            
            text_to_find = prefix_to_use + str(active_sequence_raw_name).replace("_", " ").replace("-", " ")
        elif not force_selection and current_text_before_clear not in ["--- Select Sequence ---", "No sequences found", "Populating..."]:
            text_to_find = current_text_before_clear
        
        if text_to_find:
            idx = self.sequences_combo.findText(text_to_find, Qt.MatchFlag.MatchFixedString) # Exact match
            if idx != -1: target_select_idx = idx
        
        if self.sequences_combo.count() > target_select_idx :
             self.sequences_combo.setCurrentIndex(target_select_idx)
        
        self.sequences_combo.blockSignals(False)
        # Update button states based on the new selection (or lack thereof)
        # This will be called AFTER set_enabled_state from MainWindow, so it's fine to call here.
        self._on_combo_selection_changed(self.sequences_combo.currentIndex())


    def refresh_sequences_list_and_select(self, active_sequence_raw_name: str = None, 
                                          active_sequence_type: str = None, 
                                          force_selection: bool = False):
        self.load_all_sequences_metadata()
        self._update_sequences_combo(active_sequence_raw_name, active_sequence_type, force_selection)
        # The set_enabled_state is generally called from MainWindow after this refresh,
        # considering other factors like has_active_frames.

    def _on_combo_selection_changed(self, index: int):
        is_list_populated = bool(self.loaded_sequences) and self.sequences_combo.count() > 1
        is_valid_item_selected = index > 0 and \
                                 self.sequences_combo.itemText(index) != "No sequences found"
        
        self.load_seq_button.setEnabled(is_valid_item_selected and self.isEnabled())
        can_delete = False
        if is_valid_item_selected:
            selected_display_name = self.sequences_combo.itemText(index)
            if selected_display_name in self.loaded_sequences:
                seq_info = self.loaded_sequences[selected_display_name]
                can_delete = seq_info.get("type") in ["user", "sampler"]
        self.delete_seq_button.setEnabled(can_delete and self.isEnabled())


    def get_save_path_for_new_sequence(self, current_model_name: str, target_dir_type: str = "user") -> tuple[str, str, str] | None:
        """ Prompts user for a name and returns (filepath, raw_name, type_id_of_save_dir).
            target_dir_type can be "user" or "sampler" (though sampler is usually auto-saved).
        """
        suggested_name = current_model_name if current_model_name != "New Sequence" else ""
        text, ok = QInputDialog.getText(self, "Save Sequence As...", "Sequence Name:", text=suggested_name)
        if not (ok and text): return None
        
        raw_name = text.strip() 
        if not raw_name: QMessageBox.warning(self, "Save Error", "Name cannot be empty."); return None
        
        # Prevent name clashes with [Prefab] versions if saving to user/sampler
        if target_dir_type != "prefab":
            display_name_check_prefab = "[Prefab] " + raw_name.replace("_", " ").replace("-", " ")
            if display_name_check_prefab in self.loaded_sequences:
                QMessageBox.warning(self, "Save Error", f"A prefab sequence with a similar display name ('{raw_name}') already exists. Please choose a different name."); return None

        filename_base = self._sanitize_filename(raw_name)
        filename = f"{filename_base}.json"
        
        actual_save_dir_name = ""
        actual_save_type_id = ""
        if target_dir_type == "sampler": # This case is mostly for completeness, auto-save usually handles this path
            actual_save_dir_name = SAMPLER_RECORDINGS_DIR_NAME
            actual_save_type_id = "sampler"
        else: # Default to "user"
            actual_save_dir_name = USER_SEQUENCES_DIR_NAME
            actual_save_type_id = "user"

        abs_target_dir = os.path.join(self.presets_base_path, SEQUENCES_BASE_SUBDIR, actual_save_dir_name)
        os.makedirs(abs_target_dir, exist_ok=True)
        filepath = os.path.join(abs_target_dir, filename)
        
        if os.path.exists(filepath):
            reply = QMessageBox.question(self, "Overwrite Confirmation", f"File '{filename}' already exists in '{actual_save_dir_name}'. Overwrite?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return None
            
        return filepath, raw_name, actual_save_type_id

    def _handle_delete_sequence(self):
        selected_display_name = self.sequences_combo.currentText()
        if not selected_display_name or selected_display_name == "--- Select Sequence ---" or selected_display_name == "No sequences found":
            self.status_message_requested.emit("No valid sequence selected to delete.", 2000); return
        
        if selected_display_name not in self.loaded_sequences:
            self.status_message_requested.emit(f"Internal error: Selected sequence '{selected_display_name}' not in loaded data.", 3000)
            self.refresh_sequences_list_and_select() # Refresh to fix inconsistency
            return

        seq_info = self.loaded_sequences[selected_display_name]
        if seq_info["type"] not in ["user", "sampler"]:
            QMessageBox.warning(self, "Delete Error", "Only user-saved or sampler-recorded sequences can be deleted via this UI."); return
        
        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete '{selected_display_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_sequence_requested.emit(selected_display_name, seq_info["path"], seq_info["type"])
