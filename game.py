"""Pygame screens: size setup, drawing, and mouse input."""

from __future__ import annotations

import pygame

from board import Board, GameStatus
from constants import (
    ACCENT,
    BREAK_MS,
    BREAK_STAGGER_MS,
    DANGER,
    DEFAULT_COLS,
    DEFAULT_DECOYS,
    DEFAULT_MINES,
    DEFAULT_ROWS,
    HEADER_BG,
    HEADER_HEIGHT,
    INPUT_ACTIVE,
    INPUT_BG,
    MARGIN,
    MAX_CELL_SIZE,
    MAX_SIZE,
    MIN_CELL_SIZE,
    MIN_SIZE,
    MINE_STAGGER_MS,
    MUTED,
    NUMBER_COLORS,
    PANEL,
    RULES,
    SPLAT_MS,
    TAB_ACTIVE,
    TAB_BG,
    TEXT,
    WIN,
)
from graphics import (
    Splat,
    TileBreak,
    draw_bomb,
    draw_decoy_hint,
    draw_dirt,
    draw_flag,
    draw_sod,
    make_grass,
)


class InputField:
    """Click-to-focus box for typing a number on the setup screen."""

    def __init__(self, label: str, value: int):
        self.label = label
        self.text = str(value)
        self.rect = pygame.Rect(0, 0, 140, 48)
        self.active = False

    def place(self, x: int, y: int, width: int = 140) -> None:
        """Move this field when the window is laid out."""
        self.rect = pygame.Rect(x, y, width, 48)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Focus on click; digits and backspace while focused."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active or event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.unicode.isdigit() and len(self.text) < 3:
            self.text += event.unicode

    def value(self, fallback: int, lo: int, hi: int) -> int:
        """Parse the typed number and clamp it."""
        try:
            parsed = int(self.text) if self.text else fallback
        except ValueError:
            parsed = fallback
        return max(lo, min(hi, parsed))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw the label and current value."""
        color = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT if self.active else MUTED, self.rect, 2, border_radius=8)
        label = font.render(self.label, True, MUTED)
        surface.blit(label, (self.rect.x, self.rect.y - 28))
        value = font.render(self.text or "_", True, TEXT)
        surface.blit(value, (self.rect.x + 14, self.rect.y + 12))


class Game:
    """Window, menu tabs, board play, and animations."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Minesweeper")
        self.clock = pygame.time.Clock()
        self.fullscreen = True
        self.screen = self._open_display()
        self.running = True
        self.on_setup = True
        self.setup_tab = "play"
        self.show_rules = False
        self.board: Board | None = None
        self.message = "Choose a grid, then generate."
        self.breaks: dict[tuple[int, int], TileBreak] = {}
        self.splats: dict[tuple[int, int], Splat] = {}
        self.grass: pygame.Surface | None = None
        self.cell_size = 40
        self.grid_origin = (MARGIN, HEADER_HEIGHT)
        self.row_field = InputField("Rows", DEFAULT_ROWS)
        self.col_field = InputField("Columns", DEFAULT_COLS)
        self.mine_field = InputField("Mines", DEFAULT_MINES)
        self.decoy_field = InputField("Decoys", DEFAULT_DECOYS)
        self.generate_rect = pygame.Rect(0, 0, 220, 52)
        self.new_game_rect = pygame.Rect(0, 0, 140, 36)
        self.rules_button_rect = pygame.Rect(0, 0, 100, 36)
        self.play_tab_rect = pygame.Rect(0, 0, 180, 40)
        self.rules_tab_rect = pygame.Rect(0, 0, 180, 40)
        self._refresh_fonts()
        self._layout()

    def _open_display(self) -> pygame.Surface:
        """Fullscreen by default; F11 flips to a resizable window."""
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        size = (0, 0) if self.fullscreen else (1100, 720)
        return pygame.display.set_mode(size, flags)

    def _refresh_fonts(self) -> None:
        """Scale number and hint fonts to the current tile size."""
        size = max(16, self.cell_size * 2 // 5)
        self.font = pygame.font.SysFont("menlo", 22)
        self.small_font = pygame.font.SysFont("menlo", 16)
        self.number_font = pygame.font.SysFont("menlo", size, bold=True)
        self.hint_font = pygame.font.SysFont("menlo", max(12, size - 4), bold=True)

    def _layout(self) -> None:
        """Place tabs, fields, and the grid after a resize or screen change."""
        width, height = self.screen.get_size()
        if self.grass is None or self.grass.get_size() != (width, height):
            self.grass = make_grass(width, height)
        tab_y = max(40, height // 2 - 220)
        self.play_tab_rect = pygame.Rect(width // 2 - 200, tab_y, 180, 40)
        self.rules_tab_rect = pygame.Rect(width // 2 + 20, tab_y, 180, 40)
        if self.board is None:
            field_w = 150
            gap = 24
            total = field_w * 4 + gap * 3
            left = (width - total) // 2
            y = height // 2 - 10
            self.row_field.place(left, y, field_w)
            self.col_field.place(left + field_w + gap, y, field_w)
            self.mine_field.place(left + (field_w + gap) * 2, y, field_w)
            self.decoy_field.place(left + (field_w + gap) * 3, y, field_w)
            self.generate_rect = pygame.Rect((width - 220) // 2, y + 90, 220, 52)
            return
        available_w = width - MARGIN * 2
        available_h = height - HEADER_HEIGHT - MARGIN
        self.cell_size = max(
            MIN_CELL_SIZE,
            min(MAX_CELL_SIZE, available_w // self.board.cols, available_h // self.board.rows),
        )
        grid_w = self.board.cols * self.cell_size
        grid_h = self.board.rows * self.cell_size
        origin_x = (width - grid_w) // 2
        origin_y = HEADER_HEIGHT + max(0, (available_h - grid_h) // 2)
        self.grid_origin = (origin_x, origin_y)
        self.new_game_rect = pygame.Rect(width - MARGIN - 140, 26, 140, 36)
        self.rules_button_rect = pygame.Rect(width - MARGIN - 250, 26, 100, 36)
        self._refresh_fonts()

    def run(self) -> None:
        """Main loop: events, draw, cap at 60 FPS."""
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Quit, resize, fullscreen toggle, then setup or play."""
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            self._layout()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.fullscreen = not self.fullscreen
            self.screen = self._open_display()
            self._layout()
            return
        if self.on_setup:
            self._handle_setup_event(event)
            return
        self._handle_play_event(event)

    def _handle_setup_event(self, event: pygame.event.Event) -> None:
        """Tabs, number fields, and Generate / Enter to start."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_tab_rect.collidepoint(event.pos):
                self.setup_tab = "play"
                return
            if self.rules_tab_rect.collidepoint(event.pos):
                self.setup_tab = "rules"
                return
            if self.setup_tab == "play" and self.generate_rect.collidepoint(event.pos):
                self._start_game()
                return
        if self.setup_tab != "play":
            return
        self.row_field.handle_event(event)
        self.col_field.handle_event(event)
        self.mine_field.handle_event(event)
        self.decoy_field.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._start_game()

    def _start_game(self) -> None:
        """Build a board from the setup fields and switch to play."""
        rows = self.row_field.value(DEFAULT_ROWS, MIN_SIZE, MAX_SIZE)
        cols = self.col_field.value(DEFAULT_COLS, MIN_SIZE, MAX_SIZE)
        mines = self.mine_field.value(DEFAULT_MINES, 1, rows * cols - 1)
        decoys = self.decoy_field.value(DEFAULT_DECOYS, 0, max(0, rows * cols - 1 - mines))
        self.row_field.text = str(rows)
        self.col_field.text = str(cols)
        self.mine_field.text = str(mines)
        self.decoy_field.text = str(decoys)
        self.board = Board(rows, cols, mines, decoys)
        self.breaks.clear()
        self.splats.clear()
        self.on_setup = False
        self.show_rules = False
        self.message = "Left click reveal · Right click flag · first click is free"
        self._layout()

    def _handle_play_event(self, event: pygame.event.Event) -> None:
        """Header buttons, tile clicks, Esc back to menu."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.new_game_rect.collidepoint(event.pos):
                self._return_to_setup()
                return
            if self.rules_button_rect.collidepoint(event.pos):
                self.show_rules = not self.show_rules
                return
            if self.show_rules:
                self.show_rules = False
                return
            if event.button in (1, 3):
                flag = event.button == 3 or bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
                self._handle_click(event.pos, flag=flag)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.show_rules:
                self.show_rules = False
                return
            self._return_to_setup()

    def _return_to_setup(self) -> None:
        """Leave the current board and open the menu again."""
        self.on_setup = True
        self.setup_tab = "play"
        self.show_rules = False
        self.board = None
        self.breaks.clear()
        self.splats.clear()
        self.message = "Choose a grid, then generate."
        self._layout()

    def _handle_click(self, pos: tuple[int, int], flag: bool) -> None:
        """Flag or reveal the tile under the cursor."""
        if self.board is None or self.board.status is not GameStatus.PLAYING:
            return
        cell = self._cell_from_pos(pos)
        if cell is None:
            return
        if flag:
            self.board.toggle_flag(cell.row, cell.col)
            self._sync_status_message()
            return
        opened = self.board.reveal(cell.row, cell.col)
        self._queue_breaks(opened, cell.row, cell.col)
        self._sync_status_message()

    def _queue_breaks(self, opened, origin_row: int, origin_col: int) -> None:
        """Stagger tile cracks from the click; decoys also get a splat."""
        now = pygame.time.get_ticks()
        lost = self.board is not None and self.board.status is GameStatus.LOST
        for cell in opened:
            dist = abs(cell.row - origin_row) + abs(cell.col - origin_col)
            stagger = MINE_STAGGER_MS if lost and cell.is_mine else BREAK_STAGGER_MS
            delay = dist * stagger
            rect = self._cell_rect(cell.row, cell.col)
            self.breaks[(cell.row, cell.col)] = TileBreak(rect, now + delay, BREAK_MS)
            if cell.is_decoy:
                self.splats[(cell.row, cell.col)] = Splat(rect, now + delay + 40, SPLAT_MS)

    def _cell_from_pos(self, pos: tuple[int, int]):
        """Map a mouse point onto a board cell."""
        if self.board is None:
            return None
        x, y = pos
        ox, oy = self.grid_origin
        grid_x = x - ox
        grid_y = y - oy
        if grid_x < 0 or grid_y < 0:
            return None
        col = grid_x // self.cell_size
        row = grid_y // self.cell_size
        return self.board.cell_at(row, col)

    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        """Pixel box for one tile, with a small grass gap."""
        ox, oy = self.grid_origin
        pad = max(1, self.cell_size // 16)
        return pygame.Rect(
            ox + col * self.cell_size + pad,
            oy + row * self.cell_size + pad,
            self.cell_size - pad * 2,
            self.cell_size - pad * 2,
        )

    def _sync_status_message(self) -> None:
        """Header hint after each action."""
        if self.board is None:
            return
        if self.board.status is GameStatus.WON:
            self.message = "You cleared the board. New Game to play again."
        elif self.board.status is GameStatus.LOST:
            self.message = "That was a real mine. White bombs were decoys."
        else:
            self.message = "Left click reveal · Right click flag · ? means a decoy is adjacent"

    def _draw(self) -> None:
        """Grass, then either the menu or the live board."""
        if self.grass is not None:
            self.screen.blit(self.grass, (0, 0))
        else:
            self.screen.fill((34, 92, 38))
        if self.on_setup:
            self._draw_setup()
            return
        self._draw_header()
        self._draw_board()
        if self.show_rules:
            self._draw_rules_panel()

    def _draw_tab(self, rect: pygame.Rect, label: str, active: bool) -> None:
        """One Play / Rules tab button."""
        pygame.draw.rect(self.screen, TAB_ACTIVE if active else TAB_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT if active else MUTED, rect, 2, border_radius=8)
        text = self.font.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_setup(self) -> None:
        """Menu: Play tab for settings, Rules tab for how to play."""
        width, height = self.screen.get_size()
        title = self.font.render("Minesweeper", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(width // 2, max(36, self.play_tab_rect.y - 48))))
        self._draw_tab(self.play_tab_rect, "Play", self.setup_tab == "play")
        self._draw_tab(self.rules_tab_rect, "Rules", self.setup_tab == "rules")
        if self.setup_tab == "rules":
            self._draw_rules_panel()
            return
        hint = self.small_font.render(
            f"Grid {MIN_SIZE}–{MAX_SIZE}. First click is always a free opening. F11 fullscreen.",
            True,
            MUTED,
        )
        self.screen.blit(hint, hint.get_rect(center=(width // 2, self.play_tab_rect.bottom + 36)))
        self.row_field.draw(self.screen, self.small_font)
        self.col_field.draw(self.screen, self.small_font)
        self.mine_field.draw(self.screen, self.small_font)
        self.decoy_field.draw(self.screen, self.small_font)
        pygame.draw.rect(self.screen, ACCENT, self.generate_rect, border_radius=10)
        label = self.font.render("Generate", True, TEXT)
        self.screen.blit(label, label.get_rect(center=self.generate_rect.center))
        footer = self.small_font.render(self.message, True, MUTED)
        self.screen.blit(footer, footer.get_rect(center=(width // 2, self.generate_rect.bottom + 40)))

    def _draw_rules_panel(self) -> None:
        """Centered card listing how mines, flags, numbers, and decoys work."""
        width, height = self.screen.get_size()
        card = pygame.Rect(width // 2 - 360, height // 2 - 200, 720, 420)
        if self.on_setup:
            card.y = self.play_tab_rect.bottom + 24
        panel = pygame.Surface(card.size, pygame.SRCALPHA)
        panel.fill((24, 40, 26, 230))
        self.screen.blit(panel, card.topleft)
        pygame.draw.rect(self.screen, ACCENT, card, 2, border_radius=10)
        heading = self.font.render("How to play", True, TEXT)
        self.screen.blit(heading, (card.x + 28, card.y + 20))
        y = card.y + 64
        for line in RULES:
            item = self.small_font.render(f"•  {line}", True, TEXT)
            self.screen.blit(item, (card.x + 28, y))
            y += 34

    def _draw_header(self) -> None:
        """Top bar: mine count, decoys, status, Rules, New Game."""
        bar = pygame.Surface((self.screen.get_width(), HEADER_HEIGHT), pygame.SRCALPHA)
        bar.fill(HEADER_BG)
        self.screen.blit(bar, (0, 0))
        if self.board is None:
            return
        mines = self.font.render(f"Mines left: {self.board.remaining_mines()}", True, TEXT)
        decoys = self.small_font.render(f"Decoys: {self.board.decoy_count}", True, MUTED)
        status_color = TEXT
        if self.board.status is GameStatus.WON:
            status_color = WIN
        elif self.board.status is GameStatus.LOST:
            status_color = DANGER
        status = self.small_font.render(self.message, True, status_color)
        self.screen.blit(mines, (MARGIN, 18))
        self.screen.blit(decoys, (MARGIN + 220, 22))
        self.screen.blit(status, (MARGIN, 52))
        pygame.draw.rect(self.screen, PANEL, self.rules_button_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL, self.new_game_rect, border_radius=8)
        rules_label = self.small_font.render("Rules", True, TEXT)
        new_label = self.small_font.render("New Game", True, TEXT)
        self.screen.blit(rules_label, rules_label.get_rect(center=self.rules_button_rect.center))
        self.screen.blit(new_label, new_label.get_rect(center=self.new_game_rect.center))

    def _draw_board(self) -> None:
        """Each tile: sod while closed, dirt/bomb after, plus crack and splat overlays."""
        if self.board is None:
            return
        now = pygame.time.get_ticks()
        for key in [k for k, anim in self.breaks.items() if anim.done(now)]:
            self.breaks.pop(key)
        for key in [k for k, anim in self.splats.items() if anim.done(now)]:
            self.splats.pop(key)

        for row in self.board.cells:
            for cell in row:
                rect = self._cell_rect(cell.row, cell.col)
                anim = self.breaks.get((cell.row, cell.col))
                show_hidden = not cell.is_revealed or (anim is not None and anim.waiting(now))
                if show_hidden:
                    draw_sod(self.screen, rect)
                    if cell.is_flagged:
                        draw_flag(self.screen, rect)
                    continue
                self._draw_revealed(cell, rect)
                if anim is not None:
                    anim.draw(self.screen, rect, now)
                splat = self.splats.get((cell.row, cell.col))
                if splat is not None:
                    splat.draw(self.screen, rect, now)

    def _draw_revealed(self, cell, rect: pygame.Rect) -> None:
        """Opened contents: real bomb, white decoy, or number plus a corner ? if a decoy is adjacent."""
        if cell.is_mine:
            exploded = self.board is not None and self.board.status is GameStatus.LOST
            draw_bomb(self.screen, rect, exploded=exploded)
            return
        if cell.is_decoy:
            draw_bomb(self.screen, rect, decoy=True)
            return
        draw_dirt(self.screen, rect)
        if cell.adjacent_mines > 0:
            color = NUMBER_COLORS[cell.adjacent_mines]
            text = self.number_font.render(str(cell.adjacent_mines), True, color)
            self.screen.blit(text, text.get_rect(center=rect.center))
        if cell.adjacent_decoys > 0:
            draw_decoy_hint(self.screen, rect, self.hint_font)
