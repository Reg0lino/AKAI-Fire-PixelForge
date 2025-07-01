### START OF FILE monitor_view_widget.py ###
# AKAI_Fire_RGB_Controller/gui/monitor_view_widget.py
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent, QCursor
from enum import Enum
import math

MONITOR_AREA_PADDING = 10
DEFAULT_MONITOR_BG_COLOR = QColor(55, 55, 60)
ACTIVE_MONITOR_BORDER_COLOR = QColor(100, 150, 255)
SELECTION_RECT_COLOR = QColor(0, 180, 255, 60)
SELECTION_RECT_BORDER_COLOR = QColor(0, 220, 255, 120)
HANDLE_SIZE = 8
MIN_SELECTION_LOGICAL_SIZE = 20
MIN_SELECTION_PERCENTAGE_DIM = 0.001


class ResizeHandle(Enum):
    NONE = 0
    TOP_LEFT = 1
    TOP_MIDDLE = 2
    TOP_RIGHT = 3
    MIDDLE_LEFT = 4
    MIDDLE_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_MIDDLE = 7
    BOTTOM_RIGHT = 8
    BODY = 9


class MonitorViewWidget(QWidget):
    region_selection_changed = pyqtSignal(int, dict)
    monitor_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.all_monitors_original_info: list[dict] = []
        self.target_monitor_mss_id: int | None = None
        self.target_monitor_scaled_rect = QRect()
        self.selection_rect_scaled = QRectF()
        self._current_sample_box_logical_x = 0.0
        self._current_sample_box_logical_y = 0.0
        self._current_sample_box_logical_width = 128.0
        self._current_sample_box_logical_height = 128.0
        self.current_scale_factor = 1.0
        self._active_interaction = ResizeHandle.NONE
        self._drag_start_mouse_pos = QPointF()
        self._resize_start_rect_scaled = QRectF()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def cycle_to_next_monitor(self):
        """Cycles to the next available monitor and updates the view."""
        if not self.all_monitors_original_info or len(self.all_monitors_original_info) <= 1:
            return  # Nothing to cycle to
        current_idx = -1
        if self.target_monitor_mss_id is not None:
            for i, monitor in enumerate(self.all_monitors_original_info):
                if monitor['id'] == self.target_monitor_mss_id:
                    current_idx = i
                    break
        next_idx = (current_idx + 1) % len(self.all_monitors_original_info)
        new_target_id = self.all_monitors_original_info[next_idx]['id']
        # This will set the new monitor and recalculate everything
        self.set_target_monitor_and_update_view(new_target_id)
        # This signal tells the manager about the change so it can update the sampling thread
        self._emit_selection_changed()

    def set_monitors_data(self, monitors_data_from_mss: list[dict], target_mss_id_to_focus: int | None = None):
        self.all_monitors_original_info = monitors_data_from_mss
        if not self.all_monitors_original_info:
            self.target_monitor_mss_id = None
            self._reset_scaled_rects()
            self.update()
            return
        valid_target_id = target_mss_id_to_focus
        if target_mss_id_to_focus is None or not any(m['id'] == target_mss_id_to_focus for m in self.all_monitors_original_info):
            primaries = [
                m for m in self.all_monitors_original_info if m['left'] == 0 and m['top'] == 0]
            valid_target_id = primaries[0]['id'] if primaries else self.all_monitors_original_info[0]['id']
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == valid_target_id), None)
        if target_mon_info:
            self._current_sample_box_logical_width = target_mon_info['width'] * 0.2
            self._current_sample_box_logical_height = target_mon_info['height'] * 0.2
            self._current_sample_box_logical_x = target_mon_info['width'] * 0.4
            self._current_sample_box_logical_y = target_mon_info['height'] * 0.4
        self.set_target_monitor_and_update_view(valid_target_id)

    def _reset_scaled_rects(self):
        self.target_monitor_scaled_rect = QRect()
        self.selection_rect_scaled = QRectF()
        self.current_scale_factor = 1.0

    def set_target_monitor_and_update_view(self, target_mss_id: int):
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == target_mss_id), None)
        if not target_mon_info:
            if self.all_monitors_original_info:
                self.target_monitor_mss_id = self.all_monitors_original_info[0]['id']
            else:
                self.target_monitor_mss_id = None
                self._reset_scaled_rects()
        else:
            self.target_monitor_mss_id = target_mss_id
        self._recalculate_scales_and_selection_rect()
        self.update()

    def _recalculate_scales_and_selection_rect(self):
        self.target_monitor_scaled_rect = QRect()
        self.selection_rect_scaled = QRectF()
        if self.target_monitor_mss_id is None or not self.all_monitors_original_info:
            return
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info:
            return
        widget_w = self.width() - 2 * MONITOR_AREA_PADDING
        widget_h = self.height() - 2 * MONITOR_AREA_PADDING
        if widget_w <= 0 or widget_h <= 0:
            return
        mon_orig_w, mon_orig_h = target_mon_info['width'], target_mon_info['height']
        if mon_orig_w == 0 or mon_orig_h == 0:
            return
        scale_x = widget_w / mon_orig_w
        scale_y = widget_h / mon_orig_h
        self.current_scale_factor = min(scale_x, scale_y)
        if self.current_scale_factor <= 0:
            self.current_scale_factor = 1.0
        scaled_mon_w = int(mon_orig_w * self.current_scale_factor)
        scaled_mon_h = int(mon_orig_h * self.current_scale_factor)
        offset_x = MONITOR_AREA_PADDING + (widget_w - scaled_mon_w) // 2
        offset_y = MONITOR_AREA_PADDING + (widget_h - scaled_mon_h) // 2
        self.target_monitor_scaled_rect = QRect(
            offset_x, offset_y, scaled_mon_w, scaled_mon_h)
        scaled_sel_x = self.target_monitor_scaled_rect.left(
        ) + (self._current_sample_box_logical_x * self.current_scale_factor)
        scaled_sel_y = self.target_monitor_scaled_rect.top(
        ) + (self._current_sample_box_logical_y * self.current_scale_factor)
        scaled_sel_w = self._current_sample_box_logical_width * self.current_scale_factor
        scaled_sel_h = self._current_sample_box_logical_height * self.current_scale_factor
        self.selection_rect_scaled = QRectF(scaled_sel_x, scaled_sel_y, max(
            1.0, scaled_sel_w), max(1.0, scaled_sel_h))
        self._clamp_selection_rect_to_current_monitor_view()

    def set_current_selection_from_params(self, target_mss_id: int, region_rect_percentage: dict):
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == target_mss_id), None)
        if not target_mon_info:
            print(
                f"MonitorViewWidget Error: Cannot set selection, unknown target_mss_id: {target_mss_id}")
            return
        self.target_monitor_mss_id = target_mss_id
        mon_orig_w = float(target_mon_info.get('width', 1))
        mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1))
        mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        perc_x = region_rect_percentage.get('x', 0.4)
        perc_y = region_rect_percentage.get('y', 0.4)
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM,
                    region_rect_percentage.get('width', 0.2))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM,
                    region_rect_percentage.get('height', 0.2))
        self._current_sample_box_logical_x = perc_x * mon_orig_w
        self._current_sample_box_logical_y = perc_y * mon_orig_h
        self._current_sample_box_logical_width = perc_w * mon_orig_w
        self._current_sample_box_logical_height = perc_h * mon_orig_h
        self._current_sample_box_logical_width = max(
            MIN_SELECTION_LOGICAL_SIZE, self._current_sample_box_logical_width)
        self._current_sample_box_logical_height = max(
            MIN_SELECTION_LOGICAL_SIZE, self._current_sample_box_logical_height)
        self._recalculate_scales_and_selection_rect()
        self.update()

    def _update_logical_state_from_scaled_rect(self):
        if self.current_scale_factor <= 0 or self.selection_rect_scaled.isNull() or self.target_monitor_scaled_rect.isNull():
            return
        logical_x = (self.selection_rect_scaled.left(
        ) - self.target_monitor_scaled_rect.left()) / self.current_scale_factor
        logical_y = (self.selection_rect_scaled.top(
        ) - self.target_monitor_scaled_rect.top()) / self.current_scale_factor
        logical_w = self.selection_rect_scaled.width() / self.current_scale_factor
        logical_h = self.selection_rect_scaled.height() / self.current_scale_factor
        self._current_sample_box_logical_x = logical_x
        self._current_sample_box_logical_y = logical_y
        self._current_sample_box_logical_width = max(
            MIN_SELECTION_LOGICAL_SIZE, logical_w)
        self._current_sample_box_logical_height = max(
            MIN_SELECTION_LOGICAL_SIZE, logical_h)

    def _emit_selection_changed(self):
        if self.target_monitor_mss_id is None or not self.all_monitors_original_info or self.current_scale_factor <= 0:
            return
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info:
            return
        mon_orig_w = float(target_mon_info.get('width', 1))
        mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1))
        mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        perc_x = self._current_sample_box_logical_x / mon_orig_w
        perc_y = self._current_sample_box_logical_y / mon_orig_h
        perc_w = self._current_sample_box_logical_width / mon_orig_w
        perc_h = self._current_sample_box_logical_height / mon_orig_h
        perc_x = max(0.0, min(perc_x, 1.0))
        perc_y = max(0.0, min(perc_y, 1.0))
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM, min(
            perc_w, 1.0 - perc_x if perc_x < 1.0 else 0.0))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM, min(
            perc_h, 1.0 - perc_y if perc_y < 1.0 else 0.0))
        if perc_x + perc_w > 1.0:
            perc_w = 1.0 - perc_x
        if perc_y + perc_h > 1.0:
            perc_h = 1.0 - perc_y
        region_data = {'x': perc_x, 'y': perc_y,
                        'width': perc_w, 'height': perc_h}
        self.region_selection_changed.emit(
            self.target_monitor_mss_id, region_data)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().window())
        if self.target_monitor_scaled_rect.isNull() or self.target_monitor_mss_id is None:
            painter.setPen(self.palette().text().color())
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Select target monitor.")
            return
        target_mon_orig_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_orig_info:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                            f"Error: Monitor ID {self.target_monitor_mss_id} not found.")
            return
        painter.setBrush(DEFAULT_MONITOR_BG_COLOR)
        painter.setPen(QPen(ACTIVE_MONITOR_BORDER_COLOR, 2))
        painter.drawRect(self.target_monitor_scaled_rect)
        mon_text = f"Target: {target_mon_orig_info.get('name', f'ID {self.target_monitor_mss_id}')}\n" \
            f"{target_mon_orig_info['width']}x{target_mon_orig_info['height']}"
        painter.setPen(self.palette().text().color())
        painter.drawText(self.target_monitor_scaled_rect.adjusted(
            5, 5, -5, -5), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, mon_text)
        if not self.selection_rect_scaled.isNull():
            painter.setBrush(SELECTION_RECT_COLOR)
            painter.setPen(QPen(SELECTION_RECT_BORDER_COLOR,
                            1, Qt.PenStyle.SolidLine))
            painter.drawRect(self.selection_rect_scaled.toRect())
            painter.setBrush(SELECTION_RECT_BORDER_COLOR.lighter(120))
            painter.setPen(Qt.PenStyle.NoPen)
            for rect in self._get_handle_rects().values():
                painter.drawRect(rect)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalculate_scales_and_selection_rect()
        self._emit_selection_changed()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        if event.button() == Qt.MouseButton.LeftButton:
            if self.target_monitor_mss_id is None or self.target_monitor_scaled_rect.isNull():
                return
            self._active_interaction = self._get_handle_at_pos(pos)
            if self._active_interaction != ResizeHandle.NONE:
                self._drag_start_mouse_pos = pos
                self._resize_start_rect_scaled = QRectF(
                    self.selection_rect_scaled)
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self._active_interaction == ResizeHandle.NONE:
            hover_handle = self._get_handle_at_pos(pos)
            if hover_handle in [ResizeHandle.TOP_LEFT, ResizeHandle.BOTTOM_RIGHT]:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif hover_handle in [ResizeHandle.TOP_RIGHT, ResizeHandle.BOTTOM_LEFT]:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif hover_handle in [ResizeHandle.TOP_MIDDLE, ResizeHandle.BOTTOM_MIDDLE]:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif hover_handle in [ResizeHandle.MIDDLE_LEFT, ResizeHandle.MIDDLE_RIGHT]:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif hover_handle == ResizeHandle.BODY:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        delta = pos - self._drag_start_mouse_pos
        new_rect = QRectF(self._resize_start_rect_scaled)
        min_scaled_size = MIN_SELECTION_LOGICAL_SIZE * self.current_scale_factor
        if self._active_interaction == ResizeHandle.BODY:
            new_rect.translate(delta)
            self.selection_rect_scaled = new_rect
            self._clamp_selection_rect_to_current_monitor_view()
        elif self._active_interaction != ResizeHandle.NONE:
            if self._active_interaction in [ResizeHandle.TOP_LEFT, ResizeHandle.TOP_MIDDLE, ResizeHandle.TOP_RIGHT]:
                new_top = self._resize_start_rect_scaled.top() + delta.y()
                if self._resize_start_rect_scaled.bottom() - new_top < min_scaled_size:
                    new_top = self._resize_start_rect_scaled.bottom() - min_scaled_size
                new_rect.setTop(new_top)
            if self._active_interaction in [ResizeHandle.BOTTOM_LEFT, ResizeHandle.BOTTOM_MIDDLE, ResizeHandle.BOTTOM_RIGHT]:
                new_bottom = self._resize_start_rect_scaled.bottom() + delta.y()
                if new_bottom - new_rect.top() < min_scaled_size:
                    new_bottom = new_rect.top() + min_scaled_size
                new_rect.setBottom(new_bottom)
            if self._active_interaction in [ResizeHandle.TOP_LEFT, ResizeHandle.MIDDLE_LEFT, ResizeHandle.BOTTOM_LEFT]:
                new_left = self._resize_start_rect_scaled.left() + delta.x()
                if self._resize_start_rect_scaled.right() - new_left < min_scaled_size:
                    new_left = self._resize_start_rect_scaled.right() - min_scaled_size
                new_rect.setLeft(new_left)
            if self._active_interaction in [ResizeHandle.TOP_RIGHT, ResizeHandle.MIDDLE_RIGHT, ResizeHandle.BOTTOM_RIGHT]:
                new_right = self._resize_start_rect_scaled.right() + delta.x()
                if new_right - new_rect.left() < min_scaled_size:
                    new_right = new_rect.left() + min_scaled_size
                new_rect.setRight(new_right)
            self.selection_rect_scaled = new_rect.normalized()
            self._clamp_selection_rect_to_current_monitor_view()
        self._update_logical_state_from_scaled_rect()
        self.update()
        self._emit_selection_changed()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._active_interaction != ResizeHandle.NONE:
            self._active_interaction = ResizeHandle.NONE
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._update_logical_state_from_scaled_rect()
            self.update()
            self._emit_selection_changed()

    def _get_handle_rects(self) -> dict[ResizeHandle, QRectF]:
        if self.selection_rect_scaled.isNull():
            return {}
        s = self.selection_rect_scaled
        h_half = HANDLE_SIZE / 2.0
        return {
            ResizeHandle.TOP_LEFT: QRectF(s.left() - h_half, s.top() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.TOP_MIDDLE: QRectF(s.center().x() - h_half, s.top() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.TOP_RIGHT: QRectF(s.right() - h_half, s.top() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.MIDDLE_LEFT: QRectF(s.left() - h_half, s.center().y() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.MIDDLE_RIGHT: QRectF(s.right() - h_half, s.center().y() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.BOTTOM_LEFT: QRectF(s.left() - h_half, s.bottom() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.BOTTOM_MIDDLE: QRectF(s.center().x() - h_half, s.bottom() - h_half, HANDLE_SIZE, HANDLE_SIZE),
            ResizeHandle.BOTTOM_RIGHT: QRectF(s.right() - h_half, s.bottom() - h_half, HANDLE_SIZE, HANDLE_SIZE),
        }

    def _get_handle_at_pos(self, pos: QPointF) -> ResizeHandle:
        for handle, rect in self._get_handle_rects().items():
            if rect.contains(pos):
                return handle
        if self.selection_rect_scaled.contains(pos):
            return ResizeHandle.BODY
        return ResizeHandle.NONE

    def _clamp_selection_rect_to_current_monitor_view(self):
        if self.selection_rect_scaled.isNull() or self.target_monitor_scaled_rect.isNull():
            return
        sel = self.selection_rect_scaled
        mon_rect = self.target_monitor_scaled_rect.toRectF()
        new_x = max(mon_rect.left(), min(
            sel.left(), mon_rect.right() - sel.width()))
        new_y = max(mon_rect.top(), min(
            sel.top(), mon_rect.bottom() - sel.height()))
        new_w = min(sel.width(), mon_rect.right() - new_x)
        new_h = min(sel.height(), mon_rect.bottom() - new_y)
        self.selection_rect_scaled = QRectF(new_x, new_y, new_w, new_h)

    def get_current_selection_parameters(self) -> tuple[int | None, dict | None]:
        if self.target_monitor_mss_id is None:
            return None, None
        target_mon_info = next(
            (m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info or self.current_scale_factor <= 0:
            return self.target_monitor_mss_id, None
        mon_orig_w = float(target_mon_info.get('width', 1))
        mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1))
        mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        perc_x = self._current_sample_box_logical_x / mon_orig_w
        perc_y = self._current_sample_box_logical_y / mon_orig_h
        perc_w = self._current_sample_box_logical_width / mon_orig_w
        perc_h = self._current_sample_box_logical_height / mon_orig_h
        perc_x = max(0.0, min(perc_x, 1.0))
        perc_y = max(0.0, min(perc_y, 1.0))
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM, min(
            perc_w, 1.0 - perc_x if perc_x < 1.0 else 0.0))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM, min(
            perc_h, 1.0 - perc_y if perc_y < 1.0 else 0.0))
        if perc_x + perc_w > 1.0:
            perc_w = 1.0 - perc_x
        if perc_y + perc_h > 1.0:
            perc_h = 1.0 - perc_y
        return self.target_monitor_mss_id, {'x': perc_x, 'y': perc_y, 'width': perc_w, 'height': perc_h}

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mock_monitors_main = [{'id': 1, 'name': 'Monitor 1 (1920x1080)', 'top': 0, 'left': 0, 'width': 1920, 'height': 1080, 'monitor_dict': {}},
                            {'id': 2, 'name': 'Monitor 2 (1080x1920)', 'top': 0, 'left': 1920, 'width': 1080, 'height': 1920, 'monitor_dict': {}}]
    window_main = QWidget()
    layout_main = QVBoxLayout(window_main)
    monitor_view_main = MonitorViewWidget()
    layout_main.addWidget(monitor_view_main)
    monitor_view_main.set_monitors_data(
        mock_monitors_main, target_mss_id_to_focus=1)

    def on_selection_changed_main(mon_id, region_dict):
        pass

    monitor_view_main.region_selection_changed.connect(
        on_selection_changed_main)
    btn_get_sel_main = QPushButton("Get Current Sel Params")
    btn_get_sel_main.clicked.connect(lambda: print(
        f"Test Main Get: {monitor_view_main.get_current_selection_parameters()}"))
    layout_main.addWidget(btn_get_sel_main)

    # --- Test Cycle Button ---
    btn_cycle = QPushButton("Test Cycle Monitor")
    btn_cycle.clicked.connect(monitor_view_main.cycle_to_next_monitor)
    layout_main.addWidget(btn_cycle)

    window_main.setWindowTitle("Monitor View Widget Test - Freeform Logic")
    window_main.setGeometry(200, 200, 700, 550)
    window_main.show()
    sys.exit(app.exec())
