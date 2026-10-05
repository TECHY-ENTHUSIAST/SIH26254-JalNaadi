# Node wiring (reference)
| Signal | ESP32 pin | Note |
|---|---|---|
| ADXL345 CS / SCK / MISO / MOSI | 5 / 18 / 19 / 23 | VSPI, 5 MHz, SPI mode 3 |
| SX1276 CS / SCK / MISO / MOSI | 15 / 14 / 12 / 13 | HSPI |
| SX1276 DIO0 / RST | 26 / 25 | DIO0 = RxDone interrupt used for beacon timestamps |
| GATE flow pulse | 27 | Hall sensor, pull-up |
| GATE pressure | 34 | 0.5-4.5 V transducer via divider (ADC1) |
Power: 18650 -> charger (solar in) -> 3.3 V low-Iq regulator. Use a low-quiescent regulator and no USB-UART chip on the deployed board, otherwise deep-sleep current is far above 0.15 mA.
