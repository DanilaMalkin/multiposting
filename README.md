# Мультипостинг RU⇄EN 

**Локальное Streamlit-приложение** для профессиональной замены аудиодорожки в видео (≤ 30 сек) с переводом речи на русский или английский, используя Yandex SpeechKit и Yandex GPT.

## 🔑 Ключевые особенности

* **Два направления перевода**: Русский → Английский и Английский → Русский
* **STT** (raw PCM 16 kHz, mono) для обоих языков
* **Перевод** через Yandex GPT с системными подсказками
* **TTS** (OggOpus → WAV → AAC) с голосами Alena и John
* **Без обрезки видео**: `-c:v copy`, сохранение оригинального видеопотока
* **Ограничение** длительности видео: 30 сек (превышающие файлы отклоняются)

## 📋 Требования

* Python ≥ 3.8
* FFmpeg ≥ 4.x
* Доступ к Yandex Cloud (Api-Key + Folder ID)

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo_url> && cd <repo_folder>

# 2. Создать и активировать виртуальную среду
python3 -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# 3. Установить зависимости
pip install --upgrade pip streamlit requests

# 4. Установить FFmpeg
# macOS: brew install ffmpeg
# Windows: choco install ffmpeg
# Linux: sudo apt install ffmpeg

# 5. Экспортировать ключи
export YC_API_KEY="<Ваш_API_Key>"
export YC_FOLDER_ID="<Ваш_Folder_ID>"

# 6. Запустить приложение
streamlit run main.py
```

Откройте URL `http://localhost:8501` в браузере, загрузите видео и следуйте инструкциям интерфейса.

## 🛠️ Конфигурация

* **Yandex API Key** и **Folder ID** указываются в сайдбаре.
* **Исходный язык** и **скорость озвучки** настраиваются слайдерами и селектами.
