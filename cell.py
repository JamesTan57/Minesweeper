"""A single square on the Minesweeper board."""


class Cell:
    """One grid square: real mine, decoy, counts, and whether the player opened or flagged it."""

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
        self.is_mine = False
        self.is_decoy = False
        self.adjacent_mines = 0
        self.adjacent_decoys = 0
        self.is_revealed = False
        self.is_flagged = False

    def toggle_flag(self) -> bool:
        """Plant or remove a flag on a hidden tile."""
        if self.is_revealed:
            return False
        self.is_flagged = not self.is_flagged
        return True

    def reveal(self) -> bool:
        """Open a hidden, unflagged tile."""
        if self.is_revealed or self.is_flagged:
            return False
        self.is_revealed = True
        return True
