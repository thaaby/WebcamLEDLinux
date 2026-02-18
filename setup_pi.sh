#!/bin/bash

echo "🍓 Setup Raspberry Pi per Webcam LED..."
echo "========================================"

# Aggiorna i repository
echo "📦 Aggiornamento sistema..."
sudo apt-get update

# Installa dipendenze di sistema/librerie
echo "📦 Installazione dipendenze di sistema..."
sudo apt-get install -y python3-opencv python3-numpy python3-pygame python3-serial libatlas-base-dev espeak

# Permessi seriale (solitamente necessari su Linux)
echo "🔑 Configurazione permessi seriale..."
sudo usermod -a -G dialout $USER

echo "✅ Installazione completata!"
echo "⚠️  NOTA: Riavvia il Raspberry Pi o fai logout/login per applicare i permessi seriali."
echo "👉 Per avviare: python3 main.py"
