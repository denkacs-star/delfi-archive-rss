# delfi-archive-rss

Inoffizieller **RSS-Feed** der [archive.ph](https://archive.ph/)-Snapshot-Liste
von [rus.delfi.lv](https://rus.delfi.lv/).

archive.ph bietet keinen eigenen Feed für die Snapshot-Übersicht einer
Website. Dieses Repo baut sich den Feed selbst: Ein kleines Python-Skript
liest die Liste unter https://archive.ph/rus.delfi.lv aus (Titel,
Snapshot-Permalink, Snapshot-Datum, Original-Artikel-URL), lädt dann jeden
neuen Snapshot einmal einzeln nach und extrahiert mit
[trafilatura](https://github.com/adbar/trafilatura) den vollständigen
Artikeltext für `content:encoded`. Ergebnis: RSS 2.0 mit Volltext, nicht nur
Titel/Link.

## 📡 Feed-Adresse

```
https://denkacs-star.github.io/delfi-archive-rss/feed.xml
```

Diese URL in einen beliebigen RSS-Reader (z. B. NetNewsWire, Feedly, Reeder,
Miniflux …) eintragen.

Übersichtsseite: https://denkacs-star.github.io/delfi-archive-rss/

## Wie es funktioniert

- `generate_feed.py` — Scraper + Volltext-Extraktion + Feed-Generator
  (braucht `trafilatura`/`lxml`, siehe `requirements.txt` und `venv/`).
  Schreibt `feed.xml` und `index.html` nach `docs/`.
- `cache.json` — Volltext-Cache pro Snapshot-Link. Jeder Snapshot wird nur
  **einmal** abgerufen (Snapshots ändern sich nicht mehr); spart Requests
  gegen das ohnehin strenge Rate-Limit von archive.ph. Transiente
  Fetch-Fehler (z. B. 502) werden nicht gecacht und beim nächsten Lauf
  automatisch erneut versucht.
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

Jeder Feed-Eintrag ist ein neuer archive.ph-Snapshot: Titel, Autor (falls
erkannt), Link zum Snapshot (`archive.ph/…`), Datum, ein Teaser als
`<description>` und der volle Artikeltext als `<content:encoded>`
(Original-URL steht zusätzlich am Ende des Volltexts und in `<comments>`).
Lässt sich ein Snapshot nicht extrahieren (z. B. reine Foto-Galerien ohne
Fließtext), fällt der Eintrag auf einen kurzen Hinweistext zurück.

## Lokal ausführen

```bash
cd ~/scripts/delfi-archive-rss
./venv/bin/pip install -r requirements.txt  # einmalig, falls venv/ fehlt
./lauf.sh
```

## Einstellungen

Oben in `generate_feed.py`:

- `MAX_ITEMS` — Anzahl der Einträge im Feed (Standard 60)
- `EXCERPT_LEN` — Länge des Teasers in `<description>` (Standard 400 Zeichen)
- `SNAPSHOT_FETCH_DELAY` — Pause zwischen Snapshot-Abrufen (Standard 4s)

Uhrzeit/Intervall: `StartCalendarInterval` in
`~/Library/LaunchAgents/de.denisskacs.delfi-archive-rss.plist`
(`launchctl unload/load` nach Änderungen).

---

Kein offizielles Angebot von archive.ph oder DELFI. Inhalte © jeweilige Rechteinhaber.
