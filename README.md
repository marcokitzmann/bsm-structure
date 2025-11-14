# bsm-structure

Extrahiert und speichert die Ligen- und Team-Strukturen aller Landesverbände im Deutschen Baseball- und Softball-Verband (DBV) aus dem Baseball-Softball-Manager (BSM).

## Beschreibung

Dieses Projekt sammelt automatisch die Strukturdaten (Ligen und Teams) aller Landesverbände aus der BSM-API und speichert sie als strukturierte JSON-Dateien. Die Daten werden wöchentlich aktualisiert und über GitHub Pages bereitgestellt.

## Funktionsweise

### Datenabfrage

Das Skript `bsm-fetcher.py` führt folgende Schritte aus:

1. **Konfiguration laden**: Lädt die Liste der zu verarbeitenden DBV-Landesverbände aus `config/organizations.json`
2. **API-Abfrage**: Für jeden Landesverband wird die BSM-API abgefragt, um alle Matches des aktuellen Jahres zu erhalten
3. **Datenextraktion**: Aus den Match-Daten werden automatisch alle Ligen und Teams extrahiert
4. **Strukturierung**: Die Daten werden hierarchisch strukturiert:
   - Organisationen → Ligen → Teams
5. **Speicherung**: Die vollständige Struktur wird als JSON-Datei im `data/` Verzeichnis gespeichert (Format: `bsm-structure-YYYY.json`)

### Fehlerbehandlung

- **Retry-Logik**: Automatische Wiederholung bei API-Fehlern (max. 3 Versuche)
- **Rate Limiting**: Berücksichtigung von API-Rate-Limits mit exponentieller Backoff-Strategie
- **Timeout-Behandlung**: Konfigurierbare Timeouts für API-Anfragen
- **Fehlerprotokollierung**: Detaillierte Fehlermeldungen für fehlgeschlagene Abfragen

### Automatisierung

Ein GitHub Actions Workflow führt das Skript automatisch aus:

- **Zeitplan**: Wöchentlich montags um 2:00 UTC (3:00 MEZ / 4:00 MESZ)
- **Manueller Start**: Kann auch manuell über `workflow_dispatch` ausgelöst werden
- **Automatisches Deployment**: Die generierten Daten werden automatisch auf GitHub Pages bereitgestellt

## Installation

### Voraussetzungen

- Python 3.11 oder höher
- pip (Python Package Manager)

### Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Die einzige Abhängigkeit ist:
- `requests>=2.31.0` - Für HTTP-Anfragen an die BSM-API

## Verwendung

### Manuelle Ausführung

```bash
python bsm-fetcher.py
```

Das Skript:
- Lädt die Organisationen aus `config/organizations.json`
- Fragt die BSM-API für das aktuelle Jahr ab
- Speichert die Ergebnisse in `data/bsm-structure-YYYY.json`

### Konfiguration

Die zu verarbeitenden Organisationen werden in `config/organizations.json` definiert:

```json
{
  "BWBSV": "organization_7",
  "BSVNRW": "organization_3",
  "BSVBB": "organization_9",
  ...
}
```

Jeder Eintrag besteht aus:
- **Schlüssel**: Name der Organisation (z.B. "BWBSV" für Baden-Württembergischer Baseball- und Softball-Verband)
- **Wert**: Die entsprechende BSM-Organisations-ID

## Datenstruktur

Die generierte JSON-Datei wird über GitHub Pages bereitgestellt und kann direkt verwendet werden:

- **Aktuelle Daten**: Die JSON-Datei ist über GitHub Pages verfügbar unter `https://[repository-owner].github.io/bsm-structure/bsm-structure-2025.json` (ersetze `[repository-owner]` durch den GitHub-Benutzernamen oder Organisationsnamen)

Die JSON-Datei hat folgende Struktur:

```json
{
  "year": 2025,
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
              "name": "Villingendorf Cavemen"
            },
            ...
          ]
        },
        ...
      }
    },
    ...
  },
  "metadata": {
    "generated_at": "2025-01-XX...",
    "total_organizations": 9,
    "successful_organizations": 9,
    "failed_organizations": 0
  }
}
```

## Anwendungsbeispiele

Die generierten Strukturdaten können verwendet werden, um gezielte Abfragen auf die öffentlichen BSM-API-Endpunkte zu erstellen. Hier sind praktische Beispiele:

### Matches für eine bestimmte Liga abfragen

Mit den Daten aus der JSON-Datei können Matches für eine spezifische Liga abgefragt werden. Beispiel für die Verbandsliga Baseball des HBSV (Hessischer Baseball- und Softball-Verband):

**Aus der Strukturdatei:**
- Organisation: `HBSV` → ID: `organization_4`
- Liga: `Verbandsliga Baseball` → ID: `6043`
- Jahr: `2025`

**API-Abfrage:**
```
https://bsm.baseball-softball.de/matches.json?filters[seasons][]={{year}}&filters[organizations][]={{organization_id}}&filters[leagues][]={{league_id}}&filters[gamedays][]=any&compact=true
```

Diese Abfrage liefert alle Matches der Verbandsliga Baseball des HBSV für das Jahr 2025.

### Tabellen für eine Liga abrufen

Um die aktuelle Tabelle einer Liga zu erhalten, kann die Liga-ID verwendet werden:

**Aus der Strukturdatei:**
- Liga-ID: `5829` (z.B. Verbandsliga Herren des BWBSV)

**API-Abfrage:**
```
https://bsm.baseball-softball.de/league_groups/{{league_id}}/table.json?compact=true
```

Diese Abfrage liefert die aktuelle Tabelle der Liga mit allen Teams, Punkten, Siegen und Niederlagen.

## Projektstruktur

```
bsm-structure/
├── bsm-fetcher.py          # Hauptskript zur Datenextraktion
├── config/
│   └── organizations.json  # Konfiguration der Organisationen
├── data/                   # Generierte JSON-Dateien (gitignored)
├── docs/                   # Für GitHub Pages Deployment
├── .github/
│   └── workflows/
│       └── bsm-fetcher.yml # GitHub Actions Workflow
├── requirements.txt        # Python-Abhängigkeiten
└── README.md              # Diese Datei
```

## Technische Details

### API-Dokumentation

Dieses Projekt nutzt die öffentliche API des Baseball-Softball-Managers (BSM) des Deutschen Baseball- und Softball-Verbands (DBV). Die vollständige API-Dokumentation mit allen verfügbaren Endpunkten und Parametern ist verfügbar unter:

**BSM API-Dokumentation**: [https://bsm.baseball-softball.de/api_docs](https://bsm.baseball-softball.de/api_docs)

Die API bietet sowohl freie Endpunkte (ohne API-Key) als auch authentifizierte Endpunkte. Dieses Projekt nutzt ausschließlich die freien Endpunkte mit dem Parameter `compact=true`.

### API-Endpunkt

Das Skript verwendet die BSM-API:
```
https://bsm.baseball-softball.de/matches.json?compact=true&filters[seasons][]=YYYY&filters[organizations][]=ORG_ID&filters[gamedays][]=any
```

### Konfigurierbare Parameter

Im Skript können folgende Parameter angepasst werden:

- `MAX_RETRIES`: Maximale Anzahl von Wiederholungsversuchen (Standard: 3)
- `RETRY_DELAY`: Wartezeit zwischen Wiederholungen in Sekunden (Standard: 10)
- `REQUEST_DELAY`: Wartezeit zwischen verschiedenen API-Requests in Sekunden (Standard: 2)
- `TIMEOUT`: Timeout für API-Anfragen in Sekunden (Standard: 30)

## Lizenz

### Code

Der Quellcode dieses Projekts steht unter der MIT-Lizenz. Der Code kann frei verwendet, modifiziert und verteilt werden, auch für kommerzielle Zwecke.

Siehe [LICENSE](LICENSE) für den vollständigen Lizenztext.

### Daten

Die in diesem Projekt gesammelten und bereitgestellten Daten stammen vom Deutschen Baseball- und Softball-Verband (DBV) über die BSM-API. Die Nutzung dieser Daten unterliegt den Nutzungsbedingungen des DBV. 

**Wichtiger Hinweis**: 
- Die Daten werden automatisch aus der öffentlichen BSM-API extrahiert
- Die Nutzung der Daten erfolgt auf eigene Verantwortung
- Weitere Informationen zur API finden sich in der [BSM API-Dokumentation](https://bsm.baseball-softball.de/api_docs)
