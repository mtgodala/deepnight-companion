/* Deepnight Companion — UI graczy (vanilla JS, bez builda).
   Wszystkie kości rzuca silnik po stronie serwera; UI pokazuje pełne
   rozbicie rzutu (kości + modyfikatory z ECEI/DEI + próg + Effect).
   i18n: PL (domyślny) / EN — przełącznik w topbarze, wybór w localStorage.
   Dane generowane przez serwer (typy ciał, notki) są PL — w trybie EN
   tłumaczone słownikiem po stronie klienta. */
"use strict";

const $ = (id) => document.getElementById(id);
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || r.statusText);
  }
  return r.json();
};

let STATE = null, SECTORS = [], CUR_SECTOR = null, CUR_MAP = null, SELECTED = null;
let RANGE_SEL = null;      // {sector, hex, j} — planowany zasięg od wybranego hexu
let BOOKMARKS = [];        // piny hexów (state/bookmarks.json)
const ROLLS = [];          // historia rzutów tej sesji przeglądarki (max 20)
const SEC_CACHE = {};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ikony SVG (sprite w index.html) — spójny zestaw zamiast emoji */
const ico = (n) => `<svg class="ico" aria-hidden="true"><use href="#i-${n}"/></svg>`;
const ICO_WARN = ico("warn"), ICO_BAD = ico("ban"), ICO_DICE = ico("dice");

/* ================================ i18n ================================== */

const LANG = localStorage.getItem("dn-lang") === "pl" ? "pl" : "en";   // default: EN
const LOCALE = LANG === "en" ? "en-GB" : "pl";
const num = (n) => n.toLocaleString(LOCALE);

const PL = {
  /* statyczne elementy index.html */
  static: {
    undoBtn: "cofnij", journalBtn: "Dziennik",
    themeTip: "Motyw: ciemny / mapa papierowa", accentTip: "Kolor akcentu",
    undoTitle: "Cofnij ostatnią akcję (korekta pomyłki przy stole)",
    tbDateTitle: "Data imperialna (Imperial date)",
    tbFuelTitle: "Paliwo (fuel) — 6 750 t/parsek, pełny J-4 = 27 000 t",
    tbSuTitle: "Zapasy (Supply Units) — 1 000 SU/dzień (B3 p.46)",
    tbCrewTitle: "ECEI = CEI+CEIM · morale (MOR) · zmęczenie (CFI)",
    initTitle: "Start kampanii",
    initP: "Companion nie ma jeszcze stanu statku (<code>state/ship.json</code>).",
    initStart: "Pozycja startowa:", initDate: "Data imperialna (DDD-YYYY):",
    initMor: "Rzut 2D3 na morale (MOR = CEI+2D3, B3 p.38) — puste = rzuci komputer:",
    initMorPh: "np. 4",
    initGo: "Rozpocznij",
    homeBtn: "na statek", homeTitle: "Wróć do pozycji statku",
    shipPanelH: `Statek <span class="dim">(klik na współczynnik = edycja)</span>`,
    pickHex: "Wybierz hex",
    journalTitle: "Dziennik okrętowy (ship's log)", journalClose: "← mapa",
    noteAuthorPh: "autor / postać", noteTextPh: "wpis do logu...", noteAdd: "Dodaj wpis",
    cancel: "Anuluj", jumpText: "Jumpspace — 7 dni",
    rollsTitle: "Historia rzutów", rollsBtnTip: "Historia rzutów (ta sesja)",
  },
  /* dekodery */
  STARPORT: {
    A: "port klasy A — doskonały (stocznia, paliwo rafinowane)",
    B: "port klasy B — dobry (naprawy, paliwo rafinowane)",
    C: "port klasy C — przeciętny (paliwo nierafinowane)",
    D: "port klasy D — ubogi (tylko lądowisko z obsługą)",
    E: "port klasy E — wyznaczone lądowisko, bez usług",
    X: "brak portu",
  },
  SIZE: ["planetoida (<800 km, ~0 g)", "1 600 km (0,05 g)", "3 200 km (0,15 g)",
    "4 800 km (0,25 g)", "6 400 km (0,35 g)", "8 000 km (0,45 g)", "9 600 km (0,7 g)",
    "11 200 km (0,9 g)", "12 800 km (1,0 g — jak Terra)", "14 400 km (1,25 g)", "16 000 km (1,4 g)"],
  ATMO: ["brak atmosfery (skafander próżniowy)", "śladowa (skafander)",
    "bardzo rzadka, skażona (respirator + filtr)", "bardzo rzadka (respirator)",
    "rzadka, skażona (filtr)", "rzadka (oddychalna)", "standardowa (oddychalna)",
    "standardowa, skażona (filtr)", "gęsta (oddychalna)", "gęsta, skażona (filtr)",
    "egzotyczna (aparat tlenowy)", "żrąca (skafander ochronny)", "wroga — insidious",
    "gęsta, wysoka", "rzadka, niska", "nietypowa"],
  GOV: ["brak (anarchia/rodziny)", "korporacja", "demokracja uczestnicząca",
    "oligarchia samostanowiąca", "demokracja przedstawicielska", "technokracja feudalna",
    "rząd przechwycony/kolonia", "balkanizacja", "biurokracja cywilna", "biurokracja bezosobowa",
    "dyktatura charyzmatyczna", "przywódca niecharyzmatyczny", "oligarchia charyzmatyczna", "teokracja"],
  uwpPort: (p) => p, uwpWorld: (s) => `świat ${s}`, uwpSize: (code) => "rozmiar " + code,
  uwpAtmo: (a) => `atmosfera: ${a}`, uwpHydro: (pct) => `woda: ~${pct}% powierzchni`,
  uwpNoPop: "bez populacji — świat niezamieszkany",
  uwpPop: (n, gov, law) => `populacja rzędu ${n} (${gov}, prawo ${law}/9)`,
  uwpGov: (code) => "rząd " + code, uwpTL: (tl) => `poziom techniki TL ${tl}`,
  STAR_NAMES: { M: "czerwony karzeł", K: "pomarańczowy karzeł",
    G: "żółta gwiazda (typ słoneczny)", F: "żółto-biała gwiazda",
    A: "biała gwiazda", B: "niebiesko-biała gwiazda", O: "błękitny olbrzym" },
  starWD: "biały karzeł", starRG: "czerwony olbrzym", starBD: "brązowy karzeł",
  starNS: `gwiazda neutronowa ${ICO_WARN}`, starBH: `czarna dziura ${ICO_WARN}`,
  BASES: { N: "baza Marynarki (naval base)", S: "baza Skautów (scout base)",
    NS: "bazy Marynarki i Skautów", W: "way station" },
  /* opis systemu */
  emptyHex: "Pustka Wielkiej Szczeliny — w tym hexie nie ma gwiazdy. Skok tutaj oznacza tydzień w kompletnej czerni; jedyną nadzieją na paliwo są samotne komety (Short-Range Detection, B3 p.75).",
  detectedObjects: (list) => "Wykryte obiekty: " + list + ".",
  singleStar: (s) => `Układ pojedynczej gwiazdy: ${s}.`,
  multiStar: (n, list) => `Układ ${n === 2 ? "podwójny" : "wielokrotny"}: ${list}.`,
  starClassGeneral: (cls) => `Gwiazda klasy ${cls} — typ znany tylko ogólnie (podnieś SI do 3).`,
  starPresence: "Sensory potwierdzają obecność gwiazdy. Typ nieznany — potrzebny dokładniejszy skan.",
  ggYes: "Jest gazowy olbrzym — pewne źródło paliwa (skimming, B3 p.68).",
  ggNo: "Nie wykryto gazowego olbrzyma — tankowanie tylko z lodu/komet, jeśli są.",
  habitable: "W układzie jest świat nadający się do życia! Rzadkość w Szczelinie.",
  borderline: "Świat graniczny (borderline habitable) — przetrwanie możliwe, komfort nie.",
  mainworld: (name) => `Główny świat${name ? " — " + name : ""}: `,
  onSite: (b) => `Na miejscu: ${b}.`,
  amber: "⚠ Strefa AMBER — zachowaj ostrożność.",
  red: "⛔ Strefa RED — zakaz kontaktu.",
  noData: "Brak danych — hex czeka na skanowanie.",
  /* lista ciał */
  bodiesUnknown: "Zawartość systemu nieznana — podnieś SI do 6 (skanuj), by zobaczyć listę ciał.",
  bodiesHeader: "Zawartość układu <span class='dim'>(wg strefy orbitalnej)</span>",
  zoneWord: "strefa", si7Hint: "SI 7+ ujawni warunki na poszczególnych ciałach.",
  ZONE_NAMES: { "wewnętrzna": "wewnętrzna", "ekosfera": "ekosfera",
    "zewnętrzna": "zewnętrzna", "daleka": "daleka" },
  trBody: (s) => s, trNote: (s) => s,
  /* check / wynik */
  checkOk: "sukces", checkFail: "porażka",
  /* tooltip mapy */
  tipStar: "gwiazda", tipGG: "gazowy olbrzym",
  /* topbar */
  missionDay: (d) => `dzień misji ${d}`, daysWord: "dni", pcWord: "pc",
  /* panel statku */
  STATS: {
    "cei": ["CEI", "Crew Efficiency Index 0-15 — wyszkolenie załogi (B3 p.32)"],
    "ceim": ["CEIM", "modyfikator CEI — bieżąca forma załogi (B3 p.33)"],
    "__ecei": ["ECEI", "efektywne CEI = CEI + CEIM (tego używa silnik w checkach)"],
    "mor": ["MOR", "morale 0-15; 0 = bunt (B3 p.38)"],
    "cfi": ["CFI", "Crew Fatigue Index — zmęczenie (B3 p.41)"],
    "dei.flight": ["DEI Flight", "efektywność Dywizji Flight — skimming, małe jednostki (B3 p.34)"],
    "dei.engineering": ["DEI Eng", "efektywność Dywizji Engineering — naprawy"],
    "dei.operations": ["DEI Ops", "efektywność Dywizji Operations — ochrona, zaopatrzenie"],
    "dei.mission": ["DEI Mission", "efektywność Dywizji Misji — sensory, nauka, sweepy"],
    "hull_pct": ["Kadłub %", "stan kadłuba (Hull points w %)"],
    "fuel_tons": ["Paliwo t", "paliwo w zbiornikach (max 27 900 t)"],
    "supply_units": ["SU", "Supply Units — zapasy (B3 p.46)"],
    "supply_budget_per_day": ["SU/dzień", "dzienny budżet zapasów (norma 1 000)"],
    "rare_materials": ["Rare Mat.", "rzadkie materiały — naprawy specjalne (B3 p.46)"],
    "rare_biologicals": ["Rare Bio.", "rzadkie biologiczne — leki, racje (B3 p.46)"],
    "exotic_materials": ["Exotic", "materiały egzotyczne (B3 p.46)"],
  },
  editTitle: (l) => `Zmiana: ${l}`, editNew: (v) => `Nowa wartość (obecnie ${v})`,
  editReason: "Powód zmiany — trafi do dziennika", editReasonPh: "np. event: awaria w maszynowni",
  save: "Zapisz", errTitle: "Błąd",
  defectsHead: `Defekty / awarie (DM-1 za defekt, B3 p.53)`, addDefect: "+ dodaj",
  none: "brak", repair: "napraw",
  defectDlgTitle: "Nowy defekt / awaria",
  defectDlgBody: "Defect = DM-1 na zadania z systemem; Breakdown = system osłabiony/niesprawny; Failure = totalna awaria (B3 p.53).",
  defectSystem: "System", defectSystemPh: "np. fuel_processors, m_drive, sensors, hull",
  defectKind: "Typ", defectNote: "Notatka (opcjonalnie)", add: "Dodaj",
  waitBtn: "Postój 7 dni — odpoczynek/badania w bieżącym systemie (+SI z pobytu, B3 p.74)",
  noteBtn: "Szybki wpis do dziennika okrętowego",
  waitDone: (date, su) => `Postój 7 dni. Data: ${date}, SU: ${su}`,
  noteDlgTitle: "Wpis do logu okrętowego", noteText: "Treść wpisu", noteTextDlgPh: "co się wydarzyło...",
  noteAuthor: "Autor / postać (opcjonalnie)", noteAdded: "Wpis dodany do dziennika.", addNote: "Dodaj wpis",
  /* panel hexu / akcje */
  hereBadge: "◉ POZYCJA STATKU",
  targetBadge: (d) => `cel · ${d} pc od statku`,
  siRow: `Survey Index (SI)`, uwpRow: `UWP <span class="dim">(zapis techniczny)</span>`,
  /* siatka UWP + chipy (wzór: karta świata w appkach travellermapowych) */
  GRID: { port: "Port kosmiczny", size: "Rozmiar", atmo: "Atmosfera", hydro: "Hydrografia",
    pop: "Populacja", gov: "Rząd", law: "Prawo", tl: "Poziom techniki" },
  PORT_SHORT: { A: "klasa A — doskonały", B: "klasa B — dobry", C: "klasa C — przeciętny",
    D: "klasa D — ubogi", E: "klasa E — lądowisko", X: "brak portu" },
  mainworldHdr: "Główny świat",
  uwpEstimateChip: "szacunek sensorów",
  lawVal: (n) => `${n}/9`, tlVal: (n) => `TL ${n}`, hydroVal: (pct) => `~${pct}% wody`,
  popNone: "niezamieszkany",
  siChipTip: "Survey Index — ile wiecie o tym systemie (B3 p.71)",
  chipGG: "gazowy olbrzym", chipGGno: "brak gazowego olbrzyma",
  chipHab: "świat zdatny do życia", chipBorder: "świat graniczny",
  chipAmber: "strefa AMBER", chipRed: "strefa RED", chipEmpty: "pusty hex",
  rangeHint: "zasięg stąd:",
  pinTip: "Przypnij hex (cel wyprawy)", unpinTip: "Odepnij hex",
  pinsPh: "★ piny", rollsEmpty: "Brak rzutów w tej sesji.",
  jumpBtn: (d) => `Skok (jump) — ${d} pc`,
  jumpRule: (t, can) => `${t} t paliwa · ~7 dni${can ? "" : " · za mało paliwa"}`,
  courseBtn: (d, j) => `Kurs na cel — ${d} pc (~${j} skoków)`,
  courseRule: (legD, sec, hex, can) => `wykonaj 1. odcinek: skok ${legD} pc do ${sec} ${hex}` +
    `${can ? "" : " · za mało paliwa"} · ${ICO_WARN} hex pośredni może być pusty — sprawdź paliwo`,
  outOfRange: (d) => `Cel ${d} pc — poza zasięgiem J-4; trasa wychodzi poza znane sektory.`,
  scanHintHere: "SKANY tego systemu — kośćmi rzuca silnik (B3 p.72-74):",
  scanHintRemote: (d) => `Statek jest gdzie indziej — z dystansu (${d} pc) działa tylko zdalny sweep (B3 p.72). Pełne skany wymagają skoku do tego systemu:`,
  actRemote: "Zdalny sweep", actRemoteRule: "check Average (8+) na DEI Mission · SI +2×Effect",
  actPassive: "Skan pasywny", actPassiveRule: "+1 SI · 2D min · nie zdradza pozycji",
  actActive: `Skan aktywny ${ICO_WARN}`, actActiveRule: "+D3 SI · 2D h · ujawnia statek nasłuchującym",
  actFull: "Pełny survey", actFullRule: "+1D SI · 4D h · wymaga manewrów",
  actShortrange: "Short-Range Detection", actShortrangeRule: "szukaj obiektów w pustce · 1D dni (B3 p.75)",
  actSkim: "Skimming — głębokie warstwy", actSkimRule: "750 t/pass · check DEI Flight z DM-2",
  actSkimSafe: "Skimming — górne warstwy", actSkimSafeRule: "375 t/pass · bezpiecznie",
  activeConfirmTitle: "Skan aktywny",
  activeConfirmBody: "Aktywny skan ujawni pozycję Deepnight każdemu, kto nasłuchuje (B3 p.73). Kontynuować?",
  scanWord: "Skanuj",
  courseConfirmTitle: "Kurs wieloskokowy",
  courseConfirmBody: (sec, hex) => `Skok pierwszego odcinka do <b>${sec} ${hex}</b>. ` +
    `Po przybyciu kliknij cel ponownie, by wykonać następny odcinek. ` +
    `Pamiętaj o paliwie — hex pośredni może nie mieć gazowego olbrzyma.`,
  jumpWord: "Skacz",
  courseDone: (pc, sec, hex, date) => `Odcinek kursu wykonany: ${pc} pc do ${sec} ${hex}. Data: ${date}`,
  jumpDone: (pc, fuel, date) => `Skok wykonany: ${pc} pc, -${fuel} t. Data: ${date}`,
  scanGain: (g) => ` (${ICO_DICE} przyrost: ${g})`, timeWord: "czas",
  noProgress: (best) => ` — bez postępu: liczy się tylko NAJWIĘKSZY pojedynczy przyrost (B3 p.73), a dotychczasowy najlepszy sweep dał +${best}. SI podniesie mocniejszy wynik albo pobyt w systemie (+1 co ~6 dni, B3 p.74).`,
  skimDone: (p, t, d) => `Skimming: ${p} passów, +${t} t, przetwarzanie ${d} dnia`,
  srMsg: (roll, near, days, found) => `${ICO_DICE} 2D+DM = ${roll} (najbliższa gwiazda ${near} pc) · sweep ${days} dni → ${found}`,
  srNothing: "nic nie znaleziono",
  /* dziennik */
  KIND: { init: "START", scan: "SKAN", jump: "SKOK", skim: "PALIWO",
    wait: "POSTÓJ", note: "WPIS", undo: "COFNIĘCIE", edit: "KOREKTA", shortrange: "SWEEP" },
  /* undo */
  undoConfirmTitle: "Cofnij ostatnią akcję",
  undoConfirmBody: "Pozycja, paliwo, czas i SI wrócą do stanu sprzed akcji. Wpis o cofnięciu trafi do dziennika.",
  undoWord: "Cofnij", undoDone: (a) => `↩ cofnięto: ${a}`,
  /* mapa */
  secUnmapped: "sektor niezmapowany — gwiazdy nieznane do czasu skanów",
  secData: (s) => `dane: ${s}`, noSector: "brak sektora",
  trNoteSrv: (s) => s,
};

const EN = {
  static: {
    undoBtn: "undo", journalBtn: "Log",
    themeTip: "Theme: dark / paper chart", accentTip: "Accent colour",
    undoTitle: "Undo the last action (table mistake correction)",
    tbDateTitle: "Imperial date",
    tbFuelTitle: "Fuel — 6,750 t/parsec, full J-4 = 27,000 t",
    tbSuTitle: "Supply Units — 1,000 SU/day (B3 p.46)",
    tbCrewTitle: "ECEI = CEI+CEIM · morale (MOR) · fatigue (CFI)",
    initTitle: "Campaign start",
    initP: "Companion has no ship state yet (<code>state/ship.json</code>).",
    initStart: "Starting position:", initDate: "Imperial date (DDD-YYYY):",
    initMor: "2D3 morale roll (MOR = CEI+2D3, B3 p.38) — empty = computer rolls:",
    initMorPh: "e.g. 4",
    initGo: "Begin",
    homeBtn: "to ship", homeTitle: "Return to ship position",
    shipPanelH: `Ship <span class="dim">(click a stat to edit)</span>`,
    pickHex: "Select a hex",
    journalTitle: "Ship's log", journalClose: "← map",
    noteAuthorPh: "author / character", noteTextPh: "log entry...", noteAdd: "Add entry",
    cancel: "Cancel", jumpText: "Jumpspace — 7 days",
    rollsTitle: "Roll history", rollsBtnTip: "Roll history (this session)",
  },
  STARPORT: {
    A: "class A starport — excellent (shipyard, refined fuel)",
    B: "class B starport — good (repairs, refined fuel)",
    C: "class C starport — routine (unrefined fuel)",
    D: "class D starport — poor (serviced landing site only)",
    E: "class E starport — frontier landing spot, no services",
    X: "no starport",
  },
  SIZE: ["planetoid (<800 km, ~0 g)", "1,600 km (0.05 g)", "3,200 km (0.15 g)",
    "4,800 km (0.25 g)", "6,400 km (0.35 g)", "8,000 km (0.45 g)", "9,600 km (0.7 g)",
    "11,200 km (0.9 g)", "12,800 km (1.0 g — Terra-like)", "14,400 km (1.25 g)", "16,000 km (1.4 g)"],
  ATMO: ["no atmosphere (vacc suit)", "trace (vacc suit)",
    "very thin, tainted (respirator + filter)", "very thin (respirator)",
    "thin, tainted (filter)", "thin (breathable)", "standard (breathable)",
    "standard, tainted (filter)", "dense (breathable)", "dense, tainted (filter)",
    "exotic (air supply)", "corrosive (protective suit)", "hostile — insidious",
    "dense, high", "thin, low", "unusual"],
  GOV: ["none (anarchy/families)", "corporation", "participating democracy",
    "self-perpetuating oligarchy", "representative democracy", "feudal technocracy",
    "captive government/colony", "balkanisation", "civil service bureaucracy", "impersonal bureaucracy",
    "charismatic dictator", "non-charismatic leader", "charismatic oligarchy", "religious dictatorship"],
  uwpPort: (p) => p, uwpWorld: (s) => `world ${s}`, uwpSize: (code) => "size " + code,
  uwpAtmo: (a) => `atmosphere: ${a}`, uwpHydro: (pct) => `water: ~${pct}% of surface`,
  uwpNoPop: "no population — uninhabited world",
  uwpPop: (n, gov, law) => `population on the order of ${n} (${gov}, law ${law}/9)`,
  uwpGov: (code) => "government " + code, uwpTL: (tl) => `tech level TL ${tl}`,
  STAR_NAMES: { M: "red dwarf", K: "orange dwarf",
    G: "yellow star (solar type)", F: "yellow-white star",
    A: "white star", B: "blue-white star", O: "blue giant" },
  starWD: "white dwarf", starRG: "red giant", starBD: "brown dwarf",
  starNS: `neutron star ${ICO_WARN}`, starBH: `black hole ${ICO_WARN}`,
  BASES: { N: "Naval base", S: "Scout base",
    NS: "Naval and Scout bases", W: "way station" },
  emptyHex: "The void of the Great Rift — there is no star in this hex. Jumping here means a week in total blackness; lone comets are the only hope for fuel (Short-Range Detection, B3 p.75).",
  detectedObjects: (list) => "Detected objects: " + list + ".",
  singleStar: (s) => `Single-star system: ${s}.`,
  multiStar: (n, list) => `${n === 2 ? "Binary" : "Multiple"} system: ${list}.`,
  starClassGeneral: (cls) => `Star of class ${cls} — type known only roughly (raise SI to 3).`,
  starPresence: "Sensors confirm a star is present. Type unknown — a closer scan is needed.",
  ggYes: "There is a gas giant — a reliable fuel source (skimming, B3 p.68).",
  ggNo: "No gas giant detected — refuelling only from ice/comets, if any.",
  habitable: "There is a habitable world in the system! A rarity in the Rift.",
  borderline: "Borderline habitable world — survival possible, comfort not.",
  mainworld: (name) => `Mainworld${name ? " — " + name : ""}: `,
  onSite: (b) => `On site: ${b}.`,
  amber: "⚠ AMBER zone — proceed with caution.",
  red: "⛔ RED zone — no contact allowed.",
  noData: "No data — this hex awaits scanning.",
  bodiesUnknown: "System contents unknown — raise SI to 6 (scan) to see the body list.",
  bodiesHeader: "System contents <span class='dim'>(by orbital zone)</span>",
  zoneWord: "zone:", si7Hint: "SI 7+ will reveal conditions on individual bodies.",
  ZONE_NAMES: { "wewnętrzna": "inner", "ekosfera": "habitable zone",
    "zewnętrzna": "outer", "daleka": "far outer" },
  trBody: (s) => EN_BODY[s] || s, trNote: (s) => EN_NOTE[s] || s,
  checkOk: "success", checkFail: "failure",
  tipStar: "star", tipGG: "gas giant",
  missionDay: (d) => `mission day ${d}`, daysWord: "days", pcWord: "pc",
  STATS: {
    "cei": ["CEI", "Crew Efficiency Index 0-15 — crew training (B3 p.32)"],
    "ceim": ["CEIM", "CEI modifier — current crew condition (B3 p.33)"],
    "__ecei": ["ECEI", "effective CEI = CEI + CEIM (used by the engine in checks)"],
    "mor": ["MOR", "morale 0-15; 0 = mutiny (B3 p.38)"],
    "cfi": ["CFI", "Crew Fatigue Index — fatigue (B3 p.41)"],
    "dei.flight": ["DEI Flight", "Flight Division efficiency — skimming, small craft (B3 p.34)"],
    "dei.engineering": ["DEI Eng", "Engineering Division efficiency — repairs"],
    "dei.operations": ["DEI Ops", "Operations Division efficiency — security, supply"],
    "dei.mission": ["DEI Mission", "Mission Division efficiency — sensors, science, sweeps"],
    "hull_pct": ["Hull %", "hull condition (Hull points in %)"],
    "fuel_tons": ["Fuel t", "fuel in tanks (max 27,900 t)"],
    "supply_units": ["SU", "Supply Units — supplies (B3 p.46)"],
    "supply_budget_per_day": ["SU/day", "daily supply budget (norm 1,000)"],
    "rare_materials": ["Rare Mat.", "rare materials — special repairs (B3 p.46)"],
    "rare_biologicals": ["Rare Bio.", "rare biologicals — medicine, rations (B3 p.46)"],
    "exotic_materials": ["Exotic", "exotic materials (B3 p.46)"],
  },
  editTitle: (l) => `Edit: ${l}`, editNew: (v) => `New value (currently ${v})`,
  editReason: "Reason for change — goes to the log", editReasonPh: "e.g. event: engine room failure",
  save: "Save", errTitle: "Error",
  defectsHead: `Defects / breakdowns (DM-1 per defect, B3 p.53)`, addDefect: "+ add",
  none: "none", repair: "repair",
  defectDlgTitle: "New defect / breakdown",
  defectDlgBody: "Defect = DM-1 on tasks using the system; Breakdown = system degraded/inoperable; Failure = total failure (B3 p.53).",
  defectSystem: "System", defectSystemPh: "e.g. fuel_processors, m_drive, sensors, hull",
  defectKind: "Kind", defectNote: "Note (optional)", add: "Add",
  waitBtn: "Hold 7 days — rest/research in the current system (+SI from dwelling, B3 p.74)",
  noteBtn: "Quick entry in the ship's log",
  waitDone: (date, su) => `Held for 7 days. Date: ${date}, SU: ${su}`,
  noteDlgTitle: "Ship's log entry", noteText: "Entry text", noteTextDlgPh: "what happened...",
  noteAuthor: "Author / character (optional)", noteAdded: "Entry added to the log.", addNote: "Add entry",
  hereBadge: "◉ SHIP POSITION",
  targetBadge: (d) => `target · ${d} pc from ship`,
  siRow: `Survey Index (SI)`, uwpRow: `UWP <span class="dim">(technical notation)</span>`,
  GRID: { port: "Starport", size: "Size", atmo: "Atmosphere", hydro: "Hydrographics",
    pop: "Population", gov: "Government", law: "Law level", tl: "Tech level" },
  PORT_SHORT: { A: "class A — excellent", B: "class B — good", C: "class C — routine",
    D: "class D — poor", E: "class E — frontier", X: "no starport" },
  mainworldHdr: "Mainworld",
  uwpEstimateChip: "sensor estimate",
  lawVal: (n) => `${n}/9`, tlVal: (n) => `TL ${n}`, hydroVal: (pct) => `~${pct}% water`,
  popNone: "uninhabited",
  siChipTip: "Survey Index — how much you know about this system (B3 p.71)",
  chipGG: "gas giant", chipGGno: "no gas giant",
  chipHab: "habitable world", chipBorder: "borderline habitable",
  chipAmber: "AMBER zone", chipRed: "RED zone", chipEmpty: "empty hex",
  rangeHint: "range from here:",
  pinTip: "Pin this hex (expedition target)", unpinTip: "Unpin this hex",
  pinsPh: "★ pins", rollsEmpty: "No rolls this session.",
  jumpBtn: (d) => `Jump — ${d} pc`,
  jumpRule: (t, can) => `${t} t of fuel · ~7 days${can ? "" : " · not enough fuel"}`,
  courseBtn: (d, j) => `Set course — ${d} pc (~${j} jumps)`,
  courseRule: (legD, sec, hex, can) => `execute leg 1: jump ${legD} pc to ${sec} ${hex}` +
    `${can ? "" : " · not enough fuel"} · ${ICO_WARN} the intermediate hex may be empty — watch your fuel`,
  outOfRange: (d) => `Target ${d} pc away — beyond J-4 range; the route leaves known sectors.`,
  scanHintHere: "SCANS of this system — the engine rolls the dice (B3 p.72-74):",
  scanHintRemote: (d) => `The ship is elsewhere — at range (${d} pc) only a remote sweep works (B3 p.72). Full scans require jumping to this system:`,
  actRemote: "Remote sweep", actRemoteRule: "Average (8+) check on DEI Mission · SI +2×Effect",
  actPassive: "Passive scan", actPassiveRule: "+1 SI · 2D min · does not reveal position",
  actActive: `Active scan ${ICO_WARN}`, actActiveRule: "+D3 SI · 2D h · reveals the ship to listeners",
  actFull: "Full survey", actFullRule: "+1D SI · 4D h · requires manoeuvring",
  actShortrange: "Short-Range Detection", actShortrangeRule: "search the void for objects · 1D days (B3 p.75)",
  actSkim: "Skimming — deep layers", actSkimRule: "750 t/pass · DEI Flight check at DM-2",
  actSkimSafe: "Skimming — upper layers", actSkimSafeRule: "375 t/pass · safe",
  activeConfirmTitle: "Active scan",
  activeConfirmBody: "An active scan reveals Deepnight's position to anyone listening (B3 p.73). Continue?",
  scanWord: "Scan",
  courseConfirmTitle: "Multi-jump course",
  courseConfirmBody: (sec, hex) => `Jump the first leg to <b>${sec} ${hex}</b>. ` +
    `After arrival click the target again to execute the next leg. ` +
    `Mind your fuel — the intermediate hex may have no gas giant.`,
  jumpWord: "Jump",
  courseDone: (pc, sec, hex, date) => `Course leg executed: ${pc} pc to ${sec} ${hex}. Date: ${date}`,
  jumpDone: (pc, fuel, date) => `Jump executed: ${pc} pc, -${fuel} t. Date: ${date}`,
  scanGain: (g) => ` (${ICO_DICE} gain: ${g})`, timeWord: "time",
  noProgress: (best) => ` — no progress: only the LARGEST single increase counts (B3 p.73), and the best sweep so far gave +${best}. SI will rise from a stronger result or from dwelling in-system (+1 per ~6 days, B3 p.74).`,
  skimDone: (p, t, d) => `Skimming: ${p} passes, +${t} t, processing ${d} days`,
  srMsg: (roll, near, days, found) => `${ICO_DICE} 2D+DM = ${roll} (nearest star ${near} pc) · sweep ${days} days → ${found}`,
  srNothing: "nothing found",
  KIND: { init: "START", scan: "SCAN", jump: "JUMP", skim: "FUEL",
    wait: "HOLD", note: "NOTE", undo: "UNDO", edit: "EDIT", shortrange: "SWEEP" },
  undoConfirmTitle: "Undo last action",
  undoConfirmBody: "Position, fuel, time and SI will revert to the state before the action. An undo entry goes to the log.",
  undoWord: "Undo", undoDone: (a) => `↩ undone: ${a}`,
  secUnmapped: "unmapped sector — stars unknown until scanned",
  secData: (s) => `data: ${s}`, noSector: "no sector",
  trNoteSrv: (s) => {
    for (const [re, sub] of EN_SRV_NOTES) { const m = s.match(re); if (m) return typeof sub === "function" ? sub(m) : sub; }
    return s;
  },
};

/* tłumaczenia danych generowanych przez serwer (PL w state/) — tylko EN */
const EN_BODY = {
  "gorący świat skalny (hot rockball)": "hot rockball",
  "świat skalny (rockball)": "rockball",
  "świat wulkaniczny": "volcanic world",
  "świat pustynny": "desert world",
  "świat śladowy (trace world)": "trace world",
  "świat wodny": "water world",
  "super-ziemia": "super-earth",
  "świat lodowy (iceball)": "iceball",
  "gazowy karzeł (gas dwarf)": "gas dwarf",
  "mały gazowy olbrzym": "small gas giant",
  "duży gazowy olbrzym": "large gas giant",
  "pas planetoid": "planetoid belt",
  "rozproszone planetoidy lodowe": "scattered icy planetoids",
  "ciało przechwycone (captured body)": "captured body",
  "świat nadający się do życia": "habitable world",
  "świat graniczny (borderline habitable)": "borderline habitable world",
};
const EN_NOTE = {
  "powierzchnia spieczona, bez atmosfery lub śladowa": "scorched surface, no or trace atmosphere",
  "aktywna tektonika, ryzykowne lądowanie": "active tectonics, risky landing",
  "sucho, możliwa rzadka atmosfera": "arid, possibly a thin atmosphere",
  "resztkowa atmosfera": "residual atmosphere",
  "temperatury znośne, brak wody powierzchniowej": "bearable temperatures, no surface water",
  "ocean pod atmosferą lub lodem": "ocean beneath atmosphere or ice",
  "grawitacja 1.2-2 g (B3 p.89)": "gravity 1.2-2 g (B3 p.89)",
  "lód wodny = potencjalne paliwo": "water ice = potential fuel",
  "skimming możliwy": "skimming possible",
  "nietypowa orbita": "unusual orbit",
  "możliwe źródło paliwa": "possible fuel source",
  "potwierdzone źródło paliwa (skimming, B3 p.68)": "confirmed fuel source (skimming, B3 p.68)",
  "nadaje się do wydobycia surowców (B3 p.21)": "suitable for resource mining (B3 p.21)",
  "cel priorytetowy dla Dywizji Misji": "priority target for the Mission Division",
};
/* notki/błędy generowane przez serwer — dopasowanie wzorców */
const EN_SRV_NOTES = [
  [/^AKTYWNY SKAN:/, "ACTIVE SCAN: ship position revealed to anyone listening (B3 p.73)"],
  [/^Pobyt w systemie: SI \+(\d+)/, (m) => `Dwelling in-system: SI +${m[1]} (B3 p.74)`],
  [/^SUPPLY 0:/, "SUPPLY 0: out of supplies — auto CEIM/MOR -1D every 2D days (B3 p.49)"],
  [/^Post-Jump Primary niepe/, "Post-Jump Primary incomplete: system data limited, repeat sensor procedures (B3 p.63)"],
  [/^Pusty hex:/, "Empty hex: Short-Range Detection action available (B3 p.75)"],
  [/^Operacja posz/, "Operation went poorly: time +50%; Erosion of Capabilities check advised (B3 p.56) [HR]"],
  [/wymaga obecno/, "Passive/active/full survey requires being in the system — only a remote sweep works at range (B3 p.72-73)"],
  [/^Zbiorniki pe/, "Tanks are full"],
  [/^Brak potwierdzonego gazowego olbrzyma/, "No confirmed gas giant in this system (requires SI 5+ and a GG present)"],
  [/^Brak akcji do cofni/, "No action to undo"],
];

const T = LANG === "en" ? EN : PL;
const trNotes = (notes) => (notes || []).map((n) => T.trNoteSrv(n));

function applyStaticI18n() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = T.static[el.dataset.i18n]; if (v) el.textContent = v;
  });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => {
    const v = T.static[el.dataset.i18nHtml]; if (v) el.innerHTML = v;
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const v = T.static[el.dataset.i18nTitle]; if (v) el.title = v;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const v = T.static[el.dataset.i18nPlaceholder]; if (v) el.placeholder = v;
  });
  const btn = $("btn-lang");
  btn.textContent = LANG === "en" ? "PL" : "EN";
  btn.addEventListener("click", () => {
    localStorage.setItem("dn-lang", LANG === "en" ? "pl" : "en");
    location.reload();
  });
  /* motyw ciemny/papierowy + kolor akcentu (dn-theme / dn-accent) */
  $("btn-theme").addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "paper" ? "dark" : "paper";
    document.documentElement.dataset.theme = t;
    localStorage.setItem("dn-theme", t);
  });
  const ACCENTS = ["blue", "green", "amber"];
  $("btn-accent").addEventListener("click", () => {
    const cur = document.documentElement.dataset.accent || "blue";
    const next = ACCENTS[(ACCENTS.indexOf(cur) + 1) % ACCENTS.length];
    document.documentElement.dataset.accent = next;
    localStorage.setItem("dn-accent", next);
  });
}

/* ---------- dialogi (zamiast natywnych prompt/confirm/alert) ------------- */
function showDialog({ title, body = "", fields = [], okLabel = "OK" }) {
  return new Promise((resolve) => {
    const dlg = $("dlg");
    $("dlg-title").textContent = title;
    $("dlg-body").innerHTML = body;
    $("dlg-fields").innerHTML = fields.map((f) => {
      if (f.type === "select")
        return `<label>${f.label}<select data-name="${f.name}">${f.options.map((o) => `<option value="${o}">${o}</option>`).join("")}</select></label>`;
      return `<label>${f.label}<input data-name="${f.name}" value="${f.value ?? ""}" placeholder="${f.placeholder ?? ""}"></label>`;
    }).join("");
    $("dlg-ok").textContent = okLabel;
    const close = (result) => { dlg.close(); resolve(result); cleanup(); };
    const onOk = () => {
      const vals = {};
      $("dlg-fields").querySelectorAll("[data-name]").forEach((el) => { vals[el.dataset.name] = el.value; });
      close(vals);
    };
    const onCancel = () => close(null);
    const onKey = (e) => { if (e.key === "Enter" && fields.length) { e.preventDefault(); onOk(); } };
    function cleanup() {
      $("dlg-ok").removeEventListener("click", onOk);
      $("dlg-cancel").removeEventListener("click", onCancel);
      dlg.removeEventListener("keydown", onKey);
    }
    $("dlg-ok").addEventListener("click", onOk);
    $("dlg-cancel").addEventListener("click", onCancel);
    dlg.addEventListener("keydown", onKey);
    dlg.showModal();
    const first = $("dlg-fields").querySelector("input,select");
    if (first) first.focus();
  });
}
const showConfirm = (title, body, okLabel) =>
  showDialog({ title, body, okLabel: okLabel || (LANG === "en" ? "Yes" : "Tak") }).then((r) => r !== null);
const showInfo = (title, body) => showDialog({ title, body, okLabel: LANG === "en" ? "Close" : "Zamknij" });

/* ============================ DEKODERY =================================== */

const hexVal = (ch) => parseInt(ch, 18);

/* siatka label/value dekodująca UWP — pola ponad progiem SI pokazują "—" */
function renderUwpGrid(view) {
  const el = $("hex-uwp");
  const raw = view.mainworld_uwp || view.uwp_partial || view.uwp_estimate;
  if (!raw || view.empty) { el.innerHTML = ""; return; }
  const code = raw.replace(/\s*\(.*\)\s*$/, "");   // uwp_estimate ma dopisek "(szacunek)"
  const [port, size, atmo, hydro, pop, gov, law] = code;
  const tlRaw = (code.split("-")[1] || "").trim();
  const V = (ch, fn) => (!ch || ch === "?" ? "—" : fn(ch));
  const p = pop && pop !== "?" ? hexVal(pop) : null;
  const rows = [
    [T.GRID.port, V(port, (c) => T.PORT_SHORT[c] || c)],
    [T.GRID.size, V(size, (c) => T.SIZE[hexVal(c)] || c)],
    [T.GRID.atmo, V(atmo, (c) => T.ATMO[hexVal(c)] || c)],
    [T.GRID.hydro, V(hydro, (c) => T.hydroVal(hexVal(c) * 10))],
    [T.GRID.pop, p === null ? "—" : (p === 0 ? T.popNone : num(10 ** p))],
    [T.GRID.gov, p === 0 ? "—" : V(gov, (c) => T.GOV[hexVal(c)] || c)],
    [T.GRID.law, p === 0 ? "—" : V(law, (c) => T.lawVal(hexVal(c)))],
    [T.GRID.tl, p === 0 ? "—" : (tlRaw && tlRaw !== "?" ? T.tlVal(parseInt(tlRaw, 18)) : "—")],
  ];
  const est = view.uwp_estimate ? ` <span class="chip chip-dim">${T.uwpEstimateChip}</span>` : "";
  el.innerHTML =
    `<div class="uwp-head">${T.mainworldHdr}${view.name ? " — " + view.name : ""} <code>${code}</code>${est}</div>` +
    `<div class="uwp-grid">` + rows.map(([l, v]) =>
      `<div class="uwp-cell"><span class="uwp-lbl">${l}</span><span class="uwp-val">${v}</span></div>`).join("") +
    `</div>`;
}

/* chipy statusów systemu — fakty widoczne od razu, bez czytania prozy */
function renderChips(view, hex) {
  const chips = [`<span class="chip chip-si" title="${T.siChipTip}">SI ${view.si}/12</span>`];
  if (view.empty) chips.push(`<span class="chip chip-dim">${T.chipEmpty}</span>`);
  if (view.gas_giant === true) chips.push(`<span class="chip chip-ok">${ico("gg")} ${T.chipGG}</span>`);
  else if (view.gas_giant === false) chips.push(`<span class="chip chip-dim">${T.chipGGno}</span>`);
  if (view.habitable) chips.push(`<span class="chip chip-ok">${ico("globe")} ${T.chipHab}</span>`);
  else if (view.borderline_habitable) chips.push(`<span class="chip chip-warn">${ico("half")} ${T.chipBorder}</span>`);
  if (view.bases && T.BASES[view.bases]) chips.push(`<span class="chip chip-info">${T.BASES[view.bases]}</span>`);
  if (view.zone === "A") chips.push(`<span class="chip chip-warn">${ICO_WARN} ${T.chipAmber}</span>`);
  if (view.zone === "R") chips.push(`<span class="chip chip-bad">${ICO_BAD} ${T.chipRed}</span>`);
  /* planowanie: podświetl hexy w promieniu J1-J4 od TEGO hexu */
  const active = RANGE_SEL && RANGE_SEL.sector === CUR_SECTOR && RANGE_SEL.hex === hex ? RANGE_SEL.j : 0;
  chips.push(`<span class="chip chip-dim">${T.rangeHint}</span>`);
  for (const j of [1, 2, 3, 4])
    chips.push(`<button class="chip chip-btn${active === j ? " active" : ""}" data-j="${j}">J${j}</button>`);
  if (active) chips.push(`<button class="chip chip-btn" data-j="0">✕</button>`);
  $("hex-chips").innerHTML = chips.join("");
  $("hex-chips").querySelectorAll(".chip-btn").forEach((b) =>
    b.addEventListener("click", () => {
      const j = parseInt(b.dataset.j, 10);
      RANGE_SEL = (!j || j === active) ? null : { sector: CUR_SECTOR, hex, j };
      selectHex(hex);
    }));
}

function decodeStar(s) {
  if (!s) return s;
  if (/white dwarf/i.test(s)) return T.starWD;
  if (/red giant/i.test(s)) return T.starRG;
  if (/brown dwarf/i.test(s)) return T.starBD;
  if (/neutron/i.test(s) || s.trim() === "NS") return T.starNS;
  if (/black hole/i.test(s) || s.trim() === "BH") return T.starBH;
  const m = s.trim().match(/^([OBAFGKM])(\d)?/i);
  if (m) return `${T.STAR_NAMES[m[1].toUpperCase()]} (${s.trim()})`;
  return s;
}

function describeSystem(v) {
  const p = [];
  if (v.empty) {
    p.push(T.emptyHex);
    if (v.deep_space_objects?.length)
      p.push(T.detectedObjects(v.deep_space_objects.map((o) => o.desc || o.kind).join("; ")));
    return p;
  }
  if (v.stars?.length) {
    const stars = v.stars.map(decodeStar);
    p.push(stars.length === 1 ? T.singleStar(stars[0]) : T.multiStar(stars.length, stars.join(" + ")));
  } else if (v.star_class_general) {
    p.push(T.starClassGeneral(v.star_class_general.join(", ")));
  } else if (v.star_presence) {
    p.push(T.starPresence);
  }
  /* GG / habitable / bazy / strefy / UWP przeniesione do chipów i siatki UWP */
  if (!p.length) p.push(T.noData);
  return p;
}

/* lista ciał per strefa (SI 5+: gazowe olbrzymy, 6+: wszystko, 7+: notki) */
function renderBodies(v) {
  const el = $("hex-bodies");
  if (!v.bodies_detail?.length) {
    el.innerHTML = v.empty || v.canon ? "" :
      (v.si < 6 ? `<div class="dim">${T.bodiesUnknown}</div>` : "");
    return;
  }
  const ICON = { gg: ico("gg"), belt: ico("belt"), world: ico("moon") };
  const zones = {};
  for (const b of v.bodies_detail) (zones[b.zone] ||= []).push(b);
  const html = [`<h4>${T.bodiesHeader}</h4>`];
  for (const zone of ["wewnętrzna", "ekosfera", "zewnętrzna", "daleka"]) {
    if (!zones[zone]) continue;
    html.push(`<div class="zone"><span class="zone-name">${T.zoneWord} ${T.ZONE_NAMES[zone] || zone}</span>`);
    for (const b of zones[zone])
      html.push(`<div class="body-row">${ICON[b.kind] || "•"} ${T.trBody(b.type)}${b.note ? ` <span class="dim">— ${T.trNote(b.note)}</span>` : ""}</div>`);
    html.push("</div>");
  }
  if (v.si < 7) html.push(`<div class="dim">${T.si7Hint}</div>`);
  el.innerHTML = html.join("");
}

/* rozbicie checku silnika dla graczy */
function fmtCheck(c) {
  if (!c) return "";
  const dms = c.dms.map((d) => `${d.label} ${d.value >= 0 ? "+" : ""}${d.value}`).join(" · ");
  const res = c.success ? `<b class="ok">${T.checkOk}</b>` : `<b class="warn">${T.checkFail}</b>`;
  return `<div class="check">${ICO_DICE} <b>${c.label}</b>: [${c.dice.join("+")}]=${c.dice.reduce((a, b) => a + b, 0)}` +
    (dms ? ` · ${dms}` : "") +
    ` → <b>${c.total}</b> vs ${c.target}+ → ${res} (Effect ${c.effect >= 0 ? "+" : ""}${c.effect}) <span class="dim">${c.page || ""}</span></div>`;
}

/* ========================== GEOMETRIA / MAPA ============================= */

const R = 9, H = Math.sqrt(3) * R, PREV = 4;
let BASE_VB = null, VIEW = null;   // zoom/pan: VIEW = {x,y,w,h} albo null (całość)

function hexCenter(hx, hy) {
  return [(hx - 1) * 1.5 * R, (hy - 1) * H + (((hx % 2) + 2) % 2 === 0 ? H / 2 : 0)];
}
function hexPoints(cx, cy) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * 60 * i;
    pts.push(`${(cx + R * Math.cos(a)).toFixed(1)},${(cy + R * Math.sin(a)).toFixed(1)}`);
  }
  return pts.join(" ");
}
function worldXY(secX, secY, hex) {
  return [secX * 32 + (parseInt(hex.slice(0, 2), 10) - 1),
          secY * 40 + (parseInt(hex.slice(2), 10) - 1)];
}
const toCube = ([x, y]) => {
  const q = x, r = y - Math.floor((x - (((x % 2) + 2) % 2)) / 2);
  return [q, r, -q - r];
};
const fromCube = ([q, r]) => [q, r + Math.floor((q - (((q % 2) + 2) % 2)) / 2)];
function distPc(a, b) {
  const [aq, ar, as] = toCube(a), [bq, br, bs] = toCube(b);
  return (Math.abs(aq - bq) + Math.abs(ar - br) + Math.abs(as - bs)) / 2;
}
function cubeRound(q, r, s) {
  let rq = Math.round(q), rr = Math.round(r), rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs;
  else if (dr > ds) rr = -rq - rs;
  else rs = -rq - rr;
  return [rq, rr, rs];
}
/* hex oddalony o `step` pc od `a` w kierunku `b` (interpolacja cube) */
function stepToward(a, b, step) {
  const d = distPc(a, b);
  if (d <= step) return b;
  const ca = toCube(a), cb = toCube(b);
  for (let s = step; s >= 1; s--) {           // cubeRound moze wyladowac o 1 dalej
    const t = s / d;
    const c = cubeRound(ca[0] + (cb[0] - ca[0]) * t,
                        ca[1] + (cb[1] - ca[1]) * t,
                        ca[2] + (cb[2] - ca[2]) * t);
    const w = fromCube(c);
    if (distPc(a, w) >= 1 && distPc(a, w) <= step) return w;
  }
  return null;
}
/* world (x,y) -> {sector, hex} — o ile sektor istnieje w danych */
function worldToSectorHex([x, y]) {
  const sx = Math.floor(x / 32), sy = Math.floor(y / 40);
  const sec = SECTORS.find((s) => s.x === sx && s.y === sy);
  if (!sec) return null;
  const hx = x - sx * 32 + 1, hy = y - sy * 40 + 1;
  return { sector: sec.name, hex: String(hx).padStart(2, "0") + String(hy).padStart(2, "0") };
}

async function getSector(name) {
  if (!SEC_CACHE[name]) SEC_CACHE[name] = await api(`/api/sector/${encodeURIComponent(name)}`);
  return SEC_CACHE[name];
}
function invalidateSector(name) { delete SEC_CACHE[name]; }

/* domyślny widok: wypełnij ekran, wycentrowany na statku (dwuklik = cały sektor) */
function defaultView() {
  if (!BASE_VB) return null;
  const wrap = $("map-wrap").getBoundingClientRect();
  if (!wrap.width || !wrap.height) return null;
  const w = BASE_VB.w, h = w / (wrap.width / wrap.height);
  if (h >= BASE_VB.h) return null;      // ekran wyższy niż mapa — fit całości
  let cy = BASE_VB.y + BASE_VB.h / 2;
  const s = SECTORS.find((q) => q.name === STATE?.position?.sector);
  if (s && CUR_MAP) {
    const [wx, wy] = worldXY(s.x, s.y, STATE.position.hex);
    const relX = wx - CUR_MAP.x * 32 + 1, relY = wy - CUR_MAP.y * 40 + 1;
    if (relX >= -PREV && relX <= 33 + PREV && relY >= -PREV && relY <= 41 + PREV)
      cy = hexCenter(relX, relY)[1];
  }
  const y = Math.max(BASE_VB.y, Math.min(cy - h / 2, BASE_VB.y + BASE_VB.h - h));
  return { x: BASE_VB.x, y, w, h };
}

async function loadSector(name) {
  CUR_SECTOR = name;
  invalidateSector(name);
  CUR_MAP = await getSector(name);
  $("sec-select").value = name;
  $("sec-status").textContent =
    CUR_MAP.worlds_source === "generate" ? T.secUnmapped : T.secData(CUR_MAP.data_status || "?");
  await renderMap();
  if (!VIEW) { VIEW = defaultView(); applyView(); }
  renderArrows();
}

function shipGlyph(cx, cy, angleDeg = 0) {
  return `<circle class="ship-ring" cx="${cx}" cy="${cy}" r="${(R * 0.82).toFixed(1)}"/>` +
    `<g class="ship-glyph" transform="translate(${cx},${cy}) rotate(${angleDeg.toFixed(0)}) scale(0.9)">
    <path d="M0,-8 C1.8,-5 2.2,-1 2.2,3 L4.8,6 L1.6,5.2 C0.9,6.6 -0.9,6.6 -1.6,5.2 L-4.8,6 L-2.2,3 C-2.2,-1 -1.8,-5 0,-8 Z" filter="url(#glow-s)"/>
    <circle cx="0" cy="7" r="1.5" class="engine"/>
  </g>`;
}

/* kolor i rozmiar gwiazdy wg typu widmowego (znany od SI 2-3) */
function starStyle(info) {
  const s = (info.stars && info.stars[0]) || (info.star_class_general && info.star_class_general[0]) || "";
  const t = String(s).trim();
  if (/neutron/i.test(t) || t === "NS") return { c: "var(--star-NS)", r: 1.6, cls: "ns-pulse" };
  if (/white dwarf/i.test(t)) return { c: "var(--star-WD)", r: 1.2, cls: "" };
  if (/red giant/i.test(t)) return { c: "var(--star-M)", r: 3.2, cls: "" };
  if (/brown dwarf/i.test(t)) return { c: "#a8794f", r: 1.2, cls: "" };
  const m = t.match(/^([OBAFGKM])/i);
  if (!m) return { c: "var(--star-X)", r: 1.8, cls: "" };
  const T_ = m[1].toUpperCase();
  const R_ = { O: 3.0, B: 2.8, A: 2.5, F: 2.3, G: 2.2, K: 2.0, M: 1.7 }[T_];
  return { c: `var(--star-${"OB".includes(T_) ? "B" : T_})`, r: R_, cls: "" };
}

const SVG_DEFS = `<defs>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="1.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="glow-big" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur stdDeviation="2.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="glow-s" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation=".8" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <radialGradient id="neb1" cx="35%" cy="30%" r="55%">
    <stop offset="0%" stop-color="#16223f" stop-opacity=".7"/>
    <stop offset="100%" stop-color="#16223f" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="neb2" cx="72%" cy="70%" r="50%">
    <stop offset="0%" stop-color="#101b33" stop-opacity=".8"/>
    <stop offset="100%" stop-color="#101b33" stop-opacity="0"/>
  </radialGradient>
</defs>`;

function hexInfoCard(secName, hex, info) {
  const title = `${secName} ${hex}` + (info?.name ? ` — <span class="sys-name">${info.name}</span>` : "");
  const chips = [`<span class="chip chip-si">SI ${info?.si ?? 0}</span>`];
  if (info?.stars?.length) chips.push(`<span class="chip">${info.stars.map(decodeStar).join(", ")}</span>`);
  else if (info?.star_presence) chips.push(`<span class="chip chip-dim">${T.tipStar}</span>`);
  if (info?.gas_giant === true) chips.push(`<span class="chip chip-ok">${ico("gg")} ${T.tipGG}</span>`);
  if (info?.uwp) chips.push(`<span class="chip"><code>${info.uwp}</code></span>`);
  if (info?.zone === "A") chips.push(`<span class="chip chip-warn">${ICO_WARN} AMBER</span>`);
  if (info?.zone === "R") chips.push(`<span class="chip chip-bad">${ICO_BAD} RED</span>`);
  return `<div class="tip-title">${title}</div><div class="tip-chips">${chips.join("")}</div>`;
}

function applyView() {
  const v = VIEW || BASE_VB;
  if (!v) return;
  const svg = $("hexmap");
  svg.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
  /* numery hexów widoczne dopiero przy zbliżeniu */
  svg.classList.toggle("zoomed", BASE_VB && v.w < BASE_VB.w / 2.2);
  /* glify większe przy oddaleniu (czytelność z drugiego końca stołu) */
  const k = BASE_VB ? Math.min(1.8, Math.max(1, 1.8 * v.w / BASE_VB.w)) : 1;
  svg.style.setProperty("--gs", k.toFixed(2));
}

async function renderMap() {
  const svg = $("hexmap");
  const nb = CUR_MAP.neighbors || {};
  const nbMaps = {};
  for (const dir of ["left", "right", "up", "down"])
    if (nb[dir]) nbMaps[dir] = await getSector(nb[dir]);

  const minX = -PREV, maxX = 33 + PREV, minY = -PREV, maxY = 41 + PREV;
  const [x0] = hexCenter(minX, 1), [x1] = hexCenter(maxX, 1);
  const y0 = (minY - 1) * H, y1 = maxY * H;
  BASE_VB = { x: x0 - R, y: y0, w: x1 - x0 + 3 * R, h: y1 - y0 };
  applyView();

  /* zasieg skoku: hexy w promieniu min(J-4, paliwo) od statku */
  const shipSecObj = SECTORS.find((q) => q.name === STATE.position.sector);
  const shipW = shipSecObj ? worldXY(shipSecObj.x, shipSecObj.y, STATE.position.hex) : null;
  const rangePc = Math.min(4, Math.floor(STATE.fuel_tons / STATE.ship_constants.fuel_per_parsec));
  const secX0 = CUR_MAP.x, secY0 = CUR_MAP.y;
  const inRange = (relX, relY) => {
    if (!shipW || rangePc < 1) return false;
    const w = [secX0 * 32 + (relX - 1), secY0 * 40 + (relY - 1)];
    const d = distPc(shipW, w);
    return d >= 1 && d <= rangePc;
  };
  /* zasieg planowany od wybranego hexu (chipy J1-J4 na karcie) */
  let selRange = null;
  if (RANGE_SEL) {
    const rs = SECTORS.find((q) => q.name === RANGE_SEL.sector);
    if (rs) selRange = { w: worldXY(rs.x, rs.y, RANGE_SEL.hex), j: RANGE_SEL.j };
  }
  const inRangeSel = (relX, relY) => {
    if (!selRange) return false;
    const w = [secX0 * 32 + (relX - 1), secY0 * 40 + (relY - 1)];
    const d = distPc(selRange.w, w);
    return d >= 1 && d <= selRange.j;
  };

  let out = SVG_DEFS;
  /* atmosfera rysowana NAD wypelnieniami hexow (fill hexa jest kryjacy),
     ale pod glifami — trafia na poczatek `overlays` */
  let atmo = "";
  const bgX = -PREV * 1.5 * R - R, bgY = (-PREV - 1) * H;
  const bgW = (33 + 2 * PREV) * 1.5 * R + 2 * R, bgH = (42 + 2 * PREV) * H;
  atmo += `<rect class="neb" x="${bgX}" y="${bgY}" width="${bgW}" height="${bgH}" fill="url(#neb1)" pointer-events="none"/>`;
  atmo += `<rect class="neb" x="${bgX}" y="${bgY}" width="${bgW}" height="${bgH}" fill="url(#neb2)" pointer-events="none"/>`;

  /* starfield: CZYSTA dekoracja — seed z nazwy sektora, zero wiedzy o systemach
     (fog-of-war nietkniety; w motywie paper ukrywany w CSS) */
  let sfSeed = 2166136261;
  for (const ch of CUR_SECTOR) sfSeed = Math.imul(sfSeed ^ ch.charCodeAt(0), 16777619) >>> 0;
  const sfRnd = () => {
    sfSeed = (sfSeed + 0x6D2B79F5) >>> 0;
    let t = sfSeed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  let sf = "";
  for (let i = 0; i < 150; i++) {
    const x = bgX + sfRnd() * bgW, y = bgY + sfRnd() * bgH;
    const r = 0.1 + sfRnd() * 0.32, o = 0.12 + sfRnd() * 0.45;
    sf += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(2)}" opacity="${o.toFixed(2)}"/>`;
  }
  atmo += `<g class="starfield" fill="var(--map-star)" pointer-events="none">${sf}</g>`;

  /* siatka subsektorow 4x4 z literami A-P (jak na kartach sektora) */
  const gx0 = hexCenter(1, 1)[0] - R, gx1 = hexCenter(32, 1)[0] + R;
  const gy0 = -H / 2, gy1 = 40 * H;
  let grid = "";
  for (const c of [8, 16, 24]) {
    const x = (c - 0.5) * 1.5 * R;
    grid += `<line class="subsec-line" x1="${x.toFixed(1)}" y1="${gy0.toFixed(1)}" x2="${x.toFixed(1)}" y2="${gy1.toFixed(1)}"/>`;
  }
  for (const rw of [10, 20, 30]) {
    const y = (rw - 0.25) * H;
    grid += `<line class="subsec-line" x1="${gx0.toFixed(1)}" y1="${y.toFixed(1)}" x2="${gx1.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
  }
  for (let sy = 0; sy < 4; sy++)
    for (let sx = 0; sx < 4; sx++) {
      const letter = String.fromCharCode(65 + sy * 4 + sx);
      const [lx] = hexCenter(sx * 8 + 1, 1);
      grid += `<text class="subsec-label" x="${(lx - R * 0.4).toFixed(1)}" y="${((sy * 10 + 0.35) * H).toFixed(1)}">${letter}</text>`;
    }
  atmo += `<g pointer-events="none">${grid}</g>`;

  let labels = "", overlays = atmo;
  const drawHex = (hx, hy, info, opts) => {
    const [cx, cy] = hexCenter(hx, hy);
    const si = info?.si ?? 0;
    const cls = `hex si-${Math.min(si, 12)}${opts.preview ? " preview" : ""}` +
      `${opts.selected ? " selected" : ""}${!opts.preview && inRange(hx, hy) ? " in-range" : ""}` +
      `${inRangeSel(hx, hy) ? " in-range-sel" : ""}`;
    out += `<polygon class="${cls}" data-sec="${opts.sec}" data-hex="${opts.hex}" points="${hexPoints(cx, cy)}"/>`;
    if (!opts.preview)
      labels += `<text class="hex-label" x="${cx}" y="${cy - H / 2 + 3.6}" text-anchor="middle">${opts.hex}</text>`;
    if (BOOKMARKS.some((m) => m.sector === opts.sec && m.hex === opts.hex))
      labels += `<text class="pin-mark" x="${cx + R * 0.28}" y="${cy - H / 2 + 4.6}">★</text>`;
    if (!info) return;
    if (info.star_presence && info.empty !== true) {
      /* progresja odkrywania: typ gwiazdy nieznany (SI<3) = anonimowa kropka,
         znany = barwna gwiazda; kanon = duzy glow + nazwa */
      const typeKnown = (info.stars && info.stars.length) || info.star_class_general;
      if (!typeKnown && !info.canon && si < 3) {
        overlays += `<circle class="star-dot" cx="${cx}" cy="${cy}" r="${si >= 2 ? 1.5 : 1.1}" fill="var(--star-X)" opacity="${si >= 2 ? ".75" : ".5"}"/>`;
      } else {
        const st = starStyle(info);
        const glow = info.canon ? "glow-big" : "glow";
        overlays += `<circle class="star-dot ${st.cls}" cx="${cx}" cy="${cy}" r="${info.canon ? Math.max(st.r, 2.6) : st.r}" fill="${st.c}" filter="url(#${glow})"/>`;
      }
      if (info.canon && info.name && !opts.preview)
        labels += `<text class="world-name" x="${cx}" y="${cy + H / 2 + 5.5}">${info.name.toUpperCase()}</text>`;
      /* SI 6+: znamy pelna liste cial — pipsy pod gwiazda */
      const nb = info.n_bodies ?? (info.bodies_detail ? info.bodies_detail.length : 0);
      if (nb && !opts.preview) {
        const n = Math.min(nb, 5);
        for (let i = 0; i < n; i++)
          overlays += `<circle class="body-pip" cx="${(cx + (i - (n - 1) / 2) * 1.7).toFixed(1)}" cy="${(cy + 4.6).toFixed(1)}" r=".55" fill="var(--g-400)"/>`;
      }
    }
    if (info.gas_giant) {
      /* mini-planetka z pierscieniem */
      overlays += `<g class="gg-icon" transform="translate(${cx + 4.6},${cy - 4.2})">
        <circle r="1.3" fill="#5fa8e8"/>
        <ellipse rx="2.4" ry=".8" fill="none" stroke="#8fc4f0" stroke-width=".35" transform="rotate(-24)"/></g>`;
    }
    if (info.zone === "A" || info.zone === "R") {
      const zc = info.zone === "A" ? "var(--warn)" : "var(--bad)";
      overlays += `<circle class="zone-ring" cx="${cx}" cy="${cy}" r="${R * 0.8}" fill="none" stroke="${zc}" stroke-width=".6" stroke-dasharray="2 1.6" opacity=".8"/>`;
    }
  };

  for (let hx = 1; hx <= 32; hx++)
    for (let hy = 1; hy <= 40; hy++) {
      const hex = String(hx).padStart(2, "0") + String(hy).padStart(2, "0");
      drawHex(hx, hy, CUR_MAP.hexes[hex],
        { sec: CUR_SECTOR, hex, preview: false, selected: SELECTED === hex });
    }
  const strips = [
    ["left", (c, r) => [32 - PREV + c, r], (c, r) => [c - PREV, r]],
    ["right", (c, r) => [c, r], (c, r) => [32 + c, r]],
    ["up", (c, r) => [c, 40 - PREV + r], (c, r) => [c, r - PREV]],
    ["down", (c, r) => [c, r], (c, r) => [c, 40 + r]],
  ];
  for (const [dir, src, dst] of strips) {
    const m = nbMaps[dir];
    if (!m) continue;
    const cols = dir === "left" || dir === "right" ? PREV : 32;
    const rows = dir === "left" || dir === "right" ? 40 : PREV;
    for (let c = 1; c <= cols; c++)
      for (let r = 1; r <= rows; r++) {
        const [sx, sy] = src(c, r);
        const hex = String(sx).padStart(2, "0") + String(sy).padStart(2, "0");
        const [dx, dy] = dst(c, r);
        drawHex(dx, dy, m.hexes[hex], { sec: m.name, hex, preview: true });
      }
  }
  /* trasa statku */
  const secX = CUR_MAP.x, secY = CUR_MAP.y;
  const trail = (STATE.trail || []).map((t) => {
    const s = SECTORS.find((q) => q.name === t.sector);
    if (!s) return null;
    const [wx, wy] = worldXY(s.x, s.y, t.hex);
    const relX = wx - secX * 32 + 1, relY = wy - secY * 40 + 1;
    if (relX < minX || relX > maxX || relY < minY || relY > maxY) return null;
    return hexCenter(relX, relY);
  });
  /* trasa: segmenty coraz jasniejsze ku terazniejszosci, z animowanym dashem */
  const pts = trail;
  const nSeg = pts.length - 1;
  for (let i = 0; i < nSeg; i++) {
    if (!pts[i] || !pts[i + 1]) continue;
    const op = 0.25 + 0.6 * ((i + 1) / nSeg);
    overlays += `<line class="trail-seg" x1="${pts[i][0]}" y1="${pts[i][1]}" x2="${pts[i + 1][0]}" y2="${pts[i + 1][1]}" stroke-width="${0.7 + 0.5 * ((i + 1) / nSeg)}" opacity="${op.toFixed(2)}"/>`;
  }
  if (STATE.position) {
    const s = SECTORS.find((q) => q.name === STATE.position.sector);
    if (s) {
      const [wx, wy] = worldXY(s.x, s.y, STATE.position.hex);
      const relX = wx - secX * 32 + 1, relY = wy - secY * 40 + 1;
      if (relX >= minX && relX <= maxX && relY >= minY && relY <= maxY) {
        const [cx, cy] = hexCenter(relX, relY);
        /* dziob w kierunku ostatniego skoku */
        let ang = 0;
        const prev = [...pts].reverse().find((p, i) => i > 0 && p);
        if (prev) ang = (Math.atan2(cy - prev[1], cx - prev[0]) * 180) / Math.PI + 90;
        overlays += shipGlyph(cx, cy, ang);
      }
    }
  }
  svg.innerHTML = out + overlays + labels;

  const tip = $("tooltip");
  svg.querySelectorAll(".hex").forEach((el) => {
    el.addEventListener("click", async () => {
      if (dragMoved) return;   // to był pan, nie klik
      if (el.dataset.sec !== CUR_SECTOR) {
        SELECTED = el.dataset.hex;
        await loadSector(el.dataset.sec);
        selectHex(el.dataset.hex);
      } else selectHex(el.dataset.hex);
    });
    el.addEventListener("mousemove", async (ev) => {
      const sec = el.dataset.sec, hex = el.dataset.hex;
      const m = sec === CUR_SECTOR ? CUR_MAP : await getSector(sec);
      tip.innerHTML = hexInfoCard(sec, hex, m.hexes[hex] || { si: 0 });
      tip.style.left = ev.clientX + 14 + "px";
      tip.style.top = ev.clientY + 10 + "px";
      tip.classList.remove("hidden");
    });
    el.addEventListener("mouseleave", () => tip.classList.add("hidden"));
  });
}

/* ------ zoom (scroll) + pan (przeciąganie) + dblclick reset ------ */
let dragMoved = false;
(function initZoomPan() {
  const svg = $("hexmap");
  const clientToMap = (ev) => {
    const r = svg.getBoundingClientRect();
    const v = VIEW || BASE_VB;
    /* preserveAspectRatio=meet: mapowanie przez wspólną skalę i offset */
    const scale = Math.min(r.width / v.w, r.height / v.h);
    const ox = (r.width - v.w * scale) / 2, oy = (r.height - v.h * scale) / 2;
    return [v.x + (ev.clientX - r.left - ox) / scale,
            v.y + (ev.clientY - r.top - oy) / scale];
  };
  svg.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    if (!BASE_VB) return;
    const v = { ...(VIEW || BASE_VB) };
    const [mx, my] = clientToMap(ev);
    const f = ev.deltaY > 0 ? 1.18 : 1 / 1.18;
    let w = v.w * f, h = v.h * f;
    const maxW = BASE_VB.w, minW = BASE_VB.w / 10;
    if (w > maxW) { VIEW = null; applyView(); return; }
    if (w < minW) { w = minW; h = BASE_VB.h / 10; }
    VIEW = { x: mx - (mx - v.x) * (w / v.w), y: my - (my - v.y) * (h / v.h), w, h };
    applyView();
  }, { passive: false });
  let dragging = false, start = null, startView = null;
  svg.addEventListener("pointerdown", (ev) => {
    dragging = true; dragMoved = false;
    start = [ev.clientX, ev.clientY];
    startView = { ...(VIEW || BASE_VB) };
    /* UWAGA: bez setPointerCapture na starcie — przechwycenie wskaznika
       retargetuje zdarzenie click na <svg> i klik w hex nigdy nie dociera
       do poligonu (panel systemu przestaje sie zmieniac). Capture zakladamy
       dopiero gdy faktycznie zaczyna sie przeciaganie. */
  });
  svg.addEventListener("pointermove", (ev) => {
    if (!dragging || !startView) return;
    const dx = ev.clientX - start[0], dy = ev.clientY - start[1];
    if (!dragMoved && Math.abs(dx) + Math.abs(dy) > 5) {
      dragMoved = true;
      try { svg.setPointerCapture(ev.pointerId); } catch { /* ignore */ }
    }
    if (!dragMoved) return;
    const r = svg.getBoundingClientRect();
    const scale = Math.min(r.width / startView.w, r.height / startView.h);
    VIEW = { ...startView, x: startView.x - dx / scale, y: startView.y - dy / scale };
    applyView();
  });
  svg.addEventListener("pointerup", () => { dragging = false; setTimeout(() => { dragMoved = false; }, 50); });
  /* dwuklik: przełącz podgląd całego sektora <-> widok wypełniający ekran */
  svg.addEventListener("dblclick", () => {
    const def = defaultView();
    const showingAll = !VIEW || (def && Math.abs(VIEW.w - BASE_VB.w) < 1 && Math.abs(VIEW.h - BASE_VB.h) < 1);
    VIEW = showingAll ? def : { ...BASE_VB };
    applyView();
  });
})();

function renderArrows() {
  const nb = CUR_MAP.neighbors || {};
  for (const dir of ["left", "right", "up", "down"]) {
    const btn = $(`nav-${dir}`);
    btn.disabled = !nb[dir];
    btn.title = nb[dir] ? `→ ${nb[dir]}` : T.noSector;
    btn.querySelector(".nav-name").textContent = nb[dir] || "";
    btn.onclick = nb[dir] ? () => { SELECTED = null; VIEW = null; loadSector(nb[dir]); } : null;
  }
}

/* ping skanu na hexie (sprzatany przez re-render mapy lub catch w run()) */
function showScanPing(hex) {
  document.getElementById("scan-ping-g")?.remove();
  const svg = $("hexmap");
  const [cx, cy] = hexCenter(parseInt(hex.slice(0, 2), 10), parseInt(hex.slice(2), 10));
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.id = "scan-ping-g";
  g.innerHTML = `<circle class="scan-ping" cx="${cx}" cy="${cy}" r="2"/>` +
    `<circle class="scan-ping" cx="${cx}" cy="${cy}" r="2" style="animation-delay:.55s"/>`;
  svg.appendChild(g);
}

/* ===================== HISTORIA RZUTÓW / PINY =========================== */

function recordRoll(out) {
  if (!out) return;
  const html = fmtCheck(out.check) + (out._msg || "");
  if (!html) return;
  ROLLS.unshift({ when: out.date_imperial || STATE?.date_imperial || "", html });
  if (ROLLS.length > 20) ROLLS.pop();
  if (!$("rolls-panel").classList.contains("hidden")) renderRolls();
}
function renderRolls() {
  $("rolls-list").innerHTML = ROLLS.length
    ? ROLLS.map((r) => `<div class="roll-row"><div class="roll-when">${r.when}</div>${r.html}</div>`).join("")
    : `<div class="dim">${T.rollsEmpty}</div>`;
}
$("btn-rolls").addEventListener("click", () => {
  const p = $("rolls-panel");
  p.classList.toggle("hidden");
  if (!p.classList.contains("hidden")) renderRolls();
});

async function loadBookmarks() {
  BOOKMARKS = await api("/api/bookmarks");
  const sel = $("pin-select");
  sel.classList.toggle("hidden", !BOOKMARKS.length);
  sel.innerHTML = `<option value="">${T.pinsPh}</option>` +
    BOOKMARKS.map((m, i) =>
      `<option value="${i}">★ ${m.sector} ${m.hex}${m.label ? " — " + m.label : ""}</option>`).join("");
}
$("pin-select").addEventListener("change", async (e) => {
  const m = BOOKMARKS[parseInt(e.target.value, 10)];
  e.target.value = "";
  if (!m) return;
  SELECTED = m.hex;
  VIEW = null;
  await loadSector(m.sector);
  selectHex(m.hex);
});

/* ============================== TOPBAR =================================== */

function bar(pct) {
  const cls = pct < 15 ? "crit" : pct < 40 ? "low" : "";
  return `<span class="bar ${cls}"><i style="width:${Math.max(2, pct)}%"></i></span>`;
}
function renderTopbar() {
  const C = STATE.ship_constants;
  $("tb-date").innerHTML = `${ico("cal")} ${STATE.date_imperial} (${T.missionDay(STATE.mission_day)})`;
  $("tb-pos").innerHTML = `${ico("pos")} ${STATE.position.sector} ${STATE.position.hex}`;
  const fp = (100 * STATE.fuel_tons) / C.fuel_tank_tons;
  const jumps = Math.floor(STATE.fuel_tons / C.fuel_per_parsec);
  $("tb-fuel").innerHTML = `${ico("fuel")} ${num(Math.round(STATE.fuel_tons))} t ${bar(fp)} <span class="dim">${jumps} ${T.pcWord}</span>`;
  const sp = (100 * STATE.supply_units) / C.supply_capacity;
  const days = Math.floor(STATE.supply_units / STATE.supply_budget_per_day);
  $("tb-su").innerHTML = `${ico("box")} SU ${bar(sp)} <span class="dim">${days} ${T.daysWord}</span>`;
  $("tb-crew").innerHTML = `${ico("crew")} ECEI ${STATE.cei + STATE.ceim} · MOR ${STATE.mor} · CFI ${STATE.cfi}`;
}

/* ==================== PANEL STATKU (współczynniki + akcje) =============== */

const STAT_FIELDS = ["cei", "ceim", "__ecei", "mor", "cfi",
  "dei.flight", "dei.engineering", "dei.operations", "dei.mission",
  "hull_pct", "fuel_tons", "supply_units", "supply_budget_per_day",
  "rare_materials", "rare_biologicals", "exotic_materials"];

function statValue(field) {
  if (field === "__ecei") return STATE.cei + STATE.ceim;
  if (field.includes(".")) { const [a, b] = field.split("."); return STATE[a][b]; }
  return STATE[field];
}

function renderStats() {
  $("stats-grid").innerHTML = STAT_FIELDS.map((f) => {
    const [label, tip] = T.STATS[f];
    const v = statValue(f);
    const editable = f !== "__ecei";
    return `<div class="stat${editable ? " editable" : ""}" data-field="${f}" title="${tip}">
      <span class="lbl">${label}</span><span class="val">${typeof v === "number" ? num(v) : v}</span></div>`;
  }).join("");
  $("stats-grid").querySelectorAll(".stat.editable").forEach((el) => {
    el.addEventListener("click", async () => {
      const f = el.dataset.field;
      const [label, tip] = T.STATS[f];
      const vals = await showDialog({
        title: T.editTitle(label),
        body: tip,
        fields: [
          { name: "value", label: T.editNew(statValue(f)), value: statValue(f) },
          { name: "reason", label: T.editReason, placeholder: T.editReasonPh },
        ],
        okLabel: T.save,
      });
      if (!vals || vals.value.trim() === "") return;
      try {
        await api("/api/state/edit", { method: "POST",
          body: JSON.stringify({ field: f, value: parseFloat(vals.value), reason: vals.reason || "" }) });
        await refreshState();
      } catch (e) { showInfo(T.errTitle, T.trNoteSrv(e.message)); }
    });
  });
  const rows = [];
  for (const [kind, key, ikona] of [["defect", "defects", ico("wrench")], ["breakdown", "breakdowns", ICO_WARN], ["failure", "failures", ICO_BAD]]) {
    for (const d of STATE[key] || [])
      rows.push(`<div class="defect-row">${ikona} <b>${d.system}</b>${d.note ? " — " + d.note : ""}
        <button class="mini" data-kind="${kind}" data-system="${d.system}">${T.repair}</button></div>`);
  }
  $("defects-box").innerHTML =
    `<div class="dim" style="margin-top:8px">${T.defectsHead} <button class="mini" id="defect-add">${T.addDefect}</button></div>` +
    (rows.join("") || `<div class="dim">${T.none}</div>`);
  $("defect-add").addEventListener("click", async () => {
    const vals = await showDialog({
      title: T.defectDlgTitle,
      body: T.defectDlgBody,
      fields: [
        { name: "system", label: T.defectSystem, placeholder: T.defectSystemPh },
        { name: "kind", label: T.defectKind, type: "select", options: ["defect", "breakdown", "failure"] },
        { name: "note", label: T.defectNote, placeholder: "" },
      ],
      okLabel: T.add,
    });
    if (!vals || !vals.system.trim()) return;
    await api("/api/state/defect", { method: "POST",
      body: JSON.stringify({ op: "add", kind: vals.kind, system: vals.system.trim(), note: vals.note || "" }) });
    await refreshState();
  });
  $("defects-box").querySelectorAll("button[data-kind]").forEach((b) =>
    b.addEventListener("click", async () => {
      await api("/api/state/defect", { method: "POST",
        body: JSON.stringify({ op: "remove", kind: b.dataset.kind, system: b.dataset.system }) });
      await refreshState();
    }));
  renderShipActions();
}

function renderShipActions() {
  $("ship-actions").innerHTML = `
    <button id="ship-wait">${T.waitBtn}</button>
    <button id="ship-note">${T.noteBtn}</button>`;
  $("ship-wait").addEventListener("click", async () => {
    try {
      const out = await api("/api/action/wait", { method: "POST", body: JSON.stringify({ days: 7 }) });
      $("ship-result").innerHTML = T.waitDone(out.date_imperial, num(out.supply_units)) +
        trNotes(out.notes).map((n) => `<div class="warn">${ICO_WARN} ${n}</div>`).join("");
      await refreshState();
      invalidateSector(CUR_SECTOR);
      CUR_MAP = await getSector(CUR_SECTOR);
      if (SELECTED) await selectHex(SELECTED);
    } catch (e) { $("ship-result").innerHTML = `<span class="warn">✖ ${T.trNoteSrv(e.message)}</span>`; }
  });
  $("ship-note").addEventListener("click", async () => {
    const vals = await showDialog({
      title: T.noteDlgTitle,
      fields: [
        { name: "text", label: T.noteText, placeholder: T.noteTextDlgPh },
        { name: "author", label: T.noteAuthor, placeholder: "" },
      ],
      okLabel: T.addNote,
    });
    if (!vals || !vals.text.trim()) return;
    await api("/api/journal", { method: "POST",
      body: JSON.stringify({ text: vals.text.trim(), author: vals.author || "" }) });
    $("ship-result").textContent = T.noteAdded;
  });
}

async function refreshState() {
  STATE = await api("/api/state");
  renderTopbar();
  renderStats();
}

/* ===================== PANEL SYSTEMU + AKCJE NAWIGACYJNE ================ */

async function selectHex(hex) {
  SELECTED = hex;
  await renderMap();
  /* skeleton na czas requestu — panel nie "znika" przy wolniejszym API */
  if (!$("hex-desc").innerHTML)
    $("hex-desc").innerHTML = `<div class="skel" style="width:78%"></div><div class="skel" style="width:52%"></div>`;
  const view = await api(`/api/system/${encodeURIComponent(CUR_SECTOR)}/${hex}`);
  const here = STATE.position.sector === CUR_SECTOR && STATE.position.hex === hex;
  const shipSec = SECTORS.find((s) => s.name === STATE.position.sector);
  const d = distPc(worldXY(shipSec.x, shipSec.y, STATE.position.hex),
                   worldXY(CUR_MAP.x, CUR_MAP.y, hex));
  const badge = here ? `<span class="here-badge">${T.hereBadge}</span>`
                     : `<span class="target-badge">${T.targetBadge(d)}</span>`;
  const pinned = BOOKMARKS.some((m) => m.sector === CUR_SECTOR && m.hex === hex);
  $("hex-title").innerHTML = `${CUR_SECTOR} ${hex}` +
    (view.name ? ` — <span class="sys-name">${view.name}</span>` : "") +
    `<button class="pin-btn${pinned ? " pinned" : ""}" id="pin-toggle" title="${pinned ? T.unpinTip : T.pinTip}">${pinned ? "★" : "☆"}</button> ` + badge;
  $("pin-toggle").addEventListener("click", async () => {
    await api("/api/bookmarks", { method: "POST",
      body: JSON.stringify({ sector: CUR_SECTOR, hex, label: view.name || "" }) });
    await loadBookmarks();
    selectHex(hex);
  });
  renderChips(view, hex);
  $("hex-desc").innerHTML = describeSystem(view).map((s) => `<p>${s}</p>`).join("");
  renderUwpGrid(view);
  renderBodies(view);
  $("hex-detail").innerHTML = "";
  renderActions(hex, view, here, d);
  /* retrigger animacji fade na zawartosci karty (motion, Etap 5.5) */
  const hp = $("hex-panel");
  hp.classList.remove("fade-swap");
  void hp.offsetWidth;
  hp.classList.add("fade-swap");
}

function renderActions(hex, view, here, d) {
  const el = $("hex-actions");
  const jumpsFuel = Math.floor(STATE.fuel_tons / STATE.ship_constants.fuel_per_parsec);
  const shipSec = SECTORS.find((s) => s.name === STATE.position.sector);
  const html = [];

  const btn = (id, label, rule, extra = "") =>
    `<button id="${id}" ${extra}>${label}<span class="rule">${rule}</span></button>`;

  let courseLeg = null;   // pierwszy odcinek kursu wieloskokowego
  if (!here) {
    if (d >= 1 && d <= 4) {
      const can = d <= jumpsFuel;
      html.push(btn("act-jump", T.jumpBtn(d), T.jumpRule(num(d * 6750), can),
        `class="primary" ${can ? "" : "disabled"}`));
    } else if (d > 4) {
      /* cel poza zasiegiem pojedynczego skoku J-4: zaproponuj kurs etapami */
      const legW = stepToward(worldXY(shipSec.x, shipSec.y, STATE.position.hex),
                              worldXY(CUR_MAP.x, CUR_MAP.y, hex),
                              Math.min(4, Math.max(1, jumpsFuel)));
      const leg = legW && worldToSectorHex(legW);
      const jumps = Math.ceil(d / 4);
      if (leg) {
        courseLeg = leg;
        const legD = Math.min(4, Math.max(1, jumpsFuel));
        const can = jumpsFuel >= 1;
        html.push(btn("act-course", T.courseBtn(d, jumps),
          T.courseRule(legD, leg.sector, leg.hex, can),
          `class="primary" ${can ? "" : "disabled"}`));
      } else {
        html.push(`<div class="hint">${T.outOfRange(d)}</div>`);
      }
    }
  }
  /* SKANY: pasywny/aktywny/pełny TYLKO w hexie statku (B3 p.72-74);
     z dystansu działa wyłącznie zdalny sweep (B3 p.72) */
  if (here) {
    html.push(`<div class="hint">${T.scanHintHere}</div>`);
    html.push(btn("act-passive", T.actPassive, T.actPassiveRule));
    html.push(btn("act-active", T.actActive, T.actActiveRule));
    html.push(btn("act-full", T.actFull, T.actFullRule));
    if (view.empty)
      html.push(btn("act-shortrange", T.actShortrange, T.actShortrangeRule));
    if (view.gas_giant) {
      html.push(btn("act-skim", T.actSkim, T.actSkimRule));
      html.push(btn("act-skim-safe", T.actSkimSafe, T.actSkimSafeRule));
    }
  } else {
    html.push(`<div class="hint">${T.scanHintRemote(d)}</div>`);
    html.push(btn("act-remote", T.actRemote, T.actRemoteRule));
  }
  el.innerHTML = html.join("");

  const run = async (fn) => {
    try {
      const out = await fn();
      const notes = trNotes(out.notes).map((n) => `<div class="warn">${ICO_WARN} ${n}</div>`).join("");
      $("action-result").innerHTML = fmtCheck(out.check) + (out._msg || "OK") + notes;
      recordRoll(out);
      await refreshState();
      invalidateSector(CUR_SECTOR);
      CUR_MAP = await getSector(CUR_SECTOR);
      if (SELECTED) await selectHex(SELECTED);
      else { await renderMap(); renderArrows(); }
    } catch (e) {
      document.getElementById("scan-ping-g")?.remove();
      $("action-result").innerHTML = `<span class="warn">✖ ${T.trNoteSrv(e.message)}</span>`;
    }
  };
  const scan = (mode) => run(async () => {
    /* "radar sweep": ping na hexie + minimalny czas, zeby skan byl WIDOCZNY */
    showScanPing(hex);
    const minWait = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 1100;
    const [out] = await Promise.all([
      api("/api/action/scan", { method: "POST",
        body: JSON.stringify({ sector: CUR_SECTOR, hex, mode }) }),
      sleep(minWait),
    ]);
    const roll = out.rolls?.si_gain != null ? T.scanGain(out.rolls.si_gain) : "";
    out._msg = `SI ${out.si_before} → ${out.si_after}${roll} · ${T.timeWord} ${out.time}` +
      (out.applied ? "" : T.noProgress(out.best_sweep ?? "?"));
    return out;
  });
  $("act-remote")?.addEventListener("click", () => scan("remote"));
  $("act-passive")?.addEventListener("click", () => scan("passive"));
  $("act-active")?.addEventListener("click", async () => {
    if (await showConfirm(T.activeConfirmTitle, T.activeConfirmBody, T.scanWord))
      scan("active");
  });
  $("act-full")?.addEventListener("click", () => scan("full"));
  $("act-course")?.addEventListener("click", async () => {
    if (!courseLeg) return;
    if (!(await showConfirm(T.courseConfirmTitle,
      T.courseConfirmBody(courseLeg.sector, courseLeg.hex), T.jumpWord))) return;
    run(async () => {
      const out = await api("/api/action/jump", { method: "POST",
        body: JSON.stringify({ sector: courseLeg.sector, hex: courseLeg.hex }) });
      const ov = $("jump-overlay");
      ov.classList.remove("play"); void ov.offsetWidth; ov.classList.add("play");
      setTimeout(() => ov.classList.remove("play"), 2300);
      out._msg = T.courseDone(out.plan.parsecs, courseLeg.sector, courseLeg.hex, out.date_imperial);
      if (courseLeg.sector !== CUR_SECTOR) { SELECTED = null; await loadSector(courseLeg.sector); }
      return out;
    });
  });
  $("act-jump")?.addEventListener("click", () => run(async () => {
    const out = await api("/api/action/jump", { method: "POST", body: JSON.stringify({ sector: CUR_SECTOR, hex }) });
    /* animacja przejścia przez jumpspace */
    const ov = $("jump-overlay");
    ov.classList.remove("play"); void ov.offsetWidth; ov.classList.add("play");
    setTimeout(() => ov.classList.remove("play"), 2300);
    out._msg = T.jumpDone(out.plan.parsecs, num(out.plan.fuel_required), out.date_imperial);
    return out;
  }));
  const skim = (mode) => run(async () => {
    const need = STATE.ship_constants.fuel_tank_tons - STATE.fuel_tons;
    const out = await api("/api/action/skim", { method: "POST", body: JSON.stringify({ tons: need, mode }) });
    out._msg = T.skimDone(out.plan.passes, num(out.plan.tons_skimmed), out.plan.processing_days);
    return out;
  });
  $("act-skim")?.addEventListener("click", () => skim("deep"));
  $("act-skim-safe")?.addEventListener("click", () => skim("safe"));
  $("act-shortrange")?.addEventListener("click", () => run(async () => {
    const out = await api("/api/action/shortrange", { method: "POST", body: JSON.stringify({}) });
    const found = out.objects.map((o) => o.desc || o.kind).join("; ") || T.srNothing;
    out._msg = T.srMsg(out.roll_total, out.nearest_star_pc, out.sweep_days, found);
    return out;
  }));
}

/* ============================== DZIENNIK ================================ */

async function showJournal() {
  $("main").classList.add("hidden");
  $("journal-screen").classList.remove("hidden");
  const rows = await api("/api/journal");
  $("journal-list").innerHTML = rows.slice().reverse().map((r) =>
    `<div class="log-row ${r.kind}"><span class="d">${r.date_imperial || ""}</span><span class="k">${T.KIND[r.kind] || r.kind}</span>${r.text}${r.data?.author ? ` <span class="dim">— ${r.data.author}</span>` : ""}</div>`
  ).join("");
}
$("btn-journal").addEventListener("click", showJournal);
$("journal-close").addEventListener("click", () => {
  $("journal-screen").classList.add("hidden");
  $("main").classList.remove("hidden");
});
$("note-add").addEventListener("click", async () => {
  const text = $("note-text").value.trim();
  if (!text) return;
  await api("/api/journal", { method: "POST",
    body: JSON.stringify({ text, author: $("note-author").value.trim() }) });
  $("note-text").value = "";
  showJournal();
});

/* =============================== START ================================== */

$("btn-undo").addEventListener("click", async () => {
  if (!(await showConfirm(T.undoConfirmTitle, T.undoConfirmBody, T.undoWord))) return;
  try {
    const out = await api("/api/undo", { method: "POST" });
    $("action-result").innerHTML = T.undoDone(out.undone);
    await refreshState();
    await loadSector(STATE.position.sector);
    selectHex(STATE.position.hex);
  } catch (e) { showInfo(T.errTitle, T.trNoteSrv(e.message)); }
});
$("sec-select").addEventListener("change", (e) => { SELECTED = null; VIEW = null; loadSector(e.target.value); });
$("btn-home").addEventListener("click", async () => {
  VIEW = null;
  await loadSector(STATE.position.sector);
  selectHex(STATE.position.hex);
});
$("init-go").addEventListener("click", async () => {
  const body = { start: $("init-start").value, date_imperial: $("init-date").value.trim() };
  const mor = $("init-mor").value.trim();
  if (mor) body.mor_roll = parseInt(mor, 10);
  await api("/api/init", { method: "POST", body: JSON.stringify(body) });
  location.reload();
});

(async function boot() {
  applyStaticI18n();
  SECTORS = await api("/api/sectors");
  const sel = $("sec-select");
  SECTORS.slice().sort((a, b) => a.name.localeCompare(b.name)).forEach((s) => {
    const o = document.createElement("option");
    o.value = s.name;
    o.textContent = `${s.name} (${s.x},${s.y})${s.worlds_source === "generate" ? " ∅" : ""}`;
    sel.appendChild(o);
  });
  try {
    STATE = await api("/api/state");
  } catch {
    $("init-screen").classList.remove("hidden");
    return;
  }
  $("main").classList.remove("hidden");
  renderTopbar();
  renderStats();
  await loadBookmarks();
  await loadSector(STATE.position.sector);
  selectHex(STATE.position.hex);
})();
