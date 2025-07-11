# conda allpy310
'''
-0 - Для отображения точного процента вам потребуется версия Whisper, которая поддерживает progress_callback
+1 - инфо при загрузке о доступных моделях весов виспера с указанием их размещения;
+2 - добавить возможность указания папки с весами;
+3 - если веса отсутствуют - загрузка их с уведомлением об этом в консоли (указание скорости загрузки, объем весов и оставшееся время загрузки)
+4 - добавить меню в приложении - а там добавить пункт с информацией о разработчике
5 - компилирование проекта в exe и инсталлятор (с весами, или без)
6 - переписать весь интерфейс на flux или что-то, что выглядит в духе вин10 и вин11
7 - в меню - инфо пункт про использование в вариантах CUDA и CPU (какие требования, что установить, какое железо, сколько
видеопамяти (Dzen Download)), где обычно хранятся веса, какие особенности и нагрузки на систему
+8 - переделать под внутренний ffmpeg (через pip install ffmpeg-python)
-9 - добавить возможность ставить на паузу при обработке большого объема файлов и сохранение текущего прогресса, чтобы при возобновлении
процесс начинался с того файла, на котором закончился, а также защиты от повторной обработки тех файлов, что уже обработаны.
-10 - интерфейс: информационные сообщения при задержке курсора над элементами интерфейса с подсказкой что-почему-итд
'''

import os
import torch
import whisper
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
import time
from datetime import datetime
from typing import Dict, Any
import ffmpeg as ffmpeg_module

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

# --- Темы оформления (принудительно темная) ---
THEME_DARK = {
    'bg': '#23272e', 'fg': '#e0e0e0', 'entry_bg': '#2d323b', 'entry_fg': '#e0e0e0', 'button_bg': '#444b57',
    'button_fg': '#e0e0e0', 'text_bg': '#23272e', 'text_fg': '#e0e0e0', 'select_bg': '#3a4a5a', 'select_fg': '#fff',
    'status_fg': '#b0b0b0',
    'console_bg': '#101010', 'console_fg': '#00ff00',
    'console_success_fg': '#00ff00',  # Зеленый для успешных сообщений
    'console_error_fg': '#ff0000',  # Красный для ошибок
    'console_highlight_fg': '#00FFFF',  # Голубой для выделения
    'scrollbar_bg': '#444b57', 'scrollbar_trough': '#2d323b', 'scrollbar_active': '#3a4a5a',
    'combobox_arrow': '#e0e0e0',  # Цвет стрелки комбобокса
    'menu_bg': '#2d323b',
    'menu_fg': '#e0e0e0',
    'menu_active_bg': '#3a4a5a',
    'menu_active_fg': '#fff',
    'menu_border': '#2d323b',
    'menu_disabled_fg': '#777777'
}


def apply_dark_theme(root_widget, control_widgets, result_widgets, console_widgets, menu_widgets):
    theme = THEME_DARK
    root_widget.configure(bg=theme['bg'])

    style = ttk.Style()
    style.theme_use('clam')

    # TCombobox
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

    # Vertical.TScrollbar
    style.configure('Vertical.TScrollbar',
                    background=theme['scrollbar_bg'],
                    troughcolor=theme['scrollbar_trough'],
                    gripcolor=theme['select_bg'],
                    bordercolor=theme['scrollbar_bg']
                    )
    style.map('Vertical.TScrollbar',
              background=[('active', theme['scrollbar_active'])]
              )

    # TButton
    style.configure('TButton',
                    background=theme['button_bg'],
                    foreground=theme['button_fg'],
                    bordercolor=theme['button_bg']
                    )
    style.map('TButton',
              background=[('active', theme['select_bg'])],
              foreground=[('active', theme['select_fg'])])

    # TCheckbutton
    style.configure('TCheckbutton',
                    background=theme['bg'],
                    foreground=theme['fg'],
                    indicatorcolor=theme['entry_bg'],
                    selectcolor=theme['select_bg']
                    )
    style.map('TCheckbutton',
              background=[('active', theme['bg'])],
              foreground=[('active', theme['fg'])])

    # TProgressbar
    style.configure('TProgressbar',
                    background=theme['select_bg'],
                    troughcolor=theme['entry_bg'],
                    bordercolor=theme['entry_bg']
                    )

    # Применение цветов к стандартным Tk виджетам (передаем словари виджетов)
    for widget in control_widgets.values():
        if isinstance(widget, tk.Label):
            widget.configure(bg=theme['bg'], fg=theme['fg'])
        elif isinstance(widget, tk.Button):
            widget.configure(bg=theme['button_bg'], fg=theme['button_fg'], activebackground=theme['select_bg'],
                             activeforeground=theme['select_fg'])

    for widget in result_widgets.values():
        if isinstance(widget, tk.Label):
            widget.configure(bg=theme['bg'], fg=theme['fg'])
        elif isinstance(widget, tk.Text):
            widget.configure(bg=theme['text_bg'], fg=theme['text_fg'], insertbackground=theme['fg'])

    for widget in console_widgets.values():
        if isinstance(widget, tk.Text):
            widget.configure(bg=theme['console_bg'], fg=theme['console_fg'])

    # Apply colors to Tk Frames
    left_column_frame.configure(bg=theme['bg'])
    control_frame.configure(bg=theme['bg'])
    console_frame.configure(bg=theme['bg'])
    result_container_frame.configure(bg=theme['bg'])
    result_frame.configure(bg=theme['bg'])

    # Apply colors to Tk Menus
    menu_widgets['menubar'].configure(bg=theme['menu_bg'], fg=theme['menu_fg'],
                                      activebackground=theme['menu_active_bg'],
                                      activeforeground=theme['menu_active_fg'], borderwidth=0)
    for menu in [menu_widgets['read_menu'], menu_widgets['about_menu']]:
        menu.configure(bg=theme['menu_bg'], fg=theme['menu_fg'], activebackground=theme['menu_active_bg'],
                       activeforeground=theme['menu_active_fg'], disabledforeground=theme['menu_disabled_fg'],
                       borderwidth=0)

    # Проверка наличия моделей при запуске (теперь вызывается после создания info_console)


# --- Функция для добавления сообщения в консоль ---
def log_console(console_widget, segments):
    now = datetime.now().strftime('%H:%M:%S')
    console_widget.config(state=tk.NORMAL)

    # Add timestamp with info_tag
    console_widget.insert(tk.END, f"{now} - ", 'info_tag')

    for text, tag_name in segments:
        console_widget.insert(tk.END, text, tag_name)
    console_widget.insert(tk.END, "\n")  # Add newline at the end

    console_widget.see(tk.END)
    console_widget.config(state=tk.DISABLED)


# --- Получение разрешения экрана и расчет размеров окна ---
def get_window_size():
    root = tk.Tk()
    root.withdraw()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    win_width = int(screen_width * 0.8)
    win_height = int(screen_height * 0.6)
    root.destroy()
    return win_width, win_height, screen_width, screen_height


win_width, win_height, screen_width, screen_height = get_window_size()
win_width = 1200  # Устанавливаем фиксированную ширину окна


# --- Основные функции ---
def get_media_duration(file_path):
    try:
        info = ffmpeg_module.probe(file_path)
        duration = float(info['format']['duration'])
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception as e:
        return f"Ошибка при получении длительности: {e}"


def extract_audio(video_path, audio_path):
    try:
        (
            ffmpeg_module
            .input(video_path)
            .output(audio_path, vn=None, acodec='pcm_s16le', ar='16000', ac=1)
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка при извлечении аудио: {str(e)}")


def transcribe_audio(audio_path, model_name, device, language_code):
    model = whisper.load_model(model_name, device=device)
    kwargs = {}
    if language_code:
        kwargs['language'] = language_code
    result = model.transcribe(audio_path, **kwargs)
    return result


def is_media_file(filepath):
    media_exts = (
    '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus', '.webm', '.mpga', '.aac', '.wma', '.mp4', '.avi', '.mov', '.mkv')
    return filepath.lower().endswith(media_exts)


def _is_only_audio_file(filepath):
    audio_only_exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus', '.mpga', '.aac', '.wma')
    return filepath.lower().endswith(audio_only_exts)


# --- Проверка наличия модели в кэше Whisper ---
def check_model_in_cache(model_name):
    # Whisper по умолчанию сохраняет модели в ~/.cache/whisper/
    cache_dir = os.path.join(os.path.expanduser("~/"), ".cache", "whisper")
    model_path = os.path.join(cache_dir, f"{model_name}.pt")
    return os.path.exists(model_path)


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
                           root, select_button, info_console, progress_bar, show_result_var, batch_button,
                           select_weights_button):
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        dir_name = os.path.dirname(file_path)
        output_filename = f"{base_name}.{output_format_ext}"
        output_path = os.path.join(dir_name, output_filename)

        root.title(f"Распознаем: {os.path.basename(file_path)}")
        log_console(info_console, [("Подготовка файла...", 'info')])
        start_time = time.time()

        audio_path_to_delete = None
        if _is_only_audio_file(file_path):
            audio_path = file_path
        elif is_media_file(file_path):
            audio_path = os.path.join(dir_name, base_name + "_audio.wav")
            audio_path_to_delete = audio_path  # Mark for deletion only if extracted
            status_label.config(text="Извлечение аудио...")
            log_console(info_console, [("Извлечение аудиодорожки из видео...", 'info')])
            extract_audio(file_path, audio_path)
        else:
            # This case implies it's not a supported media file, which should ideally be caught earlier
            # For robustness, we'll raise an error here if an unsupported file type reaches this point
            raise ValueError(f"Неподдерживаемый тип файла: {file_path}")

        status_label.config(text="Расшифровка аудио...")
        log_console(info_console,
                    [("Модель ", 'info_tag'), (model_name, 'highlight_tag'), (": Запуск распознавания...", 'info_tag')])

        # progress_bar.pack(fill=tk.X, padx=2, pady=2) # Делаем прогресс-бар видимым
        progress_bar.grid()  # Размещаем в сетке консольного фрейма
        progress_bar.start()  # Запускаем неопределенный прогресс-бар

        transcribe_result: Dict[str, Any] = transcribe_audio(audio_path, model_name, device, language_code)

        # Output to GUI Text field
        text_to_display = transcribe_result["text"]
        if not isinstance(text_to_display, str):
            text_to_display = str(text_to_display)

        # Обновляем поле результата только если чекбокс активен
        if show_result_var.get():
            result_text.config(state=tk.NORMAL)  # Временно активируем для записи
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, text_to_display)

        # Save to file
        if output_format_ext == 'txt':
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_to_display)
        elif output_format_ext == 'srt':
            srt_content = []
            for i, segment in enumerate(transcribe_result["segments"]):
                start_srt = to_srt_time(segment['start'])
                end_srt = to_srt_time(segment['end'])
                srt_content.append(f"{i}\n{start_srt} --> {end_srt}\n{segment['text'].strip()}\n\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.writelines(srt_content)

        status_label.config(text="Готово!")
        elapsed = time.time() - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        log_console(info_console, [("Выполнено за ", 'success_tag'), (formatted_time, 'highlight_tag')])
        log_console(info_console,
                    [("Результат сохранён в: ", 'success_tag'), (os.path.basename(output_path), 'highlight_tag')])
        log_console(info_console, [("-" * 20, 'info_tag')])

    except Exception as e:
        status_label.config(text="Ошибка!")
        log_console(info_console, [("Ошибка: " + str(e), 'error')])
        messagebox.showerror("Ошибка", str(e))
    finally:
        if audio_path_to_delete and os.path.exists(audio_path_to_delete):
            os.remove(audio_path_to_delete)
        root.title("Преобразовать видео/аудио --> текст")
        progress_bar.grid_remove()  # Скрываем прогресс-бар
        progress_bar.stop()  # Останавливаем прогресс-бар

        # Устанавливаем конечное состояние result_text на основе чекбокса
        result_text.config(state=tk.DISABLED if not show_result_var.get() else tk.NORMAL)
        root.after(100, lambda: select_button.config(state=tk.NORMAL))
        root.after(100, lambda: batch_button.config(state=tk.NORMAL))
        root.after(100, lambda: select_weights_button.config(state=tk.NORMAL))


def select_file(model_var, device_var, lang_var, output_format_var, status_label, result_text, root, select_button,
                info_console, progress_bar, show_result_var, batch_button, select_weights_button):
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
        batch_button.config(state=tk.DISABLED)
        select_weights_button.config(state=tk.DISABLED)
        status_label.config(text="Обработка...")
        log_console(info_console, [("Файл ", 'info_tag'), (os.path.basename(file_path), 'highlight_tag')])
        duration = get_media_duration(file_path)
        log_console(info_console, [("Продолжительность файла: ", 'info_tag'), (duration, 'highlight_tag')])
        model_name = model_var.get()
        device = 'cuda' if device_var.get() == 'CUDA' else 'cpu'
        selected_lang_name = lang_var.get()
        language_code = next((code for name, code in LANGUAGES if name == selected_lang_name), None)

        selected_output_format_name = output_format_var.get()
        output_format_ext = next((ext for name, ext in OUTPUT_FORMATS if name == selected_output_format_name), None)

        Thread(target=process_video_or_audio, args=(
        file_path, model_name, device, language_code, output_format_ext, status_label, result_text, root, select_button,
        info_console, progress_bar, show_result_var, batch_button, select_weights_button), daemon=True).start()


def select_folder_for_batch_processing(model_var, device_var, lang_var, output_format_var, status_label, result_text,
                                       root, select_button, batch_button, info_console, progress_bar, show_result_var,
                                       select_weights_button):
    folder_path = filedialog.askdirectory(
        title="Выберите папку для пакетной обработки"
    )
    if folder_path:
        select_button.config(state=tk.DISABLED)
        batch_button.config(state=tk.DISABLED)
        select_weights_button.config(state=tk.DISABLED)
        status_label.config(text="Начало пакетной обработки...")
        log_console(info_console,
                    [("Выбрана папка для пакетной обработки: ", 'info_tag'), (folder_path, 'highlight_tag')])

        Thread(target=process_batch, args=(
        folder_path, model_var, device_var, lang_var, output_format_var, status_label, result_text, root, select_button,
        batch_button, info_console, progress_bar, show_result_var, select_weights_button), daemon=True).start()


def process_batch(folder_path, model_var, device_var, lang_var, output_format_var, status_label, result_text, root,
                  select_button, batch_button, info_console, progress_bar, show_result_var, select_weights_button):
    try:
        audio_video_files = []
        for root_dir, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root_dir, file)
                if is_media_file(file_path):
                    audio_video_files.append(file_path)

        if not audio_video_files:
            log_console(info_console, [("В выбранной папке не найдено аудио/видео файлов.", 'info_tag')])
            status_label.config(text="Готово. Нет файлов для обработки.")
            return

        total_files = len(audio_video_files)
        log_console(info_console, [("Всего файлов для обработки: ", 'info_tag'), (str(total_files), 'highlight_tag')])
        for i, file_path in enumerate(audio_video_files):
            log_console(info_console, [(f"{i + 1} из {total_files}", 'info_tag')])
            duration = get_media_duration(file_path)
            log_console(info_console, [("Продолжительность файла: ", 'info_tag'), (duration, 'highlight_tag')])
            select_button.config(state=tk.DISABLED)
            batch_button.config(state=tk.DISABLED)
            status_label.config(text=f"Обработка файла {i + 1}/{total_files}...")
            process_video_or_audio(file_path, model_var.get(),
                                   'cuda' if device_var.get() == 'CUDA' else 'cpu',
                                   next((code for name, code in LANGUAGES if name == lang_var.get()), None),
                                   next((ext for name, ext in OUTPUT_FORMATS if name == output_format_var.get()), None),
                                   status_label, result_text, root, select_button, info_console, progress_bar,
                                   show_result_var, batch_button, select_weights_button)
        status_label.config(text="Пакетная обработка завершена.")
        log_console(info_console, [("-" * 20, 'info_tag')])

    except Exception as e:
        status_label.config(text="Ошибка пакетной обработки!")
        log_console(info_console, [("Ошибка пакетной обработки: " + str(e), 'error')])
        messagebox.showerror("Ошибка", f"Ошибка пакетной обработки: {e}")
    finally:
        root.title("Преобразовать видео/аудио --> текст")
        select_button.config(state=tk.NORMAL)
        batch_button.config(state=tk.NORMAL)
        select_weights_button.config(state=tk.NORMAL)
        progress_bar.grid_remove()
        progress_bar.stop()


# --- Функции заглушки для меню ---
def read_this():
    messagebox.showinfo("Прочти это",
                        "Нажмите 'Выбрать видео/аудио файл', чтобы выбрать файл для обработки. Вы можете выбрать модель Whisper, устройство (CUDA если доступно, иначе CPU), язык распознавания (Язык оригинала для автоматического определения) и формат выходного файла (TXT или SRT). Для пакетной обработки нажмите 'Добавить папку (пакетная обработка)'.")


def about_program():
    messagebox.showinfo("О программе",
                        "Программа для транскрибации аудио/видео файлов в текст с использованием технологии Whisper.\n\nРазработчик: alexsevas,\n\nemail: a1exsevas@yandex.ru.\n\nВерсия: 0.1")


# --- Глобальная переменная для папки с весами ---
DEFAULT_WEIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
current_weights_dir = DEFAULT_WEIGHTS_DIR

# Список моделей и соответствующих файлов
MODEL_FILE_MAP = {name: f"{name}.pt" for name in WHISPER_MODELS}


def scan_weights_folder(weights_dir, info_console=None):
    found = []
    not_found = []
    for model in WHISPER_MODELS:
        model_path = os.path.join(weights_dir, MODEL_FILE_MAP[model])
        if os.path.exists(model_path):
            found.append(model)
            if info_console:
                log_console(info_console, [(f"Модель '", 'info_tag'), (model, 'highlight_tag'),
                                           ("' найдена в выбранной папке.", 'success_tag')])
        else:
            not_found.append(model)
            if info_console:
                log_console(info_console, [(f"Модель '", 'error_tag'), (model, 'highlight_tag'),
                                           ("' НЕ найдена в выбранной папке.", 'error_tag')])
    if info_console:
        log_console(info_console, [("-" * 20, 'info_tag')])
    return found, not_found


def select_weights_folder(label_widget):
    global current_weights_dir
    folder = filedialog.askdirectory(title="Выберите папку с весами моделей Whisper")
    if folder:
        current_weights_dir = folder
        label_widget.config(text=f"Текущая папка с весами: {current_weights_dir}")
        os.environ['WHISPER_CACHE_DIR'] = current_weights_dir
        found, not_found = scan_weights_folder(current_weights_dir, info_console)
        # Обновить список моделей в combobox
        if found:
            model_combo['values'] = found
            model_var.set(found[0])
        else:
            model_combo['values'] = WHISPER_MODELS
            model_var.set('tiny')
            log_console(info_console,
                        [("В выбранной папке не найдено ни одной модели. Будет загружена модель tiny.", 'error_tag')])
            # Триггерим загрузку tiny (асинхронно)
            Thread(target=lambda: whisper.load_model('tiny'), daemon=True).start()
    else:
        label_widget.config(text=f"Текущая папка с весами: {current_weights_dir}")


# --- Интерфейс ---
root = tk.Tk()
root.title("Преобразовать видео/аудио --> текст")
root.geometry(f"{win_width}x{win_height}+{(screen_width - win_width) // 2}+{(screen_height - win_height) // 2}")

# Создание главного меню
menubar = tk.Menu(root)
root.config(menu=menubar)

# Меню "Прочти это"
read_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Прочти это", menu=read_menu)
read_menu.add_command(label="Открыть", command=read_this)

# Меню "О программе"
about_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="О программе", menu=about_menu)
about_menu.add_command(label="Показать информацию", command=about_program)

# Настройка колонок и строк корневого окна
root.grid_columnconfigure(0, weight=0)
root.grid_columnconfigure(1, weight=1)  # Правая колонка (результат) - расширяется
root.grid_rowconfigure(0,
                       weight=0)  # Верхняя строка (элементы управления в левой, чекбокс/лейбл в правой) - не расширяется сильно
root.grid_rowconfigure(1, weight=1)  # Нижняя строка (консоль в левой, текстовое поле в правой) - расширяется

# --- Левая колонка: Элементы управления и Информационная консоль ---
left_column_frame = tk.Frame(root, width=500)  # Создаем фрейм для левой колонки
left_column_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(5, 3), pady=8)
left_column_frame.grid_propagate(False)  # Отключаем автоматическое изменение размера
left_column_frame.grid_rowconfigure(0, weight=0)  # Верхняя часть (control_frame) - не расширяется
left_column_frame.grid_rowconfigure(1, weight=1)  # Нижняя часть (console_frame) - расширяется
left_column_frame.grid_columnconfigure(0, weight=1)  # Единственная колонка в left_column_frame расширяется

# --- Компактный блок управления (в левой колонке) ---
control_frame = tk.Frame(left_column_frame)  # Родитель - left_column_frame
control_frame.grid(row=0, column=0, sticky="nsew")
control_frame.grid_columnconfigure(0, weight=0)  # Метки не расширяются
control_frame.grid_columnconfigure(1, weight=1)  # Комбобоксы и кнопка расширяются

row_pad = 2

# Модель Whisper
model_label = tk.Label(control_frame, text="Модель Whisper:")
model_label.grid(row=0, column=0, sticky='w', padx=8, pady=(row_pad, 0))
model_var = tk.StringVar(value='medium')
model_combo = ttk.Combobox(control_frame, textvariable=model_var, values=WHISPER_MODELS, state="readonly", width=15)
model_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=(0, row_pad))

# Устройство
device_label = tk.Label(control_frame, text="Устройство:")
device_label.grid(row=1, column=0, sticky='w', padx=8, pady=(row_pad, 0))
device_var = tk.StringVar(value='CUDA' if torch.cuda.is_available() else 'CPU')
device_combo = ttk.Combobox(control_frame, textvariable=device_var, values=['CUDA', 'CPU'], state="readonly", width=15)
device_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, row_pad))

# Язык
lang_label = tk.Label(control_frame, text="Язык распознавания:")
lang_label.grid(row=2, column=0, sticky='w', padx=8, pady=(row_pad, 0))
lang_var = ttk.Combobox(control_frame, values=[l[0] for l in LANGUAGES], state="readonly", width=15)
lang_var.current(1)  # 'Язык оригинала'
lang_var.grid(row=2, column=1, sticky="ew", padx=8, pady=(0, row_pad))

# Формат вывода
output_format_label = tk.Label(control_frame, text="Формат выходного файла:")
output_format_label.grid(row=3, column=0, sticky='w', padx=8, pady=(row_pad, 0))
output_format_var = tk.StringVar(value='TXT файл')
output_format_combo = ttk.Combobox(control_frame, textvariable=output_format_var, values=[f[0] for f in OUTPUT_FORMATS],
                                   state="readonly", width=15)
output_format_combo.current(0)
output_format_combo.grid(row=3, column=1, sticky="ew", padx=8, pady=(0, row_pad))

# Кнопка выбора папки с весами
select_weights_button = ttk.Button(control_frame, text="Выбрать внешнюю папку с весами моделей Whisper",
                                   command=lambda: select_weights_folder(weights_label))
# Кнопка выбора файла
select_button = ttk.Button(control_frame, text="Выбрать видео/аудио файл",
                           command=lambda: select_file(model_var, device_var, lang_var, output_format_var, status_label,
                                                       result_text, root, select_button, info_console, progress_bar,
                                                       show_result_var, batch_button, select_weights_button))
# Кнопка выбора папки с весами
weights_label = tk.Label(control_frame, text=f"Текущая папка с весами: {DEFAULT_WEIGHTS_DIR}", anchor='w',
                         wraplength=280)

# Новая кнопка для пакетной обработки
batch_button = ttk.Button(control_frame, text="Добавить папку (пакетная обработка)",
                          command=lambda: select_folder_for_batch_processing(model_var, device_var, lang_var,
                                                                             output_format_var, status_label,
                                                                             result_text, root, select_button,
                                                                             batch_button, info_console, progress_bar,
                                                                             show_result_var, select_weights_button))

# Статус (сдвигаем на новую строку)
status_label = tk.Label(control_frame, text="Ожидание выбора файла.")

# Сдвигаем все элементы ниже на +2 строки (select_button, batch_button, status_label)
select_weights_button.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(row_pad + 5, row_pad))
weights_label.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, row_pad))
select_button.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=(row_pad + 5, row_pad))
batch_button.grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=(row_pad, row_pad))
status_label.grid(row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=(row_pad, row_pad))

# --- Информационная консоль (в левой колонке) ---
console_frame = tk.Frame(left_column_frame)  # Родитель - left_column_frame
console_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(10, 0))  # Размещаем под control_frame
console_frame.grid_rowconfigure(0, weight=0)  # Прогресс-бар не расширяется
console_frame.grid_rowconfigure(1, weight=1)  # Информационная консоль расширяется
console_frame.grid_columnconfigure(0, weight=1)  # Единственная колонка расширяется

# Прогресс-бар
progress_bar = ttk.Progressbar(console_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
progress_bar.grid(row=0, column=0, sticky="ew", padx=2, pady=2)  # Размещаем в сетке консольного фрейма
progress_bar.grid_remove()  # Изначально скрываем прогресс-бар

# Информационная консоль
scrollbar_console = ttk.Scrollbar(console_frame, orient=tk.VERTICAL)
info_console = tk.Text(console_frame, bg=THEME_DARK['console_bg'], fg=THEME_DARK['console_fg'],
                       state=tk.DISABLED, font=("Consolas", 10), wrap=tk.WORD,
                       borderwidth=0, highlightthickness=0, yscrollcommand=scrollbar_console.set)

scrollbar_console.config(command=info_console.yview)
scrollbar_console.grid(row=1, column=1, sticky="ns")  # Размещаем сбоку от текстового поля консоли
info_console.grid(row=1, column=0, sticky="nsew", padx=(0, 0), pady=(0, 0))  # Размещаем в сетке консольного фрейма

# Настройка тегов для цветов сообщений консоли
info_console.tag_config('info_tag', foreground=THEME_DARK['console_fg'])
info_console.tag_config('success_tag', foreground=THEME_DARK['console_success_fg'])
info_console.tag_config('error_tag', foreground=THEME_DARK['console_error_fg'])
info_console.tag_config('highlight_tag', foreground=THEME_DARK['console_highlight_fg'])

# --- Правая колонка: Чекбокс и поле результата ---
result_container_frame = tk.Frame(root)  # Родитель - root
result_container_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(4, 8),
                            pady=8)  # Занимает 2 строки, правую колонку
result_container_frame.grid_rowconfigure(2, weight=1)  # Текстовое поле будет расширяться
result_container_frame.grid_columnconfigure(0, weight=1)  # Единственная колонка расширяется

# Чекбокс для управления выводом результата
show_result_var = tk.BooleanVar(value=True)


def toggle_result_display():
    if show_result_var.get():
        result_text.config(state=tk.NORMAL)
        result_text.delete(1.0, tk.END)  # Очищаем при активации
        result_label.config(fg=THEME_DARK['fg'])  # Возвращаем нормальный цвет
    else:
        result_text.delete(1.0, tk.END)
        result_text.config(state=tk.DISABLED)
        result_label.config(fg=THEME_DARK['status_fg'])  # Делаем серым


show_result_checkbox = ttk.Checkbutton(result_container_frame, text="Отображать результат транскрипции",
                                       variable=show_result_var, command=toggle_result_display)
show_result_checkbox.grid(row=0, column=0, sticky="w", pady=(0, 5))

result_label = tk.Label(result_container_frame, text="Результат распознавания:")
result_label.grid(row=1, column=0, sticky="w", pady=(0, 5))

result_frame = tk.Frame(result_container_frame)  # Родитель - result_container_frame
result_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 0))
result_frame.grid_columnconfigure(0, weight=1)  # Позволяет result_text расширяться по горизонтали
result_frame.grid_rowconfigure(0, weight=1)  # Позволяет result_text расширяться по вертикали

scrollbar_result = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
result_text = tk.Text(result_frame, wrap=tk.WORD, yscrollcommand=scrollbar_result.set)
scrollbar_result.config(command=result_text.yview)
scrollbar_result.grid(row=0, column=1, sticky="ns")  # Размещаем сбоку от текстового поля
result_text.grid(row=0, column=0, sticky="nsew")  # Размещаем текстовое поле

# Прокрутка колесом мыши для поля результата
result_text.bind('<Enter>', lambda e: result_text.bind_all('<MouseWheel>', lambda ev: result_text.yview_scroll(
    int(-1 * (ev.delta / 120)), 'units')))
result_text.bind('<Leave>', lambda e: result_text.unbind_all('<MouseWheel>'))

# Применить темную тему по умолчанию
apply_dark_theme(root,
                 {'model_label': model_label, 'device_label': device_label, 'lang_label': lang_label,
                  'output_format_label': output_format_label, 'status_label': status_label,
                  'select_button': select_button, 'show_result_checkbox': show_result_checkbox,
                  'batch_button': batch_button},
                 {'result_label': result_label, 'result_text': result_text},
                 {'info_console': info_console, 'progress_bar': progress_bar},
                 {'menubar': menubar, 'read_menu': read_menu, 'about_menu': about_menu})

# Проверка наличия моделей при запуске (теперь вызывается после создания info_console)
if not torch.cuda.is_available():
    log_console(info_console, [
        ("CUDA-совместимое устройство не обнаружено. Будет использоваться CPU (может быть медленнее).", 'info')])

# Проверка наличия моделей при запуске
log_console(info_console, [("Проверка наличия моделей Whisper в кэше:", 'info')])
for model_name in WHISPER_MODELS:
    if check_model_in_cache(model_name):
        log_console(info_console,
                    [("Модель '", 'info_tag'), (model_name, 'highlight_tag'), ("' найдена в кэше.", 'success_tag')])
    else:
        log_console(info_console, [("Модель '", 'error_tag'), (model_name, 'highlight_tag'), (
        "' НЕ найдена в кэше. Она будет загружена автоматически при первом использовании.", 'error_tag')])
log_console(info_console, [("-" * 20, 'info_tag')])

# Установить начальное состояние поля результата
toggle_result_display()

root.mainloop()