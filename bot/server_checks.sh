#!/bin/bash
# Скрипт для сбора диагностической информации на сервере
# Запустите: bash server_checks.sh

echo "=== Диагностика бота ==="
echo "Текущая директория: $(pwd)"
echo ""

echo "1. Проверка версии Python и установленных модулей"
python3 --version
pip list | grep -E "psycopg2|aiogram|logging"
echo ""

echo "2. Проверка существования директорий изображений"
ls -ld images/ images/real/ images/anime/ 2>/dev/null || echo "Директории не найдены"
echo ""

echo "3. Запуск check_images.py"
python3 check_images.py 2>&1
echo ""

echo "4. Проверка логов бота (последние 20 строк)"
if [ -f "bot.log" ]; then
    tail -20 bot.log
else
    echo "Файл bot.log не найден"
fi
echo ""

echo "5. Проверка службы бота"
systemctl status telegram-bot.service --no-pager 2>/dev/null || echo "Служба не найдена"
echo ""

echo "6. Проверка подключения к БД (количество REAL изображений)"
python3 -c "
import database
conn = database.get_connection()
if conn:
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM pictures WHERE type = 1')
    print('REAL images in DB:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM pictures WHERE type = 0')
    print('ANIME images in DB:', cur.fetchone()[0])
    database.return_connection(conn)
else:
    print('Нет подключения к БД')
"
echo ""

echo "7. Проверка пользователя 7413924512 (из лога)"
python3 -c "
import database
user = database.get_user(7413924512)
if user:
    print('User:', user['id'])
    print('Type:', user.get('type'))
    print('Cycle:', user.get('cycle'))
    print('Viewed_real length:', len(user.get('viewed_real', [])))
    print('Viewed_real:', user.get('viewed_real'))
else:
    print('Пользователь не найден')
"
echo ""

echo "Диагностика завершена."