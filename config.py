from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any

@dataclass
class Config:
    path: Path
    deck_to_images: Dict[str, List[Dict]] = field(default_factory=dict)
    last_selected: Dict[str, str] = field(default_factory=dict)  # deck_id → fname
    prefs: Dict[str, Any] = field(default_factory=lambda: {
        "auto_show": True,
        "default_zoom": 1.0,
        "sidebar_width": 220,
        "remember_visibility": True,
    })

    def load(self):
        try:
            if not self.path.exists():
                print(f"[RefImg] config file not found at {self.path}, creating new one")
                self.save()
                return

            data = json.loads(self.path.read_text("utf-8"))
            # Initialize with empty dicts if missing
            self.deck_to_images = data.get("deck_to_images", {})
            self.last_selected = data.get("last_selected", {})
            self.prefs.update(data.get("prefs", {}))  # keep defaults for new keys
            print("[RefImg] loaded config from", self.path)
        except Exception as e:
            print("[RefImg] error loading config:", e)
            # Ensure we have valid dicts even if load fails
            self.deck_to_images = {}
            self.last_selected = {}

    def save(self):
        try:
            # Ensure parent directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "version": 1,
                "deck_to_images": self.deck_to_images,
                "last_selected": self.last_selected,
                "prefs": self.prefs,
            }
            # Write to a temporary file first
            temp_path = self.path.with_suffix('.tmp')
            temp_path.write_text(json.dumps(data, indent=2), "utf-8")
            
            # Then rename it to the actual file (atomic operation)
            temp_path.replace(self.path)
            
            print("[RefImg] saved config to", self.path)
        except Exception as e:
            print("[RefImg] error saving config:", e)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

    def ensure_deck_list(self, deck_id: str) -> List[Dict]:
        """Get or create the image list for a deck."""
        if deck_id not in self.deck_to_images:
            print(f"[RefImg] creating new image list for deck {deck_id}")
            self.deck_to_images[deck_id] = []
        return self.deck_to_images[deck_id]

def ensure_config(path: Path) -> Config:
    try:
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if not path.exists():
            print(f"[RefImg] creating new config at {path}")
            # Write to a temporary file first
            temp_path = path.with_suffix('.tmp')
            temp_path.write_text(json.dumps({
                "version": 1, 
                "deck_to_images": {},
                "last_selected": {},
                "prefs": {}
            }, indent=2))
            # Then rename it to the actual file (atomic operation)
            temp_path.replace(path)
        
        cfg = Config(path)
        cfg.load()
        return cfg
    except Exception as e:
        print("[RefImg] error ensuring config:", e)
        # Return a valid config even if file operations fail
        return Config(path)