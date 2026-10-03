# A single square on the Minesweeper board


# One grid square
class Cell:

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
        self.is_mine = False
        self.is_decoy = False
        self.adjacent_mines = 0
        self.adjacent_decoys = 0
        self.is_revealed = False
        self.is_flagged = False

    # Plant or remove a flag on a hidden tile
    def toggle_flag(self) -> bool:
        if self.is_revealed:
            return False
        self.is_flagged = not self.is_flagged
        return True

    # Open a hidden, unflagged tile
    def reveal(self) -> bool:
        if self.is_revealed or self.is_flagged:
            return False
        self.is_revealed = True
        return True

    # Mines plus decoys nearby (the number shown)
    @property
    def total_adjacent(self) -> int:
        return self.adjacent_mines + self.adjacent_decoys
