import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Sayfa Ayarları
st.set_page_config(page_title="Cyber Backup Monitor", page_icon="🛡️")

st.title("🛡️ Siber Yedekleme ve İzleme Paneli")
st.markdown("---")

# 1. Yan Menü - İstatistikler
st.sidebar.header("📊 Sistem Durumu")
if os.path.exists("backups"):
    backup_count = len([f for f in os.listdir("backups") if f.endswith(".enc")])
    st.sidebar.metric("Toplam Güvenli Yedek", backup_count)

# 2. Canlı Log İzleme
st.subheader("📜 Sistem Günlükleri (Logs)")
if os.path.exists("backup.log"):
    with open("backup.log", "r") as f:
        logs = f.readlines()
        # Son 10 logu ters sırada göster
        st.text_area("Son İşlemler", "".join(logs[-10:][::-1]), height=200)
else:
    st.warning("Henüz log kaydı oluşturulmadı.")

# 3. Yedeklenmiş Dosyalar Listesi
st.subheader("📁 Mevcut Yedekler")
if os.path.exists("backups"):
    files = os.listdir("backups")
    if files:
        df = pd.DataFrame(files, columns=["Dosya Adı"])
        st.table(df)
    else:
        st.info("Yedek klasörü boş.")

# 4. Manuel Tetikleme Butonu
if st.button("🚀 Manuel Yedeklemeyi Başlat"):
    with st.spinner('Yedekleniyor ve Şifreleniyor...'):
        import subprocess
        result = subprocess.run(["python", "src/backup_engine.py"], capture_output=True, text=True)
        st.success("Yedekleme işlemi başarıyla tetiklendi!")