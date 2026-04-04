# papyr.bck — Paperless-ngx Backup UI

## What This Is

papyr.bck ist eine Web-UI für Paperless-ngx-Backups. Die App läuft als Docker-Container auf demselben Host wie Paperless-ngx, führt den `document_exporter` per Docker-Exec im Paperless-Container aus und streamt den Output live per Server-Sent Events in den Browser. Zielgruppe: Einzelnutzer im Homelab-Umfeld.

## Core Value

Die App darf niemals die Paperless-ngx-Instanz gefährden — Korrektheit und Sicherheit haben Vorrang vor allem anderen.

## Requirements

### Validated

- ✓ SSE-basiertes Backup-Streaming mit Echtzeit-Output im Browser — existing
- ✓ Docker-Exec in den Paperless-Container (kein HTTP-Aufruf an Paperless-API) — existing
- ✓ Thread-sicherer Backup-Lock (keine parallelen Backups möglich) — existing
- ✓ Optionale HTTP Basic Auth (BACKUP_USER / BACKUP_PASS) — existing
- ✓ Backup-Retention (automatisches Löschen alter Archive, konfigurierbar) — existing
- ✓ Abort-Mechanismus zum Abbrechen laufender Backups — existing
- ✓ Auto-Erkennung des Paperless-Containers (Image-Name oder expliziter Override) — existing
- ✓ Health-Endpoint `/health` für Docker-Healthcheck — existing
- ✓ Sicheres Docker-Setup: Non-root-User, Docker-Socket-GID via group_add — existing

### Active

- [ ] Code-Audit: Implementierungsfehler, Sicherheitsprobleme und Robustheitslücken identifizieren (als Liste, vor Behebung)
- [ ] Doku-Audit: README und Code-Kommentare auf Vollständigkeit und Aktualität prüfen (als Liste, vor Behebung)
- [ ] Identifizierte Bugs und Sicherheitsprobleme beheben
- [ ] Dokumentation korrigieren und vervollständigen

### Out of Scope

- Neue Features — Fokus liegt auf Korrektheit, nicht Erweiterung
- UI-Redesign — die bestehende Oberfläche ist ausreichend
- Paperless-HTTP-API-Integration — Docker-Exec ist die gewählte Strategie
- Benutzer-/Rollenverwaltung — Single-User-Anwendung

## Context

- **Einsatzumgebung:** Homelab, Docker Compose, produktive Paperless-ngx-Instanz
- **Deployment:** Container auf dem selben Docker-Host wie Paperless-ngx; teilt sich den Docker-Socket
- **Aktueller Zustand:** App wurde noch nie produktiv eingesetzt — Code-Review vor dem ersten Start
- **Risiken:** Fehler im Docker-Exec-Befehl, falscher Container-Match, unsaubere Fehlerbehandlung bei laufenden Backups oder Abbrüchen
- **Kein automatisches Test-Setup vorhanden** — Änderungen müssen sorgfältig manuell verifiziert werden

## Constraints

- **Tech Stack:** Python 3.12, Flask 3.1.0, Docker SDK 7.1.0, Gunicorn — keine Änderung des Stacks
- **Sicherheit:** Änderungen dürfen die Paperless-Instanz unter keinen Umständen gefährden
- **Vorgehen:** Audit-Ergebnisse werden erst als Liste präsentiert, dann nach Freigabe behoben
- **Deployment:** Muss als Docker-Container laufen, Docker-Socket-Zugriff erforderlich

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Erst Liste, dann beheben | Nutzer will Kontrolle behalten vor Produktiveinsatz | — Pending |
| Docker-Exec statt Paperless-API | Kein API-Schlüssel nötig, direkter Zugriff auf Paperless-Internals | ✓ Good |
| Non-root User im Container | Sicherheits-Best-Practice | ✓ Good |
| Optional HTTP Basic Auth | Flexible für LAN-only vs. exposed deployments | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-04 after initialization*
