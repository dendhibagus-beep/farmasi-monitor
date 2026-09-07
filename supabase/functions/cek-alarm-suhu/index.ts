// Supabase Edge Function: cek-alarm-suhu
// ==========================================================================
// Dipicu otomatis oleh Database Webhook setiap ada INSERT baru ke tabel
// `log_suhu` (yaitu setiap sensor ESP32/ESP8266 mengirim data). Fungsi ini:
//   1. Mengambil ambang batas efektif untuk ruangan tsb — pakai kustom dari
//      tabel `ambang_batas` (diatur admin lewat modul Pengaturan) jika ada,
//      kalau tidak jatuh ke standar default berdasarkan kategori nama.
//   2. Mengevaluasi apakah suhu/kelembapan di luar standar.
//   3. Melakukan debounce (tidak spam) memakai tabel `alarm_log`.
//   4. Mengirim notifikasi ke Telegram dan/atau WhatsApp jika perlu,
//      baik saat ALARM BARU MULAI maupun saat KONDISI KEMBALI NORMAL.
//
// Deploy:
//   supabase functions deploy cek-alarm-suhu
//   supabase secrets set SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
//       TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_IDS=... \
//       FONNTE_TOKEN=... WHATSAPP_NUMBERS=... REMINDER_INTERVAL_MENIT=30
//
// Lalu buat Database Webhook di Supabase Dashboard:
//   Database -> Webhooks -> Create a new hook
//   Table: log_suhu | Events: Insert | Type: Supabase Edge Function -> pilih fungsi ini
// ==========================================================================

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
const TELEGRAM_CHAT_IDS = (Deno.env.get("TELEGRAM_CHAT_IDS") ?? "")
  .split(",").map((s) => s.trim()).filter(Boolean);

const FONNTE_TOKEN = Deno.env.get("FONNTE_TOKEN") ?? "";
const WHATSAPP_NUMBERS = (Deno.env.get("WHATSAPP_NUMBERS") ?? "")
  .split(",").map((s) => s.trim()).filter(Boolean);

const REMINDER_INTERVAL_MENIT = Number(Deno.env.get("REMINDER_INTERVAL_MENIT") ?? "30");

const STANDAR_DEFAULT: Record<string, { suhuMin: number; suhuMax: number; lembabMin: number; lembabMax: number }> = {
  kulkas: { suhuMin: 2.0, suhuMax: 8.0, lembabMin: 0, lembabMax: 100 },
  default: { suhuMin: 18.0, suhuMax: 25.0, lembabMin: 35, lembabMax: 65 },
};

async function getStandarEfektif(
  supabase: ReturnType<typeof createClient>,
  lokasi: string,
): Promise<{ suhuMin: number; suhuMax: number; lembabMin: number; lembabMax: number }> {
  const { data } = await supabase
    .from("ambang_batas")
    .select("*")
    .eq("lokasi", lokasi)
    .maybeSingle();

  if (data) {
    return {
      suhuMin: Number(data.suhu_min),
      suhuMax: Number(data.suhu_max),
      lembabMin: Number(data.lembab_min),
      lembabMax: Number(data.lembab_max),
    };
  }
  return lokasi.toLowerCase().includes("kulkas") ? STANDAR_DEFAULT.kulkas : STANDAR_DEFAULT.default;
}

function evaluasi(suhu: number, lembab: number, s: { suhuMin: number; suhuMax: number; lembabMin: number; lembabMax: number }) {
  if (suhu < s.suhuMin) return { level: "danger", status: "OVER-CHILLED", pesan: `Suhu terlalu DINGIN (${suhu}°C)` };
  if (suhu > s.suhuMax) return { level: "danger", status: "OVER-HEATED", pesan: `Suhu terlalu PANAS (${suhu}°C)` };
  if (lembab < s.lembabMin || lembab > s.lembabMax) {
    return { level: "warning", status: "KELEMBAPAN TIDAK STANDAR", pesan: `Kelembapan di luar rentang (${lembab}%)` };
  }
  return { level: "ok", status: "AMAN TERKENDALI", pesan: "Kondisi stabil" };
}

async function kirimTelegram(text: string) {
  if (!TELEGRAM_BOT_TOKEN || TELEGRAM_CHAT_IDS.length === 0) return;
  await Promise.all(TELEGRAM_CHAT_IDS.map((chatId) =>
    fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text, parse_mode: "Markdown" }),
    }).catch((e) => console.error("Telegram error:", e))
  ));
}

async function kirimWhatsApp(text: string) {
  // Menggunakan Fonnte (https://fonnte.com). Provider lain? Ganti blok ini sesuai
  // dokumentasi API-nya — format pesan & alur lainnya tidak perlu diubah.
  if (!FONNTE_TOKEN || WHATSAPP_NUMBERS.length === 0) return;
  await fetch("https://api.fonnte.com/send", {
    method: "POST",
    headers: {
      "Authorization": FONNTE_TOKEN,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      target: WHATSAPP_NUMBERS.join(","),
      message: text,
    }),
  }).catch((e) => console.error("WhatsApp/Fonnte error:", e));
}

function susunPesan(lokasi: string, suhu: number, lembab: number, evalHasil: { level: string; status: string; pesan: string }, kembaliNormal: boolean) {
  const waktu = new Date().toLocaleString("id-ID", { timeZone: "Asia/Jakarta" });
  if (kembaliNormal) {
    return `✅ *NORMAL KEMBALI*\n📍 Ruangan: ${lokasi}\n🌡️ Suhu: ${suhu}°C | 💧 Kelembapan: ${lembab}%\n🕒 ${waktu} WIB\n\nKondisi telah kembali ke rentang aman.`;
  }
  const icon = evalHasil.level === "danger" ? "🔴" : "🟡";
  return `${icon} *ALARM: ${evalHasil.status}*\n📍 Ruangan: ${lokasi}\n🌡️ Suhu: ${suhu}°C | 💧 Kelembapan: ${lembab}%\n🕒 ${waktu} WIB\n\n${evalHasil.pesan}. Segera periksa & tindak lanjuti sesuai SOP.`;
}

Deno.serve(async (req: Request) => {
  try {
    const payload = await req.json();
    const record = payload.record ?? payload; // dukung format Database Webhook Supabase

    const lokasi: string = record.lokasi;
    const suhu: number = Number(record.suhu);
    const lembab: number = Number(record.kelembapan);

    if (!lokasi || Number.isNaN(suhu) || Number.isNaN(lembab)) {
      return new Response(JSON.stringify({ ok: false, error: "Payload tidak lengkap" }), { status: 400 });
    }

    const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
    const standar = await getStandarEfektif(supabase, lokasi);
    const hasil = evaluasi(suhu, lembab, standar);

    const { data: existing } = await supabase
      .from("alarm_log")
      .select("*")
      .eq("lokasi", lokasi)
      .maybeSingle();

    const now = new Date();
    const reminderMs = REMINDER_INTERVAL_MENIT * 60 * 1000;

    let kirimNotif = false;
    let kembaliNormal = false;

    if (hasil.level !== "ok") {
      const statusSebelumnyaNormal = !existing || existing.last_status === "ok";
      const waktuSejakNotifTerakhir = existing?.last_notified_at
        ? now.getTime() - new Date(existing.last_notified_at).getTime()
        : Infinity;

      if (statusSebelumnyaNormal || waktuSejakNotifTerakhir > reminderMs) {
        kirimNotif = true;
      }
    } else if (existing && existing.last_status && existing.last_status !== "ok") {
      kirimNotif = true;
      kembaliNormal = true;
    }

    if (kirimNotif) {
      const pesan = susunPesan(lokasi, suhu, lembab, hasil, kembaliNormal);
      await Promise.all([kirimTelegram(pesan), kirimWhatsApp(pesan)]);
    }

    await supabase.from("alarm_log").upsert({
      lokasi,
      last_status: hasil.level,
      last_notified_at: kirimNotif ? now.toISOString() : (existing?.last_notified_at ?? null),
      updated_at: now.toISOString(),
    }, { onConflict: "lokasi" });

    return new Response(JSON.stringify({ ok: true, notified: kirimNotif, level: hasil.level }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error(err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), { status: 500 });
  }
});
