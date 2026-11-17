# lipno-pocasi

Lokální předpověď pro Adventure Park Lipno (Černá v Pošumaví, Frymburk).

Skript nevyrábí nový fyzikální model. Bere předpovědi zhruba osmnácti existujících modelů, měří je proti stanici ČHMÚ v Černé v Pošumaví, opravuje jejich soustavné chyby a míchá je podle toho, jak se v posledních týdnech trefovaly.

## Co tu je

| Soubor | K čemu |
|---|---|
| `pocasi.py` | celý výpočet |
| `pwl_export.py` | převod exportu z ProWeatherLive (CSV po 5 minutách) na hodinová data |
| `.github/workflows/pocasi.yml` | spouštění na GitHub Actions |
| `out/verifikace.md` | zpětné vyhodnocení: jak se které modely trefovaly a co přinese směs |
| `out/skill.json` | totéž strojově; odsud si předpověď bere zvolený způsob kalibrace |
| `out/predpoved.md` | aktuální předpověď pro obě místa |
| `out/predpoved.json` | totéž strojově |
| `data/stanice/<místo>/RRRR-MM.csv` | hodinová data vlastních stanic stažená z Weather Underground |
| `data/pwl_<místo>.csv` | jednorázový export z ProWeatherLive převedený na hodiny (nepovinné) |

## Spuštění

Actions → Lipno pocasi → Run workflow:

- `forecast`: aktuální předpověď (asi 2 minuty)
- `verify`: zpětné vyhodnocení od zadaného data (10 až 20 minut)
- `both`: obojí

Pravidelné spouštění je v souboru workflow připravené, ale zakomentované.

## Volitelná tajemství (Settings → Secrets and variables → Actions)

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: předpověď se po každém běhu pošle do Telegramu
- `OPENMETEO_API_KEY`: klíč k placenému tarifu Open-Meteo
- `WU_API_KEY`: klíč API z Weather Underground (Member Settings → API Keys); skript si pak sám stahuje hodinová data vlastních stanic

## Zdroje a podmínky

- Předpovědi: [Open-Meteo](https://open-meteo.com), data CC BY 4.0. Bezplatné API je jen pro nekomerční použití.
- Měření: ČHMÚ, [opendata.chmi.cz](https://opendata.chmi.cz), stanice Černá v Pošumaví (0-203-0-11547).

## Vlastní stanice

- Lanový park (terasa): Weather Underground `IERNVP8`. Po doplnění `WU_API_KEY` se při `verify` stáhne historie a při každém běhu posledních 7 dní.
- Wake Frymburk: na Weather Underground zatím není. Po založení zařízení doplnit jeho ID do `SITES["frymburk"]["wu"]` v `pocasi.py`. Historie od 11/2024 je v `data/pwl_frymburk.csv`.
- Export z ProWeatherLive (Settings → Devices → zařízení → Export Data) se převede takto:
  `python pwl_export.py EXPORT.csv data/pwl_frymburk.csv` (pro lanový park `data/pwl_cerna.csv`).
- Kontrola dat (při každém běhu): vyřadí se úseky, kdy čidlo neposílalo data, kdy stál anemometr (24 hodin skoro samé nuly, nebo nula při větru na stanici ČHMÚ) a měsíce, kdy srážkoměr naměřil méně než pětinu toho co ČHMÚ.
- Vítr a nárazy se vždy kalibrují podle stanice ČHMÚ (volné prostranství, 10 m nad zemí). Vlastní stanice jsou v závětří a slouží jen k porovnání: `verifikace.md` ukazuje, kolik stanice ukáže při jakém větru na ČHMÚ.
- Teplota ve Frymburku: `verify` porovná kalibraci podle vlastní stanice s kalibrací převzatou z Černé a rozhodne (`out/skill.json`, `targets.frymburk.transfer.T.use`): `all` = podle vlastní stanice, `night` = jen v noci (čidlo se na slunci přehřívá), `none` = stanice kalibraci nezlepší. Data starší než 14 dní se nepoužijí.

## Co chybí

- Srážky nejsou kalibrované, jen se ukazuje shoda modelů.
- Bouřky: jen hrubé riziko z modelů, žádný radar.
