# Studio animasi 2D

Studio lokal yang dipakai ulang untuk semua video. Engine berasal dari GrowKaz Stickman Studio; cerita dan scene disimpan per video. Studio berada di proyek content_generator. Paket cutout tambahan disimpan di cutout/.

## Mulai dari folder studio

```powershell
cd "C:\Projek Bryan J\content_generator\backend"
.\.venv\Scripts\python.exe tools/doctor.py
```

Node.js, FFmpeg dan FFprobe harus tersedia di PATH. Python studio memakai `.venv` sendiri, tanpa perlu activation. Dependensi JavaScript dikunci dalam `package-lock.json` setelah instalasi; dependensi Python terpasang dicatat di `requirements-lock.txt`.

## Video baru

Setelah storyline dan narasi siap:

```powershell
.\.venv\Scripts\python.exe tools/new_project.py --name cerita-pertama --voice "C:\path\narasi.wav" --script "C:\path\naskah.txt" --aspect 16:9 --resolution 1080p --title "Cerita Pertama"
```

`--script` opsional. Untuk video vertikal gunakan `--aspect 9:16 --captions`. Nama folder video harus sederhana, misalnya `cerita-pertama`.

Setiap video memakai struktur:

```text
projects/nama-video/
  config.json       pengaturan ukuran, fps, gaya, audio
  input/            narasi dan naskah sumber
  timeline/         kata dan kalimat bertimestamp
  story/bible.md    storyline, karakter, lokasi, arah visual
  story/shots.json  urutan dan timing shot
  scenes/cast.js    karakter cerita ini
  scenes/sets/      lokasi yang dipakai ulang dalam cerita
  scenes/shots/     adegan cerita ini
  audio/            musik dan efek tambahan
  build/            preview dan hasil antara
  out/              MP4 final
```

Jangan jalankan pembuat proyek dengan nama video yang sudah ada: alat bawaan dapat menimpa config dan input.

## Alur produksi

1. Tentukan storyline dan narasi; belum perlu memilih gaya saat menyiapkan studio.
2. Buat proyek, transkripsi atau impor timestamp, lalu susun `story/shots.json`.
3. Pakai ulang karakter, gerakan, kamera, overlay, efek, dan lokasi dari engine atau scene yang sudah ada. Tulis tambahan scene hanya bila cerita membutuhkannya.
4. Periksa contact sheet dan preview, lalu pilih atau ubah gaya visual.
5. Render dan campur audio untuk MP4 final.

```powershell
# Transkripsi: model diunduh saat pertama kali dipakai
.\.venv\Scripts\python.exe tools/transcribe.py --project projects/cerita-pertama --lang id --model small
.\.venv\Scripts\python.exe tools/beats.py --project projects/cerita-pertama

# Setelah scene dibuat
node render.mjs --project projects/cerita-pertama --sheet --scale 0.5
node render.mjs --project projects/cerita-pertama --from 0 --to 10 --scale 0.5
node render.mjs --project projects/cerita-pertama
.\.venv\Scripts\python.exe audio/mix.py --project projects/cerita-pertama
```

## Uji instalasi tanpa storyline baru

```powershell
node render.mjs --project examples/reaction-time --sheet --scale 0.3
node render.mjs --project examples/reaction-time --from 0 --to 2 --scale 0.3 --workers 1
```

Contoh bawaan dipertahankan sebagai referensi API; bukan template cerita wajib. Studio ini berbasis kode, belum berupa editor drag-and-drop atau sistem yang otomatis membuat semua adegan dari teks.

## Pemeliharaan

Instal ulang JavaScript: `npm.cmd ci`; browser: `npx.cmd playwright install chromium`.
Instal ulang Python: `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`.
Untuk mengubah engine, lakukan satu kali di `engine/`, lalu semua proyek dapat memakainya.

## API untuk frontend lokal
Jalankan start-api.ps1 lalu buka http://127.0.0.1:8000/docs. Kontrak, client TypeScript, dan prompt Google AI Studio ada di frontend-integration/.


## Remotion
Template animasi gambar kini tersedia pada tab Animasi Gambar. Panduan lengkap: ../2d-project-studio/REMOTION.md. Engine GrowKaz lama tetap tersedia melalui pilihan engine di Pengaturan Video.
