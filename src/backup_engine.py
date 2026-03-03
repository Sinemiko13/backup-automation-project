import os
import shutil
import datetime
import requests
import hashlib
import logging
from cryptography.fernet import Fernet

# --- # 1. MERKEZİ LOG YÖNETİMİ ---
# Tüm işlemler 'backup.log' dosyasına kaydedilir.
logging.basicConfig(
    filename='backup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- # 2. BÜTÜNLÜK KONTROLÜ (HASHING) ---
def calculate_hash(file_path):
    """Dosyanın SHA-256 parmak izini hesaplar."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def send_telegram_notification(message):
    if not TOKEN or not CHAT_ID:
        logging.warning("Telegram ayarları eksik, bildirim gönderilemedi.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.error(f"Bildirim hatası: {e}")

def encrypt_file(file_path, key):
    f = Fernet(key)
    with open(file_path, "rb") as file:
        file_data = file.read()
    encrypted_data = f.encrypt(file_data)
    with open(file_path + ".enc", "wb") as file:
        file.write(encrypted_data)
    os.remove(file_path)
    logging.info(f"Dosya AES-256 ile şifrelendi: {file_path}")

def create_backup():
    # --- # 3. DİNAMİK YAPI ---
    # Yedeklenecek klasörleri buradan liste olarak yönetebilirsin.
    source_dirs = ["data_to_backup"] 
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    for s_dir in source_dirs:
        if not os.path.exists(s_dir):
            logging.error(f"Kaynak dizin bulunamadı: {s_dir}")
            continue
            
        backup_name = f"backup_{s_dir}_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            # Arşivleme
            shutil.make_archive(backup_path, 'zip', s_dir)
            full_path = backup_path + ".zip"
            
            # Şifreleme öncesi orijinal Hash al (Bütünlük Kontrolü)
            original_hash = calculate_hash(full_path)
            
            # Şifreleme
            key = Fernet.generate_key()
            encrypt_file(full_path, key)
            
            # Başarı Mesajı
            msg = (f"✅ Yedekleme Başarılı!\n"
                   f"📁 Klasör: {s_dir}\n"
                   f"🔐 Hash (SHA-256): {original_hash[:16]}...")
            
            logging.info(msg.replace("\n", " "))
            send_telegram_notification(msg)
            
        except Exception as e:
            err_msg = f"❌ {s_dir} Yedekleme Hatası: {str(e)}"
            logging.error(err_msg)
            send_telegram_notification(err_msg)

if __name__ == "__main__":
    create_backup()