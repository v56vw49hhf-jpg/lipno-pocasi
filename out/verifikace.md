# Jak se modely trefují v Černé v Pošumaví

Období: 1. 10. 2025 až 16. 11. 2026. Měřítko: stanice ČHMÚ Černá v Pošumaví (740 m), desetiminutová data převedená na hodinová. Předpovědi: archiv Open-Meteo, vždy to, co model říkal 1, 2, 3 a 5 dní předem. Časy v UTC.

Chyba = průměrná absolutní odchylka předpovědi od měření (menší je lepší). Odchylka = průměr (předpověď − měření); kladná znamená, že model nadsazuje.
## Shrnutí

| Veličina | Předstih | Nejlepší jednotlivý model | Prostý průměr modelů | Kalibrovaná směs | Směs proti nejlepšímu |
|---|---|---|---|---|---|
| Teplota | +1 d | 1,91 | 1,97 | 1,78 | 7 % |
| Teplota | +2 d | 2,00 | 2,08 | 1,89 | 6 % |
| Teplota | +3 d | 2,06 | 2,15 | 1,96 | 5 % |
| Teplota | +5 d | 2,59 | 2,52 | 2,32 | 11 % |
| Vítr (průměr) | +1 d | 0,79 | 0,73 | 0,73 | 8 % |
| Vítr (průměr) | +2 d | 0,82 | 0,75 | 0,75 | 8 % |
| Vítr (průměr) | +3 d | 0,88 | 0,78 | 0,78 | 12 % |
| Vítr (průměr) | +5 d | 1,00 | 0,89 | 0,89 | 11 % |
| Nárazy větru | +1 d | 1,46 | 1,29 | 1,27 | 13 % |
| Nárazy větru | +2 d | 1,58 | 1,42 | 1,40 | 11 % |
| Nárazy větru | +3 d | 1,65 | 1,47 | 1,45 | 12 % |
| Nárazy větru | +5 d | 2,00 | 1,73 | 1,72 | 14 % |


## Teplota (°C)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 1,27 | – | – | – | 0,20 | 354 |
| HARMONIE-DMI 2 km | 1,86 | – | – | – | 0,77 | 9169 |
| UKMO 10 km | 1,87 | 1,96 | 2,02 | 2,55 | 1,28 | 8672 |
| HARMONIE-KNMI 5,5 km | 1,88 | – | – | – | 0,85 | 9169 |
| ICON-CH2 2 km | 1,96 | 2,06 | 2,16 | – | 1,35 | 9169 |
| ALADIN-CZ 1 km | 1,98 | 2,06 | – | – | 0,95 | 3504 |
| ALADIN-CE 2,3 km | 2,08 | 2,15 | – | – | 1,14 | 3504 |
| AROME-FR 1,3 km | 2,09 | – | – | – | 0,88 | 9169 |
| ECMWF IFS 9 km | 2,13 | 2,19 | 2,26 | 2,70 | 1,21 | 9024 |
| ICON-D2 2 km | 2,18 | – | – | – | 1,70 | 9169 |
| Open-Meteo best match | 2,18 | 2,27 | 2,38 | 2,95 | 1,70 | 9169 |
| ICON-EU 7 km | 2,19 | 2,27 | 2,38 | – | 1,60 | 9169 |
| ICON 13 km | 2,24 | 2,32 | 2,43 | 2,95 | 1,69 | 9169 |
| GFS 13 km | 2,26 | 2,35 | 2,41 | 2,83 | 1,12 | 9169 |
| GEM 15 km | 2,26 | 2,27 | 2,41 | 2,82 | 1,53 | 9052 |
| ECMWF AIFS (AI) | 2,27 | 2,31 | 2,36 | 2,66 | 1,43 | 9169 |
| ECMWF IFS 0,25° | 2,29 | 2,36 | 2,42 | 2,82 | 1,43 | 9169 |
| ARPEGE 11 km | 2,30 | 2,41 | 2,52 | – | 1,65 | 9169 |

**Který způsob kalibrace funguje nejlíp** (chyba směsi; vše počítáno jen z dat starších než den vydání):

| Způsob | +1 den | +2 dny | +3 dny | +5 dní |
|---|---|---|---|---|
| bez opravy, jen váhy podle úspěšnosti | 1,92 | 2,04 | 2,11 | 2,51 |
| oprava průměrné odchylky, okno 15 dní | 1,94 | 2,05 | 2,12 | 2,50 |
| oprava průměrné odchylky, okno 30 dní | 1,96 | 2,06 | 2,12 | 2,49 |
| oprava průměrné odchylky, okno 60 dní | 1,94 | 2,03 | 2,08 | 2,44 |
| oprava odchylky podle denní doby, okno 30 dní | 1,78 | 1,91 | 1,99 | 2,37 |
| **oprava odchylky podle denní doby, okno 60 dní** | 1,78 | 1,89 | 1,96 | 2,32 |

**Směs (oprava odchylky podle denní doby, okno 60 dní) proti jednotlivým modelům** na stejných hodinách:

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 1,78 | 1,91 (HARMONIE-DMI 2 km) | 1,97 | 2,22 | 7 % | 8401 |
| +2 d | 1,89 | 2,00 (UKMO 10 km) | 2,08 | 2,31 | 6 % | 8305 |
| +3 d | 1,96 | 2,06 (UKMO 10 km) | 2,15 | 2,41 | 5 % | 8209 |
| +5 d | 2,32 | 2,59 (UKMO 10 km) | 2,52 | 3,01 | 11 % | 8017 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| léto (V–IX) | +1 d | 1,60 | 1,75 (UKMO 10 km) | 3288 |
| zima (XI–III) | +1 d | 1,91 | 1,97 (HARMONIE-DMI 2 km) | 4008 |
| léto (V–IX) | +3 d | 1,82 | 2,00 (UKMO 10 km) | 3192 |
| zima (XI–III) | +3 d | 2,03 | 2,10 (UKMO 10 km) | 4008 |

Odchylka teploty podle denní doby (předstih 1 den, hodiny v UTC; SEČ = UTC + 1):

| Model | 00 h | 03 h | 06 h | 09 h | 12 h | 15 h | 18 h | 21 h |
|---|---|---|---|---|---|---|---|---|
| C-LAEF 1 km | 0,4 | 0,0 | 0,0 | 0,2 | 0,2 | 0,1 | 0,0 | 0,3 |
| HARMONIE-DMI 2 km | 1,6 | 1,5 | 0,9 | 0,3 | −0,1 | 0,1 | 0,6 | 1,4 |
| UKMO 10 km | 1,9 | 1,7 | 1,2 | 1,0 | 0,4 | 0,6 | 1,3 | 2,1 |
| HARMONIE-KNMI 5,5 km | 1,7 | 1,6 | 0,9 | 0,4 | −0,1 | 0,1 | 0,7 | 1,5 |
| ICON-CH2 2 km | 2,3 | 2,2 | 1,3 | 0,6 | 0,3 | 0,5 | 1,3 | 2,3 |
| ALADIN-CZ 1 km | 2,3 | 2,2 | 0,5 | −0,3 | −0,3 | −0,4 | 0,8 | 2,5 |
| ALADIN-CE 2,3 km | 2,6 | 2,5 | 0,7 | −0,3 | −0,3 | −0,3 | 1,1 | 2,9 |
| AROME-FR 1,3 km | 2,1 | 2,0 | 0,8 | −0,2 | −0,6 | −0,1 | 1,0 | 2,1 |

## Vítr (průměr) (m/s)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 0,62 | – | – | – | −0,01 | 354 |
| ICON-EU 7 km | 0,78 | 0,82 | 0,89 | – | 0,04 | 9167 |
| ICON 13 km | 0,80 | 0,84 | 0,88 | 1,05 | −0,14 | 9167 |
| ALADIN-CZ 1 km | 0,83 | 0,86 | – | – | 0,21 | 3504 |
| GFS 13 km | 0,84 | 0,88 | 0,91 | 1,07 | −0,07 | 9167 |
| GEM 15 km | 0,85 | 0,87 | 0,92 | 1,05 | −0,40 | 9167 |
| UKMO 10 km | 0,85 | 0,87 | 0,89 | 1,06 | 0,11 | 9167 |
| ICON-D2 2 km | 0,85 | – | – | – | 0,25 | 9167 |
| Open-Meteo best match | 0,85 | 0,82 | 0,89 | 1,05 | 0,25 | 9167 |
| HARMONIE-DMI 2 km | 0,85 | – | – | – | −0,08 | 9167 |
| ALADIN-CE 2,3 km | 0,85 | 0,89 | – | – | 0,33 | 3504 |
| ECMWF AIFS (AI) | 0,86 | 0,87 | 0,90 | 1,01 | 0,08 | 9167 |
| ICON-CH2 2 km | 0,88 | 0,90 | 0,96 | – | 0,28 | 9167 |
| AROME-FR 1,3 km | 0,88 | – | – | – | 0,44 | 2439 |
| HARMONIE-KNMI 5,5 km | 0,89 | – | – | – | −0,09 | 9148 |
| ECMWF IFS 0,25° | 0,89 | 0,90 | 0,94 | 1,08 | 0,12 | 9167 |
| ECMWF IFS 9 km | 0,93 | 0,93 | 0,97 | 1,13 | 0,36 | 9024 |
| ARPEGE 11 km | 1,00 | 1,05 | 1,07 | – | 0,48 | 2436 |

**Který způsob kalibrace funguje nejlíp** (chyba směsi; vše počítáno jen z dat starších než den vydání):

| Způsob | +1 den | +2 dny | +3 dny | +5 dní |
|---|---|---|---|---|
| **bez opravy, jen váhy podle úspěšnosti** | 0,73 | 0,75 | 0,78 | 0,89 |
| přeškálování, okno 15 dní | 0,73 | 0,76 | 0,79 | 0,92 |
| přeškálování, okno 30 dní | 0,73 | 0,76 | 0,79 | 0,91 |
| přeškálování, okno 60 dní | 0,73 | 0,76 | 0,79 | 0,91 |

**Směs (bez opravy, jen váhy podle úspěšnosti) proti jednotlivým modelům** na stejných hodinách:

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 0,73 | 0,79 (ICON-EU 7 km) | 0,73 | 0,85 | 8 % | 8353 |
| +2 d | 0,75 | 0,82 (ICON-EU 7 km) | 0,75 | 0,82 | 8 % | 8257 |
| +3 d | 0,78 | 0,88 (ICON 13 km) | 0,78 | 0,90 | 12 % | 8161 |
| +5 d | 0,89 | 1,00 (ECMWF AIFS (AI)) | 0,89 | 1,05 | 11 % | 7969 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| léto (V–IX) | +1 d | 0,69 | 0,74 (ICON-EU 7 km) | 3264 |
| zima (XI–III) | +1 d | 0,75 | 0,82 (ICON-EU 7 km) | 4008 |
| léto (V–IX) | +3 d | 0,73 | 0,82 (ICON-EU 7 km) | 3168 |
| zima (XI–III) | +3 d | 0,81 | 0,89 (GEM 15 km) | 4008 |

## Nárazy větru (m/s)

| Model | Chyba +1 den | +2 dny | +3 dny | +5 dní | Odchylka +1 den | Hodin (+1 den) |
|---|---|---|---|---|---|---|
| C-LAEF 1 km | 1,18 | – | – | – | −0,36 | 354 |
| ALADIN-CZ 1 km | 1,38 | 1,47 | – | – | 0,28 | 3504 |
| AROME-FR 1,3 km | 1,40 | – | – | – | 0,33 | 2439 |
| ALADIN-CE 2,3 km | 1,41 | 1,51 | – | – | 0,41 | 3504 |
| ICON-EU 7 km | 1,46 | 1,58 | 1,70 | – | 0,15 | 9167 |
| HARMONIE-DMI 2 km | 1,48 | – | – | – | −0,29 | 9167 |
| ICON-D2 2 km | 1,49 | – | – | – | −0,09 | 9167 |
| Open-Meteo best match | 1,49 | 1,58 | 1,70 | 3,06 | −0,09 | 9167 |
| HARMONIE-KNMI 5,5 km | 1,56 | – | – | – | −0,04 | 9167 |
| ARPEGE 11 km | 1,57 | 1,68 | 1,73 | – | 0,72 | 2436 |
| ICON-CH2 2 km | 1,59 | 1,68 | 1,80 | – | 0,05 | 9167 |
| UKMO 10 km | 1,59 | 1,63 | 1,63 | 2,02 | 0,15 | 8671 |
| GEM 15 km | 1,99 | 2,03 | 2,14 | 2,46 | −1,14 | 9050 |
| GFS 13 km | 2,33 | 2,40 | 2,48 | 2,72 | −1,17 | 9167 |
| ICON 13 km | 2,67 | 2,70 | 2,72 | 3,06 | 2,30 | 9167 |

**Který způsob kalibrace funguje nejlíp** (chyba směsi; vše počítáno jen z dat starších než den vydání):

| Způsob | +1 den | +2 dny | +3 dny | +5 dní |
|---|---|---|---|---|
| **bez opravy, jen váhy podle úspěšnosti** | 1,27 | 1,40 | 1,45 | 1,72 |
| přeškálování, okno 15 dní | 1,33 | 1,47 | 1,53 | 1,84 |
| přeškálování, okno 30 dní | 1,31 | 1,45 | 1,52 | 1,79 |
| přeškálování, okno 60 dní | 1,29 | 1,43 | 1,48 | 1,75 |

**Směs (bez opravy, jen váhy podle úspěšnosti) proti jednotlivým modelům** na stejných hodinách:

| Předstih | Směs | Nejlepší jednotlivý model | Prostý průměr modelů | Open-Meteo best match | Zlepšení proti nejlepšímu | Hodin |
|---|---|---|---|---|---|---|
| +1 d | 1,27 | 1,46 (ICON-EU 7 km) | 1,29 | 1,49 | 13 % | 8353 |
| +2 d | 1,40 | 1,58 (ICON-EU 7 km) | 1,42 | 1,58 | 11 % | 8257 |
| +3 d | 1,45 | 1,65 (UKMO 10 km) | 1,47 | 1,70 | 12 % | 8161 |
| +5 d | 1,72 | 2,00 (UKMO 10 km) | 1,73 | 3,03 | 14 % | 7969 |

Podle sezóny:

| Sezóna | Předstih | Směs | Nejlepší jednotlivý model | Hodin |
|---|---|---|---|---|
| léto (V–IX) | +1 d | 1,18 | 1,46 (ALADIN-CZ 1 km) | 3264 |
| zima (XI–III) | +1 d | 1,37 | 1,47 (ICON-EU 7 km) | 4008 |
| léto (V–IX) | +3 d | 1,30 | 1,57 (UKMO 10 km) | 3168 |
| zima (XI–III) | +3 d | 1,56 | 1,72 (UKMO 10 km) | 4008 |

## Srážky (denní úhrny, mm)

Zachycené deště = podíl dní s naměřeným úhrnem aspoň 1 mm, které model předpověděl. Plané poplachy = podíl dní, kdy model dal aspoň 1 mm a nenapršelo.

| Model | Chyba +1 den | Odchylka +1 den | Zachycené deště | Plané poplachy | Chyba +3 dny | Dní |
|---|---|---|---|---|---|---|
| Medián modelů | 0,94 | −0,70 | 68 % | 12 % | 1,13 | 382 |
| UKMO 10 km | 1,05 | −0,23 | 65 % | 27 % | 1,19 | 373 |
| ICON-CH2 2 km | 1,09 | −0,31 | 65 % | 20 % | 1,32 | 382 |
| ICON-D2 2 km | 1,11 | −0,03 | 77 % | 25 % | – | 382 |
| Open-Meteo best match | 1,14 | 0,05 | 79 % | 26 % | 1,39 | 382 |
| ECMWF IFS 9 km | 1,16 | 0,14 | 91 % | 32 % | 1,51 | 382 |
| ARPEGE 11 km | 1,16 | −0,27 | 76 % | 27 % | 1,38 | 382 |
| ICON-EU 7 km | 1,19 | 0,02 | 81 % | 25 % | 1,39 | 382 |
| ECMWF IFS 0,25° | 1,23 | 0,29 | 91 % | 33 % | 1,53 | 382 |
| ECMWF AIFS (AI) | 1,26 | 0,40 | 94 % | 40 % | 1,50 | 382 |
| GEM 15 km | 1,26 | 0,02 | 86 % | 31 % | 1,35 | 382 |
| ICON 13 km | 1,27 | 0,10 | 83 % | 22 % | 1,43 | 382 |
| AROME-FR 1,3 km | 1,29 | −0,06 | 74 % | 29 % | – | 382 |
| HARMONIE-KNMI 5,5 km | 1,30 | 0,05 | 81 % | 26 % | – | 377 |
| ALADIN-CZ 1 km | 1,31 | −0,02 | 83 % | 28 % | – | 146 |
| ALADIN-CE 2,3 km | 1,35 | 0,04 | 83 % | 28 % | – | 146 |
| HARMONIE-DMI 2 km | 1,43 | 0,19 | 82 % | 29 % | – | 382 |
| GFS 13 km | 1,48 | 0,52 | 81 % | 32 % | 1,57 | 382 |

Zdroje: předpovědi Open-Meteo.com (CC BY 4.0), měření ČHMÚ (opendata.chmi.cz).
