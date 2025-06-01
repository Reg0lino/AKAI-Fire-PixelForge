# AKAI_Fire_RGB_Controller/gui/monitor_view_widget.py
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent, QCursor
from enum import Enum

print("--- EXECUTING monitor_view_widget.py (VERSION: MVW_JULY_22_B) ---")
print(f"--- MVW __file__: {__file__} ---")

MONITOR_AREA_PADDING = 10
DEFAULT_MONITOR_BG_COLOR = QColor(55, 55, 60)
ACTIVE_MONITOR_BORDER_COLOR = QColor(100, 150, 255)
SELECTION_RECT_COLOR = QColor(0, 180, 255, 60) 
SELECTION_RECT_BORDER_COLOR = QColor(0, 220, 255, 120)
SNAP_THRESHOLD = 10 
HANDLE_SIZE = 8 
MIN_SELECTION_LOGICAL_SIZE = 20 # Min width/height in original monitor pixels for user interaction
MIN_SELECTION_PERCENTAGE_DIM = 0.001 # Min perc w/h to avoid division by zero if region is tiny

class ResizeHandle(Enum):
    NONE = 0; TOP_LEFT = 1; TOP_MIDDLE = 2; TOP_RIGHT = 3
    MIDDLE_LEFT = 4; MIDDLE_RIGHT = 5; BOTTOM_LEFT = 6
    BOTTOM_MIDDLE = 7; BOTTOM_RIGHT = 8; BODY = 9

class MonitorViewWidget(QWidget):
    region_selection_changed = pyqtSignal(int, dict) 

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

    def set_monitors_data(self, monitors_data_from_mss: list[dict], target_mss_id_to_focus: int | None = None):
        self.all_monitors_original_info = monitors_data_from_mss
        if not self.all_monitors_original_info:
            self.target_monitor_mss_id = None; self._reset_scaled_rects(); self.update(); return
        valid_target_id = target_mss_id_to_focus
        if target_mss_id_to_focus is None or not any(m['id'] == target_mss_id_to_focus for m in self.all_monitors_original_info):
            primaries = [m for m in self.all_monitors_original_info if m['left'] == 0 and m['top'] == 0]
            valid_target_id = primaries[0]['id'] if primaries else self.all_monitors_original_info[0]['id']
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == valid_target_id), None)
        if target_mon_info: # Set initial default logical size relative to the first target monitor
            self._current_sample_box_logical_width = target_mon_info['width'] * 0.2 # Default to 20% width
            self._current_sample_box_logical_height = target_mon_info['height'] * 0.2 # Default to 20% height
            self._current_sample_box_logical_x = target_mon_info['width'] * 0.4 # Centered X
            self._current_sample_box_logical_y = target_mon_info['height'] * 0.4 # Centered Y
        self.set_target_monitor_and_update_view(valid_target_id)

    def _reset_scaled_rects(self):
        self.target_monitor_scaled_rect = QRect()
        self.selection_rect_scaled = QRectF()
        self.current_scale_factor = 1.0

    def set_target_monitor_and_update_view(self, target_mss_id: int):
        """Sets the target monitor, recalculates scales, and updates the selection rectangle based on current logical values."""
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == target_mss_id), None)
        if not target_mon_info:
            print(f"MonitorViewWidget Error: Invalid target_mss_id: {target_mss_id}")
            # Potentially fallback or clear if current target_monitor_mss_id becomes invalid
            if self.all_monitors_original_info: self.target_monitor_mss_id = self.all_monitors_original_info[0]['id']
            else: self.target_monitor_mss_id = None; self._reset_scaled_rects()
        else:
            self.target_monitor_mss_id = target_mss_id

        self._recalculate_scales_and_selection_rect() # This will use current logical values
        self.update()
        self._emit_selection_changed() # Emit based on the newly calculated view

    def _recalculate_scales_and_selection_rect(self):
        """Recalculates target_monitor_scaled_rect, current_scale_factor, AND selection_rect_scaled from current logical values."""
        self.target_monitor_scaled_rect = QRect()
        self.selection_rect_scaled = QRectF() # Reset before recalculating
        if self.target_monitor_mss_id is None or not self.all_monitors_original_info: return
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info: return
        widget_w = self.width() - 2 * MONITOR_AREA_PADDING
        widget_h = self.height() - 2 * MONITOR_AREA_PADDING
        if widget_w <= 0 or widget_h <= 0: return
        mon_orig_w, mon_orig_h = target_mon_info['width'], target_mon_info['height']
        if mon_orig_w == 0 or mon_orig_h == 0: return
        scale_x = widget_w / mon_orig_w; scale_y = widget_h / mon_orig_h
        self.current_scale_factor = min(scale_x, scale_y)
        if self.current_scale_factor <= 0: self.current_scale_factor = 1.0 # Safety for division
        scaled_mon_w = int(mon_orig_w * self.current_scale_factor)
        scaled_mon_h = int(mon_orig_h * self.current_scale_factor)
        offset_x = MONITOR_AREA_PADDING + (widget_w - scaled_mon_w) // 2
        offset_y = MONITOR_AREA_PADDING + (widget_h - scaled_mon_h) // 2
        self.target_monitor_scaled_rect = QRect(offset_x, offset_y, scaled_mon_w, scaled_mon_h)
        # Now, update selection_rect_scaled based on current logical values and new scale
        scaled_sel_x = self.target_monitor_scaled_rect.left() + (self._current_sample_box_logical_x * self.current_scale_factor)
        scaled_sel_y = self.target_monitor_scaled_rect.top() + (self._current_sample_box_logical_y * self.current_scale_factor)
        scaled_sel_w = self._current_sample_box_logical_width * self.current_scale_factor
        scaled_sel_h = self._current_sample_box_logical_height * self.current_scale_factor
        self.selection_rect_scaled = QRectF(scaled_sel_x, scaled_sel_y, max(1.0, scaled_sel_w), max(1.0, scaled_sel_h))
        self._clamp_selection_rect_to_current_monitor_view()

    def set_current_selection_from_params(self, target_mss_id: int, region_rect_percentage: dict):
        print(f"--- MVW.set_current_selection_from_params CALLED (VERSION: MVW_JULY_22_B) --- target_id={target_mss_id}, region%={region_rect_percentage}")
        """ Called by MainWindow/Dialog to set selection based on loaded/defined parameters (percentages). """
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == target_mss_id), None)
        if not target_mon_info:
            print(f"MonitorViewWidget Error: Cannot set selection, unknown target_mss_id: {target_mss_id}"); return
        self.target_monitor_mss_id = target_mss_id # Ensure current target is this one
        mon_orig_w = float(target_mon_info.get('width', 1)); mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1)); mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        # 1. Directly update logical dimensions from incoming percentages
        perc_x = region_rect_percentage.get('x', 0.4)
        perc_y = region_rect_percentage.get('y', 0.4)
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM, region_rect_percentage.get('width', 0.2))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM, region_rect_percentage.get('height', 0.2))
        self._current_sample_box_logical_x = perc_x * mon_orig_w
        self._current_sample_box_logical_y = perc_y * mon_orig_h
        self._current_sample_box_logical_width = perc_w * mon_orig_w
        self._current_sample_box_logical_height = perc_h * mon_orig_h
        # Ensure logical dimensions are not ridiculously small before scaling
        self._current_sample_box_logical_width = max(MIN_SELECTION_LOGICAL_SIZE, self._current_sample_box_logical_width)
        self._current_sample_box_logical_height = max(MIN_SELECTION_LOGICAL_SIZE, self._current_sample_box_logical_height)
        # 2. Recalculate all scaled representations based on new logical values and current widget size
        self._recalculate_scales_and_selection_rect() 
        self.update()

    def _update_logical_state_from_scaled_rect(self):
        """Updates internal logical x,y,w,h based on the current self.selection_rect_scaled."""
        if self.current_scale_factor <= 0 or self.selection_rect_scaled.isNull() or self.target_monitor_scaled_rect.isNull():
            return
        # Calculate logical top-left relative to monitor's original 0,0
        logical_x = (self.selection_rect_scaled.left() - self.target_monitor_scaled_rect.left()) / self.current_scale_factor
        logical_y = (self.selection_rect_scaled.top() - self.target_monitor_scaled_rect.top()) / self.current_scale_factor
        logical_w = self.selection_rect_scaled.width() / self.current_scale_factor
        logical_h = self.selection_rect_scaled.height() / self.current_scale_factor
        self._current_sample_box_logical_x = logical_x
        self._current_sample_box_logical_y = logical_y
        self._current_sample_box_logical_width = max(MIN_SELECTION_LOGICAL_SIZE, logical_w)
        self._current_sample_box_logical_height = max(MIN_SELECTION_LOGICAL_SIZE, logical_h)

    def _emit_selection_changed(self):
        if self.target_monitor_mss_id is None or not self.all_monitors_original_info or self.current_scale_factor <= 0:
            return
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info: return
        mon_orig_w = float(target_mon_info.get('width', 1)); mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1)); mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        # Calculate percentages from the current logical state
        perc_x = self._current_sample_box_logical_x / mon_orig_w
        perc_y = self._current_sample_box_logical_y / mon_orig_h
        perc_w = self._current_sample_box_logical_width / mon_orig_w
        perc_h = self._current_sample_box_logical_height / mon_orig_h
        # Clamp percentages carefully to ensure they are valid and sum correctly if needed
        perc_x = max(0.0, min(perc_x, 1.0))
        perc_y = max(0.0, min(perc_y, 1.0))
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM, min(perc_w, 1.0 - perc_x if perc_x < 1.0 else 0.0))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM, min(perc_h, 1.0 - perc_y if perc_y < 1.0 else 0.0))
        # Final check ensure x+w <= 1 and y+h <= 1
        if perc_x + perc_w > 1.0: perc_w = 1.0 - perc_x
        if perc_y + perc_h > 1.0: perc_h = 1.0 - perc_y
        region_data = {'x': perc_x, 'y': perc_y, 'width': perc_w, 'height': perc_h}
        self.region_selection_changed.emit(self.target_monitor_mss_id, region_data)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().window())
        if self.target_monitor_scaled_rect.isNull() or self.target_monitor_mss_id is None:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select target monitor."); return
        target_mon_orig_info = next((m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_orig_info:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"Error: Monitor ID {self.target_monitor_mss_id} not found."); return
        painter.setBrush(DEFAULT_MONITOR_BG_COLOR)
        painter.setPen(QPen(ACTIVE_MONITOR_BORDER_COLOR, 2))
        painter.drawRect(self.target_monitor_scaled_rect)
        
        mon_text = f"Target: {target_mon_orig_info.get('name', f'ID {self.target_monitor_mss_id}')}\n" \
                    f"{target_mon_orig_info['width']}x{target_mon_orig_info['height']}"
        painter.setPen(self.palette().text().color())
        painter.drawText(self.target_monitor_scaled_rect.adjusted(5, 5, -5, -5), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, mon_text)
        if not self.selection_rect_scaled.isNull():
            painter.setBrush(SELECTION_RECT_COLOR)
            painter.setPen(QPen(SELECTION_RECT_BORDER_COLOR, 1, Qt.PenStyle.SolidLine))
            painter.drawRect(self.selection_rect_scaled.toRect()) 
            painter.setBrush(SELECTION_RECT_BORDER_COLOR.lighter(120))
            painter.setPen(Qt.PenStyle.NoPen)
            for rect in self._get_handle_rects().values():
                painter.drawRect(rect)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalculate_scales_and_selection_rect() # This updates based on current logicals
        self._emit_selection_changed() # Emit based on new visual state

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        if event.button() == Qt.MouseButton.LeftButton:
            if self.target_monitor_mss_id is None or self.target_monitor_scaled_rect.isNull(): return
            self._active_interaction = self._get_handle_at_pos(pos)
            if self._active_interaction != ResizeHandle.NONE:
                self._drag_start_mouse_pos = pos
                self._resize_start_rect_scaled = QRectF(self.selection_rect_scaled) 
                self.update() 
            elif self.target_monitor_scaled_rect.contains(pos.toPoint()): 
                target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
                if not target_mon_info: return
                # Default new selection to 20% of monitor, centered on click
                self._current_sample_box_logical_width = target_mon_info['width'] * 0.2
                self._current_sample_box_logical_height = target_mon_info['height'] * 0.2
                # Calculate logical x/y based on click position
                logical_click_x = (pos.x() - self.target_monitor_scaled_rect.left()) / self.current_scale_factor
                logical_click_y = (pos.y() - self.target_monitor_scaled_rect.top()) / self.current_scale_factor
                self._current_sample_box_logical_x = logical_click_x - self._current_sample_box_logical_width / 2.0
                self._current_sample_box_logical_y = logical_click_y - self._current_sample_box_logical_height / 2.0
                self._recalculate_scales_and_selection_rect() # Update scaled rect from new logicals
                self._try_snap_selection_drag() 
                self._update_logical_state_from_scaled_rect() # Sync logicals if snap occurred
                self.update()
                self._emit_selection_changed()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self._active_interaction == ResizeHandle.NONE: 
            hover_handle = self._get_handle_at_pos(pos)
            if hover_handle in [ResizeHandle.TOP_LEFT, ResizeHandle.BOTTOM_RIGHT]: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif hover_handle in [ResizeHandle.TOP_RIGHT, ResizeHandle.BOTTOM_LEFT]: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif hover_handle in [ResizeHandle.TOP_MIDDLE, ResizeHandle.BOTTOM_MIDDLE]: self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif hover_handle in [ResizeHandle.MIDDLE_LEFT, ResizeHandle.MIDDLE_RIGHT]: self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif hover_handle == ResizeHandle.BODY: self.setCursor(Qt.CursorShape.SizeAllCursor)
            else: self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
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
                if self._resize_start_rect_scaled.bottom() - new_top < min_scaled_size: new_top = self._resize_start_rect_scaled.bottom() - min_scaled_size
                new_rect.setTop(new_top)
            if self._active_interaction in [ResizeHandle.BOTTOM_LEFT, ResizeHandle.BOTTOM_MIDDLE, ResizeHandle.BOTTOM_RIGHT]:
                new_bottom = self._resize_start_rect_scaled.bottom() + delta.y()
                if new_bottom - new_rect.top() < min_scaled_size: new_bottom = new_rect.top() + min_scaled_size
                new_rect.setBottom(new_bottom)
            if self._active_interaction in [ResizeHandle.TOP_LEFT, ResizeHandle.MIDDLE_LEFT, ResizeHandle.BOTTOM_LEFT]:
                new_left = self._resize_start_rect_scaled.left() + delta.x()
                if self._resize_start_rect_scaled.right() - new_left < min_scaled_size: new_left = self._resize_start_rect_scaled.right() - min_scaled_size
                new_rect.setLeft(new_left)
            if self._active_interaction in [ResizeHandle.TOP_RIGHT, ResizeHandle.MIDDLE_RIGHT, ResizeHandle.BOTTOM_RIGHT]:
                new_right = self._resize_start_rect_scaled.right() + delta.x()
                if new_right - new_rect.left() < min_scaled_size: new_right = new_rect.left() + min_scaled_size
                new_rect.setRight(new_right)
            self.selection_rect_scaled = new_rect.normalized()
            self._clamp_selection_rect_to_current_monitor_view()
            self._try_snap_selection_resize() 
        self._update_logical_state_from_scaled_rect()
        self.update()
        self._emit_selection_changed() 

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._active_interaction != ResizeHandle.NONE:
            if self._active_interaction == ResizeHandle.BODY: self._try_snap_selection_drag()
            else: self._try_snap_selection_resize()
            self._active_interaction = ResizeHandle.NONE
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._update_logical_state_from_scaled_rect()
            self.update()
            self._emit_selection_changed()

    def _get_handle_rects(self) -> dict[ResizeHandle, QRectF]: 
        if self.selection_rect_scaled.isNull(): return {}
        s = self.selection_rect_scaled; h_half = HANDLE_SIZE / 2.0
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
            if rect.contains(pos): return handle
        if self.selection_rect_scaled.contains(pos): return ResizeHandle.BODY
        return ResizeHandle.NONE

    def _clamp_selection_rect_to_current_monitor_view(self): 
        if self.selection_rect_scaled.isNull() or self.target_monitor_scaled_rect.isNull(): return
        sel = self.selection_rect_scaled; mon_rect = self.target_monitor_scaled_rect.toRectF()
        new_x = max(mon_rect.left(), min(sel.left(), mon_rect.right() - sel.width()))
        new_y = max(mon_rect.top(), min(sel.top(), mon_rect.bottom() - sel.height()))
        new_w = min(sel.width(), mon_rect.right() - new_x)
        new_h = min(sel.height(), mon_rect.bottom() - new_y)
        self.selection_rect_scaled = QRectF(new_x, new_y, new_w, new_h)

    def _get_snap_points_scaled(self) -> dict[str, QPointF]: 
        points = {}; 
        if self.target_monitor_scaled_rect.isNull(): return points
        pm_rect = self.target_monitor_scaled_rect.toRectF()
        points["mon_c_x"]=pm_rect.center().x(); points["mon_c_y"]=pm_rect.center().y()
        points["mon_l"]=pm_rect.left(); points["mon_r"]=pm_rect.right()
        points["mon_t"]=pm_rect.top(); points["mon_b"]=pm_rect.bottom()
        points["mon_q1_x"]=pm_rect.left()+pm_rect.width()/4.0; points["mon_q2_x"]=pm_rect.left()+pm_rect.width()/2.0
        points["mon_q3_x"]=pm_rect.left()+3*pm_rect.width()/4.0; points["mon_q1_y"]=pm_rect.top()+pm_rect.height()/4.0
        points["mon_q2_y"]=pm_rect.top()+pm_rect.height()/2.0; points["mon_q3_y"]=pm_rect.top()+3*pm_rect.height()/4.0
        return points

    def _try_snap_selection_drag(self): 
        if self.selection_rect_scaled.isNull(): return
        snap_points = self._get_snap_points_scaled(); sel_center = self.selection_rect_scaled.center()
        sel_tl = self.selection_rect_scaled.topLeft(); best_snap_offset = QPointF(0,0)
        min_dist_sq_center = SNAP_THRESHOLD ** 2; snapped_center = False
        for target_x_key in ["mon_c_x", "mon_q1_x", "mon_q3_x"]:
            dist_x = sel_center.x() - snap_points[target_x_key]
            if abs(dist_x) < SNAP_THRESHOLD : # Check individual axis for center snap
                if not snapped_center or abs(dist_x) < abs(best_snap_offset.x()): best_snap_offset.setX(-dist_x); snapped_center = True
        for target_y_key in ["mon_c_y", "mon_q1_y", "mon_q3_y"]:
            dist_y = sel_center.y() - snap_points[target_y_key]
            if abs(dist_y) < SNAP_THRESHOLD:
                if not snapped_center or abs(dist_y) < abs(best_snap_offset.y()): best_snap_offset.setY(-dist_y); snapped_center = True
        
        min_dist_sq_tl = SNAP_THRESHOLD ** 2; snapped_tl = False; best_snap_offset_tl = QPointF(0,0)
        if abs(sel_tl.x() - snap_points["mon_l"]) < SNAP_THRESHOLD :
             offset_x = snap_points["mon_l"] - sel_tl.x(); best_snap_offset_tl.setX(offset_x); snapped_tl = True
        if abs(sel_tl.y() - snap_points["mon_t"]) < SNAP_THRESHOLD :
             offset_y = snap_points["mon_t"] - sel_tl.y(); best_snap_offset_tl.setY(offset_y); snapped_tl = True

        # Prefer TL snap if it's very close, otherwise use center snap if available
        final_offset_to_apply = QPointF(0,0)
        if snapped_tl and (best_snap_offset_tl.x() != 0 or best_snap_offset_tl.y() !=0) :
            # Heuristic: if TL snap is significant, use it.
            # This might need tuning. If TL is snapping one axis and Center the other, how to choose?
            # For now, if TL snaps any axis, prioritize its full offset.
            final_offset_to_apply = best_snap_offset_tl
        elif snapped_center:
            final_offset_to_apply = best_snap_offset
        
        if final_offset_to_apply.x() != 0 or final_offset_to_apply.y() != 0:
            self.selection_rect_scaled.translate(final_offset_to_apply)
            self._clamp_selection_rect_to_current_monitor_view()

    def _try_snap_selection_resize(self):
        if self.selection_rect_scaled.isNull() or self._active_interaction == ResizeHandle.NONE: return
        snap_points = self._get_snap_points_scaled(); current_rect = QRectF(self.selection_rect_scaled)
        active_edges_x = []; active_edges_y = []
        if self._active_interaction in [ResizeHandle.TOP_LEFT,ResizeHandle.MIDDLE_LEFT,ResizeHandle.BOTTOM_LEFT]: active_edges_x.append("left")
        if self._active_interaction in [ResizeHandle.TOP_RIGHT,ResizeHandle.MIDDLE_RIGHT,ResizeHandle.BOTTOM_RIGHT]: active_edges_x.append("right")
        if self._active_interaction in [ResizeHandle.TOP_LEFT,ResizeHandle.TOP_MIDDLE,ResizeHandle.TOP_RIGHT]: active_edges_y.append("top")
        if self._active_interaction in [ResizeHandle.BOTTOM_LEFT,ResizeHandle.BOTTOM_MIDDLE,ResizeHandle.BOTTOM_RIGHT]: active_edges_y.append("bottom")
        for edge_type in active_edges_x:
            edge_val = current_rect.left() if edge_type == "left" else current_rect.right()
            best_snap_delta = 0; min_dist = SNAP_THRESHOLD
            for sp_key in ["mon_l","mon_r","mon_c_x","mon_q1_x","mon_q3_x"]:
                dist = abs(edge_val - snap_points[sp_key])
                if dist < min_dist: min_dist = dist; best_snap_delta = snap_points[sp_key] - edge_val
            if best_snap_delta != 0:
                if edge_type == "left": current_rect.setLeft(current_rect.left() + best_snap_delta)
                else: current_rect.setRight(current_rect.right() + best_snap_delta)
        for edge_type in active_edges_y:
            edge_val = current_rect.top() if edge_type == "top" else current_rect.bottom()
            best_snap_delta = 0; min_dist = SNAP_THRESHOLD
            for sp_key in ["mon_t","mon_b","mon_c_y","mon_q1_y","mon_q3_y"]:
                dist = abs(edge_val - snap_points[sp_key])
                if dist < min_dist: min_dist = dist; best_snap_delta = snap_points[sp_key] - edge_val
            if best_snap_delta != 0:
                if edge_type == "top": current_rect.setTop(current_rect.top() + best_snap_delta)
                else: current_rect.setBottom(current_rect.bottom() + best_snap_delta)
        self.selection_rect_scaled = current_rect.normalized()
        self._clamp_selection_rect_to_current_monitor_view()

    def get_current_selection_parameters(self) -> tuple[int | None, dict | None]:
        if self.target_monitor_mss_id is None: return None, None
        target_mon_info = next((m for m in self.all_monitors_original_info if m['id'] == self.target_monitor_mss_id), None)
        if not target_mon_info or self.current_scale_factor <= 0: return self.target_monitor_mss_id, None
        mon_orig_w = float(target_mon_info.get('width', 1)); mon_orig_w = 1.0 if mon_orig_w == 0 else mon_orig_w
        mon_orig_h = float(target_mon_info.get('height', 1)); mon_orig_h = 1.0 if mon_orig_h == 0 else mon_orig_h
        perc_x = self._current_sample_box_logical_x / mon_orig_w
        perc_y = self._current_sample_box_logical_y / mon_orig_h
        perc_w = self._current_sample_box_logical_width / mon_orig_w
        perc_h = self._current_sample_box_logical_height / mon_orig_h
        perc_x = max(0.0, min(perc_x, 1.0)); perc_y = max(0.0, min(perc_y, 1.0))
        perc_w = max(MIN_SELECTION_PERCENTAGE_DIM, min(perc_w, 1.0 - perc_x if perc_x < 1.0 else 0.0))
        perc_h = max(MIN_SELECTION_PERCENTAGE_DIM, min(perc_h, 1.0 - perc_y if perc_y < 1.0 else 0.0))
        if perc_x + perc_w > 1.0: perc_w = 1.0 - perc_x
        if perc_y + perc_h > 1.0: perc_h = 1.0 - perc_y
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
    monitor_view_main.set_monitors_data(mock_monitors_main, target_mss_id_to_focus=1)

    def on_selection_changed_main(mon_id, region_dict): 
        print(f"Test Main: MonID {mon_id}, Region %: x:{region_dict['x']:.4f}, y:{region_dict['y']:.4f}, w:{region_dict['width']:.4f}, h:{region_dict['height']:.4f}")

    monitor_view_main.region_selection_changed.connect(on_selection_changed_main)
    btn_get_sel_main = QPushButton("Get Current Sel Params")
    btn_get_sel_main.clicked.connect(lambda: print(f"Test Main Get: {monitor_view_main.get_current_selection_parameters()}"))
    layout_main.addWidget(btn_get_sel_main)
    btn_switch_mon1 = QPushButton("Switch to Monitor 1 & Update View")
    btn_switch_mon1.clicked.connect(lambda: monitor_view_main.set_target_monitor_and_update_view(1))
    layout_main.addWidget(btn_switch_mon1)
    btn_switch_mon2 = QPushButton("Switch to Monitor 2 & Update View")
    btn_switch_mon2.clicked.connect(lambda: monitor_view_main.set_target_monitor_and_update_view(2))
    layout_main.addWidget(btn_switch_mon2)
    window_main.setWindowTitle("Monitor View Widget Test - Precision Logic")
    window_main.setGeometry(200, 200, 700, 550) 
    window_main.show()
    sys.exit(app.exec())