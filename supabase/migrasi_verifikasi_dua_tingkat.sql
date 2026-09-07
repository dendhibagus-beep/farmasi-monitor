-- ============================================================================
-- MIGRASI: Sistem Verifikasi Dua Tingkat (Paraf Harian + TTD Bulanan)
-- Jalankan ini di SQL Editor Supabase kalau database Anda SUDAH ada isinya
-- (tidak perlu jalankan ulang schema.sql lengkap, cukup tambahan ini saja).
-- ============================================================================

-- Paraf harian — jejak supervisi setiap hari oleh Petugas Logistik (jam kerja)
-- atau Duty Farmasi (luar jam kerja). Boleh lebih dari satu entri per hari
-- per ruangan (misal shift pagi & shift malam masing-masing memaraf).
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

-- Verifikasi bulanan — tanda tangan Penanggung Jawab, sekali per bulan,
-- meninjau rekap kepatuhan paraf_harian sepanjang bulan tsb.
create table if not exists verifikasi_bulanan (
  id bigint generated always as identity primary key,
  bulan text not null,
  lokasi text not null,
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

-- Tabel lama `verifikasi_harian` (versi verifikasi satu-tingkat sebelumnya)
-- TIDAK dipakai lagi oleh aplikasi. Aman dibiarkan (tidak mengganggu), atau
-- hapus kalau mau beres-beres:
-- drop table if exists verifikasi_harian;
