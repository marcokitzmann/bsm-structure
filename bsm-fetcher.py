import requests
import json
import os
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Variablen
year = datetime.now().year

# Konfiguration
MAX_RETRIES = 3
RETRY_DELAY = 10  # Sekunden zwischen Retries
REQUEST_DELAY = 2  # Sekunden zwischen verschiedenen API-Requests
TIMEOUT = 30  # Sekunden für API-Timeout

def get_organizations() -> Dict[str, str]:
    """
    Lädt die Organisationen aus der JSON-Datei.
    
    Returns:
        Dictionary mit Organisationsnamen und IDs
        
    Raises:
        FileNotFoundError: Wenn die Datei nicht gefunden wird
        json.JSONDecodeError: Wenn die JSON-Datei ungültig ist
        ValueError: Wenn die Datenstruktur ungültig ist
    """
    config_path = 'config/organizations.json'
    
    try:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            organizations = json.load(f)
        
        # Validiere Datenstruktur
        if not isinstance(organizations, dict):
            raise ValueError(f"Ungültige Datenstruktur in {config_path}: Erwartet Dictionary, erhalten {type(organizations).__name__}")
        
        if len(organizations) == 0:
            print("  Warnung: Keine Organisationen in der Konfigurationsdatei gefunden.")
        
        return organizations
        
    except FileNotFoundError as e:
        print(f"FEHLER: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"FEHLER: Ungültiges JSON in {config_path}: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"FEHLER: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"FEHLER: Unerwarteter Fehler beim Laden der Organisationen: {e}")
        sys.exit(1)

def fetch_api_with_retry(url: str, org_name: str, max_retries: int = MAX_RETRIES) -> Optional[requests.Response]:
    """
    Führt einen API-Aufruf mit Retry-Logik durch.
    
    Args:
        url: Die zu abfragende URL
        org_name: Name der Organisation (für Fehlermeldungen)
        max_retries: Maximale Anzahl von Wiederholungsversuchen
    
    Returns:
        Response-Objekt bei Erfolg, None bei Fehler
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=TIMEOUT)
            
            # Erfolgreiche Antwort
            if response.status_code == 200:
                return response
            
            # Spezifische Behandlung verschiedener HTTP-Status-Codes
            elif response.status_code == 429:  # Rate Limit
                if attempt < max_retries:
                    wait_time = RETRY_DELAY * attempt  # Exponential backoff
                    print(f"  Rate Limit erreicht für {org_name}. Warte {wait_time}s vor Wiederholung ({attempt}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  FEHLER: Rate Limit für {org_name} nach {max_retries} Versuchen")
                    return None
            
            elif response.status_code == 503:  # Service Unavailable
                if attempt < max_retries:
                    wait_time = RETRY_DELAY * attempt
                    print(f"  Service vorübergehend nicht verfügbar für {org_name}. Warte {wait_time}s vor Wiederholung ({attempt}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  FEHLER: Service nicht verfügbar für {org_name} nach {max_retries} Versuchen")
                    return None
            
            elif response.status_code == 404:
                print(f"  FEHLER: Ressource nicht gefunden für {org_name} (404)")
                return None
            
            elif response.status_code >= 500:  # Server-Fehler
                if attempt < max_retries:
                    wait_time = RETRY_DELAY * attempt
                    print(f"  Server-Fehler ({response.status_code}) für {org_name}. Warte {wait_time}s vor Wiederholung ({attempt}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  FEHLER: Server-Fehler ({response.status_code}) für {org_name} nach {max_retries} Versuchen")
                    return None
            
            else:
                # Andere HTTP-Fehler
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"  Timeout für {org_name}. Wiederhole Versuch ({attempt}/{max_retries})...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print(f"  FEHLER: Timeout für {org_name} nach {max_retries} Versuchen")
                return None
        
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries:
                print(f"  Verbindungsfehler für {org_name}. Wiederhole Versuch ({attempt}/{max_retries})...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print(f"  FEHLER: Verbindung zu API fehlgeschlagen für {org_name}: {e}")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"  FEHLER: Unerwarteter Request-Fehler für {org_name}: {e}")
            return None
    
    return None

def get_structure_by_organization(org_name: str, org_id: str, year: int) -> Dict[str, Any]:
    """
    Extrahiert alle Ligen und Teams einer Organisation in einem einzigen API-Abruf.
    
    Args:
        org_name: Name der Organisation
        org_id: ID der Organisation
        year: Jahr für die Abfrage
    
    Returns:
        Dictionary mit Ligen und Teams der Organisation
    """
    print(f"Lade Daten für {org_name} ({org_id})...")
    
    # URL mit korrekter Formatierung
    url = f"https://bsm.baseball-softball.de/matches.json?compact=true&filters%5Bseasons%5D%5B%5D={year}&filters%5Borganizations%5D%5B%5D={org_id}&filters%5Bgamedays%5D%5B%5D=any"
    
    leagues_dict = {}  # Dictionary: league_id -> {'id': ..., 'name': ..., 'teams': [...]}
    
    # API-Aufruf mit Retry-Logik
    response = fetch_api_with_retry(url, org_name)
    
    if response is None:
        print(f"  Konnte Daten für {org_name} nicht abrufen.")
        return {'leagues': {}}
    
    # JSON parsen
    try:
        matches = response.json()
    except json.JSONDecodeError as e:
        print(f"  FEHLER: Ungültige JSON-Antwort für {org_name}: {e}")
        return {'leagues': {}}
    
    # API gibt direkt ein Array von Matches zurück
    if not isinstance(matches, list):
        print(f"  Warnung: Unerwartete Datenstruktur für {org_name} (erwartet Liste, erhalten {type(matches).__name__})")
        return {'leagues': {}}
    
    # Durchlaufe alle Matches und extrahiere Ligen und Teams
    for match in matches:
        if not isinstance(match, dict):
            continue
        
        # Extrahiere Liga-Informationen
        league = match.get('league')
        if league and isinstance(league, dict):
            league_id = league.get('id')
            league_name = league.get('name')
            
            if league_id:
                # Initialisiere Liga-Eintrag falls noch nicht vorhanden
                if league_id not in leagues_dict:
                    leagues_dict[league_id] = {
                        'id': league_id,
                        'name': league_name,
                        'teams': {}  # Dictionary: team_id -> {'id': ..., 'name': ...}
                    }
                
                # Extrahiere Home-Team
                home_entry = match.get('home_league_entry')
                if home_entry and isinstance(home_entry, dict):
                    team = home_entry.get('team')
                    if team and isinstance(team, dict):
                        team_id = team.get('id')
                        team_name = team.get('name')
                        if team_id:
                            team_data = {
                                'id': team_id,
                                'name': team_name
                            }
                            
                            # Extrahiere Club-Informationen
                            clubs = team.get('clubs')
                            if clubs and isinstance(clubs, list) and len(clubs) > 0:
                                # Extrahiere alle Clubs aus dem Array
                                clubs_list = []
                                for club in clubs:
                                    if isinstance(club, dict):
                                        clubs_list.append({
                                            'id': club.get('id'),
                                            'name': club.get('name'),
                                            'acronym': club.get('acronym'),
                                            'short_name': club.get('short_name'),
                                            'logo_url': club.get('logo_url')
                                        })
                                # Wenn nur ein Club vorhanden ist, speichere als Objekt, sonst als Array
                                if len(clubs_list) == 1:
                                    team_data['club'] = clubs_list[0]
                                elif len(clubs_list) > 1:
                                    team_data['clubs'] = clubs_list
                            
                            leagues_dict[league_id]['teams'][team_id] = team_data
                
                # Extrahiere Away-Team
                away_entry = match.get('away_league_entry')
                if away_entry and isinstance(away_entry, dict):
                    team = away_entry.get('team')
                    if team and isinstance(team, dict):
                        team_id = team.get('id')
                        team_name = team.get('name')
                        if team_id:
                            team_data = {
                                'id': team_id,
                                'name': team_name
                            }
                            
                            # Extrahiere Club-Informationen
                            clubs = team.get('clubs')
                            if clubs and isinstance(clubs, list) and len(clubs) > 0:
                                # Extrahiere alle Clubs aus dem Array
                                clubs_list = []
                                for club in clubs:
                                    if isinstance(club, dict):
                                        clubs_list.append({
                                            'id': club.get('id'),
                                            'name': club.get('name'),
                                            'acronym': club.get('acronym'),
                                            'short_name': club.get('short_name'),
                                            'logo_url': club.get('logo_url')
                                        })
                                # Wenn nur ein Club vorhanden ist, speichere als Objekt, sonst als Array
                                if len(clubs_list) == 1:
                                    team_data['club'] = clubs_list[0]
                                elif len(clubs_list) > 1:
                                    team_data['clubs'] = clubs_list
                            
                            leagues_dict[league_id]['teams'][team_id] = team_data
    
    # Konvertiere Teams-Dictionaries zu Listen für JSON-Ausgabe
    for league_id in leagues_dict:
        teams_list = list(leagues_dict[league_id]['teams'].values())
        # Sortiere Teams nach ID für konsistente Ausgabe
        teams_list.sort(key=lambda x: x.get('id', 0))
        leagues_dict[league_id]['teams'] = teams_list
    
    print(f"  ✓ Gefunden: {len(leagues_dict)} Ligen")
    total_teams = sum(len(league['teams']) for league in leagues_dict.values())
    print(f"  ✓ Gefunden: {total_teams} Teams insgesamt")
    
    return {'leagues': leagues_dict}

def build_structure(organizations: Dict[str, str], year: int) -> Dict[str, Any]:
    """
    Baut die vollständige Struktur mit Organisationen, Ligen und Teams auf.
    
    Args:
        organizations: Dictionary mit Organisationsnamen und IDs
        year: Jahr für die Abfrage
    
    Returns:
        Dictionary mit der vollständigen Struktur
    """
    structure = {
        'year': year,
        'organizations': {},
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_organizations': len(organizations),
            'successful_organizations': 0,
            'failed_organizations': 0
        }
    }
    
    total_orgs = len(organizations)
    current_org = 0
    
    # Für jede Organisation: Ligen und Teams in einem Durchgang extrahieren
    for org_name, org_id in organizations.items():
        current_org += 1
        print(f"\n[{current_org}/{total_orgs}] Verarbeite {org_name}...")
        
        try:
            org_data = get_structure_by_organization(org_name, org_id, year)
            
            structure['organizations'][org_name] = {
                'id': org_id,
                'leagues': {}
            }
            
            # Konvertiere die Liga-Struktur für die Ausgabe
            for league_id, league_data in org_data['leagues'].items():
                structure['organizations'][org_name]['leagues'][league_id] = {
                    'id': league_data['id'],
                    'name': league_data['name'],
                    'teams': league_data['teams']
                }
            
            # Zähle erfolgreiche Organisationen
            if org_data['leagues']:
                structure['metadata']['successful_organizations'] += 1
            else:
                structure['metadata']['failed_organizations'] += 1
                print(f"  Warnung: Keine Ligen für {org_name} gefunden.")
        
        except Exception as e:
            print(f"  FEHLER: Unerwarteter Fehler bei der Verarbeitung von {org_name}: {e}")
            structure['organizations'][org_name] = {
                'id': org_id,
                'leagues': {},
                'error': str(e)
            }
            structure['metadata']['failed_organizations'] += 1
        
        # Rate Limiting: Warte zwischen Requests (außer beim letzten)
        if current_org < total_orgs:
            time.sleep(REQUEST_DELAY)
    
    return structure

def save_structure(structure: Dict[str, Any], year: int) -> bool:
    """
    Speichert die Struktur in eine JSON-Datei im /data Verzeichnis.
    
    Args:
        structure: Die zu speichernde Struktur
        year: Jahr für den Dateinamen
    
    Returns:
        True bei Erfolg, False bei Fehler
    """
    data_dir = 'data'
    output_file = os.path.join(data_dir, f'bsm-structure-{year}.json')
    
    try:
        # Erstelle /data Verzeichnis falls es nicht existiert
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"Verzeichnis {data_dir} erstellt.")
        
        # Validiere Struktur vor dem Speichern
        if not isinstance(structure, dict):
            raise ValueError(f"Ungültige Struktur: Erwartet Dictionary, erhalten {type(structure).__name__}")
        
        # Speichere in temporäre Datei zuerst, dann umbenennen (atomare Operation)
        temp_file = output_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        
        # Atomare Umbenennung (funktioniert auf Windows und Unix)
        if os.path.exists(output_file):
            os.remove(output_file)
        os.rename(temp_file, output_file)
        
        print(f"\n✓ Struktur wurde erfolgreich in {output_file} gespeichert.")
        
        # Zeige Statistiken
        if 'metadata' in structure:
            meta = structure['metadata']
            print(f"  Erfolgreich: {meta.get('successful_organizations', 0)} Organisationen")
            if meta.get('failed_organizations', 0) > 0:
                print(f"  Fehlgeschlagen: {meta.get('failed_organizations', 0)} Organisationen")
        
        return True
        
    except PermissionError as e:
        print(f"FEHLER: Keine Berechtigung zum Schreiben in {output_file}: {e}")
        return False
    except OSError as e:
        print(f"FEHLER: Dateisystem-Fehler beim Speichern: {e}")
        return False
    except json.JSONEncodeError as e:
        print(f"FEHLER: JSON-Serialisierungsfehler: {e}")
        return False
    except Exception as e:
        print(f"FEHLER: Unerwarteter Fehler beim Speichern: {e}")
        return False

def main():
    """Hauptfunktion zum Ausführen des Skripts."""
    print("BSM-Struktur Extraktor")
    print("=" * 50)
    print(f"Jahr: {year}")
    print(f"Max. Wiederholungen: {MAX_RETRIES}")
    print(f"Request-Delay: {REQUEST_DELAY}s")
    print("=" * 50)
    
    try:
        # Organisationen laden
        organizations = get_organizations()
        print(f"\nGefundene Organisationen: {len(organizations)}")
        
        if len(organizations) == 0:
            print("FEHLER: Keine Organisationen zum Verarbeiten gefunden.")
            sys.exit(1)
        
        # Struktur aufbauen
        structure = build_structure(organizations, year)
        
        # Struktur speichern
        success = save_structure(structure, year)
        
        if success:
            print("\n✓ Prozess erfolgreich abgeschlossen!")
            
            # Warnung wenn einige Organisationen fehlgeschlagen sind
            if 'metadata' in structure:
                failed = structure['metadata'].get('failed_organizations', 0)
                if failed > 0:
                    print(f"\n⚠ Warnung: {failed} Organisation(en) konnten nicht vollständig verarbeitet werden.")
                    print("  Überprüfen Sie die Fehlermeldungen oben.")
        else:
            print("\n✗ Fehler beim Speichern der Struktur.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Prozess durch Benutzer abgebrochen.")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
