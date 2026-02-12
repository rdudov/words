#!/bin/bash

# Скрипт управления сервисом Words Bot

SERVICE_NAME="words-bot"

show_help() {
    echo "Управление сервисом Words Bot"
    echo ""
    echo "Использование: $0 {start|stop|restart|status|logs|logs-live|enable|disable|install|uninstall}"
    echo ""
    echo "Команды:"
    echo "  start      - Запустить сервис"
    echo "  stop       - Остановить сервис"
    echo "  restart    - Перезапустить сервис"
    echo "  status     - Показать статус сервиса"
    echo "  logs       - Показать логи сервиса"
    echo "  logs-live  - Показать логи в реальном времени"
    echo "  enable     - Включить автозапуск"
    echo "  disable    - Отключить автозапуск"
    echo "  install    - Установить сервис"
    echo "  uninstall  - Удалить сервис"
}

check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo "Требуются права администратора. Запустите с sudo"
        exit 1
    fi
}

case "$1" in
    start)
        check_sudo
        echo "Запуск сервиса $SERVICE_NAME..."
        systemctl start "$SERVICE_NAME"
        systemctl status "$SERVICE_NAME" --no-pager -l
        ;;
    stop)
        check_sudo
        echo "Остановка сервиса $SERVICE_NAME..."
        systemctl stop "$SERVICE_NAME"
        echo "Сервис остановлен"
        ;;
    restart)
        check_sudo
        echo "Перезапуск сервиса $SERVICE_NAME..."
        systemctl restart "$SERVICE_NAME"
        systemctl status "$SERVICE_NAME" --no-pager -l
        ;;
    status)
        echo "Статус сервиса $SERVICE_NAME:"
        systemctl status "$SERVICE_NAME" --no-pager -l
        ;;
    logs)
        echo "Логи сервиса $SERVICE_NAME:"
        journalctl -u "$SERVICE_NAME" --no-pager -l
        ;;
    logs-live)
        echo "Логи сервиса $SERVICE_NAME (в реальном времени):"
        echo "Для выхода нажмите Ctrl+C"
        journalctl -u "$SERVICE_NAME" -f
        ;;
    enable)
        check_sudo
        echo "Включение автозапуска сервиса $SERVICE_NAME..."
        systemctl enable "$SERVICE_NAME"
        echo "Автозапуск включен"
        ;;
    disable)
        check_sudo
        echo "Отключение автозапуска сервиса $SERVICE_NAME..."
        systemctl disable "$SERVICE_NAME"
        echo "Автозапуск отключен"
        ;;
    install)
        check_sudo
        ./install_service.sh
        ;;
    uninstall)
        check_sudo
        echo "Удаление сервиса $SERVICE_NAME..."
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
        echo "Сервис удален"
        ;;
    *)
        show_help
        exit 1
        ;;
esac
