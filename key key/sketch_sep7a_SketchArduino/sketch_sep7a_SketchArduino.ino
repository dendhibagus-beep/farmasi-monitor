/*
  Sensor Suhu & Kelembapan (DHT22) -> Supabase
  =============================================
  Board   : ESP32 (default) atau ESP8266 (lihat catatan di bawah)
  Sensor  : DHT22 / AM2302
  Library : "DHT sensor library" by Adafruit (+ "Adafruit Unified Sensor")

  Cara kerja:
  1. Baca suhu & kelembapan dari DHT22 setiap INTERVAL_KIRIM_MS.
  2. Kirim data via HTTPS POST langsung ke Supabase REST API
     (tabel `log_suhu`). Kolom `waktu` diisi otomatis oleh database
     (default now()), jadi ESP32 tidak perlu modul RTC.

  ── UNTUK ESP8266 ──
  Ganti:
    #include <WiFi.h>          ->  #include <ESP8266WiFi.h>
    #include <HTTPClient.h>    ->  #include <ESP8266HTTPClient.h>
  Pin DHT22 sesuaikan (mis. D4/GPIO2).
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <DHT.h>

// ── KONFIGURASI WIFI ──────────────────────────────────────────────
const char* WIFI_SSID     = "hospot dendhi";
const char* WIFI_PASSWORD = "jumanjii";

// ── KONFIGURASI SUPABASE ──────────────────────────────────────────
// Gunakan "anon public" key (bukan service_role) untuk perangkat lapangan.
const char* SUPABASE_URL = "https://ahxhppdptlxxfcdwyfbf.supabase.co";
const char* SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFoeGhwcGRwdGx4eGZjZHd5ZmJmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3ODIxMTUsImV4cCI6MjEwNDM1ODExNX0.3YrYUPdc_KNts_y9_gnKS2kiK0WyAq-EGgymcxUt7yY";

// ── KONFIGURASI RUANGAN & SENSOR ─────────────────────────────────
const char* LOKASI = "Gudang 1";   // HARUS UNIK per alat, cocokkan dengan QR Code
#define DHTPIN   4                          // Pin data DHT22 (GPIO4 di ESP32)
#define DHTTYPE  DHT22

const unsigned long INTERVAL_KIRIM_MS = 15UL * 60UL * 1000UL;  // kirim tiap 15 menit

DHT dht(DHTPIN, DHTTYPE);

void connectWiFi() {
  Serial.print("Menghubungkan ke WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Terhubung!");
  Serial.println(WiFi.localIP());
}

bool kirimKeSupabase(float suhu, float kelembapan) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  WiFiClientSecure client;
  client.setInsecure(); // Untuk produksi, sebaiknya pin sertifikat/CA root Supabase.

  HTTPClient http;
  String url = String(SUPABASE_URL) + "/rest/v1/log_suhu";

  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("apikey", SUPABASE_KEY);
  http.addHeader("Authorization", String("Bearer ") + SUPABASE_KEY);
  http.addHeader("Prefer", "return=minimal");

  String payload = String("{\"lokasi\":\"") + LOKASI +
                    "\",\"suhu\":" + String(suhu, 1) +
                    ",\"kelembapan\":" + String(kelembapan, 1) + "}";

  int httpCode = http.POST(payload);
  Serial.printf("POST -> HTTP %d\n", httpCode);
  if (httpCode > 0) {
    Serial.println(http.getString());
  }
  http.end();

  return httpCode == 201 || httpCode == 200;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  connectWiFi();
}

void loop() {
  float kelembapan = dht.readHumidity();
  float suhu = dht.readTemperature();

  if (isnan(kelembapan) || isnan(suhu)) {
    Serial.println("Gagal membaca sensor DHT22!");
  } else {
    Serial.printf("Suhu: %.1f C, Kelembapan: %.1f %%\n", suhu, kelembapan);
    bool ok = kirimKeSupabase(suhu, kelembapan);
    Serial.println(ok ? "Data terkirim." : "Gagal mengirim data.");
  }

  delay(INTERVAL_KIRIM_MS);
}