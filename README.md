# Film Evreni - Yerel Uygulama

Bu küçük uygulama TMDB API ve Google Gemini (genai) kullanarak film arama ve AI destekli ruh hali önerileri sağlar.

Ön gereksinimler

- Python 3.10+
- Sanal ortam (önerilir)

Kurulum

```bash
pip install -r requirements.txt
```

Ortam değişkenleri

Kök dizine `.env` dosyası koyun veya sistem ortam değişkenlerine ekleyin. Örnek `.env.example` dosyası mevcuttur.

```
TMDB_API_KEY=your_tmdb_key
GEMINI_API_KEY=your_gemini_key
```

Çalıştırma

```bash
python main.py
```

Notlar

- Mevcut veritabanı `users.db` olarak oluşturulur. Üretimde daha güvenli bir veritabanı tercih edin.
- Parola hashleme `bcrypt` kullanır; önceki SHA256 hash'li kayıtlar uyumsuz olabilir.
- API anahtarınızı Git'e pushlamayın. `.gitignore` dosyası `.env`'i hariç tutar.
