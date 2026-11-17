import argparse
from datetime import datetime, timedelta
import pytz
from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from services.gmail_service import GmailService
from services.calendar_service import CalendarService
from services.ai_analyzer import AIAnalyzer, AnalysisError


def render_report_html(summary_overview: str, todo_list: list, calendar_events: list, date_str: str) -> str:
    """Renderiza la plantilla HTML para el correo del reporte."""
    env = Environment(
        loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report_email.html")
    return template.render(
        summary_overview=summary_overview,
        todo_list=todo_list,
        calendar_events=calendar_events,
        date_str=date_str
    )


def run_weekly_report(force: bool = False):
    """Ejecuta el flujo completo de análisis, generación y envío del reporte semanal."""
    tz = pytz.timezone(config.USER_TIMEZONE)
    now = datetime.now(tz)
    weekdays = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    date_str = f"{weekdays[now.weekday()]}, {now.day} de {months[now.month - 1]} de {now.year}"

    print(f"🚀 [1/5] Iniciando agente de reporte semanal ({date_str} - {now.strftime('%I:%M %p')})...")

    # 1. Conectar a Gmail
    print("📬 [2/5] Conectando a Gmail y recopilando correos importantes...")
    gmail_service = GmailService()
    subject = f"🚨 [ALTA PRIORIDAD] 📊 Reporte Semanal de Correos & Tareas - {now.strftime('%d/%m/%Y')}"
    if not force and gmail_service.has_sent_report(subject):
        print("ℹ️ Ya existe un reporte enviado para hoy. Se omite el duplicado (usa --force para reenviar).")
        return True

    emails = gmail_service.fetch_recent_emails(days_back=config.DAYS_BACK)
    print(f"   ✓ Se obtuvieron {len(emails)} correos candidatos de los últimos {config.DAYS_BACK} días.")

    # 2. Analizar con Inteligencia Artificial (Gemini)
    print("🧠 [3/5] Analizando correos con Gemini (Resumen, Prioridades y Calendario)...")
    analyzer = AIAnalyzer()
    try:
        analysis = analyzer.analyze_emails(emails)
    except AnalysisError as error:
        print(f"❌ No se envió el reporte porque el análisis de IA falló: {error}")
        return False

    summary_overview = analysis.get("summary_overview", "")
    todo_list = analysis.get("todo_list", [])
    raw_events = analysis.get("calendar_events", [])

    # 3. Procesar eventos y generar enlaces de Google Calendar (1-clic)
    print("📅 [4/5] Procesando eventos y fechas límite detectadas...")
    processed_events = []
    for idx, evt in enumerate(raw_events, 1):
        evt_id = f"evt-{idx}"
        evt["id"] = evt_id
        evt_date_str = evt["date"]
        evt_time_str = evt["time"]
        try:
            dt_str = f"{evt_date_str} {evt_time_str}"
            start_dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
        except ValueError:
            print(f"⚠️ Evento omitido por fecha inválida: {evt.get('title', 'Sin título')}")
            continue

        duration = evt["duration_minutes"]
        end_dt = start_dt + timedelta(minutes=duration)

        cal_url = CalendarService.generate_calendar_link(
            title=evt.get("title", "Reunión / Compromiso"),
            start_dt=start_dt,
            end_dt=end_dt,
            description=f"{evt.get('description', '')}\n\nOrigen: {evt.get('email_link', '')}",
            location=evt.get("location", "")
        )
        evt["calendar_url"] = cal_url
        evt["status"] = "pending"
        processed_events.append(evt)

    # Guardar en archivo local de eventos pendientes
    CalendarService.save_pending_events(processed_events)
    print(f"   ✓ {len(processed_events)} eventos preparados con enlaces de 1-clic.")

    # 4. Enviar reporte por correo
    print("✉️ [5/5] Generando y enviando reporte por correo...")
    html_content = render_report_html(
        summary_overview=summary_overview,
        todo_list=todo_list,
        calendar_events=processed_events,
        date_str=date_str
    )

    recipient = config.REPORT_RECIPIENT_EMAIL if config.REPORT_RECIPIENT_EMAIL else gmail_service.get_user_email()
    gmail_service.send_report_email(
        recipient_email=recipient,
        subject=subject,
        html_body=html_content,
        plain_body=summary_overview,
        high_priority=True
    )

    print(f"🎉 ¡Reporte semanal enviado exitosamente a {recipient}!")
    print(f"   • Tareas prioritarias identificadas: {len(todo_list)}")
    print(f"   • Eventos detectados para calendario: {len(processed_events)}")
    return True


def list_pending_events():
    """Muestra la lista de eventos pendientes de confirmación en la consola."""
    events = CalendarService.load_pending_events()
    if not events:
        print("ℹ️ No hay eventos pendientes de confirmación.")
        return

    print("\n📅 Eventos pendientes detectados:")
    print("-" * 60)
    for evt in events:
        status_icon = "⏳ Pendiente" if evt.get("status") == "pending" else "✅ Confirmado"
        print(f"[{evt.get('id')}] {evt.get('title')} ({status_icon})")
        print(f"   Fecha: {evt.get('date')} a las {evt.get('time')} ({evt.get('duration_minutes', 60)} min)")
        if evt.get("location"):
            print(f"   Ubicación: {evt.get('location')}")
        if evt.get("description"):
            print(f"   Detalles: {evt.get('description')}")
        print(f"   Link 1-Clic: {evt.get('calendar_url')}")
        print("-" * 60)


def confirm_event(target_id: str):
    """Crea el evento en Google Calendar vía API y actualiza el estado."""
    events = CalendarService.load_pending_events()
    if not events:
        print("❌ No hay eventos pendientes.")
        return

    gmail_service = GmailService()
    cal_service = CalendarService(gmail_service.creds)
    tz = pytz.timezone(config.USER_TIMEZONE)

    confirmed_count = 0
    for evt in events:
        if target_id.lower() == "all" or evt.get("id") == target_id:
            if evt.get("status") == "confirmed":
                print(f"ℹ️ El evento {evt.get('id')} ya estaba confirmado previamente.")
                continue

            dt_str = f"{evt.get('date')} {evt.get('time')}"
            try:
                start_dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
            except Exception:
                start_dt = datetime.now(tz) + timedelta(days=1)
            end_dt = start_dt + timedelta(minutes=int(evt.get("duration_minutes", 60)))

            created = cal_service.create_event(
                title=evt.get("title"),
                start_dt=start_dt,
                end_dt=end_dt,
                description=f"{evt.get('description', '')}\n\nOrigen: {evt.get('email_link', '')}",
                location=evt.get("location", "")
            )
            evt["status"] = "confirmed"
            evt["google_event_id"] = created.get("id")
            confirmed_count += 1
            print(f"✅ Evento agendado en Google Calendar: {evt.get('title')} ({created.get('htmlLink')})")

    CalendarService.save_pending_events(events)
    print(f"\n✨ Total de eventos confirmados y agendados: {confirmed_count}")


def test_authentication():
    """Prueba la autenticación OAuth con Google y muestra la cuenta conectada."""
    print("🔐 Verificando credenciales de Google...")
    try:
        gmail_service = GmailService()
        email_addr = gmail_service.get_user_email()
        print(f"✅ ¡Autenticación exitosa con Google!")
        print(f"   👤 Cuenta vinculada: {email_addr}")
        print("   📬 Permisos de Gmail: Activos")
        print("   📅 Permisos de Google Calendar: Activos")
        print(f"   🔑 Token guardado en: {config.TOKEN_PATH}")
    except FileNotFoundError as e:
        print(f"\n❌ Error de configuración: {e}")
        print("\n👉 Para solucionarlo:")
        print("1. Ve a Google Cloud Console (https://console.cloud.google.com/).")
        print("2. Crea un proyecto y habilita 'Gmail API' y 'Google Calendar API'.")
        print("3. En 'Pantalla de consentimiento OAuth', agrega tu correo como usuario de prueba.")
        print("4. En 'Credenciales', crea un 'ID de cliente de OAuth' tipo 'App de escritorio'.")
        print(f"5. Descarga el archivo JSON y guárdalo como: {config.CREDENTIALS_PATH}\n")
    except Exception as e:
        print(f"❌ Error durante la autenticación: {e}")


def main():
    parser = argparse.ArgumentParser(description="Agente de IA para Reporte Semanal de Correos y Calendario")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando run
    run_parser = subparsers.add_parser("run", help="Ejecuta el análisis y envía el reporte semanal (Viernes 12:00 PM)")
    run_parser.add_argument("--force", action="store_true", help="Envía el reporte aunque ya exista uno para hoy")

    # Comando auth
    subparsers.add_parser("auth", help="Inicia sesión por primera vez con Google OAuth")

    # Comando list-events
    subparsers.add_parser("list-events", help="Muestra los eventos pendientes de confirmación")

    # Comando confirm
    confirm_parser = subparsers.add_parser("confirm", help="Confirma y agenda un evento en Google Calendar")
    confirm_parser.add_argument("event_id", help="ID del evento (ej. evt-1) o 'all' para todos")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        if not run_weekly_report(force=getattr(args, "force", False)):
            raise SystemExit(1)
    elif args.command == "auth":
        test_authentication()
    elif args.command == "list-events":
        list_pending_events()
    elif args.command == "confirm":
        confirm_event(args.event_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
