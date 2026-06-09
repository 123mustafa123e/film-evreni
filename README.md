# 🎬 Film Evreni - Gemini AI Destekli Masaüstü Film Portalı

**Film Evreni**, TMDB API ve Google Gemini API entegrasyonuyla geliştirilmiş, kişiselleştirilmiş film keşif deneyimi sunan modern bir PyQt6 masaüstü uygulamasıdır. Kullanıcıların sadece türlere göre değil, kendi ruh hallerine ve kişisel izleme geçmişlerine göre akıllı film önerileri alabilmesini sağlar.

---

## ✨ Öne Çıkan Özellikler

*   🔑 **Kullanıcı Kayıt & Giriş Sistemi:** SQLite veritabanı altyapısıyla yerel kullanıcı hesap yönetimi.
*   🔒 **Gelişmiş Güvenlik:** Kullanıcı şifreleri yerel veritabanında `bcrypt` algoritması ile tuzlanarak (salted) güvenli şekilde hashlenmiş olarak saklanır.
*   🤖 **Ruh Hali Asistanı (AI Danışmanı):** `gemini-2.5-flash` modeli entegrasyonu sayesinde o anki hislerinize (Örn: *"Biraz moralsizim, kafa dağıtacak eğlenceli bir komedi öner"*) ve izleme geçmişinize en uygun 5 filmi akıllıca listeler.
*   ⚡ **Asenkron Yapı (Thread-Safe):** Görsel yüklemeleri ve yapay zeka sorguları `QThread` iş parçacıkları üzerinden arka planda yürütülür; bu sayede arayüzde donma veya takılma yaşanmaz.
*   📋 **Yapılandırılmış AI Yanıtları:** Gemini API çıktıları `jsonschema` kullanılarak şema kontrolünden geçirilir ve doğrudan arayüzde tıklanabilir dinamik hızlı arama butonlarına dönüştürülür.
*   🔄 **Kaldığın Yerden Devam Et:** En son izlenen filmi SQLite veritabanında saklayarak, uygulamaya tekrar girildiğinde kullanıcıyı akıllı bir devam etme banner'ı ile karşılar.
*   📌 **Kişisel İzleme Listesi (Watchlist):** Beğenilen filmler tek tıkla izleme listesine eklenebilir veya çıkarılabilir.
*   🔍 **Gelişmiş Filtreleme:** Kategori, çıkış yılı aralığı ve minimum TMDB puanı kriterlerine göre detaylı keşif aracı.
*   🎨 **Modern Hover Efektleri:** Film kartlarının üzerine gelindiğinde, pürüzsüz bir animasyonla filmin puanı, genişletilmiş özeti ve hızlı işlem menüsü gösterilir.

---

## 🛠️ Teknoloji Yığını

*   **Programlama Dili:** Python 3.10+
*   **Arayüz Tasarımı:** PyQt6 (GUI Framework)
*   **Veritabanı:** SQLite3
*   **Yapay Zeka SDK:** `google-genai` (Google Gemini API)
*   **Harici API:** TMDB (The Movie Database) API
*   **Şifreleme & Güvenlik:** Bcrypt
*   **Veri Doğrulama:** JSON Schema
*   **Test:** Pytest

---

## 🚀 Kurulum ve Çalıştırma

### 1. Gereksinimleri Yükleme

Projeyi klonladıktan veya indirdikten sonra, proje dizininde bir sanal ortam oluşturup bağımlılıkları yükleyin:

```bash
# Sanal ortam oluşturma (Önerilir)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# veya
venv\Scripts\activate     # Windows

# Bağımlılıkları yükleme
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Yapılandırma

Proje kök dizininde `.env` adında bir dosya oluşturun ve aşağıdaki anahtarları kendi API anahtarlarınızla doldurun (Örnek şablon için `.env.example` dosyasını inceleyebilirsiniz):

```env
TMDB_API_KEY=your_tmdb_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

> ⚠️ **Önemli Güvenlik Uyarısı:** `.env` dosyanız kişisel API anahtarlarınızı barındırır. Güvenliğiniz için bu dosyayı kesinlikle GitHub gibi uzak depolara göndermeyin. Projede `.gitignore` dosyası `.env`'i otomatik olarak hariç tutacak şekilde yapılandırılmıştır.

### 3. Uygulamayı Başlatma

Aşağıdaki komutla uygulamayı doğrudan çalıştırabilirsiniz:

```bash
python main.py
```

---

## ⚙️ Uygulamayı Derleme (.EXE Yapma)

Uygulamayı tek bir çalıştırılabilir dosya (`.exe`) haline getirmek için **PyInstaller** kullanabilirsiniz. Projede yer alan `FilmEvreni.spec` dosyası derleme ayarlarını barındırır.

Derleme işlemi için terminalde şu komutu çalıştırın:
```bash
pyinstaller FilmEvreni.spec
```
Derleme tamamlandıktan sonra, çalıştırılabilir uygulama dosyası `dist/` klasörünün altında yer alacaktır. Detaylı bilgi için `EXE_KULLANIM.txt` kılavuzuna göz atabilirsiniz.

---

## 🧪 Testlerin Çalıştırılması

Uygulamanın kararlılığını ve kod kalitesini doğrulamak amacıyla hazırlanan birim (unit) testlerini çalıştırmak için:

```bash
pytest
```

---

## 📄 Lisans

Bu proje eğitim ve kişisel gelişim amacıyla geliştirilmiştir. TMDB ve Google Gemini servislerinin kullanım koşullarına tabidir.
