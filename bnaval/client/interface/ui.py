from __future__ import annotations

import pygame
from pygame import Surface
from pygame.font import Font

from bnaval.client.input import InputManager
from bnaval.client.utils import Colors, ColorRGB, point_in_rect


class Ui:
    """Classe de assistência a desenho de partes da interface do usuário (UI)."""

    def __init__(self, screen: Surface, input_manager: InputManager) -> None:
        self.inm = input_manager
        self.screen = screen
        self.last_btn_clicked = False
        self.last_btn_hovered = False
        self.last_textbox_text = ""
        self.last_textbox_ok = False
        self.current_cursor = pygame.SYSTEM_CURSOR_ARROW

    def pre_update(self) -> None:
        self.current_cursor = pygame.SYSTEM_CURSOR_ARROW

    def post_update(self) -> None:
        pygame.mouse.set_cursor(self.current_cursor)

    def draw_button(
        self,
        center: tuple[int, int],
        size: tuple[int, int],
        text: str,
        font: Font,
        border_radius: int = 15,
        fg_color: ColorRGB = Colors.BUTTON_FG,
        bg_color: ColorRGB = Colors.BUTTON_BG,
        bg_color_hover: ColorRGB | None = Colors.BUTTON_BG_HOVER,
        bg_color_press: ColorRGB | None = Colors.BUTTON_BG_PRESS,
    ) -> None:
        cx, cy = center
        sx, sy = size
        bg_rect = (cx - sx // 2, cy - sy // 2, sx, sy)
        in_region = point_in_rect(pygame.mouse.get_pos(), bg_rect)

        if in_region:
            self.current_cursor = pygame.SYSTEM_CURSOR_HAND

        chosen_bg_color = bg_color
        if bg_color_hover is not None and in_region:
            chosen_bg_color = bg_color_hover
        if bg_color_press is not None and in_region and self.inm.mouse_l.held:
            chosen_bg_color = bg_color_press
        pygame.draw.rect(
            self.screen, chosen_bg_color, bg_rect, width=0, border_radius=border_radius
        )

        pygame.draw.rect(
            self.screen,
            tuple(int(x * 0.5) for x in chosen_bg_color),
            bg_rect,
            width=3,
            border_radius=border_radius,
        )

        rt = font.render(text, True, fg_color)
        txt_topleft = (cx - rt.get_width() // 2, cy - rt.get_height() // 2)
        self.screen.blit(rt, txt_topleft)

        self.last_btn_hovered = in_region
        self.last_btn_clicked = in_region and self.inm.mouse_l.pressed

    def draw_textbox(
        self,
        center: tuple[int, int],
        size: tuple[int, int],
        text: str,
        font: Font,
        border_radius: int = 15,
        fg_color: ColorRGB = Colors.BUTTON_FG,
        bg_color: ColorRGB = Colors.BUTTON_BG,
        bg_color_hover: ColorRGB | None = Colors.BUTTON_BG_HOVER,
        bg_color_press: ColorRGB | None = Colors.BUTTON_BG_PRESS,
    ) -> None:
        cx, cy = center
        sx, sy = size
        bg_rect = (cx - sx // 2, cy - sy // 2, sx, sy)
        in_region = point_in_rect(pygame.mouse.get_pos(), bg_rect)

        ok = False

        for k in self.inm.queued_input_keys:
            if k == pygame.K_BACKSPACE:
                text = text[:-1]
            elif k == pygame.K_RETURN:
                ok = True
            elif isinstance(k, str):
                # qualquer tecla ASCII lowercase digitada
                text += k

        pygame.draw.rect(
            self.screen, bg_color, bg_rect, width=0, border_radius=border_radius
        )

        pygame.draw.rect(
            self.screen,
            tuple(int(x * 0.5) for x in bg_color),
            bg_rect,
            width=3,
            border_radius=border_radius,
        )

        # um cursor animado quando não tem texto digitado ainda
        if len(text) == 0:
            BLINK_PERIOD = 800
            period0 = (pygame.time.get_ticks() % BLINK_PERIOD) < (BLINK_PERIOD // 2)
            cursor = "|" if period0 else " "
        else:
            cursor = ""

        rt = font.render(text + cursor, True, fg_color)
        txt_topleft = (cx - rt.get_width() // 2, cy - rt.get_height() // 2)
        self.screen.blit(rt, txt_topleft)

        self.last_textbox_text = text
        self.last_textbox_ok = ok

    def draw_text(
        self,
        center: tuple[int, int],
        text: str,
        font: Font,
        color: ColorRGB,
    ) -> None:
        cx, cy = center

        rt = font.render(text, True, color)
        txt_topleft = (cx - rt.get_width() // 2, cy - rt.get_height() // 2)
        self.screen.blit(rt, txt_topleft)
