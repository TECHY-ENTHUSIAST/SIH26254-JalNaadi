// NAADI-GATE reference skeleton: zone inlet flow + pressure logger with nightly 02:00-04:00 mean and LoRa uplink.
// STATUS: skeleton, not yet run on hardware. Field deployments should read the existing JJM bulk flow meter instead.
#include <Arduino.h>
#include <RadioLib.h>
#include <esp_sleep.h>
#define PIN_FLOW   27      // Hall flow sensor pulse input (YF-S201 class: ~7.5 Hz per L/min; calibrate on the rig)
#define PIN_PRESS  34      // 0.5-4.5 V transducer through a divider to <= 3.3 V (ADC1)
#define K_PULSE_PER_LMIN 7.5f
#define ZONE_ID "Z1"
RTC_DATA_ATTR float nightSum = 0; RTC_DATA_ATTR int nightN = 0; RTC_DATA_ATTR uint32_t secOfDay = 0;
volatile uint32_t pulses = 0; void IRAM_ATTR onPulse() { pulses++; }
float readPressureBar() { float v = analogReadMilliVolts(PIN_PRESS) / 1000.0f * (5.0f / 3.3f); return (v - 0.5f) / 4.0f * 12.0f; /* 0-12 bar span: edit */ }
void setup() {
  pinMode(PIN_FLOW, INPUT_PULLUP); attachInterrupt(PIN_FLOW, onPulse, RISING);
  uint32_t t0 = millis(); pulses = 0; while (millis() - t0 < 10000) delay(10);          // 10 s gate time
  float lmin = (pulses / 10.0f) / K_PULSE_PER_LMIN, m3h = lmin * 0.06f; float bar = readPressureBar();
  secOfDay = (secOfDay + 900) % 86400;                                                    // 15-min cycle; sync clock from gateway beacon (TODO)
  if (secOfDay >= 7200 && secOfDay < 14400) { nightSum += m3h; nightN++; }
  if (secOfDay == 14400 && nightN > 0) {                                                  // 04:00 -> uplink the night mean
    // TODO: radio.transmit("{\"gid\":\"G01\",\"did\":\"GATE1\",\"dty\":\"gate\",\"dt\":..,\"p\":{\"zone\":\"Z1\",\"qn\":<nightSum/nightN>,\"pb\":<bar>}}");
    nightSum = 0; nightN = 0;
  }
  esp_sleep_enable_timer_wakeup(890ULL * 1000000ULL); esp_deep_sleep_start();
}
void loop() {}
