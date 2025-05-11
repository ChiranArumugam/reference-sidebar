from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    path: Path
    deck_to_images: dict[str, list[dict]] = field(default_factory=dict)

    def load(self):
        data = json.loads(self.path.read_text("utf-8"))
        self.deck_to_images = data.get("deck_to_images", {})

    def save(self):
        data = {"version": 1, "deck_to_images": self.deck_to_images}
        self.path.write_text(json.dumps(data, indent=2), "utf-8")

def ensure_config(path: Path) -> Config:
    if not path.exists():
        path.write_text(json.dumps({"version": 1, "deck_to_images": {}}, indent=2))
    cfg = Config(path)
    cfg.load()
    return cfg