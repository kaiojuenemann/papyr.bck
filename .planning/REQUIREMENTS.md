# Requirements: papyr.bck

**Defined:** 2026-04-04
**Core Value:** Die App darf niemals die Paperless-ngx-Instanz gefährden — Korrektheit und Sicherheit haben Vorrang vor allem anderen.

## v1 Requirements

Ziel dieser Version: App vor dem ersten Produktiveinsatz auf Korrektheit, Sicherheit und Robustheit prüfen und bereinigen.

### Code Audit

- [ ] **AUDIT-01**: Alle Implementierungsfehler in `app.py` sind identifiziert und als Liste dokumentiert
- [ ] **AUDIT-02**: Alle Sicherheitsprobleme (Auth, Docker-Socket-Zugriff, Input-Handling) sind identifiziert und als Liste dokumentiert
- [ ] **AUDIT-03**: Alle Robustheitslücken (Fehlerbehandlung, Edge Cases, Race Conditions) sind identifiziert und als Liste dokumentiert
- [ ] **AUDIT-04**: Identifizierte Bugs und Sicherheitsprobleme sind nach Freigabe behoben
- [ ] **AUDIT-05**: Korrektheit der Container-Erkennung (falscher Container-Match, Race Conditions beim Backup-Lock) ist geprüft und ggf. behoben

### Dokumentation

- [ ] **DOCS-01**: README auf Vollständigkeit und Aktualität geprüft — alle Setup-Schritte, Konfigurationsoptionen und Einschränkungen dokumentiert
- [ ] **DOCS-02**: Code-Kommentare in `app.py` auf Richtigkeit geprüft — veraltete oder irreführende Kommentare korrigiert
- [ ] **DOCS-03**: `docker-compose.yml` und `docker-compose.secure.yml` Dokumentation geprüft und ggf. ergänzt
- [ ] **DOCS-04**: Umgebungsvariablen vollständig und korrekt in README dokumentiert

### Setup & Bedienung

- [ ] **SETUP-01**: Setup-Prozess (setup.sh / setup_web.py) ist vollständig und fehlerfrei — kein Setup-Schritt fehlt oder führt in einen Fehlerfall
- [ ] **SETUP-02**: Web-UI zeigt klare Fehlermeldungen bei Fehlkonfiguration (kein Docker, falscher Container, Auth-Fehler)

## v2 Requirements

Deferred — nach erfolgreichem ersten Produktiveinsatz:

### Observability

- **OBS-01**: Backup-History anzeigen (letzte N Backups mit Zeitstempel und Ergebnis)
- **OBS-02**: Backup-Größen in der UI anzeigen

### Hardening

- **HARD-01**: Konfigurierbare Backup-Zeitplanung (Cron-ähnlich)
- **HARD-02**: Benachrichtigung bei erfolglosem Backup (E-Mail oder Webhook)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Neue UI-Features | Fokus liegt auf Korrektheit, nicht Erweiterung |
| UI-Redesign / Styling | Bestehende Oberfläche ist funktional ausreichend |
| Paperless-HTTP-API-Integration | Docker-Exec ist die gewählte Strategie — kein Umbau |
| Benutzer-/Rollenverwaltung | Single-User-Anwendung |
| Automatische Tests (CI/CD) | Scope dieser Version ist manueller Audit + Fix |
| Cloud-Backup-Integration | Out of scope — lokale Backups reichen |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIT-01 | Phase 1 | Pending |
| AUDIT-02 | Phase 1 | Pending |
| AUDIT-03 | Phase 1 | Pending |
| AUDIT-05 | Phase 1 | Pending |
| DOCS-01 | Phase 2 | Pending |
| DOCS-02 | Phase 2 | Pending |
| DOCS-03 | Phase 2 | Pending |
| DOCS-04 | Phase 2 | Pending |
| AUDIT-04 | Phase 3 | Pending |
| SETUP-01 | Phase 3 | Pending |
| SETUP-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial definition*
