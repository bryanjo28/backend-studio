# Prompt untuk Google AI Studio

Bangun frontend React + TypeScript + Vite untuk studio animasi 2D lokal. Hasil frontend akan didownload dan dijalankan di komputer Windows yang sama dengan backend. Gunakan port Vite 5173 dengan strictPort. Backend FastAPI berjalan di http://127.0.0.1:8000. Gunakan VITE_STUDIO_API_URL agar alamat dapat diubah. Jangan memerlukan Gemini API key untuk operasi studio.

Saya akan memberikan file studio-client.ts dan openapi.json sebagai kontrak. Gunakan endpoint yang ada; jangan mengarang endpoint atau mensimulasikan render sukses. Pisahkan komponen tampilan dan client API. Semua fungsi utama harus memanggil backend, dengan loading, empty state dan pesan error.

Tampilan berbahasa Indonesia, sidebar proyek dan area kerja dengan tab:
- Proyek: daftar, buat proyek dengan slug, judul, template kosong atau demo; jangan membuat ID sendiri. Demo tersedia untuk menguji render tanpa scene baru.
- Aset: upload gambar karakter/latar/properti, narasi dan naskah; thumbnail gambar, audio player untuk narasi. Upload multipart/form-data, jangan set Content-Type manual. Nama asli tidak dipertahankan; gunakan path dan URL dari respons.
- Cerita: editor storyline yang disimpan melalui endpoint storyline dan tabel shot dengan id, start, end, line, scene. shots harus berurutan tanpa celah mulai 0. duration harus sama dengan end shot terakhir. Simpan story sebagai satu JSON dan pertahankan field tambahan.
- Pengaturan: aspect 16:9/9:16, resolution 720p/1080p/1440p/2160p, fps 24/30, captions, style dari API.
- Render: contact sheet, preview dengan rentang waktu dan scale, render penuh, campur audio. Poll job tiap 1 detik; hentikan polling saat succeeded/failed dan bersihkan timer ketika pindah halaman. Tampilkan log aktual; persentase hanya jika tersedia dari log, jangan mengarang progres. Saat render berjalan nonaktifkan edit proyek yang sama. Preview maksimal sepanjang durasi proyek.
- Hasil: tampilkan PNG dan video dari artifacts job memakai studio.fileUrl; sediakan unduh. Video render penuh masih silent; tombol campur audio memerlukan narasi dan hasil full render.

Tidak ada endpoint penghapus proyek, pembatalan render, generator scene AI, auto-rigging, atau editor kode scene. Jangan membuat tombol aktif untuk fitur itu. Jelaskan bahwa upload aset dan teks storyline tidak otomatis membangun adegan; scene perlu disiapkan terlebih dahulu. Gaya visual cerita akan dipilih kemudian. Backend adalah lokal satu pengguna, bukan layanan publik. Saat backend offline, tampilkan instruksi menjalankan start-api.ps1. Riwayat job reset saat backend dimatikan.

Simpan FE terpisah dari engine. Sertakan .env.example, README menjalankan npm install dan npm run dev, serta cara mengubah VITE_STUDIO_API_URL. Jangan menambahkan backend lain atau mengubah engine renderer.
