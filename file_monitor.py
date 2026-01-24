"""
File system monitoring module
"""

import os
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class VideoFileEventHandler(FileSystemEventHandler):
    """Handles file system events for video files"""
    
    def __init__(self, video_extensions, on_video_created_callback):
        """
        Initialize the event handler
        
        Args:
            video_extensions: List of video file extensions to monitor
            on_video_created_callback: Callback function when a video file is created
        """
        self.video_extensions = video_extensions
        self.on_video_created = on_video_created_callback
    
    def on_created(self, event):
        """Handle file creation event"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if it's a video file
        if file_ext in self.video_extensions:
            logger.info(f"New video file detected: {file_path}")
            # Call the callback with the file path
            if self.on_video_created:
                self.on_video_created(file_path)
    
    def on_modified(self, event):
        """Handle file modification event"""
        # We primarily care about creation, but this could be useful
        pass

class FileMonitor:
    """Monitors a directory for new video files"""
    
    def __init__(self, watch_folder, video_extensions, on_video_created_callback):
        """
        Initialize the file monitor
        
        Args:
            watch_folder: Path to the folder to monitor
            video_extensions: List of video file extensions
            on_video_created_callback: Callback function when video is created
        """
        self.watch_folder = watch_folder
        self.video_extensions = video_extensions
        self.observer = None
        self.event_handler = VideoFileEventHandler(video_extensions, on_video_created_callback)
    
    def start(self):
        """Start monitoring the folder"""
        if not os.path.exists(self.watch_folder):
            logger.error(f"Watch folder does not exist: {self.watch_folder}")
            raise ValueError(f"Watch folder does not exist: {self.watch_folder}")
        
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.watch_folder, recursive=False)
        self.observer.start()
        logger.info(f"File monitor started for: {self.watch_folder}")
    
    def stop(self):
        """Stop monitoring the folder"""
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=10)
                logger.info("File monitor stopped")
            except Exception as e:
                logger.warning(f"Error stopping observer: {e}")
                self.observer = None
    
    def is_alive(self):
        """Check if the monitor is running"""
        return self.observer and self.observer.is_alive()
