import unittest

from agent import render_report_html
from services.ai_analyzer import AIAnalyzer


class AIAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.emails = [
            {
                "id": "important-1",
                "from": "Ana <ana@cliente.com>",
                "subject": "Aprobación requerida",
                "date": "Fri, 19 Sep 2026 09:00:00 -0500",
                "body": "Por favor aprueba la propuesta antes del lunes.",
                "list_unsubscribe": "",
                "link": "https://mail.google.com/mail/u/0/#inbox/important-1",
            },
            {
                "id": "promo-1",
                "from": "Ofertas <news@tienda.com>",
                "subject": "50% de descuento",
                "date": "Fri, 19 Sep 2026 10:00:00 -0500",
                "body": "Compra hoy.",
                "list_unsubscribe": "<https://tienda.com/unsubscribe>",
                "link": "https://mail.google.com/mail/u/0/#inbox/promo-1",
            },
        ]

    def test_only_selected_messages_feed_the_report(self):
        analyzer = AIAnalyzer()
        responses = iter([
            {"important_email_ids": ["important-1"]},
            {
                "summary_overview": "Hay una aprobación pendiente.",
                "todo_list": [
                    {
                        "priority": "HIGH",
                        "task": "Aprobar propuesta",
                        "context": "Solicitud de Ana",
                        "deadline": "Lunes",
                        "email_link": "https://mail.google.com/mail/u/0/#inbox/important-1",
                    }
                ],
                "calendar_events": [],
            },
        ])
        analyzer._generate_json = lambda _prompt: next(responses)

        report = analyzer.analyze_emails(self.emails)

        self.assertEqual(report["todo_list"][0]["task"], "Aprobar propuesta")
        self.assertNotIn("promo-1", str(report))

    def test_unknown_links_are_removed_from_model_output(self):
        analyzer = AIAnalyzer()
        responses = iter([
            {"important_email_ids": ["important-1"]},
            {
                "summary_overview": "Resumen.",
                "todo_list": [
                    {
                        "priority": "LOW",
                        "task": "Revisar",
                        "context": "Ana",
                        "deadline": "Sin fecha",
                        "email_link": "https://example.com/phishing",
                    }
                ],
                "calendar_events": [],
            },
        ])
        analyzer._generate_json = lambda _prompt: next(responses)

        report = analyzer.analyze_emails(self.emails)

        self.assertEqual(report["todo_list"][0]["email_link"], "")

    def test_report_escapes_generated_html(self):
        html = render_report_html("<img src=x onerror=alert(1)>", [], [], "19/09/2026")
        self.assertIn("&lt;img", html)


if __name__ == "__main__":
    unittest.main()
