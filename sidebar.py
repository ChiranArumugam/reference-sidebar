from __future__ import annotations
from pathlib import Path
from aqt import mw
from aqt.qt import (QDockWidget, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout,
                    QWidget, QPixmap, Qt, QPalette,
                    QPushButton, QFileDialog, QComboBox)

try:
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    RIGHT_AREA = Qt.DockWidgetArea.RightDockWidgetArea
except AttributeError:
    ALIGN_TOP = Qt.AlignTop
    ALIGN_LEFT = Qt.AlignLeft
    RIGHT_AREA = Qt.RightDockWidgetArea

class ReferenceSidebar(QDockWidget):
    def __init__(self, config, config_path):
        super().__init__("References")
        self._cfg = config
        self._cfg_path = config_path
        self.current_deck_id: str | None = None

        # --- image label & scroll area -----------------------------------
        self._img_label = QLabel("No image")
        self._img_label.setAlignment(ALIGN_TOP | ALIGN_LEFT)
        
        # cross-Qt palette role -----------------------------------------------------
        try:                 # Qt6
            BASE_ROLE = QPalette.ColorRole.Base
        except AttributeError:  # Qt5
            BASE_ROLE = QPalette.Base

        self._img_label.setBackgroundRole(BASE_ROLE)

        self._orig_pix: QPixmap | None = None   # unscaled copy
        self._zoom = 1.0

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._img_label)

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
        self.setMinimumWidth(220)

    def show_image_for_deck(self, deck_id: str, img_path: Path | None):
        self.current_deck_id = deck_id
        self._populate_dropdown()
        # if caller didn't supply a path (no images yet) choose first/none
        if not img_path and self._combo.count():
            img_path = Path(mw.col.media.dir()) / self._combo.currentData()
        self._set_image(img_path)

    def reload_config(self):
        try:
            self._cfg.load()
        except Exception as e:
            print("[RefImg] could not reload config:", e)

    def _on_upload(self):
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
        deck_list = self._cfg.deck_to_images.setdefault(
            self.current_deck_id, []
        )
        if not any(entry["fname"] == stored_name for entry in deck_list):
            deck_list.append({"fname": stored_name, "title": Path(stored_name).stem})
            self._cfg.save()
            print(f"[RefImg] linked {stored_name} to deck {self.current_deck_id}")
        self._populate_dropdown()
        self._combo.setCurrentIndex(self._combo.findData(stored_name))
        media_dir = Path(mw.col.media.dir())
        self._set_image(media_dir / stored_name)
        self._cfg.last_selected[self.current_deck_id] = stored_name
        self._cfg.save()

    def _set_image(self, img_path: Path | None):
        if img_path and img_path.exists():
            self._orig_pix = QPixmap(str(img_path))
            self._zoom = 1.0
            self._apply_zoom()
        else:
            self._orig_pix = None
            self._img_label.setText("No image for this deck.\n\nClick 'Upload Image' to add one.")

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
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._img_label.setPixmap(scaled)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._change_zoom(1.25 if event.angleDelta().y() > 0 else 0.8)
            event.accept()
        else:
            super().wheelEvent(event)

    def _populate_dropdown(self):
        """Load current deck's image list into the combo."""
        self._combo.blockSignals(True)
        self._combo.clear()

        deck_list = self._cfg.deck_to_images.get(self.current_deck_id, [])
        for entry in deck_list:
            self._combo.addItem(entry["title"], entry["fname"])

        # restore last selection
        last = self._cfg.last_selected.get(self.current_deck_id)
        if last:
            idx = self._combo.findData(last)
            if idx != -1:
                self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)

    def _on_combo_change(self, idx: int):
        """User picked a different image."""
        if idx == -1:
            return
        fname = self._combo.itemData(idx)
        self._cfg.last_selected[self.current_deck_id] = fname
        self._cfg.save()
        media_dir = Path(mw.col.media.dir())
        self._set_image(media_dir / fname)