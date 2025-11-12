import time
import serial
import pynmea2
import smtplib
from email.mime.text import MIMEText
from gpiozero import MotionSensor, LED
from gpiozero.pins.rpigpio import RPiGPIOFactory
from gpiozero import Device
from datetime import datetime, timedelta
from signal import pause
import sys

# === CONFIGURARE GPIO ===
Device.pin_factory = RPiGPIOFactory()
pir = MotionSensor(17)    # PIR pe GPIO 17 (pin fizic 11)
led = LED(27)             # LED pe GPIO 27 (pin fizic 13)

# === CONFIGURARE EMAIL ===
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
USERNAME = 'danalacheemanuel@gmail.com'
PASSWORD = 'mcwrvuhlplbtceav'
RECIEVER_EMAIL = 'emanuel.danalache@student.tuiasi.ro'

# === TIMP MINIM INTRE EMAILURI ===
last_motion_time = datetime.min
DEBOUNCE_SECONDS = 15

# === FUNCTIE PENTRU TRIMITERE EMAIL ===
def send_email(link):
    subject = 'Alerta: miscare detectata'
    body = f'Senzorul PIR a detectat miscare.\nLocatie estimata: {link}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = USERNAME
    msg['To'] = RECIEVER_EMAIL

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.send_message(msg)
            print("[EMAIL] Email trimis cu succes.")
    except Exception as e:
        print(f"[EMAIL] Eroare la trimitere: {e}")

# === FUNCTIE PENTRU OBTINERE LOCATIE GPS ===
def get_gps_link():
    try:
        with serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1) as ser:
            for _ in range(15):  # Incearca 15 citiri (max ~15 sec)
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith(('$GPGGA', '$GNGGA', '$GPRMC', '$GNRMC')):
                    try:
                        msg = pynmea2.parse(line)
                        if msg.latitude and msg.longitude:
                            latitude = msg.latitude
                            longitude = msg.longitude
                            link = f"https://maps.google.com/?q={latitude:.6f},{longitude:.6f}"
                            return link
                    except pynmea2.ParseError:
                        continue
    except Exception as e:
        print(f"[GPS] Eroare la citire: {e}")
    return None

# === FUNCTII PENTRU SENZOR ===
def motion_detected():
    global last_motion_time
    if datetime.now() - last_motion_time < timedelta(seconds=DEBOUNCE_SECONDS):
        return  # Ignora miscare daca e prea devreme

    last_motion_time = datetime.now()

    print("[SENZOR] Miscare detectata!")
    led.on()

    link = get_gps_link()
    if link:
        print(f"[GPS] Link Google Maps: {link}")
        send_email(link)
    else:
        print("[GPS] Nu s-a putut obține locația.")

def motion_stopped():
    print("[SENZOR] Miscare oprita.")
    led.off()

pir.when_motion = motion_detected
pir.when_no_motion = motion_stopped

# === FUNCTIE DE INCHIDERE CURATA ===
def clean_exit():
    led.off()
    print("LED oprit.")
    print("Conexiune inchisa.")
    sys.exit(0)

# === MAIN ===
print("Initializare sistem...")
print("Sistem activ. Asteptam detectie miscare...")

try:
    pause()  # asteapta evenimente de la senzor
except KeyboardInterrupt:
    print("\nProgram oprit manual.")
    clean_exit()

