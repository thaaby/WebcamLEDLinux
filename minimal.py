"""
MINIMAL COLOR GRID DETECTOR
Versione ultra-leggera per Raspberry Pi 5.
Solo griglia colori + riconoscimento. Niente audio, niente Arduino.
"""

import cv2
import numpy as np
from collections import namedtuple
import math
import json
import time
import sys
from datetime import datetime

# ============================================================
# DATABASE COLORI
# ============================================================
ColorDef = namedtuple('ColorDef', ['name', 'name_it', 'rgb', 'hex_code'])

COLOR_DATABASE = [
    # Rossi
    ColorDef('Red', 'Rosso', (255, 0, 0), '#FF0000'),
    ColorDef('Dark Red', 'Rosso Scuro', (139, 0, 0), '#8B0000'),
    ColorDef('Crimson', 'Cremisi', (220, 20, 60), '#DC143C'),
    ColorDef('Indian Red', 'Rosso Indiano', (205, 92, 92), '#CD5C5C'),
    ColorDef('Light Coral', 'Corallo Chiaro', (240, 128, 128), '#F08080'),
    ColorDef('Salmon', 'Salmone', (250, 128, 114), '#FA8072'),
    ColorDef('Dark Salmon', 'Salmone Scuro', (233, 150, 122), '#E9967A'),
    ColorDef('Light Salmon', 'Salmone Chiaro', (255, 160, 122), '#FFA07A'),
    ColorDef('Fire Brick', 'Mattone', (178, 34, 34), '#B22222'),
    ColorDef('Maroon', 'Marrone Rosso', (128, 0, 0), '#800000'),
    # Arancioni
    ColorDef('Orange', 'Arancione', (255, 165, 0), '#FFA500'),
    ColorDef('Dark Orange', 'Arancione Scuro', (255, 140, 0), '#FF8C00'),
    ColorDef('Orange Red', 'Rosso Arancio', (255, 69, 0), '#FF4500'),
    ColorDef('Tomato', 'Pomodoro', (255, 99, 71), '#FF6347'),
    ColorDef('Coral', 'Corallo', (255, 127, 80), '#FF7F50'),
    ColorDef('Peach', 'Pesca', (255, 218, 185), '#FFDAB9'),
    ColorDef('Apricot', 'Albicocca', (251, 206, 177), '#FBCEB1'),
    ColorDef('Tangerine', 'Mandarino', (255, 159, 0), '#FF9F00'),
    ColorDef('Burnt Orange', 'Arancione Bruciato', (204, 85, 0), '#CC5500'),
    ColorDef('Pumpkin', 'Zucca', (255, 117, 24), '#FF7518'),
    # Gialli
    ColorDef('Yellow', 'Giallo', (255, 255, 0), '#FFFF00'),
    ColorDef('Light Yellow', 'Giallo Chiaro', (255, 255, 224), '#FFFFE0'),
    ColorDef('Lemon', 'Limone', (255, 247, 0), '#FFF700'),
    ColorDef('Gold', 'Oro', (255, 215, 0), '#FFD700'),
    ColorDef('Golden Yellow', 'Giallo Dorato', (255, 223, 0), '#FFDF00'),
    ColorDef('Mustard', 'Senape', (255, 219, 88), '#FFDB58'),
    ColorDef('Canary Yellow', 'Giallo Canarino', (255, 239, 0), '#FFEF00'),
    ColorDef('Banana Yellow', 'Giallo Banana', (255, 225, 53), '#FFE135'),
    ColorDef('Amber', 'Ambra', (255, 191, 0), '#FFBF00'),
    ColorDef('Champagne', 'Champagne', (247, 231, 206), '#F7E7CE'),
    ColorDef('Cream', 'Crema', (255, 253, 208), '#FFFDD0'),
    ColorDef('Khaki', 'Cachi', (240, 230, 140), '#F0E68C'),
    ColorDef('Dark Khaki', 'Cachi Scuro', (189, 183, 107), '#BDB76B'),
    # Verdi
    ColorDef('Green', 'Verde', (0, 128, 0), '#008000'),
    ColorDef('Lime', 'Lime', (0, 255, 0), '#00FF00'),
    ColorDef('Bright Green', 'Verde Brillante', (102, 255, 0), '#66FF00'),
    ColorDef('Dark Green', 'Verde Scuro', (0, 100, 0), '#006400'),
    ColorDef('Forest Green', 'Verde Foresta', (34, 139, 34), '#228B22'),
    ColorDef('Sea Green', 'Verde Mare', (46, 139, 87), '#2E8B57'),
    ColorDef('Medium Sea Green', 'Verde Mare Medio', (60, 179, 113), '#3CB371'),
    ColorDef('Light Green', 'Verde Chiaro', (144, 238, 144), '#90EE90'),
    ColorDef('Pale Green', 'Verde Pallido', (152, 251, 152), '#98FB98'),
    ColorDef('Spring Green', 'Verde Primavera', (0, 255, 127), '#00FF7F'),
    ColorDef('Lawn Green', 'Verde Prato', (124, 252, 0), '#7CFC00'),
    ColorDef('Chartreuse', 'Chartreuse', (127, 255, 0), '#7FFF00'),
    ColorDef('Yellow Green', 'Giallo Verde', (154, 205, 50), '#9ACD32'),
    ColorDef('Olive', 'Oliva', (128, 128, 0), '#808000'),
    ColorDef('Olive Drab', 'Oliva Opaco', (107, 142, 35), '#6B8E23'),
    ColorDef('Dark Olive', 'Oliva Scuro', (85, 107, 47), '#556B2F'),
    ColorDef('Mint', 'Menta', (189, 252, 201), '#BDFCC9'),
    ColorDef('Emerald', 'Smeraldo', (80, 200, 120), '#50C878'),
    ColorDef('Jade', 'Giada', (0, 168, 107), '#00A86B'),
    ColorDef('Teal Green', 'Verde Petrolio', (0, 128, 128), '#008080'),
    # Ciano/Acqua
    ColorDef('Cyan', 'Ciano', (0, 255, 255), '#00FFFF'),
    ColorDef('Aqua', 'Acqua', (0, 200, 200), '#00C8C8'),
    ColorDef('Light Cyan', 'Ciano Chiaro', (224, 255, 255), '#E0FFFF'),
    ColorDef('Dark Cyan', 'Ciano Scuro', (0, 139, 139), '#008B8B'),
    ColorDef('Turquoise', 'Turchese', (64, 224, 208), '#40E0D0'),
    ColorDef('Dark Turquoise', 'Turchese Scuro', (0, 206, 209), '#00CED1'),
    ColorDef('Medium Turquoise', 'Turchese Medio', (72, 209, 204), '#48D1CC'),
    ColorDef('Pale Turquoise', 'Turchese Pallido', (175, 238, 238), '#AFEEEE'),
    ColorDef('Aquamarine', 'Acquamarina', (127, 255, 212), '#7FFFD4'),
    ColorDef('Teal', 'Petrolio', (0, 128, 128), '#008080'),
    ColorDef('Cadet Blue', 'Blu Cadetto', (95, 158, 160), '#5F9EA0'),
    # Blu
    ColorDef('Blue', 'Blu', (0, 0, 255), '#0000FF'),
    ColorDef('Light Blue', 'Blu Chiaro', (173, 216, 230), '#ADD8E6'),
    ColorDef('Sky Blue', 'Azzurro Cielo', (135, 206, 235), '#87CEEB'),
    ColorDef('Light Sky Blue', 'Azzurro Cielo Chiaro', (135, 206, 250), '#87CEFA'),
    ColorDef('Deep Sky Blue', 'Azzurro Intenso', (0, 191, 255), '#00BFFF'),
    ColorDef('Dodger Blue', 'Blu Dodger', (30, 144, 255), '#1E90FF'),
    ColorDef('Cornflower Blue', 'Blu Fiordaliso', (100, 149, 237), '#6495ED'),
    ColorDef('Steel Blue', 'Blu Acciaio', (70, 130, 180), '#4682B4'),
    ColorDef('Royal Blue', 'Blu Reale', (65, 105, 225), '#4169E1'),
    ColorDef('Medium Blue', 'Blu Medio', (0, 0, 205), '#0000CD'),
    ColorDef('Dark Blue', 'Blu Scuro', (0, 0, 139), '#00008B'),
    ColorDef('Navy', 'Blu Navy', (0, 0, 128), '#000080'),
    ColorDef('Midnight Blue', 'Blu Mezzanotte', (25, 25, 112), '#191970'),
    ColorDef('Cobalt Blue', 'Blu Cobalto', (0, 71, 171), '#0047AB'),
    ColorDef('Electric Blue', 'Blu Elettrico', (125, 249, 255), '#7DF9FF'),
    ColorDef('Azure', 'Azzurro', (0, 127, 255), '#007FFF'),
    ColorDef('Powder Blue', 'Blu Polvere', (176, 224, 230), '#B0E0E6'),
    ColorDef('Alice Blue', 'Blu Alice', (240, 248, 255), '#F0F8FF'),
    # Viola/Porpora
    ColorDef('Purple', 'Viola', (128, 0, 128), '#800080'),
    ColorDef('Violet', 'Violetto', (238, 130, 238), '#EE82EE'),
    ColorDef('Dark Violet', 'Violetto Scuro', (148, 0, 211), '#9400D3'),
    ColorDef('Blue Violet', 'Blu Violetto', (138, 43, 226), '#8A2BE2'),
    ColorDef('Dark Orchid', 'Orchidea Scura', (153, 50, 204), '#9932CC'),
    ColorDef('Medium Orchid', 'Orchidea Media', (186, 85, 211), '#BA55D3'),
    ColorDef('Orchid', 'Orchidea', (218, 112, 214), '#DA70D6'),
    ColorDef('Plum', 'Prugna', (221, 160, 221), '#DDA0DD'),
    ColorDef('Medium Purple', 'Porpora Medio', (147, 112, 219), '#9370DB'),
    ColorDef('Indigo', 'Indaco', (75, 0, 130), '#4B0082'),
    ColorDef('Slate Blue', 'Blu Ardesia', (106, 90, 205), '#6A5ACD'),
    ColorDef('Dark Slate Blue', 'Blu Ardesia Scuro', (72, 61, 139), '#483D8B'),
    ColorDef('Lavender', 'Lavanda', (230, 230, 250), '#E6E6FA'),
    ColorDef('Thistle', 'Cardo', (216, 191, 216), '#D8BFD8'),
    ColorDef('Mauve', 'Malva', (224, 176, 255), '#E0B0FF'),
    ColorDef('Amethyst', 'Ametista', (153, 102, 204), '#9966CC'),
    ColorDef('Grape', 'Uva', (111, 45, 168), '#6F2DA8'),
    ColorDef('Eggplant', 'Melanzana', (97, 64, 81), '#614051'),
    # Rosa/Magenta
    ColorDef('Pink', 'Rosa', (255, 192, 203), '#FFC0CB'),
    ColorDef('Light Pink', 'Rosa Chiaro', (255, 182, 193), '#FFB6C1'),
    ColorDef('Hot Pink', 'Rosa Acceso', (255, 105, 180), '#FF69B4'),
    ColorDef('Deep Pink', 'Rosa Intenso', (255, 20, 147), '#FF1493'),
    ColorDef('Medium Violet Red', 'Rosso Violetto Medio', (199, 21, 133), '#C71585'),
    ColorDef('Pale Violet Red', 'Rosso Violetto Pallido', (219, 112, 147), '#DB7093'),
    ColorDef('Magenta', 'Magenta', (255, 0, 255), '#FF00FF'),
    ColorDef('Fuchsia', 'Fucsia', (255, 0, 200), '#FF00C8'),
    ColorDef('Rose', 'Rosa', (255, 0, 127), '#FF007F'),
    ColorDef('Blush', 'Rosa Cipria', (222, 93, 131), '#DE5D83'),
    ColorDef('Carnation Pink', 'Rosa Garofano', (255, 166, 201), '#FFA6C9'),
    ColorDef('Flamingo', 'Fenicottero', (252, 142, 172), '#FC8EAC'),
    ColorDef('Raspberry', 'Lampone', (227, 11, 92), '#E30B5C'),
    ColorDef('Cerise', 'Ciliegia', (222, 49, 99), '#DE3163'),
    # Marroni
    ColorDef('Brown', 'Marrone', (165, 42, 42), '#A52A2A'),
    ColorDef('Dark Brown', 'Marrone Scuro', (101, 67, 33), '#654321'),
    ColorDef('Saddle Brown', 'Marrone Sella', (139, 69, 19), '#8B4513'),
    ColorDef('Sienna', 'Terra di Siena', (160, 82, 45), '#A0522D'),
    ColorDef('Chocolate', 'Cioccolato', (210, 105, 30), '#D2691E'),
    ColorDef('Peru', 'Peru', (205, 133, 63), '#CD853F'),
    ColorDef('Sandy Brown', 'Marrone Sabbia', (244, 164, 96), '#F4A460'),
    ColorDef('Burly Wood', 'Legno', (222, 184, 135), '#DEB887'),
    ColorDef('Tan', 'Cuoio', (210, 180, 140), '#D2B48C'),
    ColorDef('Rosy Brown', 'Marrone Rosato', (188, 143, 143), '#BC8F8F'),
    ColorDef('Moccasin', 'Mocassino', (255, 228, 181), '#FFE4B5'),
    ColorDef('Navajo White', 'Bianco Navajo', (255, 222, 173), '#FFDEAD'),
    ColorDef('Wheat', 'Grano', (245, 222, 179), '#F5DEB3'),
    ColorDef('Bisque', 'Biscotto', (255, 228, 196), '#FFE4C4'),
    ColorDef('Blanched Almond', 'Mandorla', (255, 235, 205), '#FFEBCD'),
    ColorDef('Cornsilk', 'Seta di Mais', (255, 248, 220), '#FFF8DC'),
    ColorDef('Beige', 'Beige', (245, 245, 220), '#F5F5DC'),
    ColorDef('Antique White', 'Bianco Antico', (250, 235, 215), '#FAEBD7'),
    ColorDef('Papaya Whip', 'Papaya', (255, 239, 213), '#FFEFD5'),
    ColorDef('Linen', 'Lino', (250, 240, 230), '#FAF0E6'),
    ColorDef('Old Lace', 'Pizzo Antico', (253, 245, 230), '#FDF5E6'),
    ColorDef('Coffee', 'Caffè', (111, 78, 55), '#6F4E37'),
    ColorDef('Caramel', 'Caramello', (255, 213, 154), '#FFD59A'),
    ColorDef('Rust', 'Ruggine', (183, 65, 14), '#B7410E'),
    ColorDef('Copper', 'Rame', (184, 115, 51), '#B87333'),
    ColorDef('Bronze', 'Bronzo', (205, 127, 50), '#CD7F32'),
    ColorDef('Terracotta', 'Terracotta', (226, 114, 91), '#E2725B'),
    ColorDef('Burgundy', 'Borgogna', (128, 0, 32), '#800020'),
    ColorDef('Wine', 'Vino', (114, 47, 55), '#722F37'),
    ColorDef('Vermillion', 'Vermiglio', (227, 66, 52), '#E34234'),
    ColorDef('Ochre', 'Ocra', (204, 119, 34), '#CC7722'),
    ColorDef('Marigold', 'Calendula', (234, 162, 33), '#EAA221'),
    ColorDef('Dark Teal', 'Petrolio Scuro', (0, 109, 111), '#006D6F'),
    ColorDef('Persian Red', 'Rosso Persiano', (204, 51, 51), '#CC3333'),
    ColorDef('Sapphire', 'Zaffiro', (15, 82, 186), '#0F52BA'),
    # Grigi
    ColorDef('Gray', 'Grigio', (128, 128, 128), '#808080'),
    ColorDef('Dark Gray', 'Grigio Scuro', (169, 169, 169), '#A9A9A9'),
    ColorDef('Dim Gray', 'Grigio Tenue', (105, 105, 105), '#696969'),
    ColorDef('Light Gray', 'Grigio Chiaro', (211, 211, 211), '#D3D3D3'),
    ColorDef('Silver', 'Argento', (192, 192, 192), '#C0C0C0'),
    ColorDef('Light Slate Gray', 'Grigio Ardesia Chiaro', (119, 136, 153), '#778899'),
    ColorDef('Slate Gray', 'Grigio Ardesia', (112, 128, 144), '#708090'),
    ColorDef('Dark Slate Gray', 'Grigio Ardesia Scuro', (47, 79, 79), '#2F4F4F'),
    ColorDef('Charcoal', 'Carbone', (54, 69, 79), '#36454F'),
    ColorDef('Ash Gray', 'Grigio Cenere', (178, 190, 181), '#B2BEB5'),
    ColorDef('Gainsboro', 'Gainsboro', (220, 220, 220), '#DCDCDC'),
    ColorDef('White Smoke', 'Fumo Bianco', (245, 245, 245), '#F5F5F5'),
    # Bianco e Nero
    ColorDef('White', 'Bianco', (255, 255, 255), '#FFFFFF'),
    ColorDef('Snow', 'Neve', (255, 250, 250), '#FFFAFA'),
    ColorDef('Honeydew', 'Melata', (240, 255, 240), '#F0FFF0'),
    ColorDef('Mint Cream', 'Crema Menta', (245, 255, 250), '#F5FFFA'),
    ColorDef('Ghost White', 'Bianco Fantasma', (248, 248, 255), '#F8F8FF'),
    ColorDef('Floral White', 'Bianco Floreale', (255, 250, 240), '#FFFAF0'),
    ColorDef('Seashell', 'Conchiglia', (255, 245, 238), '#FFF5EE'),
    ColorDef('Ivory', 'Avorio', (255, 255, 240), '#FFFFF0'),
    ColorDef('Black', 'Nero', (0, 0, 0), '#000000'),
    ColorDef('Jet Black', 'Nero Corvino', (52, 52, 52), '#343434'),
    ColorDef('Onyx', 'Onice', (53, 56, 57), '#353839'),
    ColorDef('Ebony', 'Ebano', (85, 93, 80), '#555D50'),
]

# ============================================================
# FUNZIONI COLORE (LAB + Delta-E CIE2000)
# ============================================================

def rgb_to_lab(rgb):
    """Converte RGB in spazio colore CIE LAB."""
    r, g, b = [x / 255.0 for x in rgb]
    
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    
    r, g, b = linearize(r), linearize(g), linearize(b)
    
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883
    
    def f(t):
        return t ** (1/3) if t > 0.008856 else (7.787 * t + 16/116)
    
    L = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    b_val = 200 * (f(y) - f(z))
    
    return (L, a, b_val)


def delta_e_cie2000(lab1, lab2):
    """Distanza Delta-E CIE2000."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    
    kL, kC, kH = 1.0, 1.0, 1.0
    
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_avg = (C1 + C2) / 2
    
    G = 0.5 * (1 - np.sqrt(C_avg**7 / (C_avg**7 + 25**7)))
    
    a1_prime = a1 * (1 + G)
    a2_prime = a2 * (1 + G)
    
    C1_prime = np.sqrt(a1_prime**2 + b1**2)
    C2_prime = np.sqrt(a2_prime**2 + b2**2)
    
    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360
    
    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime
    
    delta_h_prime = h2_prime - h1_prime
    if abs(delta_h_prime) > 180:
        delta_h_prime -= 360 * np.sign(delta_h_prime)
    
    delta_H_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(delta_h_prime / 2))
    
    L_avg_prime = (L1 + L2) / 2
    C_avg_prime = (C1_prime + C2_prime) / 2
    
    h_avg_prime = (h1_prime + h2_prime) / 2
    if abs(h1_prime - h2_prime) > 180:
        h_avg_prime += 180
    
    T = (1 - 0.17 * np.cos(np.radians(h_avg_prime - 30)) +
         0.24 * np.cos(np.radians(2 * h_avg_prime)) +
         0.32 * np.cos(np.radians(3 * h_avg_prime + 6)) -
         0.20 * np.cos(np.radians(4 * h_avg_prime - 63)))
    
    SL = 1 + (0.015 * (L_avg_prime - 50)**2) / np.sqrt(20 + (L_avg_prime - 50)**2)
    SC = 1 + 0.045 * C_avg_prime
    SH = 1 + 0.015 * C_avg_prime * T
    
    delta_theta = 30 * np.exp(-((h_avg_prime - 275) / 25)**2)
    RC = 2 * np.sqrt(C_avg_prime**7 / (C_avg_prime**7 + 25**7))
    RT = -RC * np.sin(np.radians(2 * delta_theta))
    
    delta_E = np.sqrt(
        (delta_L_prime / (kL * SL))**2 +
        (delta_C_prime / (kC * SC))**2 +
        (delta_H_prime / (kH * SH))**2 +
        RT * (delta_C_prime / (kC * SC)) * (delta_H_prime / (kH * SH))
    )
    
    return delta_E


# Pre-calcola i valori LAB
COLOR_LAB_CACHE = {color.name: rgb_to_lab(color.rgb) for color in COLOR_DATABASE}


def find_closest_color(rgb):
    """Trova il colore più vicino con Delta-E CIE2000."""
    target_lab = rgb_to_lab(rgb)
    
    min_distance = float('inf')
    closest_color = None
    
    for color in COLOR_DATABASE:
        color_lab = COLOR_LAB_CACHE[color.name]
        distance = delta_e_cie2000(target_lab, color_lab)
        
        if distance < min_distance:
            min_distance = distance
            closest_color = color
    
    return (closest_color.name, closest_color.name_it, closest_color.hex_code, min_distance)


def rgb_to_hex(r, g, b):
    return f'#{r:02X}{g:02X}{b:02X}'


# ============================================================
# PIPELINE ACCURATEZZA (CLAHE + K-Means)
# ============================================================

CLAHE_CLIP_LIMIT = 2.0
KMEANS_CLUSTERS = 3


def _apply_clahe(roi):
    """CLAHE: Equalizzazione luminosità locale."""
    if roi.size == 0:
        return roi
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=(4, 4))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _extract_dominant_kmeans(roi, n_clusters=3):
    """Colore dominante via K-Means."""
    pixels = roi.reshape(-1, 3).astype(np.float32)
    
    if len(pixels) < n_clusters:
        return np.mean(pixels, axis=0).astype(int)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, n_clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS
    )
    
    dominant_idx = np.argmax(np.bincount(labels.flatten()))
    return centers[dominant_idx].astype(int)


# ============================================================
# GRIGLIA + PALETTE
# ============================================================

GRID_SIZES = [3, 5, 7]


def detect_grid_colors(frame, grid_size=5, sample_size=12):
    """Campiona colori su una griglia NxN."""
    height, width = frame.shape[:2]
    colors = []
    
    margin_x = int(width * 0.28)
    margin_y = int(height * 0.28)
    
    for row in range(grid_size):
        for col in range(grid_size):
            px = margin_x + int((width - 2 * margin_x) * col / max(1, grid_size - 1))
            py = margin_y + int((height - 2 * margin_y) * row / max(1, grid_size - 1))
            
            half = sample_size // 2
            x1 = max(0, px - half)
            y1 = max(0, py - half)
            x2 = min(width, px + half)
            y2 = min(height, py + half)
            
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            
            roi = _apply_clahe(roi)
            
            if roi.size > 9:
                avg_bgr = _extract_dominant_kmeans(roi, min(KMEANS_CLUSTERS, roi.shape[0] * roi.shape[1]))
            else:
                avg_bgr = np.mean(roi, axis=(0, 1)).astype(int)
            
            b, g, r = avg_bgr
            rgb = (int(r), int(g), int(b))
            
            name_en, name_it, hex_code, distance = find_closest_color(rgb)
            
            colors.append({
                'rgb': rgb,
                'bgr': (int(b), int(g), int(r)),
                'hex': rgb_to_hex(*rgb),
                'name_en': name_en,
                'name_it': name_it,
                'pos': (px, py),
                'distance': distance
            })
    
    return colors


def export_palette(palette, grid_size):
    """Esporta la palette come JSON + PNG."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "grid": f"{grid_size}x{grid_size}",
        "n_colors": len(palette),
        "colors": []
    }
    for color in palette:
        json_data["colors"].append({
            "name_en": color['name_en'],
            "name_it": color['name_it'],
            "hex": color['hex'],
            "rgb": list(color['rgb']),
        })
    
    json_filename = f"palette_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # PNG
    swatch_w = 100
    swatch_h = 100
    text_h = 35
    n = len(palette)
    if n == 0:
        return json_filename
    
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    
    img_w = cols * swatch_w
    img_h = rows * (swatch_h + text_h)
    img = np.zeros((img_h, img_w, 3), dtype=np.uint8)
    img[:] = (30, 30, 30)
    
    for i, color in enumerate(palette):
        col = i % cols
        row = i // cols
        x = col * swatch_w
        y = row * (swatch_h + text_h)
        
        cv2.rectangle(img, (x + 2, y + 2), (x + swatch_w - 2, y + swatch_h - 2), color['bgr'], -1)
        cv2.putText(img, color['hex'], (x + 5, y + swatch_h + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(img, color['name_it'][:10], (x + 5, y + swatch_h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
    
    png_filename = f"palette_{timestamp}.png"
    cv2.imwrite(png_filename, img)
    
    return json_filename


# ============================================================
# DISEGNO GRIGLIA MINIMALE (canvas sintetico, no webcam feed)
# ============================================================

def draw_minimal_grid(grid_colors, grid_size, win_w=600, win_h=600):
    """
    Genera un canvas che riempie esattamente la finestra.
    I quadrati si adattano alle dimensioni della finestra.
    """
    canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
    
    # Calcola dimensione quadrati per riempire tutto
    swatch_w = win_w // grid_size
    swatch_h = win_h // grid_size
    
    for i, color in enumerate(grid_colors):
        row = i // grid_size
        col = i % grid_size
        
        x = col * swatch_w
        y = row * swatch_h
        
        cv2.rectangle(canvas, (x, y), (x + swatch_w, y + swatch_h), color['bgr'], -1)
    
    return canvas


# ============================================================
# MAIN
# ============================================================

def list_cameras():
    """Elenca le webcam disponibili."""
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cameras.append(i)
            cap.release()
    return cameras


def select_camera():
    """Seleziona webcam."""
    print("\n[SCAN] Ricerca webcam...")
    cameras = list_cameras()
    
    if not cameras:
        print("[!] Nessuna webcam trovata, provo ID 0...")
        return 0
    
    print(f"[CAM] Trovate: {len(cameras)}")
    for cam_id in cameras:
        print(f"  [{cam_id}] Camera {cam_id}")
    
    if len(cameras) == 1:
        print(f"[OK] Camera {cameras[0]} selezionata")
        return cameras[0]
    
    while True:
        try:
            choice = input(f"> Seleziona camera (0-{cameras[-1]}): ")
            cam_id = int(choice)
            if cam_id in cameras:
                return cam_id
            print("[X] Camera non valida!")
        except ValueError:
            print("[X] Inserisci un numero!")


def main():
    print("\n" + "=" * 50)
    print("  MINIMAL COLOR GRID - RPi Edition")
    print("  Solo griglia + riconoscimento colori")
    print("=" * 50)
    
    camera_id = select_camera()
    
    print(f"\n[CAM] Avvio webcam {camera_id}...")
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print("[X] Impossibile aprire la webcam!")
        return
    
    # Risoluzione bassa per risparmiare risorse
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n" + "-" * 50)
    print("  CONTROLLI:")
    print("  [G] - Cambia griglia (3x3 -> 5x5 -> 7x7)")
    print("  [P] - Esporta palette (JSON + PNG)")
    print("  [Q/ESC] - Esci")
    print("-" * 50 + "\n")
    
    grid_size_idx = 0
    current_palette = []
    
    # Finestra ridimensionabile
    cv2.namedWindow('Color Grid', cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
    cv2.resizeWindow('Color Grid', 600, 600)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[X] Errore lettura frame!")
                break
            
            frame = cv2.flip(frame, 1)
            
            # Campiona griglia
            grid_size = GRID_SIZES[grid_size_idx]
            grid_colors = detect_grid_colors(frame, grid_size)
            current_palette = grid_colors
            
            # Leggi dimensione finestra e genera canvas adattato
            try:
                _, _, ww, wh = cv2.getWindowImageRect('Color Grid')
                if ww < 10 or wh < 10:
                    ww, wh = 600, 600
            except:
                ww, wh = 600, 600
            canvas = draw_minimal_grid(grid_colors, grid_size, ww, wh)
            cv2.imshow('Color Grid', canvas)
            
            # Input
            key = cv2.waitKey(300) & 0xFF  # 300ms = ~3 FPS (leggero!)
            
            if key == ord('q') or key == 27:
                print("\n[BYE] Arrivederci!")
                break
            elif key == ord('g'):
                grid_size_idx = (grid_size_idx + 1) % len(GRID_SIZES)
                print(f"[GRID] Griglia: {GRID_SIZES[grid_size_idx]}x{GRID_SIZES[grid_size_idx]}")
            elif key == ord('p'):
                if current_palette:
                    filename = export_palette(current_palette, grid_size)
                    print(f"[OK] Palette esportata! {len(current_palette)} colori")
                    print(f"   JSON: {filename}")
                    print(f"   PNG:  {filename.replace('.json', '.png')}")
                    for c in current_palette:
                        print(f"   {c['hex']} - {c['name_it']}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
