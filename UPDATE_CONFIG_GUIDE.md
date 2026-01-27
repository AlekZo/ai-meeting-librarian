# 🔄 Руководство по обновлению конфига

## ⚠️ ВАЖНО: Переименование параметра

Параметр конфига был переименован:

```
❌ output_folder  →  ✅ transcribed_folder
```

## 📝 Как обновить config.json

### Шаг 1: Откройте config.json

```json
{
    "watch_folder": "D:/Nextcloud/Videos/ScreenRecordings/JustRecorded",
    "to_transcribe_folder": "D:/Nextcloud/Videos/ScreenRecordings/ToTranscribe",
    "output_folder": "D:/Nextcloud/Videos/ScreenRecordings/Transcribed",  ← СТАРЫЙ
    ...
}
```

### Шаг 2: Замените параметр

```json
{
    "watch_folder": "D:/Nextcloud/Videos/ScreenRecordings/JustRecorded",
    "to_transcribe_folder": "D:/Nextcloud/Videos/ScreenRecordings/ToTranscribe",
    "transcribed_folder": "D:/Nextcloud/Videos/ScreenRecordings/Transcribed",  ← НОВЫЙ
    ...
}
```

### Шаг 3: Сохраните файл

Просто сохраните config.json с новым параметром.

## ✅ Проверка

После обновления:

1. **Убедитесь, что параметр переименован:**
   ```json
   "transcribed_folder": "D:/Path/To/Transcribed"
   ```

2. **Убедитесь, что папка существует:**
   ```
   D:\Nextcloud\Videos\ScreenRecordings\Transcribed\
   ```

3. **Запустите приложение:**
   ```
   python main.py
   ```

4. **Проверьте логи:**
   ```
   📁 Transcribed folder: D:/Nextcloud/Videos/ScreenRecordings/Transcribed
   ```

## ❌ Что произойдет, если не обновить?

Если вы не обновите config.json, приложение выдаст ошибку:

```
ERROR: Transcribed folder does not exist: None
```

## 🔍 Полный пример config.json

```json
{
    "watch_folder": "D:/Nextcloud/Videos/ScreenRecordings/JustRecorded",
    "to_transcribe_folder": "D:/Nextcloud/Videos/ScreenRecordings/ToTranscribe",
    "transcribed_folder": "D:/Nextcloud/Videos/ScreenRecordings/Transcribed",
    "google_credentials_path": "credentials.json",
    "google_token_path": "token.json",
    "video_extensions": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv"],
    "file_lock_check_delay": 2,
    "file_lock_check_attempts": 5,
    "log_level": "INFO",
    "enable_logging": true,
    "log_file": "logs/auto_renamer.log",
    "dry_run": false,
    "timezone_offset_hours": 3,
    "enable_upload": true,
    "enable_speaker_identification": false,
    "api_base_url": "http://localhost:8080",
    "api_key": "YOUR_API_KEY",
    "google_sheets_id": "YOUR_SHEETS_ID",
    "google_sheets_meeting_tab": "Meeting_Logs",
    "google_sheets_project_tab": "Project_Config",
    "drive_transcript_folder_id": "YOUR_FOLDER_ID",
    "openrouter_max_tokens": 80000,
    "openrouter_api_key": "YOUR_OPENROUTER_KEY",
    "openrouter_model": "google/gemini-2.5-flash-lite",
    "telegram_bot_token": "YOUR_TELEGRAM_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID"
}
```

## 📚 Связанная документация

- `TRANSCRIBED_FOLDER_FLOW.md` - Полный поток обработки файлов
- `TRANSCRIBED_FOLDER_CHANGES.txt` - Краткое резюме изменений
- `CONFIG_REFERENCE.md` - Справочник по всем параметрам

---

**Дата:** 27 января 2026  
**Статус:** ✅ Обновлено
