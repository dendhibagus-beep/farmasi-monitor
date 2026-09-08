/*
  DIAGNOSTIK WIFI — Jalankan sketch ini SAJA (bukan firmware utama) untuk
  mencari tahu kenapa ESP32 tidak bisa konek ke WiFi gudang.

  Cara pakai:
  1. Upload sketch ini ke ESP32 (letakkan di lokasi yang sama persis dengan
     kulkas, supaya kondisi sinyalnya sama).
  2. Buka Serial Monitor (115200 baud).
  3. Lihat daftar WiFi yang muncul — cari nama WiFi gudang Anda di situ.
  4. Kirimkan hasilnya (screenshot Serial Monitor) untuk dianalisis.
*/

#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(500);

  Serial.println("\n=== ESP32 MAC Address (untuk didaftarkan ke IT kalau ada MAC filtering) ===");
  Serial.println(WiFi.macAddress());

  Serial.println("\n=== Memindai semua WiFi yang terlihat oleh ESP32... ===");
  int n = WiFi.scanNetworks();

  if (n == 0) {
    Serial.println("Tidak ada WiFi terdeteksi sama sekali! Cek apakah antena ESP32 terpasang benar.");
  } else {
    Serial.printf("Ditemukan %d jaringan:\n\n", n);
    Serial.println("No | Nama WiFi (SSID)              | Sinyal (dBm) | Channel | Keamanan");
    Serial.println("---|--------------------------------|--------------|---------|----------");
    for (int i = 0; i < n; i++) {
      String enkripsi;
      switch (WiFi.encryptionType(i)) {
        case WIFI_AUTH_OPEN: enkripsi = "Terbuka (tanpa password)"; break;
        case WIFI_AUTH_WEP: enkripsi = "WEP"; break;
        case WIFI_AUTH_WPA_PSK: enkripsi = "WPA-PSK"; break;
        case WIFI_AUTH_WPA2_PSK: enkripsi = "WPA2-PSK (rumahan biasa)"; break;
        case WIFI_AUTH_WPA_WPA2_PSK: enkripsi = "WPA/WPA2-PSK"; break;
        case WIFI_AUTH_WPA2_ENTERPRISE: enkripsi = "WPA2-ENTERPRISE (butuh username+password)"; break;
        default: enkripsi = "Tidak diketahui"; break;
      }
      Serial.printf("%2d | %-30s | %4ld dBm    | %3d     | %s\n",
        i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.channel(i), enkripsi.c_str());
    }

    Serial.println("\n=== CARA BACA HASIL INI ===");
    Serial.println("1. Kalau nama WiFi gudang Anda TIDAK MUNCUL sama sekali di daftar di atas,");
    Serial.println("   berarti WiFi itu disiarkan di 5GHz (ESP32 tidak bisa lihat 5GHz sama sekali).");
    Serial.println("2. Kalau MUNCUL tapi keamanannya 'WPA2-ENTERPRISE', firmware standar kita");
    Serial.println("   TIDAK BISA connect ke jenis ini -- perlu kode khusus WPA2-Enterprise.");
    Serial.println("3. Kalau muncul dengan WPA2-PSK biasa tapi sinyal di bawah -75 dBm,");
    Serial.println("   sinyalnya terlalu lemah di lokasi kulkas -- perlu WiFi extender di dekat situ.");
  }
}

void loop() {
  delay(10000);
  Serial.println("\n--- Memindai ulang ---");
  setup();
}
