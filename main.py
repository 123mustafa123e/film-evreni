import sys
import os
import requests
import sqlite3
import json
import logging
import bcrypt
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QScrollArea, 
                             QGridLayout, QFrame, QDialog, QStackedWidget, QMessageBox,
                             QComboBox, QSpinBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap
import webbrowser

from ai_recommendation import AIRecommendationWidget
from http_utils import get_json
from image_loader import ImageLoader

load_dotenv()
logging.basicConfig(filename="app.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s:%(message)s")

# --- AYARLAR ---
import base64
API_KEY = os.getenv("TMDB_API_KEY")
if not API_KEY:
    try:
        API_KEY = base64.b64decode("YzJmMGNkN2YwNTQ3YjBlM2IzYTFkYjFhZmIzODI2YjM=").decode("utf-8")
    except Exception:
        API_KEY = ""
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Son izlenen film geçmişini tutacak tablo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
            username TEXT PRIMARY KEY,
            movie_id INTEGER NOT NULL,
            movie_title TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            username TEXT,
            movie_id INTEGER,
            movie_title TEXT,
            movie_data TEXT,
            UNIQUE(username, movie_id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    # bcrypt kullanılarak güvenli hash (tuz otomatik)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giriş Yap / Kayıt Ol")
        self.setFixedSize(400, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f0f13;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                padding: 12px;
                background: #1c1c24;
                border: 2px solid #2a2a35;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #e50914;
            }
            QPushButton {
                background: #e50914;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: #f40612;
            }
            QPushButton#switchBtn {
                background: transparent;
                color: #aaaaaa;
                text-decoration: underline;
                font-weight: normal;
                margin-top: 0px;
            }
            QPushButton#switchBtn:hover {
                color: white;
            }
        """)

        self.stacked_widget = QStackedWidget()
        
        # --- Giriş Formu ---
        self.login_widget = QWidget()
        login_layout = QVBoxLayout(self.login_widget)
        login_layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("🎬 Film Evreni")
        title.setStyleSheet("font-size: 28px; font-weight: 900; color: #e50914; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(title)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Kullanıcı Adı")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Şifre")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        login_btn = QPushButton("Giriş Yap")
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self.handle_login)
        
        switch_to_register_btn = QPushButton("Hesabın yok mu? Kayıt Ol")
        switch_to_register_btn.setObjectName("switchBtn")
        switch_to_register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_to_register_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        login_layout.addWidget(self.login_username)
        login_layout.addWidget(self.login_password)
        login_layout.addWidget(login_btn)
        login_layout.addWidget(switch_to_register_btn)
        login_layout.addStretch()

        # --- Kayıt Formu ---
        self.register_widget = QWidget()
        register_layout = QVBoxLayout(self.register_widget)
        register_layout.setContentsMargins(30, 30, 30, 30)
        
        reg_title = QLabel("Yeni Hesap")
        reg_title.setStyleSheet("font-size: 28px; font-weight: 900; color: #e50914; margin-bottom: 20px;")
        reg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_layout.addWidget(reg_title)

        self.reg_fullname = QLineEdit()
        self.reg_fullname.setPlaceholderText("Ad Soyad")
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Kullanıcı Adı")
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Şifre")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        register_btn = QPushButton("Kayıt Ol")
        register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        register_btn.clicked.connect(self.handle_register)

        switch_to_login_btn = QPushButton("Zaten hesabın var mı? Giriş Yap")
        switch_to_login_btn.setObjectName("switchBtn")
        switch_to_login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_to_login_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        register_layout.addWidget(self.reg_fullname)
        register_layout.addWidget(self.reg_username)
        register_layout.addWidget(self.reg_password)
        register_layout.addWidget(register_btn)
        register_layout.addWidget(switch_to_login_btn)
        register_layout.addStretch()

        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.register_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)
        
        self.logged_in_user = None
        self.logged_in_username = None

    def handle_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen tüm alanları doldurun!")
            return
            
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT fullname, password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            fullname, hashed_pass = result
            try:
                if bcrypt.checkpw(password.encode(), hashed_pass.encode()):
                    self.logged_in_user = fullname
                    self.logged_in_username = username
                    self.accept()
                else:
                    QMessageBox.warning(self, "Hata", "Yanlış şifre!")
            except Exception:
                # Eğer veritabanında eski SHA256 hash'i varsa kontrollü fallback (isteğe bağlı)
                QMessageBox.warning(self, "Hata", "Giriş doğrulanamadı. Lütfen şifrenizi sıfırlayın.")
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı bulunamadı!")

    def handle_register(self):
        fullname = self.reg_fullname.text().strip()
        username = self.reg_username.text().strip()
        password = self.reg_password.text().strip()
        
        if not fullname or not username or not password:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen tüm alanları doldurun!")
            return
            
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            QMessageBox.warning(self, "Hata", "Bu kullanıcı adı zaten alınmış!")
            conn.close()
            return

        hashed_pass = hash_password(password)
        cursor.execute("INSERT INTO users (fullname, username, password) VALUES (?, ?, ?)", 
                       (fullname, username, hashed_pass))
        conn.commit()
        conn.close()
        
        QMessageBox.information(self, "Başarılı", "Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
        self.stacked_widget.setCurrentIndex(0)
        self.login_username.setText(username)
        self.login_password.clear()

class MovieCard(QFrame):
    """
    Özelleştirilmiş Film Kartı Sınıfı.
    Normalde afiş, isim ve butonu gösterir.
    Fareyle üzerine gelindiğinde (hover) yarı saydam siyah bir katman içinde
    filmin puanı ve kısa bir özetini gösterir.
    """
    def __init__(self, movie, watch_callback, watchlist_callback, is_in_watchlist=False, parent=None):
        super().__init__(parent)
        self.movie = movie
        self.watch_callback = watch_callback
        self.watchlist_callback = watchlist_callback
        self.loader = None  # ImageLoader reference for cleanup
        self.setObjectName("movieCard")
        self.setFixedSize(230, 420)
        
        # --- Normal Görünüm ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if movie.get('poster_path'):
            # placeholder
            self.img_label.setText("Yükleniyor...")
            self.loader = ImageLoader(f"{IMAGE_URL}{movie['poster_path']}", parent=self)
            def on_loaded(pixmap):
                self.img_label.setPixmap(pixmap.scaled(200, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.img_label.setFixedSize(200, 300)

            def on_err(msg):
                logging.warning("Poster yüklenemedi: %s", movie.get('poster_path'))
                self.img_label.setText("Afiş Yüklenemedi")
                self.img_label.setStyleSheet("background: #333; color: white; border-radius: 8px;")
                self.img_label.setFixedSize(200, 300)

            self.loader.loaded.connect(on_loaded)
            self.loader.error.connect(on_err)
            self.loader.start()
        else:
            self.img_label.setText("Afiş Yok")
            self.img_label.setStyleSheet("background: #333; color: white; border-radius: 8px;")
            self.img_label.setFixedSize(200, 300)
            
        title_label = QLabel(movie['title'])
        title_label.setObjectName("movieTitle")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        watch_btn = QPushButton("▶ Şimdi İzle")
        watch_btn.setObjectName("watchBtn")
        watch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        watch_btn.clicked.connect(lambda checked, m=movie: self.watch_callback(m))

        self.main_layout.addWidget(self.img_label)
        self.main_layout.addWidget(title_label)
        self.main_layout.addStretch()
        self.main_layout.addWidget(watch_btn)

        # --- Hover Overlay ---
        self.overlay = QWidget(self)
        self.overlay.resize(230, 420)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 230); border-radius: 15px;") 
        self.overlay.hide()

        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(8)

        # Puan
        rating = movie.get('vote_average', 0)
        rating_lbl = QLabel(f"⭐ {rating:.1f}/10")
        rating_lbl.setStyleSheet("color: #ffd700; font-size: 14px; font-weight: bold; background: transparent;")
        overlay_layout.addWidget(rating_lbl)

        # Başlık
        ov_title = QLabel(movie['title'])
        ov_title.setWordWrap(True)
        ov_title.setStyleSheet("color: white; font-size: 16px; font-weight: 900; background: transparent;")
        overlay_layout.addWidget(ov_title)

        # Kısa Özet (Daha uzun)
        overview_text = movie.get('overview', 'Özet bulunmuyor.')
        if len(overview_text) > 230:
            overview_text = overview_text[:227] + "..."
            
        overview_lbl = QLabel(overview_text)
        overview_lbl.setWordWrap(True)
        overview_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        overview_lbl.setStyleSheet("color: #dddddd; font-size: 13px; background: transparent;")
        overlay_layout.addWidget(overview_lbl)
        
        overlay_layout.addStretch()
        
        watch_btn_overlay = QPushButton("▶ Filmi Başlat")
        watch_btn_overlay.setObjectName("watchBtn")
        watch_btn_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        watch_btn_overlay.clicked.connect(lambda checked, m=movie: self.watch_callback(m))
        overlay_layout.addWidget(watch_btn_overlay)

        self.watchlist_btn = QPushButton("➖ Listeden Çıkar" if is_in_watchlist else "📌 Listeme Ekle")
        self.watchlist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: 2px solid white;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:hover {
                background: white;
                color: black;
            }
        """)
        self.watchlist_btn.clicked.connect(lambda checked, m=movie: self.watchlist_callback(m, self.watchlist_btn))
        overlay_layout.addWidget(self.watchlist_btn)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.overlay.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.overlay.hide()

    def cleanup(self):
        """Clean up any running threads before widget destruction."""
        try:
            if self.loader and isinstance(self.loader, ImageLoader):
                if self.loader.isRunning():
                    self.loader.quit()
                    self.loader.wait(timeout=1000)
        except Exception as e:
            logging.exception("MovieCard cleanup: %s", e)


class MovieApp(QWidget):
    def __init__(self, username="user", user_fullname="Kullanıcı"):
        super().__init__()
        self.username = username
        self.user_fullname = user_fullname
        self.watched_genres = []
        self.genre_map: dict[int, str] = {}
        
        self.init_ui()
        self.load_genres()
        self.load_movies(f"{BASE_URL}/movie/popular")
        
        # Son izlenen filmi kontrol et
        self.check_last_watched()

    def init_ui(self):
        self.setWindowTitle("Film İzle & Öneri")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f13; 
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                padding: 12px 20px;
                background: #1c1c24;
                border: 2px solid #2a2a35;
                border-radius: 20px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #e50914;
            }
            QPushButton#searchBtn, QPushButton#homeBtn {
                background: #e50914;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#searchBtn:hover, QPushButton#homeBtn:hover {
                background: #f40612;
            }
            QPushButton#homeBtn {
                background: #2a2a35;
            }
            QPushButton#homeBtn:hover {
                background: #3a3a45;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #333;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555;
            }
            QFrame#movieCard {
                background: #1a1a24;
                border-radius: 15px;
            }
            QFrame#movieCard:hover {
                background: #252533;
                border: 1px solid #e50914;
            }
            QPushButton#watchBtn {
                background: #e50914;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton#watchBtn:hover {
                background: #f40612;
            }
            QLabel#movieTitle {
                font-size: 15px;
                font-weight: bold;
            }
            /* Yan Menü Stilleri */
            QFrame#sidebar {
                background-color: #15151c;
                border-right: 1px solid #2a2a35;
            }
            QPushButton.genreBtn {
                background-color: transparent;
                color: #bbbbbb;
                text-align: left;
                padding: 12px 20px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                margin: 2px 10px;
            }
            QPushButton.genreBtn:hover {
                background-color: #2a2a35;
                color: white;
            }
            QPushButton.genreBtn:checked {
                background-color: #e50914;
                color: white;
            }
        """)

        # --- Ana Düzen ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Yan Menü (Sidebar) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMaximumWidth(0)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)
        
        self.watchlist_side_btn = QPushButton("📌 İzleme Listem")
        self.watchlist_side_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                text-align: left;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                margin: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                color: white;
            }
        """)
        self.watchlist_side_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_side_btn.clicked.connect(self.show_watchlist)
        sidebar_layout.addWidget(self.watchlist_side_btn)

        # Filtreleme
        filter_title = QLabel("Gelişmiş Filtreleme")
        filter_title.setStyleSheet("font-size: 20px; font-weight: 900; color: white; padding-left: 20px; margin-top: 15px; margin-bottom: 10px;")
        sidebar_layout.addWidget(filter_title)

        # Kategori
        genre_layout = QHBoxLayout()
        genre_layout.setContentsMargins(15, 5, 15, 0)
        genre_label = QLabel("Kategori:")
        genre_label.setStyleSheet("color: white; font-weight: bold;")
        self.genre_cb = QComboBox()
        self.genre_cb.addItem("Tümü", None)
        self.genre_cb.setStyleSheet("color: white; background: #1c1c24; border: 1px solid #2a2a35; padding: 5px;")
        self.genre_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        genre_layout.addWidget(genre_label)
        genre_layout.addWidget(self.genre_cb)
        sidebar_layout.addLayout(genre_layout)

        # Yıl
        year_layout = QHBoxLayout()
        year_layout.setContentsMargins(15, 5, 15, 0)
        year_label = QLabel("Yıl:")
        year_label.setStyleSheet("color: white; font-weight: bold;")
        self.year_cb = QComboBox()
        self.year_cb.addItems(["Tümü", "2024", "2023", "2022", "2021", "2020", "2010-2019", "2000-2009", "1990-1999", "1990 Öncesi"])
        self.year_cb.setStyleSheet("color: white; background: #1c1c24; border: 1px solid #2a2a35; padding: 5px;")
        self.year_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        year_layout.addWidget(year_label)
        year_layout.addWidget(self.year_cb)
        sidebar_layout.addLayout(year_layout)

        # Puan
        rating_layout = QHBoxLayout()
        rating_layout.setContentsMargins(15, 5, 15, 0)
        rating_label = QLabel("Min Puan:")
        rating_label.setStyleSheet("color: white; font-weight: bold;")
        self.rating_cb = QComboBox()
        self.rating_cb.addItems(["Tümü", "9+ Puan", "8+ Puan", "7+ Puan", "6+ Puan", "5+ Puan"])
        self.rating_cb.setStyleSheet("color: white; background: #1c1c24; border: 1px solid #2a2a35; padding: 5px;")
        self.rating_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        rating_layout.addWidget(rating_label)
        rating_layout.addWidget(self.rating_cb)
        sidebar_layout.addLayout(rating_layout)

        # Filtrele Butonu
        self.filter_apply_btn = QPushButton("Filtrele")
        self.filter_apply_btn.setStyleSheet("""
            QPushButton {
                background: #e50914; color: white; font-weight: bold; border-radius: 8px; padding: 10px; margin: 25px 15px 5px 15px;
            }
            QPushButton:hover { background: #f40612; }
        """)
        self.filter_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filter_apply_btn.clicked.connect(self.apply_filters)
        sidebar_layout.addWidget(self.filter_apply_btn)
        
        sidebar_title = QLabel("Kategoriler")
        sidebar_title.setStyleSheet("font-size: 20px; font-weight: 900; color: white; padding-left: 20px; margin-top: 15px; margin-bottom: 10px;")
        sidebar_layout.addWidget(sidebar_title)
        
        self.genre_scroll = QScrollArea()
        self.genre_scroll.setWidgetResizable(True)
        self.genre_container = QWidget()
        self.genre_layout = QVBoxLayout(self.genre_container)
        self.genre_layout.setContentsMargins(0, 0, 0, 0)
        self.genre_layout.setSpacing(2)
        
        self.genre_scroll.setWidget(self.genre_container)
        sidebar_layout.addWidget(self.genre_scroll)
        self.genre_layout.addStretch()

        main_layout.addWidget(self.sidebar)

        # --- Sağ Taraf (Ana İçerik) ---
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Üst Kısım
        top_layout = QHBoxLayout()
        
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedSize(45, 45)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1c1c24;
                color: white;
                border: 2px solid #2a2a35;
                border-radius: 10px;
                font-size: 22px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border: 2px solid #e50914;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        top_layout.addWidget(self.toggle_btn)
        
        self.title_label = QLabel("🎬 Film Evreni")
        self.title_label.setStyleSheet("font-size: 32px; font-weight: 900; color: #e50914; margin-left: 10px;")
        top_layout.addWidget(self.title_label)
        
        top_layout.addStretch()
        
        welcome_label = QLabel(f"Hoşgeldin, {self.user_fullname}")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaaaaa;")
        top_layout.addWidget(welcome_label)
        
        layout.addLayout(top_layout)

        # --- Kaldığın Yerden Devam Et Banner ---
        self.continue_banner = QFrame()
        self.continue_banner.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e50914, stop:1 #8b0000);
                border-radius: 12px;
            }
        """)
        self.continue_banner.hide()
        banner_layout = QHBoxLayout(self.continue_banner)
        banner_layout.setContentsMargins(20, 15, 20, 15)
        
        banner_info_layout = QVBoxLayout()
        banner_header = QLabel("En Son İzlediğiniz Film")
        banner_header.setStyleSheet("color: #ffcccc; font-size: 13px; font-weight: bold; background: transparent;")
        
        self.continue_title_lbl = QLabel("Film Adı")
        self.continue_title_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: 900; background: transparent;")
        
        banner_info_layout.addWidget(banner_header)
        banner_info_layout.addWidget(self.continue_title_lbl)
        
        resume_btn = QPushButton("▶ Devam Et")
        resume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        resume_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #e50914;
                border: none;
                border-radius: 20px;
                padding: 10px 25px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        resume_btn.clicked.connect(self.resume_movie)
        
        banner_layout.addLayout(banner_info_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(resume_btn)
        
        layout.addWidget(self.continue_banner)

        # Arama Alanı
        search_layout = QHBoxLayout()
        search_layout.setSpacing(15)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Film ismi yazın veya yeni filmler keşfedin...")
        self.search_input.returnPressed.connect(self.search_movie)
        
        search_btn = QPushButton("Ara")
        search_btn.setObjectName("searchBtn")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self.search_movie)
        
        self.home_btn = QPushButton("Ana Ekran")
        self.home_btn.setObjectName("homeBtn")
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.clicked.connect(self.go_home)
        self.home_btn.hide()
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(self.home_btn)
        layout.addLayout(search_layout)

        # Film Listesi (Scroll)
        self.scroll = QScrollArea()
        self.container = QWidget()
        self.grid = QGridLayout()
        self.grid.setSpacing(25)
        self.grid.setContentsMargins(10, 20, 10, 20)
        self.container.setLayout(self.grid)
        self.scroll.setWidget(self.container)
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        layout.addWidget(self.scroll)

        main_layout.addWidget(content_widget)

        # --- Yüzen (Floating) Ufak Kutu AI Asistan Paneli ---
        self.ai_popup = QFrame(self)
        self.ai_popup.setObjectName("aiPopup")
        self.ai_popup.setFixedSize(350, 480) # Ufak boyutlu bir kutu
        self.ai_popup.setStyleSheet("""
            QFrame#aiPopup {
                background-color: #12121a;
                border: 2px solid #7c3aed;
                border-radius: 12px;
            }
        """)
        self.ai_popup.hide() # Başlangıçta kapalı
        
        # Gölge eklemek için
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 5)
        self.ai_popup.setGraphicsEffect(shadow)

        ai_layout = QVBoxLayout(self.ai_popup)
        ai_layout.setContentsMargins(5, 5, 5, 5)
        
        self.ai_panel = AIRecommendationWidget()
        self.ai_panel.film_search_requested.connect(self._ai_search)
        ai_layout.addWidget(self.ai_panel)
        
        # Yüzen Buton (Floating Button)
        self.ai_toggle_btn = QPushButton("✨ Ruh Hali Asistanı", self)
        self.ai_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed; 
                color: white; 
                border-radius: 20px; 
                font-weight: bold; 
                font-size: 13px;
                border: 2px solid #5b21b6;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
        """)
        self.ai_toggle_btn.resize(160, 40)
        self.ai_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_toggle_btn.clicked.connect(self.toggle_ai_popup)
        
        # Animasyon Ayarları
        self.animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)

    def on_scroll(self, value):
        try:
            scrollbar = self.scroll.verticalScrollBar()
            if value == scrollbar.maximum() and value > 0:
                if not getattr(self, 'is_loading', False) and getattr(self, 'current_url', None):
                    self.is_loading = True
                    try:
                        self.load_movies(self.current_url, getattr(self, 'current_params', {}), append=True)
                    finally:
                        self.is_loading = False
        except Exception as e:
            logging.exception("on_scroll hatası: %s", e)
            self.is_loading = False

    def check_last_watched(self):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT movie_id, movie_title FROM user_history WHERE username = ?", (self.username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            self.last_movie_id, self.last_movie_title = result
            self.continue_title_lbl.setText(self.last_movie_title)
            self.continue_banner.show()

    def update_last_watched(self, movie_id, title):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_history (username, movie_id, movie_title) VALUES (?, ?, ?)", 
                       (self.username, movie_id, title))
        conn.commit()
        conn.close()
        
        self.last_movie_id = movie_id
        self.last_movie_title = title
        self.continue_title_lbl.setText(title)
        self.continue_banner.show()

    def resume_movie(self):
        if hasattr(self, 'last_movie_id'):
            url = f"https://vidsrc.me/embed/movie?tmdb={self.last_movie_id}"
            webbrowser.open(url)

    def apply_filters(self):
        params = {}
        
        year_text = self.year_cb.currentText()
        if year_text != "Tümü":
            if year_text == "1990 Öncesi":
                params['primary_release_date.lte'] = "1989-12-31"
            elif "-" in year_text:
                start, end = year_text.split("-")
                params['primary_release_date.gte'] = f"{start}-01-01"
                params['primary_release_date.lte'] = f"{end}-12-31"
            else:
                params['primary_release_year'] = year_text
                
        rating_text = self.rating_cb.currentText()
        if rating_text != "Tümü":
            min_rating = rating_text.split("+")[0]
            params['vote_average.gte'] = min_rating
            
        genre_id = self.genre_cb.currentData()
        if genre_id is not None:
            params['with_genres'] = genre_id
            
        self.title_label.setText("🎬 Filtrelenmiş Sonuçlar")
        
        self.home_btn.show()
        self.search_input.clear()
        
        for i in range(self.genre_layout.count()):
            widget = self.genre_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setAutoExclusive(False)
                widget.setChecked(False)
                widget.setAutoExclusive(True)
                
        self.load_movies(f"{BASE_URL}/discover/movie", params)

    def toggle_sidebar(self):
        if self.sidebar.maximumWidth() == 0:
            self.animation.setStartValue(0)
            self.animation.setEndValue(300)
            self.animation.start()
        else:
            self.animation.setStartValue(300)
            self.animation.setEndValue(0)
            self.animation.start()

    def toggle_ai_popup(self):
        if self.ai_popup.isHidden():
            self.ai_popup.show()
        else:
            self.ai_popup.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Sağ altta bir miktar boşluk bırakarak butonu konumlandır
        if hasattr(self, 'ai_toggle_btn'):
            btn_width = self.ai_toggle_btn.width()
            btn_height = self.ai_toggle_btn.height()
            btn_x = self.width() - btn_width - 30
            btn_y = self.height() - btn_height - 30
            self.ai_toggle_btn.move(btn_x, btn_y)
            
            if hasattr(self, 'ai_popup'):
                # Kutuyu butonun hemen üstüne hizala
                self.ai_popup.move(btn_x - 350 + btn_width, btn_y - 490)

    def load_genres(self):
        url = f"{BASE_URL}/genre/movie/list"
        params = {'api_key': API_KEY, 'language': 'tr-TR'}
        try:
            response = get_json(url, params=params, timeout=10)
            genres = response.get('genres', [])

            item = self.genre_layout.takeAt(self.genre_layout.count() - 1)
            for genre in genres:
                self.genre_map[genre['id']] = genre['name']
                self.genre_cb.addItem(genre['name'], genre['id'])

                btn = QPushButton(genre['name'])
                btn.setProperty("class", "genreBtn")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setCheckable(True)
                btn.setAutoExclusive(True)
                btn.clicked.connect(lambda checked, g=genre: self.select_genre(g))
                self.genre_layout.addWidget(btn)

            self.genre_layout.addItem(item)
        except requests.RequestException as e:
            logging.error("Kategoriler çekilemedi: %s", e)
            print("Kategoriler çekilemedi. API anahtarınızı ve internet bağlantınızı kontrol edin.")
        except Exception as e:
            logging.exception("Beklenmeyen hata load_genres: %s", e)

    def select_genre(self, genre):
        self.title_label.setText(f"🎬 {genre['name']}")
        self.home_btn.show()
        self.search_input.clear()
        self.genre_cb.setCurrentIndex(0)
        self.year_cb.setCurrentIndex(0)
        self.rating_cb.setCurrentIndex(0)
        self.load_movies(f"{BASE_URL}/discover/movie", {'with_genres': genre['id']})
    def load_movies(self, url, params=None, append=False):
        try:
            if params is None:
                params = {}
                
            if not append:
                self.current_url = url
                self.current_params = params.copy()
                self.current_page = 1
            else:
                self.current_page += 1

            fetch_params = self.current_params.copy()
            fetch_params['api_key'] = API_KEY
            fetch_params['language'] = 'tr-TR'
            fetch_params['page'] = self.current_page

            try:
                response = get_json(self.current_url, params=fetch_params, timeout=10)
                movies = response.get('results', [])
                if movies:  # Boş sonuçları handle et
                    self.display_movies(movies, append=append)
            except requests.RequestException as e:
                logging.error("Veri çekilemedi: %s", e)
                print("Veri çekilemedi. API anahtarını veya internet bağlantısını kontrol et!")
            except Exception as e:
                logging.exception("Beklenmeyen hata load_movies: %s", e)
        except Exception as e:
            logging.exception("load_movies wrapper hatası: %s", e)

    def get_user_watchlist_ids(self):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT movie_id FROM watchlist WHERE username=?", (self.username,))
        ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        return ids

    def toggle_watchlist(self, movie, btn):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM watchlist WHERE username=? AND movie_id=?", (self.username, movie['id']))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("DELETE FROM watchlist WHERE username=? AND movie_id=?", (self.username, movie['id']))
            btn.setText("📌 Listeme Ekle")
        else:
            movie_data = json.dumps(movie)
            cursor.execute("INSERT INTO watchlist (username, movie_id, movie_title, movie_data) VALUES (?, ?, ?, ?)", 
                           (self.username, movie['id'], movie['title'], movie_data))
            btn.setText("➖ Listeden Çıkar")
        conn.commit()
        conn.close()

    def show_watchlist(self):
        self.current_url = None
        self.title_label.setText("📌 İzleme Listem")
        self.home_btn.show()
        self.search_input.clear()
        
        self.genre_cb.setCurrentIndex(0)
        self.year_cb.setCurrentIndex(0)
        self.rating_cb.setCurrentIndex(0)
        
        for i in range(self.genre_layout.count()):
            widget = self.genre_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setAutoExclusive(False)
                widget.setChecked(False)
                widget.setAutoExclusive(True)

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT movie_data FROM watchlist WHERE username=?", (self.username,))
        rows = cursor.fetchall()
        conn.close()
        
        movies = []
        for row in rows:
            try:
                movies.append(json.loads(row[0]))
            except:
                pass
                
        self.display_movies(movies)

    def display_movies(self, movies, append=False):
        try:
            if not append:
                for i in reversed(range(self.grid.count())): 
                    widget = self.grid.itemAt(i).widget()
                    if widget:
                        if isinstance(widget, MovieCard):
                            widget.cleanup()
                        widget.setParent(None)

            watchlist_ids = self.get_user_watchlist_ids()
            current_count = self.grid.count()

            for index, movie in enumerate(movies):
                try:
                    is_in_wl = movie['id'] in watchlist_ids
                    card = MovieCard(movie, self.watch_movie, self.toggle_watchlist, is_in_wl)
                    pos = current_count + index
                    self.grid.addWidget(card, pos // 4, pos % 4)
                except Exception as e:
                    logging.exception("Film kartı oluşturulamadı (ID: %s): %s", movie.get('id'), e)
                    continue
        except Exception as e:
            logging.exception("display_movies hatası: %s", e)

    def search_movie(self):
        query = self.search_input.text()
        if query:
            self.title_label.setText("🎬 Arama Sonuçları")
            self.load_movies(f"{BASE_URL}/search/movie", {'query': query})
            self.home_btn.show()
            self.genre_cb.setCurrentIndex(0)
            self.year_cb.setCurrentIndex(0)
            self.rating_cb.setCurrentIndex(0)
            for i in range(self.genre_layout.count()):
                widget = self.genre_layout.itemAt(i).widget()
                if isinstance(widget, QPushButton):
                    widget.setAutoExclusive(False)
                    widget.setChecked(False)
                    widget.setAutoExclusive(True)
    def go_home(self):
        self.search_input.clear()
        self.title_label.setText("🎬 Film Evreni")
        self.load_movies(f"{BASE_URL}/movie/popular")
        self.home_btn.hide()
        self.genre_cb.setCurrentIndex(0)
        self.year_cb.setCurrentIndex(0)
        self.rating_cb.setCurrentIndex(0)
        for i in range(self.genre_layout.count()):
            widget = self.genre_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setAutoExclusive(False)
                widget.setChecked(False)
                widget.setAutoExclusive(True)
    def _ai_search(self, term: str):
        self.search_input.setText(term)
        self.search_movie()

    def watch_movie(self, movie):
        if movie['genre_ids']:
            self.watched_genres.extend(movie['genre_ids'])
            
        genre_names = [self.genre_map.get(gid, "") for gid in movie.get("genre_ids", [])]
        self.ai_panel.add_to_history(movie["title"], genre_names)
        
        # Filmi veritabanına kaydet ve afişi göster
        self.update_last_watched(movie['id'], movie['title'])
        
        # Filmi varsayılan sistem tarayıcısında aç
        url = f"https://vidsrc.me/embed/movie?tmdb={movie['id']}"
        webbrowser.open(url)
        
        self.show_recommendations()

    def show_recommendations(self):
        if self.watched_genres:
            genre_ids = ",".join(map(str, set(self.watched_genres)))
            self.title_label.setText("🎬 Sizin İçin Önerilenler")
            self.load_movies(f"{BASE_URL}/discover/movie", {'with_genres': genre_ids})
            self.home_btn.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    # Zorunlu ayar kontrolü
    if not API_KEY:
        QMessageBox.critical(None, "Eksik API Anahtarı", "TMDB_API_KEY .env içinde tanımlı değil. Lütfen .env dosyasına ekleyin.")
        logging.critical("TMDB_API_KEY yok - uygulama başlatılamadı.")
        sys.exit(1)

    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        user_name = login_window.logged_in_username
        fullname = login_window.logged_in_user
        try:
            window = MovieApp(username=user_name, user_fullname=fullname)
            window.show()
            sys.exit(app.exec())
        except Exception as e:
            logging.exception("Ana uygulama başlatılamadı: %s", e)
            QMessageBox.critical(None, "Hata", f"Uygulama başlatılırken hata oluştu:\n{str(e)}")
            sys.exit(1)
    else:
        sys.exit(0)