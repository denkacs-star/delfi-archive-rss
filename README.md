# delfi-archive-rss

Inoffizieller **RSS-Feed** der [archive.ph](https://archive.ph/)-Snapshot-Liste
von [rus.delfi.lv](https://rus.delfi.lv/).

archive.ph bietet keinen eigenen Feed für die Snapshot-Übersicht einer
Website. Dieses Repo baut sich den Feed selbst: Ein kleines Python-Skript
liest die Liste unter https://archive.ph/rus.delfi.lv aus (Titel,
Snapshot-Permalink, Snapshot-Datum, Original-Artikel-URL) und erzeugt daraus
ein RSS 2.0. Eine GitHub Action läuft **täglich** und veröffentlicht das
Ergebnis über GitHub Pages.

## 📡 Feed-Adresse

```
https://denkacs-star.github.io/delfi-archive-rss/feed.xml
```

Diese URL in einen beliebigen RSS-Reader (z. B. NetNewsWire, Feedly, Reeder,
Miniflux …) eintragen.

Übersichtsseite: https://denkacs-star.github.io/delfi-archive-rss/

## Wie es funktioniert

- `generate_feed.py` — Scraper + Feed-Generator (nur Python-Standardbibliothek,
  keine Abhängigkeiten). Schreibt `feed.xml` und `index.html` in einen
  Ausgabeordner (Standard: `public/`).
- `.github/workflows/build.yml` — baut den Feed täglich um ~07:15 UTC und
  deployt ihn nach GitHub Pages. Lässt sich in den Actions manuell per
  „Run workflow" auslösen.

Jeder Feed-Eintrag ist ein neuer archive.ph-Snapshot: Titel, Link zum
Snapshot (`archive.ph/…`), Datum, sowie die Original-URL des Artikels auf
rus.delfi.lv im Beschreibungstext.

## Lokal ausführen

```bash
python3 generate_feed.py public
open public/feed.xml
```

## Einstellungen

Oben in `generate_feed.py`:

- `MAX_ITEMS` — Anzahl der Einträge im Feed (Standard 60)

Update-Intervall: `cron` in `.github/workflows/build.yml`.

## Bekannte Einschränkung

archive.ph blockt gelegentlich automatisierte Anfragen aus Cloud-/Rechenzentrums-
IP-Bereichen (dazu zählen auch GitHub-Actions-Runner) mit einer Sicherheits-
abfrage. Schlägt der tägliche Lauf deswegen fehl, bricht das Skript mit
Fehlercode ab und der zuletzt veröffentlichte Feed bleibt unverändert online
— es wird nichts kaputt deployt. Bei dauerhaften Fehlschlägen ggf. Cron-Zeit
anpassen oder Workflow manuell/aus anderem Netz laufen lassen.

---

Kein offizielles Angebot von archive.ph oder DELFI. Inhalte © jeweilige Rechteinhaber.
