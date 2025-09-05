#!/bin/bash
# Telegram Bot Service Script
# This script helps run the telegram bot as a background service

# Configuration
PROJECT_DIR="/Users/wnoubi/DEV/whatsapp bot"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/telegram_service.log"
PID_FILE="$PROJECT_DIR/telegram_bot.pid"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Function to start the service
start() {
    echo "Starting Telegram Bot service..."
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Telegram Bot is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file..."
            rm -f "$PID_FILE"
        fi
    fi
    
    # Start the bot
    cd "$PROJECT_DIR"
    nohup "$VENV_DIR/bin/python" run_telegram_bot.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    echo "Telegram Bot started with PID: $(cat "$PID_FILE")"
    echo "Logs are available at: $LOG_FILE"
}

# Function to stop the service
stop() {
    echo "Stopping Telegram Bot service..."
    
    if [ ! -f "$PID_FILE" ]; then
        echo "PID file not found. Bot may not be running."
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        sleep 2
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID"
            echo "Force killed Telegram Bot (PID: $PID)"
        else
            echo "Telegram Bot stopped gracefully (PID: $PID)"
        fi
    else
        echo "Bot with PID $PID is not running"
    fi
    
    rm -f "$PID_FILE"
}

# Function to restart the service
restart() {
    stop
    sleep 2
    start
}

# Function to check status
status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Telegram Bot is running (PID: $PID)"
            echo "Logs: tail -f $LOG_FILE"
            return 0
        else
            echo "Telegram Bot is not running (stale PID file exists)"
            return 1
        fi
    else
        echo "Telegram Bot is not running"
        return 1
    fi
}

# Function to show logs
logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "=== Telegram Bot Logs ==="
        tail -f "$LOG_FILE"
    else
        echo "Log file not found: $LOG_FILE"
    fi
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Telegram Bot service"
        echo "  stop    - Stop the Telegram Bot service"
        echo "  restart - Restart the Telegram Bot service"
        echo "  status  - Check if the service is running"
        echo "  logs    - Show and follow the service logs"
        exit 1
        ;;
esac
