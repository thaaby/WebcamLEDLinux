#!/usr/bin/env python3
"""
🎨 Webcam Color Detector
Rileva i colori dalla webcam usando algoritmo CIE LAB Delta-E per massima precisione.
+ Rilevamento biglie colorate con suoni personalizzati (Yellow, Red, Blue)

SETUP RASPBERRY PI 4:
1. Installa dipendenze sistema:
   sudo apt-get update
   sudo apt-get install python3-opencv python3-numpy python3-pygame libatlas-base-dev

2. Abilita la camera (se usi pi camera):
   sudo raspi-config  -> Interface Options -> Legacy Camera (o Camera) -> Enable

3. Esegui:
   python3 main.py
"""

import cv2
import numpy as np
from collections import namedtuple
import subprocess
import serial
import threading
import time
import os
import platform
import math

try:
    import serial
except ImportError:
    serial = None
    print("⚠️  pyserial non installato. Installa con: pip install pyserial")


# Prova a importare pygame per la riproduzione audio (Cross-platform)
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️  pygame non installato. Installa con: pip install pygame")
except Exception as e:
    PYGAME_AVAILABLE = False
    print(f"⚠️  Errore inizializzazione pygame: {e}")

# ============================================================
# SINESTESIA DIGITALE - MOTORE SONORO
# ============================================================
class SoundSynth:
    """Generatore di suoni procedurali (Onde Sinusoidali) usando Pygame e Numpy."""
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.bits = 16
        if PYGAME_AVAILABLE:
            try:
                # Re-inizializza mixer per bassa latenza
                pygame.mixer.quit()
                pygame.mixer.init(frequency=sample_rate, size=-16, channels=1, buffer=512)
            except Exception as e:
                print(f"Errore configurazione audio: {e}")
        
    def generate_relaxing_wave(self, freq, duration=1.5, volume=0.5):
        """
        Genera un suono 'Zen Bell' (Campana Tibetana / Soft Chime).
        Caratteristiche:
        - Onda Sinusoidale pura + Armoniche pari (calore)
        - Nessun rumore, nessuna distorsione
        - Attacco morbido, Rilascio molto lungo
        """
        if not PYGAME_AVAILABLE: return None
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # --- SINTESI ADDITIVA (Bell Tone) ---
        # Fondamentale
        wave = np.sin(2 * np.pi * freq * t) * 1.0
        # 2a Armonica (Ottava) - Aggiunge corpo
        wave += np.sin(2 * np.pi * (freq * 2.0) * t) * 0.3
        # 4a Armonica (2 Ottave) - Aggiunge brillantezza dolce
        wave += np.sin(2 * np.pi * (freq * 4.0) * t) * 0.1
        
        # --- VOLUME e MODULAZIONE ---
        wave *= volume * 0.4
        
        # Tremolo impercettibile (pulsazione vitale)
        tremolo = 1.0 + (0.05 * np.sin(2 * np.pi * 3.0 * t))
        wave *= tremolo
        
        # --- ENVELOPE (Campana) ---
        # Attacco veloce ma non "clicky" (20ms)
        # Rilascio lungo esponenziale
        envelope = np.exp(-2.5 * t) 
        
        # Micro fade-in per evitare click iniziale
        attack_len = int(self.sample_rate * 0.02)
        if attack_len > 0:
            envelope[:attack_len] *= np.linspace(0, 1, attack_len)

        wave *= envelope
        
        # Conversione a 16-bit
        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
            
        return pygame.sndarray.make_sound(audio_data)

# Inizializza Synth
synth = SoundSynth()

def get_frequency_from_hsv(h, s, v):
    """
    Calcola la frequenza basandosi SULLA SCALA PENTATONICA (Do Maggiore).
    - Hue (0-179): Mappato su 5 note (C, D, E, G, A).
    - Value (0-255): Determina l'ottava.
    In questo modo è impossibile suonare note 'stonate'.
    """
    # 1. Determina l'ottava base
    if v < 85:   base_octave_idx = 3 # Ottava 3 (Bassa)
    elif v < 170: base_octave_idx = 4 # Ottava 4 (Media)
    else:         base_octave_idx = 5 # Ottava 5 (Alta)
    
    # 2. Scala Pentatonica C Major (Intervalli in semitoni da C)
    # C=0, D=2, E=4, G=7, A=9
    pentatonic_intervals = [0, 2, 4, 7, 9] 
    
    # 3. Mappa Hue (0-179) sui 5 indici della scala
    # Ci sono 5 note. 180 / 5 = 36 gradi di hue per nota.
    scale_index = int((h / 180.0) * len(pentatonic_intervals))
    if scale_index >= len(pentatonic_intervals): 
        scale_index = len(pentatonic_intervals) - 1
        
    semitone_offset = pentatonic_intervals[scale_index]
    
    # 4. Calcolo Frequenza
    # Frequenza base C per le ottave 3, 4, 5
    # C3=130.81, C4=261.63, C5=523.25
    c_freqs = {3: 130.81, 4: 261.63, 5: 523.25}
    base_freq = c_freqs.get(base_octave_idx, 261.63)
    
    # Formula semitoni: f = f0 * 2^(n/12)
    freq = base_freq * (2 ** (semitone_offset / 12.0))
    
    return freq

last_played_note_time = 0
NOTE_COOLDOWN = 0.5  # Tempo "Zen"
current_playing_freq = 0


# ============================================================
# CONFIGURAZIONE ARDUINO & PARAMETRI OTTIMIZZAZIONE
# ============================================================
ARDUINO_PORT = '/dev/cu.usbmodem1401'  
BAUD_RATE = 115200

# 2. Parametri di Ottimizzazione (GIOCA CON QUESTI!)
# 2. Parametri di Ottimizzazione (GIOCA CON QUESTI!)
GAMMA = 2.5           
SMOOTHING = 0.1       # Un po' più basso per rendere la pulsazione più morbida
BLACK_THRESHOLD = 60 

# --- CONFIGURAZIONE EFFETTO RESPIRO ---
PULSE_SPEED = 2.5     # Velocità del respiro. (Più alto = iperventilazione, Più basso = relax zen)
MIN_BRIGHTNESS = 0.3  # Luminosità minima durante il respiro (0.0 = buio totale, 0.5 = si affievolisce solo a metà)

arduino = None

# --- PRE-CALCOLO TABELLA GAMMA (Per velocità) ---
# Crea una tabella di conversione per non fare calcoli pesanti in ogni frame
gamma_table = np.array([((i / 255.0) ** GAMMA) * 255 for i in np.arange(0, 256)]).astype("uint8")

def apply_gamma(color):
    """Applica la correzione gamma al colore RGB"""
    return gamma_table[color]

# ============================================================
# ============================================================

# Definizione colore con valori RGB e nomi
ColorDef = namedtuple('ColorDef', ['name', 'name_it', 'rgb', 'hex_code'])

# Dataset dei colori principali piu possibili variazioni
# RGB values per massima precisione nella conversione LAB
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
    ColorDef('Bright Green', 'Verde Brillante', (0, 255, 0), '#00FF00'),
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
    ColorDef('Aqua', 'Acqua', (0, 255, 255), '#00FFFF'),
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
    ColorDef('Fuchsia', 'Fucsia', (255, 0, 255), '#FF00FF'),
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

def rgb_to_lab(rgb):
    """Converte RGB in spazio colore CIE LAB per calcolo distanza percettiva."""
    # Normalizza RGB
    r, g, b = [x / 255.0 for x in rgb]
    
    # Converti in sRGB linearizzato
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    
    r, g, b = linearize(r), linearize(g), linearize(b)
    
    # Converti in XYZ (D65 illuminant)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # Normalizza per D65
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883
    
    # Converti in LAB
    def f(t):
        return t ** (1/3) if t > 0.008856 else (7.787 * t + 16/116)
    
    L = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    b_val = 200 * (f(y) - f(z))
    
    return (L, a, b_val)

def delta_e_cie2000(lab1, lab2):
    """
    Calcola la distanza Delta-E CIE2000 (più accurata per percezione umana).
    Questa è la formula standard industriale per confronto colori.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    
    # Parametri di peso
    kL, kC, kH = 1.0, 1.0, 1.0
    
    # Calcolo C'
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
    
    # Delta L', C', H'
    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime
    
    delta_h_prime = h2_prime - h1_prime
    if abs(delta_h_prime) > 180:
        delta_h_prime -= 360 * np.sign(delta_h_prime)
    
    delta_H_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(delta_h_prime / 2))
    
    # Medie
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

# Pre-calcola i valori LAB per tutti i colori nel database
COLOR_LAB_CACHE = {color.name: rgb_to_lab(color.rgb) for color in COLOR_DATABASE}

# Text-to-Speech per feedback audio
def speak_color(color_name: str):
    """Pronuncia il nome del colore usando il sintetizzatore vocale di sistema."""
    def _speak():
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['say', '-v', 'Alice', color_name], check=False)
            elif platform.system() == 'Windows':
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(color_name)
                engine.runAndWait()
            else:  
                subprocess.run(['espeak', color_name], check=False)
        except Exception:
            pass
    
    # Esegui in background per non bloccare
    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()


def play_color_note(hsv_tuple):
    """Riproduce la nota basata sui valori HSV precisi."""
    global last_played_note_time, current_playing_freq
    
    if not PYGAME_AVAILABLE: return
    
    current_time = time.time()
    if current_time - last_played_note_time < NOTE_COOLDOWN:
        return
        
    h, s, v = hsv_tuple
    
    # Ignora se troppo nero (silenzio)
    if v < BLACK_THRESHOLD:
        return

    freq = get_frequency_from_hsv(h, s, v)
    
    # Evita di riprodurre la stessa nota a raffica
    # Tolleranza di 5Hz per considerare la nota "uguale"
    if abs(freq - current_playing_freq) > 3 or (current_time - last_played_note_time > 0.8):
        sound = synth.generate_relaxing_wave(freq, duration=2.0, volume=0.5)
        if sound:
            sound.play()
            last_played_note_time = current_time
            current_playing_freq = freq

def find_closest_color(rgb):
    """
    Trova il colore più vicino nel database usando Delta-E CIE2000.
    Ritorna (nome_en, nome_it, hex_code, distanza).
    """
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

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converte RGB in codice HEX."""
    return f'#{r:02X}{g:02X}{b:02X}'

def get_color_name(hsv_pixel: np.ndarray) -> tuple:
    """
    Determina il nome del colore usando algoritmo LAB Delta-E.
    Ritorna (nome_en, nome_it, hex_code) o None se non trovato.
    """
    # Converti HSV in RGB per il matching LAB
    hsv_normalized = np.array([[[hsv_pixel[0], hsv_pixel[1], hsv_pixel[2]]]], dtype=np.uint8)
    rgb = cv2.cvtColor(hsv_normalized, cv2.COLOR_HSV2RGB)[0][0]
    
    name_en, name_it, hex_code, distance = find_closest_color(tuple(rgb))
    
    # Aggiungi indicatore di precisione
    if distance < 5:
        precision = "●"  # Molto preciso
    elif distance < 15:
        precision = "◐"  # Buono
    else:
        precision = "○"  # Approssimativo
    
    return (f"{name_en} {precision}", f"{name_it} {precision}", hex_code)


def detect_dominant_color(frame: np.ndarray, center_size: int = 50) -> dict:
    """
    Rileva il colore dominante al centro del frame.
    
    Args:
        frame: Frame della webcam in formato BGR
        center_size: Dimensione dell'area centrale da analizzare
        
    Returns:
        Dizionario con informazioni sul colore rilevato
    """
    height, width = frame.shape[:2]
    
    # Calcola l'area centrale
    cx, cy = width // 2, height // 2
    half = center_size // 2
    
    # Estrai la regione centrale
    roi = frame[cy - half:cy + half, cx - half:cx + half]
    
    # Calcola il colore medio della regione
    avg_color_bgr = np.mean(roi, axis=(0, 1)).astype(int)
    b, g, r = avg_color_bgr
    
    # Converti in HSV per il riconoscimento del nome
    avg_color_hsv = cv2.cvtColor(
        np.uint8([[avg_color_bgr]]), 
        cv2.COLOR_BGR2HSV
    )[0][0]
    
    # Ottieni il nome del colore
    color_info = get_color_name(avg_color_hsv)
    
    return {
        'rgb': (int(r), int(g), int(b)),
        'bgr': (int(b), int(g), int(r)),
        'hsv': tuple(avg_color_hsv.tolist()),
        'hex': rgb_to_hex(int(r), int(g), int(b)),
        'name_en': color_info[0] if color_info else 'Unknown',
        'name_it': color_info[1] if color_info else 'Sconosciuto',
        'center': (cx, cy),
        'roi_size': center_size
    }


def draw_info_overlay(frame: np.ndarray, color_data: dict) -> np.ndarray:
    """Disegna le informazioni del colore sul frame con UI migliorata."""
    height, width = frame.shape[:2]
    cx, cy = color_data['center']
    half = color_data['roi_size'] // 2
    
    # Disegna il rettangolo dell'area di rilevamento con bordo più spesso
    cv2.rectangle(frame, (cx - half, cy - half), (cx + half, cy + half), (0, 255, 0), 3)
    
    # Crosshair animato
    cv2.line(frame, (cx - 15, cy), (cx + 15, cy), (0, 255, 0), 2)
    cv2.line(frame, (cx, cy - 15), (cx, cy + 15), (0, 255, 0), 2)
    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
    
    # Panel informativo più grande
    info_height = 180
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, height - info_height), (width, height), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)
    
    # Linea separatore
    cv2.line(frame, (0, height - info_height), (width, height - info_height), (100, 100, 100), 2)
    
    # Testi informativi con font più grande
    r, g, b = color_data['rgb']
    h, s, v = color_data['hsv']
    y_start = height - info_height + 30
    
    # Nome colore grande
    cv2.putText(frame, color_data['name_it'], (20, y_start), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(frame, f"({color_data['name_en']})", (20, y_start + 28), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
    
    # Codici colore
    cv2.putText(frame, f"HEX: {color_data['hex']}", (20, y_start + 55), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, f"RGB: ({r}, {g}, {b})", (20, y_start + 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    
    # Barre HSV visuali
    bar_x = 280
    bar_width = 150
    bar_height = 12
    
    # Barra Hue (arcobaleno)
    cv2.putText(frame, "H:", (bar_x - 25, y_start + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    for i in range(bar_width):
        hue_color = cv2.cvtColor(np.uint8([[[int(i * 180 / bar_width), 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
        cv2.line(frame, (bar_x + i, y_start), (bar_x + i, y_start + bar_height), tuple(map(int, hue_color)), 1)
    hue_pos = int(h * bar_width / 180)
    cv2.rectangle(frame, (bar_x + hue_pos - 2, y_start - 2), (bar_x + hue_pos + 2, y_start + bar_height + 2), (255, 255, 255), 2)
    
    # Barra Saturazione
    cv2.putText(frame, "S:", (bar_x - 25, y_start + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    for i in range(bar_width):
        sat_val = int(i * 255 / bar_width)
        cv2.line(frame, (bar_x + i, y_start + 25), (bar_x + i, y_start + 25 + bar_height), (sat_val, sat_val, sat_val), 1)
    sat_pos = int(s * bar_width / 255)
    cv2.rectangle(frame, (bar_x + sat_pos - 2, y_start + 23), (bar_x + sat_pos + 2, y_start + 25 + bar_height + 2), (0, 255, 0), 2)
    
    # Barra Valore/Luminosità
    cv2.putText(frame, "V:", (bar_x - 25, y_start + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    for i in range(bar_width):
        val_val = int(i * 255 / bar_width)
        cv2.line(frame, (bar_x + i, y_start + 50), (bar_x + i, y_start + 50 + bar_height), (val_val, val_val, val_val), 1)
    val_pos = int(v * bar_width / 255)
    cv2.rectangle(frame, (bar_x + val_pos - 2, y_start + 48), (bar_x + val_pos + 2, y_start + 50 + bar_height + 2), (0, 255, 255), 2)
    
    # Valori numerici HSV
    cv2.putText(frame, f"{h}", (bar_x + bar_width + 10, y_start + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(frame, f"{s}", (bar_x + bar_width + 10, y_start + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(frame, f"{v}", (bar_x + bar_width + 10, y_start + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    # Barre RGB
    rgb_x = 500
    cv2.putText(frame, "R:", (rgb_x - 25, y_start + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 255), 1)
    cv2.rectangle(frame, (rgb_x, y_start), (rgb_x + int(r * 100 / 255), y_start + bar_height), (100, 100, 255), -1)
    cv2.rectangle(frame, (rgb_x, y_start), (rgb_x + 100, y_start + bar_height), (100, 100, 100), 1)
    
    # Anteprima colore grande con bordo
    preview_x = width - 130
    preview_y = height - info_height + 20
    preview_size = 90
    cv2.rectangle(frame, (preview_x, preview_y), (preview_x + preview_size, preview_y + preview_size), color_data['bgr'], -1)
    cv2.rectangle(frame, (preview_x, preview_y), (preview_x + preview_size, preview_y + preview_size), (255, 255, 255), 3)
    
    # Barra spettro colori in alto
    spectrum_height = 8
    for i in range(width):
        hue_val = int(i * 180 / width)
        spectrum_color = cv2.cvtColor(np.uint8([[[hue_val, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
        cv2.line(frame, (i, 0), (i, spectrum_height), tuple(map(int, spectrum_color)), 1)
    # Indicatore posizione hue corrente
    hue_indicator_x = int(h * width / 180)
    cv2.rectangle(frame, (hue_indicator_x - 3, 0), (hue_indicator_x + 3, spectrum_height + 5), (255, 255, 255), 2)
    
    # Etichetta Audio ON/OFF (per TTS)
    cv2.putText(frame, "[V] Audio", (width - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return frame
    
    return frame


def print_color_to_console(color_data: dict, verbose: bool = True) -> None:
    """Stampa le informazioni del colore nella console."""
    if verbose:
        print("\n" + "=" * 50)
        print(f"🎨 COLORE RILEVATO")
        print("=" * 50)
        print(f"  Nome:    {color_data['name_it']} ({color_data['name_en']})")
        print(f"  HEX:     {color_data['hex']}")
        print(f"  RGB:     {color_data['rgb']}")
        print(f"  HSV:     {color_data['hsv']}")
        print("=" * 50)
    else:
        print(f"[{color_data['name_it']}] HEX: {color_data['hex']} | RGB: {color_data['rgb']}")


def list_cameras() -> list:
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


def select_camera() -> int:
    """Permette all'utente di selezionare una webcam."""
    print("\n🔍 Ricerca webcam disponibili...")
    cameras = list_cameras()
    
    if not cameras:
        # Fallback a 0 se non trova nulla (a volte succede su mac)
        print("⚠️ Nessuna webcam rilevata esplicitamente, provo con ID 0...")
        return 0
    
    print(f"\n📷 Webcam trovate: {len(cameras)}")
    for i, cam_id in enumerate(cameras):
        print(f"  [{cam_id}] Camera {cam_id}")
    
    if len(cameras) == 1:
        print(f"\n✅ Selezionata automaticamente Camera {cameras[0]}")
        return cameras[0]
    
    while True:
        try:
            choice = input(f"\n👉 Seleziona camera (0-{cameras[-1]}): ")
            cam_id = int(choice)
            if cam_id in cameras:
                return cam_id
            print("❌ Camera non valida!")
        except ValueError:
            print("❌ Inserisci un numero valido!")


def main():
    """Funzione principale."""
    print("\n" + "=" * 60)
    print("  🎨 WEBCAM COLOR DETECTOR - Professional Edition")
    print("  Rileva i colori con precisione CIE LAB Delta-E")
    print("=" * 60)
    
    # Seleziona la webcam
    camera_id = select_camera()
    
    # Inizializza la webcam
    print(f"\n📷 Avvio webcam {camera_id}...")
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print("❌ Impossibile aprire la webcam!")
        return
    
    # Imposta risoluzione (HD per la UI)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # --- INIZIALIZZAZIONE ARDUINO ---
    global arduino
    if serial:
        try:
            print(f"Tentativo di connessione a {ARDUINO_PORT}...")
            arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.05)
            time.sleep(2) # Pausa tecnica per dare tempo ad Arduino di resettarsi
            print("✅ Arduino CONNESSO con successo!")
        except Exception as e:
            print(f"❌ ERRORE CONNESSIONE ARDUINO: {e}")
            print("Controlla che il Monitor Seriale di Arduino IDE sia CHIUSO.")
            arduino = None
    # --------------------------------

    
    print("\n" + "-" * 60)
    print("  CONTROLLI:")
    print("  [SPAZIO] - Cattura e stampa colore in console")
    print("  [C]      - Stampa continua colori (toggle)")
    print("  [V]      - Audio feedback (toggle)")
    print("  [+/-]    - Aumenta/Diminuisci area di rilevamento")
    print("  [S]      - Salva screenshot")
    print("  [Q/ESC]  - Esci")
    print("-" * 60 + "\n")
    print("  LEGENDA PRECISIONE: ● = Eccellente | ◐ = Buona | ○ = Appross.")
    print("-" * 60 + "\n")
    
    roi_size = 50
    continuous_mode = False
    audio_mode = False
    last_color = None
    last_spoken_color = None
    
    # Variabili per lo smoothing (Arduino)
    prev_r, prev_g, prev_b = 0, 0, 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Errore lettura frame!")
                break
            
            # Rileva il colore (Analisi Dominante)
            color_data = detect_dominant_color(frame, roi_size)
            
            # Modalità continua
            if continuous_mode:
                if last_color != color_data['name_en']:
                    print_color_to_console(color_data, verbose=False)
                    last_color = color_data['name_en']
            
            # Audio feedback
            if audio_mode:
                # Rimuovi indicatore precisione per TTS
                clean_name = color_data['name_it'].replace(' ●', '').replace(' ◐', '').replace(' ○', '')
                if last_spoken_color != clean_name:
                    # speak_color(clean_name) # TTS Disabilitato per note musicali
                    last_spoken_color = clean_name
            
            # --- 3. LOGICA INVIO DATI AD ARDUINO (Con Smoothing e Gamma) ---
            if arduino is not None and arduino.is_open:
                try:
                    # Recupera i valori RGB target dal rilevamento
                    target_r, target_g, target_b = color_data['rgb']
                    
                    # 3.1 BLACK THRESHOLD (Taglio del nero)
                    # Verifica luminosità per spegnere se troppo scuro
                    # Usiamo formula luminosità standard
                    luminance = (0.299 * target_r + 0.587 * target_g + 0.114 * target_b)
                    if luminance < BLACK_THRESHOLD:
                         target_r, target_g, target_b = 0, 0, 0
                    
                    # 3.2 SMOOTHING (Media pesata)
                    # Formula: Nuovo = (Vecchio * (1-S)) + (Target * S)
                    curr_r = int((prev_r * (1 - SMOOTHING)) + (target_r * SMOOTHING))
                    curr_g = int((prev_g * (1 - SMOOTHING)) + (target_g * SMOOTHING))
                    curr_b = int((prev_b * (1 - SMOOTHING)) + (target_b * SMOOTHING))
                    
                    # Aggiorna stati precedenti
                    prev_r, prev_g, prev_b = curr_r, curr_g, curr_b
                    
                    # 3.3 APPLICAZIONE GAMMA
                    final_r = apply_gamma(curr_r)
                    final_g = apply_gamma(curr_g)
                    final_b = apply_gamma(curr_b)
                    
                    # --- 4. CALCOLO DELL'ONDA DEL RESPIRO (Living Light) ---
                    # Usiamo il tempo corrente per generare un'onda che va da -1 a 1, poi la normalizziamo
                    wave = math.sin(time.time() * PULSE_SPEED) 
                    
                    # Trasformiamo l'onda da [-1, 1] a [0, 1]
                    norm_wave = (wave + 1) / 2.0 
                    
                    # Calcoliamo il fattore di luminosità attuale
                    pulse_factor = MIN_BRIGHTNESS + (norm_wave * (1.0 - MIN_BRIGHTNESS))
                    
                    # Applichiamo il respiro al colore finale
                    pulsing_r = int(final_r * pulse_factor)
                    pulsing_g = int(final_g * pulse_factor)
                    pulsing_b = int(final_b * pulse_factor)
                    
                    # Inviamo i dati come bytes: "R,G,B\n"
                    msg = f"{pulsing_r},{pulsing_g},{pulsing_b}\n"
                    arduino.write(msg.encode('utf-8'))
                    
                except Exception as e:
                    # Non riempire la console di errori se qualcosa va storto momentaneamente
                    pass
            # --------------------------------

            
            # === SINESTESIA (MODALITÀ SONORA) ===
            # Rimuovi indicatore precisione
            clean_color_name = color_data['name_en'].replace(' ●', '').replace(' ◐', '').replace(' ○', '')
            
            # Se siamo in modalità audio (V) o se vogliamo che suoni sempre
            # Per ora usiamo il toggle audio_mode per attivare/disattivare la musica
            if audio_mode:
                # Passa l'intero dato HSV per calcolo frequenza dinamico
                play_color_note(color_data['hsv'])
            # ------------------------------------
            
            # Disegna overlay
            display_frame = draw_info_overlay(frame, color_data)
            
            # Indicatore audio sullo schermo
            if audio_mode:
                cv2.putText(display_frame, "🎵 MUSIC MODE ON", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Mostra il frame
            cv2.imshow('Webcam Color Detector - Professional', display_frame)
            
            # Gestione input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q o ESC
                print("\n👋 Arrivederci!")
                break
            elif key == ord(' '):  # Spazio
                print_color_to_console(color_data, verbose=True)
                if audio_mode:
                    clean_name = color_data['name_it'].replace(' ●', '').replace(' ◐', '').replace(' ○', '')
                    # speak_color(clean_name)
            elif key == ord('c'):  # Toggle modalità continua
                continuous_mode = not continuous_mode
                status = "ATTIVATA" if continuous_mode else "DISATTIVATA"
                print(f"\n🔄 Modalità continua: {status}")
            elif key == ord('v'):  # Toggle audio
                audio_mode = not audio_mode
                status = "ATTIVATO" if audio_mode else "DISATTIVATO"
                print(f"\n🔊 Audio feedback: {status}")
                if audio_mode:
                    # speak_color("Audio attivato")
                    pass
            elif key == ord('+') or key == ord('='):
                roi_size = min(200, roi_size + 10)
                print(f"📐 Area rilevamento: {roi_size}x{roi_size}")
            elif key == ord('-'):
                roi_size = max(10, roi_size - 10)
                print(f"📐 Area rilevamento: {roi_size}x{roi_size}")
            elif key == ord('s'):
                filename = f"color_capture_{color_data['hex'][1:]}.png"
                cv2.imwrite(filename, frame)
                print(f"📸 Screenshot salvato: {filename}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if arduino:
            try:
                arduino.close()
                print("Connessione Arduino chiusa.")
            except:
                pass



if __name__ == "__main__":
    main()
