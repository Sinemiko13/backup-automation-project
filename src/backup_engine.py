# -*- coding: utf-8 -*-
# 1 2 3 4 5...
import os
import shutil
import datetime
import requests
import hashlib
import logging
import sqlite3
import boto3
import zipfile
from botocore.client import Config
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# --- # 1. PROFESSIONAL LOGGING SETUP ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler('backup_system.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def init_db():
    conn = sqlite3.connect('backups_metadata.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS backup_records 
                 (filename TEXT, original_hash TEXT, encryption_key TEXT, date TEXT)''')
    conn.commit()
    conn.close()

# --- # 2. UTILS ---
def calculate_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def send_telegram_notification(message):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10) 
    except Exception as e:
        logging.error(f"Telegram Notification bypassed: {e}")

# --- # 3. ENCRYPTION & CLOUD ---
def encrypt_file(file_path, key):
    f = Fernet(key)
    with open(file_path, "rb") as file:
        file_data = file.read()
    encrypted_data = f.encrypt(file_data)
    enc_path = file_path + ".enc"
    with open(enc_path, "wb") as file:
        file.write(encrypted_data)
    if os.path.exists(file_path):
        os.remove(file_path)
    return enc_path

def decrypt_file(enc_path, key):
    """Şifreli dosyayı çözer"""
    f = Fernet(key)
    with open(enc_path, "rb") as file:
        encrypted_data = file.read()
    decrypted_data = f.decrypt(encrypted_data)
    
    # .enc uzantısını kaldırarak zip dosyasını geri oluşturur
    dec_path = enc_path.replace(".enc", "")
    with open(dec_path, "wb") as file:
        file.write(decrypted_data)
    return dec_path

def upload_to_minio(file_path, object_name):
    try:
        endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        s3 = boto3.client('s3',
            endpoint_url=f"http://{endpoint}",
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
            config=Config(signature_version='s3v4'),
            verify=False
        )
        
        bucket_name = 'cyber-backups'
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            s3.create_bucket(Bucket=bucket_name)
            logging.info(f"New bucket created: {bucket_name}")

        s3.upload_file(file_path, bucket_name, object_name)
        logging.info(f"Cloud Upload Success: {object_name}")
        return True
    except Exception as e:
        logging.error(f"Cloud upload failed: {e}")
        return False

# --- # 4. RESTORE LOGIC (YENİ EKLENDİ!) ---
def restore_backup(enc_filename, dest_path):
    """
    Siber Güvenlik Geri Yükleme Motoru:
    1. Veritabanından şifre anahtarını bulur.
    2. Dosyayı çözer.
    3. Arşivi klasöre çıkartır.
    """
    logging.info(f"Restore process started for: {enc_filename}")
    try:
        # Veritabanından anahtarı al
        conn = sqlite3.connect('backups_metadata.db')
        c = conn.cursor()
        c.execute("SELECT encryption_key FROM backup_records WHERE filename=?", (enc_filename,))
        result = c.fetchone()
        conn.close()

        if not result:
            return False, "Hata: Bu dosya için şifreleme anahtarı bulunamadı!"

        key = result[0].encode()
        enc_full_path = os.path.join("backups", enc_filename)

        if not os.path.exists(enc_full_path):
            return False, "Hata: Şifreli yedek dosyası yerel 'backups' klasöründe bulunamadı!"

        # 1. Şifreyi Çöz
        zip_path = decrypt_file(enc_full_path, key)
        
        # 2. Arşivden Çıkar
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)
            
        # Temizlik: Çözülen geçici zip dosyasını sil
        os.remove(zip_path)
        
        logging.info(f"Restore successful: {enc_filename} -> {dest_path}")
        return True, f"Başarıyla geri yüklendi: {dest_path}"

    except Exception as e:
        logging.error(f"Restore failed: {str(e)}")
        return False, f"Hata: {str(e)}"

# --- # 5. CORE BACKUP LOGIC ---
def create_backup():
    logging.info("Starting automated backup process...")
    init_db()
    raw_sources = os.getenv("BACKUP_SOURCES", "data_to_backup")
    source_dirs = [s.strip() for s in raw_sources.split(",")]
    
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    conn = sqlite3.connect('backups_metadata.db')
    c = conn.cursor()

    for s_dir in source_dirs:
        if not os.path.exists(s_dir):
            logging.error(f"Source folder not found: {s_dir}")
            continue
            
        backup_name = f"backup_{s_dir}_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            shutil.make_archive(backup_path, 'zip', s_dir)
            full_path = backup_path + ".zip"
            logging.info(f"Archive created: {full_path}")
            
            original_hash = calculate_hash(full_path)
            key = Fernet.generate_key()
            
            enc_file = encrypt_file(full_path, key)
            enc_filename = os.path.basename(enc_file)
            
            c.execute("INSERT INTO backup_records VALUES (?, ?, ?, ?)", 
                      (enc_filename, original_hash, key.decode(), timestamp))
            
            if upload_to_minio(enc_file, enc_filename):
                msg = f"Success: {s_dir} backed up!\nHash: {original_hash[:16]}...\nCloud synced."
                logging.info(f"Backup successful for {s_dir}")
                send_telegram_notification(msg)
            else:
                logging.warning(f"Encryption successful but cloud sync failed for {s_dir}")

        except Exception as e:
            logging.error(f"Critical error during backup of {s_dir}: {str(e)}")

    conn.commit()
    conn.close()
    logging.info("Backup process finished.")

if __name__ == "__main__":
    create_backup()