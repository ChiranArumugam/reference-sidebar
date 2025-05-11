from __future__ import annotations
from pathlib import Path
from aqt import mw
from aqt.qt import (QDockWidget, QLabel, QScrollArea, QVBoxLayout,
                    QWidget, QPixmap, Qt, QPushButton,
                    QFileDialog, QComboBox)

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
        self._img_label = QLabel("No image")
        self._img_label.setAlignment(ALIGN_TOP | ALIGN_LEFT)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._img_label)

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_change)

        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(self._on_upload)
        
        layout = QVBoxLayout()
        layout.addWidget(self._combo)
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
            pix = QPixmap(str(img_path))
            self._img_label.setPixmap(pix)
        else:
            self._img_label.setText("No image for this deck.\n\nClick 'Upload Image' to add one.")

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