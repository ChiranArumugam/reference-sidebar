from __future__ import annotations
from pathlib import Path
from aqt import mw
from aqt.qt import (
    QDockWidget, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout,
    QWidget, QPixmap, Qt, QPalette,
    QPushButton, QFileDialog, QComboBox, QMessageBox,
    QEvent
)

# Determine pinch gesture type safely
try:
    GESTURE_PINCH = Qt.GestureType.PinchGesture
except Exception:
    try:
        from aqt.qt import QPinchGesture

        GESTURE_PINCH = QPinchGesture.gestureType()
    except Exception:
        GESTURE_PINCH = None

# Determine aspect ratio and transformation modes
try:
    ASPECT_RATIO = Qt.KeepAspectRatio
    TRANSFORM_MODE = Qt.SmoothTransformation
except AttributeError:
    ASPECT_RATIO = Qt.AspectRatioMode.KeepAspectRatio
    TRANSFORM_MODE = Qt.TransformationMode.SmoothTransformation

# Alignment and dock area constants
try:
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    RIGHT_AREA = Qt.DockWidgetArea.RightDockWidgetArea
except Exception:
    ALIGN_TOP = Qt.AlignTop
    ALIGN_LEFT = Qt.AlignLeft
    RIGHT_AREA = Qt.RightDockWidgetArea


class ReferenceSidebar(QDockWidget):
    def __init__(self, config, config_path):
        super().__init__("References")
        self._cfg = config
        self._cfg_path = config_path
        self.current_deck_id: str | None = None

        # track pinch scale
        self._last_pinch_scale = 1.0

        # --- image label & scroll area -----------------------------------
        self._img_label = QLabel("No image")
        self._img_label.setAlignment(ALIGN_TOP | ALIGN_LEFT)

        # cross-Qt palette role
        try:
            BASE_ROLE = QPalette.ColorRole.Base
        except Exception:
            BASE_ROLE = QPalette.Base
        self._img_label.setBackgroundRole(BASE_ROLE)

        self._orig_pix: QPixmap | None = None
        self._zoom = self._cfg.prefs.get("default_zoom", 1.0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._img_label)
        # enable pinch-to-zoom if supported
        if GESTURE_PINCH is not None:
            try:
                scroll.viewport().grabGesture(GESTURE_PINCH)
            except Exception:
                pass

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_change)

        # --- zoom buttons -----------------------------------
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(26)
        zoom_in_btn.clicked.connect(lambda: self._change_zoom(1.25))

        zoom_out_btn = QPushButton("–")
        zoom_out_btn.setFixedWidth(26)
        zoom_out_btn.clicked.connect(lambda: self._change_zoom(0.8))

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(self._combo)
        zoom_row.addStretch(1)
        zoom_row.addWidget(zoom_out_btn)
        zoom_row.addWidget(zoom_in_btn)

        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(self._on_upload)

        layout = QVBoxLayout()
        layout.addLayout(zoom_row)
        layout.addWidget(upload_btn)
        layout.addWidget(scroll)
        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)
        self.setMinimumWidth(self._cfg.prefs.get("sidebar_width", 200))

    def show_image_for_deck(self, deck_id: str, img_path: Path | None):
        self.current_deck_id = deck_id
        self._populate_dropdown()
        if not img_path and self._combo.count():
            img_path = Path(mw.col.media.dir()) / self._combo.currentData()
        self._set_image(img_path)

    def reload_config(self):
        try:
            self._cfg.load()
        except Exception as e:
            print("[RefImg] could not reload config:", e)

    def _on_upload(self):
        if not hasattr(mw.reviewer, 'card') or not mw.reviewer.card:
            QMessageBox.information(
                self, "Upload Image",
                "Images can only be uploaded during review.\n\n"
                "Please open a deck and start reviewing to use this feature."
            )
            return
        if not self.current_deck_id:
            print("[RefImg] No active deck – upload aborted.")
            return
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Select image to link",
            "",
            "Images (*.png *.jpg *.jpeg *.gif)"
        )
        if not fname:
            return
        stored_name = mw.col.media.add_file(fname)
        deck_list = self._cfg.deck_to_images.setdefault(self.current_deck_id, [])
        if not any(entry["fname"] == stored_name for entry in deck_list):
            deck_list.append({"fname": stored_name, "title": Path(stored_name).stem})
            self._cfg.save()
            print(f"[RefImg] linked {stored_name} to deck {self.current_deck_id}")
        self._populate_dropdown()
        idx = self._combo.findData(stored_name)
        if idx != -1:
            self._combo.setCurrentIndex(idx)
        self._set_image(Path(mw.col.media.dir()) / stored_name)
        self._cfg.last_selected[self.current_deck_id] = stored_name
        self._cfg.save()

    def _set_image(self, img_path: Path | None):
        if img_path and img_path.exists():
            self._orig_pix = QPixmap(str(img_path))
            self._zoom = self._cfg.prefs.get("default_zoom", 1.0)
            self._apply_zoom()
        else:
            self._orig_pix = None
            self._img_label.setText(
                "No image for this deck.\n\nClick 'Upload Image' to add one."
            )

    def _change_zoom(self, factor: float):
        if not self._orig_pix:
            return
        self._zoom = max(0.25, min(4.0, self._zoom * factor))
        self._apply_zoom()

    def _apply_zoom(self):
        if not self._orig_pix:
            return
        scaled = self._orig_pix.scaled(
            self._orig_pix.width() * self._zoom,
            self._orig_pix.height() * self._zoom,
            ASPECT_RATIO,
            TRANSFORM_MODE,
        )
        self._img_label.setPixmap(scaled)

    def event(self, event):
        # ----- trackpad/touchpad pinch (macOS, some Wayland/X11 drivers) ---
        if event.type() == QEvent.Type.NativeGesture:
            try:
                ZOOM_NATIVE = Qt.NativeGestureType.ZoomNativeGesture
            except AttributeError:              # Qt-5 fallback
                ZOOM_NATIVE = Qt.ZoomNativeGesture

            if event.gestureType() == ZOOM_NATIVE:
                delta = 1.0 + event.value()     # value() is small, e.g. ±0.1
                self._change_zoom(delta)
                event.accept()
                return True

        # ----- true touchscreen pinch (rare on desktops) -------------------
        if GESTURE_PINCH is not None:
            if event.type() == QEvent.Type.Gesture:
                pinch = event.gesture(GESTURE_PINCH)
                if pinch:
                    delta = pinch.scaleFactor() / self._last_pinch_scale
                    self._change_zoom(delta)
                    if pinch.state() == Qt.GestureState.GestureFinished:
                        self._last_pinch_scale = 1.0
                    else:
                        self._last_pinch_scale = pinch.scaleFactor()
                    event.accept()
                    return True

        return super().event(event)

    def _populate_dropdown(self):
        self._combo.blockSignals(True)
        self._combo.clear()
        for entry in self._cfg.deck_to_images.get(self.current_deck_id, []):
            self._combo.addItem(entry["title"], entry["fname"])
        last = self._cfg.last_selected.get(self.current_deck_id)
        if last is not None:
            idx = self._combo.findData(last)
            if idx != -1:
                self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)

    def _on_combo_change(self, idx: int):
        if idx == -1:
            return
        fname = self._combo.itemData(idx)
        self._cfg.last_selected[self.current_deck_id] = fname
        self._cfg.save()
        self._set_image(Path(mw.col.media.dir()) / fname)
