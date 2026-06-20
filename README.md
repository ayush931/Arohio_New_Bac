# Arohio Backend Service

Arohio is a FastAPI-based backend application designed to help teams generate, manage, and export high-quality, WCAG-compliant **Alt Text** for accessibility. It provides powerful features for processing PDFs, images, and Excel sheets in bulk, alongside an AI-powered conversational assistant.

---

## 🚀 Key Features

* **PDF Image Extraction**: Extract images from PDF documents and manage them individually.
* **Alt Text Generation**: Automatic Alt Text generation using state-of-the-art vision models (OpenAI API), with support for editing and regenerating outputs.
* **Direct Image Uploads**: Single or batch image uploads with real-time Alt Text generation.
* **Bulk Sheet Processing (Excel/CSV)**:
  * Extract embedded images anchored in worksheets.
  * Generate bulk Alt Text for images referenced via local paths or web URLs.
  * Export results to custom `.json`, `.csv`, or `.xlsx` formats.
* **AI Chat Assistant**: Integrated conversational bot powered by Ollama to answer questions specifically about accessibility, WCAG guidelines, and Arohio workflows.
* **Access Control & Audits**: Role-based access control (RBAC) and detailed audit logs for admin oversight.
* **Plans & Usage Management**: Tracking user plans, transaction histories, usage limits (PDF and image processing counts), and resource allocations.
* **Support & Community**: In-built support ticketing system, contact forms, and newsletter integrations.

---

## 🛠️ Technology Stack

* **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python ASGI web framework)
* **Database ORM**: [SQLAlchemy](https://www.sqlalchemy.org/) (Synchronous engine with async options)
* **Migrations**: [Alembic](https://alembic.sqlalchemy.org/) (Database migrations tool)
* **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI server)
* **AI Integrations**:
  * **OpenAI API**: Used for image extraction, analysis, and Alt Text generation using GPT Vision models.
  * **Ollama**: Host for local conversational models (e.g. `llama3` or `llava`) for domain-restricted chat.
* **OCR**: [EasyOCR](https://github.com/JaidedAI/EasyOCR) (for image text detection)
* **Data Processing**: [Pandas](https://pandas.pydata.org/) & [Openpyxl](https://openpyxl.readthedocs.io/) (for parsing and writing Excel sheets)
* **Authentication & Security**: [passlib](https://passlib.readthedocs.io/) (Bcrypt password hashing) & JWT tokens

---

## 📁 Repository Structure

```text
Arohio_New_Backend/
├── alembic/                # Alembic database migration scripts & versions
├── alembic.ini             # Alembic configuration
├── app/
│   ├── api/                # FastAPI endpoints (routes_users, routes_ai_chat, routes_excel_to_alt_text, etc.)
│   ├── controllers/        # Business logic controllers
│   ├── core/               # Application configuration, settings, and db connections
│   ├── db/                 # DB Session and helper declarations
│   ├── models/             # SQLAlchemy Database models (User, Project, UserPlan, etc.)
│   ├── schemas/            # Pydantic schemas for request/response serialization
│   ├── seeders/            # Database seed scripts for users, plans, and logs
│   ├── services/           # External service integrations
│   └── main.py             # FastAPI entrypoint file
├── public/                 # Static files and profile images
├── storage/                # Storage directories
├── uploads/                # Directory for uploaded documents and processed images
├── requirements.txt        # Project dependencies (encoded in UTF-16LE)
└── venv/                   # Python virtual environment (optional)
```

---

## 🔧 Installation & Setup

Follow these steps to set up the backend service locally:

### 1. Clone & Set Up Python Environment

Create and activate a Python virtual environment:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it (Linux/macOS)
source venv/bin/activate

# Or activate it (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies
>
> [!NOTE]
> The `requirements.txt` file is encoded in **UTF-16LE**. If your `pip install` command has issues reading the encoding, convert the file to UTF-8 first before running installation:

```bash
# Convert requirements to UTF-8 (Linux/macOS)
iconv -f UTF-16LE -t UTF-8 requirements.txt > requirements_utf8.txt

# Install dependencies
pip install -r requirements_utf8.txt
```

### 3. Environment Variables Setup

Copy the sample env file and configure it:

```bash
cp .env.example .env
```

Open `.env` and fill out the following keys:

```ini
# Database configuration
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<dbname>

# Security configuration
JWT_SECRET=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Application configuration
BASE_URL=http://localhost:8000

# Chat assistant configuration (Ollama)
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llava:latest  # or llama3:latest

# Vision/Alt-Text generator configuration (OpenAI)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

---

## 🗄️ Database Setup & Seeding

### 1. Run Migrations

Run Alembic migrations to construct the database schema:

```bash
alembic upgrade head
```

### 2. Run Seeders

Populate the database with initial admin accounts, user plans, usage logs, and sample transactions:

```bash
# Seed default admin user (admin@yopmail.com / Admin@123)
python -m app.seeders.seeder_user_details

# Seed plans
python -m app.seeders.seeder_user_plans

# Seed transactions
python -m app.seeders.seeder_plan_transactions

# Seed usage logs
python -m app.seeders.seeder_usage_logs
```

---

## 🚦 Running the Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* **API Root URL**: `http://localhost:8000`
* **Swagger Documentation**: `http://localhost:8000/docs` (Interactive UI for testing routes)
* **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 🤖 AI Chat Assistant Scope

The chatbot located at the `/ai` route only responds to questions about accessibility, WCAG guidelines, and Arohio platform workflows. It is configured to gracefully decline queries that fall outside of this domain to ensure compliance and focus.
