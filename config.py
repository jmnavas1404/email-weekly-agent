import os
from pathlib import Path
from dotenv import load_dotenv


# Cargar variables de entorno desde .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Modelos de IA disponibles (cascada: se intenta en orden hasta que uno responda)
GEMINI_MODEL_OPTIONS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite"
]

# Configuración de Inteligencia Artificial
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", GEMINI_MODEL_OPTIONS[0])

# Configuración Horaria y Programación Semanal
USER_TIMEZONE = os.getenv("USER_TIMEZONE", "America/Bogota")
REPORT_DAY = os.getenv("REPORT_DAY", "friday")
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "12"))
REPORT_MINUTE = int(os.getenv("REPORT_MINUTE", "0"))

# Rango de análisis de correos
DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))
MAX_EMAIL_CANDIDATES = int(os.getenv("MAX_EMAIL_CANDIDATES", "100"))

# Destinatario del reporte
REPORT_RECIPIENT_EMAIL = os.getenv("REPORT_RECIPIENT_EMAIL", "").strip()

# Rutas de archivos clave
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
PENDING_EVENTS_PATH = BASE_DIR / "pending_events.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# Scopes requeridos para Google OAuth (Gmail lectura/envío y Google Calendar)
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
]
