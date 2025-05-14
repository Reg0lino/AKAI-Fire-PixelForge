# AKAI_Fire_RGB_Controller/animator/timeline_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QAbstractItemView, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction # For context menu

class SequenceTimelineWidget(QWidget):
    frame_selected = pyqtSignal(int)  # Emits frame index when selected
    # For context menu actions (could also be handled internally or connect to MainWindow)
    add_frame_action_triggered = pyqtSignal(str) # "snapshot", "blank"
    duplicate_frame_action_triggered = pyqtSignal(int) # frame_index
    delete_frame_action_triggered = pyqtSignal(int) # frame_index
    insert_blank_frame_before_action_triggered = pyqtSignal(int) # frame_index
    insert_blank_frame_after_action_triggered = pyqtSignal(int) # frame_index

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_selected_frame_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.frame_list_widget = QListWidget()
        self.frame_list_widget.setViewMode(QListWidget.ViewMode.IconMode) # Horizontal layout
        self.frame_list_widget.setFlow(QListWidget.Flow.LeftToRight)     # Items flow left to right
        self.frame_list_widget.setWrapping(False)                       # No wrapping, use scrollbar
        self.frame_list_widget.setMovement(QListWidget.Movement.Static) # Items not movable by user drag (yet)
        self.frame_list_widget.setUniformItemSizes(True) # Optimization
        self.frame_list_widget.setStyleSheet("""
            QListWidget { 
                border: 1px solid #444; 
                background-color: #282828; /* Darker background for timeline itself */
            }
            QListWidget::item { 
                background-color: #3A3A3A; 
                color: #E0E0E0; 
                border: 1px solid #505050; 
                border-radius: 3px; 
                padding: 5px; 
                margin: 2px; 
                min-width: 60px; /* Width of frame item */
                max-width: 60px;
                min-height: 40px; /* Height of frame item */
                max-height: 40px;
            }
            QListWidget::item:selected { 
                background-color: #5A7EA6; /* Selection color */
                border: 1px solid #7A9EC6;
            }
        """)
        self.frame_list_widget.currentItemChanged.connect(self._on_current_item_changed)
        self.frame_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frame_list_widget.customContextMenuRequested.connect(self.show_timeline_context_menu)

        layout.addWidget(self.frame_list_widget)
        self.setMinimumHeight(80) # Give it some default height

    def _on_current_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            index = self.frame_list_widget.row(current)
            if index != self.current_selected_frame_index:
                self.current_selected_frame_index = index
                self.frame_selected.emit(index)
        # else: # No item selected
        #     if self.current_selected_frame_index != -1:
        #         self.current_selected_frame_index = -1
        #         self.frame_selected.emit(-1) # Indicate no selection

    def show_timeline_context_menu(self, position: QPoint):
        menu = QMenu()
        item_at_pos = self.frame_list_widget.itemAt(position)
        selected_index = self.frame_list_widget.row(item_at_pos) if item_at_pos else -1

        # Actions that don't depend on an item being selected
        add_snapshot_action = QAction("➕ Add Snapshot Frame", self) # Using plus emoji as it's more common than camera for this
        add_snapshot_action.triggered.connect(lambda: self.add_frame_action_triggered.emit("snapshot"))
        menu.addAction(add_snapshot_action)

        add_blank_action = QAction("➕ Add Blank Frame", self)
        add_blank_action.triggered.connect(lambda: self.add_frame_action_triggered.emit("blank"))
        menu.addAction(add_blank_action)
        
        menu.addSeparator()

        if item_at_pos and selected_index != -1: # If right-clicked on an existing frame
            duplicate_action = QAction("📋 Duplicate Frame", self)
            duplicate_action.triggered.connect(lambda: self.duplicate_frame_action_triggered.emit(selected_index))
            menu.addAction(duplicate_action)
            
            menu.addSeparator()

            insert_blank_before = QAction("➕ Insert Blank Before", self)
            insert_blank_before.triggered.connect(lambda: self.insert_blank_frame_before_action_triggered.emit(selected_index))
            menu.addAction(insert_blank_before)
            
            insert_blank_after = QAction("➕ Insert Blank After", self)
            insert_blank_after.triggered.connect(lambda: self.insert_blank_frame_after_action_triggered.emit(selected_index + 1)) # Insert after current
            menu.addAction(insert_blank_after)

            menu.addSeparator()
            
            delete_action = QAction("🗑️ Delete Frame", self)
            delete_action.triggered.connect(lambda: self.delete_frame_action_triggered.emit(selected_index))
            menu.addAction(delete_action)
        
        menu.exec(self.frame_list_widget.mapToGlobal(position))


    def update_frames_display(self, frame_count: int, current_edit_idx: int = -1, current_playback_idx: int = -1):
        # print(f"Timeline: Updating display. Frames: {frame_count}, EditIdx: {current_edit_idx}, PlaybackIdx: {current_playback_idx}")
        self.frame_list_widget.blockSignals(True) # Block signals during programmatic update
        
        current_selection_restored = False
        # Store current item's text if possible to reselect it by content
        # selected_item_text = self.frame_list_widget.currentItem().text() if self.frame_list_widget.currentItem() else None

        self.frame_list_widget.clear()
        
        for i in range(frame_count):
            item_text = f"Frame {i + 1}"
            # TODO: Later, item could be a custom widget with a mini-preview
            item = QListWidgetItem(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) # Center text
            self.frame_list_widget.addItem(item)

            # if selected_item_text and item_text == selected_item_text:
            #    self.frame_list_widget.setCurrentItem(item)
            #    current_selection_restored = True

        # Try to set current item based on index
        if 0 <= current_edit_idx < self.frame_list_widget.count():
            self.frame_list_widget.setCurrentRow(current_edit_idx) # This should also trigger _on_current_item_changed if it changes
            self.current_selected_frame_index = current_edit_idx # Ensure internal state is consistent
            # Make sure the selected item is visible
            item_to_scroll = self.frame_list_widget.item(current_edit_idx)
            if item_to_scroll:
                self.frame_list_widget.scrollToItem(item_to_scroll, QAbstractItemView.ScrollHint.EnsureVisible)

        # TODO: Visual indication for current_playback_idx (e.g., different background/border)
        # This might require custom item delegates or per-item styling if QListWidgetItem doesn't support it easily.
        # For now, selection indicates edit frame. Playback highlight is a future enhancement.

        self.frame_list_widget.blockSignals(False)

    def set_selected_frame_by_index(self, index: int):
        """Programmatically selects a frame in the list."""
        self.frame_list_widget.blockSignals(True)
        if 0 <= index < self.frame_list_widget.count():
            self.frame_list_widget.setCurrentRow(index)
            self.current_selected_frame_index = index
            # self.frame_selected.emit(index) # No, _on_current_item_changed handles this if selection actually changes
        elif self.frame_list_widget.count() == 0: # No items
            self.current_selected_frame_index = -1
            # self.frame_selected.emit(-1)
        self.frame_list_widget.blockSignals(False)

    def get_selected_frame_index(self) -> int:
        # current_item = self.frame_list_widget.currentItem()
        # return self.frame_list_widget.row(current_item) if current_item else -1
        return self.current_selected_frame_index # Use our tracked index