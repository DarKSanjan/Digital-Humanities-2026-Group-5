"""
Design System Configuration for Full HD Chatbot UI (1920x1080)

This module defines the visual design system including colors, typography,
spacing, and component styles for a modern, professional dark theme interface.

Requirements: 13.1, 13.2, 13.3, 16.1
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ColorPalette:
    """Dark theme color palette optimized for Full HD displays."""
    primary: str = "#4A90E2"
    primary_hover: str = "#357ABD"
    primary_active: str = "#2868A8"
    secondary: str = "#7B68EE"
    secondary_hover: str = "#6A5ACD"
    bg_primary: str = "#1A1A1A"
    bg_secondary: str = "#242424"
    bg_tertiary: str = "#2E2E2E"
    bg_elevated: str = "#333333"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0B0B0"
    text_tertiary: str = "#808080"
    text_disabled: str = "#4D4D4D"
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#F44336"
    info: str = "#2196F3"
    avatar_border: str = "#4A90E2"
    avatar_glow: str = "#4A90E280"
    hover_overlay: str = "#FFFFFF10"
    active_overlay: str = "#FFFFFF20"
    focus_ring: str = "#4A90E2"
    border_subtle: str = "#3A3A3A"
    border_medium: str = "#4D4D4D"
    border_strong: str = "#666666"
    divider: str = "#2E2E2E"
    shadow_sm: str = "rgba(0, 0, 0, 0.2)"
    shadow_md: str = "rgba(0, 0, 0, 0.3)"
    shadow_lg: str = "rgba(0, 0, 0, 0.4)"
    shadow_xl: str = "rgba(0, 0, 0, 0.5)"


@dataclass
class Typography:
    """Typography system with fonts, sizes, and weights."""
    font_primary: str = "Segoe UI"
    font_secondary: str = "Arial"
    font_monospace: str = "Consolas"
    size_xs: int = 12
    size_sm: int = 14
    size_base: int = 16
    size_lg: int = 18
    size_xl: int = 22
    size_2xl: int = 28
    size_3xl: int = 36
    size_4xl: int = 48
    weight_light: int = 300
    weight_normal: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    weight_bold: int = 700
    line_height_tight: float = 1.2
    line_height_normal: float = 1.5
    line_height_relaxed: float = 1.8
    letter_spacing_tight: float = -0.5
    letter_spacing_normal: float = 0.0
    letter_spacing_wide: float = 0.5


@dataclass
class Spacing:
    """Consistent spacing scale for layout and components."""
    unit: int = 8
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48
    xxxl: int = 64
    padding_button: Tuple[int, int] = (12, 24)
    padding_card: int = 24
    padding_modal: int = 32
    padding_input: Tuple[int, int] = (10, 16)
    gap_xs: int = 4
    gap_sm: int = 8
    gap_md: int = 16
    gap_lg: int = 24
    gap_xl: int = 32


@dataclass
class ButtonStyles:
    """Button component styling."""
    primary_bg: str = "#4A90E2"
    primary_bg_hover: str = "#357ABD"
    primary_bg_active: str = "#2868A8"
    primary_text: str = "#FFFFFF"
    secondary_bg: str = "#2E2E2E"
    secondary_bg_hover: str = "#333333"
    secondary_text: str = "#FFFFFF"
    danger_bg: str = "#F44336"
    danger_bg_hover: str = "#D32F2F"
    danger_text: str = "#FFFFFF"
    height_sm: int = 32
    height_md: int = 40
    height_lg: int = 48
    border_radius: int = 8
    font_size: int = 16
    font_weight: int = 500


@dataclass
class CardStyles:
    """Card component styling."""
    bg: str = "#2E2E2E"
    bg_hover: str = "#333333"
    border_color: str = "#3A3A3A"
    border_width: int = 1
    border_radius: int = 12
    padding: int = 24
    shadow: str = "0 4px 12px rgba(0, 0, 0, 0.3)"
    shadow_hover: str = "0 8px 24px rgba(0, 0, 0, 0.4)"


@dataclass
class ShadowStyles:
    """Shadow definitions for depth and elevation."""
    none: str = "none"
    sm: str = "0 1px 3px rgba(0, 0, 0, 0.2)"
    md: str = "0 4px 12px rgba(0, 0, 0, 0.3)"
    lg: str = "0 8px 24px rgba(0, 0, 0, 0.4)"
    xl: str = "0 16px 48px rgba(0, 0, 0, 0.5)"
    glow_primary: str = "0 0 20px #4A90E280"
    glow_focus: str = "0 0 0 3px #4A90E240"


@dataclass
class InputStyles:
    """Input field styling."""
    bg: str = "#242424"
    bg_focus: str = "#2E2E2E"
    border_color: str = "#4D4D4D"
    border_color_focus: str = "#4A90E2"
    border_width: int = 2
    border_radius: int = 8
    text_color: str = "#FFFFFF"
    placeholder_color: str = "#808080"
    height: int = 44
    padding: Tuple[int, int] = (10, 16)
    font_size: int = 16


@dataclass
class ModalStyles:
    """Modal/dialog styling."""
    bg: str = "#333333"
    overlay_bg: str = "rgba(0, 0, 0, 0.7)"
    border_radius: int = 16
    padding: int = 32
    shadow: str = "0 24px 64px rgba(0, 0, 0, 0.5)"
    max_width: int = 600
    min_height: int = 200


@dataclass
class LayoutDimensions:
    """Layout dimensions optimized for Full HD displays."""
    window_width: int = 1920
    window_height: int = 1080
    avatar_size: Tuple[int, int] = (512, 512)
    avatar_border_width: int = 3
    header_height: int = 80
    footer_height: int = 60
    sidebar_width: int = 400
    content_max_width: int = 1200
    content_padding: int = 32


@dataclass
class AnimationSettings:
    """Animation timing and easing functions."""
    duration_fast: int = 150
    duration_normal: int = 300
    duration_slow: int = 500
    ease_in: str = "cubic-bezier(0.4, 0.0, 1.0, 1.0)"
    ease_out: str = "cubic-bezier(0.0, 0.0, 0.2, 1.0)"
    ease_in_out: str = "cubic-bezier(0.4, 0.0, 0.2, 1.0)"
    ease_smooth: str = "cubic-bezier(0.25, 0.1, 0.25, 1.0)"
    target_fps: int = 30


class DesignSystem:
    """Complete design system for the Full HD chatbot UI."""
    
    def __init__(self):
        self.colors = ColorPalette()
        self.typography = Typography()
        self.spacing = Spacing()
        self.buttons = ButtonStyles()
        self.cards = CardStyles()
        self.shadows = ShadowStyles()
        self.inputs = InputStyles()
        self.modals = ModalStyles()
        self.layout = LayoutDimensions()
        self.animations = AnimationSettings()
    
    def get_font_config(self, size: str = "base", weight: str = "normal") -> Dict[str, any]:
        """Get font configuration for tkinter."""
        size_map = {
            "xs": self.typography.size_xs,
            "sm": self.typography.size_sm,
            "base": self.typography.size_base,
            "lg": self.typography.size_lg,
            "xl": self.typography.size_xl,
            "2xl": self.typography.size_2xl,
            "3xl": self.typography.size_3xl,
            "4xl": self.typography.size_4xl,
        }
        weight_map = {
            "light": "normal",
            "normal": "normal",
            "medium": "normal",
            "semibold": "bold",
            "bold": "bold",
        }
        return {
            "family": self.typography.font_primary,
            "size": size_map.get(size, self.typography.size_base),
            "weight": weight_map.get(weight, "normal"),
        }
    
    def get_button_style(self, variant: str = "primary", size: str = "md") -> Dict[str, any]:
        """Get button style configuration for tkinter."""
        size_map = {
            "sm": self.buttons.height_sm,
            "md": self.buttons.height_md,
            "lg": self.buttons.height_lg,
        }
        variant_styles = {
            "primary": {
                "bg": self.buttons.primary_bg,
                "fg": self.buttons.primary_text,
                "activebackground": self.buttons.primary_bg_active,
            },
            "secondary": {
                "bg": self.buttons.secondary_bg,
                "fg": self.buttons.secondary_text,
                "activebackground": self.buttons.secondary_bg_hover,
            },
            "danger": {
                "bg": self.buttons.danger_bg,
                "fg": self.buttons.danger_text,
                "activebackground": self.buttons.danger_bg_hover,
            },
        }
        base_style = {
            "height": size_map.get(size, self.buttons.height_md),
            "borderwidth": 0,
            "relief": "flat",
            "cursor": "hand2",
            "font": (self.typography.font_primary, self.buttons.font_size, "normal"),
        }
        base_style.update(variant_styles.get(variant, variant_styles["primary"]))
        return base_style
    
    def get_card_style(self) -> Dict[str, any]:
        """Get card style configuration for tkinter."""
        return {
            "bg": self.cards.bg,
            "borderwidth": self.cards.border_width,
            "relief": "solid",
            "highlightthickness": 0,
        }


# Global design system instance
design_system = DesignSystem()


# Utility functions
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a hex color by a given factor."""
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex(r, g, b)


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a hex color by a given factor."""
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex(r, g, b)
