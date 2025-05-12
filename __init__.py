from __future__ import annotations
import json
from pathlib import Path
from aqt import mw, gui_hooks
from aqt.qt import Qt, QWidget, QAction, QMessageBox
from .sidebar import ReferenceSidebar
from .config import Config, ensure_config
from .manage import ManageDialog
from .prefs import PrefsDialog

addon_dir = Path(__file__).parent
config_path = addon_dir / "ref_images.json"
config: Config = ensure_config(config_path)

manage_act = mw.form.menuTools.addAction("Reference Images…")
manage_act.triggered.connect(lambda: ManageDialog(config).exec())
manage_act.setToolTip("Manage reference images")

sidebar = ReferenceSidebar(config, config_path)
mw.refimg_sidebar = sidebar  # store reference for manage dialog
try:
    RIGHT_AREA = Qt.DockWidgetArea.RightDockWidgetArea
except AttributeError:
    RIGHT_AREA = Qt.RightDockWidgetArea

mw.addDockWidget(RIGHT_AREA, sidebar)
sidebar.hide()

toggle_act = QAction("Reference Sidebar", mw)
toggle_act.setShortcut("Alt+R")
toggle_act.setToolTip("Show/hide reference images (Alt+R)\nOnly available in review mode")

def _toggle():
    # can only view it while reviewing
    if not hasattr(mw.reviewer, 'card') or not mw.reviewer.card:
        QMessageBox.information(mw, "Reference Images",
            "Reference images are only available during review.\n\n"
            "Please open a deck and start reviewing to use this feature.")
        toggle_act.setChecked(False)
        return

    vis = not sidebar.isVisible()
    sidebar.setVisible(vis)
    toggle_act.setChecked(vis)

toggle_act.setCheckable(True)
toggle_act.triggered.connect(_toggle)
mw.form.menuTools.addAction(toggle_act)

def on_reviewer_show(card):
    try:
        deck_id = str(card.did)
        print(f"[RefImg] showing deck {deck_id}")
        
        # Verify deck exists
        deck = mw.col.decks.get(int(deck_id))
        if not deck:
            print(f"[RefImg] error: deck {deck_id} not found")
            return

        images = config.deck_to_images.get(deck_id, [])
        media_dir = Path(mw.col.media.dir())
        if images:
            preferred = config.last_selected.get(deck_id, images[0]["fname"])
            img_path = media_dir / preferred
            print(f"[RefImg] showing image: {img_path}")
        else:
            img_path = None
            print(f"[RefImg] no images for deck {deck_id}")
        
        sidebar.show_image_for_deck(deck_id, img_path)
        if config.prefs["auto_show"]:
            sidebar.show()
    except Exception as e:
        print(f"[RefImg] error in on_reviewer_show: {e}")

def _save_vis():
    if config.prefs["remember_visibility"]:
        config.prefs["_last_visible"] = sidebar.isVisible()
        config.save()

sidebar.visibilityChanged.connect(lambda _: _save_vis())

# restore on profile load
if config.prefs["remember_visibility"] and config.prefs.get("_last_visible"):
    sidebar.show()

def on_reviewer_cleanup():

    sidebar.hide()
    toggle_act.setChecked(False)

gui_hooks.reviewer_did_show_question.append(on_reviewer_show)
gui_hooks.reviewer_will_end.append(on_reviewer_cleanup)

def on_profile_loaded():
    sidebar.reload_config()

def on_profile_open():
    sidebar.reload_config()

if hasattr(gui_hooks, "profile_did_open"):
    gui_hooks.profile_did_open.append(on_profile_open)
elif hasattr(gui_hooks, "profile_loaded"):
    gui_hooks.profile_loaded.append(on_profile_open)

prefs_act = mw.form.menuTools.addAction("Reference Sidebar Settings…")
prefs_act.triggered.connect(lambda: PrefsDialog(config).exec())