import os
import requests
import json
import logging
import time
import threading
import queue
from pathlib import Path
from http_client import request_json, request_text

logger = logging.getLogger(__name__)

class VideoUploader:
    def __init__(self, config):
        self.config = config
        self.base_url = config.get("api_base_url", "http://localhost:8080").rstrip('/')
        self.api_key = config.get("api_key", "")
        self.enable_upload = config.get("enable_upload", False)
        
        # Initialize Queue
        self.upload_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Video uploader queue worker started")

        self.meeting_info_by_job = {}
        self.transcription_lock = threading.Lock()
        self.is_transcribing = False

    def _worker(self):
        """Background worker to process uploads one by one"""
        while True:
            try:
                item = self.upload_queue.get()
                if item is None:
                    break

                if isinstance(item, tuple):
                    file_path, meeting_info = item
                else:
                    file_path, meeting_info = item, None

                logger.info(f"Queue processing: {file_path}")
                
                # Wait if another transcription is already in progress
                while self.is_transcribing:
                    logger.debug("Another transcription in progress, waiting...")
                    time.sleep(10)
                
                self._process_upload(file_path, meeting_info)
                self.upload_queue.task_done()
                # Small delay between uploads
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in queue worker: {str(e)}")

    def upload_video(self, file_path, meeting_info=None):
        """Add a file to the upload queue"""
        if not self.enable_upload:
            logger.info(f"Upload disabled. Skipping queue for {file_path}")
            return

        logger.info(f"Adding to upload queue: {file_path}")
        self.upload_queue.put((file_path, meeting_info))

    def _process_upload(self, file_path, meeting_info=None):
        """Actual upload logic (previously upload_video)"""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return

        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Determine endpoint based on file extension
        if file_ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
            url = f"{self.base_url}/api/v1/transcription/submit"
            file_field = 'audio'
            mime_type = 'audio/mpeg' if file_ext == '.mp3' else f'audio/{file_ext[1:]}'
        else:
            url = f"{self.base_url}/api/v1/transcription/upload-video"
            file_field = 'video'
            mime_type = 'video/mp4'

        headers = {"X-API-Key": self.api_key}

        try:
            with open(file_path, 'rb') as f:
                files = {
                    file_field: (file_name, f, mime_type),
                    'title': (None, file_name)
                }
                
                # Add transcription parameters if using /submit
                if url.endswith("/submit"):
                    # Add default parameters for /submit
                    files['diarization'] = (None, 'true')
                    if meeting_info and meeting_info.get('language'):
                        files['language'] = (None, meeting_info['language'])

                response, response_data = request_json("POST", url, headers=headers, files=files)
                if not response:
                    self._save_log(file_path, "ERROR", "Upload failed")
                    return
                if response.status_code != 200:
                    response_data = response.text
            self._save_log(file_path, response.status_code, response_data)
            
            if response.status_code == 200:
                logger.info(f"Successfully uploaded {file_name}")
                cb_id = f"cancel_{int(time.time())}"
                # Store in config or pass back to main to handle cancellation
                self._send_telegram_notification(
                    f"📤 Uploaded: {file_name}",
                    reply_markup={"inline_keyboard": [[{"text": "🛑 Cancel Processing", "callback_data": cb_id}]]}
                )
                if isinstance(response_data, dict) and 'id' in response_data:
                    job_id = response_data['id']
                    if meeting_info:
                        self.meeting_info_by_job[job_id] = meeting_info
                    # Register the job for potential cancellation
                    if hasattr(self, 'main_app'):
                        self.main_app.callback_map[cb_id] = {"action": "cancel", "job_id": job_id, "file_path": file_path}
                        self.main_app.callback_persistence.save(self.main_app.callback_map)
                    
                    # Move file to output folder after successful upload
                    self._move_file_to_output(file_path)
                    
                    # If we used /submit, transcription is already started
                    if url.endswith("/submit"):
                        logger.info(f"Transcription already started via /submit for {job_id}")
                        # We still need to start polling
                        threading.Thread(target=self._poll_status, args=(job_id, file_path)).start()
                    else:
                        self.start_transcription(job_id, file_path)
            else:
                logger.error(f"Failed to upload {file_name}. Status: {response.status_code}")
                self._send_telegram_notification(f"❌ Upload failed: {file_name}")
        except Exception as e:
            logger.error(f"Error during upload of {file_name}: {str(e)}")
            self._save_log(file_path, "ERROR", str(e))

    def _move_file_to_output(self, file_path):
        """Move uploaded file to transcribed folder"""
        try:
            transcribed_folder = self.config.get("transcribed_folder")
            if not transcribed_folder or not os.path.exists(transcribed_folder):
                logger.warning(f"Transcribed folder not configured or doesn't exist: {transcribed_folder}")
                return False
            
            filename = os.path.basename(file_path)
            destination_path = os.path.join(transcribed_folder, filename)
            
            # Check if file still exists (might have been deleted)
            if not os.path.exists(file_path):
                logger.warning(f"Source file no longer exists: {file_path}")
                return False
            
            # Move file to transcribed folder
            logger.info(f"Moving file to transcribed folder: {destination_path}")
            os.rename(file_path, destination_path)
            logger.info(f"✓ File moved to transcribed folder: {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Error moving file to output folder: {e}")
            return False

    def start_transcription(self, job_id, original_file_path, retry_on_cpu=False):
        url = f"{self.base_url}/api/v1/transcription/{job_id}/start"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Get language from meeting info if available
        language = None
        if job_id in self.meeting_info_by_job:
            language = self.meeting_info_by_job[job_id].get("language")
        
        device = "cpu" if retry_on_cpu else "cuda"
        compute_type = "int8" if retry_on_cpu else "float16"
        # Reduced batch_size for long meetings to avoid CUDA OOM
        batch_size = 1 if retry_on_cpu else 4  # Reduced from 8 to 4 for better stability on long files

        # Model configuration
        model_family = "whisper"
        model_name = "large-v3"
        
        # Store start time and params for the notification
        if not hasattr(self, 'job_stats'):
            self.job_stats = {}
        self.job_stats[job_id] = {
            "start_time": time.time(),
            "device": device,
            "params": f"bs={batch_size}, {compute_type}",
            "model_family": model_family,
            "model": model_name,
            "diarize_model": "pyannote"
        }

        payload = {
            "model_family": model_family,
            "model": model_name,
            "model_cache_only": False,
            "device": device,
            "device_index": 0,
            "batch_size": batch_size,
            "compute_type": compute_type,
            "threads": 14,  # Optimized for your 14-core CPU
            "output_format": "all",
            "verbose": True,
            "task": "transcribe",
            "language": language,
            "interpolate_method": "nearest",
            "no_align": False,
            "return_char_alignments": False,
            "vad_method": "pyannote",
            "vad_onset": 0.55,
            "vad_offset": 0.35,
            "chunk_size": 20, # Reduced from 30 to 20 to lower memory pressure during alignment
            "diarize": True,
            "diarize_model": "pyannote",
            "speaker_embeddings": False,
            "temperature": 0,
            "best_of": 5,
            "beam_size": 5,
            "patience": 1,
            "length_penalty": 1,
            "suppress_numerals": False,
            "condition_on_previous_text": False,
            "fp16": not retry_on_cpu,
            "temperature_increment_on_fallback": 0.2,
            "compression_ratio_threshold": 2.4,
            "logprob_threshold": -1,
            "no_speech_threshold": 0.6,
            "highlight_words": False,
            "segment_resolution": "sentence",
            "print_progress": False,
            "attention_context_left": 256,
            "attention_context_right": 256,
            "is_multi_track_enabled": False,
            "api_key": ""
        }

        try:
            response, response_data = request_json("POST", url, headers=headers, json_body=payload)
            if not response:
                self._append_to_log(original_file_path, "TRANSCRIPTION_ERROR", "ERROR", "No response")
                return
            if response.status_code != 200:
                response_data = response.text
            self._append_to_log(original_file_path, "TRANSCRIPTION_START", response.status_code, response_data)
            
            if response.status_code == 200:
                logger.info(f"Successfully started transcription for job {job_id} on {device}")
                self.is_transcribing = True
                cb_id = f"cancel_{int(time.time())}"
                if hasattr(self, 'main_app'):
                    self.main_app.callback_map[cb_id] = {"action": "cancel", "job_id": job_id, "file_path": original_file_path}
                    self.main_app.callback_persistence.save(self.main_app.callback_map)
                
                self._send_telegram_notification(
                    f"🎙️ Transcription started ({device}): {os.path.basename(original_file_path)}",
                    reply_markup={"inline_keyboard": [[{"text": "🛑 Stop Transcription", "callback_data": cb_id}]]}
                )
                threading.Thread(target=self._poll_status, args=(job_id, original_file_path), daemon=True).start()
            else:
                logger.error(f"Failed to start transcription for job {job_id}. Status: {response.status_code}")
                self._send_telegram_notification(f"❌ Transcription failed to start: {os.path.basename(original_file_path)}")
        except Exception as e:
            logger.error(f"Error starting transcription for job {job_id}: {str(e)}")
            self._append_to_log(original_file_path, "TRANSCRIPTION_ERROR", "ERROR", str(e))

    def _poll_status(self, job_id, original_file_path):
        """Poll transcription status until completion or failure"""
        url = f"{self.base_url}/api/v1/transcription/{job_id}/status"
        headers = {"X-API-Key": self.api_key}
        
        logger.info(f"Starting status polling for job {job_id}")
        poll_count = 0
        
        while True:
            try:
                poll_count += 1
                logger.debug(f"[Poll #{poll_count}] Checking status for job {job_id}")
                response, data = request_json("GET", url, headers=headers, timeout=10)
                
                if response and response.status_code == 200 and data:
                    status = data.get("status")
                    logger.info(f"[Poll #{poll_count}] Job {job_id} status: {status}")
                    
                    if status == "completed":
                        logger.info(f"✅ Transcription completed for job {job_id}")
                        self.is_transcribing = False
                        scriberr_link = f"{self.base_url}/audio/{job_id}"
                        
                        # Calculate duration and get stats
                        stats_text = ""
                        if hasattr(self, 'job_stats') and job_id in self.job_stats:
                            stats = self.job_stats[job_id]
                            duration = int(time.time() - stats["start_time"])
                            m, s = divmod(duration, 60)
                            time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
                            stats_text = f"\n⚙️ {stats['device'].upper()} | {stats['params']} | ⏱️ {time_str}"
                            del self.job_stats[job_id]

                        self._send_telegram_notification(
                            f"✅ Transcription completed: {os.path.basename(original_file_path)}{stats_text}\n🔗 View on Scriberr: {scriberr_link}"
                        )
                        
                        # Download transcript and send enhanced notification with additional parameters
                        self._download_transcript_and_notify(job_id, original_file_path)
                        break
                    elif status == "failed":
                        logger.error(f"❌ Transcription failed for job {job_id}")
                        self.is_transcribing = False
                        
                        # Check if it was a CUDA OOM error
                        error_msg = ""
                        if isinstance(data, dict) and "error" in data:
                            error_msg = str(data.get("error", ""))
                        
                        if "CUDA failed with error out of memory" in error_msg or "out of memory" in error_msg.lower():
                            logger.warning(f"Detected OOM for job {job_id}. Retrying on CPU...")
                            self._send_telegram_notification(f"⚠️ GPU OOM detected for {os.path.basename(original_file_path)}. Retrying on CPU...")
                            # Small delay before retry
                            time.sleep(5)
                            self.start_transcription(job_id, original_file_path, retry_on_cpu=True)
                            break
                        
                        # For other failures, offer a manual retry button
                        retry_cb_id = f"retry_tx_{int(time.time())}"
                        if hasattr(self, 'main_app'):
                            self.main_app.callback_map[retry_cb_id] = {
                                "action": "retry_transcription", 
                                "job_id": job_id, 
                                "file_path": original_file_path
                            }
                            self.main_app.callback_persistence.save(self.main_app.callback_map)

                        self._send_telegram_notification(
                            f"❌ Transcription failed: {os.path.basename(original_file_path)}\nError: {error_msg[:100]}...",
                            reply_markup={"inline_keyboard": [[{"text": "🔄 Retry Transcription", "callback_data": retry_cb_id}]]}
                        )
                        self._append_to_log(original_file_path, "TRANSCRIPTION_FAILED", 200, data)
                        break
                    else:
                        logger.debug(f"Job {job_id} still processing... (status: {status})")
                else:
                    logger.warning(f"Failed to get status for job {job_id}: {response.status_code if response else 'no response'}")
                
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error polling status for job {job_id}: {str(e)}")
                time.sleep(10)

    def _download_transcript_and_notify(self, job_id, original_file_path):
        """Download transcript and send enhanced notification with Scriberr parameters."""
        url = f"{self.base_url}/api/v1/transcription/{job_id}/transcript"
        headers = {"X-API-Key": self.api_key}
        
        try:
            response, transcript_data = request_json("GET", url, headers=headers)
            if response and response.status_code == 200 and transcript_data:
                # Extract statistics from the transcript
                stats = self._extract_transcript_stats(transcript_data)
                
                # Get model information from job stats
                model_info = {}
                if hasattr(self, 'job_stats') and job_id in self.job_stats:
                    job_stats = self.job_stats[job_id]
                    model_info = {
                        "model_family": job_stats.get("model_family", ""),
                        "model": job_stats.get("model", ""),
                        "diarize_model": job_stats.get("diarize_model", ""),
                        "device": job_stats.get("device", ""),
                        "params": job_stats.get("params", "")
                    }
                    
                    # Get model size information
                    model_details = self._get_model_info(model_info["model_family"], model_info["model"])
                    if model_details:
                        model_info["size"] = model_details.get("size")
                        model_info["model_params"] = model_details.get("params")
                
                # Build enhanced notification with additional parameters
                scriberr_link = f"{self.base_url}/audio/{job_id}"
                file_name = os.path.basename(original_file_path)
                
                # Format additional parameters
                additional_params = []
                
                # Model information section
                if model_info.get("model_family"):
                    additional_params.append(f"🤖 LLM: {model_info['model_family'].upper()}")
                
                if model_info.get("model"):
                    model_display = model_info['model']
                    if model_info.get("size"):
                        model_display += f" ({model_info['size']})"
                    additional_params.append(f"🧠 Model: {model_display}")
                
                if model_info.get("model_params"):
                    additional_params.append(f"📊 Parameters: {model_info['model_params']}")
                
                if model_info.get("diarize_model"):
                    additional_params.append(f"👤 Diarization: {model_info['diarize_model']}")
                
                if model_info.get("device"):
                    device_str = model_info['device'].upper()
                    params_str = model_info.get('params', '')
                    if params_str:
                        additional_params.append(f"⚙️ {device_str} | {params_str}")
                    else:
                        additional_params.append(f"⚙️ {device_str}")
                
                # Transcript statistics section
                if stats["speakers"]:
                    additional_params.append(f"👥 Speakers: {stats['speakers']}")
                
                if stats["word_count"]:
                    additional_params.append(f"📝 Words: {stats['word_count']:,}")
                
                if stats["segments_count"]:
                    additional_params.append(f"📋 Segments: {stats['segments_count']}")
                
                if stats["language"]:
                    lang_code = stats["language"].upper() if isinstance(stats["language"], str) else "AUTO"
                    additional_params.append(f"🌐 Language: {lang_code}")
                
                if stats["audio_duration"]:
                    duration_m, duration_s = divmod(int(stats["audio_duration"]), 60)
                    duration_str = f"{duration_m}m {duration_s}s" if duration_m > 0 else f"{duration_s}s"
                    additional_params.append(f"🎵 Audio Duration: {duration_str}")
                
                # Build the enhanced message
                enhanced_message = f"✅ Transcription completed: {file_name}"
                if additional_params:
                    enhanced_message += "\n" + " | ".join(additional_params)
                enhanced_message += f"\n🔗 View on Scriberr: {scriberr_link}"
                
                logger.info(f"Sending enhanced notification with stats: {stats}")
                logger.info(f"Model info: {model_info}")
                self._send_telegram_notification(enhanced_message)
                
        except Exception as e:
            logger.error(f"Error in enhanced notification: {e}")
        
        # Continue with normal transcript processing
        self._download_transcript(job_id, original_file_path)

    def _download_transcript(self, job_id, original_file_path, existing_transcript_data=None, finalize=False):
        url = f"{self.base_url}/api/v1/transcription/{job_id}/transcript"
        headers = {"X-API-Key": self.api_key}
        is_manual_refresh = original_file_path == "manual_refresh"
        
        try:
            response, transcript_data = request_json("GET", url, headers=headers)
            if response and response.status_code == 200 and transcript_data:
                
                # Clean and merge segments before processing
                logger.info(f"Cleaning transcript segments for job {job_id}")
                transcript_data = self._clean_transcript_data(transcript_data)
                enable_speaker_identification = self.config.get("enable_speaker_identification", True)
                
                if not finalize:
                    # Check if manual renaming has already occurred
                    has_manual_renames = False
                    if hasattr(self, 'main_app'):
                        # Check if we already have manual renames for this job
                        if job_id in self.main_app.active_mappings:
                            has_manual_renames = True
                    
                    if not has_manual_renames:
                        # Identify speakers using OpenRouter (if enabled)
                        if enable_speaker_identification:
                            logger.info(f"Starting speaker identification for job {job_id}")
                            identified_speakers = self._identify_speakers(transcript_data, job_id)
                        else:
                            logger.info(f"Speaker identification disabled for job {job_id}")
                            identified_speakers = None

                            # Still send transcript file to Telegram when speaker identification is disabled
                            self._send_formatted_transcript_to_telegram(transcript_data)
                        
                        if identified_speakers:
                            logger.info(f"Speakers identified: {identified_speakers}")
                            if hasattr(self, 'main_app'):
                                self.main_app.initial_speaker_mappings[job_id] = identified_speakers
                            updated = self._update_scriberr_speakers(job_id, identified_speakers)
                            if updated:
                                # Re-fetch transcript to get updated names
                                time.sleep(2) # Small delay to let Scriberr update
                                response, transcript_data = request_json("GET", url, headers=headers)
                                if response and response.status_code == 200 and transcript_data:
                                    # CRITICAL: Re-clean the data so it's merged and formatted, not raw JSON
                                    logger.info(f"Re-cleaning transcript segments after speaker update for job {job_id}")
                                    transcript_data = self._clean_transcript_data(transcript_data)
                            else:
                                logger.warning(f"Speaker update was not applied for job {job_id}")
                        else:
                            logger.warning(f"No speakers identified for job {job_id}")
                            # Only notify about missing speakers if speaker identification is enabled
                            if enable_speaker_identification:
                                # Get response from OpenRouter for the message
                                file_name = os.path.basename(original_file_path) if not is_manual_refresh else transcript_data.get('title', 'meeting')
                                prompt = f"The transcription job for the file '{file_name}' (ID: {job_id}) completed, but no speakers could be identified from the transcript. Please provide a short, helpful message for the user about this situation."
                                ai_response = self._get_openrouter_response(prompt)
                                scriberr_link = f"{self.base_url}/audio/{job_id}"
                                self._send_telegram_notification(
                                    f"⚠️ No speakers identified for: {file_name}\n\nAI Response: {ai_response}\nView on Scriberr: {scriberr_link}"
                                )

                    # Offer manual speaker assignment based on transcript data UNLESS we are in the finalize step
                    # OR if speaker identification is disabled
                    if enable_speaker_identification:
                        speakers = self._extract_speakers(transcript_data)
                        if speakers:
                            # Re-fetch identified_speakers if we skipped identification but have manual renames
                            # This is a bit complex, but _offer_manual_speaker_assignment handles identified_names=None fine
                            self._offer_manual_speaker_assignment(job_id, speakers, transcript_data, identified_names=(identified_speakers if not has_manual_renames else None))

                # If manual refresh, we don't need to offer assignment again unless we want to allow multiple rounds
                # But we DO need to save the file and trigger on_transcript_ready
                
                if is_manual_refresh and existing_transcript_data:
                    # Use the title from existing data if available
                    transcript_data['title'] = existing_transcript_data.get('title', 'meeting')
                    # Build a readable FINAL filename for the refreshed transcript
                    safe_title = transcript_data.get('title', 'meeting').replace(':', '').replace('/', '_')
                    if not safe_title:
                        safe_title = 'meeting'
                    save_path = f"{safe_title}_FINAL.txt"
                    # Restore meeting_info from the job_id if it was lost during manual refresh
                    if job_id not in self.meeting_info_by_job and 'meeting_info' in existing_transcript_data:
                        self.meeting_info_by_job[job_id] = existing_transcript_data['meeting_info']
                else:
                    save_path = original_file_path

                # Save the human-readable version locally
                transcript_path = self._save_transcript_file(save_path, transcript_data, job_id=job_id)
                
                if hasattr(self, 'main_app'):
                    meeting_info = self.meeting_info_by_job.pop(job_id, None)
                    # If finalize=False but we are skipping interaction (e.g. no Telegram token), we must treat it as final.
                    is_final_call = finalize
                    if not finalize and (not self.config.get("telegram_bot_token") or not enable_speaker_identification):
                        is_final_call = True
                        
                    self.main_app.on_transcript_ready(
                        job_id,
                        original_file_path,
                        transcript_data,
                        transcript_path,
                        meeting_info,
                        is_final=is_final_call
                    )
                
                if is_manual_refresh and finalize:
                    # Send finalization notifications
                    self._send_telegram_notification(f"✅ Finalizing transcript for {transcript_data.get('title', 'meeting')}...")
                    self._send_telegram_notification(f"✅ Transcript finalized and published for {transcript_data.get('title', 'meeting')}")
            else:
                logger.error(f"Failed to download transcript for {job_id}: {response.status_code if response else 'no response'}")
        except Exception as e:
            logger.error(f"Error downloading transcript: {str(e)}")

    def _find_segments(self, data):
        """Recursively find the first segments list in nested transcript data."""
        if isinstance(data, dict):
            segments = data.get("segments")
            if isinstance(segments, list):
                return segments
            for value in data.values():
                found = self._find_segments(value)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_segments(item)
                if found is not None:
                    return found
        return None

    def _get_segment_fields(self, segment):
        speaker = (
            segment.get("speaker")
            or segment.get("speaker_id")
            or segment.get("speaker_label")
            or segment.get("speaker_name")
            or "Unknown_Speaker"
        )
        text = (
            segment.get("text")
            or segment.get("transcript")
            or segment.get("utterance")
            or ""
        ).strip()
        start = (
            segment.get("start")
            if segment.get("start") is not None
            else segment.get("start_time")
            if segment.get("start_time") is not None
            else segment.get("timestamp")
            if segment.get("timestamp") is not None
            else 0.0
        )
        end = (
            segment.get("end")
            if segment.get("end") is not None
            else segment.get("end_time")
            if segment.get("end_time") is not None
            else 0.0
        )
        return speaker, text, start, end

    def _clean_transcript_data(self, transcript_data):
        """
        Parses raw WhisperX transcript data and merges continuous speech 
        by the same speaker into single segments.
        """
        cleaned_segments = []
        try:
            if not transcript_data:
                return transcript_data

            raw_segments = self._find_segments(transcript_data)
            if not raw_segments:
                return transcript_data

            current_block = None
            for segment in raw_segments:
                speaker, text, start, end = self._get_segment_fields(segment)

                if not text:
                    continue

                if current_block is None or current_block['speaker'] != speaker:
                    if current_block:
                        cleaned_segments.append(current_block)
                    current_block = {
                        'speaker': speaker,
                        'start': start,
                        'end': end,
                        'text': text
                    }
                else:
                    current_block['text'] += f" {text}"
                    current_block['end'] = end

            if current_block:
                cleaned_segments.append(current_block)

            # Return a new dict with cleaned segments to maintain structure
            return {**transcript_data, 'segments': cleaned_segments}

        except Exception as e:
            logger.error(f"Error cleaning transcript: {e}")
            return transcript_data

    def _format_timestamp(self, seconds):
        """Converts seconds (float) to [MM:SS] format string."""
        try:
            seconds = int(seconds)
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"[{minutes:02d}:{remaining_seconds:02d}]"
        except (ValueError, TypeError):
            return "[00:00]"

    def _send_formatted_transcript_to_telegram(self, transcript_data):
        """Send a formatted transcript file to Telegram without running speaker identification."""
        try:
            segments = self._find_segments(transcript_data) or []
            if not segments:
                return

            formatted_lines = []
            current_speaker = None
            current_start_time = 0.0
            current_buffer = []

            for segment in segments:
                speaker_id, text, start, _ = self._get_segment_fields(segment)
                if not text:
                    continue

                if current_speaker is not None and speaker_id != current_speaker:
                    time_str = self._format_timestamp(current_start_time)
                    formatted_lines.append(f"{time_str} {current_speaker}: {' '.join(current_buffer)}")
                    current_buffer = []
                    current_start_time = start

                if current_speaker is None:
                    current_start_time = start

                current_speaker = speaker_id
                current_buffer.append(text)

            if current_speaker and current_buffer:
                time_str = self._format_timestamp(current_start_time)
                formatted_lines.append(f"{time_str} {current_speaker}: {' '.join(current_buffer)}")

            full_transcript_text = "\n\n".join(formatted_lines)

            token = self.config.get("telegram_bot_token")
            chat_id = self.config.get("telegram_chat_id")
            if token and chat_id and full_transcript_text:
                file_name = f"transcript_{os.path.basename(transcript_data.get('title', 'meeting'))}.txt"
                url = f"https://api.telegram.org/bot{token}/sendDocument"
                files = {'document': (file_name, full_transcript_text.encode('utf-8'))}
                data = {'chat_id': chat_id, 'caption': f"📄 Transcript for: {os.path.basename(transcript_data.get('title', 'Unknown'))}"}
                request_text("POST", url, data=data, files=files, timeout=15)
                logger.info("Sent formatted transcript to Telegram (speaker identification disabled)")
        except Exception as e:
            logger.error(f"Failed to send transcript to Telegram: {e}")

    def _identify_speakers(self, transcript_data, job_id=None):
        api_key = self.config.get("openrouter_api_key")
        if not api_key:
            return None

        segments = self._find_segments(transcript_data) or []
        if not segments:
            return None

        # Prepare formatted transcript for Telegram and speaker list for LLM
        formatted_lines = []
        speakers = set()
        
        current_speaker = None
        current_start_time = 0.0
        current_buffer = []

        for segment in segments:
            speaker_id, text, start, _ = self._get_segment_fields(segment)

            if not text:
                continue
            
            speakers.add(speaker_id)

            # Check if speaker changed
            if current_speaker is not None and speaker_id != current_speaker:
                time_str = self._format_timestamp(current_start_time)
                full_line = f"{time_str} {current_speaker}: {' '.join(current_buffer)}"
                formatted_lines.append(full_line)
                current_buffer = []
                current_start_time = start

            if current_speaker is None:
                current_start_time = start

            current_speaker = speaker_id
            current_buffer.append(text)

        if current_speaker and current_buffer:
            time_str = self._format_timestamp(current_start_time)
            full_line = f"{time_str} {current_speaker}: {' '.join(current_buffer)}"
            formatted_lines.append(full_line)

        full_transcript_text = "\n\n".join(formatted_lines)
        logger.info(f"Full transcript prepared for OpenRouter: {len(full_transcript_text)} characters")

        # Send the formatted transcript to Telegram for manual review
        try:
            token = self.config.get("telegram_bot_token")
            chat_id = self.config.get("telegram_chat_id")
            if token and chat_id:
                file_name = f"transcript_{os.path.basename(transcript_data.get('title', 'meeting'))}.txt"
                url = f"https://api.telegram.org/bot{token}/sendDocument"
                files = {'document': (file_name, full_transcript_text.encode('utf-8'))}
                data = {'chat_id': chat_id, 'caption': f"📄 Formatted transcript for: {os.path.basename(transcript_data.get('title', 'Unknown'))}"}
                request_text("POST", url, data=data, files=files, timeout=15)
                logger.info("Sent formatted transcript to Telegram")
        except Exception as e:
            logger.error(f"Failed to send transcript to Telegram: {e}")

        # Token Efficiency: Use only first and last 5 minutes for speaker identification
        # Assuming roughly 150 words per minute, 5 mins is ~750 words. 
        # We'll take the first 20 and last 20 segments as a heuristic for "start and end".
        if len(formatted_lines) > 40:
            logger.info(f"Transcript is long ({len(formatted_lines)} segments). Truncating for OpenRouter efficiency.")
            efficient_transcript = (
                "--- START OF TRANSCRIPT ---\n" +
                "\n\n".join(formatted_lines[:20]) +
                "\n\n... [Transcript truncated for token efficiency] ...\n\n" +
                "\n\n".join(formatted_lines[-20:]) +
                "\n--- END OF TRANSCRIPT ---"
            )
        else:
            efficient_transcript = full_transcript_text

        # OpenRouter Prompt (Including efficient transcript for identification)
        prompt = f"""
You are an expert linguistic analyst specialized in transcript diarization. 
Your task is to identify the real names of the speakers in the provided conversation text.

**Input Data:**
Current Speaker Labels: {', '.join(speakers)}

**Conversation (Start and End of Transcript):**
{efficient_transcript}

**Analysis Instructions:**
1. **Self-Identification:** Prioritize explicit introductions (e.g., "Hi, this is Alex").
2. **Direct Address:** Use times where one speaker names another (e.g., "Hello, Amanda"). **CRITICAL:** Ensure you do not confuse the speaker with the person they are talking to.
3. **Context Clues:** If a name is not mentioned, infer roles based on context (e.g., "Tech Support", "Client", "Interviewer").
4. **Unknowns:** If you cannot identify a name or role with confidence, retain the original label (e.g., "SPEAKER_00").

**Output Format:**
Return **ONLY** a valid JSON object. Do not output markdown backticks, explanations, or thinking.
Format:
{{
  "SPEAKER_00": "Real Name or Role",
  "SPEAKER_01": "Real Name or Role"
}}
"""

        try:
            logger.info(f"Sending full speaker identification request to OpenRouter for {len(segments)} segments")
            logger.debug(f"Prompt snippet: {prompt[:500]}...")
            self._send_telegram_notification(f"🔍 Identifying speakers for: {os.path.basename(transcript_data.get('title', 'Unknown'))}")
            response, result = request_json(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/your-username/sync-meeting-name-with-google",
                    "X-Title": "Auto-Meeting Video Renamer"
                },
                json_body={
                    "model": self.config.get("openrouter_model", "google/gemini-2.0-flash-001"),
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            if response and response.status_code == 200 and result:
                content = result['choices'][0]['message']['content']
                logger.info(f"OpenRouter response: {content}")
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    names = json.loads(match.group())
                    # Just return names; the calling function (_download_transcript) will handle the UI display
                    return names
                else:
                    logger.warning(f"Could not find JSON in OpenRouter response: {content}")
            else:
                logger.error(f"OpenRouter API error: {response.status_code if response else 'no response'} - {response.text if response else ''}")
                self._send_telegram_notification(f"❌ OpenRouter error: {response.status_code if response else 'no response'}")
        except Exception as e:
            logger.error(f"Error identifying speakers: {str(e)}")

        # If we reach here, identification failed or we want to offer manual assignment
        return None

    def _extract_speakers(self, transcript_data):
        segments = self._find_segments(transcript_data) or []
        speakers = set()
        for segment in segments:
            speaker_id, text, _, _ = self._get_segment_fields(segment)
            if text:
                speakers.add(speaker_id)
        return speakers

    def _offer_manual_speaker_assignment(self, job_id, speakers, transcript_data, identified_names=None):
        """Sends a message to Telegram with buttons to manually assign speaker names."""
        if not speakers:
            return

        file_name = os.path.basename(transcript_data.get('title', 'Unknown'))
        
        # Merge identified_names with any active manual mappings from the session
        # Priority: Default (SPEAKER_XX) < AI Initial Guesses < Manual Overrides
        display_map = {s: s for s in speakers}
        if hasattr(self, 'main_app'):
            # Apply AI Initial Guesses
            if job_id in self.main_app.initial_speaker_mappings:
                display_map.update(self.main_app.initial_speaker_mappings[job_id])
            # Apply Manual Overrides (Highest Priority)
            if job_id in self.main_app.active_mappings:
                display_map.update(self.main_app.active_mappings[job_id])
        elif identified_names:
            display_map.update(identified_names)
        
        if (hasattr(self, 'main_app') and (job_id in self.main_app.initial_speaker_mappings or job_id in self.main_app.active_mappings)) or identified_names:
            message = f"✅ Speakers identified for: {file_name}\n\nTap a speaker below to correct their name:"
        else:
            message = f"Manual Speaker Assignment for: {file_name}\n\nSelect a speaker to rename:"
        
        keyboard = []
        row = []
        sorted_speakers = sorted(list(speakers))
        for speaker in sorted_speakers:
            display_name = display_map.get(speaker, speaker)
            cb_id = f"spk_{int(time.time())}_{speaker}"
            if hasattr(self, 'main_app'):
                self.main_app.callback_map[cb_id] = {
                    "action": "assign_speaker",
                    "job_id": job_id,
                    "speaker_id": speaker,
                    "file_name": file_name,
                    "current_name": display_name,
                    "all_speakers": sorted(list(speakers))
                }
            # Requirement 5: Clearer Labels (Label + Current Name)
            button_text = f"👤 {speaker}: {display_name}" if speaker != display_name else f"👤 {speaker}"
            row.append({"text": button_text, "callback_data": cb_id})
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Requirement 5: Handling Identity Swaps
        if len(sorted_speakers) >= 2:
            swap_cb_id = f"swap_{int(time.time())}"
            if hasattr(self, 'main_app'):
                self.main_app.callback_map[swap_cb_id] = {
                    "action": "offer_swap",
                    "job_id": job_id,
                    "speakers": sorted_speakers,
                    "display_map": display_map,
                    "file_name": file_name
                }
            keyboard.append([{"text": "🔄 Swap Two Speakers", "callback_data": swap_cb_id}])

        # Add a "Done" button
        done_cb_id = f"spk_done_{int(time.time())}"
        if hasattr(self, 'main_app'):
            self.main_app.callback_map[done_cb_id] = {
                "action": "speaker_assignment_done",
                "job_id": job_id,
                "file_name": file_name,
                "transcript_data": {**transcript_data, "meeting_info": self.meeting_info_by_job.get(job_id)} # Store for re-processing
            }
            self.main_app.callback_persistence.save(self.main_app.callback_map)
        keyboard.append([{"text": "✅ Finalize Transcript", "callback_data": done_cb_id}])

        self._send_telegram_notification(message, reply_markup={"inline_keyboard": keyboard})

    def _send_telegram_notification(self, message, reply_markup=None):
        token = self.config.get("telegram_bot_token")
        chat_id = self.config.get("telegram_chat_id")
        if not token or not chat_id:
            logger.warning("Telegram token or chat_id missing in config")
            return None

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            logger.info(f"Sending Telegram message: {message[:50]}...")
            response, payload = request_json("POST", url, json_body=payload, timeout=10)
            if response and response.status_code != 200:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return payload
        except Exception as e:
            logger.error(f"Failed to send telegram notification: {str(e)}")
            return None

    def _update_scriberr_speakers(self, job_id, speaker_map):
        url = f"{self.base_url}/api/v1/transcription/{job_id}/speakers"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        mappings = []
        # Standardize input to a list of mappings
        if isinstance(speaker_map, dict):
            for original, custom in speaker_map.items():
                mappings.append({
                    "original_speaker": str(original).strip(),
                    "custom_name": str(custom).strip()
                })
        elif isinstance(speaker_map, list):
            for entry in speaker_map:
                if isinstance(entry, dict):
                    original = entry.get("original_speaker")
                    custom = entry.get("custom_name")
                    if original is not None and custom is not None:
                        mappings.append({
                            "original_speaker": str(original).strip(),
                            "custom_name": str(custom).strip()
                        })
        else:
            logger.warning(f"Unsupported speaker map type: {type(speaker_map)}")
            return False

        if not mappings:
            logger.warning("No valid speaker mappings to update")
            return False

        try:
            logger.debug(f"Updating speakers for job {job_id} with payload: {mappings}")
            # Standardize to wrapped payload as per Scriberr API expectations
            response, payload = request_json("POST", url, headers=headers, json_body={"mappings": mappings})
            if response and response.status_code == 200:
                logger.info(f"Successfully updated speaker names for job {job_id}")
                return True
            else:
                response_text = response.text if response is not None else ""
                logger.error(f"Failed to update speakers: {response.status_code if response else 'no response'} - {response_text}")
        except Exception as e:
            logger.error(f"Error updating Scriberr speakers: {str(e)}")
        return False

    def _save_transcript_file(self, original_file_path, transcript_data, job_id=None):
        """
        Saves the transcript to a .txt file, merging continuous speech 
        by the same speaker into single blocks with timestamps.
        """
        try:
            file_path_obj = Path(original_file_path)
            transcribed_folder = self.config.get("transcribed_folder")
            if transcribed_folder:
                output_dir = Path(transcribed_folder)
                output_dir.mkdir(parents=True, exist_ok=True)
                transcript_path = output_dir / f"{file_path_obj.stem}_transcript.txt"
            else:
                transcript_path = file_path_obj.parent / f"{file_path_obj.stem}_transcript.txt"
            
            segments = self._find_segments(transcript_data) or []
            if not segments:
                transcript_text = None
                if isinstance(transcript_data, dict):
                    transcript_text = (
                        transcript_data.get("text")
                        or transcript_data.get("transcript")
                        or transcript_data.get("full_text")
                    )
                    if isinstance(transcript_text, dict):
                        transcript_text = transcript_text.get("text")

                if transcript_text:
                    with open(transcript_path, 'w', encoding='utf-8') as f:
                        f.write(str(transcript_text))
                return str(transcript_path)

            # Get speaker mappings if available
            mapping = {}
            if job_id and hasattr(self, 'main_app'):
                mapping = self.main_app.active_mappings.get(job_id, {})

            cleaned_lines = []
            current_speaker = None
            current_start_time = 0.0
            current_buffer = []

            for segment in segments:
                speaker, text, start, _ = self._get_segment_fields(segment)

                if not text:
                    continue

                # Apply mapping if exists
                display_speaker = mapping.get(speaker, speaker)

                # Check if speaker changed
                if current_speaker is not None and display_speaker != current_speaker:
                    # Save previous block
                    mins, secs = divmod(int(current_start_time), 60)
                    time_str = f"[{mins:02d}:{secs:02d}]"
                    full_line = f"{time_str} {current_speaker}: {' '.join(current_buffer)}"
                    cleaned_lines.append(full_line)
                    
                    # Reset for new block
                    current_buffer = []
                    current_start_time = start

                # If it's the very first segment
                if current_speaker is None:
                    current_start_time = start

                current_speaker = display_speaker
                current_buffer.append(text)

            # Flush final buffer
            if current_speaker and current_buffer:
                mins, secs = divmod(int(current_start_time), 60)
                time_str = f"[{mins:02d}:{secs:02d}]"
                full_line = f"{time_str} {current_speaker}: {' '.join(current_buffer)}"
                cleaned_lines.append(full_line)

            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(cleaned_lines))
                
            logger.info(f"Transcript saved to: {transcript_path}")
            return str(transcript_path)
        except Exception as e:
            logger.error(f"Failed to save transcript: {str(e)}")
            return None

    def _append_to_log(self, file_path, action, status, response_content):
        # ...existing code...
        try:
            file_path_obj = Path(file_path)
            log_path = file_path_obj.parent / f"{file_path_obj.name}_upload.log"
            log_data = {}
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            log_data[action] = {"status": status, "response": response_content, "timestamp": str(time.time())}
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def _save_log(self, file_path, status, response_content):
        # ...existing code...
        try:
            file_path_obj = Path(file_path)
            log_path = file_path_obj.parent / f"{file_path_obj.name}_upload.log"
            log_data = {"file_name": file_path_obj.name, "status": status, "response": response_content}
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def _get_model_info(self, model_family, model_name):
        """Get detailed model information including size."""
        model_sizes = {
            "whisper": {
                "tiny": {"size": "39MB", "params": "39M"},
                "base": {"size": "140MB", "params": "74M"},
                "small": {"size": "461MB", "params": "244M"},
                "medium": {"size": "1.5GB", "params": "769M"},
                "large": {"size": "2.9GB", "params": "1.5B"},
                "large-v3": {"size": "2.9GB", "params": "1.5B"},
                "large-v2": {"size": "2.9GB", "params": "1.5B"},
                "large-v1": {"size": "2.9GB", "params": "1.5B"}
            }
        }
        
        try:
            if model_family and model_family in model_sizes:
                if model_name and model_name in model_sizes[model_family]:
                    return model_sizes[model_family][model_name]
        except Exception:
            pass
        
        return None

    def _extract_transcript_stats(self, transcript_data):
        """Extract additional statistics from transcript data for better notifications."""
        stats = {
            "word_count": 0,
            "speakers": set(),
            "segments_count": 0,
            "language": None,
            "audio_duration": None
        }
        
        try:
            # Get segments
            segments = self._find_segments(transcript_data)
            if segments:
                stats["segments_count"] = len(segments)
                
                for segment in segments:
                    # Count words
                    text = segment.get("text") or segment.get("transcript") or segment.get("utterance") or ""
                    stats["word_count"] += len(text.split())
                    
                    # Collect unique speakers
                    speaker = (
                        segment.get("speaker")
                        or segment.get("speaker_id")
                        or segment.get("speaker_label")
                        or segment.get("speaker_name")
                    )
                    if speaker:
                        stats["speakers"].add(speaker)
                    
                    # Get audio duration from last segment
                    end = segment.get("end") or segment.get("end_time") or 0
                    if end > (stats["audio_duration"] or 0):
                        stats["audio_duration"] = end
            
            # Get language
            if "language" in transcript_data:
                stats["language"] = transcript_data["language"]
            elif "language_code" in transcript_data:
                stats["language"] = transcript_data["language_code"]
            
            # Convert speakers set to count
            speaker_count = len(stats["speakers"])
            stats["speakers"] = speaker_count
            
        except Exception as e:
            logger.warning(f"Error extracting transcript stats: {e}")
        
        return stats

    def _get_openrouter_response(self, prompt):
        api_key = self.config.get("openrouter_api_key")
        if not api_key:
            return "OpenRouter API key missing."

        try:
            response, result = request_json(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/your-username/sync-meeting-name-with-google",
                    "X-Title": "Auto-Meeting Video Renamer"
                },
                json_body={
                    "model": self.config.get("openrouter_model", "google/gemini-2.0-flash-001"),
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            if response and response.status_code == 200 and result:
                return result['choices'][0]['message']['content']
            return f"Error from OpenRouter: {response.status_code if response else 'no response'}"
        except Exception as e:
            return f"Exception during OpenRouter call: {str(e)}"
