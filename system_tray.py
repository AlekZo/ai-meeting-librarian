import threading
import logging
import os
import sys
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

logger = logging.getLogger(__name__)

class SystemTrayIcon:
    def __init__(self, on_quit_callback):
        self.on_quit = on_quit_callback
        self.icon = None
        self.status = "Starting..."
        self._thread = None

    def _create_image(self, color):
        # Generate a simple 64x64 icon with a colored circle
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), (255, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill=color, outline="black")
        return image

    def _setup_menu(self):
        return pystray.Menu(
            item(lambda text: f"Status: {self.status}", lambda: None, enabled=False),
            item('Quit', self._on_quit_clicked)
        )

    def _on_quit_clicked(self, icon, item):
        logger.info("Quit clicked in system tray")
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def update_status(self, status, color="green"):
        self.status = status
        if self.icon:
            self.icon.icon = self._create_image(color)
            # Force menu refresh by updating title if needed, 
            # but pystray handles dynamic labels via lambdas in _setup_menu

    def run(self):
        self.icon = pystray.Icon(
            "AutoMeetingVideoRenamer",
            self._create_image("yellow"),
            "Auto-Meeting Video Renamer",
            self._setup_menu()
        )
        self.icon.run()

    def start(self):
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logger.info("System tray thread started")

    def stop(self):
        if self.icon:
            self.icon.stop()
