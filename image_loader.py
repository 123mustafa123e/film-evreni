from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from http_utils import get_content
import logging


class ImageLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.finished.connect(self.deleteLater)  # Thread bitince self'i sil

    def run(self):
        try:
            data = get_content(self.url, timeout=10)
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.loaded.emit(pixmap)
        except Exception as e:
            logging.exception("Resim yüklenemedi: %s", e)
            self.error.emit(str(e))
