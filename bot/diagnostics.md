# Диагностика проблемы "Нет доступных изображений"

## 1. Обновление кода на сервере

Убедитесь, что все изменения загружены на сервер:

```bash
cd /path/to/bot
git pull origin main  # или другая ветка
```

Проверьте, что файлы `database.py`, `logging_config.py`, `bot.py`, `image_loader.py` обновлены.

## 2. Перезапуск бота

```bash
sudo systemctl restart telegram-bot.service   # или другой способ
```

## 3. Запуск скрипта проверки изображений

Скрипт `check_images.py` уже находится в папке `bot`. Запустите его:

```bash
cd /path/to/bot
python3 check_images.py
```

Пришлите полный вывод.

## 4. Проверка логов бота

После перезапуска попробуйте запросить real изображения через бота (нажмите кнопку "real" или отправьте команду /start). Затем посмотрите логи:

```bash
sudo journalctl -u telegram-bot.service -n 50 --no-pager
```

Или посмотрите файл `bot.log` в корневой директории бота:

```bash
tail -f /path/to/bot/bot.log
```

Пришлите новые логи, особенно строки, содержащие "candidate", "First candidate path", "has no available images".

## 5. Проверка базы данных (опционально)

Если проблема не ясна, можно выполнить SQL-запросы:

```bash
sudo -u postgres psql -d your_database_name -c "SELECT COUNT(*) FROM pictures WHERE type = 1;"
sudo -u postgres psql -d your_database_name -c "SELECT path FROM pictures WHERE type = 1 LIMIT 5;"
```

Замените `your_database_name` на имя вашей БД.

## 6. Проверка путей

Убедитесь, что директория `images/real` существует и содержит файлы:

```bash
ls -la /path/to/bot/images/real/ | head -10
```

Сравьте имена файлов с путями в БД.

## Интерпретация результатов

- Если скрипт `check_images.py` показывает, что файлы отсутствуют (MISSING), значит пути в БД не соответствуют фактическому расположению файлов. Возможно, нужно изменить `IMAGE_DIR_REAL` в `database.py`.
- Если кандидатов нет (`No candidate images`), значит запрос не возвращает строк. Это может быть из-за того, что все изображения уже просмотрены (поле `viewed_real` содержит все ID) или условие `need_moderate = false` не выполняется.
- Если кандидаты есть, но файлы не найдены, возможно, путь строится неправильно (например, из-за относительных путей). Проверьте значение `BASE_DIR` на сервере.

После получения диагностических данных пришлите их мне для анализа.
