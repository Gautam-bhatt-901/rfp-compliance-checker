#  RFP Evaluator - Installation Guide

Complete step-by-step guide to set up the RFP Compliance Evaluator on your local machine.

---

##  Prerequisites

### Required Software

Before starting, install the following:

| Software | Version | Download Link |
|----------|---------|---------------|
| **Python** | 3.9+ | https://www.python.org/downloads/ |
| **Node.js** | 18.0+ | https://nodejs.org/ |
| **PostgreSQL** | 14+ | https://www.postgresql.org/download/ |
| **Git** | Latest | https://git-scm.com/ |

### Required API Keys

You'll need API keys from:

- **OpenAI** (Required): https://platform.openai.com/api-keys
- **Anthropic** (Optional): https://console.anthropic.com/

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: 5GB free space
- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)

---

##  Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/Gautam-bhatt-901/rfp-compliance-checker.git

# Navigate to project directory
cd rfp-evaluator
```


---

##  Step 2: Backend Setup

### 2.1 Create Virtual Environment

**On Windows:**

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

**On macOS/Linux:**

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

**Verify activation:**
You should see `(venv)` prefix in your terminal prompt.

---

### 2.2 Install Python Dependencies

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

**Expected output:**

```
Installing collected packages: fastapi, uvicorn, sqlalchemy, openai, langchain...
Successfully installed fastapi-0.109.0 uvicorn-0.27.0...
```

⏱️ **Time required**: 5-10 minutes (depending on internet speed)

---

### 2.3 Download spaCy Language Model

```bash
# Download English language model for NLP
python -m spacy download en_core_web_md
```

**Expected output:**

```
✔ Download and installation successful
You can now load the package via spacy.load('en_core_web_md')
```


---

### 2.4 Configure Environment Variables

#### Create .env file

```bash
# Copy template to create your .env file
cp .env.example .env
```

**If `.env.example` doesn't exist, create `.env` manually:**

```bash
# On Windows
notepad .env

# On macOS/Linux
nano .env
```


#### Add Required Configuration

**Paste this into your `.env` file:**

```env
# API Keys (REQUIRED)
OPENAI_API_KEY="your-openai-api-key-here"
ANTHROPIC_API_KEY="your-anthropic-key-here"

# Security (REQUIRED - Generate secure secret)
SECRET_KEY="your-jwt-secret-key"


# Database
DATABASE_URL=postgresql://rfp_user:admin@localhost:5432/rfp_db

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# RAG Configuration
USE_RAG_MATCHING=true
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_MODEL=text-embedding-3-small

# Performance Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
ENABLE_REDIS_CACHE=false
REDIS_URL=redis://localhost:6379/0

# Enable hybrid matching
USE_RAG_MATCHING=true
RAG_USE_LLM_VERIFICATION=true
RAG_TOP_K_CHUNKS=5

# Use cheaper model for verification (optional)
RAG_VERIFICATION_MODEL=gpt-4o-mini

# Keep existing settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_MODEL=text-embedding-3-small

# ============ ENHANCED DOCUMENT EXTRACTION ============
USE_ENHANCED_EXTRACTION=true

# PyMuPDF4LLM Settings
PYMUPDF4LLM_PAGE_CHUNKS=true
PYMUPDF4LLM_WRITE_IMAGES=false
PYMUPDF4LLM_TABLE_STRATEGY=lines_strict  # Options: lines, lines_strict, explicit
PYMUPDF4LLM_EXTRACT_WORDS=false

# Table Handling
TABLE_AS_SINGLE_CHUNK=true
TABLE_MAX_CHARS=4000
MARKDOWN_TABLE_DETECTION=true

# Fallback
EXTRACTION_FALLBACK_ENABLED=true

# ============ PADDLEOCR SETTINGS ============
PADDLEOCR_USE_GPU=false  # Set to true if you have GPU
PADDLEOCR_LANG=en
PADDLEOCR_SHOW_LOG=false

# Compliance Validation Settings
ENABLE_STRUCTURED_VALIDATION=true
VALIDATION_CONFIDENCE_HIGH=0.85
VALIDATION_CONFIDENCE_MEDIUM=0.65
NUMERIC_EXTRACTION_PRECISION=2
DATE_VALIDATION_BUFFER_DAYS=0
COUNT_VALIDATION_STRICT=true

# Performance Optimization Settings
ENABLE_BACKGROUND_PROCESSING=true
ENABLE_PARALLEL_PROCESSING=true
ENABLE_CHUNKED_PROCESSING=true
ENABLE_CACHE=true

# Parallel Processing
MAX_WORKER_PROCESSES=0  # 0 = auto-detect optimal count
MIN_FILES_FOR_PARALLEL=3

# Large File Handling
MAX_PDF_SIZE_MB=100
PDF_CHUNK_SIZE_PAGES=20
OCR_SELECTIVE_MODE=true
OCR_DPI=150
MEMORY_LIMIT_MB=1024

# Caching
CACHE_BACKEND=memory  # Use 'redis' for production
CACHE_MAX_SIZE=100
CACHE_TTL_SECONDS=3600

# Redis (if using redis backend)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_DB=0
# REDIS_PASSWORD=

# Security
ALLOWED_MIME_TYPES=application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document
MAX_CONCURRENT_UPLOADS=10
```


#### Generate Secure SECRET_KEY

```bash
# Generate a secure random secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and replace `your-super-secret-jwt-key-min-32-characters-change-this` with it.

#### Update API Keys

1. Get OpenAI API key from: https://platform.openai.com/api-keys
2. Replace `sk-proj-your-actual-openai-key-here` with your actual key
3. (Optional) Get Anthropic key and update accordingly

---

##  Step 3: Database Setup

### 3.1 Install PostgreSQL

**On Windows:**

1. Download installer from https://www.postgresql.org/download/windows/
2. Run the installer
3. Set password for `postgres` user (remember this!)
4. Default port: 5432
5. Complete installation

**On macOS:**

```bash
# Install using Homebrew
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Verify it's running
brew services list
```

**On Linux (Ubuntu/Debian):**

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql

# Enable auto-start on boot
sudo systemctl enable postgresql
```


---

### 3.2 Create Database and User

**Step 1: Connect to PostgreSQL**

```bash
# Connect as postgres superuser
psql -U postgres
```

**On Linux, you may need:**

```bash
sudo -u postgres psql
```

**Step 2: Run SQL Commands**

In the PostgreSQL prompt (`postgres=#`), run these commands:

```sql
-- Create the database
CREATE DATABASE rfp_db;

-- Create the user with password
CREATE USER rfp_user WITH PASSWORD 'admin';

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE rfp_db TO rfp_user;

-- Connect to the new database
\c rfp_db

-- Grant schema privileges (PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO rfp_user;

-- Exit PostgreSQL
\q
```

**Expected output:**

```
CREATE DATABASE
CREATE ROLE
GRANT
```


---

### 3.3 Install pgvector Extension

**Step 1: Install pgvector**

**On macOS:**

```bash
brew install pgvector
```

**On Linux (Ubuntu/Debian):**

```bash
sudo apt install postgresql-14-pgvector
```

**On Windows:**
Download from: https://github.com/pgvector/pgvector/releases

**Step 2: Enable in Database**

```bash
# Connect to your database
psql -U rfp_user -d rfp_db

# Enter password: admin
```

In PostgreSQL prompt:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
\dx

-- You should see 'vector' in the list
-- Exit
\q
```


---

### 3.4 Initialize Database Tables

**Option 1: Auto-create (Recommended for Development)**

Tables will be automatically created when you first start the backend server.

**Option 2: Manual Migration with Alembic**

```bash
# Ensure you're in backend directory with venv activated
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Initialize Alembic (if needed)
alembic init alembic

# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```


---

##  Step 4: Frontend Setup

### 4.1 Navigate to Frontend Directory

**Open a NEW terminal** (keep backend terminal open)

```bash
cd frontend
```


---

### 4.2 Install Node Dependencies

```bash
# Install all required packages
npm install
```

**Expected output:**

```
added 300 packages, and audited 301 packages in 45s
```

⏱️ **Time required**: 2-3 minutes

**Packages installed:**

- React 18.2.0
- React Router 6.21.0
- Material-UI 5.15.0
- Axios 1.6.5
- Vite 5.0.8

---

### 4.3 Configure Frontend Environment

#### Create .env file

```bash
# Copy template
cp .env.example .env
```

**If `.env.example` doesn't exist, create `.env` manually:**

```bash
# On Windows
notepad .env

# On macOS/Linux
nano .env
```


#### Add Configuration

**Paste this into your `.env` file:**

```env
# Backend API URL (default for local development)
VITE_API_URL=http://localhost:8000/api
```

**Save and close the file.**

---

##  Step 5: Verify Installation

### 5.1 Test Backend

**Terminal 1 (Backend):**

```bash
# Ensure you're in backend/ directory with venv activated
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process  using WatchFiles
INFO:     Started server process 
INFO:     Waiting for application startup.
✓ Structured Validation: ENABLED
INFO:     Application startup complete.
```

**✅ Success indicators:**

- No error messages
- Server running on port 8000
- Can access http://localhost:8000/docs (Swagger UI)

---

### 5.2 Test Frontend

**Terminal 2 (Frontend):**

```bash
# Ensure you're in frontend/ directory
cd frontend

# Start the development server
npm run dev
```

**Expected output:**

```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

**✅ Success indicators:**

- No error messages
- Server running on port 5173
- Can access http://localhost:5173 (shows login page)

---

### 5.3 Test Database Connection

**Open browser and go to:**

```
http://localhost:8000/docs
```

**Test the health endpoint:**

1. Find `/api/health` endpoint
2. Click "Try it out"
3. Click "Execute"
4. Should return `{"status": "healthy"}`

---

##  Installation Complete!

### Quick Start

**Start Backend:**

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Start Frontend:**

```bash
cd frontend
npm run dev
```

**Access Application:**

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

##  Troubleshooting

### Backend Issues

#### Error: "ModuleNotFoundError"

```bash
# Ensure venv is activated and reinstall
pip install -r requirements.txt
```


#### Error: "Database connection failed"

```bash
# Check PostgreSQL is running
# Windows: Check Services
# macOS: brew services list
# Linux: sudo systemctl status postgresql

# Verify DATABASE_URL in .env file
```


#### Error: "OpenAI API key invalid"

```bash
# Verify your API key at https://platform.openai.com/api-keys
# Check .env file has correct key
# Restart backend server
```


---

### Frontend Issues

#### Error: "Network Error / Can't connect"

```bash
# 1. Verify backend is running on port 8000
# 2. Check frontend/.env has correct VITE_API_URL
# 3. Restart frontend: npm run dev
```


#### Error: "npm install failed"

```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```


---

### Database Issues

#### Error: "pgvector extension not found"

```bash
# Install pgvector for your OS
# macOS: brew install pgvector
# Linux: sudo apt install postgresql-14-pgvector

# Then enable in database:
psql -U rfp_user -d rfp_db -c "CREATE EXTENSION vector;"
```


#### Error: "Permission denied for schema public"

```sql
-- Connect to database
psql -U postgres -d rfp_db

-- Grant permissions
GRANT ALL ON SCHEMA public TO rfp_user;
\q
```


---

##  Next Steps

After successful installation:

1. **Create Account**: Register at http://localhost:5173/register
2. **Upload Documents**: Go to Analyze page
3. **Run Analysis**: Upload RFP and supporting documents
4. **View Results**: Check Dashboard for history

---

**Installation Guide Version**: 2.0

