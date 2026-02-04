import requests
import time

# Script ini hanya untuk memunculkan IP di LOG Railway
while True:
    try:
        ip = requests.get('https://api.ipify.org').text
        print(f"ALAMAT IP RAILWAY KAMU: {ip}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Supaya tidak spam log, cek setiap 1 menit
    time.sleep(60)
      
