let currentLanguage = "en";

const uiText = {
  en: {
    pageTitle: "Capture WebUI",
    appTitle: "Capture WebUI",
    recordingTitle: "Recording",
    languageLabel: "Language",
    englishOption: "English",
    germanOption: "Deutsch",
    customOption: "Custom...",
    idle: "Idle",
    live: "Live",
    noActiveRecording: "No active recording",
    sessionNameLabel: "Session Name",
    driverLabel: "Driver",
    channelsLabel: "Channels",
    samplerateLabel: "Samplerate",
    durationLabel: "Duration (seconds)",
    endCommentLabel: "Optional end comment",
    displayValueLabel: "Display value",
    startRecording: "Recording Start",
    stopRecording: "Recording Stop",
    testAnalyzer: "Test analyzer",
    shutdown: "Shutdown",
    reloadRecordings: "Reload recordings",
    clearLog: "Clear log",
    sigrokCommandLog: "Sigrok Command Log",
    simulateWithoutHardware: "Simulate without hardware",
    mobileAnnotationTitle: "Mobile Annotation",
    mobileAnnotationHint:
      "Flow: Start recording, tap only the real panel buttons, then stop recording. Optional: add one end comment.",
    panelButtonsTitle: "Panel Buttons",
    panelButtonsHint:
      "No manual annotation fields. Taps are saved automatically for the active recording.",
    mainControlFunctions: "Main Control Functions",
    displayAndSymbolsTitle: "Display and Symbols",
    displayAndSymbolsHint:
      "Tap symbols directly in the center display. Add value or cycle number only if needed, then save.",
    displaySymbolsHint:
      "Tap symbols directly in the center display. Add value or cycle number only if needed, then save.",
    simulateLabelText: "Simulate without hardware",
    cycleNumberLabel: "Filter cycle number (top 8 symbol)",
    resetSymbols: "Reset symbols",
    noSymbolsActive: "No symbols active",
    lcdScreenFunctions: "LCD Screen Functions",
    saveDisplayState: "Save display state",
    recordingsTitle: "Recordings",
    deleteAll: "Delete all",
    tableId: "ID",
    tableName: "Name",
    tableStatus: "Status",
    tableMeasuredAt: "Measured At",
    tableDuration: "Duration",
    tableSamplerate: "Samplerate",
    tableChannels: "Channels",
    tableAnnotations: "Annotations",
    tableActions: "Actions",
    driverCustomPlaceholder: "custom driver id",
    displayValuePlaceholder: "e.g. 29.9C or 12:45",
    cycleNumberPlaceholder: "e.g. 1",
    endCommentPlaceholder: "e.g. unusual panel behavior",
    exportJson: "Export JSON",
    downloadSr: "Download .sr",
    delete: "Delete",
    save: "Save",
    annotations: "Annotations:",
    none: "none",
    notAvailable: "Not available",
    noSequenceToCopy: "No sequence to copy",
    sequenceCopied: "Sequence copied",
    noStepsYet: "No steps yet",
    noActiveRecordingError: "No active recording",
    selectAtLeastOneChannel: "Select at least one channel",
    startARecordingFirst: "Start a recording first",
    deleteAllRecordingsQuestion: "Delete all recordings?",
    shutdownConfirm: "Shutdown this host now?",
    recordingNameLabel: "Name",
    commentLabel: "Comment",
    listRefreshed: "List refreshed",
    shutdownRequested: "Shutdown requested",
    sequenceCleared: "Sequence cleared",
    recordingStarted: (id) => `Recording ${id} started`,
    recordingStopped: (id) => `Recording ${id} stopped`,
    recordingDeleted: (id) => `Recording ${id} deleted`,
    recordingSaved: (id) => `Recording ${id} saved`,
    analyzerTestPassed: (driver) => `Analyzer test passed for ${driver}`,
    analyzerTestFailed: (driver) => `Analyzer test failed for ${driver}`,
    analyzerTestOk: (driver) => `Analyzer test ok for ${driver}`,
    activeStatus: (id, seconds) => `ID ${id} running for ${seconds}s`,
    inactiveStatus: "No active recording",
    waitingForFirstCaptureCommand: "PS> waiting for first capture command...",
    noSignalAnalyzerHardware: (driver) => `No signal analyzer hardware detected for driver ${driver}`,
    signalAnalyzerFirmwareFailure:
      "Signal analyzer detected, but firmware upload failed. Check the probe firmware, USB connection, and device support for the selected driver.",
    recordingAlreadyActive: "Recording already active",
    signalAnalyzerTestFailed: "Signal analyzer test failed",
    recordingModeNoCommand: "simulation mode enabled (no sigrok-cli command executed)",
    noCurrentRecording: "No active recording",
    deleteRecordingQuestion: (id) => `Delete recording ${id}?`,
  },
  de: {
    pageTitle: "Capture WebUI",
    appTitle: "Capture WebUI",
    recordingTitle: "Aufnahme",
    languageLabel: "Sprache",
    englishOption: "Englisch",
    germanOption: "Deutsch",
    customOption: "Benutzerdefiniert...",
    idle: "Leerlauf",
    live: "Live",
    noActiveRecording: "Keine aktive Aufnahme",
    sessionNameLabel: "Sitzungsname",
    driverLabel: "Treiber",
    channelsLabel: "Kanäle",
    samplerateLabel: "Samplerate",
    durationLabel: "Dauer (Sekunden)",
    endCommentLabel: "Optionaler Endkommentar",
    displayValueLabel: "Displaywert",
    startRecording: "Aufnahme starten",
    stopRecording: "Aufnahme stoppen",
    testAnalyzer: "Analyzer testen",
    shutdown: "Herunterfahren",
    reloadRecordings: "Aufnahmen neu laden",
    clearLog: "Log leeren",
    sigrokCommandLog: "Sigrok-Befehlsprotokoll",
    simulateWithoutHardware: "Ohne Hardware simulieren",
    mobileAnnotationTitle: "Mobile Erfassung",
    mobileAnnotationHint:
      "Ablauf: Aufnahme starten, nur die echten Panel-Tasten antippen und danach die Aufnahme stoppen. Optional: einen Endkommentar hinzufügen.",
    panelButtonsTitle: "Panel-Tasten",
    panelButtonsHint:
      "Keine manuellen Eingabefelder. Taps werden automatisch für die aktive Aufnahme gespeichert.",
    mainControlFunctions: "Hauptfunktionen",
    displayAndSymbolsTitle: "Display und Symbole",
    displayAndSymbolsHint:
      "Symbole direkt im mittleren Display antippen. Nur Wert oder Zyklusnummer eintragen, wenn nötig, dann speichern.",
    displaySymbolsHint:
      "Symbole direkt im mittleren Display antippen. Nur Wert oder Zyklusnummer eintragen, wenn nötig, dann speichern.",
    simulateLabelText: "Ohne Hardware simulieren",
    cycleNumberLabel: "Filterzyklus-Nummer (oberes 8-Symbol)",
    resetSymbols: "Symbole zurücksetzen",
    noSymbolsActive: "Keine Symbole aktiv",
    lcdScreenFunctions: "LCD-Symbolfunktionen",
    saveDisplayState: "Displayzustand speichern",
    recordingsTitle: "Aufnahmen",
    deleteAll: "Alle löschen",
    tableId: "ID",
    tableName: "Name",
    tableStatus: "Status",
    tableMeasuredAt: "Gemessen am",
    tableDuration: "Dauer",
    tableSamplerate: "Samplerate",
    tableChannels: "Kanäle",
    tableAnnotations: "Annotationen",
    tableActions: "Aktionen",
    driverCustomPlaceholder: "benutzerdefinierte Treiber-ID",
    displayValuePlaceholder: "z. B. 29.9C oder 12:45",
    cycleNumberPlaceholder: "z. B. 1",
    endCommentPlaceholder: "z. B. ungewöhnliches Panel-Verhalten",
    exportJson: "JSON exportieren",
    downloadSr: ".sr herunterladen",
    delete: "Löschen",
    save: "Speichern",
    annotations: "Annotationen:",
    none: "keine",
    notAvailable: "Nicht verfügbar",
    noSequenceToCopy: "Keine Sequenz zum Kopieren",
    sequenceCopied: "Sequenz kopiert",
    noStepsYet: "Noch keine Schritte",
    noActiveRecordingError: "Keine aktive Aufnahme",
    selectAtLeastOneChannel: "Mindestens einen Kanal auswählen",
    startARecordingFirst: "Zuerst eine Aufnahme starten",
    deleteAllRecordingsQuestion: "Alle Aufnahmen löschen?",
    shutdownConfirm: "Diesen Host jetzt herunterfahren?",
    recordingNameLabel: "Name",
    commentLabel: "Kommentar",
    listRefreshed: "Liste aktualisiert",
    shutdownRequested: "Herunterfahren angefordert",
    sequenceCleared: "Sequenz geleert",
    recordingStarted: (id) => `Aufnahme ${id} gestartet`,
    recordingStopped: (id) => `Aufnahme ${id} gestoppt`,
    recordingDeleted: (id) => `Aufnahme ${id} gelöscht`,
    recordingSaved: (id) => `Aufnahme ${id} gespeichert`,
    analyzerTestPassed: (driver) => `Analyzer-Test für ${driver} bestanden`,
    analyzerTestFailed: (driver) => `Analyzer-Test für ${driver} fehlgeschlagen`,
    analyzerTestOk: (driver) => `Analyzer-Test für ${driver} erfolgreich`,
    activeStatus: (id, seconds) => `ID ${id} läuft seit ${seconds}s`,
    inactiveStatus: "Keine aktive Aufnahme",
    waitingForFirstCaptureCommand: "PS> warte auf den ersten Capture-Befehl...",
    noSignalAnalyzerHardware: (driver) => `Kein Signal-Analyzer für den Treiber ${driver} gefunden`,
    signalAnalyzerFirmwareFailure:
      "Signal-Analyzer erkannt, aber Firmware-Upload fehlgeschlagen. Bitte Firmware, USB-Verbindung und Treiber-Unterstützung prüfen.",
    recordingAlreadyActive: "Aufnahme läuft bereits",
    signalAnalyzerTestFailed: "Signal-Analyzer-Test fehlgeschlagen",
    recordingModeNoCommand: "Simulationsmodus aktiv (kein sigrok-cli-Befehl ausgeführt)",
    noCurrentRecording: "Keine aktive Aufnahme",
    deleteRecordingQuestion: (id) => `Aufnahme ${id} löschen?`,
  },
};

const keyDocs = {
  en: {
    A: "Select Button: Scrolls the menu through filter cycle programming features. Manually activates the circulation pump when it is off for 1 hour.",
    B: "Cycle Button: Accesses filter cycle program mode and advances to the next cycle.",
    C: "Mode Button: Switches between Standard and Economy modes.",
    D: "Display Button: Displays the time of day and opens time setting and lock functions.",
    E: "Invert Button: Inverts the main 4-digit LCD display.",
    F: "Jets 2 Button: Controls jets pump 2 (and Maxxus/Aspen jets pump 3).",
    G: "Jets 1 Button: Controls jets pump 1.",
    H: "Blower Button: Controls the air blower.",
    I: "Light Mode Button: Selects one of 4 color modes for waterfall, footwell, and air control lights.",
    J: "Light Button: Turns waterfall, footwell, and air control lights on in unison. Press once for high intensity, a second time for medium, a third time for low, and a fourth time to turn off.",
    K: "Warmer and Cooler Buttons: Display and adjust the temperature setting and other programming features.",
  },
  de: {
    A: "Auswahl-Taste: Blättert durch die Funktionen der Filterzyklus-Programmierung. Aktiviert die Umwälzpumpe manuell, wenn sie 1 Stunde lang aus war.",
    B: "Zyklus-Taste: Öffnet den Filterzyklus-Programmmodus und springt zum nächsten Zyklus.",
    C: "Modus-Taste: Wechselt zwischen Standard- und Economy-Modus.",
    D: "Anzeige-Taste: Zeigt die Uhrzeit an und öffnet die Funktionen für Zeiteinstellung und Sperre.",
    E: "Umdrehen-Taste: Spiegelt die 4-stellige Hauptanzeige.",
    F: "Jets-2-Taste: Steuert Pumpe 2 (und bei Maxxus/Aspen Pumpe 3).",
    G: "Jets-1-Taste: Steuert Pumpe 1.",
    H: "Gebläse-Taste: Steuert das Luftgebläse.",
    I: "Lichtmodus-Taste: Wählt einen von 4 Farbmodi für Wasserfall-, Fußraum- und Lichtsteuerung.",
    J: "Licht-Taste: Schaltet Wasserfall-, Fußraum- und Lichtsteuerung gemeinsam ein. Einmal drücken für hohe Intensität, ein zweites Mal für mittel, ein drittes Mal für niedrig und ein viertes Mal zum Ausschalten.",
    K: "Wärmer- und Kühler-Tasten: Zeigen die Temperatureinstellung und andere Programmfunktionen an und passen sie an.",
  },
};

function ui(key, ...args) {
  const entry = uiText[currentLanguage]?.[key] ?? uiText.en[key];
  if (typeof entry === "function") {
    return entry(...args);
  }
  return entry || key;
}

function setText(node, key, ...args) {
  if (node) {
    node.textContent = ui(key, ...args);
  }
}

function setPlaceholder(node, key) {
  if (node) {
    node.placeholder = ui(key);
  }
}

function setOptionText(selectNode, index, key) {
  if (!selectNode || !selectNode.options || !selectNode.options[index]) {
    return;
  }
  selectNode.options[index].textContent = ui(key);
}

const panelButtonLayout = [
  {
    code: "A",
    cls: "hs-a",
    nameEn: "Select",
    nameDe: "Auswahl",
    icon: "/static/button-icons/original/selection.png",
  },
  {
    code: "B",
    cls: "hs-b",
    nameEn: "Cycle",
    nameDe: "Zyklus",
    icon: "/static/button-icons/original/cycle.png",
  },
  {
    code: "C",
    cls: "hs-c",
    nameEn: "Mode",
    nameDe: "Modus",
    icon: "/static/button-icons/original/mode.png",
  },
  {
    code: "D",
    cls: "hs-d",
    nameEn: "Display",
    nameDe: "Anzeige",
    icon: "/static/button-icons/original/display.png",
  },
  {
    code: "K",
    cls: "hs-k-warm",
    nameEn: "Warmer",
    nameDe: "Wärmer",
    icon: "/static/button-icons/original/warmer.png",
    direction: "warmer",
  },
  {
    code: "K",
    cls: "hs-k-cool",
    nameEn: "Cooler",
    nameDe: "Kühler",
    icon: "/static/button-icons/original/cooler.png",
    direction: "cooler",
  },
  {
    code: "J",
    cls: "hs-j",
    nameEn: "Light",
    nameDe: "Licht",
    icon: "/static/button-icons/original/light_on_off.png",
  },
  {
    code: "I",
    cls: "hs-i",
    nameEn: "Light mode",
    nameDe: "Lichtmodus",
    icon: "/static/button-icons/original/lighting_mode.png",
  },
  {
    code: "H",
    cls: "hs-h",
    nameEn: "Blower",
    nameDe: "Gebläse",
    icon: "/static/button-icons/original/fan.png",
  },
  {
    code: "G",
    cls: "hs-g",
    nameEn: "Jets 1",
    nameDe: "Jets 1",
    icon: "/static/button-icons/original/jet_pump_1.png",
  },
  {
    code: "F",
    cls: "hs-f",
    nameEn: "Jets 2",
    nameDe: "Jets 2",
    icon: "/static/button-icons/original/jet_pump_2.png",
  },
  {
    code: "E",
    cls: "hs-e",
    nameEn: "Invert",
    nameDe: "Anzeige umkehren",
    icon: "/static/button-icons/original/reverse_display.png",
  },
];

const displaySymbolLayout = [
  { key: "lock", labelEn: "Lock", labelDe: "Sperre", icon: "/static/display-icons/original/lock.png", x: 4.2, y: 6, w: 7.2 },
  { key: "heater", labelEn: "Heater", labelDe: "Heizung", icon: "/static/display-icons/original/heater.png", x: 12.5, y: 6.2, w: 7.2 },
  { key: "sanitizer", labelEn: "Sanitizer", labelDe: "Desinfektion", icon: "/static/display-icons/original/uv-cleaner.png", x: 20.9, y: 5.8, w: 7.8 },
  { key: "cycle_set", labelEn: "Filter Cycle Setting", labelDe: "Filterzyklus-Einstellung", icon: "/static/display-icons/original/filter-cycle-settings.png", x: 30.3, y: 6, w: 7.4 },
  {
    key: "cycle_num",
    labelEn: "Filter Cycle Number",
    labelDe: "Filterzyklus-Nummer",
    icon: "/static/display-icons/original/filter-cycle-number.png",
    x: 39,
    y: 6.2,
    w: 7.1,
    interactive: false,
  },
  { key: "clock", labelEn: "Start Time", labelDe: "Startzeit", icon: "/static/display-icons/original/filter-cycle-start-time.png", x: 47.6, y: 6.3, w: 7.2 },
  { key: "duration", labelEn: "Duration", labelDe: "Dauer", icon: "/static/display-icons/original/filter-cycle-duration.png", x: 56.3, y: 6.4, w: 7.2 },
  { key: "set_temp", labelEn: "Set Temperature", labelDe: "Solltemperatur", icon: "/static/display-icons/original/set-temperature.png", x: 4.6, y: 28.4, w: 7.2 },
  { key: "set_time", labelEn: "Set Time", labelDe: "Uhrzeit einstellen", icon: "/static/display-icons/original/set-time.png", x: 12.4, y: 28.6, w: 6.2 },
  { key: "filter", labelEn: "Filter Indicator", labelDe: "Filteranzeige", icon: "/static/display-icons/original/filter-indicator.png", x: 4.4, y: 45.4, w: 7.6 },
  { key: "am", label: "AM", icon: "/static/display-icons/original/AM.png", x: 81.2, y: 33.2, w: 7.2 },
  { key: "pm", label: "PM", icon: "/static/display-icons/original/PM.png", x: 81.2, y: 42.6, w: 7.2 },
  { key: "mode_standard", labelEn: "Standard", labelDe: "Standard", icon: "/static/display-icons/original/standard-mode.png", x: 78.8, y: 56.1, w: 16.2 },
  { key: "blower", labelEn: "Air Jet", labelDe: "Luftdüse", icon: "/static/display-icons/original/airjet.png", x: 24.2, y: 75.4, w: 10.4 },
  { key: "pump1", labelEn: "Water Jet 1", labelDe: "Wasserstrahl 1", icon: "/static/display-icons/original/waterjet1.png", x: 49.3, y: 75.2, w: 11.1 },
  { key: "pump2", labelEn: "Water Jet 2", labelDe: "Wasserstrahl 2", icon: "/static/display-icons/original/waterjet2.png", x: 65.5, y: 75.2, w: 11.1 },
  { key: "float_23", labelEn: "Point 2-3", labelDe: "Punkt 2-3", icon: "/static/display-icons/original/floating-point-digit-2-3.png", x: 45.5, y: 51.1, w: 1.9 },
  { key: "float_34", labelEn: "Point 3-4", labelDe: "Punkt 3-4", icon: "/static/display-icons/original/floating-point-digit-3-4.png", x: 57.2, y: 51.1, w: 1.9 },
  { key: "clock_delimiter", labelEn: "Clock Delimiter", labelDe: "Uhrzeit-Trenner", icon: "/static/display-icons/original/clock_delimiter.png", x: 51.1, y: 43.1, w: 1.7 },
];

const displaySymbolDescriptionsByLang = {
  en: [
  {
    key: "lock",
    title: "Lock",
    text: "Indicates panel, set temperature, or filter cycle programming is locked.",
  },
  {
    key: "heater",
    title: "Heat",
    text: "Indicates heater is on.",
  },
  {
    key: "sanitizer",
    title: "Sanitizer",
    text: "Indicates that the sanitizing system is on.",
  },
  {
    key: "cycle_set",
    title: "Adjust Filter Cycle",
    text: "Indicates filter cycle programming feature is accessed.",
  },
  {
    key: "cycle_num",
    title: "Filter Cycle Number",
    text: "Indicates which programmed filter cycle is running.",
  },
  {
    key: "cycle_running",
    title: "Filter Cycle",
    text: "Indicates programmed filter cycle is running.",
  },
  {
    key: "clock",
    title: "Filter Cycle Start Time",
    text: "Indicates filter cycle start time programming is accessed.",
  },
  {
    key: "duration",
    title: "Filter Cycle Duration",
    text: "Indicates filter cycle duration programming is accessed.",
  },
  {
    key: "set_temp",
    title: "Set Temperature",
    text: "Indicates current set temperature is displayed.",
  },
  {
    key: "set_time",
    title: "Set Time",
    text: "Indicates current time is displayed.",
  },
  {
    key: "filter",
    title: "Filter Annunciator",
    text: "Indicates filter cleaning and/or replacement is required.",
  },
  {
    key: "blower",
    title: "Blower",
    text: "Indicates blower is on.",
  },
  {
    key: "pump1",
    title: "Jets 1",
    text: "Indicates jets pump 1 is on.",
  },
  {
    key: "pump2",
    title: "Jets 2",
    text: "Indicates jets pump 2 is on (also shown for Maxxus/Aspen pump 3).",
  },
  {
    key: "mode_standard",
    title: "Mode",
    text: "Indicates selected filter mode. No icon means Economy mode is selected.",
  },
  ],
  de: [
    {
      key: "lock",
      title: "Sperre",
      text: "Zeigt an, dass Panel, Solltemperatur oder Filterzyklus-Programmierung gesperrt sind.",
    },
    {
      key: "heater",
      title: "Heizung",
      text: "Zeigt an, dass die Heizung aktiv ist.",
    },
    {
      key: "sanitizer",
      title: "Desinfektion",
      text: "Zeigt an, dass das Desinfektionssystem aktiv ist.",
    },
    {
      key: "cycle_set",
      title: "Filterzyklus anpassen",
      text: "Zeigt an, dass die Filterzyklus-Programmierung geöffnet ist.",
    },
    {
      key: "cycle_num",
      title: "Filterzyklus-Nummer",
      text: "Zeigt an, welcher programmierte Filterzyklus läuft.",
    },
    {
      key: "cycle_running",
      title: "Filterzyklus",
      text: "Zeigt an, dass der programmierte Filterzyklus läuft.",
    },
    {
      key: "clock",
      title: "Startzeit Filterzyklus",
      text: "Zeigt an, dass die Startzeit-Programmierung des Filterzyklus geöffnet ist.",
    },
    {
      key: "duration",
      title: "Dauer Filterzyklus",
      text: "Zeigt an, dass die Dauer-Programmierung des Filterzyklus geöffnet ist.",
    },
    {
      key: "set_temp",
      title: "Solltemperatur",
      text: "Zeigt die aktuell eingestellte Temperatur an.",
    },
    {
      key: "set_time",
      title: "Uhrzeit einstellen",
      text: "Zeigt an, dass die aktuelle Uhrzeit angezeigt wird.",
    },
    {
      key: "filter",
      title: "Filteranzeige",
      text: "Zeigt an, dass eine Filterreinigung und/oder ein Filterwechsel erforderlich ist.",
    },
    {
      key: "blower",
      title: "Gebläse",
      text: "Zeigt an, dass das Gebläse aktiv ist.",
    },
    {
      key: "pump1",
      title: "Jets 1",
      text: "Zeigt an, dass Pumpe 1 aktiv ist.",
    },
    {
      key: "pump2",
      title: "Jets 2",
      text: "Zeigt an, dass Pumpe 2 aktiv ist (bei Maxxus/Aspen auch Pumpe 3).",
    },
    {
      key: "mode_standard",
      title: "Modus",
      text: "Zeigt den gewählten Filtermodus an. Kein Symbol bedeutet Economy-Modus.",
    },
  ],
};

const state = {
  activeStatus: null,
  lastRecordingId: null,
  sequenceSteps: [],
  activeDisplaySymbols: new Set(),
  sigrokLogLines: [],
};

function renderSigrokLog() {
  const node = element("sigrokLog");
  if (!node) {
    return;
  }
  if (state.sigrokLogLines.length === 0) {
    node.textContent = ui("waitingForFirstCaptureCommand");
    return;
  }
  node.textContent = state.sigrokLogLines.join("\n");
}

function appendSigrokLog(line) {
  const stamp = new Date().toLocaleTimeString();
  state.sigrokLogLines.push(`[${stamp}] ${line}`);
  if (state.sigrokLogLines.length > 120) {
    state.sigrokLogLines = state.sigrokLogLines.slice(-120);
  }
  renderSigrokLog();
}

function clearSigrokLog() {
  state.sigrokLogLines = [];
  renderSigrokLog();
}

function localizedButtonName(item) {
  return currentLanguage === "de" ? item.nameDe || item.nameEn : item.nameEn;
}

function localizedKeyDoc(code) {
  return keyDocs[currentLanguage]?.[code] || keyDocs.en[code] || "";
}

function element(id) {
  return document.getElementById(id);
}

function setSyncInfo(ok, details = "") {
  const node = element("syncInfo");
  if (!node) {
    return;
  }
  const stamp = new Date().toLocaleTimeString();
  if (ok) {
    node.textContent = `Updated ${stamp}${details ? ` - ${details}` : ""}`;
    return;
  }
  node.textContent = `Refresh failed ${stamp}${details ? ` - ${details}` : ""}`;
}

function getSelectedChannels() {
  const group = element("channelsGroup");
  if (!group) {
    return "D4,D5,D6,D7";
  }
  const selected = Array.from(group.querySelectorAll("input[type=checkbox]:checked"))
    .map((node) => node.value)
    .filter((value) => Boolean(value));
  return selected.join(",");
}

function setSelectedChannels(channelsCsv) {
  const group = element("channelsGroup");
  if (!group) {
    return;
  }
  const wanted = new Set(
    String(channelsCsv || "")
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
  );
  for (const input of group.querySelectorAll("input[type=checkbox]")) {
    input.checked = wanted.has(input.value);
  }
}

function getSelectedDriver() {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select) {
    return "fx2lafw";
  }
  if (select.value === "__custom__") {
    const value = custom ? String(custom.value || "").trim() : "";
    if (!value) {
      throw new Error(
        currentLanguage === "de"
          ? "Bitte Custom-Driver eintragen"
          : "Please enter custom driver"
      );
    }
    return value;
  }
  return select.value;
}

function setSelectedDriver(driver) {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select || !custom) {
    return;
  }
  const value = String(driver || "").trim();
  const options = Array.from(select.options).map((opt) => opt.value);
  if (options.includes(value)) {
    select.value = value;
    custom.classList.add("hidden");
    custom.value = "";
    return;
  }
  select.value = "__custom__";
  custom.classList.remove("hidden");
  custom.value = value;
}

function updateDriverCustomVisibility() {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select || !custom) {
    return;
  }
  if (select.value === "__custom__") {
    custom.classList.remove("hidden");
  } else {
    custom.classList.add("hidden");
    custom.value = "";
  }
}

function showToast(message, isError = false) {
  const toast = element("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.background = isError ? "#7e1f33" : "#133e33";
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 2400);
}

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  return body;
}

function currentRecordingId() {
  const value = Number(element("recordingId").value || "0");
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(ui("startARecordingFirst"));
  }
  return value;
}

function updateSequencePreview() {
  const preview = element("sequencePreview");
  if (!preview) {
    return;
  }
  if (state.sequenceSteps.length === 0) {
    preview.textContent = ui("noStepsYet");
    return;
  }

  const lines = state.sequenceSteps.map((step, idx) => `${idx + 1}. ${step}`);
  preview.textContent = lines.join("\n");

  const compact = state.sequenceSteps.join(" > ");
  const sequenceInput = element("sequence");
  if (sequenceInput) {
    sequenceInput.value = compact;
  }
}

function appendStep(stepText) {
  state.sequenceSteps.push(stepText);
  updateSequencePreview();
}

function clearSequence() {
  state.sequenceSteps = [];
  updateSequencePreview();
}

async function copySequence() {
  const sequenceInput = element("sequence");
  if (!sequenceInput) {
    showToast(ui("notAvailable"), true);
    return;
  }
  const text = sequenceInput.value.trim();
  if (!text) {
    showToast(ui("noSequenceToCopy"), true);
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    showToast(ui("sequenceCopied"));
    return;
  }

  const tmp = document.createElement("textarea");
  tmp.value = text;
  document.body.appendChild(tmp);
  tmp.select();
  document.execCommand("copy");
  tmp.remove();
  showToast(ui("sequenceCopied"));
}

async function refreshStatus() {
  const status = await jsonFetch("/api/status");
  state.activeStatus = status;

  const badge = element("statusBadge");
  const text = element("statusText");

  if (!status.active) {
    badge.textContent = ui("idle");
    badge.className = "badge idle";
    text.textContent = ui("noActiveRecording");
    return;
  }

  state.lastRecordingId = status.recordingId;
  badge.textContent = ui("live");
  badge.className = "badge live";
  const seconds = (status.elapsedMs / 1000).toFixed(1);
  text.textContent = ui("activeStatus", status.recordingId, seconds);
}

async function refreshRecordings() {
  const data = await jsonFetch("/api/recordings?limit=60");
  const body = element("recordingsBody");
  body.innerHTML = "";

  const exportLabel = ui("exportJson");
  const downloadSrLabel = ui("downloadSr");
  const deleteLabel = ui("delete");
  const saveLabel = ui("save");

  function formatDuration(startIso, endIso, status) {
    if (!startIso) {
      return "-";
    }
    const start = Date.parse(startIso);
    if (!Number.isFinite(start)) {
      return "-";
    }
    const end = endIso ? Date.parse(endIso) : Date.now();
    if (!Number.isFinite(end)) {
      return "-";
    }
    const sec = Math.max(0, Math.round((end - start) / 1000));
    const mm = Math.floor(sec / 60);
    const ss = sec % 60;
    const text = `${mm}:${String(ss).padStart(2, "0")}`;
    if (!endIso && status === "recording") {
      return `${text}*`;
    }
    return text;
  }

  function formatMeasuredAt(startIso) {
    if (!startIso) {
      return "-";
    }
    const ts = Date.parse(startIso);
    if (!Number.isFinite(ts)) {
      return String(startIso);
    }
    return new Date(ts).toLocaleString();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  for (const item of data.items) {
    const duration = formatDuration(item.start_time, item.end_time, item.status);
    const measuredAt = formatMeasuredAt(item.start_time);
    const previewItems = Array.isArray(item.annotation_preview)
      ? item.annotation_preview
      : [];
    let preview = previewItems.join(" | ");
    const totalAnnotations = Number(item.annotation_count || 0);
    if (totalAnnotations > previewItems.length) {
      const missing = totalAnnotations - previewItems.length;
      preview = preview
        ? `${preview} | +${missing} more`
        : `+${missing} more`;
    }

    const trMain = document.createElement("tr");
    trMain.innerHTML = `
      <td>${item.id}</td>
      <td>${item.name}</td>
      <td>${item.status}</td>
      <td>${measuredAt}</td>
      <td>${duration}</td>
      <td>${item.samplerate}</td>
      <td>${item.channels}</td>
      <td>${item.annotation_count}</td>
      <td>
        <button class="btn" data-download-sr="${item.id}">${downloadSrLabel}</button>
        <button class="btn" data-export="${item.id}">${exportLabel}</button>
        <button class="btn" data-save="${item.id}">${saveLabel}</button>
        <button class="btn danger" data-delete="${item.id}">${deleteLabel}</button>
      </td>
    `;
    body.appendChild(trMain);

    const trDetails = document.createElement("tr");
    trDetails.className = "recording-details-row";
    trDetails.innerHTML = `
      <td colspan="9">
        <div class="recording-details-line">
          <span class="recording-preview-label">${ui("annotations")}</span>
          <span class="recording-preview-text">${preview || ui("none")}</span>
        </div>
        <div class="recording-edit-grid">
          <label>
            ${ui("recordingNameLabel")}
            <input data-edit-name="${item.id}" value="${escapeHtml(item.name)}" />
          </label>
          <label>
            ${ui("commentLabel")}
            <input data-edit-notes="${item.id}" value="${escapeHtml(item.notes || "")}" placeholder="optional" />
          </label>
        </div>
      </td>
    `;
    body.appendChild(trDetails);
  }

  setSyncInfo(true, `${data.items.length} items`);

  for (const btn of body.querySelectorAll("button[data-export]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.export);
      const exported = await jsonFetch(`/api/recordings/${id}/export`);
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `recording_${id}_annotations.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    });
  }

  for (const btn of body.querySelectorAll("button[data-download-sr]")) {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.downloadSr);
      const anchor = document.createElement("a");
      anchor.href = `/api/recordings/${id}/file`;
      anchor.download = `recording_${id}.sr`;
      anchor.click();
    });
  }

  for (const btn of body.querySelectorAll("button[data-delete]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.delete);
      const ok = window.confirm(
        ui("deleteRecordingQuestion", id)
      );
      if (!ok) {
        return;
      }

      try {
        await jsonFetch("/api/recordings/delete", {
          method: "POST",
          body: JSON.stringify({ recordingId: id }),
        });
        showToast(ui("recordingDeleted", id));
        await refreshRecordings();
        await refreshStatus();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  for (const btn of body.querySelectorAll("button[data-save]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.save);
      const nameInput = body.querySelector(`input[data-edit-name="${id}"]`);
      const notesInput = body.querySelector(`input[data-edit-notes="${id}"]`);
      const name = nameInput ? String(nameInput.value || "") : "";
      const notes = notesInput ? String(notesInput.value || "") : "";
      try {
        await jsonFetch("/api/recordings/update", {
          method: "POST",
          body: JSON.stringify({
            recordingId: id,
            name,
            notes,
          }),
        });
        showToast(ui("recordingSaved", id));
        await refreshRecordings();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }
}

async function startRecording() {
  const channels = getSelectedChannels();
  if (!channels) {
    throw new Error(ui("selectAtLeastOneChannel"));
  }

  const payload = {
    name: element("name").value,
    sequence: "auto-panel-flow",
    notes: "",
    samplerate: element("samplerate").value,
    channels,
    driver: getSelectedDriver(),
    durationSeconds: Number(element("durationSeconds").value || "20"),
    simulate: element("simulate").checked,
  };

  if (!payload.simulate) {
    appendSigrokLog(`PS> ${ui("recordingModeNoCommand")}`);
  }

  const result = await jsonFetch("/api/recordings/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (Array.isArray(result.command) && result.command.length > 0) {
    appendSigrokLog(`PS> ${result.command.join(" ")}`);
  } else if (payload.simulate) {
    appendSigrokLog("PS> simulation mode enabled (no sigrok-cli command executed)");
  }

  state.lastRecordingId = result.recordingId;
  showToast(ui("recordingStarted", result.recordingId));
  await refreshStatus();
  await refreshRecordings();
}

async function testSignalAnalyzer(driver = getSelectedDriver()) {
  const result = await jsonFetch("/api/analyzer/test", {
    method: "POST",
    body: JSON.stringify({ driver }),
  });

  appendSigrokLog(`PS> ${ui("analyzerTestOk", driver)}`);
  if (Array.isArray(result.command) && result.command.length > 0) {
    appendSigrokLog(`PS> ${result.command.join(" ")}`);
  }
  if (result.output) {
    appendSigrokLog(`PS> ${String(result.output).split("\n").join(" | ")}`);
  }
  showToast(ui("analyzerTestPassed", driver));
  return result;
}

async function requestSystemShutdown() {
  const result = await jsonFetch("/api/system/shutdown", {
    method: "POST",
    body: "{}",
  });
  if (Array.isArray(result.command) && result.command.length > 0) {
    appendSigrokLog(`PS> ${result.command.join(" ")}`);
  }
  appendSigrokLog(`PS> ${ui("shutdownRequested")}`);
  showToast(ui("shutdownRequested"));
}

async function stopRecording() {
  const result = await jsonFetch("/api/recordings/stop", {
    method: "POST",
    body: "{}",
  });
  if (result.stopped) {
    const endCommentField = element("endComment");
    const endComment = endCommentField ? endCommentField.value.trim() : "";
    if (endComment) {
      await addAnnotationForRecording(result.recordingId, "session_comment", { text: endComment });
      if (endCommentField) {
        endCommentField.value = "";
      }
    }
    showToast(ui("recordingStopped", result.recordingId));
    appendSigrokLog(`PS> recording ${result.recordingId} stopped (${result.status})`);
  } else {
    showToast(result.message || ui("noActiveRecordingError"), true);
    appendSigrokLog(`PS> ${ui("noCurrentRecording")}`);
  }
  await refreshStatus();
  await refreshRecordings();
}

function resolveRecordingId() {
  if (state.activeStatus && state.activeStatus.active) {
    return Number(state.activeStatus.recordingId);
  }
  if (state.lastRecordingId) {
    return Number(state.lastRecordingId);
  }
  throw new Error(
    ui("startARecordingFirst")
  );
}

async function addAnnotationForRecording(recordingId, kind, payload) {
  const body = { recordingId, kind, payload };
  const result = await jsonFetch("/api/annotations", {
    method: "POST",
    body: JSON.stringify(body),
  });
  showToast(`Annotation ${kind}`);
  await refreshRecordings();
  return result;
}

async function addAnnotation(kind, payload) {
  return addAnnotationForRecording(resolveRecordingId(), kind, payload);
}

function highlightTap(target) {
  target.classList.add("is-active");
  setTimeout(() => target.classList.remove("is-active"), 160);
}

function buildPanelHotspots() {
  const target = element("panelHotspots");
  target.innerHTML = "";
  for (const item of panelButtonLayout) {
    const localizedName = localizedButtonName(item);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `panel-hotspot ${item.cls}`;
    const iconSrc = item.icon;
    button.innerHTML = `
      <img class="panel-icon" src="${iconSrc}" alt="${localizedName}" />
      <span class="visually-hidden">${localizedName}</span>
    `;
    const docKey = item.code;
    button.setAttribute("title", localizedKeyDoc(docKey));
    button.setAttribute("aria-label", `${localizedName}: ${localizedKeyDoc(docKey)}`);

    button.addEventListener("click", async () => {
      try {
        highlightTap(button);
        if (item.direction) {
          await addAnnotation("button_press", {
            button: item.code,
            name: localizedName,
            direction: item.direction,
          });
        } else {
          await addAnnotation("button_press", {
            button: item.code,
            name: localizedName,
          });
        }
        appendStep(localizedName);
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });

    target.appendChild(button);
  }
}

function buildKeyGuide() {
  const target = element("keyGuide");
  if (!target) {
    return;
  }

  const entries = [
    {
      name: "Select Button",
      code: "A",
      docCode: "A",
      icons: ["/static/button-icons/original/selection.png"],
    },
    {
      name: "Cycle Button",
      code: "B",
      docCode: "B",
      icons: ["/static/button-icons/original/cycle.png"],
    },
    {
      name: "Mode Button",
      code: "C",
      docCode: "C",
      icons: ["/static/button-icons/original/mode.png"],
    },
    {
      name: "Display Button",
      code: "D",
      docCode: "D",
      icons: ["/static/button-icons/original/display.png"],
    },
    {
      name: "Invert Button",
      code: "E",
      docCode: "E",
      icons: ["/static/button-icons/original/reverse_display.png"],
    },
    {
      name: "Jets 2 Button",
      code: "F",
      docCode: "F",
      icons: ["/static/button-icons/original/jet_pump_2.png"],
    },
    {
      name: "Jets 1 Button",
      code: "G",
      docCode: "G",
      icons: ["/static/button-icons/original/jet_pump_1.png"],
    },
    {
      name: "Blower Button",
      code: "H",
      docCode: "H",
      icons: ["/static/button-icons/original/fan.png"],
    },
    {
      name: "Light Mode Button",
      code: "I",
      docCode: "I",
      icons: ["/static/button-icons/original/lighting_mode.png"],
    },
    {
      name: "Light Button",
      code: "J",
      docCode: "J",
      icons: ["/static/button-icons/original/light_on_off.png"],
    },
    {
      name: "Warmer and Cooler Buttons",
      code: "K+/K-",
      docCode: "K",
      icons: [
        "/static/button-icons/original/warmer.png",
        "/static/button-icons/original/cooler.png",
      ],
    },
  ];
  target.innerHTML = "";

  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "key-item";
    const docCode = entry.docCode || entry.code;
    const displayName = entry.name;
    const iconsHtml = (entry.icons || [])
      .map((icon) => `<img src="${icon}" alt="${displayName}" />`)
      .join("");
    row.innerHTML = `
      <span class="key-icon-stack">${iconsHtml}</span>
      <span class="key-text"><strong>${displayName}:</strong> ${localizedKeyDoc(docCode)}</span>
    `;
    target.appendChild(row);
  }
}

function refreshActiveDisplaySymbolsInfo() {
  const target = element("activeDisplaySymbols");
  if (!target) {
    return;
  }

  const active = displaySymbolLayout
    .filter((symbol) => state.activeDisplaySymbols.has(symbol.key))
    .map((symbol) => (currentLanguage === "de" ? symbol.labelDe || symbol.labelEn : symbol.labelEn));

  target.textContent = active.length > 0
    ? `${currentLanguage === "de" ? "Aktiv" : "Active"}: ${active.join(" | ")}`
    : ui("noSymbolsActive");
}

function updateDisplayValuePreview() {
  const input = element("displayValue");
  if (!input) {
    return;
  }
  const value = input.value.trim();
  const preview = element("displayValuePreview");
  if (!preview) {
    return;
  }
  preview.textContent = value || "88:8.8";
}

function updateCycleNumberPreview() {
  const node = element("cycleNumberPreview");
  if (!node) {
    return;
  }
  const toggle = element("showCycleNumber");
  const enabled = Boolean(toggle && toggle.checked);
  const input = element("cycleNumber");
  if (!input) {
    return;
  }
  input.disabled = !enabled;
  node.classList.toggle("hidden", !enabled);
  if (!enabled) {
    return;
  }
  const digits = input.value.replace(/\D+/g, "");
  const oneDigit = digits ? digits.slice(-1) : "8";
  if (input.value !== oneDigit) {
    input.value = oneDigit;
  }
  node.textContent = oneDigit;
}

function buildDisplayBoard() {
  const board = element("displayBoard");
  if (!board) {
    return;
  }

  board.innerHTML = "";

  const cycleNumberSymbol = displaySymbolLayout.find((item) => item.key === "cycle_num");

  for (const symbol of displaySymbolLayout) {
    if (symbol.key === "cycle_num") {
      continue;
    }

    if (symbol.interactive === false) {
      const marker = document.createElement("div");
      marker.className = "display-symbol-static";
      marker.style.left = `${symbol.x}%`;
      marker.style.top = `${symbol.y}%`;
      marker.style.width = `${symbol.w}%`;
      marker.innerHTML = `<img src="${symbol.icon}" alt="${currentLanguage === "de" ? symbol.labelDe || symbol.labelEn : symbol.labelEn}" />`;
      board.appendChild(marker);
      continue;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "display-symbol-btn";
    button.dataset.symbol = symbol.key;
    button.setAttribute("aria-label", currentLanguage === "de" ? symbol.labelDe || symbol.labelEn : symbol.labelEn);
    button.setAttribute("title", currentLanguage === "de" ? symbol.labelDe || symbol.labelEn : symbol.labelEn);
    button.style.left = `${symbol.x}%`;
    button.style.top = `${symbol.y}%`;
    button.style.width = `${symbol.w}%`;
    button.innerHTML = `<img src="${symbol.icon}" alt="${currentLanguage === "de" ? symbol.labelDe || symbol.labelEn : symbol.labelEn}" />`;

    button.addEventListener("click", () => {
      const isActive = state.activeDisplaySymbols.has(symbol.key);
      if (isActive) {
        state.activeDisplaySymbols.delete(symbol.key);
      } else {
        state.activeDisplaySymbols.add(symbol.key);
      }
      button.classList.toggle("is-on", !isActive);
      refreshActiveDisplaySymbolsInfo();
    });

    board.appendChild(button);
  }

  const cycleNumber = document.createElement("div");
  cycleNumber.id = "cycleNumberPreview";
  cycleNumber.className = "cycle-number-preview";
  if (cycleNumberSymbol) {
    cycleNumber.style.left = `${cycleNumberSymbol.x}%`;
    cycleNumber.style.top = `${cycleNumberSymbol.y}%`;
    cycleNumber.style.width = `${cycleNumberSymbol.w}%`;
  }
  cycleNumber.textContent = "8";
  board.appendChild(cycleNumber);

  refreshActiveDisplaySymbolsInfo();
  updateCycleNumberPreview();
}

function buildSymbolLegend() {
  const target = element("symbolLegend");
  if (!target) {
    return;
  }
  target.innerHTML = "";

  const descriptions =
    displaySymbolDescriptionsByLang[currentLanguage] || displaySymbolDescriptionsByLang.en;

  for (const entry of descriptions) {
    const symbol = displaySymbolLayout.find((item) => item.key === entry.key);
    const row = document.createElement("div");
    row.className = "symbol-legend-item";
    row.innerHTML = `
      <span class="symbol-legend-icon">${symbol ? `<img src="${symbol.icon}" alt="${entry.title}" />` : ""}</span>
      <span class="symbol-legend-text"><strong>${entry.title}:</strong> ${entry.text}</span>
    `;
    target.appendChild(row);
  }
}

function activeSymbolsFromUi() {
  return Array.from(state.activeDisplaySymbols);
}

async function saveDisplayState() {
  const value = element("displayValue").value.trim();
  const cycleNumberRaw = element("cycleNumber").value.trim();
  const cycleEnabled = Boolean(element("showCycleNumber")?.checked);
  const symbols = activeSymbolsFromUi();
  const cycleNumber = cycleEnabled && cycleNumberRaw ? Number(cycleNumberRaw) : null;

  await addAnnotation("display_state", {
    value,
    cycleNumber,
    symbols,
  });

  const summaryParts = [];
  if (value) {
    summaryParts.push(`Display ${value}`);
  }
  if (symbols.length > 0) {
    summaryParts.push(`Symbols(${symbols.join(",")})`);
  }
  if (cycleNumber !== null && Number.isFinite(cycleNumber)) {
    summaryParts.push(`Filter cycle ${cycleNumber}`);
  }
  if (!value && symbols.length === 0) {
    summaryParts.push("Display without details");
  }
  appendStep(summaryParts.join(" "));
}

function applyLanguage(lang) {
  currentLanguage = lang === "de" ? "de" : "en";
  document.documentElement.lang = currentLanguage;

  const isDe = currentLanguage === "de";

  document.title = ui("pageTitle");

  const appTitle = document.querySelector(".topbar h1");
  if (appTitle) appTitle.textContent = ui("appTitle");

  setText(element("languageLabel"), "languageLabel");
  setText(element("recordingTitle"), "recordingTitle");
  setText(element("sessionNameLabel"), "sessionNameLabel");
  setText(element("driverLabel"), "driverLabel");
  setText(element("channelsLabel"), "channelsLabel");
  setText(element("samplerateLabel"), "samplerateLabel");
  setText(element("durationLabel"), "durationLabel");
  setText(element("endCommentLabel"), "endCommentLabel");
  setText(element("displayValueLabel"), "displayValueLabel");
  setText(element("startBtn"), "startRecording");
  setText(element("stopBtn"), "stopRecording");
  setText(element("testAnalyzerBtn"), "testAnalyzer");
  setText(element("shutdownBtn"), "shutdown");
  setText(element("refreshBtn"), "reloadRecordings");
  setText(element("clearSigrokLogBtn"), "clearLog");
  setText(element("sigrokLogTitle"), "sigrokCommandLog");
  setText(element("simulateLabelText"), "simulateLabelText");
  setText(element("mobileAnnotationTitle"), "mobileAnnotationTitle");
  setText(element("mobileAnnotationHint"), "mobileAnnotationHint");
  setText(element("panelButtonsTitle"), "panelButtonsTitle");
  setText(element("panelButtonsHint"), "panelButtonsHint");
  setText(element("keyGuideTitle"), "mainControlFunctions");
  setText(element("displaySymbolsTitle"), "displayAndSymbolsTitle");
  setText(element("displaySymbolsHint"), "displaySymbolsHint");
  setText(element("cycleNumberLabelText"), "cycleNumberLabel");
  setText(element("clearDisplaySymbolsBtn"), "resetSymbols");
  setText(element("activeDisplaySymbols"), "noSymbolsActive");
  setText(element("symbolLegendTitle"), "lcdScreenFunctions");
  setText(element("saveDisplayBtn"), "saveDisplayState");
  setText(element("recordingsTitle"), "recordingsTitle");
  setText(element("deleteAllBtn"), "deleteAll");
  setText(element("recordingsHeaderId"), "tableId");
  setText(element("recordingsHeaderName"), "tableName");
  setText(element("recordingsHeaderStatus"), "tableStatus");
  setText(element("recordingsHeaderMeasuredAt"), "tableMeasuredAt");
  setText(element("recordingsHeaderDuration"), "tableDuration");
  setText(element("recordingsHeaderSamplerate"), "tableSamplerate");
  setText(element("recordingsHeaderChannels"), "tableChannels");
  setText(element("recordingsHeaderAnnotations"), "tableAnnotations");
  setText(element("recordingsHeaderActions"), "tableActions");
  setPlaceholder(element("driverCustom"), "driverCustomPlaceholder");
  setPlaceholder(element("displayValue"), "displayValuePlaceholder");
  setPlaceholder(element("cycleNumber"), "cycleNumberPlaceholder");
  setPlaceholder(element("endComment"), "endCommentPlaceholder");

  const languageSelect = element("languageSelect");
  setText(languageSelect?.parentElement?.querySelector("span"), "languageLabel");
  setOptionText(languageSelect, 0, "englishOption");
  setOptionText(languageSelect, 1, "germanOption");

  const driverSelect = element("driverSelect");
  if (driverSelect) {
    setOptionText(driverSelect, driverSelect.options.length - 1, "customOption");
  }

  const annotationTitle = document.querySelector(".card-annotation h2");
  const noActive = element("statusText");
  if (noActive && (!state.activeStatus || !state.activeStatus.active)) {
    noActive.textContent = ui("noActiveRecording");
  }

  buildPanelHotspots();
  buildKeyGuide();
  buildSymbolLegend();
  refreshActiveDisplaySymbolsInfo();
  updateSequencePreview();
  refreshRecordings().catch(() => {});

  const keyGuideTitle = document.querySelector(".key-guide-wrap h4");
  if (keyGuideTitle) {
    keyGuideTitle.textContent = ui("mainControlFunctions");
  }
}

function bindActions() {
  element("startBtn").addEventListener("click", async () => {
    try {
      await startRecording();
    } catch (error) {
      appendSigrokLog(`PS> start failed: ${String(error.message || error)}`);
      showToast(String(error.message || error), true);
    }
  });

  element("stopBtn").addEventListener("click", async () => {
    try {
      await stopRecording();
    } catch (error) {
      appendSigrokLog(`PS> stop failed: ${String(error.message || error)}`);
      showToast(String(error.message || error), true);
    }
  });

  const testAnalyzerBtn = element("testAnalyzerBtn");
  if (testAnalyzerBtn) {
    testAnalyzerBtn.addEventListener("click", async () => {
      try {
        await testSignalAnalyzer();
      } catch (error) {
        appendSigrokLog(`PS> ${ui("analyzerTestFailed", getSelectedDriver())}: ${String(error.message || error)}`);
        showToast(String(error.message || error), true);
      }
    });
  }

  const shutdownBtn = element("shutdownBtn");
  if (shutdownBtn) {
    shutdownBtn.addEventListener("click", async () => {
      const ok = window.confirm(ui("shutdownConfirm"));
      if (!ok) {
        return;
      }
      try {
        await requestSystemShutdown();
      } catch (error) {
        appendSigrokLog(`PS> shutdown failed: ${String(error.message || error)}`);
        showToast(String(error.message || error), true);
      }
    });
  }

  const clearSigrokLogBtn = element("clearSigrokLogBtn");
  if (clearSigrokLogBtn) {
    clearSigrokLogBtn.addEventListener("click", () => {
      clearSigrokLog();
    });
  }

  element("refreshBtn").addEventListener("click", async () => {
    try {
      await refreshRecordings();
      await refreshStatus();
      showToast(ui("listRefreshed"));
    } catch (error) {
      setSyncInfo(false, String(error.message || error));
      showToast(String(error.message || error), true);
    }
  });

  const deleteAllBtn = element("deleteAllBtn");
  if (deleteAllBtn) {
    deleteAllBtn.addEventListener("click", async () => {
      const ok = window.confirm(
        ui("deleteAllRecordingsQuestion")
      );
      if (!ok) {
        return;
      }

      try {
        const result = await jsonFetch("/api/recordings/delete-all", {
          method: "POST",
          body: "{}",
        });
        showToast(ui("recordingDeleted", result.deleted));
        await refreshRecordings();
        await refreshStatus();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const saveDisplayBtn = element("saveDisplayBtn");
  if (saveDisplayBtn) {
    saveDisplayBtn.addEventListener("click", async () => {
      try {
        await saveDisplayState();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const clearSequenceBtn = element("clearSequenceBtn");
  if (clearSequenceBtn) {
    clearSequenceBtn.addEventListener("click", () => {
      clearSequence();
      showToast(ui("sequenceCleared"));
    });
  }

  const copySequenceBtn = element("copySequenceBtn");
  if (copySequenceBtn) {
    copySequenceBtn.addEventListener("click", async () => {
      try {
        await copySequence();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const clearDisplaySymbolsBtn = element("clearDisplaySymbolsBtn");
  if (clearDisplaySymbolsBtn) {
    clearDisplaySymbolsBtn.addEventListener("click", () => {
      state.activeDisplaySymbols.clear();
      for (const node of document.querySelectorAll("#displayBoard .display-symbol-btn")) {
        node.classList.remove("is-on");
      }
      const showCycleNumber = element("showCycleNumber");
      if (showCycleNumber) {
        showCycleNumber.checked = false;
      }
      updateCycleNumberPreview();
      refreshActiveDisplaySymbolsInfo();
    });
  }

  const displayValue = element("displayValue");
  if (displayValue) {
    displayValue.addEventListener("input", () => {
      updateDisplayValuePreview();
    });
  }

  const cycleNumber = element("cycleNumber");
  if (cycleNumber) {
    cycleNumber.addEventListener("input", () => {
      updateCycleNumberPreview();
    });
  }

  const showCycleNumber = element("showCycleNumber");
  if (showCycleNumber) {
    showCycleNumber.addEventListener("change", () => {
      updateCycleNumberPreview();
    });
  }

  const languageSelect = element("languageSelect");
  if (languageSelect) {
    languageSelect.addEventListener("change", () => {
      applyLanguage(languageSelect.value);
    });
  }

  const driverSelect = element("driverSelect");
  if (driverSelect) {
    driverSelect.addEventListener("change", () => {
      updateDriverCustomVisibility();
    });
  }

}

async function boot() {
  buildPanelHotspots();
  buildKeyGuide();
  buildDisplayBoard();
  buildSymbolLegend();
  bindActions();
  renderSigrokLog();
  updateSequencePreview();
  updateDisplayValuePreview();

  try {
    const config = await jsonFetch("/api/config");
    element("samplerate").value = config.defaults.samplerate;
    setSelectedChannels(config.defaults.channels);
    setSelectedDriver(config.defaults.driver || "fx2lafw");
    element("durationSeconds").value = String(config.defaults.durationSeconds);
    element("simulate").checked = Boolean(config.defaults.simulate);
  } catch (error) {
    setSyncInfo(false, String(error.message || error));
    showToast(String(error.message || error), true);
  }

  updateDriverCustomVisibility();

  await refreshStatus();
  await refreshRecordings();
  applyLanguage("en");
  setInterval(refreshStatus, 3000);
}

boot().catch((error) => {
  showToast(String(error.message || error), true);
});
