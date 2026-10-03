# Pygame screens, drawing, and input

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
    HIGHLIGHT,
    INPUT_ACTIVE,
    INPUT_BG,
    LEADERBOARD_SIZE,
    LOSS_MENU_DELAY_MS,
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
    WIN_MENU_DELAY_MS,
)
from graphics import (
    Splat,
    TileBreak,
    draw_bomb,
    draw_clock,
    draw_decoy_hint,
    draw_dirt,
    draw_flag,
    draw_sod,
    make_grass,
)
from leaderboard import Leaderboard, config_key, format_time, key_label


# Click-to-focus box for typing a number on the setup screen
class InputField:

    def __init__(self, label: str, value: int):
        self.label = label
        self.text = str(value)
        self.rect = pygame.Rect(0, 0, 140, 48)
        self.active = False

    # Move this field when the window is laid out
    def place(self, x: int, y: int, width: int = 140) -> None:
        self.rect = pygame.Rect(x, y, width, 48)

    # Focus on click; digits and backspace while focused
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active or event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.unicode.isdigit() and len(self.text) < 3:
            self.text += event.unicode

    # Parse the typed number and clamp it
    def value(self, fallback: int, lo: int, hi: int) -> int:
        try:
            parsed = int(self.text) if self.text else fallback
        except ValueError:
            parsed = fallback
        return max(lo, min(hi, parsed))

    # Draw the label and current value
    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        color = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT if self.active else MUTED, self.rect, 2, border_radius=8)
        label = font.render(self.label, True, MUTED)
        surface.blit(label, (self.rect.x, self.rect.y - 28))
        value = font.render(self.text or "_", True, TEXT)
        surface.blit(value, (self.rect.x + 14, self.rect.y + 12))


# Main game window and all its screens
class Game:

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

        # Round state: settings used, stopwatch, and end-of-round menus
        self.config: tuple[int, int, int, int] | None = None
        self.start_ms: int | None = None
        self.end_ms: int | None = None
        self.end_at: int | None = None
        self.end_modal = False

        # Leaderboard screen state
        self.leaderboard = Leaderboard()
        self.show_leaderboard = False
        self.lb_keys: list[str] = []
        self.lb_key: str | None = None
        self.lb_new: tuple[str, int, int | None] | None = None  # (key, time ms, rank)

        self.row_field = InputField("Rows", DEFAULT_ROWS)
        self.col_field = InputField("Columns", DEFAULT_COLS)
        self.mine_field = InputField("Mines", DEFAULT_MINES)
        self.decoy_field = InputField("Decoys", DEFAULT_DECOYS)
        self.generate_rect = pygame.Rect(0, 0, 220, 52)
        self.leaderboard_button_rect = pygame.Rect(0, 0, 220, 48)
        self.new_game_rect = pygame.Rect(0, 0, 140, 36)
        self.rules_button_rect = pygame.Rect(0, 0, 100, 36)
        self.play_tab_rect = pygame.Rect(0, 0, 180, 40)
        self.rules_tab_rect = pygame.Rect(0, 0, 180, 40)
        self._refresh_fonts()
        self._layout()

    # Fullscreen by default; F11 flips to a resizable window
    def _open_display(self) -> pygame.Surface:
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        size = (0, 0) if self.fullscreen else (1100, 720)
        return pygame.display.set_mode(size, flags)

    # Scale number and hint fonts to the current tile size
    def _refresh_fonts(self) -> None:
        size = max(16, self.cell_size * 2 // 5)
        self.font = pygame.font.SysFont("menlo", 22)
        self.small_font = pygame.font.SysFont("menlo", 16)
        self.number_font = pygame.font.SysFont("menlo", size, bold=True)
        self.hint_font = pygame.font.SysFont("menlo", max(12, size - 4), bold=True)

    # Positions tabs, fields, and the grid
    def _layout(self) -> None:
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
            self.leaderboard_button_rect = pygame.Rect((width - 220) // 2, y + 90 + 52 + 16, 220, 48)
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

    # Main loop: events, timers, draw, cap at 60 FPS
    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    # ------------------------------------------------------------------ events

    # Routes events to the current screen
    def _handle_event(self, event: pygame.event.Event) -> None:
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
        if self.show_leaderboard:
            self._handle_leaderboard_event(event)
            return
        if self.on_setup:
            self._handle_setup_event(event)
            return
        self._handle_play_event(event)

    # Handles the main menu
    def _handle_setup_event(self, event: pygame.event.Event) -> None:
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
            if self.setup_tab == "play" and self.leaderboard_button_rect.collidepoint(event.pos):
                self._open_leaderboard()
                return
        if self.setup_tab != "play":
            return
        self.row_field.handle_event(event)
        self.col_field.handle_event(event)
        self.mine_field.handle_event(event)
        self.decoy_field.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._start_game()

    # Handles clicks while playing
    def _handle_play_event(self, event: pygame.event.Event) -> None:
        if self.end_modal:
            self._handle_end_modal_event(event)
            return
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

    # Lose menu: Play Again (same settings) or Main Menu
    def _handle_end_modal_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            _, again_rect, menu_rect = self._modal_rects()
            if again_rect.collidepoint(event.pos):
                self._play_again()
            elif menu_rect.collidepoint(event.pos):
                self._return_to_setup()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._play_again()
            elif event.key == pygame.K_ESCAPE:
                self._return_to_setup()

    # X or Esc closes; arrows flip between grid types
    def _handle_leaderboard_event(self, event: pygame.event.Event) -> None:
        _, close_rect, prev_rect, next_rect = self._leaderboard_rects()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_rect.collidepoint(event.pos):
                self._close_leaderboard()
            elif len(self.lb_keys) > 1 and prev_rect.collidepoint(event.pos):
                self._cycle_leaderboard(-1)
            elif len(self.lb_keys) > 1 and next_rect.collidepoint(event.pos):
                self._cycle_leaderboard(1)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_leaderboard()
            elif event.key == pygame.K_LEFT and len(self.lb_keys) > 1:
                self._cycle_leaderboard(-1)
            elif event.key == pygame.K_RIGHT and len(self.lb_keys) > 1:
                self._cycle_leaderboard(1)

    # ------------------------------------------------------------ game flow

    # Reads the setup fields, clamped to legal values
    def _setup_values(self) -> tuple[int, int, int, int]:
        rows = self.row_field.value(DEFAULT_ROWS, MIN_SIZE, MAX_SIZE)
        cols = self.col_field.value(DEFAULT_COLS, MIN_SIZE, MAX_SIZE)
        mines = self.mine_field.value(DEFAULT_MINES, 1, rows * cols - 1)
        decoys = self.decoy_field.value(DEFAULT_DECOYS, 0, max(0, rows * cols - 1 - mines))
        return rows, cols, mines, decoys

    # Build a board from the setup fields and switch to play
    def _start_game(self) -> None:
        rows, cols, mines, decoys = self._setup_values()
        self.row_field.text = str(rows)
        self.col_field.text = str(cols)
        self.mine_field.text = str(mines)
        self.decoy_field.text = str(decoys)
        self._begin(rows, cols, mines, decoys)

    # Fresh board and a reset stopwatch
    def _begin(self, rows: int, cols: int, mines: int, decoys: int) -> None:
        self.board = Board(rows, cols, mines, decoys)
        self.config = (self.board.rows, self.board.cols, self.board.mine_count, self.board.decoy_count)
        self.breaks.clear()
        self.splats.clear()
        self._reset_round_state()
        self.on_setup = False
        self.show_rules = False
        self.message = "Left click reveal · Right click flag · first click is free"
        self._layout()

    # Clear the stopwatch and any round-end menu
    def _reset_round_state(self) -> None:
        self.start_ms = None
        self.end_ms = None
        self.end_at = None
        self.end_modal = False

    # Restart with the same grid settings
    def _play_again(self) -> None:
        if self.config is None:
            self._return_to_setup()
            return
        self._begin(*self.config)

    # Leave the current board and open the menu again
    def _return_to_setup(self) -> None:
        self.on_setup = True
        self.setup_tab = "play"
        self.show_rules = False
        self.show_leaderboard = False
        self.lb_new = None
        self.board = None
        self.breaks.clear()
        self.splats.clear()
        self._reset_round_state()
        self.message = "Choose a grid, then generate."
        self._layout()

    # Flag or reveal the tile under the cursor
    def _handle_click(self, pos: tuple[int, int], flag: bool) -> None:
        if self.board is None or self.board.status is not GameStatus.PLAYING:
            return
        cell = self._cell_from_pos(pos)
        if cell is None:
            return
        if flag:
            self.board.toggle_flag(cell.row, cell.col)
            self._sync_status_message()
            return
        now = pygame.time.get_ticks()
        opened = self.board.reveal(cell.row, cell.col)
        if self.start_ms is None and self.board.mines_placed:
            self.start_ms = now  # the stopwatch starts on the first real click
        self._queue_breaks(opened, cell.row, cell.col)
        self._check_round_end(now)
        self._sync_status_message()

    # Stops the timer and schedules the end screen
    def _check_round_end(self, now: int) -> None:
        if self.board is None or self.board.status is GameStatus.PLAYING or self.end_ms is not None:
            return
        self.end_ms = now
        delay = WIN_MENU_DELAY_MS if self.board.status is GameStatus.WON else LOSS_MENU_DELAY_MS
        self.end_at = now + delay

    # Shows the lose menu or leaderboard after a short delay
    def _update(self) -> None:
        if self.board is None or self.show_leaderboard or self.end_modal or self.end_at is None:
            return
        if pygame.time.get_ticks() < self.end_at:
            return
        self.end_at = None
        if self.board.status is GameStatus.WON:
            self._finish_win()
        elif self.board.status is GameStatus.LOST:
            self.end_modal = True

    # Saves the win time and opens the leaderboard
    def _finish_win(self) -> None:
        if self.config is None:
            return
        key = config_key(*self.config)
        elapsed = self._elapsed_ms()
        rank = self.leaderboard.add(key, elapsed)
        self._open_leaderboard(highlight=(key, elapsed, rank))

    # Timer value in ms (0 until the first click)
    def _elapsed_ms(self) -> int:
        if self.start_ms is None:
            return 0
        end = self.end_ms if self.end_ms is not None else pygame.time.get_ticks()
        return max(0, end - self.start_ms)

    # ------------------------------------------------------------ leaderboard

    # Opens the leaderboard, highlighting a new time if given
    def _open_leaderboard(self, highlight: tuple[str, int, int | None] | None = None) -> None:
        self.lb_keys = self.leaderboard.keys()
        self.lb_new = highlight
        if highlight is not None:
            self.lb_key = highlight[0]
        else:
            current = config_key(*self._setup_values())
            if current in self.lb_keys:
                self.lb_key = current
            else:
                self.lb_key = self.lb_keys[0] if self.lb_keys else None
        self.show_leaderboard = True

    # Closes the leaderboard and returns to the main menu
    def _close_leaderboard(self) -> None:
        self.show_leaderboard = False
        self.lb_new = None
        if self.board is not None:
            self._return_to_setup()

    # Move to the previous or next grid type
    def _cycle_leaderboard(self, step: int) -> None:
        if not self.lb_keys or self.lb_key not in self.lb_keys:
            return
        index = self.lb_keys.index(self.lb_key)
        self.lb_key = self.lb_keys[(index + step) % len(self.lb_keys)]

    # Card, close button, and the two arrow buttons
    def _leaderboard_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        width, height = self.screen.get_size()
        card = pygame.Rect(0, 0, 640, min(540, height - 40))
        card.center = (width // 2, height // 2)
        close = pygame.Rect(card.right - 52, card.y + 12, 40, 40)
        prev_rect = pygame.Rect(card.x + 28, card.y + 84, 40, 40)
        next_rect = pygame.Rect(card.right - 68, card.y + 84, 40, 40)
        return card, close, prev_rect, next_rect

    # Rects for the lose menu card and buttons
    def _modal_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        width, height = self.screen.get_size()
        card = pygame.Rect(0, 0, 460, 240)
        card.center = (width // 2, height // 2)
        again = pygame.Rect(card.x + 30, card.bottom - 84, 190, 52)
        menu = pygame.Rect(card.right - 220, card.bottom - 84, 190, 52)
        return card, again, menu

    # ----------------------------------------------------------------- board

    # Starts break animations (decoys also splat)
    def _queue_breaks(self, opened, origin_row: int, origin_col: int) -> None:
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

    # Map a mouse point onto a board cell
    def _cell_from_pos(self, pos: tuple[int, int]):
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

    # Pixel box for one tile, with a small grass gap
    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        ox, oy = self.grid_origin
        pad = max(1, self.cell_size // 16)
        return pygame.Rect(
            ox + col * self.cell_size + pad,
            oy + row * self.cell_size + pad,
            self.cell_size - pad * 2,
            self.cell_size - pad * 2,
        )

    # Header hint after each action
    def _sync_status_message(self) -> None:
        if self.board is None:
            return
        if self.board.status is GameStatus.WON:
            self.message = "You cleared the board!"
        elif self.board.status is GameStatus.LOST:
            self.message = "That was a real mine. White bombs were decoys."
        else:
            self.message = "Left click reveal · Right click flag · ? means a decoy is adjacent"

    # --------------------------------------------------------------- drawing

    # Draws the current screen
    def _draw(self) -> None:
        if self.grass is not None:
            self.screen.blit(self.grass, (0, 0))
        else:
            self.screen.fill((34, 92, 38))
        if self.show_leaderboard:
            self._draw_leaderboard()
            return
        if self.on_setup:
            self._draw_setup()
            return
        self._draw_header()
        self._draw_board()
        if self.show_rules:
            self._draw_rules_panel()
        if self.end_modal:
            self._draw_end_modal()

    # One Play / Rules tab button
    def _draw_tab(self, rect: pygame.Rect, label: str, active: bool) -> None:
        pygame.draw.rect(self.screen, TAB_ACTIVE if active else TAB_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT if active else MUTED, rect, 2, border_radius=8)
        text = self.font.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))

    # Menu: Play tab for settings, Rules tab for how to play
    def _draw_setup(self) -> None:
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
        pygame.draw.rect(self.screen, PANEL, self.leaderboard_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, MUTED, self.leaderboard_button_rect, 2, border_radius=10)
        lb_label = self.font.render("Leaderboard", True, TEXT)
        self.screen.blit(lb_label, lb_label.get_rect(center=self.leaderboard_button_rect.center))
        footer = self.small_font.render(self.message, True, MUTED)
        self.screen.blit(footer, footer.get_rect(center=(width // 2, self.leaderboard_button_rect.bottom + 36)))

    # Draws the rules card
    def _draw_rules_panel(self) -> None:
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

    # Little picture beside each header stat
    def _draw_header_icon(self, kind: str, rect: pygame.Rect) -> None:
        if kind == "flag":
            draw_sod(self.screen, rect)
            draw_flag(self.screen, rect)
        elif kind == "decoy":
            draw_bomb(self.screen, rect, decoy=True)
        else:
            draw_clock(self.screen, rect)

    # Draws the top bar (mines, decoys, timer, buttons)
    def _draw_header(self) -> None:
        width = self.screen.get_width()
        bar = pygame.Surface((width, HEADER_HEIGHT), pygame.SRCALPHA)
        bar.fill(HEADER_BG)
        self.screen.blit(bar, (0, 0))
        if self.board is None:
            return

        icon = 34
        icon_gap = 8
        item_gap = 36
        center_y = 30
        items = [
            ("flag", self.font.render(f"Mines left: {self.board.remaining_mines()}", True, TEXT)),
            ("decoy", self.small_font.render(f"Decoys: {self.board.decoy_count}", True, MUTED)),
            ("clock", self.font.render(format_time(self._elapsed_ms()), True, TEXT)),
        ]
        total = sum(icon + icon_gap + text.get_width() for _, text in items) + item_gap * (len(items) - 1)
        x = (width - total) // 2
        for kind, text in items:
            self._draw_header_icon(kind, pygame.Rect(x, center_y - icon // 2, icon, icon))
            self.screen.blit(text, text.get_rect(midleft=(x + icon + icon_gap, center_y)))
            x += icon + icon_gap + text.get_width() + item_gap

        status_color = TEXT
        if self.board.status is GameStatus.WON:
            status_color = WIN
        elif self.board.status is GameStatus.LOST:
            status_color = DANGER
        status = self.small_font.render(self.message, True, status_color)
        self.screen.blit(status, status.get_rect(center=(width // 2, 68)))

        pygame.draw.rect(self.screen, PANEL, self.rules_button_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL, self.new_game_rect, border_radius=8)
        rules_label = self.small_font.render("Rules", True, TEXT)
        new_label = self.small_font.render("New Game", True, TEXT)
        self.screen.blit(rules_label, rules_label.get_rect(center=self.rules_button_rect.center))
        self.screen.blit(new_label, new_label.get_rect(center=self.new_game_rect.center))

    # Draws every tile and its animations
    def _draw_board(self) -> None:
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

    # Draws an opened tile (bomb, decoy, or number)
    def _draw_revealed(self, cell, rect: pygame.Rect) -> None:
        if cell.is_mine:
            exploded = self.board is not None and self.board.status is GameStatus.LOST
            draw_bomb(self.screen, rect, exploded=exploded)
            return
        if cell.is_decoy:
            draw_bomb(self.screen, rect, decoy=True)
            return
        draw_dirt(self.screen, rect)
        total = cell.total_adjacent
        if total > 0:
            color = NUMBER_COLORS[total]
            text = self.number_font.render(str(total), True, color)
            self.screen.blit(text, text.get_rect(center=rect.center))
        if cell.adjacent_decoys > 0:
            draw_decoy_hint(self.screen, rect, self.hint_font)

    # Lose menu over the revealed board
    def _draw_end_modal(self) -> None:
        width, height = self.screen.get_size()
        shade = pygame.Surface((width, height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        self.screen.blit(shade, (0, 0))
        card, again_rect, menu_rect = self._modal_rects()
        panel = pygame.Surface(card.size, pygame.SRCALPHA)
        panel.fill((24, 40, 26, 240))
        self.screen.blit(panel, card.topleft)
        pygame.draw.rect(self.screen, DANGER, card, 2, border_radius=10)
        title = self.font.render("You hit a mine!", True, DANGER)
        self.screen.blit(title, title.get_rect(center=(card.centerx, card.y + 48)))
        sub = self.small_font.render(f"Time: {format_time(self._elapsed_ms())}", True, MUTED)
        self.screen.blit(sub, sub.get_rect(center=(card.centerx, card.y + 92)))
        ask = self.font.render("Play again?", True, TEXT)
        self.screen.blit(ask, ask.get_rect(center=(card.centerx, card.y + 132)))
        pygame.draw.rect(self.screen, ACCENT, again_rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL, menu_rect, border_radius=10)
        pygame.draw.rect(self.screen, MUTED, menu_rect, 2, border_radius=10)
        again_label = self.font.render("Play Again", True, TEXT)
        menu_label = self.font.render("Main Menu", True, TEXT)
        self.screen.blit(again_label, again_label.get_rect(center=again_rect.center))
        self.screen.blit(menu_label, menu_label.get_rect(center=menu_rect.center))

    # Draws the leaderboard screen
    def _draw_leaderboard(self) -> None:
        card, close_rect, prev_rect, next_rect = self._leaderboard_rects()
        panel = pygame.Surface(card.size, pygame.SRCALPHA)
        panel.fill((24, 40, 26, 238))
        self.screen.blit(panel, card.topleft)
        pygame.draw.rect(self.screen, ACCENT, card, 2, border_radius=10)
        heading = self.font.render("Leaderboard", True, TEXT)
        self.screen.blit(heading, (card.x + 28, card.y + 20))

        # Close (X) button
        pygame.draw.rect(self.screen, PANEL, close_rect, border_radius=8)
        pygame.draw.rect(self.screen, MUTED, close_rect, 2, border_radius=8)
        inset = close_rect.inflate(-20, -20)
        pygame.draw.line(self.screen, TEXT, inset.topleft, inset.bottomright, 3)
        pygame.draw.line(self.screen, TEXT, inset.topright, inset.bottomleft, 3)

        # Banner for a just-finished win
        if self.lb_new is not None and self.lb_new[0] == self.lb_key:
            _, new_ms, rank = self.lb_new
            if rank is not None:
                banner = f"Your time: {format_time(new_ms)}  ·  Rank #{rank}"
            else:
                banner = f"Your time: {format_time(new_ms)}  ·  Not in the top {LEADERBOARD_SIZE}"
            text = self.small_font.render(banner, True, HIGHLIGHT)
            self.screen.blit(text, (card.x + 28, card.y + 56))

        # Grid-type selector
        if self.lb_key is None:
            label_text = "No times yet"
        else:
            label_text = key_label(self.lb_key)
        label = self.font.render(label_text, True, TEXT)
        self.screen.blit(label, label.get_rect(center=(card.centerx, prev_rect.centery)))
        if len(self.lb_keys) > 1:
            for rect, direction in ((prev_rect, -1), (next_rect, 1)):
                pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
                pygame.draw.rect(self.screen, MUTED, rect, 2, border_radius=8)
                cx, cy = rect.center
                tip = cx + 7 * direction
                back = cx - 7 * direction
                pygame.draw.polygon(self.screen, TEXT, [(tip, cy), (back, cy - 10), (back, cy + 10)])

        # Times
        times = self.leaderboard.times(self.lb_key) if self.lb_key is not None else []
        if not times:
            note = self.small_font.render("No times yet. Win a round to set one.", True, MUTED)
            self.screen.blit(note, note.get_rect(center=(card.centerx, card.y + 190)))
            return
        mark = None
        if self.lb_new is not None and self.lb_new[0] == self.lb_key and self.lb_new[2] is not None:
            mark = self.lb_new[2] - 1
        y = card.y + 148
        for index, ms in enumerate(times):
            row = pygame.Rect(card.x + 28, y - 4, card.width - 56, 30)
            is_new = index == mark
            if is_new:
                pygame.draw.rect(self.screen, TAB_ACTIVE, row, border_radius=6)
                pygame.draw.rect(self.screen, HIGHLIGHT, row, 2, border_radius=6)
            color = HIGHLIGHT if is_new else TEXT
            place = self.small_font.render(f"{index + 1:>2}.", True, color)
            value = self.small_font.render(format_time(ms), True, color)
            self.screen.blit(place, (row.x + 14, y))
            self.screen.blit(value, (row.x + 80, y))
            y += 34
