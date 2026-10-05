// NAADI-EAR reference skeleton: beacon-synchronised vibration burst -> classify -> pair exchange (ESP-NOW)
// -> GCC-PHAT on the pair master -> compact result over LoRa.
// STATUS: skeleton written from the design in docs/; compiles are not yet verified, nothing here has run on hardware.
// Libraries: RadioLib, arduinoFFT (v2), ESP-DSP (esp-dsp), ESP32 Arduino core 2.x.
#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_timer.h>
#include <esp_sleep.h>
#include <RadioLib.h>
#include "config.h"

SPIClass loraSPI(HSPI);
SX1276 radio = new Module(PIN_LORA_CS, PIN_LORA_DIO0, PIN_LORA_RST, RADIOLIB_NC, loraSPI);
volatile int64_t tBeaconRx = 0;      // esp_timer microseconds at the beacon RxDone interrupt (same instant at every node)
volatile bool beaconFlag = false;
static int16_t rec[N_SAMPLES];       // own burst (z-axis, raw counts); use PSRAM (ESP32-WROVER) for the pair copy
static int16_t *peer = nullptr;      // partner burst received over ESP-NOW (heap_caps_malloc in PSRAM)
volatile uint32_t peerCount = 0;

struct __attribute__((packed)) Chunk { uint16_t seq; int16_t s[110]; };   // 222 B < 250 B ESP-NOW limit

void IRAM_ATTR onBeacon() { tBeaconRx = esp_timer_get_time(); beaconFlag = true; }

// ---------------------------------------------------------------- ADXL345 (SPI, FIFO stream mode)
void accWrite(uint8_t r, uint8_t v) { digitalWrite(PIN_ACC_CS, LOW); SPI.transfer(r); SPI.transfer(v); digitalWrite(PIN_ACC_CS, HIGH); }
uint8_t accRead(uint8_t r) { digitalWrite(PIN_ACC_CS, LOW); SPI.transfer(r | 0x80); uint8_t v = SPI.transfer(0); digitalWrite(PIN_ACC_CS, HIGH); return v; }
void accBegin() {
  SPI.begin(PIN_ACC_SCK, PIN_ACC_MISO, PIN_ACC_MOSI, PIN_ACC_CS);
  SPI.beginTransaction(SPISettings(5000000, MSBFIRST, SPI_MODE3));
  accWrite(0x2D, 0x00);            // standby
  accWrite(0x2C, 0x0F);            // BW_RATE = 3200 Hz
  accWrite(0x31, 0x0B);            // FULL_RES, +/-16 g
  accWrite(0x38, 0x80 | 0x1F);     // FIFO stream, 31-sample watermark
}
void accStartMeasure() { accWrite(0x2D, 0x08); }
void accStandby() { accWrite(0x2D, 0x00); }
int accFifoLevel() { return accRead(0x39) & 0x3F; }
int16_t accReadZ() {               // read one FIFO entry (6 bytes), keep Z
  digitalWrite(PIN_ACC_CS, LOW); SPI.transfer(0x32 | 0xC0);
  SPI.transfer(0); SPI.transfer(0); SPI.transfer(0); SPI.transfer(0);
  uint8_t zl = SPI.transfer(0), zh = SPI.transfer(0);
  digitalWrite(PIN_ACC_CS, HIGH); return (int16_t)((zh << 8) | zl);
}

// ---------------------------------------------------------------- synchronous recording
void recordBurst() {
  while ((esp_timer_get_time() - tBeaconRx) < START_OFFSET_US) { /* spin: <1 ms resolution is enough */ }
  accStartMeasure();
  uint32_t n = 0;
  while (n < N_SAMPLES) { int lvl = accFifoLevel(); while (lvl-- > 0 && n < N_SAMPLES) rec[n++] = accReadZ(); }
  accStandby();
}

// ---------------------------------------------------------------- features (rule-based classifier, see dsp.py)
struct Feat { float rms, kurt, tonal, bandRatio; };
Feat computeFeatures() {
  Feat f{}; double mean = 0; for (uint32_t i = 0; i < N_SAMPLES; i++) mean += rec[i]; mean /= N_SAMPLES;
  double m2 = 0, m4 = 0; for (uint32_t i = 0; i < N_SAMPLES; i++) { double d = rec[i] - mean; m2 += d * d; m4 += d * d * d * d; }
  m2 /= N_SAMPLES; m4 /= N_SAMPLES; f.rms = sqrt(m2); f.kurt = m4 / (m2 * m2) - 3.0;
  // TODO: Welch PSD with arduinoFFT (512-pt Hann segments, 50% overlap) -> f.tonal (local line prominence), f.bandRatio (50-1000 Hz energy fraction)
  return f;
}
const char* classify(const Feat& f) {
  if (f.rms <= RMS_FLOOR) return "quiet";
  if (f.kurt > KURT_MAX) return "tap";
  if (f.tonal > TONAL_MAX) return "pump";
  if (f.bandRatio >= BAND_MIN) return "leak";
  return "quiet";
}

// ---------------------------------------------------------------- pair exchange (ESP-NOW)
uint8_t PEER_MAC[6] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x01};   // TODO: set to partner node MAC
void onPeerChunk(const uint8_t*, const uint8_t* data, int len) {
  const Chunk* c = (const Chunk*)data; if (!peer || len < 2) return;
  uint32_t base = (uint32_t)c->seq * 110; for (int i = 0; i < 110 && base + i < N_SAMPLES; i++) peer[base + i] = c->s[i];
  peerCount++;
}
void sendBurstToMaster() {
  Chunk c; for (uint32_t base = 0, seq = 0; base < N_SAMPLES; base += 110, seq++) {
    c.seq = seq; for (int i = 0; i < 110; i++) c.s[i] = (base + i < N_SAMPLES) ? rec[base + i] : 0;
    esp_now_send(PEER_MAC, (uint8_t*)&c, sizeof(c)); delay(2);
  }
}

// ---------------------------------------------------------------- GCC-PHAT on the master
// TODO: implement with ESP-DSP: split into 2 s segments (6400 samples, pad to 8192), dsps_fft2r_fc32 on both,
// R = conj(A)*B / |conj(A)*B| inside 50-1000 Hz, inverse FFT, accumulate over segments, pick the peak within
// +/- L / 200 m/s, refine by parabolic interpolation. Reference implementation: analysis/jalnaadi/dsp.py gcc_phat().
bool gccPhat(float &tauS, float &ratio) { tauS = 0; ratio = 0; return false; }

void sendResult(float x, float cf, const char* cls) {
  char json[120];
  snprintf(json, sizeof(json), "{\"gid\":\"G01\",\"did\":\"%s\",\"dty\":\"ear\",\"dt\":%lu,\"p\":{\"seg\":\"%s\",\"x\":%.2f,\"L\":%.1f,\"v\":%.0f,\"cf\":%.1f,\"cls\":\"%s\"}}",
           NODE_ID, (unsigned long)(millis() / 1000), SEGMENT_ID, x, SEGMENT_LEN_M, WAVE_SPEED_MS, cf, cls);
  radio.transmit(json);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_ACC_CS, OUTPUT); digitalWrite(PIN_ACC_CS, HIGH);
  loraSPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_CS);
  radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, 7, RADIOLIB_SX127X_SYNC_WORD, LORA_PWR_DBM);
  radio.setPacketReceivedAction(onBeacon);
  radio.startReceive();                                    // wake-check window (~1 s)
  WiFi.mode(WIFI_STA); esp_now_init(); esp_now_register_recv_cb(onPeerChunk);
  esp_now_peer_info_t p{}; memcpy(p.peer_addr, PEER_MAC, 6); p.channel = 0; esp_now_add_peer(&p);
  accBegin();
  uint32_t t0 = millis();
  while (!beaconFlag && millis() - t0 < 1000) delay(1);
  if (beaconFlag) {                                        // beacon = "listen now": every node timestamps the same RxDone instant
    String pkt; radio.readData(pkt);                       // payload: epoch, window flags, sequence
    recordBurst();
    Feat f = computeFeatures(); const char* cls = classify(f);
    if (!PAIR_ROLE_MASTER) { if (!strcmp(cls, "leak")) sendBurstToMaster(); }
    else if (!strcmp(cls, "leak")) {
      peer = (int16_t*)heap_caps_malloc(N_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM); delay(3000);   // wait for A's chunks
      float tau, ratio; if (gccPhat(tau, ratio)) sendResult((SEGMENT_LEN_M - WAVE_SPEED_MS * tau) / 2.0f, ratio, cls);
    }
  }
  esp_sleep_enable_timer_wakeup((uint64_t)WAKE_CHECK_S * 1000000ULL);
  esp_deep_sleep_start();
}
void loop() {}
