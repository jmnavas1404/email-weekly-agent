import json
import os
import urllib.parse
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build

import config


class CalendarService:
    def __init__(self, creds):
        self.creds = creds
        self.service = build("calendar", "v3", credentials=self.creds)

    @staticmethod
    def generate_calendar_link(title: str, start_dt: datetime, end_dt: datetime = None, description: str = "", location: str = "") -> str:
        """
        Genera un enlace directo a Google Calendar (1-clic) para que el usuario
        pueda abrirlo desde el correo y confirmar la creación con un solo toque.
        """
        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        # Formato Google Calendar: YYYYMMDDTHHMMSSZ (en UTC)
        start_utc = start_dt.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")
        end_utc = end_dt.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")

        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_utc}/{end_utc}",
            "details": description,
            "location": location
        }
        return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

    def create_event(self, title: str, start_dt: datetime, end_dt: datetime = None, description: str = "", location: str = "") -> dict:
        """Crea el evento directamente en Google Calendar vía API."""
        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        tz_str = config.USER_TIMEZONE

        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": tz_str
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": tz_str
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                    {"method": "email", "minutes": 60}
                ]
            }
        }

        created = self.service.events().insert(calendarId="primary", body=event_body).execute()
        return created

    @staticmethod
    def save_pending_events(events: list):
        """Guarda los eventos detectados en pending_events.json para consulta o confirmación."""
        with open(config.PENDING_EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_pending_events() -> list:
        """Carga los eventos pendientes de aprobación."""
        if not os.path.exists(config.PENDING_EVENTS_PATH):
            return []
        try:
            with open(config.PENDING_EVENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
