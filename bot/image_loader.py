import os
import argparse
import logging
import shutil
from pathlib import Path
from collections import defaultdict
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

# Пути к папкам (относительно расположения скрипта)
SCRIPT_DIR = Path(__file__).parent
NEW_ANIME_DIR = SCRIPT_DIR / 'images' / 'new' / 'anime'
NEW_REAL_DIR = SCRIPT_DIR / 'images' / 'new' / 'real'
TARGET_ANIME_DIR = SCRIPT_DIR / 'images' / 'anime'
TARGET_REAL_DIR = SCRIPT_DIR / 'images' / 'real'


def extract_date_from_filename(filename):
    """
    Извлекает дату из имени файла, которая находится между '@' и первой точкой.
    Пример: "some_name@2025-03-10.jpg" -> "2025-03-10"
    Если дата не найдена, возвращает None.
    """
    try:
        return filename.split('@')[1].split('.')[0]
    except IndexError:
        return None


def collect_images_from_folder(folder_path):
    """
    Рекурсивно обходит папку и возвращает словарь:
    { date1: [(filename1, full_path1), ...], date2: [...], ... }
    Файлы без даты пропускаются.
    """
    images_by_date = defaultdict(list)
    base = Path(folder_path)
    if not base.is_dir():
        logging.warning(f"Предупреждение: {folder_path} не существует, пропускаем.")
        return images_by_date

    for file_path in base.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            date = extract_date_from_filename(file_path.name)
            if date:
                images_by_date[date].append((file_path.name, file_path))
            else:
                logging.warning(f"Предупреждение: не удалось извлечь дату из {file_path.name}, пропускаем.")
    return images_by_date


def merge_dicts(dict_list):
    """Объединяет несколько словарей {date: [(filename, path), ...]} в один, суммируя списки."""
    merged = defaultdict(list)
    for d in dict_list:
        for date, files in d.items():
            merged[date].extend(files)
    return merged


def move_file(src_path, dest_dir, filename):
    """
    Перемещает файл из src_path в dest_dir с именем filename.
    Если файл с таким именем уже существует, добавляет суффикс _1, _2 и т.д.
    Возвращает новое имя файла (может быть изменено из-за конфликта).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    if dest_path.exists():
        base, ext = os.path.splitext(filename)
        counter = 1
        while dest_path.exists():
            new_filename = f"{base}_{counter}{ext}"
            dest_path = dest_dir / new_filename
            counter += 1
        logging.info(f"Файл {filename} уже существует, переименовываем в {dest_path.name}")
    try:
        shutil.move(str(src_path), str(dest_path))
        logging.debug(f"Перемещён {src_path} -> {dest_path}")
        return dest_path.name
    except Exception as e:
        logging.error(f"Ошибка при перемещении {src_path} в {dest_dir}: {e}")
        raise


def load_to_database(data, target_anime_dir, target_real_dir):
    """
    Загружает изображения в базу данных и перемещает файлы в целевые папки.
    data: словарь {'anime': dict, 'real': dict}, где каждый внутренний dict
          имеет вид {date: [(filename, src_path), ...]}
    """
    for category in data:
        pic_type = database.ImageType.ANIME.value if category == 'anime' else database.ImageType.REAL.value
        target_dir = target_anime_dir if category == 'anime' else target_real_dir
        logging.info(f"Загрузка типа: {category}")
        for date in data[category]:
            logging.info(f"  Дата: {date}")
            post_id = database.add_post_record(pic_type, date)
            if not post_id:
                logging.error(f"Не удалось создать запись поста для даты {date}, пропускаем.")
                continue
            for filename, src_path in data[category][date]:
                logging.debug(f"    Картинка: {filename}")
                # Сначала добавляем запись в БД, получаем ID картинки
                picture_id = database.add_picture_record(pic_type, post_id, filename)
                if not picture_id:
                    logging.error(f"Не удалось добавить картинку {filename} в БД, пропускаем.")
                    continue
                # Затем перемещаем файл
                try:
                    new_filename = move_file(src_path, target_dir, filename)
                    # Если имя файла изменилось, обновляем запись в БД
                    if new_filename != filename:
                        if database.update_picture_path(picture_id, new_filename):
                            logging.info(f"Обновлён путь картинки {picture_id} на {new_filename}")
                        else:
                            logging.error(f"Не удалось обновить путь картинки {picture_id}")
                except Exception as e:
                    logging.error(f"Ошибка при перемещении файла {filename}: {e}")
                    # Откатываем добавление в БД? Можно удалить запись, но оставим для ручного исправления.
                    # Удаляем запись из БД, чтобы не было несоответствия.
                    database.delete_image(picture_id)
                    logging.warning(f"Удалена запись картинки {picture_id} из-за ошибки перемещения.")


def main():
    parser = argparse.ArgumentParser(description='Сбор изображений из папок с группировкой по дате.')
    parser.add_argument('--anime', action='append', help='Папка с аниме (можно несколько)')
    parser.add_argument('--real', action='append', help='Папка с реальными фото (можно несколько)')
    parser.add_argument('--output', '-o', required=True, help='Файл для сохранения JSON')
    args = parser.parse_args()

    # Если папки не указаны, используем стандартные
    anime_folders = args.anime or [NEW_ANIME_DIR]
    real_folders = args.real or [NEW_REAL_DIR]

    # Проверка существования папок
    for folder in anime_folders + real_folders:
        if not Path(folder).exists():
            logging.warning(f"Папка {folder} не существует, будет создана при необходимости.")

    # Сбор и объединение данных по типам
    anime_merged = merge_dicts([collect_images_from_folder(f) for f in anime_folders])
    real_merged = merge_dicts([collect_images_from_folder(f) for f in real_folders])

    result = {
        'anime': dict(anime_merged),
        'real': dict(real_merged)
    }

    # Загрузка в БД и перемещение файлов
    load_to_database(result, TARGET_ANIME_DIR, TARGET_REAL_DIR)

    # Статистика
    total_anime = sum(len(v) for v in result['anime'].values())
    total_real = sum(len(v) for v in result['real'].values())
    logging.info(f"Собрано аниме: {total_anime} файлов, реальных: {total_real} файлов")

    # Сохранение в JSON
    import json
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump({k: {date: [fn for fn, _ in files] for date, files in v.items()} for k, v in result.items()},
                  f, ensure_ascii=False, indent=2)
    logging.info(f"Результат сохранён в {args.output}")


if __name__ == '__main__':
    main()