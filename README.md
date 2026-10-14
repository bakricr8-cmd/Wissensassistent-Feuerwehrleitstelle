# Wissensassistent-Feuerwehrleitstelle

Ein lokaler, KI-gestützter Wissensassistent zur Suche und Beantwortung von Fragen auf Grundlage von Feuerwehrdokumenten wie Dienstanweisungen, Alarm- und Ausrückeordnungen (AAO), Standard Operating Procedures (SOPs) und Katastrophenschutzkonzepten.

## Projekt

Im Rahmen des Projekts wird ein Wissensassistent für die Feuerwehrleitstelle Krefeld konzipiert und prototypisch umgesetzt. Ziel ist es, relevante Informationen aus vorhandenen Dokumenten schnell auffindbar zu machen und Disponenten sowie Lagedienst bei der Informationssuche zu unterstützen.

Das System basiert auf dem **Retrieval-Augmented-Generation-Prinzip (RAG)**. Dabei werden zunächst passende Textstellen aus den hinterlegten Dokumenten gesucht. Anschließend erzeugt ein Sprachmodell auf Grundlage dieser Informationen eine Antwort.

Ein besonderer Schwerpunkt liegt auf der Nachvollziehbarkeit der Antworten sowie auf der Versionierung und Aktualität der verwendeten Dokumente.

## Features

- Beantwortung natürlichsprachlicher Fragen zu hinterlegten Feuerwehrdokumenten
- Suche nach relevanten Textstellen in PDF-Dokumenten
- KI-gestützte Antwortgenerierung mithilfe eines lokalen Sprachmodells
- Anzeige der verwendeten Quellen zur Nachvollziehbarkeit der Antworten
- Verwaltung und Aktualisierung der Dokumentengrundlage
- Konzept zur Versionierung und Protokollierung von Dokumenten
- Ziel: Berücksichtigung der Gültigkeit und Aktualität von Dokumentversionen

## Technischer Stack

| Technologie | Aufgabe |
|---|---|
| Python | Programmiersprache und Anwendungslogik |
| Streamlit | Benutzeroberfläche |
| LlamaIndex | Verarbeitung der Dokumente und RAG-Pipeline |
| ChromaDB | Vektordatenbank für die semantische Suche |
| Ollama | Lokale Ausführung des Sprachmodells |
| Qwen3 | Geplantes Sprachmodell |
| SQLite | Geplante Speicherung von Versionsinformationen und Metadaten |
| PlantUML | Modellierung der technischen Systemarchitektur |

*Hinweis: Der Stack beschreibt die geplante Architektur. Die tatsächlich implementierten Komponenten werden im Projektverlauf ergänzt bzw. angepasst.*

## Inhaltsverzeichnis

- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Verwendung](#verwendung)
- [Architektur](#architektur)
- [Dokumentenverwaltung und Versionierung](#dokumentenverwaltung-und-versionierung)
- [Projektstatus](#projektstatus)
- [Sicherheitshinweis](#sicherheitshinweis)

## Voraussetzungen

Für den geplanten Prototyp werden folgende Komponenten benötigt:

- Python 3.11 oder höher (konkrete Version wird im Projekt festgelegt)
- Ollama
- Ein lokal verfügbares, unterstütztes Sprachmodell, z. B. Qwen3
- Git
- PDF-Dokumente als Wissensgrundlage

Die konkreten Versionsanforderungen werden im weiteren Projektverlauf festgelegt.

## Installation

### 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd <REPOSITORY-ORDNER>
```

Ersetze die Platzhalter durch die URL und den Ordnernamen eures GitHub-Repositories.

### 2. Virtuelle Python-Umgebung erstellen

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Abhängigkeiten installieren

Sobald die Datei `requirements.txt` im Repository vorhanden ist:

```bash
pip install -r requirements.txt
```

### 4. Ollama einrichten

Ollama installieren und das im Projekt konfigurierte Sprachmodell lokal bereitstellen.

Beispiel für Qwen3:

```bash
ollama pull qwen3:8b
```

Das konkrete Modell kann je nach verfügbarer Hardware angepasst werden.

### 5. Anwendung starten

Sobald die Streamlit-Anwendung implementiert ist, kann sie beispielsweise folgendermaßen gestartet werden:

```bash
streamlit run app.py
```

Der tatsächliche Startbefehl richtet sich nach der späteren Projektstruktur.

## Konfiguration

### Dokumente

Die Wissensgrundlage besteht aus freigegebenen PDF-Dokumenten, beispielsweise:

- Alarm- und Ausrückeordnungen (AAO)
- Dienstanweisungen
- Standard Operating Procedures (SOPs)
- Katastrophenschutzkonzepte

Die konkrete Ablage und Verarbeitung der Dokumente wird im Projekt festgelegt.

### Sprachmodell

Das Sprachmodell wird lokal über Ollama bereitgestellt. Das verwendete Modell und dessen Konfiguration sollen zentral dokumentiert werden.

### Versionsverwaltung

Für die Nachvollziehbarkeit sollen relevante Dokumentmetadaten erfasst werden. Dazu können beispielsweise gehören:

- Dokumentname und eindeutige Kennung
- Versionsnummer
- Datum der letzten Aktualisierung
- Gültigkeitszeitraum, sofern vorhanden
- Status der Dokumentversion
- Zuordnung der verwendeten Quellen zu einer Antwort

Die konkreten Felder und Prüfmechanismen werden im Rahmen der Implementierung definiert.

## Verwendung

Der vorgesehene Ablauf des Wissensassistenten:

1. Freigegebene Dokumente werden in das System aufgenommen.
2. Die Dokumente werden für die Suche aufbereitet und indexiert.
3. Ein Disponent stellt eine Frage über die Benutzeroberfläche.
4. Das System sucht passende Textstellen in der Wissensbasis.
5. Das Sprachmodell erstellt auf Grundlage der gefundenen Informationen eine Antwort.
6. Die Antwort wird zusammen mit den zugehörigen Quellen angezeigt.

Beispiel für eine mögliche Anfrage:

> Welche Informationen enthält die hinterlegte Dienstanweisung zu einem bestimmten Einsatzszenario?

Die konkrete Antwort hängt von den tatsächlich hinterlegten und freigegebenen Dokumenten ab.

## Architektur

Die geplante Systemarchitektur besteht aus folgenden Komponenten:

- **Streamlit:** Benutzeroberfläche
- **Python:** Anwendungslogik und Steuerung
- **LlamaIndex:** Dokumentenverarbeitung und RAG-Ablauf
- **ChromaDB:** Speicherung und Suche semantischer Dokumentrepräsentationen
- **Ollama mit Qwen3:** Lokale Antwortgenerierung
- **SQLite:** Geplante Speicherung von Dokumentmetadaten und Versionsinformationen

Das System folgt grundsätzlich diesem Ablauf:

**Frage → Retrieval → relevante Textstellen → Sprachmodell → Antwort mit Quellen**

Die technische Architektur wird zusätzlich mit PlantUML modelliert und im Projektverlauf an die tatsächliche Implementierung angepasst.

## Dokumentenverwaltung und Versionierung

Ein wesentliches Projektziel ist die nachvollziehbare Verwendung von Dokumentversionen.

Dabei soll berücksichtigt werden, welche Dokumentversion zum Zeitpunkt einer Anfrage als gültig eingestuft wurde und welche Quellen für die Antwort verwendet wurden.

Die dafür erforderlichen Prüfungen, Aktualisierungsprozesse und Protokollierungsmechanismen werden im Rahmen des Prototyps entwickelt und evaluiert.

## Projektstatus

**Aktueller Status:** Konzeption und technischer Entwurf.

Geplante Arbeitsschritte:

- Anforderungen und Systemarchitektur definieren
- RAG-Prototyp aufbauen
- Dokumente einlesen und durchsuchbar machen
- Antworten mit Quellenangaben erzeugen
- Versionierung und Protokollierung umsetzen
- Qualität, Nachvollziehbarkeit und Aktualität evaluieren

Die tatsächlich umgesetzten Funktionen werden im Verlauf des Projekts ergänzt.

## Sicherheitshinweis

Dieser Wissensassistent ist ein studentischer Forschungs- und Entwicklungsprototyp. Er ist nicht für den ungeprüften Einsatz in einer realen Feuerwehrleitstelle vorgesehen.

KI-generierte Antworten können unvollständig oder fehlerhaft sein. Insbesondere bei einsatzrelevanten Informationen müssen die Originaldokumente und deren Gültigkeit geprüft werden. Eine Nutzung im operativen Einsatz setzt eine entsprechende fachliche, technische und organisatorische Freigabe voraus.

Vertrauliche Feuerwehrdokumente, personenbezogene Daten und interne Einsatzinformationen dürfen nur nach ausdrücklicher Freigabe und unter Einhaltung der geltenden Datenschutz- und Sicherheitsvorgaben verarbeitet werden.
