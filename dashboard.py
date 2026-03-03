# -*- coding: utf-8 -*-
# 1 2 3 4 5...
import streamlit as st
import pandas as pd
import os
import sqlite3
import subprocess
from src.backup_engine import restore_backup # Engine'deki restore fonksiyonunu bağladık

# Page Config
st.set_page_config(page_title="Cyber Backup Monitor", page_icon="🛡️")

st.title("🛡️ Cyber Backup & Monitoring Panel")
st.markdown("---")

# --- # 1. SIDEBAR - SYSTEM STATUS ---
st.sidebar.header("📊 System Status")
if os.path.exists("backups"):
    backup_count = len([f for f in os.listdir("backups") if f.endswith(".enc")])
    st.sidebar.metric("Total Secure Backups", backup_count)

# --- # 2. LOG VIEWER ---
st.subheader("📜 System Logs")
if os.path.exists("backup.log"):
    with open("backup.log", "r") as f:
        logs = f.readlines()
        st.text_area("Recent Actions", "".join(logs[-10:][::-1]), height=200)
else:
    st.warning("No logs found yet.")

# --- # 3. DATABASE RECORDS & RESTORE SECTION ---
st.subheader("📁 Database Records & Recovery")
db_path = "backups_metadata.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    # Database'den yedek kayıtlarını çekiyoruz
    df = pd.read_sql_query("SELECT filename, date, original_hash FROM backup_records", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True) # Tabloyu daha şık gösterir
        
        # Restore Feature
        st.markdown("---")
        st.subheader("🔄 Emergency Restore & Verify")
        selected_file = st.selectbox("Select a backup to restore:", df['filename'].tolist())
        
        if st.button("Verify & Restore Selected Backup"):
            with st.spinner('Decrypting and verifying integrity...'):
                # backup_engine.py içindeki restore fonksiyonunu çağırdık
                status_message = restore_backup(selected_file)
                if "Verified" in status_message:
                    st.success(status_message)
                else:
                    st.error(status_message)
    else:
        st.info("Database is empty. Run a backup first!")
else:
    st.info("Database not found. Initializing on first run...")

# --- # 4. MANUAL TRIGGER ---
st.markdown("---")
if st.button("🚀 Start Manual Backup"):
    with st.spinner('Running multi-source backup...'):
        # Arka planda backup_engine.py dosyasını çalıştırır
        result = subprocess.run(["python", "src/backup_engine.py"], capture_output=True, text=True)
        st.success("Backup process triggered successfully!")
        st.rerun() # Sayfayı yenileyerek yeni yedeği listeye ekler