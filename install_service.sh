#!/bin/bash

# Скрипт установки сервиса Words Bot

set -e

echo "Установка сервиса Words Bot..."

# Проверяем права администратора
if [ "$EUID" -ne 0 ]; then
    echo "Запустите скрипт с правами администратора (sudo)"
    exit 1
fi

# Проверяем наличие файла сервиса
if [ ! -f "words-bot.service" ]; then
    echo "Файл words-bot.service не найден"
    exit 1
fi

# Копируем файл сервиса
echo "Копирование файла сервиса..."
cp words-bot.service /etc/systemd/system/

# Устанавливаем права доступа
chmod 644 /etc/systemd/system/words-bot.service

# Перезагружаем конфигурацию systemd
echo "Перезагрузка конфигурации systemd..."
systemctl daemon-reload

# Включаем автозапуск
echo "Включение автозапуска..."
systemctl enable words-bot.service

echo "Сервис успешно установлен"
echo ""
echo "Доступные команды:"
echo "  sudo systemctl start words-bot    - Запустить сервис"
echo "  sudo systemctl stop words-bot     - Остановить сервис"
echo "  sudo systemctl restart words-bot  - Перезапустить сервис"
echo "  sudo systemctl status words-bot   - Проверить статус"
echo "  sudo journalctl -u words-bot -f   - Логи в реальном времени"
echo ""
echo "Для запуска сервиса выполните: sudo systemctl start words-bot"
