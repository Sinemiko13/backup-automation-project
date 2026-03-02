import os
import shutil
import datetime
import requests
from cryptography.fernet import Fernet

# --- GÜVENLİK AYARI ---
# Artık token kodun içinde değil, sistemin güvenli kasasında duruyor!
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_notification(message):
    if not TOKEN or not CHAT_ID:
        print("Hata: Telegram bilgileri eksik! Lütfen Secrets kısmını kontrol et.")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Bildirim gönderilemedi: {e}")

def encrypt_file(file_path, key):
    f = Fernet(key)
    with open(file_path, "rb") as file:
        file_data = file.read()
    encrypted_data = f.encrypt(file_data)
    with open(file_path + ".enc", "wb") as file:
        file.write(encrypted_data)
    os.remove(file_path) # Orijinal dosyayı güvenlik için siliyoruz.

def create_backup():
    source_dir = "data_to_backup"
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        shutil.make_archive(backup_path, 'zip', source_dir)
        full_path = backup_path + ".zip"
        
        # Şifreleme (Opsiyonel: Key'i de secret olarak saklayabilirsin)
        key = Fernet.generate_key()
        encrypt_file(full_path, key)
        
        msg = f"✅ Yedekleme Başarılı: {backup_name}.zip.enc"
        print(msg)
        send_telegram_notification(msg)
    except Exception as e:
        err_msg = f"❌ Yedekleme Hatası: {str(e)}"
        print(err_msg)
        send_telegram_notification(err_msg)

if __name__ == "__main__":
    create_backup()