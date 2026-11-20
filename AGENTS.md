# Studio animasi yang dipakai ulang

- Kerjakan semua produksi video di folder studio ini. Folder induk adalah proyek content_generator.
- Pakai engine dan alat yang sudah ada; jangan membangun ulang renderer untuk setiap cerita.
- Setiap video baru berada di `projects/<slug>/`; jangan menimpa proyek lama.
- Gunakan `.venv/Scripts/python.exe` untuk Python di Windows.
- Ikuti skill `make-2d-video` dan stage skill yang relevan. Storyline dan pilihan visual datang dari permintaan video; jangan menganggap contoh reaction-time sebagai storyline pengguna.
- `story/shots.json` menjadi sumber timing. Scene khusus cerita berada di proyek; perbaikan yang berlaku untuk semua video masuk engine.
- Lihat contact sheet dan periksa error scene sebelum full render. Periksa video dengan ffprobe setelah render.
- Jangan mengklaim semua cerita bisa dibuat hanya dengan mengganti teks: aset atau aksi yang belum tersedia memerlukan tambahan scene.
