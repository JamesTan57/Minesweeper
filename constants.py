"""Shared layout, colors, and game limits for Minesweeper."""

# Grid generation
MIN_SIZE = 5
MAX_SIZE = 30
DEFAULT_ROWS = 9
DEFAULT_COLS = 9
DEFAULT_MINES = 10
DEFAULT_DECOYS = 3

# Window / cells
CELL_SIZE = 32
HEADER_HEIGHT = 88
MARGIN = 24
MIN_CELL_SIZE = 28
MAX_CELL_SIZE = 72

# Animation timings for tile cracks, mine ripple, and decoy splat
BREAK_MS = 320
BREAK_STAGGER_MS = 38
MINE_STAGGER_MS = 28
SPLAT_MS = 420

# Colors
BG = (34, 92, 38)
HEADER_BG = (28, 42, 28, 210)
PANEL = (48, 72, 42)
TEXT = (245, 246, 232)
MUTED = (196, 210, 170)
HIDDEN = (86, 138, 52)
HIDDEN_TOP = (118, 168, 72)
HIDDEN_BORDER = (48, 92, 36)
DIRT = (166, 124, 78)
DIRT_DARK = (132, 96, 58)
MINE_BG = (168, 58, 48)
DECOY_BG = (186, 154, 72)
FLAG_RED = (214, 54, 48)
FLAG_POLE = (62, 44, 28)
ACCENT = (92, 148, 72)
DANGER = (214, 86, 70)
WIN = (186, 220, 120)
INPUT_BG = (32, 58, 34)
INPUT_ACTIVE = (48, 86, 50)
BOMB_BODY = (28, 26, 24)
BOMB_GLOSS = (70, 68, 64)
DECOY_BOMB = (248, 250, 252)
DECOY_BOMB_EDGE = (190, 198, 210)
DECOY_GLOSS = (255, 255, 255)
SPLAT_COLORS = ((248, 250, 252), (220, 226, 236), (186, 196, 210), (255, 255, 255))
HINT = (90, 40, 140)
TAB_BG = (36, 64, 38)
TAB_ACTIVE = (68, 118, 58)

# Setup-screen rules copy
RULES = [
    "Clear every safe tile. Do not click a real bomb.",
    "Left click opens a tile. Right click (or Ctrl+click) plants a flag.",
    "The number is how many real bombs touch that tile.",
    "A ? in the top-right corner means a decoy bomb is next door.",
    "Your first click is always a free opening — mines are placed after it.",
    "White bombs are decoys: they splat and do not end the game. You still must open them.",
    "Dark bombs are real. Hit one and every bomb on the board is shown.",
    "Flag the bombs you have found. Open every non-bomb tile to win.",
    "F11 toggles fullscreen. Esc or New Game returns to this menu.",
]

GRASS_BASE = (46, 112, 44)
GRASS_DARK = (34, 88, 34)
GRASS_LIGHT = (78, 148, 58)
GRASS_BLADE = (58, 132, 48)

# Adjacent-mine number colors (1–8)
NUMBER_COLORS = {
    1: (40, 80, 180),
    2: (36, 110, 48),
    3: (180, 40, 36),
    4: (90, 40, 150),
    5: (130, 40, 36),
    6: (20, 120, 120),
    7: (24, 24, 24),
    8: (70, 70, 70),
}
