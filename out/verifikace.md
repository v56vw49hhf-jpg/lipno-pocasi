# Jak se modely trefují v Černé v Pošumaví

Období: 10. 10. 2026 až 16. 11. 2026. Měřítko: stanice ČHMÚ Černá v Pošumaví (740 m), desetiminutová data převedená na hodinová. Předpovědi: archiv Open-Meteo, vždy to, co model říkal 1, 2, 3 a 5 dní předem. Časy v UTC.

Chyba = průměrná absolutní odchylka předpovědi od měření (menší je lepší). Odchylka = průměr (předpověď − měření); kladná znamená, že model nadsazuje.
## Shrnutí

| Veličina | Předstih | Nejlepší jednotlivý model | Kalibrovaná směs | Zlepšení |
|---|---|---|---|---|
| Teplota | +1 d | 1,23 | 1,63 | −33 % |
| Teplota | +2 d | 1,28 | 1,64 | −28 % |
| Teplota | +3 d | 1,54 | 1,72 | −12 % |
| Teplota | +5 d | 1,79 | 2,03 | −13 % |
| Vítr (průměr) | +1 d | 0,70 | 0,67 | 4 % |
| Vítr (průměr) | +2 d | 0,73 | 0,70 | 3 % |
| Vítr (průměr) | +3 d | 0,73 | 0,67 | 8 % |
| Vítr (průměr) | +5 d | 0,76 | 0,75 | 1 % |
| Nárazy větru | +1 d | 1,28 | 1,09 | 15 % |
| Nárazy větru | +2 d | 1,39 | 1,20 | 14 % |
| Nárazy větru | +3 d | 1,49 | 1,23 | 18 % |
| Nárazy větru | +5 d | 1,79 | 1,59 | 11 % |


## Teplota (°C)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 1,27 | – | – | – | 0,20 | 354 |
| UKMO 10 km | 1,45 | 1,54 | 1,74 | 2,40 | 0,73 | 912 |
| HARMONIE-DMI 2 km | 1,55 | – | – | – | 0,53 | 912 |
| HARMONIE-KNMI 5,5 km | 1,55 | – | – | – | 0,58 | 912 |
| ALADIN-CZ 1 km | 1,59 | 1,59 | – | – | 0,60 | 912 |
| ALADIN-CE 2,3 km | 1,65 | 1,63 | – | – | 0,72 | 912 |
| AROME-FR 1,3 km | 1,70 | – | – | – | 0,60 | 912 |
| ARPEGE 11 km | 1,70 | 1,75 | 1,89 | – | 0,79 | 912 |
| ECMWF AIFS (AI) | 1,74 | 1,75 | 1,79 | 2,07 | 0,87 | 912 |
| ICON-CH2 2 km | 1,75 | 1,85 | 1,98 | – | 1,17 | 912 |
| GEM 15 km | 1,76 | 1,86 | 2,00 | 2,50 | 1,02 | 912 |
| ECMWF IFS 9 km | 1,83 | 1,90 | 2,00 | 2,40 | 0,88 | 912 |
| ICON 13 km | 1,84 | 1,92 | 2,15 | 2,66 | 1,54 | 912 |
| ICON-D2 2 km | 1,84 | – | – | – | 1,45 | 912 |
| Open-Meteo best match | 1,84 | 2,10 | 2,33 | 2,66 | 1,45 | 912 |
| ECMWF IFS 0,25° | 2,00 | 2,05 | 2,16 | 2,50 | 1,16 | 912 |
| ICON-EU 7 km | 2,01 | 2,10 | 2,33 | – | 1,77 | 912 |
| GFS 13 km | 2,08 | 2,17 | 2,27 | 2,34 | 1,09 | 912 |

**Kalibrovaná směs proti jednotlivým modelům** (jen období, kdy už je z čeho kalibrovat; směs smí použít jen data starší než den vydání předpovědi):

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 1,63 | 1,23 (UKMO 10 km) | 1,31 | 1,53 | −33 % | 600 |
| +2 d | 1,64 | 1,28 (UKMO 10 km) | 1,38 | 1,82 | −28 % | 552 |
| +3 d | 1,72 | 1,54 (ECMWF AIFS (AI)) | 1,53 | 1,99 | −12 % | 504 |
| +5 d | 2,03 | 1,79 (ECMWF AIFS (AI)) | 1,84 | 2,24 | −13 % | 408 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| zima (XI–III) | +1 d | 1,64 | 1,27 (C-LAEF 1 km) | 384 |
| zima (XI–III) | +3 d | 1,68 | 1,45 (UKMO 10 km) | 384 |

Odchylka teploty podle denní doby (předstih 1 den, hodiny v UTC; SEČ = UTC + 1):

| Model | 00 h | 03 h | 06 h | 09 h | 12 h | 15 h | 18 h | 21 h |
|---|---|---|---|---|---|---|---|---|
| C-LAEF 1 km | 0,4 | 0,0 | 0,0 | 0,2 | 0,2 | 0,1 | 0,0 | 0,3 |
| UKMO 10 km | 0,6 | 0,6 | 0,6 | 0,8 | 0,2 | 0,2 | 1,2 | 1,2 |
| HARMONIE-DMI 2 km | 0,6 | 0,5 | 0,5 | 0,6 | 0,2 | 0,1 | 0,5 | 0,8 |
| HARMONIE-KNMI 5,5 km | 0,8 | 0,6 | 0,6 | 0,7 | 0,1 | 0,1 | 0,6 | 1,0 |
| ALADIN-CZ 1 km | 0,5 | 0,4 | 0,0 | 0,5 | 0,5 | 0,5 | 0,9 | 1,0 |
| ALADIN-CE 2,3 km | 0,7 | 0,6 | 0,2 | 0,4 | 0,5 | 0,6 | 1,1 | 1,3 |
| AROME-FR 1,3 km | 1,0 | 0,9 | 0,5 | 0,0 | −0,2 | 0,0 | 0,9 | 1,3 |
| ARPEGE 11 km | 1,0 | 1,1 | 0,7 | 0,5 | 0,4 | 0,4 | 1,0 | 1,1 |

## Vítr (průměr) (m/s)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 0,62 | – | – | – | −0,01 | 354 |
| ICON 13 km | 0,74 | 0,78 | 0,78 | 1,07 | −0,16 | 912 |
| GEM 15 km | 0,76 | 0,77 | 0,84 | 0,97 | −0,28 | 912 |
| ALADIN-CZ 1 km | 0,78 | 0,83 | – | – | 0,22 | 912 |
| GFS 13 km | 0,79 | 0,83 | 0,85 | 0,96 | −0,05 | 912 |
| HARMONIE-DMI 2 km | 0,80 | – | – | – | 0,04 | 912 |
| ALADIN-CE 2,3 km | 0,81 | 0,86 | – | – | 0,34 | 912 |
| UKMO 10 km | 0,83 | 0,84 | 0,82 | 1,03 | 0,14 | 912 |
| HARMONIE-KNMI 5,5 km | 0,83 | – | – | – | 0,06 | 912 |
| ECMWF IFS 0,25° | 0,86 | 0,89 | 0,89 | 1,05 | 0,19 | 912 |
| ECMWF AIFS (AI) | 0,86 | 0,88 | 0,87 | 1,01 | 0,36 | 912 |
| ICON-D2 2 km | 0,88 | – | – | – | 0,36 | 912 |
| Open-Meteo best match | 0,88 | 0,89 | 0,95 | 1,07 | 0,36 | 912 |
| ICON-CH2 2 km | 0,88 | 0,93 | 1,00 | – | 0,42 | 912 |
| ICON-EU 7 km | 0,90 | 0,89 | 0,95 | – | 0,27 | 912 |
| AROME-FR 1,3 km | 0,91 | – | – | – | 0,45 | 912 |
| ECMWF IFS 9 km | 0,95 | 0,99 | 0,98 | 1,10 | 0,50 | 912 |
| ARPEGE 11 km | 1,01 | 1,08 | 1,14 | – | 0,50 | 912 |

**Kalibrovaná směs proti jednotlivým modelům** (jen období, kdy už je z čeho kalibrovat; směs smí použít jen data starší než den vydání předpovědi):

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 0,67 | 0,70 (ICON 13 km) | 0,71 | 0,91 | 4 % | 672 |
| +2 d | 0,70 | 0,73 (ICON 13 km) | 0,74 | 0,91 | 3 % | 624 |
| +3 d | 0,67 | 0,73 (GEM 15 km) | 0,70 | 0,91 | 8 % | 576 |
| +5 d | 0,75 | 0,76 (GEM 15 km) | 0,72 | 0,90 | 1 % | 480 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| zima (XI–III) | +1 d | 0,61 | 0,62 (C-LAEF 1 km) | 384 |
| zima (XI–III) | +3 d | 0,64 | 0,68 (GEM 15 km) | 384 |

## Nárazy větru (m/s)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 1,18 | – | – | – | −0,36 | 354 |
| ALADIN-CZ 1 km | 1,28 | 1,40 | – | – | 0,23 | 912 |
| ALADIN-CE 2,3 km | 1,32 | 1,44 | – | – | 0,34 | 912 |
| ICON-D2 2 km | 1,34 | – | – | – | 0,27 | 912 |
| Open-Meteo best match | 1,34 | 1,44 | 1,55 | 3,18 | 0,27 | 912 |
| ICON-EU 7 km | 1,38 | 1,44 | 1,55 | – | 0,36 | 912 |
| AROME-FR 1,3 km | 1,40 | – | – | – | 0,24 | 912 |
| UKMO 10 km | 1,42 | 1,47 | 1,53 | 1,98 | 0,15 | 912 |
| HARMONIE-DMI 2 km | 1,42 | – | – | – | 0,17 | 912 |
| ICON-CH2 2 km | 1,45 | 1,61 | 1,74 | – | 0,55 | 912 |
| ARPEGE 11 km | 1,55 | 1,70 | 1,85 | – | 0,61 | 912 |
| HARMONIE-KNMI 5,5 km | 1,56 | – | – | – | 0,54 | 912 |
| GEM 15 km | 1,70 | 1,67 | 1,85 | 2,13 | −0,55 | 912 |
| GFS 13 km | 2,01 | 2,12 | 2,20 | 2,40 | −0,50 | 912 |
| ICON 13 km | 2,88 | 2,89 | 2,88 | 3,18 | 2,71 | 912 |

**Kalibrovaná směs proti jednotlivým modelům** (jen období, kdy už je z čeho kalibrovat; směs smí použít jen data starší než den vydání předpovědi):

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 1,09 | 1,28 (ALADIN-CZ 1 km) | 1,18 | 1,35 | 15 % | 672 |
| +2 d | 1,20 | 1,39 (ALADIN-CZ 1 km) | 1,32 | 1,48 | 14 % | 624 |
| +3 d | 1,23 | 1,49 (UKMO 10 km) | 1,32 | 1,50 | 18 % | 576 |
| +5 d | 1,59 | 1,79 (UKMO 10 km) | 1,62 | 3,13 | 11 % | 480 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| zima (XI–III) | +1 d | 1,04 | 1,18 (C-LAEF 1 km) | 384 |
| zima (XI–III) | +3 d | 1,23 | 1,52 (ICON-CH2 2 km) | 384 |

## Srážky (denní úhrny, mm)

Zachycené deště = podíl dní s naměřeným úhrnem aspoň 1 mm, které model předpověděl. Plané poplachy = podíl dní, kdy model dal aspoň 1 mm a nenapršelo.

| Model | Chyba +1 den | Odchylka +1 den | Zachycené deště | Plané poplachy | Chyba +3 dny | Dní |
|---|---|---|---|---|---|---|

Zdroje: předpovědi Open-Meteo.com (CC BY 4.0), měření ČHMÚ (opendata.chmi.cz).
