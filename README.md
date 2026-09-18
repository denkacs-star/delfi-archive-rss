# delfi-archive-rss

Inoffizieller **RSS-Feed** der [archive.ph](https://archive.ph/)-Snapshot-Liste
von [rus.delfi.lv](https://rus.delfi.lv/).

archive.ph bietet keinen eigenen Feed für die Snapshot-Übersicht einer
Website. Dieses Repo baut sich den Feed selbst: Ein kleines Python-Skript
liest die Liste unter https://archive.ph/rus.delfi.lv aus (Titel,
Snapshot-Permalink, Snapshot-Datum, Original-Artikel-URL) und erzeugt daraus
ein RSS 2.0.

## 📡 Feed-Adresse

```
https://denkacs-star.github.io/delfi-archive-rss/feed.xml
```

Diese URL in einen beliebigen RSS-Reader (z. B. NetNewsWire, Feedly, Reeder,
Miniflux …) eintragen.

Übersichtsseite: https://denkacs-star.github.io/delfi-archive-rss/

## Wie es funktioniert

- `generate_feed.py` — Scraper + Feed-Generator (nur Python-Standardbibliothek,
  keine Abhängigkeiten). Schreibt `feed.xml` und `index.html` nach `docs/`.
- `docs/` — wird von GitHub Pages direkt aus dem `main`-Branch ausgeliefert
  (Pages-Quelle: Branch `main`, Ordner `/docs`).

**Kein GitHub-Actions-Workflow:** archive.ph blockt Anfragen aus
Cloud-/Rechenzentrums-IP-Bereichen (dazu zählen GitHub-Actions-Runner) mit
HTTP 429, dauerhaft und auch nach Retries. Der Abruf läuft deshalb **lokal**
auf einem Mac, per LaunchAgent einmal täglich:

- `lauf.sh` — ruft `generate_feed.py`, committet `docs/` bei Änderungen und
  pusht nach `main`. GitHub Pages published danach automatisch.
- LaunchAgent `de.denisskacs.delfi-archive-rss` (`~/Library/LaunchAgents/`)
  startet `lauf.sh` täglich um 9:20 Uhr. Log: `~/scripts/delfi-archive-rss/lauf.log`.

Jeder Feed-Eintrag ist ein neuer archive.ph-Snapshot: Titel, Link zum
Snapshot (`archive.ph/…`), Datum, sowie die Original-URL des Artikels auf
rus.delfi.lv im Beschreibungstext.

## Lokal ausführen

```bash
cd ~/scripts/delfi-archive-rss
./lauf.sh
```

## Einstellungen

Oben in `generate_feed.py`:

- `MAX_ITEMS` — Anzahl der Einträge im Feed (Standard 60)

Uhrzeit/Intervall: `StartCalendarInterval` in
`~/Library/LaunchAgents/de.denisskacs.delfi-archive-rss.plist`
(`launchctl unload/load` nach Änderungen).

---

Kein offizielles Angebot von archive.ph oder DELFI. Inhalte © jeweilige Rechteinhaber.
