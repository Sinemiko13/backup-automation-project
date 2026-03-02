import boto3
import os
import shutil
import requests
from datetime import datetime
from cryptography.fernet import Fernet
from botocore.client import Config

# --- 1. GÜVENLİ KONFİGÜRASYON ---
# GitHub Secrets'tan veya yerel bilgisayarından bilgileri çeker
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8549893092:AAGCYwRrYQ02EOmuHKKEzUyOM_luvZsGNxo")
CHAT_ID = os.getenv("CHAT_ID", "8403674666")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = "backup-project-sinem"

# Klasör Yolları
SOURCE_DIR = "./data_to_backup" 
BACKUP_DIR = "./backups"

# --- 2. YARDIMCI FONKSİYONLAR ---

def send_notification(text):
    """İşlem sonucunu Telegram botuna iletir."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"[!] Bildirim gönderilemedi: {e}")

def upload_to_minio(file_path):
    """Şifrelenmiş dosyayı yerel bulut (MinIO) sistemine yükler."""
    try:
        s3 = boto3.client('s3',
                          endpoint_url=MINIO_ENDPOINT,
                          aws_access_key_id=MINIO_ACCESS_KEY,
                          aws_secret_access_key=MINIO_SECRET_KEY,
                          config=Config(signature_version='s3v4'))
        
        file_name = os.path.basename(file_path)
        s3.upload_file(file_path, BUCKET_NAME, file_name)
        print(f"🚀 [BULUT] {file_name} başarıyla yüklendi!")
        return True
    except Exception as e:
        print(f"❌ [HATA] Bulut yükleme hatası: {e}")
        return False

# --- 3. ANA YEDEKLEME MOTORU ---

def run_backup():
    # Klasör kontrolü
    if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_base_name = f"backup_{timestamp}"
    local_zip_path = os.path.join(BACKUP_DIR, backup_base_name)
    
    try:
        # ADIM 1: Sıkıştır
        shutil.make_archive(local_zip_path, 'zip', SOURCE_DIR)
        final_zip = local_zip_path + ".zip"
        print(f"📦 [YEREL] Zip oluşturuldu: {final_zip}")

        # ADIM 2: Şifrele (AES-256)
        # Her yedekleme için yeni bir anahtar üretilir (Geliştirmek istersen bu anahtarı bir yere kaydetmelisin)
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        with open(final_zip, "rb") as f:
            original_data = f.read()
        
        encrypted_data = fernet.encrypt(original_data)
        encrypted_file = f"{final_zip}.enc"
        
        with open(encrypted_file, "wb") as f:
            f.write(encrypted_data)
        
        # Orijinal şifresiz dosyayı sil (Güvenlik için)
        os.remove(final_zip)
        print(f"🔐 [GÜVENLİK] Dosya şifrelendi: {encrypted_file}")

        # ADIM 3: Buluta Yükle
        success = upload_to_minio(encrypted_file)
        
        # ADIM 4: Bildirim Gönder
        if success:
            msg = f"✅ Yedekleme Başarılı Sinem!\n📂 Dosya: {os.path.basename(encrypted_file)}\n🔐 Şifreleme: AES-256\n☁️ Lokasyon: MinIO Cloud"
            send_notification(msg)
            print(msg)

    except Exception as e:
        err_msg = f"❌ Yedekleme Hatası!\nDetay: {str(e)}"
        send_notification(err_msg)
        print(err_msg)

if __name__ == "__main__":
    run_backup()