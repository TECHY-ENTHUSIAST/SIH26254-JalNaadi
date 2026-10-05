// NAADI-EAR node configuration  (reference skeleton - not yet run on hardware)
#pragma once
// ---- identity
#define NODE_ID        "E01"
#define PAIR_ROLE_MASTER 1      // 1 = pair master (node B: receives A's burst and correlates), 0 = slave (node A: records and sends)
#define SEGMENT_ID     "S1"
#define SEGMENT_LEN_M  8.0f     // L between node A and node B (measured on site)
#define WAVE_SPEED_MS  400.0f   // overwritten by one-tap commissioning, stored in NVS
// ---- LoRa (India delicensed band 865-867 MHz, <= 200 kHz carrier)
#define LORA_FREQ_MHZ  866.0f
#define LORA_BW_KHZ    125.0f
#define LORA_SF        9
#define LORA_PWR_DBM   14
// ---- pins (ESP32-WROVER-E; VSPI = accelerometer, HSPI = LoRa)
#define PIN_ACC_CS 5
#define PIN_ACC_SCK 18
#define PIN_ACC_MISO 19
#define PIN_ACC_MOSI 23
#define PIN_LORA_CS 15
#define PIN_LORA_SCK 14
#define PIN_LORA_MISO 12
#define PIN_LORA_MOSI 13
#define PIN_LORA_DIO0 26
#define PIN_LORA_RST 25
// ---- sampling (ADXL345 max ODR 3200 Hz; use ADXL355 for 4000 Hz, keep both nodes identical)
#define FS_HZ          3200
#define RECORD_S       10
#define N_SAMPLES      (FS_HZ * RECORD_S)
#define START_OFFSET_US 200000  // both nodes start measuring this long after the beacon RX interrupt
#define WAKE_CHECK_S   900      // 15-min LoRa wake-check (96/day)
#define DEEP_SLEEP_AFTER_MS 20000
// ---- classifier thresholds (tune on the rig; see analysis/jalnaadi/dsp.py)
#define RMS_FLOOR      0.12f
#define TONAL_MAX      12.0f
#define KURT_MAX       2.0f
#define BAND_MIN       0.60f
