from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QSpinBox, QCheckBox,
    QLabel, QPushButton,
)


class PrefsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Reference Sidebar – Preferences")
        self._cfg = cfg
        p = cfg.prefs

        # widgets
        self._chk_auto = QCheckBox("Auto-show sidebar when a review starts")
        self._chk_auto.setChecked(p["auto_show"])

        self._chk_vis = QCheckBox("Remember sidebar visibility across sessions")
        self._chk_vis.setChecked(p["remember_visibility"])

        self._zoom = QDoubleSpinBox()
        self._zoom.setRange(0.25, 4.0)
        self._zoom.setSingleStep(0.05)
        self._zoom.setValue(p["default_zoom"])
        self._zoom.setSuffix("×")

        self._width = QSpinBox()
        self._width.setRange(120, 600)
        self._width.setValue(p["sidebar_width"])
        self._width.setSuffix(" px")

        # layout
        lay = QVBoxLayout(self)
        lay.addWidget(self._chk_auto)
        lay.addWidget(self._chk_vis)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Default zoom:"))
        row1.addWidget(self._zoom)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Sidebar width:"))
        row2.addWidget(self._width)
        lay.addLayout(row2)

        btn = QPushButton("Save")
        btn.clicked.connect(self._on_save)
        lay.addStretch(1)
        lay.addWidget(btn)

    def _on_save(self):
        p = self._cfg.prefs
        p["auto_show"] = self._chk_auto.isChecked()
        p["remember_visibility"] = self._chk_vis.isChecked()
        p["default_zoom"] = round(self._zoom.value(), 2)
        p["sidebar_width"] = self._width.value()
        self._cfg.save()
        self.accept()
