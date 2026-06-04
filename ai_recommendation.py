import os
import json
import time
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import logging
import jsonschema
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy
)
from google import genai
from google.genai import types

load_dotenv()

# --- Gemini Ayarları ---
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    import base64
    try:
        GEMINI_API_KEY = base64.b64decode("QVEuQWI4Uk42S0M0el85cXpGWXFscjIzNFdCcTRJVGV2VV95RkZvS2pIUHJsQkRhOVU4QWc=").decode("utf-8")
    except Exception:
        pass

if not GEMINI_API_KEY:
    logging.warning("GEMINI_API_KEY bulunamadı, AI özellikleri devre dışı bırakılacak.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

# JSON şeması (test ve tekrar kullanım için modül seviyesinde tanımlandı)
SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "year": {"type": "integer"},
                    "reason": {"type": "string"},
                    "tmdb_search": {"type": "string"}
                },
                "required": ["title", "reason"]
            }
        },
        "summary": {"type": "string"}
    },
    "required": ["recommendations"]
}

# ─── 1. Arka Plan Thread'i ────────────────────────────────────────────────────

class AIWorker(QThread):
    """
    Gemini API'yi UI'ı kilitlemeden arka planda çağırır.
    Yanıt hazır olunca result_ready sinyali yayar.
    Hata durumunda error_occurred sinyali yayar.
    """
    result_ready   = pyqtSignal(str, list)   # (öneri metni, tmdb_id listesi)
    error_occurred = pyqtSignal(str)

    def __init__(self, user_query: str, watch_history: list[dict]):
        super().__init__()
        self.user_query    = user_query
        self.watch_history = watch_history  # [{"title": ..., "genres": [...]}]

    def run(self):
        try:
            history_text = self._format_history()

            system_instruction = (
                "Sen Film Evreni uygulamasının AI film danışmanısın. Kullanıcının bir ruh halini belirten bir giriş yapacak. "
                "Kullanıcının izleme geçmişini ve isteğini (ruh halini) analiz ederek "
                "Türkçe, samimi ve kısa öneriler yaparsın. "
                "Her öneriyi şu JSON şemasıyla döndür — başka hiçbir şey yazma:\n"
                '{"recommendations": ['
                '  {"title": "Film Adı", "year": 2023, "reason": "Kısa neden (1 cümle)", '
                '   "tmdb_search": "TMDB arama terimi"}'
                "], "
                '"summary": "Kullanıcıya yönelik 1-2 cümle genel yorum"}'
            )

            user_message = (
                f"İzleme geçmişim:\n{history_text}\n\n"
                f"Şu anki ruh halim / İsteğim: {self.user_query}\n\n"
                "Lütfen bu ruh halime ve isteğime uygun 5 film öner."
            )

            if client is None:
                raise RuntimeError("AI istemcisi yapılandırılmamış (GEMINI_API_KEY eksik).")

            # Retry logic for rate limits and timeouts
            max_retries = 3
            backoff = 1
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=user_message,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                        )
                    )
                    # Başarılı, loop'tan çık
                    break
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # Rate limit, timeout veya temporary hatalarında retry et
                    if attempt < max_retries - 1 and any(x in error_str for x in ["429", "503", "timeout", "temporarily", "rate"]):
                        wait_time = backoff * (2 ** attempt)
                        logging.warning("AI API retry (%d/%d) sonra %ds bekleyeceğim: %s", attempt + 1, max_retries, wait_time, error_str)
                        time.sleep(wait_time)
                    else:
                        raise

            raw = response.text
            # Kod bloğu varsa temizle
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # JSON parse hatası → ham metni göster
                self.result_ready.emit(raw, [])
                return

            # Şema kontrolü
            

            try:
                jsonschema.validate(instance=data, schema=SCHEMA)
            except jsonschema.ValidationError:
                logging.warning("AI yanıtı şema doğrulamasından geçemedi. Ham içerik gösterilecek.")
                self.result_ready.emit(raw, [])
                return

            summary = data.get("summary", "")
            tmdb_searches = [r.get("tmdb_search", r["title"]) for r in data["recommendations"]]

            # Formatlanmış öneri metni oluştur
            lines = [f"🤖  {summary}\n"]
            for i, rec in enumerate(data["recommendations"], 1):
                lines.append(
                    f"{i}. {rec['title']} ({rec.get('year', '?')})\n"
                    f"   ↳ {rec['reason']}"
                )
            result_text = "\n".join(lines)

            self.result_ready.emit(result_text, tmdb_searches)

        except Exception as e:
            logging.exception("AIWorker hata: %s", e)
            error_str = str(e)
            
            # Kullanıcı-dostu hata mesajı
            if "429" in error_str or "rate" in error_str.lower():
                msg = "⚠️  AI öneri hizmetine çok fazla isteğin gitti (rate limit). Lütfen birkaç saniye sonra tekrar deneyin."
            elif "503" in error_str or "unavailable" in error_str.lower():
                msg = "⚠️  AI hizmeti geçici olarak unavailable. Lütfen biraz sonra tekrar deneyin."
            elif "timeout" in error_str.lower():
                msg = "⚠️  Bağlantı timeout oldu. Internet bağlantınızı kontrol edin ve tekrar deneyin."
            elif "permission" in error_str.lower() or "permission_denied" in error_str.lower():
                msg = "⚠️  AI API anahtarında izin sorunu var. Tasarımcıya başvurun."
            else:
                msg = f"⚠️  AI hatası: {error_str[:80]}"
            
            self.error_occurred.emit(msg)

    def _format_history(self) -> str:
        if not self.watch_history:
            return "Henüz film izlenilmemiş."
        return "\n".join(
            f"- {item['title']}  (türler: {', '.join(item.get('genres', []))})"
            for item in self.watch_history[-10:]   # son 10 film yeterli
        )


# ─── 2. AI Öneri Paneli Widget ────────────────────────────────────────────────

class AIRecommendationWidget(QFrame):
    """
    Kenar çubuğunun altına eklenebilecek Ruh Hali Modu paneli.
    Sinyal: film_search_requested(str)  → MovieApp'in arama kutusunu tetikler.
    """
    film_search_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiPanel")
        self.watch_history: list[dict] = []
        self._worker: AIWorker | None  = None
        self._build_ui()

    # ── Arayüz ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet("""
            QFrame#aiPanel {
                background: #12121a;
                border-top: 1px solid #2a2a35;
                margin-top: 10px;
            }
            QTextEdit {
                background: #1c1c24;
                border: 1px solid #2a2a35;
                border-radius: 8px;
                color: #dddddd;
                font-size: 13px;
                padding: 8px;
            }
            QLineEdit {
                background: #1c1c24;
                border: 1px solid #2a2a35;
                border-radius: 8px;
                color: white;
                font-size: 13px;
                padding: 8px 12px;
            }
            QLineEdit:focus { border-color: #7c3aed; }
            QPushButton#aiBtn {
                background: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#aiBtn:hover   { background: #6d28d9; }
            QPushButton#aiBtn:disabled { background: #3a3a45; color: #777; }
            QPushButton#searchFilmBtn {
                background: #e50914;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton#searchFilmBtn:hover { background: #f40612; }
            QLabel { color: #aaaaaa; font-size: 12px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Başlık
        title = QLabel("✨ Ruh Hali Modu - AI Danışmanı")
        title.setStyleSheet("color: #a78bfa; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Bugün nasıl hissediyorsun? Sana özel filmler önereyim!")
        layout.addWidget(subtitle)

        # Giriş alanı
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText(
            "Örn: Biraz moralsizim, eğlenceli ve komik bir şeyler öner..."
        )
        self.query_input.returnPressed.connect(self._ask_claude)
        layout.addWidget(self.query_input)

        # Gönder butonu
        self.ask_btn = QPushButton("🔮 Öneri İste")
        self.ask_btn.setObjectName("aiBtn")
        self.ask_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask_btn.clicked.connect(self._ask_claude)
        layout.addWidget(self.ask_btn)

        # Sonuç alanı
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFixedHeight(180)
        self.result_area.setPlaceholderText("Öneriler burada görünecek…")
        layout.addWidget(self.result_area)

        # Hızlı arama butonları (dinamik olarak doldurulur)
        self.quick_search_layout = QHBoxLayout()
        self.quick_search_layout.setSpacing(6)
        layout.addLayout(self.quick_search_layout)

    # ── Genel API ────────────────────────────────────────────────────────────
    def add_to_history(self, title: str, genre_names: list[str]):
        """MovieApp.watch_movie() tarafından çağrılır."""
        self.watch_history.append({"title": title, "genres": genre_names})

    # ── İç Mantık ────────────────────────────────────────────────────────────
    def _ask_claude(self):
        query = self.query_input.text().strip()
        if not query:
            return

        self._set_loading(True)
        self._clear_quick_buttons()

        self._worker = AIWorker(query, self.watch_history)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_result(self, text: str, tmdb_searches: list[str]):
        self._set_loading(False)
        self.result_area.setPlainText(text)
        for term in tmdb_searches:
            self._add_quick_button(term)

    def _on_error(self, message: str):
        self._set_loading(False)
        self.result_area.setPlainText(f"⚠️  {message}")

    def _set_loading(self, loading: bool):
        self.ask_btn.setEnabled(not loading)
        self.ask_btn.setText("⏳ Yanıt bekleniyor…" if loading else "🔮 Öneri İste")

    def _clear_quick_buttons(self):
        while self.quick_search_layout.count():
            item = self.quick_search_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_quick_button(self, search_term: str):
        """Her öneri için uygulamada arama yapan küçük buton oluşturur."""
        # Uzun terimleri kısalt
        label = search_term if len(search_term) <= 18 else search_term[:16] + "…"
        btn = QPushButton(f"▶ {label}")
        btn.setObjectName("searchFilmBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(search_term)
        btn.clicked.connect(lambda _, t=search_term: self.film_search_requested.emit(t))
        self.quick_search_layout.addWidget(btn)
