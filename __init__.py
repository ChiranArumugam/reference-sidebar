from __future__ import annotations
import json
from pathlib import Path
from aqt import mw, gui_hooks
from aqt.qt import Qt, QWidget, QAction
from .sidebar import ReferenceSidebar
from .config import Config, ensure_config
from .manage import ManageDialog

addon_dir = Path(__file__).parent
config_path = addon_dir / "ref_images.json"
config: Config = ensure_config(config_path)

manage_act = mw.form.menuTools.addAction("Reference Images…")
manage_act.triggered.connect(lambda: ManageDialog(config).exec())

sidebar = ReferenceSidebar(config, config_path)
try:
    RIGHT_AREA = Qt.DockWidgetArea.RightDockWidgetArea
except AttributeError:
    RIGHT_AREA = Qt.RightDockWidgetArea

mw.addDockWidget(RIGHT_AREA, sidebar)
sidebar.hide()

# ---------- Tools menu toggle --------------------------------------------
toggle_act = QAction("Reference Sidebar", mw)
toggle_act.setShortcut("Alt+R")

def _toggle():
    vis = not sidebar.isVisible()
    sidebar.setVisible(vis)
    toggle_act.setChecked(vis)

toggle_act.setCheckable(True)
toggle_act.triggered.connect(_toggle)
mw.form.menuTools.addAction(toggle_act)

def on_reviewer_show(card):
    deck_id = str(card.did)
    images = config.deck_to_images.get(deck_id, [])
    media_dir = Path(mw.col.media.dir())
    if images:
        preferred = config.last_selected.get(deck_id, images[0]["fname"])
        img_path = media_dir / preferred
    else:
        img_path = None
    sidebar.show_image_for_deck(deck_id, img_path)

gui_hooks.reviewer_did_show_question.append(on_reviewer_show)

def on_profile_loaded():
    sidebar.reload_config()

def on_profile_open():
    sidebar.reload_config()

if hasattr(gui_hooks, "profile_did_open"):
    gui_hooks.profile_did_open.append(on_profile_open)
elif hasattr(gui_hooks, "profile_loaded"):
    gui_hooks.profile_loaded.append(on_profile_open)