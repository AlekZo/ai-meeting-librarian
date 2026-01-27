# 📊 Анализ логики работы приложения

## 🔴 ПРОБЛЕМА: Дублирование уведомлений и строк в Google Sheets

### Сценарий: Пользователь завершает редактирование спикеров (нажимает "Done")

---

## 📍 ЭТАП 1: Завершение транскрипции (автоматический)

### Когда: Scriberr завершает транскрипцию видео

**Файл:** `video_uploader.py`

```
1. _poll_status() - опрашивает статус каждые 10 секунд
   ↓
2. Когда status == "completed":
   - Отправляет уведомление: "✅ Transcription completed: {filename}"
   - Вызывает: _download_transcript(job_id, original_file_path)
     └─ Параметры: finalize=False (по умолчанию)
```

**Что происходит в `_download_transcript(job_id, original_file_path, finalize=False)`:**

```
1. Загружает транскрипт с Scriberr
2. Очищает данные: _clean_transcript_data()
3. Так как finalize=False:
   ├─ Идентифицирует спикеров: _identify_speakers()
   ├─ Обновляет в Scriberr: _update_scriberr_speakers()
   ├─ Предлагает пользователю выбрать спикеров: _offer_manual_speaker_assignment()
   └─ Сохраняет транскрипт локально
4. Вызывает: main_app.on_transcript_ready(
     job_id, 
     original_file_path, 
     transcript_data, 
     transcript_path, 
     meeting_info, 
     is_final=False  ← КЛЮЧЕВОЙ ПАРАМЕТР
   )
```

**Что происходит в `on_transcript_ready(..., is_final=False)`:**

```
1. ПРОВЕРКА: if not is_final:
   └─ logger.info("Transcript for job {job_id} is not final yet. Skipping Sheets logging.")
   └─ return  ← ВЫХОД! Ничего не публикуется в Google Sheets
```

✅ **Результат:** На этом этапе в Google Sheets НИЧЕГО не добавляется.

---

## 📍 ЭТАП 2: Пользователь нажимает "Done" (завершает редактирование спикеров)

### Когда: Пользователь нажимает кнопку "Done" в Telegram

**Файл:** `main.py`

```
1. handle_telegram_callback() получает callback_query
2. cb_data["action"] == "speaker_assignment_done"
3. Выполняет:
   ├─ Собирает финальные маппинги спикеров:
   │  ├─ initial_speaker_mappings[job_id] (AI-определенные)
   │  └─ active_mappings[job_id] (пользовательские изменения)
   │
   ├─ Обновляет Scriberr: _update_scriberr_speakers(job_id, final_mappings)
   ├─ Отправляет таблицу маппингов в Telegram
   │
   └─ Запускает в отдельном потоке:
      _download_transcript(
        job_id, 
        "manual_refresh",  ← СПЕЦИАЛЬНЫЙ ФЛАГ
        transcript_data, 
        finalize=True      ← КЛЮЧЕВОЙ ПАРАМЕТР
      )
```

**Что происходит в `_download_transcript(job_id, "manual_refresh", transcript_data, finalize=True)`:**

```
1. is_manual_refresh = ("manual_refresh" == "manual_refresh") = True
2. Загружает транскрипт с Scriberr
3. Очищает данные: _clean_transcript_data()
4. Так как finalize=True:
   └─ ПРОПУСКАЕТ блок "if not finalize:" (не предлагает спикеров)
5. Так как is_manual_refresh=True:
   ├─ Использует существующие данные
   ├─ Сохраняет как "{title}_FINAL.txt"
   └─ Восстанавливает meeting_info
6. Вызывает: main_app.on_transcript_ready(
     job_id, 
     "manual_refresh", 
     transcript_data, 
     transcript_path, 
     meeting_info, 
     is_final=True  ← КЛЮЧЕВОЙ ПАРАМЕТР
   )
7. Отправляет уведомления:
   ├─ "✅ Finalizing transcript for {title}..."
   └─ "✅ Transcript finalized and published for {title}"
```

**Что происходит в `on_transcript_ready(..., is_final=True)`:**

```
1. ПРОВЕРКА: if not is_final: return
   └─ Проходит! (is_final=True)
2. Выполняет полную логику:
   ├─ Загружает конфиг Google Sheets
   ├─ Применяет маппинги спикеров к транскрипту
   ├─ Загружает транскрипт в Google Drive: upload_transcript()
   ├─ Извлекает спикеров: _extract_speakers()
   ├─ Определяет тип встречи: _get_openrouter_response()
   ├─ Генерирует summary: _get_openrouter_response()
   ├─ Определяет проект: _identify_project_tag()
   ├─ Подготавливает данные для таблицы
   ├─ Проверяет интернет: if not self.internet_available
   │  └─ Если нет: enqueue(item) и return
   │  └─ Если да: _publish_meeting_log(item)
   └─ Отправляет уведомление с ссылкой на Google Doc
```

**Что происходит в `_publish_meeting_log(item)`:**

```
1. Получает sheet_id из конфига
2. Подготавливает строку данных:
   [meeting_time, meeting_name, meeting_type, speakers, summary, 
    project_tag, video_source_link, scribber_link, transcript_drive_link, status]
3. Вызывает: sheets_handler.append_meeting_log(sheet_id, meeting_tab, row)
   └─ ДОБАВЛЯЕТ НОВУЮ СТРОКУ В GOOGLE SHEETS
```

---

## 🔍 АНАЛИЗ ДУБЛИРОВАНИЯ

### Сценарий 1: Дублирование уведомлений в Telegram

**Логи показывают:**
```
✅ Finalizing transcript for Front - Aorta weekly sync_2026-01-26_20-30-03.mp4...
✅ Finalizing transcript for Front - Aorta weekly sync_2026-01-26_20-30-03.mp4...
✅ Transcript finalized and published for Front - Aorta weekly sync_2026-01-26_20-30-03.mp4
✅ Transcript finalized and published for Front - Aorta weekly sync_2026-01-26_20-30-03.mp4
```

**Возможные причины:**

1. **Вариант А: `_download_transcript` вызывается дважды**
   - Может быть вызвана дважды из разных мест
   - Проверить: есть ли другие места, где вызывается `_download_transcript` с `finalize=True`

2. **Вариант Б: Уведомление отправляется дважды в одном вызове**
   - В `video_uploader.py` строка 321-322 отправляет ДВА уведомления подряд
   - Это может быть причиной дублирования

3. **Вариант В: `_send_telegram_notification` имеет баг**
   - Функция может отправлять сообщение дважды
   - Проверить реализацию `_send_telegram_notification`

---

### Сценарий 2: Дублирование строк в Google Sheets

**Возможные причины:**

1. **`on_transcript_ready` вызывается дважды с `is_final=True`**
   - Если `_download_transcript` вызывается дважды
   - То `on_transcript_ready` вызывается дважды
   - То `_publish_meeting_log` вызывается дважды
   - **РЕЗУЛЬТАТ:** Две строки в Google Sheets

2. **`_publish_meeting_log` вызывается дважды**
   - Может быть вызвана из разных мест
   - Проверить: есть ли другие места, где вызывается `_publish_meeting_log`

3. **Очередь `meeting_queue` обрабатывается дважды**
   - Если интернета нет, item добавляется в очередь
   - Когда интернет появляется, очередь обрабатывается
   - Может быть обработана дважды

---

## ✅ ПРОВЕРОЧНЫЙ СПИСОК

### 1. Проверить вызовы `_download_transcript`

**Вопрос:** Где вызывается `_download_transcript` с `finalize=True`?

**Ответ:**
- ✅ `main.py` строка 726: `_download_transcript(job_id, "manual_refresh", transcript_data, True)`
- ❓ Есть ли другие места?

**Команда для проверки:**
```bash
grep -n "_download_transcript.*True" *.py
grep -n "_download_transcript.*finalize=True" *.py
```

---

### 2. Проверить вызовы `on_transcript_ready`

**Вопрос:** Где вызывается `on_transcript_ready` с `is_final=True`?

**Ответ:**
- ✅ `video_uploader.py` строка 311: `on_transcript_ready(..., is_final=is_final_call)`
  - Где `is_final_call = finalize` или `is_final_call = True` (если нет Telegram токена)

**Команда для проверки:**
```bash
grep -n "on_transcript_ready" *.py
```

---

### 3. Проверить вызовы `_publish_meeting_log`

**Вопрос:** Где вызывается `_publish_meeting_log`?

**Ответ:**
- ✅ `main.py` строка 1245: `_publish_meeting_log(item)`

**Команда для проверки:**
```bash
grep -n "_publish_meeting_log" *.py
```

---

### 4. Проверить реализацию `_send_telegram_notification`

**Вопрос:** Может ли функция отправлять сообщение дважды?

**Ответ:** Нужно посмотреть реализацию функции

---

## 🎯 ГИПОТЕЗА: Основная причина дублирования

### Сценарий:

1. Пользователь нажимает "Done"
2. `handle_telegram_callback` запускает `_download_transcript(..., finalize=True)` в отдельном потоке
3. `_download_transcript` вызывает `on_transcript_ready(..., is_final=True)`
4. `on_transcript_ready` вызывает `_publish_meeting_log(item)`
5. **ПРОБЛЕМА:** Если `_download_transcript` вызывается дважды (из-за бага или логики), то:
   - `on_transcript_ready` вызывается дважды
   - `_publish_meeting_log` вызывается дважды
   - **РЕЗУЛЬТАТ:** Две строки в Google Sheets

### Возможные причины дублирования `_download_transcript`:

1. **Вызывается из двух разных мест**
   - Проверить все места, где вызывается `_download_transcript`

2. **Вызывается дважды из одного места**
   - Проверить логику в `handle_telegram_callback`

3. **Вызывается в цикле**
   - Проверить, есть ли цикл, который вызывает `_download_transcript`

---

## 📋 РЕКОМЕНДАЦИИ ДЛЯ ПРОВЕРКИ

### Шаг 1: Добавить логирование

```python
# В _download_transcript
logger.info(f"_download_transcript called: job_id={job_id}, finalize={finalize}, is_manual_refresh={is_manual_refresh}")

# В on_transcript_ready
logger.info(f"on_transcript_ready called: job_id={job_id}, is_final={is_final}")

# В _publish_meeting_log
logger.info(f"_publish_meeting_log called: meeting_name={item.get('meeting_name')}")
```

### Шаг 2: Проверить логи

- Сколько раз вызывается `_download_transcript` с `finalize=True`?
- Сколько раз вызывается `on_transcript_ready` с `is_final=True`?
- Сколько раз вызывается `_publish_meeting_log`?

### Шаг 3: Проверить потоки

- Может ли `_download_transcript` вызваться дважды из разных потоков?
- Есть ли race condition?

---

## 🔧 ВОЗМОЖНЫЕ ИСПРАВЛЕНИЯ

### Исправление 1: Добавить флаг "уже обработано"

```python
# В main.py
self.processed_jobs = set()

# В on_transcript_ready
if job_id in self.processed_jobs:
    logger.warning(f"Job {job_id} already processed, skipping")
    return
self.processed_jobs.add(job_id)
```

### Исправление 2: Убедиться, что `_download_transcript` вызывается только один раз

```python
# В handle_telegram_callback
if job_id not in self.download_in_progress:
    self.download_in_progress.add(job_id)
    threading.Thread(target=self.uploader._download_transcript, args=(...)).start()
```

### Исправление 3: Убедиться, что `_publish_meeting_log` вызывается только один раз

```python
# В on_transcript_ready
if job_id not in self.published_jobs:
    self._publish_meeting_log(item)
    self.published_jobs.add(job_id)
```

---

## 📝 ВЫВОДЫ

**Основная проблема:** Функции вызываются дважды, что приводит к дублированию уведомлений и строк в Google Sheets.

**Возможные причины:**
1. `_download_transcript` вызывается дважды
2. `on_transcript_ready` вызывается дважды
3. `_publish_meeting_log` вызывается дважды

**Решение:** Добавить логирование и проверить, сколько раз вызываются эти функции.
