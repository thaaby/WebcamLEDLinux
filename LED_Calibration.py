import serial
import time
import glob

# Configurazione Arduino
ARDUINO_BAUD = 500000

# Trova automaticamente la porta
porte_trovate = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/cu.usbmodem*')
if not porte_trovate:
    print("ERRORE: Nessuna porta seriale trovata. Controlla il cavo USB dell'Arduino!")
    exit(1)

ARDUINO_PORT = porte_trovate[0]
print(f"Porta rilevata automaticamente: {ARDUINO_PORT}")

print(f"Tentativo di connessione a {ARDUINO_PORT}...")
try:
    ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=0.1)
    time.sleep(2)
    print("Connesso!")
except Exception as e:
    print(f"Errore connessione: {e}")
    exit(1)

def send_raw_leds(buffer):
    """Invia 3072 byte (1024 led x 3) all'Arduino via protocollo 'V'"""
    # L'Arduino si aspetta 'V' seguito da 3072 byte raw RGB
    ser.write(b'V' + buffer)
    time.sleep(0.05) # Lascia il tempo all'Arduino di scrivere sui led

while True:
    print("\n--- TEST CALIBRAZIONE LED MATRIX ---")
    print("1: Ordine Pannelli (R, V, B, Giallo)")
    print("2: Orientamento (Primi 8 LED bianchi)")
    print("3: Primo e Ultimo LED (Inizio=Bianco, Fine=Rosso)")
    print("q: Esci")
    
    scelta = input("Scegli: ")
    
    buf = bytearray(3072)
    
    if scelta == '1':
        # Colora i 4 blocchi di 256 LED (Pannelli)
        for i in range(256):
            # Block 0 (Rosso)
            buf[i*3] = 255; buf[i*3+1] = 0; buf[i*3+2] = 0
            # Block 1 (Verde)
            buf[(i+256)*3] = 0; buf[(i+256)*3+1] = 255; buf[(i+256)*3+2] = 0
            # Block 2 (Blu)
            buf[(i+512)*3] = 0; buf[(i+512)*3+1] = 0; buf[(i+512)*3+2] = 255
            # Block 3 (Giallo)
            buf[(i+768)*3] = 255; buf[(i+768)*3+1] = 255; buf[(i+768)*3+2] = 0
        send_raw_leds(buf)
        print(">> Inviato. Annota in che ordine da sinistra a destra compaiono R, V, B, Giallo!")
        
    elif scelta == '2':
        # Illumina solo i primissimi 8 led di goni blocco
        for p in range(4):
            for i in range(8):
                idx = (p*256 + i) * 3
                buf[idx] = 255
                buf[idx+1] = 255
                buf[idx+2] = 255
        send_raw_leds(buf)
        print(">> Inviato. Vedi 4 piccole righe bianche? Da che lato del pannello sono e in che direzione vanno?")
        
    elif scelta == '3':
        for p in range(4):
            start_idx = (p*256) * 3
            end_idx = (p*256 + 255) * 3
            # Primo led = Bianco
            buf[start_idx] = 255; buf[start_idx+1] = 255; buf[start_idx+2] = 255;
            # Ultimo led = Rosso
            buf[end_idx] = 255; buf[end_idx+1] = 0; buf[end_idx+2] = 0;
        send_raw_leds(buf)
        print(">> Inviato. Guarda i vari pannelli, c'è un punto BIANCO (Inizio) e uno ROSSO (Fine).")
        
    elif scelta == 'q':
        break
