import os
import sys
import shutil
from PIL import Image
import clip
import torch
from tqdm import tqdm

# ===================== НАСТРОЙКИ =====================
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
# Множественные промпты для аниме
ANIME_PROMPTS = [
    "anime artwork",
    "anime style",
    "manga drawing",
    "cel shaded illustration",
    "Japanese animation style",
    "anime character",
    "colorful anime scene",
    "anime girl",
    "anime boy"
]
# Множественные промпты для реальных фото
REAL_PROMPTS = [
    "realistic photograph",
    "real life photo",
    "natural image",
    "photorealistic",
    "camera photo",
    "real world scene",
    "high resolution photo",
    "photograph of a person",
    "landscape photography"
]
# Порог уверенности для аниме (повышен до 0.8)
ANIME_CONFIDENCE_THRESHOLD = 0.8
# Порог для реальных фото (оставим 0.5, но можно тоже поднять)
REAL_CONFIDENCE_THRESHOLD = 0.5
# =====================================================

def load_clip_model():
    print("[INFO] Загружаем модель CLIP...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    print(f"[OK] Модель загружена на устройство: {device}")
    return model, preprocess, device

def classify_image_clip(image_path, model, preprocess, device):
    try:
        image = Image.open(image_path).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)

        anime_texts = clip.tokenize(ANIME_PROMPTS).to(device)
        real_texts = clip.tokenize(REAL_PROMPTS).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            anime_features = model.encode_text(anime_texts)
            anime_features /= anime_features.norm(dim=-1, keepdim=True)
            real_features = model.encode_text(real_texts)
            real_features /= real_features.norm(dim=-1, keepdim=True)

            anime_sim = (100.0 * image_features @ anime_features.T).mean(dim=-1)
            real_sim = (100.0 * image_features @ real_features.T).mean(dim=-1)

            logits = torch.stack([anime_sim, real_sim], dim=-1)
            probs = logits.softmax(dim=-1).squeeze().cpu().numpy()

        anime_prob = probs[0]
        real_prob = probs[1]

        # Строгая логика: аниме только если уверенность высокая
        if anime_prob >= ANIME_CONFIDENCE_THRESHOLD:
            return "anime", anime_prob
        else:
            # Всё остальное (включая случаи, где real_prob выше или оба низкие) отправляем в real
            return "real", real_prob

    except Exception as e:
        return None, None

def process_folder(input_folder, output_folder=None):
    if not os.path.isdir(input_folder):
        print(f"[ОШИБКА] Папка {input_folder} не найдена")
        return

    if output_folder is None:
        output_folder = os.path.join(input_folder, "sorted_clip_strict")

    anime_dir = os.path.join(output_folder, "anime")
    real_dir = os.path.join(output_folder, "real")
    os.makedirs(anime_dir, exist_ok=True)
    os.makedirs(real_dir, exist_ok=True)

    model, preprocess, device = load_clip_model()

    all_files = []
    thumb_count = 0
    for filename in os.listdir(input_folder):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath):
            continue
        if "thumb" in filename.lower():
            thumb_count += 1
            continue
        if os.path.splitext(filename)[1].lower() not in IMAGE_EXTENSIONS:
            continue
        all_files.append((filename, filepath))

    total = len(all_files)
    if total == 0:
        print("[INFO] Нет изображений для обработки.")
        return

    anime_count = 0
    real_count = 0
    errors = 0

    print(f"\n[INFO] Начинаем обработку {total} изображений...\n")

    for filename, filepath in tqdm(all_files, desc="Сортировка", unit="img", smoothing=0.1):
        label, conf = classify_image_clip(filepath, model, preprocess, device)
        if label is None:
            errors += 1
            continue

        if label == "anime":
            dest_dir = anime_dir
            anime_count += 1
        else:
            dest_dir = real_dir
            real_count += 1

        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(dest_dir, f"{base}_{counter}{ext}")):
                counter += 1
            dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")

        shutil.copy2(filepath, dest_path)

    print("\n" + "="*50)
    print("ГОТОВО!")
    print(f"Всего обработано: {total}")
    print(f"Аниме (уверенно): {anime_count}")
    print(f"Реальные фото: {real_count}")
    print(f"Пропущено (thumb): {thumb_count}")
    print(f"Ошибок при классификации: {errors}")
    print(f"Результаты в: {output_folder}")
    print("="*50)

def main():
    if len(sys.argv) < 2:
        print("Использование: python sort_clip.py <входная_папка> [выходная_папка]")
        print("Пример: python sort_clip.py C:\images C:\sorted")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) == 3 else None
    process_folder(input_folder, output_folder)

if __name__ == "__main__":
    main()