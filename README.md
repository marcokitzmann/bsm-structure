# bsm-structure

Extrahiert die Liga- und Team-Strukturen des Deutschen Baseball- und Softball-Verbands (DBV) und seiner Landesverbände aus dem Baseball-Softball-Manager (BSM) und stellt sie als JSON über GitHub Pages bereit.

## Beschreibung

Das Projekt sammelt automatisch die Strukturdaten (Organisationen → Ligen → Teams → Clubs) aus der öffentlichen BSM-API und speichert sie je Saison als JSON-Datei. Abgebildet wird nur der **Liga-Betrieb**: Turniere, Meisterschaften, Pokale und Auswahl-Wettbewerbe werden aussortiert (siehe [Nur Liga-Betrieb](#nur-liga-betrieb)).

Die Daten werden in der Saison (März–Oktober) täglich und in der Off-Season (November–Februar) wöchentlich aktualisiert.

**Daten abrufen:**

```
https://marcokitzmann.github.io/bsm-structure/bsm-structure-YYYY.json
```

Verfügbar sind die Saisons ab 2024 (z. B. [`bsm-structure-2026.json`](https://marcokitzmann.github.io/bsm-structure/bsm-structure-2026.json)).

## Funktionsweise

### Ablauf

Das Skript `bsm-fetcher.py` führt folgende Schritte aus:

1. **Konfiguration laden**: Organisationen aus `config/organizations.json`, Ausnahmen für die Turnier-Erkennung aus `config/competition-overrides.json`
2. **API-Abfrage**: Je Organisation ein Abruf aller Matches der Saison (ein Request pro Organisation, 2 s Pause dazwischen)
3. **Datenextraktion**: Aus Liga, Heim- und Gast-Eintrag jedes Matches werden Ligen, Teams und Clubs gewonnen
4. **Nur Liga-Betrieb**: Turniere und Auswahl-Wettbewerbe werden aussortiert und unter `metadata.excluded_competitions` protokolliert
5. **Speicherung**: Ergebnis in `data/bsm-structure-YYYY.json` (atomar über eine temporäre Datei)

Da die Struktur aus den Matches abgeleitet wird, erscheint eine Liga erst, wenn für sie mindestens ein Spiel angesetzt ist.

### Nur Liga-Betrieb

Ausgegeben werden Ligen einschließlich Play-offs, Playdowns, Wild-Card-Runden, Interleague und Runden (z. B. R1/R2, Herbstrunde). BSM kennzeichnet Turniere nicht (`league.type` ist immer `"League"`), daher wird ein Wettbewerb aussortiert, wenn eine der folgenden Regeln greift:

| Regel | Beispiel | `reason` |
|---|---|---|
| Name enthält `DM` als eigenes Wort | DM Junioren Gruppe A | `Deutsche Meisterschaft` |
| Name beginnt mit `LP ` | LP U15 BB Play-offs | `Länderpokal` |
| Name enthält `Meisterschaft` | Jugend Softball (U16) - Bay. Meisterschaft | `Meisterschaft` |
| Name enthält `Pokal` | Deutschlandpokal Softball, Landesliga-Pokal | `Pokal` |
| Name enthält `Finale` | NBSV Landesliga Finale 2026 | `Finale` |
| Name enthält `All-Star` oder `Allstar` | S/HBV-Allstar-Game | `All-Star` |
| Name enthält `Slowpitch` | BBQ Slowpitch-Mixed Softball | `Slowpitch-Turnier` |
| Mindestens ein Team, dessen einziger „Club“ ein Landesverband ohne Namen ist | U13SB Gruppe A | `Landesauswahl` |

Groß-/Kleinschreibung spielt keine Rolle, außer bei den Kürzeln `DM` und `LP`. Die Regeln stehen in `TOURNAMENT_NAME_PATTERNS` und `classify_competition()` in `bsm-fetcher.py`. Saison 2026: 65 von 225 Wettbewerben aussortiert.

**Ausnahmen** je Saison über BSM-Liga-IDs in `config/competition-overrides.json`:

```json
{
  "include": [6123],
  "exclude": [6456]
}
```

- `include`: Wettbewerb immer ausgeben, auch wenn eine Regel greift
- `exclude`: Wettbewerb immer aussortieren (`reason`: `Manuell ausgeschlossen`)

Liga-IDs ändern sich jede Saison. Eine ID in beiden Listen oder ungültige Werte brechen den Lauf mit Fehlermeldung ab.

### Fehlerbehandlung

- **Retry-Logik**: Bis zu 3 Versuche bei Timeouts, Verbindungsfehlern, 429 und 5xx
- **Wartezeit**: Steigt mit jedem Versuch (10 s, 20 s), bei Timeouts und Verbindungsfehlern fest 10 s
- **Ausfall einer Organisation**: Der Lauf geht weiter; die Organisation erscheint mit leeren Ligen (ggf. mit `error`) und wird in `metadata.failed_organizations` gezählt
- **Konfigurationsfehler**: Fehlende oder ungültige Konfigurationsdateien beenden den Lauf mit Exit-Code 1

### Automatisierung

Der GitHub-Actions-Workflow `.github/workflows/bsm-fetcher.yml`:

- **Zeitplan**: 2:00 UTC (3:00 MEZ / 4:00 MESZ)
  - März–Oktober täglich (`0 2 * 3-10 *`)
  - November–Februar nur montags (`0 2 * 11,12,1,2 1`)
- **Manueller Start**: über `workflow_dispatch`
- **Aktuelles Jahr**: wird bei jedem Lauf neu erzeugt
- **Historische Jahre** (ab 2024): werden nur erzeugt, wenn die Datei in `docs/` fehlt
- **Veröffentlichung**: Die Dateien werden nach `docs/` kopiert, committet (`[skip ci]`) und auf GitHub Pages deployt

**Hinweis zu historischen Jahren**: Die Dateien für 2024 und 2025 stammen von vor der Turnier-Erkennung und enthalten noch Turniere (ohne `excluded_competitions`). Zum Neuerzeugen die Datei aus `docs/` löschen und den Workflow manuell starten.

## Installation

### Voraussetzungen

- Python 3.11 oder höher (wie im Workflow)
- pip

### Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Einzige Abhängigkeit: `requests>=2.31.0` für die HTTP-Anfragen an die BSM-API.

## Verwendung

### Manuelle Ausführung

```bash
python bsm-fetcher.py              # aktuelles Jahr
python bsm-fetcher.py --year 2026  # bestimmtes Jahr (2000–2100)
```

Das Ergebnis landet in `data/bsm-structure-YYYY.json`. Am Ende listet das Skript alle aussortierten Wettbewerbe mit Grund auf.

### Konfiguration

**`config/organizations.json`**: zu verarbeitende Organisationen

```json
{
  "DBV": "federation_1",
  "BWBSV": "organization_7",
  "BSVNRW": "organization_3",
  ...
}
```

- **Schlüssel**: Kürzel der Organisation (z. B. `BWBSV` für den Baden-Württembergischen Baseball- und Softball-Verband); wird als Schlüssel unter `organizations` ausgegeben
- **Wert**: BSM-Organisations-ID

Aktuell: DBV sowie die Landesverbände BWBSV, BSVNRW, BSVBB, BBSV, HBSV, MBSV, NBSV, SHBV und SWBSV.

**`config/competition-overrides.json`**: Ausnahmen für die Turnier-Erkennung (siehe oben). Fehlt die Datei, gelten nur die automatischen Regeln.

## Datenstruktur

```json
{
  "year": 2026,
  "organizations": {
    "BWBSV": {
      "id": "organization_7",
      "leagues": {
        "5829": {
          "id": 5829,
          "name": "Verbandsliga Herren",
          "teams": [
            {
              "id": 22812,
              "league_entry_id": 45210,
              "name": "Villingendorf Cavemen",
              "club": {
                "id": 438,
                "name": "Cavemen",
                "acronym": "VIL",
                "short_name": "Villingendorf Cavemen",
                "logo_url": "https://bsm.baseball-softball.de/system/clubs/logos/..."
              }
            },
            {
              "id": 23473,
              "league_entry_id": 45218,
              "name": "SG Friedberg Braves/Giessen Busters",
              "clubs": [
                {
                  "id": 193,
                  "name": "Braves",
                  "acronym": "FRI",
                  "short_name": "Friedberg Braves",
                  "logo_url": null
                },
                {
                  "id": 199,
                  "name": "Giessen Busters",
                  "acronym": "GIE",
                  "short_name": "Giessen Busters",
                  "logo_url": "https://bsm.baseball-softball.de/system/clubs/logos/..."
                }
              ]
            }
          ]
        }
      }
    }
  },
  "metadata": {
    "generated_at": "2026-11-02T02:01:13.000000",
    "total_organizations": 10,
    "successful_organizations": 10,
    "failed_organizations": 0,
    "excluded_competitions": [
      {
        "organization": "DBV",
        "id": 6315,
        "name": "DM Junioren Gruppe A",
        "reason": "Deutsche Meisterschaft"
      }
    ]
  }
}
```

(IDs im Beispiel gekürzt bzw. illustrativ.)

### Ligen

- Schlüssel unter `leagues` ist die BSM-Liga-ID als String, `id` dieselbe ID als Zahl
- **`name`** (string): Name der Liga laut BSM

### Teams

- **`id`** (integer): BSM-Team-ID
- **`league_entry_id`** (integer): BSM-Ligaeintrag des Teams (Meldung eines Teams für eine Liga)
- **`name`** (string): Name des Teams
- **`club`** (object): Club, wenn das Team genau einem Club zugeordnet ist
  - **`id`** (integer), **`name`** (string), **`acronym`** (string), **`short_name`** (string), **`logo_url`** (string|null)
- **`clubs`** (array): Clubs einer Spielgemeinschaft, gleiche Felder wie `club`

Ein Team hat entweder `club` oder `clubs`, nie beides. Teams sind je Liga nach `id` sortiert.

**Teams in mehreren Ligen**: Dieselbe Team-ID kann in mehreren Ligen vorkommen, z. B. in Hauptrunde und Play-offs (meist mit eigenem `league_entry_id` je Liga). Weil die Zuordnung aus den Matches stammt, kann ein Team mit demselben `league_entry_id` auch in einer zweiten Liga auftauchen, wenn es dort gruppenübergreifend gespielt hat.

### Metadaten

- **`generated_at`**: Zeitpunkt der Erzeugung (Zeit des Runners, UTC im Workflow)
- **`total_organizations`**, **`successful_organizations`**, **`failed_organizations`**: Anzahl konfigurierter, erfolgreich und nicht verarbeiteter Organisationen
- **`excluded_competitions`**: aussortierte Wettbewerbe mit `organization`, `id`, `name`, `reason`

## Anwendungsbeispiele

Mit den Strukturdaten lassen sich gezielte Abfragen an die öffentlichen BSM-Endpunkte stellen.

### Matches einer Liga

Aus der Strukturdatei: Organisation `HBSV` → `organization_4`, Liga `Verbandsliga Baseball` → `6043`, Jahr `2025`.

```
https://bsm.baseball-softball.de/matches.json?filters[seasons][]={{year}}&filters[organizations][]={{organization_id}}&filters[leagues][]={{league_id}}&filters[gamedays][]=any&compact=true
```

### Tabelle einer Liga

```
https://bsm.baseball-softball.de/league_groups/{{league_id}}/table.json?compact=true
```

Liefert die aktuelle Tabelle mit allen Teams, Punkten, Siegen und Niederlagen.

## Projektstruktur

```
bsm-structure/
├── bsm-fetcher.py                   # Hauptskript zur Datenextraktion
├── config/
│   ├── organizations.json           # Zu verarbeitende Organisationen
│   └── competition-overrides.json   # Ausnahmen für die Turnier-Erkennung
├── data/                            # Lokal erzeugte JSON-Dateien (gitignored)
├── docs/                            # Veröffentlichte JSON-Dateien (GitHub Pages)
├── .github/
│   └── workflows/
│       └── bsm-fetcher.yml          # GitHub-Actions-Workflow
├── requirements.txt                 # Python-Abhängigkeiten
└── README.md                        # Diese Datei
```

## Technische Details

### BSM-API

Das Projekt nutzt ausschließlich freie Endpunkte der BSM-API (ohne API-Key) mit `compact=true`. Dokumentation: [https://bsm.baseball-softball.de/api_docs](https://bsm.baseball-softball.de/api_docs)

Verwendeter Endpunkt:

```
https://bsm.baseball-softball.de/matches.json?compact=true&filters[seasons][]=YYYY&filters[organizations][]=ORG_ID&filters[gamedays][]=any
```

### Parameter im Skript

- `MAX_RETRIES`: Anzahl Versuche je Request (Standard: 3)
- `RETRY_DELAY`: Basis-Wartezeit zwischen Versuchen in Sekunden (Standard: 10)
- `REQUEST_DELAY`: Pause zwischen Organisationen in Sekunden (Standard: 2)
- `TIMEOUT`: Timeout je Request in Sekunden (Standard: 30)
- `TOURNAMENT_NAME_PATTERNS`: Namensregeln der Turnier-Erkennung
- `COMPETITION_OVERRIDES_PATH`: Pfad der Ausnahme-Datei

## Lizenz

### Code

Der Quellcode steht unter der MIT-Lizenz und darf frei verwendet, verändert und weitergegeben werden, auch kommerziell. Siehe [LICENSE](LICENSE).

### Daten

Die Daten stammen vom Deutschen Baseball- und Softball-Verband (DBV) über die BSM-API. Ihre Nutzung unterliegt den Nutzungsbedingungen des DBV.

**Wichtiger Hinweis**:
- Die Daten werden automatisch aus der öffentlichen BSM-API extrahiert
- Die Nutzung erfolgt auf eigene Verantwortung
- Weitere Informationen in der [BSM API-Dokumentation](https://bsm.baseball-softball.de/api_docs)
