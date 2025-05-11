from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    path: Path
    deck_to_images: dict[str, list[dict]] = field(default_factory=dict)
    last_selected: dict[str, str] = field(default_factory=dict)  # deck_id → fname

    def load(self):
        data = json.loads(self.path.read_text("utf-8"))
        self.deck_to_images = data.get("deck_to_images", {})
        self.last_selected = data.get("last_selected", {})

    def save(self):
        data = {
            "version": 1,
            "deck_to_images": self.deck_to_images,
            "last_selected": self.last_selected,
        }
        self.path.write_text(json.dumps(data, indent=2), "utf-8")

def ensure_config(path: Path) -> Config:
    if not path.exists():
        path.write_text(json.dumps({
            "version": 1, 
            "deck_to_images": {},
            "last_selected": {}
        }, indent=2))
    cfg = Config(path)
    cfg.load()
    return cfg