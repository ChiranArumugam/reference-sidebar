from __future__ import annotations
import json
from pathlib import Path
from aqt import mw, gui_hooks
from aqt.qt import Qt, QWidget
from .sidebar import ReferenceSidebar
from .config import Config, ensure_config

addon_dir = Path(__file__).parent
config_path = addon_dir / "ref_images.json"
config: Config = ensure_config(config_path)

sidebar = ReferenceSidebar(config, config_path)
try:
    RIGHT_AREA = Qt.DockWidgetArea.RightDockWidgetArea
except AttributeError:
    RIGHT_AREA = Qt.RightDockWidgetArea

mw.addDockWidget(RIGHT_AREA, sidebar)
sidebar.hide()

def on_reviewer_show(card):
    deck_id = str(card.did)
    images = config.deck_to_images.get(deck_id, [])
    media_dir = Path(mw.col.media.dir())
    if images:
        img_path = media_dir / images[0]["fname"]
    else:
        img_path = None
    sidebar.show_image_for_deck(deck_id, img_path)
    sidebar.show()

gui_hooks.reviewer_did_show_question.append(on_reviewer_show)

def on_profile_loaded():
    sidebar.reload_config()

def on_profile_open():
    sidebar.reload_config()

if hasattr(gui_hooks, "profile_did_open"):
    gui_hooks.profile_did_open.append(on_profile_open)
elif hasattr(gui_hooks, "profile_loaded"):
    gui_hooks.profile_loaded.append(on_profile_open)