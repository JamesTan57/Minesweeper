"""Grid logic: mines, decoys, flood fill, win/lose."""

from __future__ import annotations

import random
from enum import Enum, auto

from cell import Cell
from constants import MAX_SIZE, MIN_SIZE


class GameStatus(Enum):
    """High-level match state used by drawing and input."""

    PLAYING = auto()
    WON = auto()
    LOST = auto()


class Board:
    """The grid. Mines and decoys land after the first click so that click is always a free opening."""

    def __init__(self, rows: int, cols: int, mine_count: int, decoy_count: int = 0):
        self.rows = self._clamp_size(rows)
        self.cols = self._clamp_size(cols)
        self.mine_count = self._clamp_mines(mine_count)
        self.decoy_count = self._clamp_decoys(decoy_count)
        self.cells: list[list[Cell]] = [
            [Cell(r, c) for c in range(self.cols)] for r in range(self.rows)
        ]
        self.status = GameStatus.PLAYING
        self.mines_placed = False
        self.flags_placed = 0

    @staticmethod
    def _clamp_size(value: int) -> int:
        """Keep the board inside the allowed size range."""
        return max(MIN_SIZE, min(MAX_SIZE, int(value)))

    def _clamp_mines(self, mine_count: int) -> int:
        """Leave at least one safe cell so the first click can never be a mine."""
        max_mines = self.rows * self.cols - 1
        return max(1, min(max_mines, int(mine_count)))

    def _clamp_decoys(self, decoy_count: int) -> int:
        """Decoys fill leftover cells after mines and the freebie opening."""
        leftover = self.rows * self.cols - 1 - self.mine_count
        return max(0, min(leftover, int(decoy_count)))

    def cell_at(self, row: int, col: int) -> Cell | None:
        """Look up a cell, or None if the coordinate is off the board."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    def neighbors(self, row: int, col: int) -> list[Cell]:
        """The up-to-eight squares touching this one."""
        nearby: list[Cell] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                cell = self.cell_at(row + dr, col + dc)
                if cell is not None:
                    nearby.append(cell)
        return nearby

    def remaining_mines(self) -> int:
        """Mines still unflagged, shown in the header."""
        return self.mine_count - self.flags_placed

    def toggle_flag(self, row: int, col: int) -> None:
        """Right-click: flag or unflag while the match is still going."""
        if self.status is not GameStatus.PLAYING:
            return
        cell = self.cell_at(row, col)
        if cell is None or cell.is_revealed:
            return
        if cell.toggle_flag():
            self.flags_placed += 1 if cell.is_flagged else -1

    def reveal(self, row: int, col: int) -> list[Cell]:
        """Left-click: open a tile, flood empties, or trip a real mine. Returns newly opened cells."""
        opened: list[Cell] = []
        if self.status is not GameStatus.PLAYING:
            return opened
        cell = self.cell_at(row, col)
        if cell is None or cell.is_flagged or cell.is_revealed:
            return opened

        if not self.mines_placed:
            self._place_mines(safe_row=row, safe_col=col)

        if not cell.reveal():
            return opened
        opened.append(cell)

        if cell.is_mine:
            opened.extend(self._reveal_all_mines())
            self.status = GameStatus.LOST
            return opened

        if not cell.is_decoy and cell.adjacent_mines == 0:
            opened.extend(self._flood_fill(cell))

        self._check_win()
        return opened

    def _place_mines(self, safe_row: int, safe_col: int) -> None:
        """Drop mines and decoys, keeping the first click and its neighbors empty so it floods."""
        opening = {(safe_row, safe_col)}
        for neighbor in self.neighbors(safe_row, safe_col):
            opening.add((neighbor.row, neighbor.col))

        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in opening
        ]
        needed = self.mine_count + self.decoy_count
        if len(candidates) < needed:
            candidates = [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) != (safe_row, safe_col)
            ]
            extra = max(0, len(candidates) - self.mine_count)
            self.decoy_count = min(self.decoy_count, extra)

        spots = random.sample(candidates, self.mine_count + self.decoy_count)
        for r, c in spots[: self.mine_count]:
            self.cells[r][c].is_mine = True
        for r, c in spots[self.mine_count :]:
            self.cells[r][c].is_decoy = True

        self._clear_opening(safe_row, safe_col)
        self._recount_neighbors()
        self.mines_placed = True

    def _clear_opening(self, safe_row: int, safe_col: int) -> None:
        """Move any mine/decoy off the first-click pocket so that break is always a free empty flood."""
        pocket = [self.cells[safe_row][safe_col], *self.neighbors(safe_row, safe_col)]
        parked = {(c.row, c.col) for c in pocket}
        free = [
            self.cells[r][c]
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in parked and not self.cells[r][c].is_mine and not self.cells[r][c].is_decoy
        ]
        random.shuffle(free)
        for cell in pocket:
            if not (cell.is_mine or cell.is_decoy) or not free:
                cell.is_mine = False
                cell.is_decoy = False
                continue
            dest = free.pop()
            dest.is_mine = cell.is_mine
            dest.is_decoy = cell.is_decoy
            cell.is_mine = False
            cell.is_decoy = False

    def _recount_neighbors(self) -> None:
        """Numbers count real mines only; adjacent_decoys drives the corner ? hint."""
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                nearby = self.neighbors(r, c)
                cell.adjacent_mines = sum(1 for n in nearby if n.is_mine)
                cell.adjacent_decoys = sum(1 for n in nearby if n.is_decoy)

    def _flood_fill(self, start: Cell) -> list[Cell]:
        """Open the connected empty region, stopping at numbers, flags, mines, and decoys."""
        opened: list[Cell] = []
        stack = [start]
        seen = {(start.row, start.col)}
        while stack:
            current = stack.pop()
            if current.adjacent_mines != 0:
                continue
            for neighbor in self.neighbors(current.row, current.col):
                key = (neighbor.row, neighbor.col)
                if key in seen or neighbor.is_flagged or neighbor.is_mine or neighbor.is_decoy:
                    continue
                seen.add(key)
                if neighbor.reveal():
                    opened.append(neighbor)
                if neighbor.adjacent_mines == 0:
                    stack.append(neighbor)
        return opened

    def _reveal_all_mines(self) -> list[Cell]:
        """On a loss, uncover every real bomb and leftover decoy."""
        opened: list[Cell] = []
        for row in self.cells:
            for cell in row:
                if cell.is_mine or cell.is_decoy:
                    was_hidden = not cell.is_revealed
                    cell.is_revealed = True
                    cell.is_flagged = False
                    if was_hidden:
                        opened.append(cell)
        return opened

    def _check_win(self) -> None:
        """Win when every non-mine tile (including decoys) is open; auto-flag remaining mines."""
        for row in self.cells:
            for cell in row:
                if not cell.is_mine and not cell.is_revealed:
                    return
        self.status = GameStatus.WON
        for row in self.cells:
            for cell in row:
                if cell.is_mine and not cell.is_flagged:
                    cell.is_flagged = True
                    self.flags_placed += 1
