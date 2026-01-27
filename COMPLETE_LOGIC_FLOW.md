# 🎬 Полная логика работы приложения от начала до конца

## 📋 Оглавление
1. [Инициализация приложения](#инициализация-приложения)
2. [Мониторинг файлов](#мониторинг-файлов)
3. [Обработка видео файла](#обработка-видео-файла)
4. [Переименование файла](#переименование-файла)
5. [Загрузка на сервер транскрипции](#загрузка-на-сервер-транскрипции)
6. [Обработка транскрипции](#обработка-транскрипции)
7. [Редактирование спикеров](#редактирование-спикеров)
8. [Финализация и публикация](#финализация-и-публикация)

---

## 🚀 Инициализация приложения

### Файл: `main.py` - `__init__()` и `initialize()`

```
1. AutoMeetingVideoRenamer.__init__()
   ├─ Инициализирует конфиг
   ├─ Создает VideoUploader (для загрузки видео)
   ├─ Создает SystemTrayIcon (иконка в трее)
   ├─ Отправляет стартовое уведомление в Telegram
   ├─ Инициализирует структуры данных:
   │  ├─ callback_map: {cb_id: {action, data}}
   │  ├─ user_states: {chat_id: {state, data}}
   │  ├─ active_mappings: {job_id: {speaker_id: custom_name}}
   │  └─ initial_speaker_mappings: {job_id: {speaker_id: ai_name}}
   ├─ Создает SheetsDriveHandler (для Google Sheets и Drive)
   └─ Создает MeetingLogQueue (очередь для офлайн режима)

2. initialize()
   ├─ Проверяет конфиг
   ├─ Инициализирует FileMonitor
   │  └─ Подписывается на события создания видео файлов
   ├─ Инициализирует GoogleCalendarHandler
   │  └─ Аутентифицируется с Google Calendar
   ├─ Инициализирует Google Sheets табы
   └─ Возвращает True если успешно

3. run()
   ├─ Запускает FileMonitor.start()
   ├─ Запускает мониторинг интернета в отдельном потоке
   ├─ Запускает Telegram update poller в отдельном потоке
   ├─ Обрабатывает существующие файлы: process_existing_files()
   ├─ Обрабатывает файлы из офлайн очереди: process_pending_files()
   └─ Ждет сигнала выхода (Ctrl+C)
```

---

## 👁️ Мониторинг файлов

### Файл: `file_monitor.py` - `FileMonitor` и `VideoFileEventHandler`

```
1. FileMonitor.start()
   └─ Запускает watchdog Observer
      └─ Слушает события в watch_folder

2. VideoFileEventHandler.on_created(event)
   ├─ Проверяет, что это файл (не папка)
   ├─ Проверяет расширение файла (mp4, mov, avi и т.д.)
   └─ Вызывает callback: on_video_created(file_path)
      └─ Это метод main.py: AutoMeetingVideoRenamer.on_video_created()
```

---

## 🎥 Обработка видео файла

### Файл: `main.py` - `on_video_created()`

```
1. on_video_created(file_path)
   │
   ├─ Проверка 1: Готов ли файл к обработке?
   │  └─ _is_file_ready(file_path)
   │     └─ Проверяет, что файл не заблокирован (не пишется)
   │        └─ Если нет → return (выход)
   │
   ├─ Проверка 2: Есть ли интернет?
   │  └─ _queue_if_offline(file_path)
   │     ├─ Если нет интернета:
   │     │  └─ Добавляет файл в pending_files
   │     │  └─ return (выход)
   │     └─ Если есть интернет:
   │        └─ Продолжает обработку
   │
   ├─ Шаг 1: Извлечение временной метки из имени файла
   │  └─ FileRenamer.extract_timestamp_from_filename(filename)
   │     └─ Возвращает: (datetime, timestamp_str, format_type)
   │        └─ Если не удалось → return (выход)
   │
   ├─ Шаг 2: Поиск встреч в Google Calendar
   │  └─ _get_meetings_for_timestamp(dt, format_type)
   │     └─ GoogleCalendarHandler.get_meetings_at_time(dt_utc)
   │        └─ Возвращает список встреч в это время
   │
   ├─ Шаг 3: Обработка результатов поиска
   │  │
   │  ├─ Если встреч не найдено:
   │  │  └─ _notify_no_meeting(file_path, filename)
   │  │     ├─ Получает все встречи на эту дату
   │  │     ├─ Если встреч нет вообще:
   │  │     │  └─ Отправляет уведомление "No meeting found"
   │  │     │     └─ Кнопки: "Retry", "Cancel"
   │  │     └─ Если встречи есть:
   │  │        └─ Показывает список встреч пользователю
   │  │           └─ _prompt_meeting_selection()
   │  │
   │  ├─ Если найдена одна встреча:
   │  │  └─ Переименовывает файл с названием встречи
   │  │     └─ _rename_with_title(file_path, meeting_title, ...)
   │  │
   │  └─ Если найдено несколько встреч:
   │     └─ Показывает список встреч пользователю
   │        └─ _prompt_meeting_selection(file_path, filename, meetings)
   │           ├─ Создает кнопки для каждой встречи
   │           ├─ Сохраняет callback_map
   │           └─ Отправляет сообщение в Telegram
   │              └─ Пользователь нажимает кнопку → handle_telegram_callback()
```

---

## 📝 Переименование файла

### Файл: `main.py` - `_rename_with_title()` и `handle_successful_rename()`

```
1. _rename_with_title(file_path, meeting_title, timestamp_str, meeting_time)
   │
   ├─ Генерирует новое имя файла
   │  └─ FileRenamer.generate_new_filename_from_timestamp()
   │     └─ Формат: "{meeting_title}_{YYYY-MM-DD}_{HH-MM-SS}.mp4"
   │
   ├─ Переименовывает файл
   │  └─ FileRenamer.rename_file(file_path, new_path)
   │     └─ Если успешно:
   │        └─ Вызывает handle_successful_rename()
   │
   └─ Если ошибка:
      └─ Логирует ошибку

2. handle_successful_rename(result, file_path)
   │
   ├─ Отправляет уведомление в Telegram
   │  └─ "✅ Successfully renamed to {new_filename}"
   │
   ├─ Проверяет, нужно ли копировать в output_folder
   │  └─ Если output_folder настроен:
   │     ├─ Копирует файл в output_folder
   │     │  └─ FileRenamer.copy_file(new_path, destination_path)
   │     │
   │     ├─ Проверяет, нужно ли загружать на сервер
   │     │  └─ Если enable_upload=True:
   │     │     ├─ Подготавливает meeting_info:
   │     │     │  ├─ meeting_name: название встречи
   │     │     │  ├─ meeting_time: время встречи
   │     │     │  └─ video_source_link: путь к файлу
   │     │     │
   │     │     └─ Загружает видео на сервер
   │     │        └─ self.uploader.upload_video(destination_path, meeting_info)
   │     │           └─ Добавляет в очередь загрузки
   │     │
   │     └─ Удаляет переименованный файл из watch_folder
   │        └─ FileRenamer.delete_file(new_path)
   │
   └─ Если output_folder не настроен:
      └─ Логирует предупреждение
```

---

## 📤 Загрузка на сервер транскрипции

### Файл: `video_uploader.py` - `upload_video()` и `_process_upload()`

```
1. upload_video(file_path, meeting_info)
   │
   ├─ Проверяет, включена ли загрузка
   │  └─ Если нет → return
   │
   └─ Добавляет в очередь загрузки
      └─ self.upload_queue.put((file_path, meeting_info))

2. _worker() - фоновый поток
   │
   └─ Обрабатывает очередь загрузки
      └─ Вызывает _process_upload() для каждого файла

3. _process_upload(file_path, meeting_info)
   │
   ├─ Проверяет, существует ли файл
   │  └─ Если нет → return
   │
   ├─ Отправляет POST запрос на сервер
   │  └─ POST /api/v1/transcription/upload-video
   │     ├─ Параметры:
   │     │  ├─ video: содержимое файла
   │     │  └─ title: имя файла
   │     │
   │     └─ Ответ: {id: job_id, ...}
   │
   ├─ Отправляет уведомление в Telegram
   │  └─ "📤 Uploaded: {filename}"
   │     └─ Кнопка: "🛑 Cancel Processing"
   │
   ├─ Сохраняет job_id и meeting_info
   │  └─ self.meeting_info_by_job[job_id] = meeting_info
   │
   └─ Запускает опрос статуса транскрипции
      └─ _poll_status(job_id, original_file_path)
         └─ Опрашивает статус каждые 10 секунд
```

---

## 🎙️ Обработка транскрипции

### Файл: `video_uploader.py` - `_poll_status()` и `_download_transcript()`

```
1. _poll_status(job_id, original_file_path)
   │
   └─ Цикл: каждые 10 секунд
      │
      ├─ GET /api/v1/transcription/{job_id}/status
      │  └─ Возвращает: {status: "processing" | "completed" | "failed"}
      │
      ├─ Если status == "completed":
      │  │
      │  ├─ Отправляет уведомление
      │  │  └─ "✅ Transcription completed: {filename}"
      │  │
      │  └─ Загружает транскрипт
      │     └─ _download_transcript(job_id, original_file_path)
      │        └─ Параметры: finalize=False (по умолчанию)
      │
      ├─ Если status == "failed":
      │  │
      │  ├─ Отправляет уведомление
      │  │  └─ "❌ Transcription failed: {filename}"
      │  │
      │  └─ Выход из цикла
      │
      └─ Если status == "processing":
         └─ Продолжает опрос

2. _download_transcript(job_id, original_file_path, existing_transcript_data=None, finalize=False)
   │
   ├─ Загружает транскрипт с сервера
   │  └─ GET /api/v1/transcription/{job_id}/transcript
   │     └─ Возвращает: {segments: [...], title: "...", ...}
   │
   ├─ Очищает данные
   │  └─ _clean_transcript_data(transcript_data)
   │     └─ Объединяет сегменты, форматирует текст
   │
   ├─ Если finalize=False (первый вызов):
   │  │
   │  ├─ Идентифицирует спикеров
   │  │  └─ _identify_speakers(transcript_data, job_id)
   │  │     ├─ Использует OpenRouter AI
   │  │     └─ Возвращает: {speaker_id: ai_name, ...}
   │  │
   │  ├─ Обновляет спикеров в Scriberr
   │  │  └─ _update_scriberr_speakers(job_id, identified_speakers)
   │  │     └─ PATCH /api/v1/transcription/{job_id}/speakers
   │  │
   │  ├─ Предлагает пользователю выбрать спикеров
   │  │  └─ _offer_manual_speaker_assignment(job_id, speakers, transcript_data)
   │  │     ├─ Создает кнопки для редактирования спикеров
   │  │     ├─ Сохраняет callback_map
   │  │     └─ Отправляет сообщение в Telegram
   │  │        └─ Пользователь может:
   │  │           ├─ Переименовать спикера
   │  │           ├─ Поменять спикеров местами
   │  │           └─ Нажать "Done" для финализации
   │  │
   │  └─ Вызывает on_transcript_ready(..., is_final=False)
   │     └─ Проверка: if not is_final: return
   │        └─ ВЫХОД (ничего не публикуется)
   │
   └─ Если finalize=True (второй вызов, после "Done"):
      │
      ├─ Пропускает идентификацию спикеров
      │
      ├─ Сохраняет транскрипт локально
      │  └─ _save_transcript_file(save_path, transcript_data)
      │
      ├─ Вызывает on_transcript_ready(..., is_final=True)
      │  └─ Выполняется полностью (см. ниже)
      │
      └─ Отправляет уведомления
         ├─ "✅ Finalizing transcript for {title}..."
         └─ "✅ Transcript finalized and published for {title}"
```

---

## 👤 Редактирование спикеров

### Файл: `main.py` - `handle_telegram_callback()` и `handle_telegram_message()`

```
1. Пользователь нажимает кнопку в Telegram
   │
   └─ _handle_telegram_updates() получает callback_query
      │
      └─ handle_telegram_callback(callback_query)
         │
         ├─ Получает cb_data из callback_map
         │  └─ cb_data = self.callback_map[callback_data]
         │
         └─ Обрабатывает действие в зависимости от cb_data["action"]

2. Действие: "rename_speaker"
   │
   ├─ Пользователь нажимает кнопку "Edit Speaker Name"
   │  └─ Отправляется сообщение: "Enter new name for {speaker_id}"
   │
   ├─ Пользователь отправляет текст
   │  └─ handle_telegram_message() получает сообщение
   │     │
   │     ├─ Проверяет, находится ли пользователь в состоянии "awaiting_name"
   │     │  └─ user_states[chat_id] = {state: "awaiting_name", job_id, speaker_id, ...}
   │     │
   │     ├─ Получает новое имя из сообщения
   │     │  └─ new_name = text.strip()
   │     │
   │     ├─ Отправляет подтверждение
   │     │  └─ "Confirm: {speaker_id} → {new_name}?"
   │     │     └─ Кнопки: "✅ Confirm", "❌ Cancel"
   │     │
   │     └─ Сохраняет в callback_map для подтверждения
   │
   └─ Пользователь нажимает "Confirm"
      │
      ├─ Сохраняет маппинг
      │  └─ self.active_mappings[job_id][speaker_id] = new_name
      │
      ├─ Обновляет в Scriberr
      │  └─ _update_scriberr_speakers(job_id, {speaker_id: new_name})
      │
      └─ Показывает меню снова
         └─ _offer_manual_speaker_assignment()

3. Действие: "swap_speakers"
   │
   ├─ Пользователь нажимает кнопку "Swap"
   │  └─ Меняет спикеров местами
   │
   ├─ Сохраняет маппинг
   │  └─ self.active_mappings[job_id][s1] = name2
   │  └─ self.active_mappings[job_id][s2] = name1
   │
   ├─ Обновляет в Scriberr
   │  └─ _update_scriberr_speakers(job_id, {s1: name2, s2: name1})
   │
   └─ Показывает меню снова
      └─ _offer_manual_speaker_assignment()

4. Действие: "speaker_assignment_done"
   │
   ├─ Пользователь нажимает кнопку "Done"
   │  └─ Завершает редактирование спикеров
   │
   ├─ Собирает финальные маппинги
   │  ├─ initial_speaker_mappings[job_id] (AI-определенные)
   │  └─ active_mappings[job_id] (пользовательские)
   │
   ├─ Обновляет в Scriberr в последний раз
   │  └─ _update_scriberr_speakers(job_id, final_mappings)
   │
   ├─ Отправляет таблицу маппингов в Telegram
   │  └─ "📊 Final Speaker Mapping for {filename}:"
   │
   └─ Запускает финализацию в отдельном потоке
      └─ _download_transcript(job_id, "manual_refresh", transcript_data, finalize=True)
         └─ Это вызывает on_transcript_ready(..., is_final=True)
```

---

## ✅ Финализация и публикация

### Файл: `main.py` - `on_transcript_ready()`

```
1. on_transcript_ready(job_id, original_file_path, transcript_data, transcript_path, meeting_info, is_final=False)
   │
   ├─ Проверка: if not is_final: return
   │  └─ Если is_final=False → ВЫХОД (ничего не делается)
   │
   └─ Если is_final=True → Продолжает выполнение

2. Подготовка данных
   │
   ├─ Загружает конфиг Google Sheets
   │  ├─ sheet_id
   │  ├─ meeting_tab
   │  ├─ project_tab
   │  └─ drive_folder_id
   │
   ├─ Применяет маппинги спикеров к транскрипту
   │  └─ Для каждого сегмента:
   │     └─ segment["speaker"] = mapping.get(speaker_id, speaker_id)
   │
   ├─ Загружает транскрипт в Google Drive
   │  └─ sheets_handler.upload_transcript(transcript_path, drive_folder_id)
   │     └─ Создает Google Doc с содержимым транскрипта
   │     └─ Возвращает: transcript_drive_link
   │
   └─ Сохраняет JSON версию транскрипта
      └─ Для отладки и анализа

3. Извлечение информации из транскрипта
   │
   ├─ Извлекает спикеров
   │  └─ _extract_speakers(transcript_data)
   │     └─ Возвращает: [speaker1, speaker2, ...]
   │
   ├─ Применяет маппинги к спикерам
   │  └─ Если speaker_id в mapping → использует custom_name
   │
   ├─ Определяет тип встречи
   │  └─ _get_openrouter_response(type_prompt)
   │     ├─ Использует AI для классификации
   │     └─ Возвращает: "Daily Standup" | "Sprint Planning" | ...
   │
   ├─ Генерирует summary
   │  └─ _get_openrouter_response(summary_prompt)
   │     ├─ Анализирует транскрипт
   │     └─ Возвращает: краткое описание встречи
   │
   └─ Определяет проект
      └─ _identify_project_tag(projects, trimmed_text)
         ├─ Ищет ключевые слова в транскрипте
         └─ Возвращает: project_tag

4. Подготовка строки для Google Sheets
   │
   ├─ Форматирует время встречи
   │  └─ Формат: M/D/YYYY HH:MM:SS (с часовым поясом +3)
   │
   ├─ Подготавливает ссылки
   │  ├─ video_source_link: =HYPERLINK("...", "Link")
   │  ├─ scribber_link: =HYPERLINK("...", "Scriberr")
   │  └─ transcript_drive_link: =HYPERLINK("...", "Google Doc")
   │
   └─ Создает item (словарь с данными)
      ├─ meeting_time
      ├─ meeting_name
      ├─ meeting_type
      ├─ speakers
      ├─ summary
      ├─ project_tag
      ├─ video_source_link
      ├─ scribber_link
      ├─ transcript_drive_link
      └─ status: "Processed"

5. Проверка интернета и публикация
   │
   ├─ Если интернета нет:
   │  │
   │  ├─ Добавляет item в очередь
   │  │  └─ self.meeting_queue.enqueue(item)
   │  │
   │  └─ return (выход)
   │
   └─ Если интернет есть:
      │
      ├─ Публикует в Google Sheets
      │  └─ _publish_meeting_log(item)
      │     │
      │     ├─ Получает sheet_id
      │     ├─ Подготавливает строку данных
      │     └─ Вызывает sheets_handler.append_meeting_log()
      │        └─ Добавляет новую строку в таблицу
      │
      └─ Отправляет уведомление в Telegram
         └─ "📄 Transcript (Google Doc): {link}"
```

---

## 🔄 Обработка офлайн режима

### Файл: `main.py` - `process_pending_files()` и `flush_meeting_queue()`

```
1. Когда интернет недоступен:
   │
   ├─ Видео файлы добавляются в pending_files
   │  └─ _queue_if_offline(file_path)
   │
   └─ Встречи добавляются в meeting_queue
      └─ self.meeting_queue.enqueue(item)

2. Когда интернет восстанавливается:
   │
   ├─ monitor_internet_connection() обнаруживает восстановление
   │  └─ self.internet_available = True
   │
   ├─ Обрабатывает pending_files
   │  └─ process_pending_files()
   │     └─ Вызывает on_video_created() для каждого файла
   │
   └─ Обрабатывает meeting_queue
      └─ flush_meeting_queue()
         └─ Публикует каждый item в Google Sheets
```

---

## 📊 Диаграмма потока данных

```
┌─────────────────────────────────────────────────────────────────┐
│                    ИНИЦИАЛИЗАЦИЯ                                │
│  initialize() → FileMonitor, GoogleCalendarHandler, Sheets      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   МОНИТОРИНГ ФАЙЛОВ                             │
│  FileMonitor.on_created() → on_video_created()                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ПРОВЕРКА ГОТОВНОСТИ                            │
│  _is_file_ready() → _queue_if_offline()                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ПОИСК ВСТРЕЧ В КАЛЕНДАРЕ                       │
│  _get_meetings_for_timestamp() → GoogleCalendarHandler          │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    Нет встреч    1 встреча      Несколько встреч
         │               │               │
         ▼               ▼               ▼
   Показать      Переименовать   Показать список
   список всех   файл            для выбора
   встреч на     │               │
   дату          ▼               ▼
         │   _rename_with_title()
         │       │
         └───────┼───────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │  handle_successful_rename()    │
    │  Копирование и загрузка        │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  uploader.upload_video()       │
    │  Добавление в очередь          │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  _process_upload()             │
    │  POST /upload-video            │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  _poll_status()                │
    │  Опрос каждые 10 сек           │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  _download_transcript()        │
    │  finalize=False                │
    │  Идентификация спикеров        │
    │  Предложение редактирования    │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  Пользователь редактирует      │
    │  спикеров в Telegram           │
    │  Нажимает "Done"               │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  _download_transcript()        │
    │  finalize=True                 │
    │  Финализация                   │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  on_transcript_ready()         │
    │  is_final=True                 │
    │  Полная обработка              │
    └────────────────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    Загрузка в    Определение    Генерация
    Google Drive  типа встречи   summary
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  _publish_meeting_log()        │
    │  Добавление строки в Sheets    │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  Отправка уведомления в TG     │
    │  с ссылкой на Google Doc       │
    └────────────────────────────────┘
```

---

## 🔍 Ключевые моменты

### 1. Двойной вызов `_download_transcript`

- **Первый вызов** (finalize=False):
  - Идентифицирует спикеров
  - Предлагает пользователю редактировать
  - Вызывает `on_transcript_ready(..., is_final=False)` → ВЫХОД

- **Второй вызов** (finalize=True):
  - Пропускает идентификацию
  - Вызывает `on_transcript_ready(..., is_final=True)` → ПОЛНАЯ ОБРАБОТКА

### 2. Маппинги спикеров

- **initial_speaker_mappings**: AI-определенные имена спикеров
- **active_mappings**: Пользовательские изменения имен спикеров
- Оба маппинга применяются при финализации

### 3. Офлайн режим

- Видео файлы: `pending_files` (список)
- Встречи: `meeting_queue` (JSON файл)
- Обрабатываются при восстановлении интернета

### 4. Telegram интеграция

- Callback buttons для выбора встреч
- ForceReply для ввода имен спикеров
- Inline buttons для редактирования спикеров

---

## 🐛 Возможные проблемы

### Проблема 1: Дублирование уведомлений

**Причина:** `_download_transcript` может вызваться дважды с `finalize=True`

**Решение:** Добавить флаг "уже обработано"

### Проблема 2: Дублирование строк в Google Sheets

**Причина:** `on_transcript_ready` вызывается дважды с `is_final=True`

**Решение:** Добавить проверку "уже опубликовано"

### Проблема 3: Race condition в многопоточности

**Причина:** Несколько потоков могут обрабатывать один job_id одновременно

**Решение:** Использовать lock или флаг "в обработке"

---

## ✨ Итоговая логика

1. **Мониторинг** → Обнаружение видео файла
2. **Поиск** → Поиск встречи в Google Calendar
3. **Переименование** → Переименование файла по названию встречи
4. **Загрузка** → Загрузка на сервер транскрипции
5. **Транскрипция** → Ожидание завершения транскрипции
6. **Идентификация** → AI определяет спикеров
7. **Редактирование** → Пользователь редактирует спикеров в Telegram
8. **Финализация** → Финальная загрузка транскрипта
9. **Публикация** → Добавление строки в Google Sheets
10. **Уведомление** → Отправка ссылки на Google Doc в Telegram
