import cv2
import numpy as np
from collections import namedtuple
import subprocess
import threading
import time
import os
import sys
import platform
import math
import json
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
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

    def generate_drum_hit(self, freq, duration=0.4, volume=0.5):
        """
        Genera un colpo di batteria sintetico.
        Noise burst + sine sweep discendente per un suono percussivo.
        """
        if not PYGAME_AVAILABLE: return None
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Corpo: Sine sweep da freq alta a freq bassa (kick-like)
        sweep_freq = freq * 4.0 * np.exp(-8.0 * t)
        body = np.sin(2 * np.pi * sweep_freq * t) * 0.8
        
        # Rumore percussivo (snare/hi-hat character)
        noise = np.random.uniform(-1, 1, n_samples) * 0.3
        noise_env = np.exp(-15.0 * t)  # Decadimento molto rapido
        noise *= noise_env
        
        wave = (body + noise) * volume * 0.5
        
        # Envelope: attacco istantaneo, decadimento rapido
        envelope = np.exp(-6.0 * t)
        attack_len = int(self.sample_rate * 0.005)
        if attack_len > 0:
            envelope[:attack_len] *= np.linspace(0, 1, attack_len)
        
        wave *= envelope
        
        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_synth_pad(self, freq, duration=2.0, volume=0.5):
        """
        Genera un pad sintetico ambient.
        Layer di onde leggermente detunate con attacco lento.
        """
        if not PYGAME_AVAILABLE: return None
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # 3 oscillatori leggermente detunati (chorus effect)
        wave  = np.sin(2 * np.pi * freq * t) * 0.5
        wave += np.sin(2 * np.pi * (freq * 1.005) * t) * 0.3  # +5 cents
        wave += np.sin(2 * np.pi * (freq * 0.995) * t) * 0.3  # -5 cents
        # Sub oscillatore (ottava sotto)
        wave += np.sin(2 * np.pi * (freq * 0.5) * t) * 0.2
        
        wave *= volume * 0.3
        
        # Envelope: attacco lento, sustain, rilascio lento
        attack_time = 0.3
        release_time = 0.5
        envelope = np.ones(n_samples)
        attack_len = int(self.sample_rate * attack_time)
        release_len = int(self.sample_rate * release_time)
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        if release_len > 0 and release_len < n_samples:
            envelope[-release_len:] = np.linspace(1, 0, release_len)
        
        wave *= envelope
        
        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_pluck(self, freq, duration=1.0, volume=0.5):
        """
        Genera un suono di corda pizzicata (Karplus-Strong semplificato).
        Breve burst di rumore filtrato con rapido decadimento.
        """
        if not PYGAME_AVAILABLE: return None
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Impulso iniziale: mix di noise + fondamentale
        wave = np.sin(2 * np.pi * freq * t) * 0.6
        wave += np.sin(2 * np.pi * freq * 2 * t) * 0.25  # 2a armonica
        wave += np.sin(2 * np.pi * freq * 3 * t) * 0.1   # 3a armonica
        
        # Rumore iniziale breve (simulazione plettro)
        noise_duration = 0.015
        noise_samples = int(self.sample_rate * noise_duration)
        noise = np.random.uniform(-1, 1, min(noise_samples, n_samples)) * 0.4
        wave[:len(noise)] += noise
        
        wave *= volume * 0.4
        
        # Envelope: attacco immediato, decadimento rapido
        envelope = np.exp(-4.0 * t)
        attack_len = int(self.sample_rate * 0.003)
        if attack_len > 0:
            envelope[:attack_len] *= np.linspace(0, 1, attack_len)
        
        wave *= envelope
        
        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_organ(self, freq, duration=1.5, volume=0.5):
        """
        Genera un suono d'organo (armoniche dispari sovrapposte).
        Simile a un'onda quadra addolcita, ricco e sostenuto.
        """
        if not PYGAME_AVAILABLE: return None
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Armoniche dispari (carattere organo/square wave)
        wave  = np.sin(2 * np.pi * freq * t) * 1.0       # Fondamentale
        wave += np.sin(2 * np.pi * freq * 3 * t) * 0.33   # 3a armonica
        wave += np.sin(2 * np.pi * freq * 5 * t) * 0.2    # 5a armonica
        wave += np.sin(2 * np.pi * freq * 7 * t) * 0.14   # 7a armonica
        wave += np.sin(2 * np.pi * freq * 9 * t) * 0.11   # 9a armonica
        
        # Leggero tremolo (vibrato d'organo)
        tremolo = 1.0 + (0.03 * np.sin(2 * np.pi * 5.5 * t))
        wave *= tremolo
        
        wave *= volume * 0.25
        
        # Envelope: attacco veloce, sustain piatto, rilascio medio  
        envelope = np.ones(n_samples)
        attack_len = int(self.sample_rate * 0.03)
        release_len = int(self.sample_rate * 0.3)
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        if release_len > 0 and release_len < n_samples:
            envelope[-release_len:] *= np.exp(-3.0 * np.linspace(0, 1, release_len))
        
        wave *= envelope
        
        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    # ========================================================
    # LIBRERIA SYNTH RILASSANTI / MEDITATIVI
    # ========================================================

    def generate_crystal_bowl(self, freq, duration=3.0, volume=0.5):
        """
        Campana di Cristallo Tibetana.
        Sinusoide purissima con armoniche pari e battimento lento
        che crea un effetto ipnotico e avvolgente.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Fondamentale pura
        wave = np.sin(2 * np.pi * freq * t) * 1.0
        # 2a armonica leggermente detunata (beating a ~1Hz)
        wave += np.sin(2 * np.pi * (freq * 2.001) * t) * 0.35
        # 3a armonica pura (dolcezza)
        wave += np.sin(2 * np.pi * (freq * 3.0) * t) * 0.15
        # 5a armonica appena percepibile (brillantezza cristallina)
        wave += np.sin(2 * np.pi * (freq * 5.0) * t) * 0.05

        wave *= volume * 0.3

        # Envelope: attacco morbido, decadimento lunghissimo
        envelope = np.exp(-0.8 * t)
        attack_len = int(self.sample_rate * 0.05)
        if attack_len > 0:
            envelope[:attack_len] *= np.linspace(0, 1, attack_len)

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_deep_drone(self, freq, duration=3.5, volume=0.5):
        """
        Drone Profondo Meditativo.
        Sub-bass con oscillatori detunati e modulazione LFO lenta.
        Crea una vibrazione profonda e grounding.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Usiamo frequenza bassa (un'ottava sotto)
        low_freq = freq * 0.5

        # 3 oscillatori detunati (effetto chorus denso)
        wave  = np.sin(2 * np.pi * low_freq * t) * 0.6
        wave += np.sin(2 * np.pi * (low_freq * 1.003) * t) * 0.4
        wave += np.sin(2 * np.pi * (low_freq * 0.997) * t) * 0.4

        # Sub-bass un'ottava ancora sotto
        wave += np.sin(2 * np.pi * (low_freq * 0.5) * t) * 0.3

        # LFO lento sull'ampiezza (respiro)
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.3 * t)
        wave *= lfo

        wave *= volume * 0.25

        # Envelope: attacco molto lento, sustain lungo, rilascio graduale
        envelope = np.ones(n_samples)
        attack_len = int(self.sample_rate * 0.8)
        release_len = int(self.sample_rate * 1.0)
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        if release_len > 0 and release_len < n_samples:
            envelope[-release_len:] = np.linspace(1, 0, release_len)

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_ethereal_choir(self, freq, duration=2.5, volume=0.5):
        """
        Coro Etereo / Voci Angeliche.
        Formanti vocali sintetiche (ah/oh) con vibrato delicato.
        Evoca un coro celestiale.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Vibrato lento e delicato
        vibrato = np.sin(2 * np.pi * 4.5 * t) * 0.008
        mod_freq = freq * (1 + vibrato)

        # Formante "ah" (armoniche 1, 2, 3 con pesi specifici)
        wave  = np.sin(2 * np.pi * mod_freq * t) * 0.5
        wave += np.sin(2 * np.pi * mod_freq * 2 * t) * 0.35
        wave += np.sin(2 * np.pi * mod_freq * 3 * t) * 0.2

        # Seconda voce (quinta sopra, leggermente detunata)
        freq2 = freq * 1.498
        wave += np.sin(2 * np.pi * freq2 * (1 + vibrato * 0.7) * t) * 0.25
        wave += np.sin(2 * np.pi * freq2 * 2 * (1 + vibrato * 0.7) * t) * 0.15

        # Terza voce (ottava sopra)
        freq3 = freq * 2.003
        wave += np.sin(2 * np.pi * freq3 * (1 + vibrato * 1.2) * t) * 0.15

        wave *= volume * 0.2

        # Envelope: attacco lentissimo, sustain, rilascio lungo
        envelope = np.ones(n_samples)
        attack_len = int(self.sample_rate * 0.6)
        release_len = int(self.sample_rate * 0.8)
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len) ** 1.5
        if release_len > 0 and release_len < n_samples:
            envelope[-release_len:] = np.linspace(1, 0, release_len) ** 1.5

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_ocean_pad(self, freq, duration=3.0, volume=0.5):
        """
        Pad Oceanico.
        Noise filtrato + strati sinusoidali con modulazione ciclica
        che simula il movimento delle onde.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Layer sinusoidale base (pad morbido)
        wave  = np.sin(2 * np.pi * freq * t) * 0.4
        wave += np.sin(2 * np.pi * (freq * 1.002) * t) * 0.3
        wave += np.sin(2 * np.pi * (freq * 0.5) * t) * 0.2

        # Noise filtrato (simulazione "shhh" delle onde)
        noise = np.random.uniform(-1, 1, n_samples) * 0.15
        # Filtro passa-basso semplice (media mobile)
        kernel_size = int(self.sample_rate * 0.002)
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            noise = np.convolve(noise, kernel, mode='same')

        wave += noise

        # Modulazione ciclica (onda che va e viene)
        ocean_mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t)
        wave *= ocean_mod

        wave *= volume * 0.3

        # Envelope: fade-in e fade-out graduali
        envelope = np.ones(n_samples)
        fade_len = int(self.sample_rate * 0.5)
        if fade_len > 0:
            envelope[:fade_len] = np.linspace(0, 1, fade_len)
        if fade_len > 0 and fade_len < n_samples:
            envelope[-fade_len:] = np.linspace(1, 0, fade_len)

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_wind_chimes(self, freq, duration=2.0, volume=0.5):
        """
        Campanelli al Vento.
        Cluster di sinusoidi ad alta frequenza con decay randomizzati.
        Ogni nota è un piccolo tintinnio cristallino.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        wave = np.zeros(n_samples)

        # 5 campanelli a frequenze armoniche/inharmoniche
        chime_ratios = [1.0, 1.5, 2.0, 2.67, 3.17]
        chime_decays = [2.5, 3.0, 3.5, 4.0, 2.8]
        chime_delays = [0.0, 0.08, 0.15, 0.25, 0.35]

        for ratio, decay, delay in zip(chime_ratios, chime_decays, chime_delays):
            chime_freq = freq * ratio * 2  # Registro alto
            delay_samples = int(self.sample_rate * delay)
            if delay_samples < n_samples:
                t_local = np.linspace(0, duration - delay, n_samples - delay_samples, False)
                chime = np.sin(2 * np.pi * chime_freq * t_local) * 0.3
                chime *= np.exp(-decay * t_local)
                wave[delay_samples:] += chime


        wave *= volume * 0.35

        # Micro fade-in
        attack_len = int(self.sample_rate * 0.01)
        if attack_len > 0 and attack_len < n_samples:
            wave[:attack_len] *= np.linspace(0, 1, attack_len)

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_binaural_theta(self, freq, duration=3.0, volume=0.5):
        """
        Toni Binaurali Theta (4-8 Hz).
        Due toni a frequenze vicine creano una differenza nella banda Theta,
        associata a meditazione profonda e rilassamento.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Differenza di ~6Hz (centro banda theta)
        theta_diff = 6.0
        freq_left = freq
        freq_right = freq + theta_diff

        # Mono mix dei due toni (in mono il battimento è udibile)
        wave  = np.sin(2 * np.pi * freq_left * t) * 0.5
        wave += np.sin(2 * np.pi * freq_right * t) * 0.5

        # Aggiunta di un pad morbido di sfondo
        wave += np.sin(2 * np.pi * (freq * 0.5) * t) * 0.15

        wave *= volume * 0.35

        # Envelope: fade-in molto lento, sustain, fade-out lento
        envelope = np.ones(n_samples)
        fade_in_len = int(self.sample_rate * 0.8)
        fade_out_len = int(self.sample_rate * 0.8)
        if fade_in_len > 0:
            envelope[:fade_in_len] = np.linspace(0, 1, fade_in_len)
        if fade_out_len > 0 and fade_out_len < n_samples:
            envelope[-fade_out_len:] = np.linspace(1, 0, fade_out_len)

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_glass_harmonica(self, freq, duration=2.5, volume=0.5):
        """
        Armonica a Bicchieri di Cristallo.
        Sinusoide pura con vibrato delicato e armoniche alte.
        Suono delicato, fragile e trasparente.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # Vibrato delicatissimo
        vibrato = np.sin(2 * np.pi * 5.0 * t) * 0.005
        mod_freq = freq * (1 + vibrato)

        # Fondamentale (molto pura)
        wave = np.sin(2 * np.pi * mod_freq * t) * 1.0
        # Armoniche alte (brillantezza cristallina)
        wave += np.sin(2 * np.pi * mod_freq * 3 * t) * 0.12
        wave += np.sin(2 * np.pi * mod_freq * 5 * t) * 0.06
        wave += np.sin(2 * np.pi * mod_freq * 7 * t) * 0.03

        wave *= volume * 0.3

        # Envelope: attacco morbido, decay lento
        envelope = np.exp(-1.2 * t)
        attack_len = int(self.sample_rate * 0.08)
        if attack_len > 0:
            envelope[:attack_len] *= np.linspace(0, 1, attack_len)

        wave *= envelope

        audio_data = (wave * 32767).astype(np.int16)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        return pygame.sndarray.make_sound(audio_data)

    def generate_cosmic_pad(self, freq, duration=3.0, volume=0.5):
        """
        Pad Cosmico Spaziale.
        FM synthesis leggera con modulazione lenta e riverbero simulato.
        Suono vasto, spaziale e trascendente.
        """
        if not PYGAME_AVAILABLE: return None

        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # FM synthesis: modulatore lento per texture spaziale
        mod_index = 0.8 + 0.5 * np.sin(2 * np.pi * 0.2 * t)  # Indice che cambia
        modulator = np.sin(2 * np.pi * (freq * 2.01) * t) * mod_index

        # Carrier con FM
        wave = np.sin(2 * np.pi * freq * t + modulator) * 0.5

        # Layer pad base (calore)
        wave += np.sin(2 * np.pi * freq * t) * 0.3
        wave += np.sin(2 * np.pi * (freq * 1.004) * t) * 0.2

        # Ottava sopra appena percepibile
        wave += np.sin(2 * np.pi * (freq * 2.0) * t) * 0.1

        # Riverbero simulato (eco ripetuto e attenuato)
        delay_samples = int(self.sample_rate * 0.08)
        if delay_samples < n_samples:
            delayed = np.zeros(n_samples)
            delayed[delay_samples:] = wave[:-delay_samples] * 0.3
            wave += delayed

        wave *= volume * 0.2

        # Envelope: attacco lento, sustain, rilascio lungo
        envelope = np.ones(n_samples)
        attack_len = int(self.sample_rate * 0.5)
        release_len = int(self.sample_rate * 0.8)
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len) ** 1.3
        if release_len > 0 and release_len < n_samples:
            envelope[-release_len:] = np.linspace(1, 0, release_len) ** 1.3

        wave *= envelope

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
NOTE_COOLDOWN = 0.5  # Cooldown minimo tra note diverse
current_playing_freq = 0
same_note_repeat_count = 0  # Contatore ripetizioni stessa nota

# ============================================================
# STRUMENTI MUSICALI - Selezione Timbro
# ============================================================
INSTRUMENTS = [
    {'name': 'Zen Bell',  'icon': 'BELL',  'method': 'generate_relaxing_wave'},
    {'name': 'Drums',     'icon': 'DRUM',  'method': 'generate_drum_hit'},
    {'name': 'Synth Pad', 'icon': 'SYNTH', 'method': 'generate_synth_pad'},
    {'name': 'Pluck',     'icon': 'PLUCK', 'method': 'generate_pluck'},
    {'name': 'Organ',     'icon': 'ORGAN', 'method': 'generate_organ'},
    # --- LIBRERIA SYNTH RILASSANTI ---
    {'name': 'Crystal Bowl',     'icon': '🔮',    'method': 'generate_crystal_bowl'},
    {'name': 'Deep Drone',       'icon': '🌊',    'method': 'generate_deep_drone'},
    {'name': 'Ethereal Choir',   'icon': '👼',    'method': 'generate_ethereal_choir'},
    {'name': 'Ocean Pad',        'icon': '🌅',    'method': 'generate_ocean_pad'},
    {'name': 'Wind Chimes',      'icon': '🎐',    'method': 'generate_wind_chimes'},
    {'name': 'Binaural Theta',   'icon': '🧘',    'method': 'generate_binaural_theta'},
    {'name': 'Glass Harmonica',  'icon': '✨',    'method': 'generate_glass_harmonica'},
    {'name': 'Cosmic Pad',       'icon': '🪐',    'method': 'generate_cosmic_pad'},
]
current_instrument_index = 0


# ============================================================
# CONFIGURAZIONE ARDUINO & PARAMETRI OTTIMIZZAZIONE
# ============================================================

# --- FUNZIONE DI RICERCA AUTOMATICA ---
def find_arduino_port():
    print("🔍 Scansione porte seriali...")
    ports = list(serial.tools.list_ports.comports())
    
    for p in ports:
        # Controlla se nella descrizione della porta c'è "Arduino" o parole chiave simili
        # (Funziona sia su Mac che su Raspberry Pi)
        if "Arduino" in p.description or "usbmodem" in p.device or "ttyACM" in p.device or "usbserial" in p.device or "ttyUSB" in p.device:
            print(f"✅ Arduino trovato su: {p.device}")
            return p.device
            
    print("❌ Nessun Arduino trovato!")
    return None

ARDUINO_PORT = None  # Verrà impostato in main()
BAUD_RATE = 115200

# 2. Parametri di Ottimizzazione (GIOCA CON QUESTI!)
GAMMA = 2.5           
SMOOTHING = 0.15      
BLACK_THRESHOLD = 5   # Abbassato drasticamente per debug  

# --- CONFIGURAZIONE EFFETTO RESPIRO ---
PULSE_SPEED = 2.0     # Velocità del respiro
MIN_BRIGHTNESS = 0.3  # Luminosità minima

# --- CONFIGURAZIONE LOGICA LED (FIX "ROSA" SUL PI) ---
# Se il tuo LED è Common Anode (o vedi i colori invertiti/rosa), imposta True.
# Puoi cambiarlo in tempo reale premendo [I]
COMMON_ANODE = False  

# --- CONFIGURAZIONE HEADLESS (SENZA MONITOR) ---
HEADLESS_MODE = False  # <--- METTI TRUE QUANDO LO USI SENZA MONITOR!

# ============================================================
# CONFIGURAZIONE ACCURATEZZA COLORE (Interventi 1-5)
# ============================================================
CLAHE_ENABLED = True          # Intervento 1: Equalizzazione luminosità locale
CLAHE_CLIP_LIMIT = 2.0        # Aggressività CLAHE (1.0=leggero, 3.0=forte)
WB_ENABLED = False            # Intervento 2: Compensazione White Balance (disabilitato)
KMEANS_ENABLED = True         # Intervento 3: K-Means colore dominante
KMEANS_CLUSTERS = 3           # Numero di cluster K-Means
BRADFORD_ENABLED = False      # Intervento 4: Adattamento cromatico Bradford (richiede WB)
TEMPORAL_SMOOTH_ENABLED = True # Intervento 5: Smoothing temporale
TEMPORAL_ALPHA = 0.35         # EMA alpha (0.1=stabile, 0.5=reattivo)

# Stato globale White Balance
wb_gains = None  # Verrà impostato con calibrazione [W]

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
    """Riproduce la nota basata sui valori HSV precisi, usando lo strumento corrente."""
    global last_played_note_time, current_playing_freq, same_note_repeat_count
    
    if not PYGAME_AVAILABLE: return
    
    current_time = time.time()
    elapsed = current_time - last_played_note_time
    
    if elapsed < NOTE_COOLDOWN:
        return
        
    h, s, v = hsv_tuple
    
    # Ignora se troppo nero (silenzio)
    if v < BLACK_THRESHOLD:
        return

    freq = get_frequency_from_hsv(h, s, v)
    
    # Controlla se è una nota nuova o la stessa
    is_new_note = abs(freq - current_playing_freq) > 3
    
    if is_new_note:
        # Nota nuova! Suona subito e resetta il contatore
        same_note_repeat_count = 0
    else:
        # Stessa nota: cooldown adattivo che cresce ad ogni ripetizione
        # 1a ripetizione: 3s, 2a: 6s, 3a: 12s, poi max 15s
        adaptive_cooldown = min(15.0, 3.0 * (2 ** same_note_repeat_count))
        if elapsed < adaptive_cooldown:
            return
        same_note_repeat_count += 1
    
    # Usa lo strumento corrente selezionato
    instrument = INSTRUMENTS[current_instrument_index]
    generate_method = getattr(synth, instrument['method'])
    sound = generate_method(freq, duration=2.0, volume=0.5)
    if sound:
        sound.play()
        last_played_note_time = current_time
        current_playing_freq = freq


# Stato arpeggio
_arpeggio_index = 0
_arpeggio_last_time = 0
ARPEGGIO_INTERVAL = 0.25  # Intervallo tra note dell'arpeggio (secondi)

def play_arpeggio_note(grid_colors: list):
    """Suona un arpeggio ciclico con solo note UNICHE (colori diversi = note diverse)."""
    global _arpeggio_index, _arpeggio_last_time, _arpeggio_freqs
    
    if not PYGAME_AVAILABLE or not grid_colors:
        return
    
    current_time = time.time()
    if (current_time - _arpeggio_last_time) < ARPEGGIO_INTERVAL:
        return
    
    # Calcola le frequenze uniche dalla griglia
    unique_freqs = []
    seen = set()
    for color in grid_colors:
        r, g, b = color['rgb']
        pixel = np.uint8([[[b, g, r]]])
        hsv_pixel = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
        h, s, v = hsv_pixel[0][0]
        
        if v < BLACK_THRESHOLD:
            continue
        
        freq = get_frequency_from_hsv(h, s, v)
        # Arrotonda per raggruppare frequenze vicine (stessa nota)
        freq_rounded = round(freq)
        if freq_rounded not in seen:
            seen.add(freq_rounded)
            unique_freqs.append(freq)
    
    if not unique_freqs:
        return
    
    # Cicla solo tra le note uniche
    _arpeggio_index = _arpeggio_index % len(unique_freqs)
    freq = unique_freqs[_arpeggio_index]
    
    instrument = INSTRUMENTS[current_instrument_index]
    generate_method = getattr(synth, instrument['method'])
    sound = generate_method(freq, duration=1.0, volume=0.4)
    if sound:
        sound.play()
    
    _arpeggio_last_time = current_time
    _arpeggio_index += 1

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


def get_color_name_from_rgb(rgb_tuple: tuple) -> tuple:
    """
    Determina il nome del colore direttamente da RGB usando LAB Delta-E.
    Evita il roundtrip HSV→RGB che perde precisione.
    Ritorna (nome_en, nome_it, hex_code) o None se non trovato.
    """
    name_en, name_it, hex_code, distance = find_closest_color(rgb_tuple)
    
    # Aggiungi indicatore di precisione
    if distance < 5:
        precision = "●"  # Molto preciso
    elif distance < 15:
        precision = "◐"  # Buono
    else:
        precision = "○"  # Approssimativo
    
    return (f"{name_en} {precision}", f"{name_it} {precision}", hex_code)


# ============================================================
# FUNZIONI PIPELINE ACCURATEZZA COLORE
# ============================================================

def _apply_clahe(roi: np.ndarray) -> np.ndarray:
    """
    Intervento 1: CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Equalizza la luminosità locale nel canale L dello spazio LAB.
    Recupera dettaglio nei rossi scuri che la camera comprime.
    """
    if roi.size == 0:
        return roi
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=(4, 4))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _apply_white_balance(roi: np.ndarray, gains: np.ndarray) -> np.ndarray:
    """
    Intervento 2: Applica i guadagni White Balance pre-calibrati.
    Compensa la tinta della luce ambiente.
    """
    corrected = roi.astype(np.float32) * gains
    return np.clip(corrected, 0, 255).astype(np.uint8)


def _extract_dominant_kmeans(roi: np.ndarray, n_clusters: int = 3) -> np.ndarray:
    """
    Intervento 3: Estrae il colore dominante usando K-Means.
    Ignora outlier (ombre, riflessi) prendendo il cluster più grande.
    """
    pixels = roi.reshape(-1, 3).astype(np.float32)
    
    if len(pixels) < n_clusters:
        return np.mean(pixels, axis=0).astype(int)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, n_clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS
    )
    
    # Prendi il cluster con più pixel (colore dominante)
    dominant_idx = np.argmax(np.bincount(labels.flatten()))
    return centers[dominant_idx].astype(int)


def _apply_bradford_cat(rgb: tuple, gains: np.ndarray) -> tuple:
    """
    Intervento 4: Chromatic Adaptation Transform (Bradford).
    Trasforma i colori dallo spazio dell'illuminante stimato a D65 standard.
    L'illuminante viene stimato dai guadagni WB.
    """
    # Matrice Bradford (Forward: XYZ → LMS cone space)
    M_brad = np.array([
        [ 0.8951,  0.2664, -0.1614],
        [-0.7502,  1.7135,  0.0367],
        [ 0.0389, -0.0685,  1.0296]
    ])
    M_brad_inv = np.linalg.inv(M_brad)
    
    # D65 reference white (standard daylight)
    d65_xyz = np.array([0.95047, 1.00000, 1.08883])
    
    # Stima illuminante sorgente dai guadagni WB
    # Guadagni alti = canale debole = illuminante carente in quel canale
    # Ricostruiamo un bianco approssimativo sotto la luce attuale
    src_rgb = np.array([1.0 / max(g, 0.01) for g in gains])
    src_rgb = src_rgb / np.max(src_rgb)  # Normalizza
    
    # RGB → XYZ (sRGB linearizzato)
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    
    src_linear = np.array([linearize(c) for c in src_rgb])
    M_rgb_to_xyz = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])
    src_xyz = M_rgb_to_xyz @ src_linear
    
    # Adattamento cromatico
    src_lms = M_brad @ src_xyz
    dst_lms = M_brad @ d65_xyz
    
    # Evita divisione per zero
    src_lms = np.maximum(src_lms, 1e-10)
    
    # Matrice di scaling diagonale
    scale = dst_lms / src_lms
    M_adapt = M_brad_inv @ np.diag(scale) @ M_brad
    
    # Applica al colore input
    r, g, b = [x / 255.0 for x in rgb]
    input_linear = np.array([linearize(c) for c in [r, g, b]])
    input_xyz = M_rgb_to_xyz @ input_linear
    adapted_xyz = M_adapt @ input_xyz
    
    # XYZ → RGB (inversa)
    M_xyz_to_rgb = np.linalg.inv(M_rgb_to_xyz)
    adapted_linear = M_xyz_to_rgb @ adapted_xyz
    
    # Gamma encoding
    def gamma_encode(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055
    
    adapted_rgb = tuple(int(gamma_encode(c) * 255) for c in adapted_linear)
    adapted_rgb = tuple(max(0, min(255, c)) for c in adapted_rgb)
    
    return adapted_rgb


def calibrate_white_balance(frame: np.ndarray, center_size: int = 80) -> np.ndarray:
    """
    Calibra il White Balance. L'utente deve inquadrare una superficie bianca.
    Ritorna i guadagni per canale (B, G, R).
    """
    height, width = frame.shape[:2]
    cx, cy = width // 2, height // 2
    half = center_size // 2
    
    roi = frame[cy - half:cy + half, cx - half:cx + half]
    white_ref = np.mean(roi, axis=(0, 1))
    
    # Evita divisione per zero
    white_ref = np.maximum(white_ref, 1.0)
    
    # Calcola guadagni: quanto manca a ciascun canale per arrivare a 255
    gains = 255.0 / white_ref
    
    # Normalizza rispetto al canale più luminoso (per non saturare)
    gains = gains / np.max(gains)
    # Ma assicurati che il canale più debole venga comunque compensato
    gains = gains * (255.0 / np.max(white_ref))
    
    return gains


def detect_dominant_color(frame: np.ndarray, center_size: int = 50) -> dict:
    """
    Rileva il colore dominante al centro del frame.
    Pipeline migliorata: CLAHE → WB → K-Means → Bradford → LAB matching.
    
    Args:
        frame: Frame della webcam in formato BGR
        center_size: Dimensione dell'area centrale da analizzare
        
    Returns:
        Dizionario con informazioni sul colore rilevato
    """
    global wb_gains
    height, width = frame.shape[:2]
    
    # Calcola l'area centrale
    cx, cy = width // 2, height // 2
    half = center_size // 2
    
    # Bounds check: evita ROI fuori dai bordi del frame
    half = min(half, cx, cy, width - cx, height - cy)
    if half < 1:
        half = 1
    
    # Estrai la regione centrale
    roi = frame[cy - half:cy + half, cx - half:cx + half]
    
    # === INTERVENTO 1: CLAHE (Normalizzazione luminosità locale) ===
    if CLAHE_ENABLED:
        roi = _apply_clahe(roi)
    
    # === INTERVENTO 2: White Balance (se calibrato) ===
    if WB_ENABLED and wb_gains is not None:
        roi = _apply_white_balance(roi, wb_gains)
    
    # === INTERVENTO 3: K-Means colore dominante ===
    if KMEANS_ENABLED and roi.size > 0:
        avg_color_bgr = _extract_dominant_kmeans(roi, KMEANS_CLUSTERS)
    else:
        avg_color_bgr = np.mean(roi, axis=(0, 1)).astype(int)
    
    b, g, r = avg_color_bgr
    
    # === INTERVENTO 4: Bradford Chromatic Adaptation ===
    rgb_for_lab = (int(r), int(g), int(b))
    if BRADFORD_ENABLED and wb_gains is not None:
        rgb_for_lab = _apply_bradford_cat(rgb_for_lab, wb_gains)
    
    # Converti in HSV per il riconoscimento del nome
    avg_color_hsv = cv2.cvtColor(
        np.uint8([[avg_color_bgr]]), 
        cv2.COLOR_BGR2HSV
    )[0][0]
    
    # Ottieni il nome del colore (usa RGB corretto da Bradford se disponibile)
    color_info = get_color_name_from_rgb(rgb_for_lab)
    
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

# ============================================================
# MODALITÀ PALETTE MULTI-PUNTO
# ============================================================

GRID_SIZES = [3, 5, 7]  # Dimensioni griglia ciclica

def detect_grid_colors(frame: np.ndarray, grid_size: int = 5, sample_size: int = 12) -> list:
    """
    Campiona colori su una griglia NxN distribuita sul frame.
    Ogni punto usa un mini-ROI con CLAHE + K-Means.
    
    Returns:
        Lista di dict con info colore per ogni punto della griglia.
    """
    height, width = frame.shape[:2]
    colors = []
    
    # Margini ampi per concentrare la griglia al centro (dove sta il piatto)
    margin_x = int(width * 0.28)
    margin_y = int(height * 0.28)
    
    for row in range(grid_size):
        for col in range(grid_size):
            # Calcola posizione del punto
            px = margin_x + int((width - 2 * margin_x) * col / max(1, grid_size - 1))
            py = margin_y + int((height - 2 * margin_y) * row / max(1, grid_size - 1))
            
            half = sample_size // 2
            # Bounds check
            x1 = max(0, px - half)
            y1 = max(0, py - half)
            x2 = min(width, px + half)
            y2 = min(height, py + half)
            
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            
            # Applica CLAHE se abilitato
            if CLAHE_ENABLED:
                roi = _apply_clahe(roi)
            
            # Estrai colore dominante
            if KMEANS_ENABLED and roi.size > 9:
                avg_bgr = _extract_dominant_kmeans(roi, min(KMEANS_CLUSTERS, roi.shape[0] * roi.shape[1]))
            else:
                avg_bgr = np.mean(roi, axis=(0, 1)).astype(int)
            
            b, g, r = avg_bgr
            rgb = (int(r), int(g), int(b))
            
            # Match colore
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


def extract_palette(grid_colors: list, max_colors: int = 8, min_delta_e: float = 10.0) -> list:
    """
    Deduplica i colori della griglia: tiene solo quelli con ΔE > soglia.
    Ritorna max_colors colori unici ordinati per frequenza.
    """
    if not grid_colors:
        return []
    
    palette = []
    
    for color in grid_colors:
        color_lab = rgb_to_lab(color['rgb'])
        
        # Controlla se è troppo simile a un colore già in palette
        is_unique = True
        for existing in palette:
            existing_lab = rgb_to_lab(existing['rgb'])
            if delta_e_cie2000(color_lab, existing_lab) < min_delta_e:
                existing['count'] = existing.get('count', 1) + 1
                is_unique = False
                break
        
        if is_unique:
            color['count'] = 1
            palette.append(color)
    
    # Ordina per frequenza (più presente = prima)
    palette.sort(key=lambda c: c.get('count', 1), reverse=True)
    
    return palette[:max_colors]


def draw_grid_overlay(frame: np.ndarray, grid_colors: list) -> np.ndarray:
    """Disegna i punti della griglia di campionamento sul frame."""
    for color in grid_colors:
        px, py = color['pos']
        bgr = color['bgr']
        
        # Cerchio colorato con bordo bianco
        cv2.circle(frame, (px, py), 8, (255, 255, 255), 2)
        cv2.circle(frame, (px, py), 6, bgr, -1)
        
        # Linee della griglia (sottili, semi-trasparenti)
        cv2.drawMarker(frame, (px, py), (200, 200, 200), cv2.MARKER_CROSS, 16, 1)
    
    return frame


def draw_palette_overlay(frame: np.ndarray, palette: list, grid_size: int = 3) -> np.ndarray:
    """Disegna la palette 1:1 come griglia di swatch che rispecchia la griglia di campionamento."""
    if not palette:
        return frame
    
    height, width = frame.shape[:2]
    n_colors = len(palette)
    
    # Dimensioni adattive in base alla griglia
    if grid_size <= 3:
        swatch = 36
        font_scale = 0.28
    elif grid_size <= 5:
        swatch = 24
        font_scale = 0.22
    else:
        swatch = 16
        font_scale = 0.18
    
    gap = 2
    cols = grid_size
    rows = grid_size
    
    palette_w = cols * (swatch + gap) + gap
    palette_h = rows * (swatch + gap) + gap + 18  # +18 per titolo
    
    # Posizione: alto a sinistra sotto gli indicatori
    start_x = 10
    start_y = 95
    
    # Background semi-trasparente
    overlay = frame.copy()
    cv2.rectangle(overlay, (start_x - 2, start_y - 18), 
                  (start_x + palette_w + 2, start_y + palette_h), 
                  (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    # Titolo
    cv2.putText(frame, f"PALETTE {cols}x{rows}", (start_x, start_y - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 220), 1)
    
    # Disegna griglia di swatch
    for i, color in enumerate(palette):
        row = i // cols
        col = i % cols
        
        x = start_x + gap + col * (swatch + gap)
        y = start_y + gap + row * (swatch + gap)
        
        # Quadrato colore
        cv2.rectangle(frame, (x, y), (x + swatch, y + swatch), color['bgr'], -1)
        cv2.rectangle(frame, (x, y), (x + swatch, y + swatch), (180, 180, 180), 1)
        
        # HEX dentro lo swatch (solo se abbastanza grande)
        if swatch >= 24:
            # Testo nero o bianco in base alla luminosità del colore
            r, g, b = color['rgb']
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            txt_color = (0, 0, 0) if lum > 128 else (255, 255, 255)
            cv2.putText(frame, color['hex'], (x + 1, y + swatch - 3), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, txt_color, 1)
    
    return frame


def export_palette(palette: list, frame: np.ndarray = None) -> str:
    """
    Esporta la palette corrente come JSON + PNG.
    Ritorna il nome del file salvato.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # --- JSON ---
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "n_colors": len(palette),
        "colors": []
    }
    for color in palette:
        json_data["colors"].append({
            "name_en": color['name_en'],
            "name_it": color['name_it'],
            "hex": color['hex'],
            "rgb": list(color['rgb']),
            "count": color.get('count', 1)
        })
    
    json_filename = f"palette_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # --- PNG Swatch ---
    swatch_w = 80
    swatch_h = 80
    text_h = 40
    n = len(palette)
    if n == 0:
        return json_filename
    
    img_w = n * swatch_w
    img_h = swatch_h + text_h
    img = np.zeros((img_h, img_w, 3), dtype=np.uint8)
    img[:] = (30, 30, 30)  # Sfondo scuro
    
    for i, color in enumerate(palette):
        x = i * swatch_w
        # Swatch colore
        cv2.rectangle(img, (x + 2, 2), (x + swatch_w - 2, swatch_h - 2), color['bgr'], -1)
        cv2.rectangle(img, (x + 2, 2), (x + swatch_w - 2, swatch_h - 2), (255, 255, 255), 1)
        # Testo HEX
        cv2.putText(img, color['hex'], (x + 5, swatch_h + 18), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        # Nome
        cv2.putText(img, color['name_it'][:8], (x + 5, swatch_h + 33), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
    
    png_filename = f"palette_{timestamp}.png"
    cv2.imwrite(png_filename, img)
    
    return json_filename


# --- Cache pre-calcolate per barre spettro UI (performance) ---
_hue_bar_cache = {}
_spectrum_cache = {}

def _get_hue_bar(bar_width, bar_height):
    """Pre-calcola la barra arcobaleno Hue come immagine NumPy."""
    key = (bar_width, bar_height)
    if key not in _hue_bar_cache:
        hue_values = np.linspace(0, 179, bar_width, dtype=np.uint8)
        hsv_bar = np.zeros((bar_height, bar_width, 3), dtype=np.uint8)
        hsv_bar[:, :, 0] = hue_values  # Hue
        hsv_bar[:, :, 1] = 255         # Saturation
        hsv_bar[:, :, 2] = 255         # Value
        _hue_bar_cache[key] = cv2.cvtColor(hsv_bar, cv2.COLOR_HSV2BGR)
    return _hue_bar_cache[key]

def _get_spectrum_strip(width, height):
    """Pre-calcola la striscia spettro in alto come immagine NumPy."""
    key = (width, height)
    if key not in _spectrum_cache:
        hue_values = np.linspace(0, 179, width, dtype=np.uint8)
        hsv_strip = np.zeros((height, width, 3), dtype=np.uint8)
        hsv_strip[:, :, 0] = hue_values
        hsv_strip[:, :, 1] = 255
        hsv_strip[:, :, 2] = 255
        _spectrum_cache[key] = cv2.cvtColor(hsv_strip, cv2.COLOR_HSV2BGR)
    return _spectrum_cache[key]


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
    
    # Barra Hue (arcobaleno) - pre-calcolata
    cv2.putText(frame, "H:", (bar_x - 25, y_start + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    hue_bar_img = _get_hue_bar(bar_width, bar_height)
    frame[y_start:y_start + bar_height, bar_x:bar_x + bar_width] = hue_bar_img
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
    
    # Barra spettro colori in alto - pre-calcolata
    spectrum_height = 8
    spectrum_img = _get_spectrum_strip(width, spectrum_height)
    frame[0:spectrum_height, 0:width] = spectrum_img
    # Indicatore posizione hue corrente
    hue_indicator_x = int(h * width / 180)
    cv2.rectangle(frame, (hue_indicator_x - 3, 0), (hue_indicator_x + 3, spectrum_height + 5), (255, 255, 255), 2)
    
    # Etichetta Audio ON/OFF (per TTS)
    cv2.putText(frame, "[V] Audio", (width - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Etichetta Strumento corrente
    instrument = INSTRUMENTS[current_instrument_index]
    instr_text = f"[T] {instrument['icon']}: {instrument['name']}"
    cv2.putText(frame, instr_text, (width - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
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
    global arduino, COMMON_ANODE, current_instrument_index, ARDUINO_PORT, wb_gains
    ARDUINO_PORT = find_arduino_port()
    if serial:
        # ⚠️ CHECK CRITICO PER CONFLITTO LIBRERIE
        if not hasattr(serial, 'Serial'):
             print("\n" + "!"*60)
             print("❌ ERRORE CRITICO: CONFLITTO LIBRERIE RILEVATO")
             print("Hai installato il pacchetto sbagliato 'serial' invece di 'pyserial'.")
             print("SOLUZIONE: Esegui questi comandi nel terminale:")
             print("  pip uninstall -y serial")
             print("  pip install pyserial")
             print("!"*60 + "\n")
             sys.exit(1) # Uscita pulita con cleanup

        if ARDUINO_PORT is None:
            print("⚠️ Nessuna porta Arduino trovata, proseguo senza LED.")
            arduino = None
        else:
            try:
                print(f"🔌 Tentativo di connessione a {ARDUINO_PORT}...")
                # 'write_timeout=0.1' è fondamentale se Arduino è "bloccato" da sensori lenti
                arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.1)
                time.sleep(2)  # Pausa FONDAMENTALE per il reset di Arduino
                
                # Puliamo i tubi della comunicazione
                arduino.reset_input_buffer()
                arduino.reset_output_buffer()
                print("✅ ARDUINO CONNESSO! Invio dati...")
            except Exception as e:
                print(f"❌ ERRORE: Non riesco a collegarmi. {e}")
                print("Suggerimento: Chiudi il Monitor Seriale di Arduino IDE e controlla il nome della porta.")
                arduino = None
    # --------------------------------

    
    print("\n" + "-" * 60)
    print("  CONTROLLI:")
    print("  [SPAZIO] - Cattura e stampa colore in console")
    print("  [C]      - Stampa continua colori (toggle)")
    print("  [V]      - Audio feedback (toggle)")
    print("  [G]      - Modalità Griglia/Palette (3x3 → 5x5 → 7x7 → off)")
    print("  [P]      - Esporta palette (JSON + PNG)")
    print("  [+/-]    - Aumenta/Diminuisci area di rilevamento")
    print("  [I]      - Inverti Colori (Fix LED 'Rosa'/Common Anode)")
    print("  [T]      - Cambia strumento musicale")
    print("  [S]      - Salva screenshot")
    print("  [Q/ESC]  - Esci")
    print("-" * 60 + "\n")
    print("  LEGENDA PRECISIONE: ● = Eccellente | ◐ = Buona | ○ = Appross.")
    print("-" * 60 + "\n")
    
    roi_size = 50
    continuous_mode = False
    audio_mode = True
    last_color = None
    last_spoken_color = None
    
    # Variabili per lo smoothing (Arduino)
    prev_r, prev_g, prev_b = 0, 0, 0
    
    # ADAPTIVE RATE LIMITING (Auto-Throttling)
    # Se Arduino è lento (timeout), aumentiamo questo valore.
    # Se Arduino è veloce, lo diminuiamo.
    loop_delay = 0.05
    
    # === INTERVENTO 5: Smoothing Temporale ===
    prev_lab = None  # Stato precedente per EMA su LAB
    
    # === MODALITÀ GRIGLIA/PALETTE ===
    grid_mode = False
    grid_size_idx = 1  # Indice in GRID_SIZES (default 5x5)
    current_palette = []  # Palette corrente estratta
    last_sent_palette = []  # Cache ultima palette inviata ad Arduino
    last_palette_send_time = 0  # Timestamp ultimo invio palette
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Errore lettura frame!")
                break
            
            # Rimuovi effetto specchio (flip orizzontale)
            frame = cv2.flip(frame, 1)
            
            # Rileva il colore (Pipeline Avanzata: CLAHE → WB → K-Means → Bradford)
            color_data = detect_dominant_color(frame, roi_size)
            
            # === INTERVENTO 5: Smoothing Temporale su LAB ===
            if TEMPORAL_SMOOTH_ENABLED:
                current_lab = np.array(rgb_to_lab(color_data['rgb']))
                if prev_lab is not None:
                    smoothed_lab = prev_lab * (1 - TEMPORAL_ALPHA) + current_lab * TEMPORAL_ALPHA
                    prev_lab = smoothed_lab
                    # Riconverti LAB smoothed → nome colore
                    smoothed_color_info = None
                    min_dist = float('inf')
                    for color in COLOR_DATABASE:
                        color_lab = COLOR_LAB_CACHE[color.name]
                        dist = delta_e_cie2000(tuple(smoothed_lab), color_lab)
                        if dist < min_dist:
                            min_dist = dist
                            smoothed_color_info = color
                    if smoothed_color_info:
                        if min_dist < 5:
                            prec = "●"
                        elif min_dist < 15:
                            prec = "◐"
                        else:
                            prec = "○"
                        color_data['name_en'] = f"{smoothed_color_info.name} {prec}"
                        color_data['name_it'] = f"{smoothed_color_info.name_it} {prec}"
                else:
                    prev_lab = current_lab
            
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
                    # 5.b PROTEZIONE BUFFER INPUT
                    arduino.reset_input_buffer()
                    
                    # === MODALITÀ PALETTE: Invia tutti i colori ===
                    if grid_mode and current_palette:
                        now = time.time()
                        # Aggiorna ogni 0.3s (Arduino fa fillBlocks istantaneo)
                        if (now - last_palette_send_time) > 0.3:
                            palette_parts = []
                            for c in current_palette:
                                pr, pg, pb = c['rgb']
                                pr = min(255, max(0, int(apply_gamma(pr))))
                                pg = min(255, max(0, int(apply_gamma(pg))))
                                pb = min(255, max(0, int(apply_gamma(pb))))
                                if COMMON_ANODE:
                                    pr, pg, pb = 255 - pr, 255 - pg, 255 - pb
                                palette_parts.append(f"{pr:02X}{pg:02X}{pb:02X}")
                            
                            msg = f"P:{len(current_palette)}:{':'.join(palette_parts)}\n"
                            arduino.write(msg.encode('utf-8'))
                            last_palette_send_time = now
                    
                    else:
                        # === MODALITÀ SINGOLO COLORE (come prima) ===
                        target_r, target_g, target_b = color_data['rgb']
                        
                        # 3.1 BLACK THRESHOLD (Taglio del nero)
                        luminance = (0.299 * target_r + 0.587 * target_g + 0.114 * target_b)
                        if luminance < BLACK_THRESHOLD:
                             target_r, target_g, target_b = 0, 0, 0
                        
                        # 3.2 SMOOTHING (Media pesata)
                        curr_r = int((prev_r * (1 - SMOOTHING)) + (target_r * SMOOTHING))
                        curr_g = int((prev_g * (1 - SMOOTHING)) + (target_g * SMOOTHING))
                        curr_b = int((prev_b * (1 - SMOOTHING)) + (target_b * SMOOTHING))
                        
                        prev_r, prev_g, prev_b = curr_r, curr_g, curr_b
                        
                        # 3.3 APPLICAZIONE GAMMA
                        final_r = apply_gamma(curr_r)
                        final_g = apply_gamma(curr_g)
                        final_b = apply_gamma(curr_b)
                        
                        # --- 4. CALCOLO DELL'ONDA DEL RESPIRO ---
                        wave = math.sin(time.time() * PULSE_SPEED) 
                        norm_wave = (wave + 1) / 2.0 
                        pulse_factor = MIN_BRIGHTNESS + (norm_wave * (1.0 - MIN_BRIGHTNESS))
                        
                        pulsing_r = int(final_r * pulse_factor)
                        pulsing_g = int(final_g * pulse_factor)
                        pulsing_b = int(final_b * pulse_factor)
                        
                        if COMMON_ANODE:
                            pulsing_r = 255 - pulsing_r
                            pulsing_g = 255 - pulsing_g
                            pulsing_b = 255 - pulsing_b
                        
                        msg = f"{pulsing_r},{pulsing_g},{pulsing_b}\n"
                        arduino.write(msg.encode('utf-8'))
                    
                    # SUCCESSO: accelera
                    loop_delay = max(0.05, loop_delay - 0.01)

                except serial.SerialTimeoutException:
                     # TIMEOUT: Arduino è occupato (es. sta leggendo sensore ultrasuoni)
                     # RALLENTIAMO il loop per dargli respiro
                     loop_delay = min(0.5, loop_delay + 0.05)
                     if loop_delay > 0.15:
                         print(f"⚠️ Arduino Busy (Ultrasonic?) - Slowing down... (Delay: {loop_delay:.2f}s)")
                
                except Exception as e:
                    print(f"Errore scrittura: {e}")
            
            # --- IL SEGRETO DEL SUCCESSO ---
            # --- IL SEGRETO DEL SUCCESSO (ADAPTIVE) ---
            # Questa pausa dinamica si adatta alla velocità di Arduino
            time.sleep(loop_delay)
            # ------------------------------------------

            
            # === SINESTESIA (MODALITÀ SONORA) ===
            # Rimuovi indicatore precisione
            clean_color_name = color_data['name_en'].replace(' ●', '').replace(' ◐', '').replace(' ○', '')
            
            # Se siamo in modalità audio (V) o se vogliamo che suoni sempre
            # Per ora usiamo il toggle audio_mode per attivare/disattivare la musica
            if audio_mode:
                if grid_mode and current_palette:
                    # Arpeggio: una nota per colore, in sequenza
                    play_arpeggio_note(current_palette)
                else:
                    # Singola nota dal colore centrale
                    play_color_note(color_data['hsv'])
            
            # === GRIGLIA/PALETTE (campiona PRIMA di disegnare overlay!) ===
            grid_colors = []
            if grid_mode:
                grid_colors = detect_grid_colors(frame, GRID_SIZES[grid_size_idx])
                current_palette = grid_colors  # 1:1 — nessuna deduplica!
            
            # Disegna overlay (crosshair, info panel — DOPO il campionamento)
            display_frame = draw_info_overlay(frame, color_data)
            
            # Disegna griglia e palette sopra il display frame
            if grid_mode:
                display_frame = draw_grid_overlay(display_frame, grid_colors)
                display_frame = draw_palette_overlay(display_frame, current_palette, GRID_SIZES[grid_size_idx])
                # Indicatore griglia
                cv2.putText(display_frame, f"GRID {GRID_SIZES[grid_size_idx]}x{GRID_SIZES[grid_size_idx]}", (10, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 200), 1)
            
            # Indicatore audio sullo schermo
            if audio_mode:
                cv2.putText(display_frame, "🎵 MUSIC MODE ON", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Indicatore pipeline attiva
            cv2.putText(display_frame, "CLAHE+KM", (10, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 200), 1)
            
            # MOSTRA A VIDEO SOLO SE HEADLESS_MODE È FALSE
            if not HEADLESS_MODE:
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
                elif key == ord('+') or key == ord('=') or key == 43:
                    roi_size = min(200, roi_size + 10)
                    print(f"📐 Area rilevamento: {roi_size}x{roi_size}")
                elif key == ord('-') or key == ord('_') or key == 45 or key == 173:
                    roi_size = max(10, roi_size - 10)
                    print(f"📐 Area rilevamento: {roi_size}x{roi_size}")
                elif key == ord('s'):
                    filename = f"color_capture_{color_data['hex'][1:]}.png"
                    cv2.imwrite(filename, frame)
                    print(f"📸 Screenshot salvato: {filename}")
                elif key == ord('i'):
                    COMMON_ANODE = not COMMON_ANODE
                    state = "ATTIVA (LED Invertiti/Common Anode)" if COMMON_ANODE else "DISATTIVA (Standard)"
                    print(f"\n🔄 Modalità Inversione Colore: {state}")
                elif key == ord('t'):
                    current_instrument_index = (current_instrument_index + 1) % len(INSTRUMENTS)
                    instr = INSTRUMENTS[current_instrument_index]
                    print(f"\n🎵 Strumento: {instr['icon']} {instr['name']}")
                elif key == ord('g'):
                    # Toggle griglia / cicla dimensione
                    if not grid_mode:
                        grid_mode = True
                        grid_size_idx = 0  # Parte da 3x3
                        print(f"\n🔲 Modalità Griglia: ON ({GRID_SIZES[grid_size_idx]}x{GRID_SIZES[grid_size_idx]})")
                    else:
                        grid_size_idx += 1
                        if grid_size_idx >= len(GRID_SIZES):
                            grid_mode = False
                            current_palette = []
                            print("\n❌ Modalità Griglia: OFF")
                        else:
                            print(f"\n🔲 Griglia: {GRID_SIZES[grid_size_idx]}x{GRID_SIZES[grid_size_idx]}")
                elif key == ord('p'):
                    # Esporta palette
                    if current_palette:
                        filename = export_palette(current_palette, frame)
                        print(f"\n🎨 Palette esportata! {len(current_palette)} colori")
                        print(f"   JSON: {filename}")
                        print(f"   PNG:  {filename.replace('.json', '.png')}")
                        # Stampa anche i colori
                        for c in current_palette:
                            print(f"   {c['hex']} - {c['name_it']} (x{c.get('count', 1)})")
                    else:
                        print("\n⚠️ Attiva prima la griglia con [G] per generare la palette!")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if arduino:
            try:
                # Spegni i LED prima di chiudere!
                print("💡 Spegnimento LED...")
                for _ in range(5):
                    arduino.write(b"0,0,0\n")
                    time.sleep(0.05)
                time.sleep(0.3)  # Attendi che Arduino processi
                arduino.close()
                print("✅ LED spenti. Connessione Arduino chiusa.")
            except Exception:
                pass



if __name__ == "__main__":
    main()