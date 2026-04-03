# papyr.bck

**papyr.bck** ist eine kleine Web-App, mit der du deine [Paperless-ngx](https://docs.paperless-ngx.com/)-Dokumente per Knopfdruck sichern kannst. Du öffnest einfach eine Seite im Browser, klickst auf „Backup starten" und siehst live, was passiert.

**Repository:** https://github.com/kaiojuenemann/papyr.bck

---

## Was macht die App genau?

Paperless-ngx speichert alle deine eingescannten Dokumente auf deinem Server. papyr.bck macht davon eine Sicherungskopie – eine sogenannte **Backup-Datei** (`.tar.gz`). Diese Datei enthält alle deine Dokumente und kann im Notfall (z.B. wenn dein Server abstürzt) wiederhergestellt werden.

Die App:
- findet deinen Paperless-Container automatisch
- exportiert alle Dokumente aus Paperless
- packt sie in eine Archiv-Datei mit Datum im Namen
- löscht alte Sicherungen automatisch, wenn du zu viele hast
- zeigt dir alles live im Browser-Fenster

---

## Was du brauchst, bevor du anfängst

- **Docker** ist auf deinem Server installiert
  *(Docker ist ein Programm, das Apps in abgeschlossenen „Boxen" – sogenannten Containern – ausführt)*
- **Paperless-ngx** läuft bereits als Docker-Container
- Du kannst Befehle in einem Terminal eingeben
  *(Das Terminal ist das schwarze Fenster, in dem man Texteingaben macht)*

---

## Schritt-für-Schritt-Anleitung

### Schritt 1 – Dateien herunterladen

Lade dir das Repository auf deinen Server herunter:

```bash
git clone https://github.com/kaiojuenemann/papyr.bck.git
cd papyr.bck
```

> **Was passiert hier?** `git clone` kopiert alle Dateien vom Internet auf deinen Server. `cd` wechselt dann in den neuen Ordner.

---

### Schritt 2 – Backup-Ordner anlegen

Die fertigen Backup-Dateien werden in einem Ordner gespeichert. Leg diesen Ordner jetzt an:

```bash
mkdir -p /backup/paperless
```

> **Was passiert hier?** `mkdir -p` erstellt den Ordner `/backup/paperless` auf deinem Server. Wenn du einen anderen Ort möchtest, kannst du den Pfad ändern – denk dann daran, ihn auch in Schritt 4 anzupassen.

---

### Schritt 3 – Herausfinden, welche Gruppen-ID der Docker-Socket hat

Docker läuft auf deinem Server mit bestimmten Berechtigungen. papyr.bck muss die richtige Gruppen-ID kennen, damit es mit Docker sprechen darf.

Führe diesen Befehl aus:

```bash
stat -c '%g' /var/run/docker.sock
```

Du bekommst eine Zahl ausgegeben, zum Beispiel `999`. Merke dir diese Zahl.

---

### Schritt 4 – Konfiguration anpassen

Öffne die Datei `docker-compose.yml` in einem Texteditor. Suche nach diesen Stellen und passe sie an:

**a) Export-Pfad von Paperless**
Das ist der Ordner, in den Paperless deine Dokumente exportiert. Standardmäßig steht dort:
```yaml
- ./paperless/export:/usr/src/paperless/export:ro
```
Ersetze `./paperless/export` durch den tatsächlichen Pfad auf deinem Server.

**b) Backup-Zielordner**
Das ist der Ordner aus Schritt 2. Standardmäßig steht dort:
```yaml
- /backup/paperless:/backup/paperless
```
Wenn du in Schritt 2 einen anderen Pfad gewählt hast, passe ihn hier an.

**c) Gruppen-ID**
Suche nach `group_add` und trage die Zahl aus Schritt 3 ein:
```yaml
group_add:
  - "999"   ← deine Zahl hier eintragen
```

---

### Schritt 5 – Passwortschutz einrichten (empfohlen!)

Damit nicht jeder im Netzwerk deine Backups starten kann, solltest du einen Benutzernamen und ein Passwort setzen. Suche in `docker-compose.yml` nach diesen Zeilen:

```yaml
BACKUP_USER: ""
BACKUP_PASS: ""
```

Und ersetze die leeren Anführungszeichen durch deine Zugangsdaten:

```yaml
BACKUP_USER: "mein-benutzername"
BACKUP_PASS: "mein-sicheres-passwort"
```

> **Wichtig:** Wenn du `BACKUP_USER` setzt, muss auch `BACKUP_PASS` gesetzt sein. Ohne Passwort blockiert die App alle Anfragen.

---

### Schritt 6 – App starten

Jetzt kannst du die App starten:

```bash
docker compose up -d --build
```

> **Was passiert hier?** Docker lädt alle nötigen Pakete, baut die App zusammen und startet sie im Hintergrund (`-d` steht für „detached", also im Hintergrund). Das dauert beim ersten Mal ein bisschen länger.

Öffne danach deinen Browser und gehe zu:

```
http://DEINE-SERVER-IP:8080
```

*(Wenn du es lokal testest: `http://localhost:8080`)*

---

### Schritt 7 – Backup durchführen

1. Öffne die Web-App im Browser
2. Du siehst den Status: ob Docker erreichbar ist und ob Paperless gefunden wurde
3. Klicke auf **„Backup starten"**
4. Im Log-Fenster siehst du live, was passiert
5. Wenn alles geklappt hat, erscheint „Backup erfolgreich abgeschlossen"
6. Unter „Vorhandene Archive" siehst du deine Backup-Dateien – von dort kannst du sie auch herunterladen

---

## Für Fortgeschrittene: Noch sicherer mit Socket-Proxy

Standardmäßig hat papyr.bck Zugriff auf den gesamten Docker-Socket. Das ist vergleichbar damit, jemandem den Generalschlüssel zu geben, obwohl er nur ein bestimmtes Zimmer braucht.

Mit dem Socket-Proxy gibst du der App nur den Zugriff, den sie wirklich braucht. Starte dazu die App so:

```bash
docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d --build
```

---

## Alle Einstellungen im Überblick

Diese Einstellungen kannst du in `docker-compose.yml` unter `environment` anpassen:

| Einstellung                | Standardwert                    | Bedeutung |
|----------------------------|---------------------------------|-----------|
| `PAPERLESS_IMAGE_NAME`     | `paperless-ngx`                 | Name des Paperless-Docker-Images |
| `PAPERLESS_CONTAINER_NAME` | *(leer)*                        | Falls du den Container-Namen direkt angeben willst |
| `EXPORT_PATH_IN_CONTAINER` | `/usr/src/paperless/export`     | Pfad im Paperless-Container, in den exportiert wird |
| `MANAGE_PY_WORKDIR`        | `/usr/src/paperless/src`        | Arbeitsverzeichnis in Paperless (normalerweise nicht ändern) |
| `BACKUP_DIR`               | `/backup/paperless`             | Wohin die fertigen Backup-Dateien gespeichert werden |
| `BACKUP_KEEP_LAST`         | `7`                             | Wie viele Backups aufbewahrt werden (ältere werden gelöscht) |
| `BACKUP_USER`              | *(leer)*                        | Benutzername für den Passwortschutz |
| `BACKUP_PASS`              | *(leer)*                        | Passwort für den Passwortschutz |

---

## Häufige Probleme

**„Docker nicht erreichbar" in der Web-App**
→ Überprüfe, ob die Gruppen-ID in `docker-compose.yml` stimmt (Schritt 3).

**„Kein Paperless-Container gefunden"**
→ Stelle sicher, dass Paperless-ngx läuft (`docker ps` zeigt alle laufenden Container).
→ Du kannst auch `PAPERLESS_CONTAINER_NAME` mit dem genauen Container-Namen setzen.

**Die App startet, aber ich sehe HTTP 503**
→ Du hast `BACKUP_USER` gesetzt, aber `BACKUP_PASS` vergessen. Beide Felder müssen ausgefüllt sein.

**Ich komme nicht auf Port 8080**
→ Prüfe, ob eine Firewall den Port blockiert: `sudo ufw allow 8080` (bei UFW).
