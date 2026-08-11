# Plan podniesienia jakości frontendu companiona

Stan: 2026-08-08 (etapy 1–3 ✅ commit 92abb3b; Etap 5 w toku) · benchmark: karta świata i mapa z Traveller RPG Companion (AceGoulet)
· zasada nadrzędna: **fog-of-war po SI zostaje sercem UI** — konkurencja pokazuje
wszystko (katalog OTU), my pokazujemy to, co załoga *wie*.

Kolejność wykonania = kolejność sekcji. Każdy etap kończy się weryfikacją
screenshotową na stanie demo (Playwright, jak przy panelu UWP) i commitem
do obu repo (prywatne `deepnight` + publiczne `deepnight-companion`).

---

## Etap 1 — CSS-only (~1 sesja, zero ryzyka regresji logiki)

### 1.1 Pływająca karta panelu bocznego
- **Pliki:** `companion/web/style.css`
- `#side-col .panel`: tło `color-mix(in srgb, var(--g-850) 86%, transparent)`,
  `backdrop-filter: blur(10px)`, ramka 1px `color-mix(accent 35%)`,
  cień `0 12px 40px rgba(0,0,0,.5)`; `#side-col` traci pełne tło (mapa
  prześwituje pod kartami).
- **Uwaga techniczna:** `backdrop-filter` wymaga, by `#side-col` nakładał się
  na mapę → `#main` przechodzi na `position: relative`, `#side-col` na
  `position: absolute; right: 0; top: 0; bottom: 0` + `#map-col` bez zmian
  szerokości (mapa pod spodem na pełną szerokość). Fallback: jeśli overlap
  zaburzy klikalność prawego skraju mapy, zostawić layout flex i dać samą
  przezroczystość + glow (80% efektu, zero ryzyka).
- **Kryterium:** karta wygląda jak „REGINA card" (szkło + glow); klik w hexy
  pod prawą krawędzią mapy nadal działa.

### 1.2 Typografia danych
- **Pliki:** `style.css` (+ ew. klasa w `app.js` przy renderze topbaru)
- Mono/`font-variant-numeric: tabular-nums` dla: `code` (UWP), `#tb-fuel`,
  `#tb-su`, `#tb-date`, wartości `.stat .val`, współrzędnych w `#hex-title`.
- `#hex-title` → 15px, nazwa systemu **italic** + letter-spacing (wzór „REGINA").
- **Kryterium:** liczby w topbarze nie „skaczą" przy odświeżeniu; UWP wyraźnie
  techniczny.

### 1.3 Czytelność mapy przy oddaleniu
- **Pliki:** `app.js` (`renderMap`, `starStyle`, `applyView`), `style.css`
- Mnożnik rozmiaru glifów `k = clamp(1, viewW / (BASE_VB.w/2), 1.9)` liczony
  w `applyView` → re-render overlayów albo CSS `--glyph-scale` na grupach
  (prościej: przy zmianie VIEW przerysować overlaye z mnożnikiem).
- Pierścienie stref Amber/Red: stroke-width 0.6 → 1.0·k, pełniejszy kolor.
- **Kryterium:** przy pełnym sektorze gwiazdy i strefy rozpoznawalne z ~1,5 m
  (test: screenshot 1600×900, ocena rozmiaru glifów ≥ 4 px).

### 1.4 Hover i zaznaczenie hexu
- `.hex:hover` — jaśniejszy fill + stroke akcentu (przejście 120 ms);
  `.hex.selected` — grubszy stroke + zewnętrzny glow (filter drop-shadow).
- **Kryterium:** widać bez wpatrywania się, który hex jest wybrany.

## Etap 2 — interakcje mapy (~1–2 sesje, tylko frontend)

### 2.1 Przełącznik zasięgu J1–J4 na karcie hexu
- **Pliki:** `app.js` (`selectHex`, `renderMap`), `style.css`
- Rząd chipów `J1 J2 J3 J4 ✕` pod chipami statusu; stan globalny
  `RANGE_FROM = {sector, hex, j}`; `renderMap` maluje klasę `.in-range-sel`
  (halo w drugim kolorze niż zasięg paliwowy statku) na hexach w promieniu j
  od wybranego hexu (dystans już jest: `distPc`).
- Wyłączanie: ✕ albo zmiana zaznaczenia.
- **Kryterium:** klik J2 na dowolnym hexie podświetla pierścień 2 pc wokół
  niego; zasięg paliwowy statku (`.in-range`) wizualnie odróżnialny.

### 2.2 Animacja skanu („radar sweep")
- **Pliki:** `app.js` (funkcja `scan` w `renderActions`), `style.css`
- Na czas requestu skanu: na skanowanym hexie SVG-owe koło z animacją
  rozchodzącej się fali (2 okręgi, opacity/r animowane CSS, ~1.2 s) —
  wstawiane przed `await api(...)`, sprzątane po re-renderze.
- `prefers-reduced-motion` wyłącza.
- **Kryterium:** każdy skan daje widoczny „ping" na mapie.

### 2.3 Tooltip → mini-karta
- **Pliki:** `app.js` (`hexInfoSummary` → `hexInfoCard`), `style.css`
- Zamiast jednej linijki: nazwa/hex + rząd chipów (SI, gwiazda, GG) w tym samym
  stylu co `#hex-chips` (reużycie klas `.chip`).
- **Kryterium:** tooltip czytelny w <1 s, brak migotania przy ruchu myszy.

## Etap 3 — progresja odkrywania (frontend + drobne API, ~2 sesje)

### 3.1 Glif systemu rośnie z SI
- **Pliki:** `app.js` (`drawHex`), ew. `server.py` (`sector_map` — upewnić się,
  że zwraca `gas_giant`/`stars` dokładnie wg progów SI — już zwraca)
- Progi: SI 0–1 kropka szara · SI 2 kropka jaśniejsza · SI 3–4 barwna gwiazda
  wg typu (jest) · SI 5+ dochodzi ikonka GG (jest) · SI 6+ mini-kropki liczby
  ciał pod gwiazdą (nowe) · kanon: duży glow + nazwa (jest).
- **Kryterium:** na mapie da się odróżnić „nic nie wiemy" od „przeskanowane",
  bez otwierania panelu; zero informacji ponad próg SI (sprawdzić w player view).

### 3.2 Piny / zakładki hexów („Chart this world")
- **Pliki:** `server.py` (GET/POST `/api/bookmarks`, zapis
  `state/bookmarks.json`), `app.js` (gwiazdka przy tytule hexu, glif pinezki
  na mapie), `style.css`
- Pin = {sector, hex, label?, ts}; toggle z karty hexu; lista pinów jako
  rozwijka przy selektorze sektora (skok do pinu).
- **Kryterium:** pin przeżywa restart serwera; widoczny na mapie i w liście.

### 3.3 Historia rzutów
- **Pliki:** `app.js` (bufor ostatnich N=20 `fmtCheck` + wyników), panel
  rozwijany z topbaru (przycisk 🎲)
- Tylko klient (sesja przeglądarki) — bez zmian API; dziennik i tak loguje
  akcje trwale.
- **Kryterium:** po serii akcji panel pokazuje chronologię rzutów z rozbiciem.

## Etap 5 — art direction (2026-08-08; domyka gap do benchmarku)

Diagnoza: etapy 1–3 dały design *funkcjonalny*; wrażenie „surowości" robią
brak własnej typografii, emoji zamiast ikon i płaskie tło mapy. Etap 5 =
warstwa tożsamości wizualnej. (Wykonywany PRZED opcjonalnym Etapem 4;
podpunkty 4.2/4.3 wchłonięte tutaj jako 5.4/5.3.)

### 5.1 Typografia własna (największa dźwignia)
- **Pliki:** `web/fonts/` (nowy), `style.css`, `index.html` (preload)
- Self-hosted woff2 (latin + latin-ext — PL diakrytyki!): **Exo 2** 600/700
  (display: brand, nagłówki paneli, dialogi, jump-text) + **IBM Plex Mono**
  400/600 (dane: `code`, UWP, wartości statów, liczby topbaru).
  Body zostaje na systemowym (czytelność).
- **Kryterium:** zero FOUT rozwalającego layout (font-display: swap +
  preload); PL znaki renderują się w display foncie.

### 5.2 Spójny zestaw ikon SVG zamiast emoji
- **Pliki:** `index.html` (sprite `<symbol>`), `app.js` (helper `ico()`),
  `style.css` (`.ico`)
- Jeden zestaw stroke 2px currentColor (wzór Lucide): kalendarz, pozycja,
  paliwo, zapasy, załoga, kości, undo, dziennik, planeta-GG, glob, półksiężyc,
  trójkąt ⚠, oktagon ⛔, klucz, kometa, księżyc, radar.
- Wymiana we WSZYSTKICH miejscach struktury UI: topbar, chipy, lista ciał,
  defekty, `fmtCheck`. Emoji zostaje tylko w wolnym tekście dziennika.
- **Kryterium:** brak kolorowych emoji w chrome UI; ikony dziedziczą kolor
  chipa/przycisku.

### 5.3 Atmosfera mapy (fog-of-war nietknięty)
- **Pliki:** `app.js` (`renderMap`), `style.css`
- Deterministyczny starfield per sektor (PRNG mulberry32 z hasha nazwy
  sektora, ~140 punkcików o zmiennym r/opacity) — tło NIE koduje żadnej
  wiedzy o systemach; winieta CSS na `#map-wrap`; siatka subsektorów 4×4
  z literami A–P (złoty serif, opacity ≤ .15). Nazwy subsektorów — gdy
  `fetch_map_data.py` kiedyś dociągnie dane (na dziś litery kanoniczne).
- **Kryterium:** mapa ma głębię „kosmosu" przy zachowaniu czytelności;
  player view nie zdradza nic ponad SI.

### 5.4 Motyw „paper chart" + akcenty (dawne 4.2)
- **Pliki:** `style.css` (`[data-theme=paper]`, `[data-accent=…]`),
  `index.html` + `app.js` (przełączniki w topbarze, `localStorage
  dn-theme`/`dn-accent`)
- Paper: kremowe tło, atramentowe hexy, czerwone strefy, starfield/mgławice
  ukryte (trade dress „z książki"). Akcenty: blue (default) / green / amber.
- **Kryterium:** oba motywy × oba języki czytelne; fog-of-war widoczny
  w paper (jasność ↔ wiedza odwzorowana na atrament).

### 5.5 Motion między widokami
- **Pliki:** `style.css`, `app.js`
- Wejście paneli (dziennik, historia rzutów) — slide/fade ~200 ms; zawartość
  karty hexu fade przy zmianie zaznaczenia; skeleton w karcie na czas
  requestu. Wszystko pod `prefers-reduced-motion`.
- **Kryterium:** zmiany widoku nie „skaczą"; brak migotania przy szybkim
  klikaniu po hexach.

### 5.6 Custom kontrolki
- **Pliki:** `style.css`
- Selecty `appearance:none` + własny chevron (osobny wariant dla paper);
  spójne stany focus/hover.
- **Kryterium:** selecty nie wyglądają „jak z OS"; focus widoczny z klawiatury.

## Etap 6 — pełna grafika „wnętrze książek Deepnight" (2026-08-10, WYKONANY)

Kierunek wybrany przez Mateusza: malowany art z posiadanych PDF-ów + czysta
typografia. Assety w `web/art/` (przetworzone przez PIL z `extracted/*/images`):
- `hero.jpg` — okładka Book 1 (czerwony księżyc) bez logo/stopki → ekran startowy
  (full-bleed + gradient + glass panel);
- `starfield.jpg` — malowane pole gwiazd (B1 p.2) → tło mapy (nieznane hexy
  półprzezroczyste `color-mix 62%`, gwiazdy prześwitują — fog-of-war nietknięty,
  hexy ze znanym SI pozostają kryjące) + tło overlaya skoku;
- `tex-nav.jpg` — oryginalna tekstura stron książek (trajektorie) → tło dziennika;
- `tex-grid.jpg` — tekstura „tech-grid" (B2) → tło kolumny paneli.

**⚠ COPYRIGHT:** art Mongoose z posiadanych PDF-ów — TYLKO repo prywatne.
Publiczny mirror NIE dostaje `web/art/` (CSS degraduje się do kolorów fallback);
ewentualnie do wygenerowania substytuty AI (`scripts/gen_image.py`).
Motyw paper wyłącza wszystkie zdjęcia ([data-theme=paper] overrides).

## Etap 4 — klimat (opcjonalny, po użyciu na sesji)

### 4.1 Dźwięki (ping skanu, jump, kości) + mute w topbarze
- WebAudio, syntetyczne biipy (bez plików audio = zero wagi w repo);
  `localStorage dn-mute`.
### 4.2 Motyw „paper chart" (jasny, drukowalny)
- Drugi zestaw zmiennych CSS (`[data-theme=paper]`), przełącznik obok EN/PL;
  mapa: kremowe tło, czarne hexy, czerwone strefy (trade dress „z książki").
### 4.3 Nazwy subsektorów w tle mapy
- Złoty serif, opacity ~0.15, 4×4 siatka subsektorów — dane subsektorów
  trzeba dociągnąć do `sectors.json` (rozszerzenie `fetch_map_data.py`).

---

## Zasady jakości (obowiązują w każdym etapie)

1. Skale, nie intuicja: odstępy 4/8/16/24/32, typografia 11/12/13/16/20
   (jak dotychczas w `style.css`).
2. Po każdym etapie: `node --check`, pytest (bez zmian silnika = smoke),
   screenshot demo EN+PL, ocena na ekranie laptopa stołowego.
3. Commit per etap do obu repo; exe przebudowywać dopiero po Etapie 2
   (nie po każdej zmianie).
4. Nic nie wolno pokazać graczom ponad próg SI — każda zmiana mapy/tooltipa
   sprawdzana na hexie z niskim SI.

## Poza zakresem (świadomie)

- Teksturowane planetki na mapie (łamią fog-of-war i estetykę dotmapy).
- Granice polityczne / trasy handlowe (w Szczelinie nie istnieją).
- Mobile layout (companion gra na laptopie; telefon = artefakty z Drive).
