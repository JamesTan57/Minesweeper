# Grid logic: mines, decoys, flood fill, win/lose

from __future__ import annotations

import random
from enum import Enum, auto

from cell import Cell
from constants import MAX_SIZE, MIN_SIZE


# High-level match state used by drawing and input
class GameStatus(Enum):

    PLAYING = auto()
    WON = auto()
    LOST = auto()


# The grid; mines and decoys are placed after the first click
class Board:

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

    # Keep the board inside the allowed size range
    @staticmethod
    def _clamp_size(value: int) -> int:
        return max(MIN_SIZE, min(MAX_SIZE, int(value)))

    # Keeps at least one safe cell for the first click
    def _clamp_mines(self, mine_count: int) -> int:
        max_mines = self.rows * self.cols - 1
        return max(1, min(max_mines, int(mine_count)))

    # Limits decoys to the leftover cells
    def _clamp_decoys(self, decoy_count: int) -> int:
        leftover = self.rows * self.cols - 1 - self.mine_count
        return max(0, min(leftover, int(decoy_count)))

    # Gets a cell, or None if off the board
    def cell_at(self, row: int, col: int) -> Cell | None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    # The up-to-eight squares touching this one
    def neighbors(self, row: int, col: int) -> list[Cell]:
        nearby: list[Cell] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                cell = self.cell_at(row + dr, col + dc)
                if cell is not None:
                    nearby.append(cell)
        return nearby

    # Mines still unflagged, shown in the header
    def remaining_mines(self) -> int:
        return self.mine_count - self.flags_placed

    # Toggles a flag on a hidden tile
    def toggle_flag(self, row: int, col: int) -> None:
        if self.status is not GameStatus.PLAYING:
            return
        cell = self.cell_at(row, col)
        if cell is None or cell.is_revealed:
            return
        if cell.toggle_flag():
            self.flags_placed += 1 if cell.is_flagged else -1

    # Reveals a tile and returns the newly opened cells
    def reveal(self, row: int, col: int) -> list[Cell]:
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

        if not cell.is_decoy and cell.total_adjacent == 0:
            opened.extend(self._flood_fill(cell))

        self._check_win()
        return opened

    # Places mines and decoys, keeping the first click's area clear
    def _place_mines(self, safe_row: int, safe_col: int) -> None:
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

    # Moves any mine or decoy out of the first-click area
    def _clear_opening(self, safe_row: int, safe_col: int) -> None:
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

    # Counts nearby mines and decoys for every cell
    def _recount_neighbors(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                nearby = self.neighbors(r, c)
                cell.adjacent_mines = sum(1 for n in nearby if n.is_mine)
                cell.adjacent_decoys = sum(1 for n in nearby if n.is_decoy)

    # Opens connected empty tiles, stopping at numbers
    def _flood_fill(self, start: Cell) -> list[Cell]:
        opened: list[Cell] = []
        stack = [start]
        seen = {(start.row, start.col)}
        while stack:
            current = stack.pop()
            if current.total_adjacent != 0:
                continue
            for neighbor in self.neighbors(current.row, current.col):
                key = (neighbor.row, neighbor.col)
                if key in seen or neighbor.is_flagged or neighbor.is_mine or neighbor.is_decoy:
                    continue
                seen.add(key)
                if neighbor.reveal():
                    opened.append(neighbor)
                if neighbor.total_adjacent == 0:
                    stack.append(neighbor)
        return opened

    # On a loss, uncover every real bomb and leftover decoy
    def _reveal_all_mines(self) -> list[Cell]:
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

    # Wins when every non-mine tile is open, then flags the mines
    def _check_win(self) -> None:
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
