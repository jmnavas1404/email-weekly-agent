#!/usr/bin/env bash

# GitHub Actions es el programador principal. Este script solo habilita cron local de forma explícita.
PROJECT_DIR="/home/juan-alvarez/Me/git/personal/ai-agent"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
AGENT_SCRIPT="$PROJECT_DIR/agent.py"
LOG_FILE="$PROJECT_DIR/agent.log"

# 0 12 * * 5 = Minuto 0, Hora 12, Cualquier día del mes, Cualquier mes, Viernes (5)
CRON_CMD="0 12 * * 5 cd $PROJECT_DIR && $VENV_PYTHON $AGENT_SCRIPT run >> $LOG_FILE 2>&1"
CRON_TAG="# AI-EMAIL-AGENT-WEEKLY-FRIDAY-12PM"

if [ "$1" == "--remove" ]; then
    # Limpiar tags antiguos (incluyendo el anterior de las 6pm si existía)
    crontab -l 2>/dev/null | grep -v "# AI-EMAIL-AGENT" | crontab -
    echo "🗑️ Tarea cron eliminada exitosamente."
    exit 0
fi

if [ "$1" != "--enable-local" ]; then
    echo "ℹ️ No se creó una tarea cron local. GitHub Actions es el programador recomendado."
    echo "   Para usar cron local, primero desactiva el workflow de GitHub y ejecuta: ./setup_cron.sh --enable-local"
    exit 0
fi

# Limpiar una posible versión anterior antes de crear la nueva regla.
crontab -l 2>/dev/null | grep -v "# AI-EMAIL-AGENT" | crontab -

# Agregar la nueva regla al crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD $CRON_TAG") | crontab -

echo "✅ Tarea programada configurada con éxito en crontab:"
echo "   ⏰ Horario: Cada viernes a las 12:00 PM (Mediodía - Hora Colombia)"
echo "   📁 Proyecto: $PROJECT_DIR"
echo "   📄 Logs de ejecución: $LOG_FILE"
echo ""
echo "Para verificar tu crontab: crontab -l"
echo "Para desinstalarla: ./setup_cron.sh --remove"
