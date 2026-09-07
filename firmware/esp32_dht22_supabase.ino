/*
  Sensor Suhu & Kelembapan (DHT22) -> Supabase, dengan BUFFER OFFLINE
  =======================================================================
  Board   : ESP32 (default) atau ESP8266 (lihat catatan di bawah)
  Sensor  : DHT22 / AM2302
  Library : "DHT sensor library" by Adafruit (+ "Adafruit Unified Sensor")
            LittleFS & time.h sudah bawaan ESP32 Arduino core, tidak perlu instal tambahan.

  FITUR:
  1. Sinkronisasi waktu lewat NTP saat boot, supaya setiap pembacaan dikirim
     dengan timestamp yang akurat secara eksplisit (bukan mengandalkan jam
     server Supabase saat data DITERIMA — penting untuk data yang tertunda).
  2. Kalau pengiriman gagal (WiFi/internet putus), data TIDAK hilang — disimpan
     ke flash (LittleFS) dan otomatis dikirim susulan begitu koneksi pulih,
     dengan waktu pembacaan ASLI, bukan waktu saat akhirnya terkirim.
  3. Kapasitas antrian offline: default 2000 pembacaan. Pada interval 15 menit,
     itu setara ±20,8 hari (2000 x 15 menit ÷ 60 ÷ 24) — jauh melebihi durasi
     gangguan WiFi/listrik yang wajar. Bisa dinaikkan lewat MAX_BARIS_ANTRIAN
     kalau perlu (ruang flash ESP32 masih sangat longgar untuk ukuran ini).

  ── UNTUK ESP8266 ──
  Ganti:
    #include <WiFi.h>          ->  #include <ESP8266WiFi.h>
    #include <HTTPClient.h>    ->  #include <ESP8266HTTPClient.h>
  Pin DHT22 sesuaikan (mis. D4/GPIO2). LittleFS di ESP8266 pakai library yang sama.
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <LittleFS.h>
#include <time.h>
#include <vector>

// ── KONFIGURASI WIFI ──────────────────────────────────────────────
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";

// ── KONFIGURASI SUPABASE ──────────────────────────────────────────
// Gunakan "anon public" key (bukan service_role) untuk perangkat lapangan.
const char* SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co";
const char* SUPABASE_KEY = "PASTE_ANON_KEY_ANDA_DISINI";

// ── KONFIGURASI RUANGAN & SENSOR ─────────────────────────────────
const char* LOKASI = "Kulkas Vaksin 1";   // HARUS UNIK per alat, cocokkan dengan QR Code
#define DHTPIN   4                          // Pin data DHT22 (GPIO4 di ESP32)
#define DHTTYPE  DHT22

const unsigned long INTERVAL_KIRIM_MS = 15UL * 60UL * 1000UL;  // kirim tiap 15 menit

// ── KONFIGURASI ANTRIAN OFFLINE ───────────────────────────────────
const char* FILE_ANTRIAN = "/antrian.csv";
const int MAX_BARIS_ANTRIAN = 2000;  // ±20,8 hari pada interval 15 menit

DHT dht(DHTPIN, DHTTYPE);

void connectWiFi() {
  Serial.print("Menghubungkan ke WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long mulai = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - mulai < 30000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Terhubung!");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" Gagal terhubung untuk saat ini, akan dicoba lagi nanti.");
  }
}

void sinkronisasiWaktu() {
  // gmtOffset_sec = 0 supaya jam ESP32 mengikuti UTC — Supabase menyimpan
  // waktu dalam UTC, dan dashboard yang mengonversinya ke WIB saat ditampilkan.
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Sinkronisasi waktu NTP");
  struct tm waktu;
  int percobaan = 0;
  while (!getLocalTime(&waktu) && percobaan < 20) {
    delay(500);
    Serial.print(".");
    percobaan++;
  }
  Serial.println(percobaan < 20 ? " Berhasil." : " Gagal — pembacaan awal akan pakai waktu perkiraan server.");
}

String waktuUtcIso() {
  struct tm waktu;
  if (!getLocalTime(&waktu, 1000)) {
    return "";  // waktu belum tersedia — biarkan Supabase isi waktu saat diterima
  }
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &waktu);
  return String(buf);
}

bool kirimSatuData(const String& waktuIso, float suhu, float kelembapan) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    if (WiFi.status() != WL_CONNECTED) return false;
  }

  WiFiClientSecure client;
  client.setInsecure(); // Untuk produksi, sebaiknya pin sertifikat/CA root Supabase.

  HTTPClient http;
  http.setTimeout(8000);
  String url = String(SUPABASE_URL) + "/rest/v1/log_suhu";

  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("apikey", SUPABASE_KEY);
  http.addHeader("Authorization", String("Bearer ") + SUPABASE_KEY);
  http.addHeader("Prefer", "return=minimal");

  String payload = String("{\"lokasi\":\"") + LOKASI +
                    "\",\"suhu\":" + String(suhu, 1) +
                    ",\"kelembapan\":" + String(kelembapan, 1);
  if (waktuIso.length() > 0) {
    payload += ",\"waktu\":\"" + waktuIso + "\"";
  }
  payload += "}";

  int httpCode = http.POST(payload);
  bool sukses = (httpCode == 201 || httpCode == 200);
  Serial.printf("POST -> HTTP %d (%s)\n", httpCode, sukses ? "sukses" : "gagal");
  http.end();
  return sukses;
}

void jagaBatasAntrian() {
  File f = LittleFS.open(FILE_ANTRIAN, "r");
  if (!f) return;

  int jumlahBaris = 0;
  while (f.available()) {
    f.readStringUntil('\n');
    jumlahBaris++;
  }
  f.close();

  if (jumlahBaris <= MAX_BARIS_ANTRIAN) return;

  // Buang baris tertua secukupnya (10% dari kapasitas) sekali jalan,
  // supaya tidak perlu trim tiap kali antrian nambah 1 baris.
  int buang = jumlahBaris - MAX_BARIS_ANTRIAN + (MAX_BARIS_ANTRIAN / 10);
  File asal = LittleFS.open(FILE_ANTRIAN, "r");
  File sementara = LittleFS.open("/antrian_tmp.csv", "w");
  int i = 0;
  while (asal.available()) {
    String baris = asal.readStringUntil('\n');
    if (i >= buang && baris.length() > 0) {
      sementara.println(baris);
    }
    i++;
  }
  asal.close();
  sementara.close();
  LittleFS.remove(FILE_ANTRIAN);
  LittleFS.rename("/antrian_tmp.csv", FILE_ANTRIAN);
  Serial.printf("Antrian offline penuh, %d pembacaan tertua dibuang.\n", buang);
}

void simpanKeAntrian(const String& waktuIso, float suhu, float kelembapan) {
  jagaBatasAntrian();
  File f = LittleFS.open(FILE_ANTRIAN, "a");
  if (!f) {
    Serial.println("Gagal membuka file antrian untuk ditulis.");
    return;
  }
  f.printf("%s,%.1f,%.1f\n", waktuIso.c_str(), suhu, kelembapan);
  f.close();
  Serial.println("Koneksi gagal — data disimpan ke antrian offline untuk dikirim susulan.");
}

void cobaKirimAntrian() {
  if (!LittleFS.exists(FILE_ANTRIAN)) return;

  File f = LittleFS.open(FILE_ANTRIAN, "r");
  if (!f) return;

  std::vector<String> sisaBaris;
  bool berhentiKirim = false;
  int terkirim = 0;

  while (f.available()) {
    String baris = f.readStringUntil('\n');
    baris.trim();
    if (baris.length() == 0) continue;

    if (berhentiKirim) {
      sisaBaris.push_back(baris);
      continue;
    }

    int koma1 = baris.indexOf(',');
    int koma2 = baris.indexOf(',', koma1 + 1);
    if (koma1 < 0 || koma2 < 0) continue;  // baris rusak/tidak lengkap, lewati

    String waktuIso = baris.substring(0, koma1);
    float suhu = baris.substring(koma1 + 1, koma2).toFloat();
    float kelembapan = baris.substring(koma2 + 1).toFloat();

    if (kirimSatuData(waktuIso, suhu, kelembapan)) {
      terkirim++;
    } else {
      // Jaga urutan kronologis: begitu satu gagal, berhenti kirim susulan
      // untuk siklus ini (kemungkinan koneksi putus lagi), sisanya tetap disimpan.
      berhentiKirim = true;
      sisaBaris.push_back(baris);
    }
  }
  f.close();

  LittleFS.remove(FILE_ANTRIAN);
  if (!sisaBaris.empty()) {
    File tulis = LittleFS.open(FILE_ANTRIAN, "w");
    for (auto& b : sisaBaris) tulis.println(b);
    tulis.close();
  }

  if (terkirim > 0) {
    Serial.printf("%d data susulan dari antrian offline berhasil terkirim.\n", terkirim);
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  if (!LittleFS.begin(true)) {
    Serial.println("Gagal mount LittleFS — fitur antrian offline tidak akan berfungsi.");
  }

  connectWiFi();
  if (WiFi.status() == WL_CONNECTED) {
    sinkronisasiWaktu();
  }
}

void loop() {
  float kelembapan = dht.readHumidity();
  float suhu = dht.readTemperature();

  if (isnan(kelembapan) || isnan(suhu)) {
    Serial.println("Gagal membaca sensor DHT22!");
  } else {
    String waktuIso = waktuUtcIso();
    Serial.printf("Suhu: %.1f C, Kelembapan: %.1f %%\n", suhu, kelembapan);

    bool sukses = kirimSatuData(waktuIso, suhu, kelembapan);
    if (sukses) {
      cobaKirimAntrian();  // sekalian susulkan data lama di antrian kalau ada
    } else {
      simpanKeAntrian(waktuIso, suhu, kelembapan);
    }
  }

  delay(INTERVAL_KIRIM_MS);
}
