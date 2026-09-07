-- ============================================================================
-- Skema database lengkap — Command Center Logistik & Perbekalan Farmasi
-- Jalankan seluruh isi file ini di Supabase SQL Editor (New query -> Run).
-- ============================================================================

-- 1. Data mentah pembacaan sensor
create table if not exists log_suhu (
  id bigint generated always as identity primary key,
  lokasi text not null,
  suhu numeric not null,
  kelembapan numeric not null,
  waktu timestamptz not null default now()
);

alter table log_suhu enable row level security;

create policy "Izinkan insert publik (perangkat sensor)"
  on log_suhu for insert
  with check (true);

create policy "Izinkan baca publik (dashboard & landing page)"
  on log_suhu for select
  using (true);

-- 2. Ambang batas kustom per ruangan (opsional; kalau kosong, aplikasi
--    memakai standar default berdasarkan kategori nama ruangan)
create table if not exists ambang_batas (
  lokasi text primary key,
  suhu_min numeric not null,
  suhu_max numeric not null,
  lembab_min numeric not null,
  lembab_max numeric not null,
  updated_at timestamptz not null default now()
);

alter table ambang_batas enable row level security;

create policy "Izinkan baca publik (dashboard)"
  on ambang_batas for select
  using (true);

create policy "Izinkan tulis publik (modul Pengaturan)"
  on ambang_batas for all
  using (true)
  with check (true);

-- 3. Riwayat status & waktu notifikasi terakhir per ruangan (anti-spam alarm)
create table if not exists alarm_log (
  lokasi text primary key,
  last_status text not null,
  last_notified_at timestamptz,
  updated_at timestamptz not null default now()
);

alter table alarm_log enable row level security;

create policy "Izinkan baca publik (dashboard)"
  on alarm_log for select
  using (true);

-- Insert/update ke alarm_log hanya dilakukan Edge Function memakai service_role key
-- (otomatis melewati RLS) — tidak perlu policy insert/update publik.

-- 4. (Lama, boleh diabaikan) Verifikasi harian versi awal — digantikan oleh
--    paraf_harian + verifikasi_bulanan di bawah. Dibiarkan di sini agar tidak
--    error kalau sudah pernah dibuat sebelumnya; aman untuk di-drop kalau mau.
create table if not exists verifikasi_harian (
  id bigint generated always as identity primary key,
  tanggal date not null,
  lokasi text not null,
  nama_supervisor text not null,
  jabatan text not null,
  catatan text,
  tanda_tangan_base64 text,
  dibuat_pada timestamptz not null default now()
);

alter table verifikasi_harian enable row level security;

create policy "Izinkan baca publik (riwayat verifikasi)"
  on verifikasi_harian for select
  using (true);

create policy "Izinkan insert publik (modul Verifikasi)"
  on verifikasi_harian for insert
  with check (true);

-- 5. Paraf harian — jejak supervisi setiap hari oleh Petugas Logistik (jam kerja)
--    atau Duty Farmasi (luar jam kerja). Boleh lebih dari satu entri per hari
--    per ruangan (misal shift pagi & shift malam masing-masing memaraf).
create table if not exists paraf_harian (
  id bigint generated always as identity primary key,
  tanggal date not null,
  lokasi text not null,
  nama_petugas text not null,
  peran text not null,
  catatan text,
  tanda_tangan_base64 text,
  dibuat_pada timestamptz not null default now()
);

alter table paraf_harian enable row level security;

create policy "Izinkan baca publik (riwayat paraf harian)"
  on paraf_harian for select
  using (true);

create policy "Izinkan insert publik (modul Paraf Harian)"
  on paraf_harian for insert
  with check (true);

-- 6. Verifikasi bulanan — tanda tangan Penanggung Jawab, sekali per bulan,
--    meninjau rekap kepatuhan paraf_harian sepanjang bulan tsb.
create table if not exists verifikasi_bulanan (
  id bigint generated always as identity primary key,
  bulan text not null,               -- label tampilan, mis. 'September 2026'
  lokasi text not null,              -- daftar ruangan yang ditinjau (dipisah koma)
  nama_penanggung_jawab text not null,
  jabatan text not null,
  catatan text,
  tanda_tangan_base64 text,
  dibuat_pada timestamptz not null default now()
);

alter table verifikasi_bulanan enable row level security;

create policy "Izinkan baca publik (riwayat verifikasi bulanan)"
  on verifikasi_bulanan for select
  using (true);

create policy "Izinkan insert publik (modul Verifikasi Bulanan)"
  on verifikasi_bulanan for insert
  with check (true);
