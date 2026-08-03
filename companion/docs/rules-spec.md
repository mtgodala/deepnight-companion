# Deepnight Companion — specyfikacja mechanik (silnik gry)

> Źródło: ekstrakcja z B3 (Referee's Handbook) + karta statku z B2, wykonana 2026-07-30.
> Konwencja stron: **numery WYDRUKOWANE** (w extracted/text.md znacznik `<!-- p.N -->` = strona PDF = druk+1).
> Każda stała w `companion/rules/` MUSI cytować stronę z tego dokumentu.

---

## 0. STATEK — RSS Deepnight Revelation (B2, karta statku)

| Parametr | Wartość | Źródło |
|---|---|---|
| Kadłub | 75 000 t (potwierdzone: B3 p.68 — 750 t = 1%/pass) | B2 karta |
| M-Drive | Thrust 4 (energy efficient ×3) + Deep Space Manoeuvring System | B2 karta |
| J-Drive | **Jump-4**, reduced fuel requirement **-10%** | B2 karta |
| Zbiorniki paliwa | **27 900 t** = „8 weeks of operation, J-4" | B2 karta |
| Paliwo na skok | core MGT2: 10% kadłuba × parsek; z -10%: **6 750 t/parsek**, J-4 = **27 000 t** | core + B2 |
| Paliwo reaktora | ~900 t = 8 tygodni (≈112,5 t/tydz.) | wyliczenie z karty |
| Fuel Scoop + Processor | **4 000 t/dzień** przetwarzania | B2 karta |
| UNREP System | 200 t/h transfer | B2 karta |
| Power Plant | Fusion TL15, Power 90 000 | B2 karta |
| Sensory | Advanced (distributed) ×2, Military CM ×2, Deep Penetration, Integrated Long Range Array, Mineral Detection, Life Scanner | B2 karta |
| Załoga | „just under 500 active personnel" (B3 p.37); etat 488 (B2, ustalenie z briefów) | B3/B2 |
| **Startowe CEI = 7** („set at a value of 7 at the beginning of the final [phase]"), CEIM = 0 | B2 (linie ~7784-7800) |
| Startowe MOR | **CEI + 2D3** | B2 + B3 p.38 |
| Startowe DEI (Flight/Eng/Ops/Mission) | = CEI | B3 p.34 |
| Hover | max nad ciałem Size 2 / 0,15g | B3 p.68 |

**Konsekwencja rytmu gry:** pełne tankowanie J-4 = 36 passów skimmingu (po 750 t) + ~7 dni przetwarzania (4 000 t/d). Bottleneckiem jest procesor, nie skimming.

---

## 1. SURVEY INDEX (SI) — B3 p.71-74

SI per hex, skala 0-12. Dane nie są w 100% dokładne, błędy „w granicach możliwości".

| SI | Co ujawnia (B3 p.71) |
|---|---|
| 0 | Brak danych |
| 1 | Obecność gwiazd; wielkie fenomeny (czarna dziura) |
| 2 | + ogólny typ gwiazd (giant / main-sequence…) |
| 3 | Obecność i typ gwiazd |
| 4 | + ciała wielkości brązowego karła |
| 5 | + gazowe olbrzymy i większe (⇒ pewność tankowania) |
| 6 | + planety skaliste, pasy planetoid |
| 7 | + ogólne warunki (atmosfera, woda powierzchniowa) |
| 8 | + szacunek Size/Hydro/Atmo (pierwsze 3 cyfry UWP) |
| 9 | + POPRAWNE 3 pierwsze cyfry; szacunek Pop/TL |
| 10 | Pełny UWP |
| 11 | + rogue planetary bodies systemu |
| 12 | + rogue cometary bodies (⇒ pewne źródła paliwa, B3 p.69) |

- **Start:** mapa gwiezdna daje SI 1-3; przy pierwszym zainteresowaniu hexem rzuć **D3** (B3 p.71).
- **Instrumenty automatyczne:** np. gravitic survey ⇒ całe otoczenie na SI 5 (B3 p.72).
- **Podnoszenie:**
  1. Remote sensor sweep: Average (8+) DEI lub Electronics (sensors); sukces ⇒ **SI += 2×Effect**; DM+2 suite naukowy DNR (B3 p.72)
  2. Passive survey: 2D minut, **+1 SI**, nie zdradza pozycji (B3 p.73)
  3. Active survey: 2D godzin, **+D3 SI**, **ujawnia statek** wszystkim nasłuchującym (B3 p.73)
  4. Full survey: 4D godzin, **+1D SI**, wymaga zmiany pozycji (B3 p.74)
  5. Pobyt w systemie: **+1 SI co 1D dni** zbierania danych (B3 p.74)
- **REGUŁA: liczy się tylko NAJWIĘKSZY pojedynczy przyrost, nie suma** (Active +2 potem Full +4 ⇒ +4, nie +6) (B3 p.73). Interpretacja silnika: dotyczy sweepów tego samego „poziomu wiedzy"; pobyt i remote sweep kumulują się osobno — FLAGA do decyzji GM.

### SI w deep space (B3 p.74)
Progi detekcji (scan points, patrz §2): gwiazda auto; brown dwarf 4; large GG 6; small GG 8; planeta 10; kometa 12; **+1 za każdy parsek odległości**.

---

## 2. SCAN POINTS — B3 p.72, p.74

- Produkcja: **6/dzień** (pełny suite DNR); 1 punkt = 1 osoba (może być unskilled).
- Koszt sweepu systemu: **rzut 2D** punktów (B3 p.72).
- Alokacja: kilka sweepów RÓWNOLEGLE — każdy cel dostaje pełne punkty dnia (3 systemy × 5 dni = 5 pkt każdy, nie dzielone!) (B3 p.72).
- Deep space: 6 hexów naraz po 1 pkt LUB kumulacja na jeden hex (B3 p.74).
- Defekty obniżają: Mission-Related Sensors DM-1/Defekt (B3 p.54-55); mgławica protogwiazdowa DM-2 (B3 p.11).

---

## 3. NAWIGACJA PO SKOKU — B3 p.63, p.72-73

**Positional Checks (B3 p.73):**

| Check | Czas | Zasięg |
|---|---|---|
| Routine | D3 min | preset points vs oczekiwane dane |
| Detailed Routine | 2D min | potwierdzenie oczekiwanej pozycji |
| Close | 4D min | ciała w promieniu 6 pc (z danych ostatnich skoków) |
| Local | 2D×10 min | ~subsektor |
| Sector | 2D×30 min | ~sektor, znane ciała do 20 pc |
| Distant | 3D h | znane punkty do 100 pc |
| Full | 1D dni | dowolna odległość; +1D dni na doprecyzowanie |

- Rozjazd danych (misjump itp.) wykrywany „niemal natychmiast": **max 12 minut** do „nie jesteśmy tam, gdzie mieliśmy być"; **24 min** do „nie jesteśmy w promieniu 6 pc od znanego systemu" (B3 p.73).
- Każda gwiazda w promieniu 6 pc trasy jest rutynowo dodawana do lokalnych plików referencyjnych (B3 p.72-73).
- **Post-Jump Primary (B3 p.63):** Easy (4+) CEI; sukces = raport wstępny + szczegółowy po 20-30 min (pozycja, podstawowe dane systemu, emisje radiowe, status statku/paliwa). Ukryte problemy wymagają wyższego Effectu (General/Vague Checks, B3 p.5-6).

---

## 4. SKOK — B3 + core MGT2

**B3 wprost NIE MA:** liczb paliwa (⇒ §0), tabeli misjumpu (⇒ core), czasu skoku poza „usual 7 days" (B3 p.17).

**Silnik:** skok = wybór celu w zasięgu ≤4 pc → walidacja paliwa (6 750 t × parseki) → czas ~168h (opcjonalnie 148+6D h) → misjump check wg core MGT2 przy DM-ach:

| Okoliczność | DM (B3 p.11) |
|---|---|
| Skok do/z mgławicy | -4 |
| Skok przez mgławicę | -2 |
| Skok przez protostar/gęstą chmurę | -4 |
| Skok do/z chmury protogwiazdowej | -8 |
| T Tauri | jak protostar + jump shadow 7-10 AU |

**Jump Interference Zone (B3 p.10-11):** obiekty zwarte (BH, gwiazda neutronowa) — JIZ = 100-diameter limit gwiazdy o RÓWNOWAŻNEJ MASIE (neutron star masy Sol ⇒ limit ~0,88 AU), nie fizycznej średnicy.

**Tempo maksymalne (B3 p.15):** teoretycznie 12 pc/mies. przy 3 skokach (48h między skokami, zero eksploracji).

### Skok w pusty hex — Short-Range Detection (B3 p.75)
Rzut 2D: **+2** znany obiekt międzygwiezdny w hexie; **+4** w hexie systemu ale poza nim; **+6** Oort Cloud; **+8** Kuiper Belt; **-1/parsek** do najbliższego systemu.

| 2D | Wynik |
|---|---|
| 7− | nic |
| 8-9 | 1 obiekt |
| 10-11 | 1D3 obiektów |
| 12 | 1D obiektów (+1 za każdy pkt >12) |

Sweep: **1D dni**, pokrywa sferę ~50 AU. Brak wykrycia ≠ pusty hex.

**Nature of Objects Found (B3 p.76)** — 2D per obiekt:
2 ⇒ 1D: 1 extremely unusual / 2 wrak / 3 dangerous / 4 anomalia graw./rad. / 5 planetoida ze śladami zamieszkania / 6 gęsty obłok. 3-4 = glitch (nic). **5-9 = mała kometa (JEDNO tankowanie). 10-11 = ciało kometarne (wiele tankowań).** 12 ⇒ 1D: 1 large comet / 2 rogue dwarf / 3 rogue planetoid cluster / 4 rogue planet / 5 rogue GG / 6 unusual large body.

---

## 5. TANKOWANIE — B3 p.68-69

- **Skimming GG:** 1% kadłuba/pass = **750 t**, pass 2D minut, Pilot z **DM-2** (głębokie warstwy); górne warstwy: **~375 t/pass**, bez DM. Abstrakcja: Mission na DEI Flight (B3 p.68).
- **Lód/woda:** cracking = „simple task", brak tempa w B3 ⇒ silnik używa Fuel Processor **4 000 t/dzień** (B2).
- **Fuel Source check** (szukanie źródła bez SI 12) — Electronics (sensors) lub Science (cosmology) (B3 p.69):

| Gęstość systemu | Trudność | Czas |
|---|---|---|
| Extremely Dense | Simple (2+) | 1D h |
| Very Dense | Easy (4+) | 2D h |
| Dense | Routine (6+) | 3D h |
| Normal | Average (8+) | 4D h |
| Sparse | Difficult (10+) | 6D h |
| Very Sparse | Very Difficult (12+) | 8D h |
| Extremely Sparse | Formidable (14+) | 12D h |
| Barren | jak deep space objects (§4) | — |

- Defekt Fuel Processors: **+10% czasu/Defekt** (B3 p.55). Skimming przy wietrze = ryzyko Erosion of Capabilities (B3 p.56).
- Preferencja: najbardziej wewnętrzny GG (dostęp do inner system) (B3 p.69).

---

## 6. GENERACJA SYSTEMÓW — B3 p.8, p.20-21 + core MGT2

**Podział odpowiedzialności silnika:**
- **Obecność gwiazdy:** z dotmapy travellermap (kanon). Rzut Star System Presence TYLKO dla hexów spoza danych: Cluster 1-5/1D; Dense 1-4/1D; Average 1-3/1D; Sparse 1-2/1D; **Rift 2/2D; Void 3/3D** (B3 p.20).
- **SDI (System Density Index):** rzut **3D-3, +1D-1 za każdą naturalną 6** (bez łańcucha). Typowo 8-11, max 30 (B3 p.20-21).

| SDI | Gęstość | Ciała planetarne (B3 p.8) |
|---|---|---|
| 0 | Barren | 0 (możliwe komety/planetoidy) |
| 1-3 | Extremely Sparse | 1 |
| 4-6 | Very Sparse | D3 |
| 7-9 | Sparse | 1D+1 |
| 10-12 | Normal | 2D |
| 13-15 | Dense | 2D+3 |
| 16-18 | Very Dense | 3D |
| 19-21 | Extremely Dense | 4D |
| 22+ | Anomalous | — |

- **Specific Bodies (B3 p.21):** SDI = pula DM do rozdzielenia (min +1 na rzut, pula się wyczerpuje). Rzut 1D+DM: GG do tankowania **9+**; borderline habitable **9+**; habitable **12+**; planetoidy do wydobycia **10+**. Negatywny wynik ≠ brak ciała (quick gen mówi co jest PEWNE; pełna gen = co jest faktycznie).
- **UWP mainworldu / gwiazdy / orbity:** core MGT2 worldgen (B3 p.20, p.70 odsyła wprost). Cyfry UWP odsłaniane wg SI (§1).
- **Katalog 22 typów światów** (B3 p.83-91): opisowy, do flavor textu; Super-Earth 3-10× masy Terry; hover-limit Size 2/0,15g.
- **Kanon nadpisuje generator:** hex z pełnym UWP w dotmapie = system kanoniczny.
- **Determinizm:** seed = SHA256(f"{sector}:{hex}") → wszystkie rzuty generacji.

---

## 7. RATE OF ADVANCE (abstrakcja tranzytu) — B3 p.15-17

Segment abstrakcji: max Reach 1-2 miesiące; dłuższe dzielić na miesięczne (B3 p.15).

| Rate | Avoid Event | Point of Interest | Parseki/mies. |
|---|---|---|---|
| Flank Speed | 10+ | 12+ | 1D+6 |
| Rapid Transit | **8+** ⚠HR (druk: „18+") | 10+ | 1D+4 |
| Cursory Exploration | 6+ | 8+ | 1D+2 |
| Detailed Exploration | 4+ | 6+ | 1D |

CEI DM dodatni: dzielony dowolnie między Avoid Event / POI / parseki (B3 p.17).

**Events (2D, B3 p.17):** 2 Major Supply / 3 Major Crew / 4 Bad Data / 5 Cargo / 6 Minor Crew / 7 Minor Supply / 8 Illness / 9 Non-Critical Malfunction / 10 Critical Malfunction / 11 Non-Critical Breakdown / 12 Critical Breakdown.
Liczby (B3 p.18): Minor Supply = **1D×5%** pozostałych zapasów bezużyteczne; Major = **3D×5%**.

**Points of Interest (2D typ + 1D szczegół, B3 p.19):** 2 Anomaly / 3 Stellar Body / 4 System Composition / 5 Rogue Bodies / 6-8 Phenomenon / 9 Mainworld / 10-11 Outsystem World / 12 Encounter (1-2 Ruins, 3-4 Intelligent Beings, 5 Transmission, 6 Sighting). Pełne podtabele w raporcie źródłowym.

---

## 8. SUPPLY UNITS — B3 p.46-52

- Zużycie: **1 000 SU/dzień** (zawsze; port nieistotny poza Charted Space). Pojemność wewnętrzna: **200 000 SU** (= 200 dni). Cargo: +100 SU/t (wymaga rozpakowania).
- **Extending Duration (B3 p.47):** Average (8+) Admin na początku Reachu: zużycie **-2,5%/Effect** (porażka: +2,5%/|Effect|).
- **Celowe cięcie budżetu (B3 p.48):** Difficult (10+) Leadership, **DM-1 za każde 5% cięcia**; negatywny Effect ⇒ minor MOR check z tym DM. Max normalne cięcie 50%. **Do progów liczy się BUDŻET, nie faktyczne zużycie.**

**Supply Level Effects (B3 p.49):**

| Budżet dzienny | Efekt załogowy | Maintenance DM |
|---|---|---|
| 0 | auto: CEIM i MOR **-1D** co 2D dni | +12 |
| 1-10% | auto: **-D3** co 2D dni | +10 |
| 11-20% | auto: **-1** co 2D dni | +8 |
| 21-40% | Formidable (14+) Leadership co 4D dni | +6 |
| 41-60% | Very Difficult (12+) co 4D dni | +4 |
| 61-80% | Difficult (10+) co 4D dni | +2 |
| 81-90% | Average (8+) co 4D dni | +1 |
| 91-100% | Routine (6+) co 4D dni | +0 |

Porażka checku: negatywny Effect dzielony między CEIM i MOR (wybór graczy).

**Materiały specjalne (B3 p.46-47):** Rare Materials / Rare Biologicals / Exotic Materials; 100 j./t cargo. Zastosowania (B3 p.47): naprawa awaryjna 4D h = 1D RM; narzędzie specjalne = 1D RM; amunicja specjalna = 2D RM lub 1D EM; antidotum/szczepionka (25 os.) = 1D RB; racje połówkowe bez kar MOR (tydzień) = 2D RB; **DM+1 na check CEI/DEI** = 2D RM/RB lub 1D EM; **DM+2** = 3D EM. Zakaz łamania fizyki.

**Pozyskiwanie (B3 p.50-51):** koncentracja Concentrated +4 / Raw +0 / Bulk -4; Resource Value 2D+DM (w tym DM z CEI, sprzęt -2/-4): 0−=2D SU/os.; 1-3=2D×5; 4-6=2D×10; 7-9=2D×25; 10-12=2D×50; 13-15=2D×100; 16+=4D×100 (kolumna średnia zakłada 50 os.). Resource Availability per typ świata — tabela w raporcie źródłowym. Exotic NIGDY z rutynowej misji resupply.

---

## 9. MAINTENANCE — B3 p.53-59

- **Cykl:** początek każdego Reachu. Check: Average (8+) CEI (lub DEI dedykowanego detachmentu). **Effect zapisywany** ⇒ anuluje problemy: **Defect=1 / Breakdown=3 / Failure=6 pkt** (przed określeniem natury!).
- **Rzut na problemy: 2D + DM-y:** Supply Maintenance DM (§8) / +1 za każde 10% utraconych Hull / +1 za pełny rok podróży / +2 substandard / +4 very little maintenance / +2 brak overhaulu 24 mies.

**Maintenance Issues (B3 p.53):** 1-3: 0/0/0 · 4-6: 1D/0/0 · 7-9: 2D/0/0 · 10-12: 3D/0/0 · 13-15: 1D/1B/0 · 16-18: 2D/1B/0 · **[19-20: brak w druku ⇒ HR: jak 16-18]** · 21-24: 3D/1B/0 · 25-27: 1/2/1 · 28-30: 2/2/1 · 31-33: 3/2/1 · 34-36: 1/3/2 · 37-39: 2/3/2 · 40-42: ALL/3/2 · 43-45: ALL/ALL/2 · 45+: X/X/ALL (D=Defects, B=Breakdowns, F=Failures).

- Defect: DM-1/szt. (max -6 ⇒ staje się Breakdownem). Breakdown: obniżona sprawność (np. Thrust -1) lub niesprawny; jury-rig możliwy. Failure: total, bez jury-rig.
- **System (1D):** 1-2 Structure / 3 Sensors&Electronics / 4 Drives&Power / 5 Weapons&Defensive / 6 General. Podtabele subsystemów z efektami — w raporcie źródłowym; kluczowe: Hull Minor 3D HP/Defekt (B ×10, F ×100); Jump Major = Jump -1/Defekt; Powerplant Major = -15% output/Defekt; M-Drive Major = Thrust -1/Defekt; Computer = BW -1D; General Failures⇒MOR-3 / B⇒-2 / D⇒-1 (tylko najwyższa kara).
- **Erosion of Capabilities (B3 p.56):** Average (8+) CEI po brute-force/długim tranzycie; porażka ⇒ Defekty = |Effect|; każdy: 1D 4+ = tymczasowy.
- **Zaniedbanie (B3 p.56-57):** >10 dni bez maintenance ⇒ substandard (+2); >20 dni ⇒ very little (+4). Personel <60% przez >10 dni ⇒ shortfall; <30% przez >20 dni ⇒ severe.
- **Overhaul (B3 p.57-58):** co 12-18 mies.; **2D+12 dni**, cała załoga; koszt **4D×5 000 SU** (Difficult 10+ Admin: ±5%/Effect). Start kampanii: świeży overhaul ⇒ Crisis DM-3 rok 1, DM-2 rok 2 (B3 p.27).
- **Naprawy (B3 p.58-59):** Minor=20 os. / Major=50 / Structural=100 (do 25% unskilled). Koszty: Defect minor 2D h + 2D×100 SU … Failure major 30D h + 8D×500 SU + 8D rare/4D exotic; Hull 2D+6 HP = 2D×10 h + 2D×5 000 SU; Armour 1 pkt = 2D×50 h + 2D×2 000 SU (pełna tabela w raporcie). Niedobór ludzi: czas +50% + 20%/10% braku; DM-1/10% braku. Rozstrzygnięcie: Difficult (10+) DEI + Effect z Average (8+) skilla nadzorcy; porażka zużywa POŁOWĘ supplies.

---

## 10. INDEKSY ZAŁOGI — B3 p.31-45

- **CEI 0-15**; DM: 0⇒-6, 2⇒-4, 5⇒-1, 7-8⇒0, 9-10⇒+1, 11⇒+2, 12⇒+3, 15⇒+6 (pełna tabela B3 p.32). **ECEI = CEI + CEIM** (start: 7+0).
- **CEI w dół:** -1 za każde **25 casualties**; Loss of Confidence (Leadership 8+ albo -1); Shakeup >50 os. (Leadership/Admin 8+, negatywny Effect od CEI).
- **CEI w górę (B3 p.34):** co 2D mies. kwalifikacja; trening 4D dni + Difficult (10+) Leadership/Admin; Effect+2D > obecne CEI ⇒ +1.
- **CEIM:** tragedy (casualties 5% załogi / utrata głównego systemu / Leadership Crisis / utrata dowódcy) ⇒ Difficult (10+) Leadership lub CEIM-1 i MOR-|Effect|. **Cykl co 2D tygodni** (B3 p.34): Difficult (10+) Leadership, Effect jako DM: 0−⇒MOR-1D+3,CEIM-3 / 1-2⇒MOR-1D,CEIM-2 / 3-4⇒MOR-D3,CEIM-1 / 5-8⇒bez zmian / 9-11⇒MOR+1 / 12+⇒CEIM+1,MOR+D3.
- **DEI:** per dywizja (start=CEI); rozstrzygnięcia DEI+CEIM; trening dywizyjny w dowolnym momencie (4D dni zwolnienia, Difficult 10+, Effect+2D>DEI ⇒ +1) — NIE podczas eksploracji/szybkiego tranzytu.
- **MOR 0-15** (DM jak charakterystyka); start CEI+2D3; MOR 0 ⇒ bunt. Minor check fail ⇒ -1; Major ⇒ -1D. Leadership Crisis: MOR -3+ w jednym zdarzeniu lub utrata oficera bez następcy ⇒ check (zwykle Average 8+ Leadership) lub CEIM-|Effect| i CEI-1. Zdarzenia: Hardship/Injustice/Liberty/Severe Danger/Success(+1)/Weak Leadership (B3 p.39).
- **CFI:** start 0. Interwały (B3 p.41): initial 10D dni; standard 6D; stressful 4D; highly stressful 2D; modyfikatory kwater/zapasów ±1D, luxuries +2D. Średnio: pierwszy pkt ~35 dni, potem ~21 dni. Check uniknięcia Fatigued: 2D ≥ CFI (DM: najwyższy skill okrętowy / ECEI dla załogi). Poziomy: Fatigued 0 / Highly -1 / Dangerously -2 (MOR-1) / Exhausted -3 (MOR-D3) / Incapable -4 (MOR-1D). Defatiguing (B3 p.44-45): redukcja CFI ⇒ 2D≥CFI zdejmuje poziom; port -1; Change of Pace 2D dni + Leadership 8+ ⇒ -1; sukces przedsięwzięcia: Difficult 10+ ⇒ -Effect; Wonders ⇒ -1 auto; R&R: -1D/3 dni (przyjazny port) lub -1/7 dni; CFI 0 czyści wszystkie poziomy.
- **EST (Esteem) per Traveller:** Despised -4 … Average 0 … Excellent +4; checki 2D czyste na koniec Reachu (progi 8+/10+/12+ wg pasma). Używany w Extreme Measures.
- **Extreme Measures (B3 p.35):** Difficult (10+) Leadership (dowolny Traveller, EST się liczy); Effect = pula punktów DEI/CEI; **1 pkt DEI = DM+3** na zadanie; **1 pkt CEI = 1 próba niemożliwego**; punkty TRWALE stracone; straty ~1D casualties/pkt.

---

## 11. OPERACJE W SYSTEMIE — B3 p.60-69

- **Tranzyty (rule-of-thumb, B3 p.64):** body↔satelita 1-2h; short inner 20-24h; longer inner 30-40h; mainworld→krawędź inner 50-60h; →outsystem GG 60-80h; →far outsystem 250-300h; outsystem↔outsystem blisko 350-400h; po przeciwnych stronach 500-600h.
- **Course Plotting (B3 p.65):** Average (8+) Astrogation; Effect+DM ⇒ tabela czasu od +75% (0−) do -75% (25+); DM-y: no margin +4 / minimal +2 / fast flyby +8 / flyby-return +4 / harsh braking +2 / close alignment -2 / perfect -4.
- **Deep space manoeuvring (B3 p.65-66):** m-drive DNR zmodyfikowany: >1g w deep space; pilotaż o poziom trudniejszy; Pilot fail Effect -6 ⇒ kolizja albo dryf.
- **Manewry orbitalne (B3 p.66-67):** flyby Easy 4+; slingshot Astrogation 8+ + Pilot 6+; powered orbit Pilot 6+; capture 6+/8+/10+ wg stabilności; insercja jednoetapowa: +1 poziom trudności.
- **Wachty:** 3×8h +1h przygotowania (B3 p.60). Security sweep: 2D×30 min, Easy (4+) CEI/DEI (B3 p.63-64).
- **Planetary surveys (B3 p.77-78):** Preliminary (orbita): kometa 2D min / planeta 4D h / GG 12D h; Routine (6+) DEI lub Electronics. Detailed: planeta 3D dni (20-30 os.) / pas ×3 / kometa 2D h; Easy (4+). Ekspedycje: tabela 8 typów (2 os./2D×5 min … 24 os./2D×6 h); skalowanie +50%/-20% braku, -10%/+25% nadmiaru.

---

## 12. SILNIK ROZSTRZYGANIA ABSTRAKCJI — B3 p.4-6, p.13-29

Hierarchia: Voyage → Reach → Mission → Segment → Operation; Adventure = zejście do RPG. „Adventures use skill checks for individuals; large-scale endeavours use abstract resolution" (B3 p.4).

**Resolution (2D + CEI/DEI DM + modyfikatory, B3 p.23-24):** 0−=Fiasco+Mishap / 1-2=chaos+Mishap / 3-4=Incident / 5=2D 10+⇒Mishap / 6=OK+Incident / 7=OK / 8=OK+Opportunity / 9-10=solidnie / 11-12=2D 12+⇒MOR+1 / 13-14=2D 10+⇒MOR+1, Opportunity / 15+=2D 8+⇒MOR+1, Opportunity.
Modyfikatory (B3 p.23): specialist +2 / improved equipment +1 / pressure -1 / extreme pressure -2 / distractions -1 / difficult circumstances -3 / reluctance -1 / internal divisions -3. Dobrze odegrany Adventure: DM+1 (max +2).

**Incidents / Mishaps / Opportunities (B3 p.25-29):** pełne tabele 2D w raporcie źródłowym. Mishap 12 ⇒ **Crisis**: severity 2D + (podróż >2 lata +2, +1/rok dalej; brak maintenance+treningu +2; major maintenance 12 mies. -1; full overhaul 24 mies. -2): 3−=False Alarm / 4-6=Serious Mishap / 7-9=Minor / 10-12=Major / 13-15=Severe / 16+=Disaster. Nature 1D: 1 Crew / 2-5 systemy / 6 External. Outcome (skala Crew/System/Hull): Minor=1D rannych 2D tyg. / DM-1 / 1D% HP; Major=1D zabitych,ECEI-1 / trwałe -1 / 3D%; Severe=2D zabitych,ECEI-D3,CEI-1 / disabled / 6D%; Disaster=3D zabitych,ECEI-1D,CEI-D3 / destroyed / 12D%. Crisis zawsze ⇒ Adventure.

---

## 13. HOUSE RULES (błędy druku — każda oflagowana w kodzie `# HR:`)

| Miejsce | Problem | Decyzja silnika |
|---|---|---|
| Maintenance Issues (p.53) | brak wiersza 19-20 | traktuj jak 16-18 |
| Rate of Advance (p.17) | Rapid „18+" | **8+** |
| Course Plots (p.65) | pasma 1-2/2-4 nachodzą na 2 | 2 ⇒ +50% |
| Research Events (p.82) | 1-3/3-5 nachodzą na 3 | 3 ⇒ niższe pasmo |
| Effects of Fatigue (p.42) | kolumna DM rozjechana | Fatigued=0 … Incapable=-4 (jak w raporcie) |
| Maintenance Issues (p.53) | 45 w dwóch wierszach | 45 ⇒ 43-45 |
| SI „largest increase" (p.73) | zakres reguły niejasny | sweepy: max; pobyt/remote: kumulacja — do zatwierdzenia przez GM |

## 14. POZA ZAKRESEM SILNIKA (świadomie)

Research (B3 p.79-82), Teams/Weakening (p.35-37), Esteem per-Traveller, Alien Contact (brak mechaniki w B3), walka kosmiczna (core), planetary expeditions szczegółowe — Faza 3+ lub przy stole. Dziennik i GM-mode mają pola na ręczne wpisy tych rozstrzygnięć.
