from __future__ import annotations
from pathlib import Path
from typing import List

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QAbstractItemView, QComboBox, Qt, QFileIconProvider, QIcon,
    QMessageBox, QInputDialog,
)

icon_provider = QFileIconProvider()


class ManageDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Manage Reference Images")
        self._cfg = cfg

        self._deck_filter = QComboBox()
        self._deck_filter.currentIndexChanged.connect(self._refresh_table)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["", "File", "Deck"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected)

        move_btn = QPushButton("Re-assign Deck")
        move_btn.clicked.connect(self._move_selected)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(move_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._deck_filter)
        layout.addWidget(self._table)
        layout.addLayout(btn_row)

        self._populate_deck_filter()
        self._refresh_table()

    # ---------- GUI helpers -------------------------------------------------
    def _populate_deck_filter(self):
        self._deck_filter.addItem("All Decks", None)
        for did in self._cfg.deck_to_images.keys():
            deck = mw.col.decks.get(int(did))
            name = deck.name if hasattr(deck, 'name') else deck["name"]  # handle both old and new API
            self._deck_filter.addItem(name, did)

    def _refresh_table(self):
        deck_filter = self._deck_filter.currentData()
        self._table.setRowCount(0)

        for did, images in self._cfg.deck_to_images.items():
            if deck_filter and did != deck_filter:
                continue
            deck = mw.col.decks.get(int(did))
            deck_name = deck.name if hasattr(deck, 'name') else deck["name"]  # handle both old and new API
            for entry in images:
                row = self._table.rowCount()
                self._table.insertRow(row)

                # cross-Qt: File icon enum moved in Qt6
                try:
                    FILE_ICON = QFileIconProvider.IconType.File
                except AttributeError:  # Qt5
                    FILE_ICON = QFileIconProvider.File
                icon = icon_provider.icon(FILE_ICON)

                self._table.setItem(row, 0, QTableWidgetItem(icon, ""))  # placeholder icon
                self._table.setItem(row, 1, QTableWidgetItem(entry["fname"]))
                self._table.setItem(row, 2, QTableWidgetItem(deck_name))
                # stash ids for later
                for col in range(3):
                    self._table.item(row, col).setData(Qt.ItemDataRole.UserRole, (did, entry["fname"]))

    def _selected_items(self) -> List[tuple[str, str]]:
        rows = {idx.row() for idx in self._table.selectionModel().selectedRows()}
        items: List[tuple[str, str]] = []
        for r in rows:
            did, fname = self._table.item(r, 1).data(Qt.ItemDataRole.UserRole)
            items.append((did, fname))
        return items

    # ---------- actions -----------------------------------------------------
    def _delete_selected(self):
        sel = self._selected_items()
        if not sel:
            return
        if QMessageBox.question(self, "Confirm", f"Delete {len(sel)} image(s)?") != QMessageBox.StandardButton.Yes:
            return
        for did, fname in sel:
            deck_list = self._cfg.deck_to_images[did]
            deck_list[:] = [e for e in deck_list if e["fname"] != fname]
            if not deck_list:
                self._cfg.deck_to_images.pop(did)
            # remove media if truly unused
            still_used = any(
                fname == e["fname"]
                for deck_list in self._cfg.deck_to_images.values()
                for e in deck_list
            )
            if not still_used:
                try:
                    mw.col.media.trash_files([fname])
                except Exception as e:
                    print("[RefImg] media remove failed:", e)
            # clean last_selected
            if self._cfg.last_selected.get(did) == fname:
                self._cfg.last_selected.pop(did, None)
        self._cfg.save()
        self._refresh_table()

    def _move_selected(self):
        sel = self._selected_items()
        if not sel:
            return
        # pick target deck
        name_id_pairs = mw.col.decks.all_names_and_ids()          # returns DeckNameId objects
        all_deck_ids   = [str(d.id)   for d in name_id_pairs]
        all_deck_names = [d.name      for d in name_id_pairs]
        target, ok = QInputDialog.getItem(self, "Move to Deck", "Deck:", all_deck_names, editable=False)
        if not ok:
            return
        target_id = all_deck_ids[all_deck_names.index(target)]
        for did, fname in sel:
            # remove from old
            self._cfg.deck_to_images[did] = [e for e in self._cfg.deck_to_images[did] if e["fname"] != fname]
            # add to new
            self._cfg.deck_to_images.setdefault(target_id, []).append({"fname": fname, "title": Path(fname).stem})
            if not self._cfg.deck_to_images[did]:
                self._cfg.deck_to_images.pop(did, None)
            if self._cfg.last_selected.get(did) == fname:
                self._cfg.last_selected.pop(did, None)
        self._cfg.save()
        self._refresh_table()
