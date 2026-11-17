import os
import base64
import email
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup
from email.utils import formataddr, make_msgid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config


class GmailService:
    def __init__(self):
        self.creds = None
        self.service = None
        self.user_email = None
        self._authenticate()

    def _authenticate(self):
        """Gestiona la autenticación OAuth 2.0 con Google."""
        if os.path.exists(config.TOKEN_PATH):
            self.creds = Credentials.from_authorized_user_file(
                str(config.TOKEN_PATH), config.GOOGLE_SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(config.CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"No se encontró el archivo '{config.CREDENTIALS_PATH}'. "
                        "Por favor descarga tu credentials.json desde Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.CREDENTIALS_PATH), config.GOOGLE_SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Guardar el token para futuras ejecuciones
            with open(config.TOKEN_PATH, "w", encoding="utf-8") as token_file:
                token_file.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds)
        profile = self.service.users().getProfile(userId="me").execute()
        self.user_email = profile.get("emailAddress", "")

    def get_user_email(self) -> str:
        """Retorna la dirección de correo de la cuenta autenticada."""
        return self.user_email

    def fetch_recent_emails(self, days_back: int = None, max_results: int = None):
        """
        Obtiene los correos importantes recibidos en los últimos N días.
        Filtra automáticamente promociones, spam y redes sociales.
        """
        if days_back is None:
            days_back = config.DAYS_BACK
        if max_results is None:
            max_results = config.MAX_EMAIL_CANDIDATES

        tz = pytz.timezone(config.USER_TIMEZONE)
        since_date = (datetime.now(tz) - timedelta(days=days_back)).strftime("%Y/%m/%d")

        # Query que excluye spam, promociones, redes sociales y reportes del propio agente
        query = f'after:{since_date} -category:promotions -category:social -category:spam -subject:"Reporte Semanal"'

        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        email_items = []

        for msg_meta in messages:
            msg = self.service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("subject", "(Sin Asunto)")
            sender = headers.get("from", "(Remitente Desconocido)")
            date_str = headers.get("date", "")

            body = self._extract_body(msg.get("payload", {}))
            snippet = msg.get("snippet", "")

            # Truncar cuerpo para optimizar contexto
            clean_body = (body if body else snippet)[:1200]

            email_items.append({
                "id": msg_meta["id"],
                "subject": subject,
                "from": sender,
                "date": date_str,
                "snippet": snippet,
                "body": clean_body,
                "list_unsubscribe": headers.get("list-unsubscribe", ""),
                "link": f"https://mail.google.com/mail/u/0/#inbox/{msg_meta['id']}"
            })

        return email_items

    def has_sent_report(self, subject: str) -> bool:
        """Indica si ya hay un reporte con ese asunto en la carpeta Enviados."""
        results = self.service.users().messages().list(
            userId="me", q=f'in:sent subject:"{subject}"', maxResults=1
        ).execute()
        return bool(results.get("messages", []))

    def _extract_body(self, payload: dict) -> str:
        """Extrae el contenido de texto plano o HTML limpio de un mensaje."""
        text = ""
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif mime_type == "text/html" and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    html_content = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html_content, "html.parser")
                    text = soup.get_text(separator="\n").strip()
                elif "parts" in part:
                    nested_text = self._extract_body(part)
                    if nested_text:
                        return nested_text
        elif "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            content = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            if payload.get("mimeType") == "text/html":
                soup = BeautifulSoup(content, "html.parser")
                return soup.get_text(separator="\n").strip()
            return content

        return text

    def send_report_email(self, recipient_email: str, subject: str, html_body: str, plain_body: str = "", high_priority: bool = True):
        """Envía el reporte formateado en HTML al destinatario con marca de Alta Prioridad."""
        message = MIMEMultipart("alternative")
        message["To"] = recipient_email
        message["From"] = formataddr(("Agente Semanal IA", self.user_email))
        message["Reply-To"] = self.user_email
        message["Subject"] = subject
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message["Auto-Submitted"] = "auto-generated"

        # Encabezados de Alta Prioridad (reconocidos por Gmail, Outlook, Apple Mail)
        if high_priority:
            message["X-Priority"] = "1"
            message["X-MSMail-Priority"] = "High"
            message["Importance"] = "High"
            message["Priority"] = "urgent"

        if plain_body:
            message.attach(MIMEText(plain_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        sent = self.service.users().messages().send(
            userId="me", body={"raw": raw_message}
        ).execute()

        return sent
