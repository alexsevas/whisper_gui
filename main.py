# conda allpy310

import os
import subprocess
import torch
import whisper
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread


def extract_audio(video_path, audio_path):
    command = [
        'ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка при извлечении аудио: {result.stderr.decode()}")

def transcribe_audio(audio_path, model_name="medium"):  # Можно выбрать 'base', 'small', 'medium', 'large', 'large-v3'
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(audio_path, language='ru')
    return result["text"]

def process_video(video_path, status_label, root):
    try:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = base_name + "_audio.wav"
        text_path = base_name + "_transcript.txt"
        status_label.config(text="Извлечение аудио...")
        extract_audio(video_path, audio_path)
        status_label.config(text="Расшифровка аудио...")
        text = transcribe_audio(audio_path)
        if not isinstance(text, str):
            text = str(text)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        status_label.config(text=f"Готово! Сохранено: {text_path}")
        messagebox.showinfo("Успех", f"Расшифровка завершена. Результат сохранён в: {text_path}")
    except Exception as e:
        status_label.config(text="Ошибка!")
        messagebox.showerror("Ошибка", str(e))
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        root.after(100, lambda: select_button.config(state=tk.NORMAL))

def select_file():
    file_path = filedialog.askopenfilename(
        title="Выберите видеофайл",
        filetypes=[("Видео файлы", "*.mp4;*.avi;*.mov;*.mkv;*.webm"), ("Все файлы", "*.*")]
    )
    if file_path:
        select_button.config(state=tk.DISABLED)
        status_label.config(text="Обработка...")
        Thread(target=process_video, args=(file_path, status_label, root), daemon=True).start()

root = tk.Tk()
root.title("WhisperAPP")
root.geometry("640x360")

frame = tk.Frame(root)
frame.pack(expand=True)

select_button = tk.Button(frame, text="Выбрать видеофайл", command=select_file, width=25)
select_button.pack(pady=20)

status_label = tk.Label(frame, text="Ожидание выбора файла.")
status_label.pack(pady=10)

root.mainloop()