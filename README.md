# lipno-pocasi

Lokální předpověď pro Adventure Park Lipno (Černá v Pošumaví, Frymburk).

Skript nevyrábí nový fyzikální model. Bere předpovědi zhruba osmnácti existujících modelů, měří je proti stanici ČHMÚ v Černé v Pošumaví, opravuje jejich soustavné chyby a míchá je podle toho, jak se v posledních týdnech trefovaly.

## Co tu je

| Soubor | K čemu |
|---|---|
| `pocasi.py` | celý výpočet |
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
- `verify`: zpětné vyhodnocení od zadaného data (asi 8 minut)
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
- Wake Frymburk: na Weather Underground zatím není. Po založení zařízení doplnit jeho ID do `SITES["frymburk"]["wu"]` v `pocasi.py`.
- Při `verify` se pro každou stanici s aspoň 45 dny dat spočítá vlastní vyhodnocení modelů a porovnání se stanicí ČHMÚ (vítr podle směru, teplota podle denní doby, srážky po měsících).
- Předpověď pro Frymburk se kalibruje podle vlastní stanice, pokud má data mladší než 4 dny; jinak podle ČHMÚ v Černé.

## Co chybí

- Srážky nejsou kalibrované, jen se ukazuje shoda modelů.
- Bouřky: jen hrubé riziko z modelů, žádný radar.
