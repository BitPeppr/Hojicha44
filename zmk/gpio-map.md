# Hojicha44 GPIO continuity map

Machine-generated from the exported netlists + spec `nrf_mapping`.
Left and right halves are electrically identical except TRRS pins 1/2.

## Left (U_L1)

| pin | Arduino | nRF | net | function |
|---|---|---|---|---|
| 1 | D1 | P0.06 | /TRRS_T | TRRS tip |
| 2 | D0 | P0.08 | /TRRS_R1 | TRRS ring1 |
| 3 | GND | — | GND | GND |
| 4 | GND | — | GND | GND |
| 5 | D2 | P0.17 | /COL2_L | COL2 |
| 6 | D3 | P0.20 | /COL3_L | COL3 |
| 7 | D4 | P0.22 | /ROW0_L | ROW0 |
| 8 | D5 | P0.24 | /ROW1_L | ROW1 |
| 9 | D6 | P1.00 | /ROW2_L | ROW2 |
| 10 | D7 | P0.11 | /ROW3_L | ROW3 |
| 11 | D8 | P1.04 | /COL0_L | COL0 |
| 12 | D9 | P1.06 | /COL1_L | COL1 |
| 13 | D10 | P0.09 | /D10_L | D10 spare |
| 14 | D16 | P0.10 | /ENC_SW_L | ENC push |
| 15 | D14 | P1.11 | /COL4_L | COL4 |
| 16 | D15 | P1.13 | /COL5_L | COL5 |
| 17 | A0 | P1.15 | /ENC_A_L | ENC A |
| 18 | A1 | P0.02 | /ENC_B_L | ENC B |
| 19 | A2 | P0.29 | /A2_L | A2 spare |
| 20 | A3 | P0.31 | /A3_L | A3 spare |
| 21 | VCC | — | /VCC3V3_L | VCC 3V3 |
| 22 | RST | — | /RST_L | RST |
| 23 | GND | — | GND | GND |
| 24 | RAW | — | /VBAT_SW_L | VBAT (RAW) |

## Right (U_R1)

| pin | Arduino | nRF | net | function |
|---|---|---|---|---|
| 1 | D1 | P0.06 | /TRRS_R1 | TRRS tip |
| 2 | D0 | P0.08 | /TRRS_T | TRRS ring1 |
| 3 | GND | — | GND | GND |
| 4 | GND | — | GND | GND |
| 5 | D2 | P0.17 | /COL2_R | COL2 |
| 6 | D3 | P0.20 | /COL3_R | COL3 |
| 7 | D4 | P0.22 | /ROW0_R | ROW0 |
| 8 | D5 | P0.24 | /ROW1_R | ROW1 |
| 9 | D6 | P1.00 | /ROW2_R | ROW2 |
| 10 | D7 | P0.11 | /ROW3_R | ROW3 |
| 11 | D8 | P1.04 | /COL0_R | COL0 |
| 12 | D9 | P1.06 | /COL1_R | COL1 |
| 13 | D10 | P0.09 | /D10_R | D10 spare |
| 14 | D16 | P0.10 | /ENC_SW_R | ENC push |
| 15 | D14 | P1.11 | /COL4_R | COL4 |
| 16 | D15 | P1.13 | /COL5_R | COL5 |
| 17 | A0 | P1.15 | /ENC_A_R | ENC A |
| 18 | A1 | P0.02 | /ENC_B_R | ENC B |
| 19 | A2 | P0.29 | /A2_R | A2 spare |
| 20 | A3 | P0.31 | /A3_R | A3 spare |
| 21 | VCC | — | /VCC3V3_R | VCC 3V3 |
| 22 | RST | — | /RST_R | RST |
| 23 | GND | — | GND | GND |
| 24 | RAW | — | /VBAT_SW_R | VBAT (RAW) |
