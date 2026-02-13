<![CDATA[# 🎨 Webcam Color Detector

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Rileva i colori in tempo reale dalla tua webcam e visualizza nome e codice colore nella console.**

</div>

---

## 📋 Indice

- [Caratteristiche](#-caratteristiche)
- [Requisiti di Sistema](#-requisiti-di-sistema)
- [Installazione](#-installazione)
- [Utilizzo](#-utilizzo)
- [Controlli](#-controlli)
- [Colori Supportati](#-colori-supportati)
- [Troubleshooting](#-troubleshooting)
- [Personalizzazione](#-personalizzazione)

---

## ✨ Caratteristiche

| Feature | Descrizione |
|---------|-------------|
| 🔍 **Rilevamento in tempo reale** | Analisi del colore dominante al centro del frame |
| 🏷️ **Nomi colori** | Supporto bilingue italiano/inglese |
| 🎯 **Codici colore** | Output in formato HEX, RGB e HSV |
| 📷 **Multi-camera** | Supporto per webcam esterne |
| 📸 **Screenshot** | Salva catture con il codice colore nel nome |
| 🔄 **Modalità continua** | Stampa automatica quando il colore cambia |
| 📐 **Area regolabile** | Modifica la dimensione dell'area di campionamento |

---

## 💻 Requisiti di Sistema

### Hardware
- 🖥️ **Mac** con macOS 10.14 (Mojave) o superiore
- 📷 **Webcam** integrata o esterna USB

### Software
- 🐍 **Python 3.8** o superiore
- 📦 **pip** (package manager Python)

---

## 🚀 Installazione

### 1. Clona o scarica il progetto

```bash
cd ~/Desktop/Webcam\ project
```

### 2. Crea un ambiente virtuale (consigliato)

```bash
# Crea l'ambiente virtuale
python3 -m venv venv

# Attiva l'ambiente virtuale
source venv/bin/activate
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Verifica l'installazione

```bash
python3 -c "import cv2; print(f'OpenCV versione: {cv2.__version__}')"
```

---

## 📖 Utilizzo

### Avvio rapido

```bash
python3 main.py
```

### Workflow tipico

```
1. Avvia lo script
   └── python3 main.py

2. Seleziona la webcam (se ne hai più di una)
   └── Inserisci il numero della camera

3. Punta la webcam verso un oggetto colorato
   └── L'area di rilevamento è al centro

4. Premi SPAZIO per stampare il colore in console
   └── Oppure attiva la modalità continua con C

5. Premi Q o ESC per uscire
```

### Output Console

Quando premi **SPAZIO**, vedrai un output simile a questo:

```
==================================================
🎨 COLORE RILEVATO
==================================================
  Nome:    Rosso (Red)
  HEX:     #E53935
  RGB:     (229, 57, 53)
  HSV:     (1, 199, 229)
==================================================
```

---

## 🎮 Controlli

| Tasto | Azione |
|:-----:|--------|
| `SPAZIO` | Cattura e stampa il colore corrente in console |
| `C` | Attiva/disattiva la modalità continua |
| `+` | Aumenta l'area di rilevamento |
| `-` | Diminuisce l'area di rilevamento |
| `S` | Salva uno screenshot |
| `Q` / `ESC` | Esci dall'applicazione |

### Modalità Continua

Quando attivata con `C`, il programma stampa automaticamente in console ogni volta che il colore rilevato cambia:

```
[Rosso] HEX: #E53935 | RGB: (229, 57, 53)
[Verde] HEX: #43A047 | RGB: (67, 160, 71)
[Blu] HEX: #1E88E5 | RGB: (30, 136, 229)
```

---

## 🌈 Colori Supportati

Il sistema riconosce i seguenti colori base:

| Colore | Nome IT | Nome EN | HEX |
|:------:|---------|---------|-----|
| 🔴 | Rosso | Red | `#FF0000` |
| 🟠 | Arancione | Orange | `#FFA500` |
| 🟡 | Giallo | Yellow | `#FFFF00` |
| 🟢 | Verde | Green | `#00FF00` |
| 🔵 | Ciano | Cyan | `#00FFFF` |
| 🔷 | Blu | Blue | `#0000FF` |
| 🟣 | Viola | Purple | `#800080` |
| 🩷 | Rosa | Pink | `#FFC0CB` |
| ⚪ | Bianco | White | `#FFFFFF` |
| ⚫ | Nero | Black | `#000000` |
| 🩶 | Grigio | Gray | `#808080` |

> **Nota:** I codici HEX e RGB mostrati nella console rappresentano il colore reale rilevato, non il colore base della categoria.

---

## 🔧 Troubleshooting

### ❌ "Nessuna webcam trovata"

**Causa:** La webcam non è collegata o non è riconosciuta dal sistema.

**Soluzione:**
1. Verifica che la webcam sia collegata correttamente
2. Controlla i permessi della webcam su macOS:
   - Vai in **Preferenze di Sistema** → **Privacy e Sicurezza** → **Fotocamera**
   - Assicurati che il Terminale abbia il permesso di accedere alla fotocamera

### ❌ "Impossibile aprire la webcam"

**Causa:** Un'altra applicazione sta utilizzando la webcam.

**Soluzione:**
1. Chiudi FaceTime, Zoom, Teams o altre app che usano la camera
2. Riavvia lo script

### ❌ Errore di importazione OpenCV

**Causa:** OpenCV non è installato correttamente.

**Soluzione:**
```bash
pip uninstall opencv-python
pip install opencv-python
```

### ❌ Frame scuro o nero

**Causa:** La webcam ha bisogno di tempo per adattarsi all'illuminazione.

**Soluzione:**
1. Attendi 2-3 secondi dopo l'avvio
2. Assicurati che ci sia sufficiente illuminazione

### ❌ Webcam esterna non rilevata

**Soluzione:**
1. Scollega e ricollega la webcam USB
2. Prova una porta USB diversa
3. Verifica che la webcam sia compatibile con macOS

---

## ⚙️ Personalizzazione

### Aggiungere nuovi colori

Modifica il dizionario `COLORS` in `main.py`:

```python
COLORS = [
    # ... colori esistenti ...
    ColorRange(
        'Brown',                          # Nome inglese
        'Marrone',                        # Nome italiano
        np.array([10, 100, 50]),          # HSV minimo
        np.array([20, 255, 150]),         # HSV massimo
        '#8B4513'                         # Codice HEX rappresentativo
    ),
]
```

### Valori HSV

> **Tip:** I valori HSV in OpenCV hanno i seguenti range:
> - **H (Hue):** 0-180 (non 0-360!)
> - **S (Saturation):** 0-255
> - **V (Value):** 0-255

### Modificare la dimensione iniziale dell'area

Cambia il valore di `roi_size` nella funzione `main()`:

```python
roi_size = 100  # Default: 50
```

### Cambiare la risoluzione della webcam

```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)   # Default: 1280
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # Default: 720
```

---

## 📁 Struttura del Progetto

```
Webcam project/
├── main.py              # Script principale
├── requirements.txt     # Dipendenze Python
├── README.md            # Questa documentazione
└── venv/                # Ambiente virtuale (opzionale)
```

---

## 📜 License

MIT License - Sei libero di usare, modificare e distribuire questo progetto.

---

<div align="center">

**Made with ❤️ for color enthusiasts**

</div>
]]>
