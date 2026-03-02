FROM python:3.9-slim
WORKDIR /app
RUN mkdir -p /backups /data_to_backup

# Kütüphane listesini kopyala
COPY requirements.txt .

# Kütüphaneleri yükle (Bu satır çok önemli!)
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY src/ /app/src/

CMD ["python", "src/backup_engine.py"]