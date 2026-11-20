# Menghubungkan frontend lokal

1. Jalankan `start-api.ps1` dari folder studio memakai PowerShell. Jika kebijakan script memblokir, jalankan `.\.venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8000`.
2. Buka `http://127.0.0.1:8000/docs`. Kontrak lengkap ada di `openapi.json` atau URL `/openapi.json`.
3. Berikan `GOOGLE_AI_STUDIO_PROMPT.md`, `studio-client.ts`, dan `openapi.json` ke Google AI Studio.
4. Download frontend ke `C:\Projek Bryan J\content_generator\frontend`. Tambahkan client ke src frontend; gunakan `.env.local` berisi `VITE_STUDIO_API_URL=http://127.0.0.1:8000`.
5. Jalankan FE pada `http://localhost:5173`. Backend juga mengizinkan port 3000 dan hostname 127.0.0.1. Untuk port lain, atur `STUDIO_CORS_ORIGINS` pada terminal backend sebelum startup (daftar origin dipisah koma), lalu restart.

Backend dan FE dijalankan sebagai dua proses lokal. Tidak perlu hosting, tunnel, akun cloud, atau API key untuk mengoperasikan studio. Gunakan satu proses backend tanpa reload ketika ada render.

## Urutan uji FE

POST `/api/projects` dengan `{"slug":"uji-fe","title":"Uji FE","template":"demo","resolution":"720p"}`.
POST `/api/projects/uji-fe/jobs` dengan `{"kind":"preview","start":0,"end":2,"scale":0.3}`.
Poll GET `/api/jobs/<id>` hingga terminal; buka URL artifacts dengan prefix alamat backend.

Endpoint utama: GET `/api/health`, GET `/api/styles`, GET/POST `/api/projects`, GET `/api/projects/{slug}`, PATCH `.../config`, GET/PUT `.../storyline`, PUT `.../story`, GET/POST `.../assets`, POST `.../jobs`, GET `/api/jobs/{id}`, GET `.../files/{path}`.

Upload: multipart field `file` dan `category` (characters/backgrounds/props/voiceover/script). Maksimal 100 MiB tiap file; gambar PNG/JPG/WebP, narasi MP3/WAV/M4A/OGG/FLAC, naskah TXT/SRT/VTT. File tidak otomatis ditempel ke scene. Narasi dan naskah mengubah path input pada config. API versi awal belum menjalankan transkripsi dari FE; gunakan alat studio untuk timing.

Render tidak mengarang scene dari teks. Proyek kosong perlu modul scene JavaScript di `projects/<slug>/scenes/shots`. Story timing harus contiguous dari 0, ID unik, durasi positif. Mutasi proyek ditolak selama job queued/running. Render penuh memakai resolusi config, preview/contact sheet memakai scale.

Job: queued/running/succeeded/failed, log aktual maksimal 24000 karakter, artifacts berupa URL relatif. Antrean satu worker (maksimal 8 job aktif), riwayat disimpan di memori; restart menghapus riwayat, file video tetap tersimpan. Belum ada cancel/resume. Jangan hentikan server saat render berjalan. Backend hanya untuk komputer lokal satu pengguna; tidak memiliki autentikasi untuk akses publik.

Test: `.\.venv\Scripts\python.exe -m unittest api.test_app -v`.
