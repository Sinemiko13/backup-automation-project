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
from botocore.client import Config
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Yapılandırmayı yükle
load_dotenv()

# --- # LOGGING & DB SETUP ---
logging.basicConfig(
    filename='backup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def init_db():
    """Veritabanını başlatır"""
    conn = sqlite3.connect('backups_metadata.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS backup_records 
                 (filename TEXT, original_hash TEXT, encryption_key TEXT, date TEXT)''')
    conn.commit()
    conn.close()

# --- # UTILS ---
def calculate_hash(file_path):
    """SHA-256 bütünlük kontrolü"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def send_telegram_notification(message):
    """Bildirim gönderimi"""
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10) 
    except Exception as e:
        logging.error(f"Telegram Notification bypassed: {e}")

# --- # ENCRYPTION & CLOUD ---
def encrypt_file(file_path, key):
    """AES-256 Şifreleme"""
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

# 1 2 3 4 5...
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
        
        # --- EKSTRA GÜVENLİK: Klasör var mı kontrol et, yoksa oluştur ---
        bucket_name = 'cyber-backups'
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            s3.create_bucket(Bucket=bucket_name)
            logging.info(f"New bucket created: {bucket_name}")
        # ----------------------------------------------------------

        s3.upload_file(file_path, bucket_name, object_name)
        logging.info(f"Cloud Upload Success: {object_name}")
        return True
    except Exception as e:
        logging.error(f"Cloud upload failed: {e}")
        return False

# --- # CORE BACKUP LOGIC ---
def create_backup():
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
            logging.error(f"Source not found: {s_dir}")
            continue
            
        backup_name = f"backup_{s_dir}_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            # 1. Zip
            shutil.make_archive(backup_path, 'zip', s_dir)
            full_path = backup_path + ".zip"
            
            # 2. Hash & Key
            original_hash = calculate_hash(full_path)
            key = Fernet.generate_key()
            
            # 3. Encrypt
            enc_file = encrypt_file(full_path, key)
            enc_filename = os.path.basename(enc_file)
            
            # 4. Save to DB
            c.execute("INSERT INTO backup_records VALUES (?, ?, ?, ?)", 
                      (enc_filename, original_hash, key.decode(), timestamp))
            
            # 5. Cloud Sync & Notification (Doğru sıralama!)
            if upload_to_minio(enc_file, enc_filename):
                msg = f"Success: {s_dir} backed up!\nHash: {original_hash[:16]}...\nCloud synced."
                logging.info(msg.replace("\n", " "))
                send_telegram_notification(msg)
            else:
                msg = f"Partial Success: {s_dir} encrypted but Cloud Upload failed."
                logging.warning(msg)

        except Exception as e:
            logging.error(f"Error backing up {s_dir}: {str(e)}")

    conn.commit()
    conn.close()

# --- # RESTORE LOGIC ---
def restore_backup(enc_filename):
    conn = sqlite3.connect('backups_metadata.db')
    c = conn.cursor()
    c.execute("SELECT encryption_key, original_hash FROM backup_records WHERE filename=?", (enc_filename,))
    row = c.fetchone()
    conn.close()

    if not row: return "Error: Metadata not found."

    key, old_hash = row
    restore_dir = "restored_files"
    if not os.path.exists(restore_dir): os.makedirs(restore_dir)

    source_path = os.path.join("backups", enc_filename)
    dest_path = os.path.join(restore_dir, enc_filename.replace(".enc", ""))

    try:
        f = Fernet(key.encode())
        with open(source_path, "rb") as file:
            encrypted_data = file.read()
        
        decrypted_data = f.decrypt(encrypted_data)
        with open(dest_path, "wb") as file:
            file.write(decrypted_data)

        if calculate_hash(dest_path) == old_hash:
            return "Integrity Verified: Data is original and safe! ✅"
        else:
            return "Warning: Hash mismatch! ⚠️"
    except Exception as e:
        return f"Restore error: {str(e)}"

if __name__ == "__main__":
    create_backup()