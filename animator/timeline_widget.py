# AKAI_Fire_RGB_Controller/animator/timeline_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                             QAbstractItemView, QMenu, QStyledItemDelegate, QApplication,
                             QStyleOptionViewItem, QStyle) # <<< ADD QStyle HERE
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QRect, QModelIndex
from PyQt6.QtGui import QAction, QPainter, QColor, QBrush, QPen, QKeySequence

# --- Icons (Unicode Emojis) - Mirroring controls_widget for consistency ---
ICON_ADD_SNAPSHOT = "📷"
ICON_ADD_BLANK = "⬛"
ICON_DUPLICATE = "📋" # Also used for Paste
ICON_DELETE = "🗑️"
ICON_COPY = "📄"
ICON_CUT = "✂️"
# ICON_PASTE = "📋" # Re-using ICON_DUPLICATE for Paste

THUMBNAIL_PAD_SIZE = 3
THUMBNAIL_PAD_SPACING = 1
THUMBNAIL_COLS = 16 
THUMBNAIL_ROWS = 4

# Item Padding (around the content within an item)
ITEM_PADDING_HORIZONTAL = 5 # e.g., 5px left, 5px right
ITEM_PADDING_VERTICAL_TOP_FOR_TEXT = 2 # Padding above text
ITEM_PADDING_VERTICAL_BETWEEN_TEXT_THUMB = 3 # Padding between text and thumbnail grid
ITEM_PADDING_VERTICAL_BOTTOM = 2 # Padding below thumbnail grid

# --- Recalculate THUMBNAIL_ITEM_WIDTH and THUMBNAIL_ITEM_HEIGHT ---
# Width calculation:
# (Num cols * pad size) + (Num spaces between cols * space size) + (2 * horizontal item padding)
THUMBNAIL_GRID_CONTENT_WIDTH = (THUMBNAIL_COLS * THUMBNAIL_PAD_SIZE) + \
                               ((THUMBNAIL_COLS - 1) * THUMBNAIL_PAD_SPACING if THUMBNAIL_COLS > 0 else 0)
THUMBNAIL_ITEM_WIDTH = THUMBNAIL_GRID_CONTENT_WIDTH + (2 * ITEM_PADDING_HORIZONTAL)

# Height calculation:
# Text Height (approximate, can be font-dependent, let's use a reasonable fixed estimate or calculate dynamically)
# For simplicity, let's estimate text height + its top padding + padding below it before thumbnail.
# A typical small font might be 12-15px high.
ESTIMATED_TEXT_AREA_HEIGHT_WITH_PADDING = 15 + ITEM_PADDING_VERTICAL_TOP_FOR_TEXT + ITEM_PADDING_VERTICAL_BETWEEN_TEXT_THUMB

THUMBNAIL_GRID_CONTENT_HEIGHT = (THUMBNAIL_ROWS * THUMBNAIL_PAD_SIZE) + \
                                ((THUMBNAIL_ROWS - 1) * THUMBNAIL_PAD_SPACING if THUMBNAIL_ROWS > 0 else 0)

THUMBNAIL_ITEM_HEIGHT = ESTIMATED_TEXT_AREA_HEIGHT_WITH_PADDING + \
                        THUMBNAIL_GRID_CONTENT_HEIGHT + \
                        ITEM_PADDING_VERTICAL_BOTTOM

class FrameThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame_data_list: list[list[str]] = [] # List of color lists (hex strings)
        self.current_playback_idx = -1
        self.current_edit_idx = -1 # To draw a distinct border for the edit frame if not selected

    def set_frame_data_list(self, data_list: list[list[str]]):
        self.frame_data_list = data_list

    def set_current_playback_idx(self, idx: int):
        self.current_playback_idx = idx
    
    def set_current_edit_idx(self, idx: int):
        self.current_edit_idx = idx

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        rect = option.rect # This is the total QListWidgetItem rect

        from PyQt6.QtWidgets import QStyle # Ensure QStyle is available

        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_current_edit_frame = (index.row() == self.current_edit_idx)
        is_playback_frame = (index.row() == self.current_playback_idx)

        # Background
        bg_color = option.palette.base().color()
        if is_selected:
            bg_color = option.palette.highlight().color()
        elif is_playback_frame:
            bg_color = option.palette.base().color().darker(130)
            if bg_color == option.palette.base().color(): bg_color = QColor("#103020") 
        elif is_current_edit_frame:
             bg_color = option.palette.base().color().lighter(115)
             if bg_color == option.palette.base().color(): bg_color = QColor("#383838")
        painter.fillRect(rect, bg_color)
        
        pen_color = option.palette.highlightedText().color() if is_selected else option.palette.text().color()
        painter.setPen(pen_color)

        # --- Text Drawing ---
        frame_number_text = f"Frame {index.row() + 1}"
        # Use constants for padding
        text_y_start = rect.y() + ITEM_PADDING_VERTICAL_TOP_FOR_TEXT
        # Calculate actual text height required by font
        font_metrics = painter.fontMetrics()
        text_display_height = font_metrics.height() 
        
        text_rect = QRect(
            rect.x() + ITEM_PADDING_HORIZONTAL, 
            text_y_start, 
            rect.width() - (2 * ITEM_PADDING_HORIZONTAL), 
            text_display_height
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, frame_number_text) # VCenter text in its allocated rect

        # --- Thumbnail Area Calculation & Drawing ---
        # Y position for the top of the thumbnail grid
        thumbnail_area_y_start = text_rect.bottom() + ITEM_PADDING_VERTICAL_BETWEEN_TEXT_THUMB
        
        # Calculate available height for the thumbnail grid itself
        # available_height_for_grid = rect.height() - thumbnail_area_y_start - ITEM_PADDING_VERTICAL_BOTTOM
        # This was used for vertical centering, but fixed positioning is better given fixed item height.

        # Horizontal offset for centering the grid content within the item's width
        thumb_x_offset_within_item = (rect.width() - THUMBNAIL_GRID_CONTENT_WIDTH) // 2
        
        # Absolute X start for the first pad in the grid
        pad_grid_abs_x_start = rect.x() + thumb_x_offset_within_item

        frame_colors = None
        if 0 <= index.row() < len(self.frame_data_list):
            frame_colors = self.frame_data_list[index.row()]

        if frame_colors and len(frame_colors) == THUMBNAIL_ROWS * THUMBNAIL_COLS:
            for r_idx in range(THUMBNAIL_ROWS):
                for c_idx in range(THUMBNAIL_COLS):
                    pad_idx = r_idx * THUMBNAIL_COLS + c_idx
                    color_str = frame_colors[pad_idx]
                    q_color = QColor(color_str if color_str else "#000000")
                    if not q_color.isValid(): q_color = QColor("#1C1C1C")

                    pad_x = pad_grid_abs_x_start + c_idx * (THUMBNAIL_PAD_SIZE + THUMBNAIL_PAD_SPACING)
                    # Y position for the current pad
                    pad_y = thumbnail_area_y_start + r_idx * (THUMBNAIL_PAD_SIZE + THUMBNAIL_PAD_SPACING)
                    
                    # Check if pad_y + THUMBNAIL_PAD_SIZE exceeds item bottom boundary (minus bottom padding)
                    # This is a defensive check; ideally THUMBNAIL_ITEM_HEIGHT is calculated correctly.
                    if pad_y + THUMBNAIL_PAD_SIZE <= rect.bottom() - ITEM_PADDING_VERTICAL_BOTTOM:
                        painter.fillRect(pad_x, pad_y, THUMBNAIL_PAD_SIZE, THUMBNAIL_PAD_SIZE, QBrush(q_color))
                    # else:
                        # print(f"Warning: Pad drawing for item {index.row()} would exceed item boundary.")

        else: # No data or malformed data
            no_data_rect_y_start = thumbnail_area_y_start
            no_data_rect_height = THUMBNAIL_GRID_CONTENT_HEIGHT # Use the calculated grid content height
            
            no_data_rect = QRect(
                rect.x() + ITEM_PADDING_HORIZONTAL, 
                no_data_rect_y_start, 
                rect.width() - (2 * ITEM_PADDING_HORIZONTAL), 
                no_data_rect_height
            )
            # Ensure "No Data" text fits within the available space for the grid
            if no_data_rect.height() > 0 and no_data_rect.width() > 0 :
                 painter.drawText(no_data_rect, Qt.AlignmentFlag.AlignCenter, "No Data")

        # Border for playback/edit frame if not selected
        if not is_selected:
            if is_playback_frame:
                painter.setPen(QPen(QColor("lime"), 1.5))
                painter.drawRect(rect.adjusted(0,0,-1,-1))
            elif is_current_edit_frame:
                painter.setPen(QPen(QColor("gold"), 1.5))
                painter.drawRect(rect.adjusted(0,0,-1,-1))
        
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(THUMBNAIL_ITEM_WIDTH, THUMBNAIL_ITEM_HEIGHT)


class SequenceTimelineWidget(QWidget):
    # Signals for actions, mostly triggered by context menu or potentially hotkeys handled by this widget
    frame_selected = pyqtSignal(int) # Emits single selected index, or first of multi-selection
    
    # Context Menu / Action Signals (generic, MainWindow handles selection)
    add_frame_action_triggered = pyqtSignal(str) # "snapshot" or "blank"
    copy_frames_action_triggered = pyqtSignal()
    cut_frames_action_triggered = pyqtSignal()
    paste_frames_action_triggered = pyqtSignal()
    duplicate_selected_action_triggered = pyqtSignal() # Generic duplicate
    delete_selected_action_triggered = pyqtSignal()    # Generic delete
    select_all_action_triggered = pyqtSignal()

    # Specific context menu actions that might need an index (e.g., insert before/after this specific item)
    # These might be simplified if all actions become generic and rely on MainWindow to get selection
    insert_blank_frame_before_action_triggered = pyqtSignal(int) # index of item to insert before
    insert_blank_frame_after_action_triggered = pyqtSignal(int)  # index of item to insert after


    def __init__(self, parent=None):
        super().__init__(parent)

        self._all_frames_data: list[list[str]] = [] # Cache of color data for thumbnails

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.frame_list_widget = QListWidget()
        self.frame_list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list_widget.setWrapping(True) # Allow items to wrap to next line
        self.frame_list_widget.setResizeMode(QListWidget.ResizeMode.Adjust) # Adjust layout on resize
        self.frame_list_widget.setMovement(QListWidget.Movement.Static) # Items are not draggable
        self.frame_list_widget.setUniformItemSizes(True) # Performance boost if all items are same size
        self.frame_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # Enable multi-select

        self.thumbnail_delegate = FrameThumbnailDelegate(self.frame_list_widget)
        self.frame_list_widget.setItemDelegate(self.thumbnail_delegate)

        self.frame_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #444;
                background-color: #282828; /* Dark background for the list widget itself */
            }
            /* Item styling is mostly handled by the delegate now */
        """)
        
        # This signal is good for single selections or primary selection changes
        self.frame_list_widget.currentItemChanged.connect(self._on_current_item_changed)
        # selectionChanged is better for knowing about multi-select operations
        self.frame_list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)

        self.frame_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frame_list_widget.customContextMenuRequested.connect(self.show_timeline_context_menu)

        layout.addWidget(self.frame_list_widget)
        
        # Set a reasonable initial height
        self.setMinimumHeight(THUMBNAIL_ITEM_HEIGHT + 10) # Min height for at least one row
        # Preferred starting height for 2 rows
        # self.setFixedHeight( (THUMBNAIL_ITEM_HEIGHT * 2) + 20 if THUMBNAIL_ITEM_HEIGHT > 0 else 100)

# In class SequenceTimelineWidget(QWidget):
    # ... (other methods like set_wrapping_enabled) ...

    def update_single_frame_thumbnail_data(self, frame_index: int, new_frame_colors: list[str]):
        """
        Updates the color data for a single frame in the cache and schedules
        only that item for repaint in the QListWidget.
        """
        if not (0 <= frame_index < len(self._all_frames_data) and
                0 <= frame_index < self.frame_list_widget.count()):
            # print(f"Timeline WARNING: update_single_frame_thumbnail_data - index {frame_index} out of bounds. Data cache size: {len(self._all_frames_data)}, ListWidget count: {self.frame_list_widget.count()}")
            return

        if not isinstance(new_frame_colors, list) or len(new_frame_colors) != (THUMBNAIL_ROWS * THUMBNAIL_COLS):
            # print(f"Timeline WARNING: update_single_frame_thumbnail_data - Invalid new_frame_colors for index {frame_index}.")
            return

        # Update the cached data that the delegate uses
        self._all_frames_data[frame_index] = new_frame_colors

        # Get the QModelIndex for the specific item in the QListWidget's model
        # QListWidget uses a simple list model, so row is frame_index, column is 0.
        model_idx = self.frame_list_widget.model().index(frame_index, 0)

        if model_idx.isValid():
            # Tell the QListWidget to update (repaint) the view for this specific model index.
            # This will cause the delegate's paint method to be called for just this item.
            self.frame_list_widget.update(model_idx)
            # print(f"Timeline DEBUG: Requested update for thumbnail at model_idx (row {model_idx.row()}) due to single frame data change.") # Optional
        # else:
            # print(f"Timeline WARNING: update_single_frame_thumbnail_data - Could not get valid QModelIndex for frame_index {frame_index}.")



    def _on_current_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            index = self.frame_list_widget.row(current)
            if len(self.frame_list_widget.selectedItems()) <= 1:
                 self.frame_selected.emit(index)

    def _on_item_selection_changed(self):
        selected_items = self.frame_list_widget.selectedItems()
        if selected_items:
            first_selected_index = self.frame_list_widget.row(selected_items[0])
            # print(f"DEBUG TimelineWidget: _on_item_selection_changed. Emitting frame_selected({first_selected_index})") # ADD THIS
            self.frame_selected.emit(first_selected_index)
        else:
            self.frame_selected.emit(-1) # No items selected

    def get_selected_item_indices(self) -> list[int]:
        """Returns a list of integer indices of all currently selected items."""
        selected_indices = []
        for item in self.frame_list_widget.selectedItems():
            selected_indices.append(self.frame_list_widget.row(item))
        return sorted(list(set(selected_indices))) # Return sorted unique indices

    def select_items_by_indices(self, indices_to_select: list[int]):
        """Programmatically selects items at the given indices."""
        self.frame_list_widget.blockSignals(True)
        self.frame_list_widget.clearSelection() # Clear previous selection first
        
        last_selected_item = None
        for index in indices_to_select:
            if 0 <= index < self.frame_list_widget.count():
                item = self.frame_list_widget.item(index)
                if item:
                    item.setSelected(True)
                    last_selected_item = item
        
        if last_selected_item: # Ensure the last selected item is current and visible
            self.frame_list_widget.setCurrentItem(last_selected_item)
            self.frame_list_widget.scrollToItem(last_selected_item, QAbstractItemView.ScrollHint.EnsureVisible)

        self.frame_list_widget.blockSignals(False)
        self._on_item_selection_changed() # Manually trigger to update state if needed

    def keyPressEvent(self, event):
        """Handle key presses for actions like Select All."""
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.select_all_action_triggered.emit()
            event.accept()
        # Potentially handle Delete key here as well if MainWindow doesn't catch it globally
        # elif event.key() == Qt.Key.Key_Delete:
        #     if self.frame_list_widget.selectedItems():
        #         self.delete_selected_action_triggered.emit()
        #         event.accept()
        else:
            super().keyPressEvent(event)


    def show_timeline_context_menu(self, position: QPoint):
        menu = QMenu(self)
        
        # Get the item under the cursor, if any
        item_at_pos = self.frame_list_widget.itemAt(position)
        right_clicked_item_row = self.frame_list_widget.row(item_at_pos) if item_at_pos else -1

        selected_indices = self.get_selected_item_indices()
        num_selected = len(selected_indices)

        # --- Add Frame Actions (Always available) ---
        add_blank_action = QAction(ICON_ADD_BLANK + " Add Blank Frame", self)
        add_blank_action.setStatusTip(f"Add Blank Frame (Ctrl+Shift+B). Inserts after selection or at end.")
        add_blank_action.triggered.connect(lambda: self.add_frame_action_triggered.emit("blank"))
        menu.addAction(add_blank_action)
        menu.addSeparator()

        # --- Clipboard Actions ---
        # Enabled state will be handled by MainWindow's QActions based on selection and clipboard content
        copy_action = QAction(ICON_COPY + " Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy) # Informative
        copy_action.setStatusTip(f"Copy selected frame(s) to clipboard (Ctrl+C).")
        copy_action.triggered.connect(self.copy_frames_action_triggered)
        copy_action.setEnabled(num_selected > 0)
        menu.addAction(copy_action)

        cut_action = QAction(ICON_CUT + " Cut", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut) # Informative
        cut_action.setStatusTip(f"Cut selected frame(s) to clipboard (Ctrl+X).")
        cut_action.triggered.connect(self.cut_frames_action_triggered)
        cut_action.setEnabled(num_selected > 0)
        menu.addAction(cut_action)

        paste_action = QAction(ICON_DUPLICATE + " Paste", self) # Using ICON_DUPLICATE for paste icon
        paste_action.setShortcut(QKeySequence.StandardKey.Paste) # Informative
        paste_action.setStatusTip(f"Paste frame(s) from clipboard (Ctrl+V). Inserts after selection or at end.")
        paste_action.triggered.connect(self.paste_frames_action_triggered)
        # Paste enabled state depends on MainWindow's clipboard content, not managed here directly
        # For the menu item, we can assume if it's shown, MainWindow's QAction will handle actual possibility.
        # Or, this QAction could be enabled/disabled by MainWindow if TimelineWidget exposes a way.
        # For now, let it always be triggerable.
        menu.addAction(paste_action)
        menu.addSeparator()

        # --- Selection-dependent Actions ---
        duplicate_action = QAction(ICON_DUPLICATE + " Duplicate", self)
        duplicate_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_D)) # Informative
        duplicate_action.setStatusTip(f"Duplicate selected frame(s) (Ctrl+D).")
        duplicate_action.triggered.connect(self.duplicate_selected_action_triggered)
        duplicate_action.setEnabled(num_selected > 0)
        menu.addAction(duplicate_action)

        delete_action = QAction(ICON_DELETE + " Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete) # Informative
        delete_action.setStatusTip(f"Delete selected frame(s) (Delete).")
        delete_action.triggered.connect(self.delete_selected_action_triggered)
        delete_action.setEnabled(num_selected > 0)
        menu.addAction(delete_action)

        # --- Insert Blank Specific (if a single item was right-clicked) ---
        if item_at_pos and num_selected <= 1: # Only show if right-click was on an item, and it's the only one selected or focus
            menu.addSeparator()
            insert_blank_before = QAction(ICON_ADD_BLANK + " Insert Blank Before This", self)
            insert_blank_before.setStatusTip(f"Insert a new blank frame before Frame {right_clicked_item_row + 1}.")
            insert_blank_before.triggered.connect(lambda: self.insert_blank_frame_before_action_triggered.emit(right_clicked_item_row))
            menu.addAction(insert_blank_before)

            insert_blank_after = QAction(ICON_ADD_BLANK + " Insert Blank After This", self)
            insert_blank_after.setStatusTip(f"Insert a new blank frame after Frame {right_clicked_item_row + 1}.")
            insert_blank_after.triggered.connect(lambda: self.insert_blank_frame_after_action_triggered.emit(right_clicked_item_row))
            menu.addAction(insert_blank_after)
        
        menu.addSeparator()
        select_all_qaction = QAction("Select All", self)
        select_all_qaction.setShortcut(QKeySequence.StandardKey.SelectAll) # Informative
        select_all_qaction.setStatusTip(f"Select all frames (Ctrl+A).")
        select_all_qaction.triggered.connect(self.select_all_action_triggered)
        select_all_qaction.setEnabled(self.frame_list_widget.count() > 0)
        menu.addAction(select_all_qaction)

        menu.exec(self.frame_list_widget.mapToGlobal(position))

    def update_frames_display(self, all_frames_color_data: list[list[str]], 
                              current_edit_idx: int = -1, 
                              current_playback_idx: int = -1):
        self.frame_list_widget.blockSignals(True)

        self._all_frames_data = all_frames_color_data # Cache for the delegate
        self.thumbnail_delegate.set_frame_data_list(self._all_frames_data)
        self.thumbnail_delegate.set_current_playback_idx(current_playback_idx)
        self.thumbnail_delegate.set_current_edit_idx(current_edit_idx) # Pass edit index to delegate

        # Preserve selection if possible
        previously_selected_indices = self.get_selected_item_indices()

        self.frame_list_widget.clear() # Clears items and selection

        for i in range(len(all_frames_color_data)):
            item = QListWidgetItem() # No need to set text, delegate handles it
            # item.setSizeHint(QSize(THUMBNAIL_ITEM_WIDTH, THUMBNAIL_ITEM_HEIGHT)) # Delegate handles sizeHint
            self.frame_list_widget.addItem(item)

        # Restore selection
        # If current_edit_idx is valid and was part of old selection, prioritize it for focus.
        # Otherwise, try to restore old selection.
        restored_selection_for_focus = False
        if previously_selected_indices:
            valid_previous_selection = [idx for idx in previously_selected_indices if 0 <= idx < len(all_frames_color_data)]
            if valid_previous_selection:
                self.select_items_by_indices(valid_previous_selection) # This will also handle setCurrentItem
                restored_selection_for_focus = True

        # If no previous selection was restored, or if current_edit_idx is now different, set current item
        if not restored_selection_for_focus or \
           (0 <= current_edit_idx < self.frame_list_widget.count() and current_edit_idx not in previously_selected_indices) :
            if 0 <= current_edit_idx < self.frame_list_widget.count():
                current_item_to_set = self.frame_list_widget.item(current_edit_idx)
                if current_item_to_set:
                    # If it wasn't part of a multi-selection restore, select it singly.
                    if not current_item_to_set.isSelected():
                        self.frame_list_widget.clearSelection() # Clear if we are focusing a new single item
                        current_item_to_set.setSelected(True)
                    self.frame_list_widget.setCurrentItem(current_item_to_set) # Ensure it's the "current" for keyboard nav
                    self.frame_list_widget.scrollToItem(current_item_to_set, QAbstractItemView.ScrollHint.EnsureVisible)
            elif self.frame_list_widget.count() > 0 and not restored_selection_for_focus: # Fallback to first item if no edit_idx and no restored selection
                self.frame_list_widget.setCurrentRow(0) # Selects and sets current
                self.frame_list_widget.scrollToItem(self.frame_list_widget.item(0), QAbstractItemView.ScrollHint.EnsureVisible)


        self.frame_list_widget.blockSignals(False)
        # QListWidget usually updates itself, but an explicit update() can sometimes help force repaint of delegate items.
        self.frame_list_widget.update() 

    def set_selected_frame_by_index(self, index: int): # This might be deprecated if multi-select is primary
        """Primarily for setting a single selected frame, e.g., when model's edit index changes."""
        self.frame_list_widget.blockSignals(True)
        self.frame_list_widget.clearSelection() # Clear multi-selection first
        if 0 <= index < self.frame_list_widget.count():
            item = self.frame_list_widget.item(index)
            if item:
                item.setSelected(True)
                self.frame_list_widget.setCurrentItem(item) # Also make it the "current" item
                self.frame_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
        # No else needed to emit frame_selected(-1) because clearSelection() above should trigger _on_item_selection_changed
        self.frame_list_widget.blockSignals(False)
        if self.frame_list_widget.selectedItems():
             self._on_item_selection_changed() # Manually trigger if selection changed
        else: # If selection was cleared and index was invalid
             self.frame_selected.emit(-1)


    def get_current_single_selected_frame_index(self) -> int: # Might be deprecated
        """Returns the index of the 'current' item, often the first or focus of a selection."""
        current_item = self.frame_list_widget.currentItem()
        if current_item:
            return self.frame_list_widget.row(current_item)
        return -1

    def set_wrapping_enabled(self, enabled: bool):
        self.frame_list_widget.setWrapping(enabled)
        # self.frame_list_widget.updateGeometries() # May not be necessary, Adjust resizeMode handles it