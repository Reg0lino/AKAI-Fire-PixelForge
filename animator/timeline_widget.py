# AKAI_Fire_RGB_Controller/animator/timeline_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                             QAbstractItemView, QMenu, QStyledItemDelegate, QApplication,
                             QStyleOptionViewItem) # Removed QStyle as it's not directly used now
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QRect, QModelIndex
from PyQt6.QtGui import QAction, QPainter, QColor, QBrush, QPen

THUMBNAIL_PAD_SIZE = 3
THUMBNAIL_PAD_SPACING = 1
THUMBNAIL_COLS = 16
THUMBNAIL_ROWS = 4
THUMBNAIL_ITEM_WIDTH = (THUMBNAIL_COLS * THUMBNAIL_PAD_SIZE) + ((THUMBNAIL_COLS -1) * THUMBNAIL_PAD_SPACING) + 10
THUMBNAIL_ITEM_HEIGHT = (THUMBNAIL_ROWS * THUMBNAIL_PAD_SIZE) + ((THUMBNAIL_ROWS -1) * THUMBNAIL_PAD_SPACING) + 20

class FrameThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame_data_list = []
        self.current_playback_idx = -1

    def set_frame_data_list(self, data_list):
        self.frame_data_list = data_list

    def set_current_playback_idx(self, idx: int):
        self.current_playback_idx = idx

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        rect = option.rect

        is_selected = False
        # option.widget should be the QListWidget instance. Get the QListWidgetItem from it.
        if option.widget and isinstance(option.widget, QListWidget):
            list_widget_item = option.widget.item(index.row()) # Get the QListWidgetItem
            if list_widget_item:
                is_selected = list_widget_item.isSelected() # CORRECTED: Call isSelected() on the item

        is_playback_frame = (index.row() == self.current_playback_idx)

        # Background
        if is_selected:
            painter.fillRect(rect, option.palette.highlight())
            pen_color = option.palette.highlightedText().color()
        elif is_playback_frame:
            playback_highlight_color = option.palette.base().color().lighter(120)
            if playback_highlight_color == option.palette.base().color():
                playback_highlight_color = QColor("#40404F") # A distinct dark blue/purple
            painter.fillRect(rect, playback_highlight_color)
            pen_color = option.palette.text().color()
        else:
            painter.fillRect(rect, option.palette.base())
            pen_color = option.palette.text().color()

        painter.setPen(pen_color)

        frame_number_text = f"Frame {index.row() + 1}"
        text_rect = QRect(rect.x() + 5, rect.y() + 2, rect.width() - 10, 15)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, frame_number_text)

        thumbnail_area_y_offset = text_rect.bottom() + 3
        thumb_content_width = (THUMBNAIL_COLS * THUMBNAIL_PAD_SIZE) + ((THUMBNAIL_COLS - 1) * THUMBNAIL_PAD_SPACING)
        thumb_x_offset = (rect.width() - thumb_content_width) // 2

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

                    pad_x = rect.x() + thumb_x_offset + c_idx * (THUMBNAIL_PAD_SIZE + THUMBNAIL_PAD_SPACING)
                    pad_y = thumbnail_area_y_offset + r_idx * (THUMBNAIL_PAD_SIZE + THUMBNAIL_PAD_SPACING)

                    painter.fillRect(pad_x, pad_y, THUMBNAIL_PAD_SIZE, THUMBNAIL_PAD_SIZE, QBrush(q_color))
        else:
            no_data_rect_height = (THUMBNAIL_ROWS * THUMBNAIL_PAD_SIZE) + ((THUMBNAIL_ROWS - 1) * THUMBNAIL_PAD_SPACING)
            no_data_rect = QRect(rect.x() + 5, thumbnail_area_y_offset, rect.width() - 10, no_data_rect_height)
            painter.drawText(no_data_rect, Qt.AlignmentFlag.AlignCenter, "No Data")

        if is_playback_frame and not is_selected: # Draw border only if not selected (selection has its own highlight)
            painter.setPen(QPen(QColor("yellow"), 1))
            painter.drawRect(rect.adjusted(0,0,-1,-1)) # Draw inside the item rect

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(THUMBNAIL_ITEM_WIDTH, THUMBNAIL_ITEM_HEIGHT)


class SequenceTimelineWidget(QWidget):
    frame_selected = pyqtSignal(int)
    add_frame_action_triggered = pyqtSignal(str)
    duplicate_frame_action_triggered = pyqtSignal(int)
    delete_frame_action_triggered = pyqtSignal(int)
    insert_blank_frame_before_action_triggered = pyqtSignal(int)
    insert_blank_frame_after_action_triggered = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_selected_frame_index = -1
        self._all_frames_data = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.frame_list_widget = QListWidget()
        self.frame_list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list_widget.setWrapping(True)
        self.frame_list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.frame_list_widget.setMovement(QListWidget.Movement.Static)
        self.frame_list_widget.setUniformItemSizes(True)

        self.thumbnail_delegate = FrameThumbnailDelegate(self.frame_list_widget)
        self.frame_list_widget.setItemDelegate(self.thumbnail_delegate)

        self.frame_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #444;
                background-color: #282828;
            }
        """)
        self.frame_list_widget.currentItemChanged.connect(self._on_current_item_changed)
        self.frame_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frame_list_widget.customContextMenuRequested.connect(self.show_timeline_context_menu)

        layout.addWidget(self.frame_list_widget)
        # Set a reasonable initial height, allowing for 1-2 rows of thumbnails
        self.setMinimumHeight(THUMBNAIL_ITEM_HEIGHT + 10) 
        # If you want it to grow, don't set a fixed height, or use a layout that allows growth.
        # For now, let's set a preferred starting height.
        # self.setFixedHeight( (THUMBNAIL_ITEM_HEIGHT * 2) + 20 if THUMBNAIL_ITEM_HEIGHT > 0 else 100)


    def _on_current_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            index = self.frame_list_widget.row(current)
            if index != self.current_selected_frame_index:
                self.current_selected_frame_index = index
                self.frame_selected.emit(index)
        else:
            if self.current_selected_frame_index != -1:
                self.current_selected_frame_index = -1
                self.frame_selected.emit(-1)

    def show_timeline_context_menu(self, position: QPoint):
        menu = QMenu(self)
        item_at_pos = self.frame_list_widget.itemAt(position)
        selected_index = self.frame_list_widget.row(item_at_pos) if item_at_pos else -1

        add_snapshot_action = QAction("➕ Add Snapshot Frame", self)
        add_snapshot_action.triggered.connect(lambda: self.add_frame_action_triggered.emit("snapshot"))
        menu.addAction(add_snapshot_action)
        add_blank_action = QAction("➕ Add Blank Frame", self)
        add_blank_action.triggered.connect(lambda: self.add_frame_action_triggered.emit("blank"))
        menu.addAction(add_blank_action)
        menu.addSeparator()
        if item_at_pos and selected_index != -1:
            duplicate_action = QAction("📋 Duplicate Frame", self)
            duplicate_action.triggered.connect(lambda: self.duplicate_frame_action_triggered.emit(selected_index))
            menu.addAction(duplicate_action)
            menu.addSeparator()
            insert_blank_before = QAction("➕ Insert Blank Before", self)
            insert_blank_before.triggered.connect(lambda: self.insert_blank_frame_before_action_triggered.emit(selected_index))
            menu.addAction(insert_blank_before)
            insert_blank_after = QAction("➕ Insert Blank After", self)
            insert_blank_after.triggered.connect(lambda: self.insert_blank_frame_after_action_triggered.emit(selected_index + 1))
            menu.addAction(insert_blank_after)
            menu.addSeparator()
            delete_action = QAction("🗑️ Delete Frame", self)
            delete_action.triggered.connect(lambda: self.delete_frame_action_triggered.emit(selected_index))
            menu.addAction(delete_action)
        menu.exec(self.frame_list_widget.mapToGlobal(position))

    def update_frames_display(self, all_frames_color_data: list, current_edit_idx: int = -1, current_playback_idx: int = -1):
        self.frame_list_widget.blockSignals(True)

        self._all_frames_data = all_frames_color_data
        self.thumbnail_delegate.set_frame_data_list(self._all_frames_data)
        self.thumbnail_delegate.set_current_playback_idx(current_playback_idx)

        self.frame_list_widget.clear()

        for i in range(len(all_frames_color_data)):
            item = QListWidgetItem()
            self.frame_list_widget.addItem(item)

        if 0 <= current_edit_idx < self.frame_list_widget.count():
            self.frame_list_widget.setCurrentRow(current_edit_idx)
            item_to_scroll = self.frame_list_widget.item(current_edit_idx)
            if item_to_scroll:
                self.frame_list_widget.scrollToItem(item_to_scroll, QAbstractItemView.ScrollHint.EnsureVisible)
        elif self.frame_list_widget.count() > 0 :
             self.frame_list_widget.setCurrentRow(0)

        self.frame_list_widget.blockSignals(False)
        self.frame_list_widget.update() # Request repaint for all items

    def set_selected_frame_by_index(self, index: int):
        self.frame_list_widget.blockSignals(True)
        if 0 <= index < self.frame_list_widget.count():
            if self.frame_list_widget.currentRow() != index:
                self.frame_list_widget.setCurrentRow(index)
        elif self.frame_list_widget.count() == 0:
             if self.current_selected_frame_index != -1:
                 self.frame_list_widget.clearSelection()
                 self.current_selected_frame_index = -1
                 self.frame_selected.emit(-1)
        self.frame_list_widget.blockSignals(False)

    def get_selected_frame_index(self) -> int:
        return self.current_selected_frame_index

    def set_wrapping_enabled(self, enabled: bool):
        self.frame_list_widget.setWrapping(enabled)
        self.frame_list_widget.updateGeometries()