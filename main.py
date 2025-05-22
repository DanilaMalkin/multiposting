"""
RU⇄EN Video Audio Replacer PRO
--------------------------------
Локальное Streamlit-приложение, которое:
- переводит закадровую речь Рус⇄Англ,
- генерирует новую озвучку Yandex TTS,
- заменяет аудиодорожку в исходном видео (≤30с),
- сохраняет видеопоток без изменений.
"""

import subprocess, tempfile, shutil, time, uuid
from pathlib import Path
from typing import Dict
import streamlit as st
import requests

# ============ Константы ============
LANGS: Dict[str, str] = {"ru-RU": "Русский", "en-US": "English"}
VOICES: Dict[str, str] = {"ru-RU": "alena", "en-US": "john"}
MAX_DURATION = 30.0
RETRIES = 3

# ============ Функции ============

def get_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ])
    return float(out)

def stt(api_key: str, folder: str, pcm_bytes: bytes, lang: str) -> str:
    """STT через raw PCM (lpcm)."""
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {"Authorization": f"Api-Key {api_key}"}
    params = {
        "folderId": folder,
        "lang": lang,
        "format": "lpcm",
        "sampleRateHertz": 16000
    }
    for i in range(RETRIES):
        try:
            resp = requests.post(
                url, headers=headers, params=params,
                data=pcm_bytes, timeout=30
            )
            resp.raise_for_status()
            return resp.json().get("result", "")
        except Exception as e:
            if i < RETRIES - 1:
                time.sleep(1)
            else:
                st.error(f"STT failed: {e}")
                raise

def translate(api_key: str, folder: str, text: str, target: str) -> str:
    """Перевод текста через Yandex GPT на целевой язык."""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    system = f"Переведи текст на {LANGS[target]}, сохрани смысл и естественность."
    payload = {
        "modelUri": f"gpt://{folder}/yandexgpt",
        "messages": [
            {"role": "system", "text": system},
            {"role": "user", "text": text}
        ],
        "completionOptions": {"temperature": 0.2, "maxTokens": 2048}
    }
    headers = {"Authorization": f"Api-Key {api_key}"}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        resp.raise_for_status()
    except Exception:
        st.error(f"Translation API error {resp.status_code}: {resp.text}")
        raise
    return resp.json()["result"]["alternatives"][0]["message"]["text"].strip()

def tts(api_key: str, folder: str, text: str, lang: str, speed: float) -> bytes:
    """Генерация речи OggOpus через Yandex TTS."""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    data = {
        "text": text, "lang": lang,
        "voice": VOICES[lang], "speed": speed,
        "format": "oggopus", "folderId": folder
    }
    headers = {"Authorization": f"Api-Key {api_key}"}
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.content

def replace_audio(video_path: Path, audio_path: Path, output_path: Path):
    """Меняет дорожку аудио, копируя видеопоток."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)

# ============ Интерфейс Streamlit ============

st.set_page_config(page_title="RU⇄EN ", layout="wide")
st.title("🌐 Мультипостинг видео")

api_key = st.sidebar.text_input("Yandex API Key", type="password").strip()
folder_id = st.sidebar.text_input("Folder ID").strip()
src_lang = st.sidebar.selectbox("Исходный язык", list(LANGS.keys()), format_func=lambda x: LANGS[x])
trg_lang = "en-US" if src_lang == "ru-RU" else "ru-RU"
st.sidebar.markdown(f"**Целевой язык:** {LANGS[trg_lang]}")
speed = st.sidebar.slider("Скорость речи", 0.8, 1.3, 1.0, 0.05)

videos = st.file_uploader("Загрузите MP4/MOV (≤30 сек)", type=["mp4","mov"], accept_multiple_files=True)
if st.button("Запустить обработку"):
    if not api_key or not folder_id or not videos:
        st.error("Укажите API Key, Folder ID и загрузите видео.")
        st.stop()

    for vid_file in videos:
        # подготовка
        tmpdir = Path(tempfile.mkdtemp(prefix="vtr_"))
        in_path = tmpdir / "in.mp4"
        in_path.write_bytes(vid_file.getbuffer())

        # проверяем длительность
        dur = get_duration(in_path)
        if dur > MAX_DURATION:
            st.error(f"{vid_file.name}: длительность {dur:.1f} с > {MAX_DURATION} с, пропуск.")
            shutil.rmtree(tmpdir)
            continue

        # извлекаем raw PCM для STT
        pcm_path = tmpdir / "in.pcm"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(in_path),
            "-ac", "1", "-ar", "16000", "-f", "s16le", str(pcm_path)
        ], check=True)
        pcm_bytes = pcm_path.read_bytes()

        # распознаём, переводим и синтезируем
        text_ru = stt(api_key, folder_id, pcm_bytes, src_lang)
        st.text_area("Распознанный текст", text_ru, height=120)
        if not text_ru.strip():
            st.warning("Пустой результат STT, пропуск ролика.")
            shutil.rmtree(tmpdir)
            continue

        text_tr = translate(api_key, folder_id, text_ru, trg_lang)
        audio_ogg = tts(api_key, folder_id, text_tr, trg_lang, speed)

        # конверт в WAV для мультиплексирования
        wav_path = tmpdir / "out.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", "pipe:0",
            "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
            str(wav_path)
        ], input=audio_ogg, check=True)

        # заменяем аудио
        out_path = tmpdir / f"out_{LANGS[trg_lang]}.mp4"
        replace_audio(in_path, wav_path, out_path)

        # показываем и предлагаем скачать
        st.success(f"Готово: {vid_file.name}")
        st.video(str(out_path))
        st.download_button("Скачать видео", out_path.read_bytes(), file_name=out_path.name)

        # очистка
        shutil.rmtree(tmpdir)