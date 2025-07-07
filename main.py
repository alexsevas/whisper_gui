# conda allpy310

import os
import subprocess
import torch
import whisper
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
import time
from datetime import datetime

# class ProgressHandler:
#     def __init__(self, progress_bar, root):
#         self.progress_bar = progress_bar
#         self.root = root

#     def __call__(self, progress):
#         # Прогресс от whisper обычно от 0 до 1, преобразуем в 0-100
#         # self.progress_bar['value'] = progress * 100 # Этот параметр не используется в indeterminate режиме
#         self.root.update_idletasks() # Обновляем GUI

WHISPER_MODELS = [
    'tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3', 'turbo'
]
LANGUAGES = [
    ('Русский', 'ru'),
    ('Язык оригинала', None)
]
OUTPUT_FORMATS = [
    ('TXT файл', 'txt'),
    ('SRT файл (субтитры)', 'srt')
]


# --- Функция для добавления сообщения в консоль ---
def log_console(console_widget, message):
    now = datetime.now().strftime('%H:%M:%S')
    console_widget.config(state=tk.NORMAL)
    console_widget.insert(tk.END, f"{now} - {message}\n")
    console_widget.see(tk.END)
    console_widget.config(state=tk.DISABLED)


# --- Получение разрешения экрана и расчет размеров окна ---
def get_window_size():
    root = tk.Tk()
    root.withdraw()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    min_side = min(screen_width, screen_height)
    win_width = int(min_side * 0.5)
    win_height = int(screen_height * 0.8)
    root.destroy()
    return win_width, win_height, screen_width, screen_height


win_width, win_height, screen_width, screen_height = get_window_size()


# --- Основные функции ---
def extract_audio(video_path, audio_path):
    command = [
        'ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка при извлечении аудио: {result.stderr.decode()}")


def transcribe_audio(audio_path, model_name, device, language_code):
    model = whisper.load_model(model_name, device=device)
    kwargs = {}
    if language_code:
        kwargs['language'] = language_code
    result = model.transcribe(audio_path, **kwargs)
    return result


def is_audio_file(filepath):
    audio_exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus', '.webm', '.mpga', '.aac', '.wma')
    return filepath.lower().endswith(audio_exts)


def format_timedelta(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes:02d} мин {remaining_seconds:02d} сек"


def to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds * 1000) % 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"


def process_video_or_audio(file_path, model_name, device, language_code, output_format_ext, status_label, result_text,
                           root, select_button, info_console, progress_bar):
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        dir_name = os.path.dirname(file_path)
        output_filename = f"{base_name}_transcript.{output_format_ext}"
        output_path = os.path.join(dir_name, output_filename)

        root.title(f"Распознаем: {os.path.basename(file_path)}")
        log_console(info_console, "Подготовка файла...")
        start_time = time.time()

        audio_path_to_delete = None
        if is_audio_file(file_path):
            audio_path = file_path
        else:
            audio_path = os.path.join(dir_name, base_name + "_audio.wav")
            audio_path_to_delete = audio_path  # Mark for deletion only if extracted
            status_label.config(text="Извлечение аудио...")
            log_console(info_console, "Извлечение аудиодорожки из видео...")
            extract_audio(file_path, audio_path)

        status_label.config(text="Расшифровка аудио...")
        log_console(info_console, "Распознавание речи...")

        # progress_bar['value'] = 0 # Сбрасываем прогресс-бар
        progress_bar.pack(fill=tk.X, padx=2, pady=2)  # Делаем прогресс-бар видимым
        progress_bar.start()  # Запускаем неопределенный прогресс-бар

        # progress_handler = ProgressHandler(progress_bar, root)
        transcribe_result = transcribe_audio(audio_path, model_name, device, language_code)

        # Output to GUI Text field
        text_to_display = transcribe_result["text"]
        if not isinstance(text_to_display, str):
            text_to_display = str(text_to_display)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, text_to_display)

        # Save to file
        if output_format_ext == 'txt':
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_to_display)
        elif output_format_ext == 'srt':
            srt_content = []
            for i, segment in enumerate(transcribe_result["segments"], start=1):
                start_srt = to_srt_time(segment['start'])
                end_srt = to_srt_time(segment['end'])
                srt_content.append(f"{i}\n{start_srt} --> {end_srt}\n{segment['text'].strip()}\n\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.writelines(srt_content)

        status_label.config(text="Готово!")
        elapsed = time.time() - start_time
        log_console(info_console, f"Время распознавания текущего файла - {format_timedelta(elapsed)}")
        log_console(info_console, f"Результат сохранён в: {os.path.basename(output_path)}")

    except Exception as e:
        status_label.config(text="Ошибка!")
        log_console(info_console, str(e))
        messagebox.showerror("Ошибка", str(e))
    finally:
        if audio_path_to_delete and os.path.exists(audio_path_to_delete):
            os.remove(audio_path_to_delete)
        root.title("Преобразовать видео/аудио --> текст")
        progress_bar.pack_forget()  # Скрываем прогресс-бар
        progress_bar.stop()  # Останавливаем прогресс-бар
        root.after(100, lambda: select_button.config(state=tk.NORMAL))


def select_file(model_var, device_var, lang_var, output_format_var, status_label, result_text, root, select_button,
                info_console, progress_bar):
    filetypes = [
        (
        "Видео/Аудио файлы", "*.mp4;*.avi;*.mov;*.mkv;*.webm;*.mp3;*.wav;*.m4a;*.flac;*.ogg;*.opus;*.mpga;*.aac;*.wma"),
        ("Видео файлы", "*.mp4;*.avi;*.mov;*.mkv;*.webm"),
        ("Аудио файлы", "*.mp3;*.wav;*.m4a;*.flac;*.ogg;*.opus;*.webm;*.mpga;*.aac;*.wma"),
        ("Все файлы", "*.*")
    ]
    file_path = filedialog.askopenfilename(
        title="Выберите видео или аудиофайл",
        filetypes=filetypes
    )
    if file_path:
        select_button.config(state=tk.DISABLED)
        status_label.config(text="Обработка...")
        log_console(info_console, "Файл выбран: " + os.path.basename(file_path))
        model_name = model_var.get()
        device = 'cuda' if device_var.get() == 'CUDA' else 'cpu'
        # Получаем выбранный язык из StringVar и ищем соответствующий код
        selected_lang_name = lang_var.get()
        language_code = next((code for name, code in LANGUAGES if name == selected_lang_name), None)

        # Получаем выбранный формат из StringVar и ищем соответствующее расширение
        selected_output_format_name = output_format_var.get()
        output_format_ext = next((ext for name, ext in OUTPUT_FORMATS if name == selected_output_format_name), None)

        Thread(target=process_video_or_audio, args=(
        file_path, model_name, device, language_code, output_format_ext, status_label, result_text, root, select_button,
        info_console, progress_bar), daemon=True).start()


# --- Интерфейс ---
root = tk.Tk()
root.title("Преобразовать видео/аудио --> текст")
root.geometry(f"{win_width}x{win_height}+{(screen_width - win_width) // 2}+{(screen_height - win_height) // 2}")

# --- Темы оформления (принудительно темная) ---
THEME_DARK = {
    'bg': '#23272e', 'fg': '#e0e0e0', 'entry_bg': '#2d323b', 'entry_fg': '#e0e0e0', 'button_bg': '#444b57',
    'button_fg': '#e0e0e0', 'text_bg': '#23272e', 'text_fg': '#e0e0e0', 'select_bg': '#3a4a5a', 'select_fg': '#fff',
    'status_fg': '#b0b0b0',
    'console_bg': '#101010', 'console_fg': '#00ff00',
    'scrollbar_bg': '#444b57', 'scrollbar_trough': '#2d323b', 'scrollbar_active': '#3a4a5a',
    'combobox_arrow': '#e0e0e0'  # Цвет стрелки комбобокса
}


def apply_dark_theme():
    theme = THEME_DARK
    root.configure(bg=theme['bg'])
    control_frame.configure(bg=theme['bg'])

    # Настройка стилей ttk виджетов
    style = ttk.Style()
    style.theme_use('clam')  # Выбираем тему, которую можно настроить

    style.configure('TCombobox',
                    fieldbackground=theme['entry_bg'],
                    background=theme['entry_bg'],
                    foreground=theme['entry_fg'],
                    arrowcolor=theme['combobox_arrow'],
                    bordercolor=theme['entry_bg']
                    )
    style.map('TCombobox',
              fieldbackground=[('readonly', theme['entry_bg'])],
              background=[('readonly', theme['entry_bg'])],
              foreground=[('readonly', theme['entry_fg'])],
              selectbackground=[('readonly', theme['select_bg'])],
              selectforeground=[('readonly', theme['select_fg'])]
              )

    style.configure('Vertical.TScrollbar',
                    background=theme['scrollbar_bg'],
                    troughcolor=theme['scrollbar_trough'],
                    gripcolor=theme['select_bg'],
                    bordercolor=theme['scrollbar_bg']
                    )
    style.map('Vertical.TScrollbar',
              background=[('active', theme['scrollbar_active'])]
              )

    # Применение цветов к стандартным Tk виджетам
    model_label.configure(bg=theme['bg'], fg=theme['fg'])
    device_label.configure(bg=theme['bg'], fg=theme['fg'])
    lang_label.configure(bg=theme['bg'], fg=theme['fg'])
    output_format_label.configure(bg=theme['bg'], fg=theme['fg'])
    select_button.configure(bg=theme['button_bg'], fg=theme['button_fg'], activebackground=theme['select_bg'],
                            activeforeground=theme['select_fg'])
    status_label.configure(bg=theme['bg'], fg=theme['status_fg'])
    result_label.configure(bg=theme['bg'], fg=theme['fg'])
    result_text.configure(bg=theme['text_bg'], fg=theme['text_fg'], insertbackground=theme['fg'])
    info_console.configure(bg=theme['console_bg'], fg=theme['console_fg'])
    style.configure('TProgressbar',
                    background=theme['select_bg'],  # Цвет заполнения прогресс-бара
                    troughcolor=theme['entry_bg'],  # Цвет фона прогресс-бара
                    bordercolor=theme['entry_bg']
                    )


# Компактный блок управления (до 40% высоты окна)
max_control_height = int(win_height * 0.4)
control_frame = tk.Frame(root)
control_frame.pack(side=tk.TOP, fill=tk.X, pady=int(win_width * 0.01))

# Плотная вертикальная группировка
# for widget in control_frame.winfo_children(): # Удалено: pack_forget() не нужен при первом pack
#     widget.pack_forget()

row_pad = 2
# Модель Whisper
model_label = tk.Label(control_frame, text="Модель Whisper:")
model_label.pack(anchor='w', padx=8, pady=(row_pad, 0))
model_var = tk.StringVar(value='large-v3')
model_combo = ttk.Combobox(control_frame, textvariable=model_var, values=WHISPER_MODELS, state="readonly", width=22)
model_combo.pack(fill=tk.X, padx=8, pady=(0, row_pad))

# Устройство
device_label = tk.Label(control_frame, text="Устройство:")
device_label.pack(anchor='w', padx=8, pady=(row_pad, 0))
device_var = tk.StringVar(value='CUDA' if torch.cuda.is_available() else 'CPU')
device_combo = ttk.Combobox(control_frame, textvariable=device_var, values=['CUDA', 'CPU'], state="readonly", width=22)
device_combo.pack(fill=tk.X, padx=8, pady=(0, row_pad))

# Язык
lang_label = tk.Label(control_frame, text="Язык распознавания:")
lang_label.pack(anchor='w', padx=8, pady=(row_pad, 0))
lang_var = ttk.Combobox(control_frame, values=[l[0] for l in LANGUAGES], state="readonly", width=22)
lang_var.current(0)
lang_var.pack(fill=tk.X, padx=8, pady=(0, row_pad))

# Формат вывода
output_format_label = tk.Label(control_frame, text="Формат выходного файла:")
output_format_label.pack(anchor='w', padx=8, pady=(row_pad, 0))
output_format_var = tk.StringVar(value='TXT файл')
output_format_combo = ttk.Combobox(control_frame, textvariable=output_format_var, values=[f[0] for f in OUTPUT_FORMATS],
                                   state="readonly", width=22)
output_format_combo.current(0)
output_format_combo.pack(fill=tk.X, padx=8, pady=(0, row_pad))

# Кнопка выбора файла
select_button = tk.Button(control_frame, text="Выбрать видео/аудио файл",
                          command=lambda: select_file(model_var, device_var, lang_var, output_format_var, status_label,
                                                      result_text, root, select_button, info_console, progress_bar),
                          width=25)  # Передача аргументов
select_button.pack(padx=8, pady=(row_pad + 5, row_pad), fill=tk.X)

# Статус
status_label = tk.Label(control_frame, text="Ожидание выбора файла.")
status_label.pack(padx=8, pady=(row_pad, row_pad), fill=tk.X)

# Ограничение высоты блока управления
control_frame.update_idletasks()
if control_frame.winfo_height() > max_control_height:
    control_frame.config(height=max_control_height)
    control_frame.pack_propagate(False)

# Поле для вывода результата с полосой прокрутки
result_label = tk.Label(root, text="Результат распознавания:")
result_label.pack(pady=(10, 0))

text_height = max(8, int((win_height - max_control_height - 50 - 60) // 20))  # -60 for console height
text_width = max(40, int(win_width // 8))

result_frame = tk.Frame(root)
result_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

scrollbar_result = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)  # Изменено на ttk.Scrollbar
result_text = tk.Text(result_frame, wrap=tk.WORD, height=text_height, width=text_width,
                      yscrollcommand=scrollbar_result.set)
scrollbar_result.config(command=result_text.yview)
scrollbar_result.pack(side=tk.RIGHT, fill=tk.Y)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Прокрутка колесом мыши для поля результата
result_text.bind('<Enter>', lambda e: result_text.bind_all('<MouseWheel>', lambda ev: result_text.yview_scroll(
    int(-1 * (ev.delta / 120)), 'units')))
result_text.bind('<Leave>', lambda e: result_text.unbind_all('<MouseWheel>'))

# --- Информационная консоль (4 строки, темный фон, зеленый текст) ---
console_frame = tk.Frame(root)
console_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 4))

progress_bar = ttk.Progressbar(console_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
progress_bar.pack_forget()  # Изначально скрываем прогресс-бар

scrollbar_console = ttk.Scrollbar(console_frame, orient=tk.VERTICAL)  # Добавлена полоса прокрутки
info_console = tk.Text(console_frame, height=4, bg=THEME_DARK['console_bg'], fg=THEME_DARK['console_fg'],
                       state=tk.DISABLED, font=("Consolas", 10), wrap=tk.WORD,
                       borderwidth=0, highlightthickness=0, yscrollcommand=scrollbar_console.set)
scrollbar_console.config(command=info_console.yview)

scrollbar_console.pack(side=tk.RIGHT, fill=tk.Y)
info_console.pack(fill=tk.BOTH, expand=True)

# Применить темную тему по умолчанию
apply_dark_theme()

root.mainloop()