# Автозапуск сервиса Words Bot

Этот документ описывает настройку автозапуска телеграм-бота Words через systemd.

## Требования

- Linux с systemd
- Права администратора (sudo)
- Установленный Python и виртуальное окружение
- Настроенный `.env`

## Быстрая установка

1. Установка сервиса:
   ```bash
   sudo ./install_service.sh
   ```

2. Запуск сервиса:
   ```bash
   sudo systemctl start words-bot
   ```

3. Проверка статуса:
   ```bash
   sudo systemctl status words-bot
   ```

## Управление сервисом

```bash
# Справка
./manage_service.sh

# Запуск / остановка / перезапуск
sudo ./manage_service.sh start
sudo ./manage_service.sh stop
sudo ./manage_service.sh restart

# Статус
./manage_service.sh status

# Логи
./manage_service.sh logs
./manage_service.sh logs-live

# Автозапуск
sudo ./manage_service.sh enable
sudo ./manage_service.sh disable

# Удаление
sudo ./manage_service.sh uninstall
```

## Основные команды systemctl

```bash
sudo systemctl start words-bot
sudo systemctl stop words-bot
sudo systemctl restart words-bot
sudo systemctl status words-bot
sudo systemctl enable words-bot
sudo systemctl disable words-bot
sudo journalctl -u words-bot
sudo journalctl -u words-bot -f
```

## Файлы сервиса

- `words-bot.service` - unit-файл systemd
- `install_service.sh` - установка unit-файла
- `manage_service.sh` - управление сервисом

## Конфигурация

- Рабочая директория: `/opt/projects/words`
- Python: `/opt/projects/words/venv/bin/python`
- Команда запуска: `python -m src.words`
- Автоперезапуск: включен
- Логи: systemd journal

## Диагностика

```bash
# Статус
sudo systemctl status words-bot

# Последние логи
sudo journalctl -u words-bot -n 50

# Проверка .env
ls -la /opt/projects/words/.env

# Проверка окружения
/opt/projects/words/venv/bin/python -m pip list
```
