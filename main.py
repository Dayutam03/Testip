import requests
import json
import time
from datetime import datetime, timedelta

# Konfigurasi API
API_KEY = "RbWLjVBwT6-Ht-MfKt08wg"
# Coba gunakan endpoint JSON murni jika /csv error
URL = "https://api.iprn-elite.com/v1.0/json" 

def get_sms():
    headers = {
        "Content-Type": "application/json",
        "Api-Key": API_KEY
    }
    
    # Set waktu dari 1 jam yang lalu sampai sekarang (Format ISO 8601)
    now = datetime.utcnow()
    start_time = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    payload = {
        "jsonrpc": "2.0",
        "method": "sms.mdr_full:get_list",
        "params": {
            "filter": {
                "start_date": start_time,
                "end_date": end_time
            },
            "page": 1,
            "per_page": 10
        },
        "id": 1
    }

    try:
        # Gunakan json=payload agar requests otomatis mengatur format JSON
        response = requests.post(URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Jika masih error 400, tampilkan pesan error dari server
            print(f"Server Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

last_seen_id = None
print("--- Menunggu SMS Masuk (PROJECT BULK FB) ---")

while True:
    data = get_sms()
    
    if data and "result" in data:
        sms_list = data["result"].get("mdr_full_list", [])
        if sms_list:
            latest_sms = sms_list[0]
            # Gunakan kombinasi phone dan datetime sebagai ID unik
            current_id = f"{latest_sms.get('phone')}_{latest_sms.get('datetime')}"

            if current_id != last_seen_id:
                print("\nNEW SMS RECEIVED")
                print(f"Phone   : {latest_sms.get('phone')}")
                print(f"Service : {latest_sms.get('senderid')}")
                print(f"Message : {latest_sms.get('message')}")
                print("-" * 25)
                last_seen_id = current_id
    
    time.sleep(10)
    
