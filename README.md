# Wissensassistent Feuerwehrleitstelle

Lokaler Wissensassistent zur Suche und Beantwortung von Fragen auf Grundlage von Feuerwehrdokumenten unter Berücksichtigung von Dokumentversionen und Gültigkeitszeiträumen.

## Projekt

Dieses Projekt entwickelt einen Wissensassistenten für die Feuerwehr der Stadt Krefeld.

Ziel ist es, Mitarbeitenden einer Feuerwehrleitstelle den Zugriff auf wichtige Informationen aus verschiedenen Dokumenten zu erleichtern. Dazu gehören beispielsweise Dienstanweisungen, Alarm- und Ausrückeordnungen (AAO), Checklisten, Standard Operating Procedures (SOPs) und Katastrophenschutzkonzepte.

Dokumente können eingelesen, verwaltet und durchsucht werden. Zu einer Anfrage werden passende Textstellen und die zugehörigen Quellen angezeigt. Optional kann ein lokal ausgeführtes Sprachmodell von Ollama zur Formulierung einer Antwort verwendet werden.

Ein besonderer Schwerpunkt liegt auf der Verwaltung von Dokumentversionen und Gültigkeitszeiträumen, damit abgelaufene oder nicht freigegebene Dokumente nicht als gültige Informationsgrundlage verwendet werden.

![Benutzeroberfläche des Wissensassistenten](UML/Screenshot.png)

## Features

- **Multi-Format-Import:** Import von PDF-, TXT- und Markdown-Dateien
- **Semantische & Textsuche:** Suche nach passenden Textstellen in den hinterlegten Dokumenten
- **Lokale KI-Integration:** Optionale Antwortgenerierung mit einem lokalen Ollama-Modell
- **Transparenz:** Anzeige der verwendeten Dokumente und Fundstellen
- **Gültigkeits- & Versionsverwaltung:** Steuerung von Dokumentversionen, Gültigkeitszeiträumen und Unterscheidung zwischen freigegebenen Dokumenten und Entwürfen
- **Lokale Datenspeicherung:** Speicherung von Dokumentinformationen und Suchvorgängen in SQLite
- **Audit-Trail:** Prüfprotokoll mit Quellen und Dokumentversionen
- **Datenschutz:** Vollständig lokale Verarbeitung aller Dokumente

## Inhaltsverzeichnis

- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Anwendung starten](#anwendung-starten)
- [Ollama konfigurieren](#ollama-konfigurieren)
- [Tests](#tests)
- [Projektstruktur](#projektstruktur)
- [Dokumentverwaltung und Nachvollziehbarkeit](#dokumentverwaltung-und-nachvollziehbarkeit)

## Voraussetzungen

- **Python:** 3.11 oder neuer
- **Package Manager:** `pip` zur Installation der Python-Bibliotheken
- **Versionsverwaltung:** Git zum Klonen des Repositorys
- **Optional:** Ollama für die KI-gestützte Antwortgenerierung (für die reine Dokumentensuche wird keine Ollama-Installation benötigt)

## Installation

### 1. Repository klonen
```bash
git clone <REPOSITORY-URL>
cd Wissensassistent-Feuerwehrleitstelle
```

### 2. Virtuelle Umgebung erstellen

#### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Bibliotheken installieren
```bash
python -m pip install -r requirements.txt
```

## Anwendung starten

Die Anwendung wird mit Streamlit gestartet:

```bash
streamlit run app.py
```

Nach dem Start ist die Benutzeroberfläche standardmäßig unter folgender Adresse erreichbar:  
[http://localhost:8501](http://localhost:8501)

## Ollama konfigurieren

Für die KI-gestützte Antwortgenerierung muss Ollama installiert und gestartet sein.

Die Anwendung verwendet standardmäßig folgende lokale Verbindung:
- **URL:** `http://127.0.0.1:11434`
- **Port:** `11434`

Das verwendete Modell kann in der Benutzeroberfläche angegeben werden. Als Standardmodell ist `qwen3:4b-instruct` hinterlegt.

### Modell herunterladen
```bash
ollama pull qwen3:4b-instruct
```

Anschließend kann in der Anwendung im Seitenbereich der Modus **Ollama (lokal)** ausgewählt werden. Alternativ kann die Anwendung ohne Ollama im Modus **Fundstellen (ohne KI)** verwendet werden.

## Tests

Die Tests werden mit folgendem Befehl ausgeführt:

```bash
python -m unittest discover -s tests -v
```

> **Hinweis:** Eine laufende Ollama-Instanz ist für die Durchführung der Tests nicht erforderlich.

## Projektstruktur

```text
Wissensassistent-Feuerwehrleitstelle/
│
├── app.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── database.py
│   ├── document_loader.py
│   ├── document_search.py
│   ├── rag_pipeline.py
│   └── version_manager.py
│
├── Dokumente/
│   ├── Beispieldokumente
│   └── metadaten.json
│
├── tests/
│   ├── test_rag.py
│   └── test_versions.py
│
├── UML/
│   ├── Aktivitätendiagramm.pdf
│   ├── Komponentendiagramm.pdf
│   └── Use Case Diagramm.pdf
│
└── data/
    └── wissensassistent.sqlite3
```

## Dokumentverwaltung und Nachvollziehbarkeit

Dokumente werden mit strukturierten Metadaten gespeichert:
- Dokument-ID
- Dokumentart
- Versionsnummer
- Status (z. B. Freigegeben vs. Entwurf)
- Gültigkeitszeitraum

Bei jeder Suche wird automatisch geprüft, welche Dokumente zum jeweiligen Gültigkeitsstichtag verwendet werden dürfen. Die verwendeten Textstellen und Quellen werden zusammen mit den zugehörigen Dokumentinformationen in einem Prüfprotokoll nachvollziehbar dokumentiert.

Die SQLite-Datenbank wird lokal im Verzeichnis `data/` gespeichert und ist über `.gitignore` von der Versionsverwaltung ausgeschlossen.
