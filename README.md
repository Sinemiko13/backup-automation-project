# 🛡️ Backup Automation Project  
## Secure Cloud Backup, Monitoring & Disaster Recovery Suite

Cyber-Guardian is a Dockerized, S3-compatible secure backup system that encrypts local data before upload, verifies integrity using cryptographic hashing, and provides a real-time monitoring & recovery dashboard.
End-to-end encrypted cloud backup system with integrity verification, CI/CD automation and real-time monitoring dashboard.

---

## 🚀 Key Features

### 🔐 Client-Side AES-256 Encryption
- Files are encrypted locally using Fernet (AES-256)
- No plaintext data is ever uploaded to cloud storage

### 🧩 SHA-256 Integrity Verification
- Each file is hashed before upload
- Hash is stored in SQLite
- Integrity is verified during recovery before decryption

### ☁️ S3-Compatible Cloud Storage
- Uses MinIO running in Docker
- Integrated via boto3 (AWS S3 API compatible)
- Automatic bucket validation & creation

### 📊 Real-Time Monitoring Dashboard
Built with Streamlit.

The dashboard provides:
- Total secure backups counter
- Real-time system logs
- Backup metadata records (SQLite)
- One-click restore & verify
- Manual secure backup trigger

### ♻️ Disaster Recovery Workflow

Recovery process:

1. Download encrypted object from cloud  
2. Validate SHA-256 hash  
3. Decrypt using AES-256  
4. Restore original file safely  

---

## 🔄 CI/CD Pipeline

This project includes an automated CI pipeline using GitHub Actions.

On every push or pull request:

- Dependencies are installed  
- Code quality checks are executed  
- Unit tests are run  
- Docker image is built  
- Pipeline status is reported  

Workflow location:
.github/workflows/ci.yml


---

## 🏗️ Architecture Overview
Local File
↓
AES-256 Encryption
↓
SHA-256 Hash Generation
↓
Upload via Boto3
↓
MinIO (Docker - S3 API)
↓
Metadata stored in SQLite

Recovery:
Download → Verify Hash → Decrypt → Restore

---

## 🛠 Tech Stack

- Python 3
- Cryptography (Fernet – AES-256)
- hashlib (SHA-256)
- SQLite3
- MinIO (S3 compatible)
- Docker
- GitHub Actions (CI/CD)
- Boto3
- Streamlit
- Telegram Bot API

---

## ⚙️ Setup & Installation

### 1. Install Dependencies
pip install -r requirements.txt

### 2. Start MinIO (Docker)
docker run -p 9000:9000 -p 9001:9001
-e MINIO_ROOT_USER=minioadmin
-e MINIO_ROOT_PASSWORD=minioadmin
minio/minio server /data --console-address ":9001"

MinIO Console:  
http://localhost:9001

### 3. Configure Environment Variables

Create a `.env` file using `.env.example` as reference.

⚠️ Do not commit `.env` to version control.

### 4. Run the Application
streamlit run src/app.py

---

## 🔒 Security Design Principles

- Zero plaintext exposure  
- Integrity verification before decryption  
- Separation of encrypted data and metadata  
- Dockerized cloud simulation  
- CI-protected codebase  

---

## 🔮 Future Improvements

- AWS S3 production deployment  
- Role-based access control (RBAC)  
- Scheduled automated backups  
- Key rotation mechanism  
- Centralized logging (ELK / Prometheus)  
- Docker Compose deployment  
