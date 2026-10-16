# Chemie-Werkzeuge für den Unterricht

Interaktive Seiten für den Chemie-/NTG-Unterricht: Teilchenmodell, Geschichte der
Atommodelle, Elektronen und Energiestufen. Jede Seite
ist eine einzelne, selbstständige HTML-Datei auf GitHub Pages — keine externen
Anfragen, auch Schriften sind eingebettet.

| Datei | Inhalt | Entstehung |
|---|---|---|
| `index.html` | Startseite mit Links zu den Werkzeugen | von Hand |
| `timeline.html` | Zeitleiste der Atommodelle (Dalton 1808 bis Kernschalenmodell 1949/50) | **generiert** aus `content/` + `template/` |
| `rutherford.html` | Rutherford gegen das Spektrum (Vorhersage, Experiment, Erklärung; H, Na, Sr, Ba) | von Hand |
| `fuellen.html` | Elektronen einfüllen (Energiestufen, 2n², Atome und Ionen H bis Ca) | von Hand |
| `ionisierung.html` | Ionisierungsenergie (Klickspiel, Na, Mg, Al, K, Ca) | von Hand |
| `diagramm.html` | Energiestufendiagramm (Baukasten und Test) | von Hand |
| `pse.html` | Klickbares Periodensystem | von Hand |
| `modelle.html` | Atommodelle im Vergleich (Dalton bis Schrödinger, H bis Ar, 2D und 3D) | von Hand |
| `aggregatzustaende.html` | Aggregatzustände: 2D-Teilchenmodell im Zylinder mit Stempel, Schieberegler für Temperatur (°C) und Druck (bar), erkannter Zustand und Beobachtungstabelle, Geschwindigkeitsfarben | von Hand |
| `diffusion.html` | Diffusion: blaue und gelbe Lösung im Standzylinder (Stoffebene) und drei Lupen mit Brownscher Teilchenbewegung (Teilchenebene), drei Temperaturen, Zeitraffer | von Hand |
| `vanthoff.html` | Van ’t Hoff: Isomere zählen. H durch Cl, Br, F ersetzen an Quadrat, Pyramide und Tetraeder; erkennt gleiche (gedrehte) Moleküle und Spiegelbilder; Tabelle mit dem Experiment | von Hand |
| `vsepr.html` | Elektronenpaarabstoßung: CH₄, NH₃, H₂O, Winkel einstellen, berechnete Energie (Psi4 MP2/aug-cc-pVTZ), lokalisierte Elektronenpaare beim stabilsten Winkel | von Hand + Daten |
| `polaritaet.html` | Moleküle im elektrischen Feld: Kasten mit geladenen Platten links und rechts, neun Stoffe (H₂O, HCl, NH₃, CO₂, CH₄, H₂, Cl₂, N₂, O₂), Dipolpfeile, Teilladungen, Anziehung zwischen den Molekülen | von Hand |
| `elektronenwolken.html` | Elektronenwolken der neun Stoffe aus „Moleküle im elektrischen Feld“ in 3D (WebGL): Hülle mit Ladungsfarben oder Punktwolke, Größe der Wolke, Atome, δ+/δ−, Dipolpfeil | von Hand + Daten |
| `london.html` | London-Kräfte: Drude-Modell schwankender Elektronenwolken (zwei Teilchen, Gleichtakt) und viele Teilchen von Edelgasen und Alkanen bei wählbarer Temperatur | von Hand |
| `wasser.html` | Wasser: Tropfen und Eis. 2D-Wassermodell (Mercedes-Benz-Modell): Tropfen mit Oberflächenspannung, Gefrieren an einer kalten Fläche mit Kolben (Eis braucht mehr Platz) | von Hand |
| `eis.html` | Eis und Wasser in 3D: hexagonales Eis (Eisregeln) und flüssiges Wasser (OpenMM TIP4P-Ew) im gleichen Kasten, Wasserstoffbrücken, Dichte | von Hand + Daten |
| `protonen.html` | Protonenübergang: HCl + H₂O (Nahaufnahme in Schritten), HCl in Wasser mit Grotthuss-Mechanismus, viele Teilchen im Kasten; 3D-Kugel-Stab-Modell, Wasserstoffbrücken und Valenzstrichformeln zuschaltbar | von Hand + Engine |
| `ammoniak.html` | Ammoniak in Wasser: NH₃ + H₂O (Nahaufnahme mit Rückreaktion), NH₃ in Wasser (Gleichgewicht), viele Teilchen mit Universalindikator | von Hand + Engine |
| `neutralisation.html` | Neutralisation: HCl trifft NaOH (wenige Teilchen), viele Teilchen mit HCl- und NaOH-Knopf und Universalindikator | von Hand + Engine |
| `quellen.html` | Quellen und Danksagung | von Hand |
| `impressum.html` | Impressum, Haftungsausschluss, Lizenz, Einbetten | von Hand |
| `datenschutz.html` | Datenschutz (keine Cookies, kein Tracking, Hosting GitHub Pages) | von Hand |

## Seitenmenü

Das Menü (links, auf dem Handy oben mit „Menü“-Knopf) steht **an einer Stelle**:
`template/site/nav.html` (Einträge, nach Themen gruppiert) und
`template/site/nav.css` (Aussehen). `python3 build.py` kopiert beides in jede
Seite und ins Timeline-Template und markiert dort die eigene Seite. Den
Menüblock in den Seiten (`<!--SITENAV-->…<!--/SITENAV-->`) nicht von Hand
bearbeiten.

Neue Seite: Eintrag in `template/site/nav.html` ergänzen, `python3 build.py`
ausführen, außerdem eine Karte in der passenden Themengruppe von `index.html`.

## Elektronenwolken-Daten

`elektronenwolken.html` enthält die berechnete Elektronendichte und das
elektrostatische Potential der Moleküle. Sie stehen in
`template/site/wolken-data.js` (erzeugt von `scripts/esp/export_web.py` aus
Psi4-Rechnungen) und werden von `python3 build.py` zwischen die Marken
`/*__WOLKEN__*/` und `/*__/WOLKEN__*/` kopiert. Neue Rechnung: siehe
`scripts/README.md`.

## Teilchen-Engine (Säuren und Basen)

`protonen.html`, `ammoniak.html` und `neutralisation.html` nutzen dieselbe Simulation:
`template/site/teilchen.js` (Teilchenmodell, Protonenübergänge, Zeichnen,
Bedienung). `python3 build.py` kopiert sie zwischen die Marken
`/*__TEILCHEN__*/` und `/*__/TEILCHEN__*/` in jede dieser Seiten. Änderungen an
der Simulation also in `template/site/teilchen.js` machen, nicht in den Seiten;
die Seiten selbst enthalten nur ihre Szenen, Formeln und Texte (nach der
Endmarke).

## Rechenskripte

`scripts/` enthält Psi4- und OpenMM-Skripte für Unterrichtsmaterial
(Elektronendichte und elektrostatisches Potential, Dipol-Dipol-Anziehung,
Protonenübergang). Sie gehören nicht zu den Seiten; Ergebnisse landen in
`results/` und werden nicht eingecheckt. Details in `scripts/README.md`.

## Schrift

Alle Seiten nutzen Source Sans 3 (SIL Open Font License), als variable
woff2-Schrift (normal und kursiv) direkt im `<style>` eingebettet.

**Wichtig: `timeline.html` wird nicht von Hand bearbeitet.** Sie wird aus den
Dateien in `content/` und `template/index.template.html` von `build.py`
erzeugt. Jede Änderung an `timeline.html` selbst geht beim nächsten Build
verloren.

## Workflow

1. Eine Datei unter `content/` (oder das Menü unter `template/site/`) bearbeiten (siehe unten, welche Datei was
   enthält).
2. `python3 build.py` ausführen.
3. Bei Fehlern: Die Meldung nennt genau die Datei und das Feld. Beheben,
   erneut ausführen.
4. Bei Erfolg wird `timeline.html` neu geschrieben. `timeline.html` im Browser
   öffnen und prüfen.
5. Änderungen committen und pushen (`content/`, `template/` und die neue
   `timeline.html` gehören zusammen in einen Commit).

Ein GitHub Action-Workflow (`.github/workflows/build.yml`) führt `build.py`
zusätzlich bei jedem Push automatisch aus und committet eine aktualisierte
`timeline.html`, falls man das selbst vergisst — der lokale Lauf vorher bleibt
aber der schnellere Weg, um Fehler sofort zu sehen.

## Ordnerstruktur

```
content/
  events/*.md       — ein Ereignis, Experiment, Modell oder Hinweis je Datei
  questions/*.md     — eine offene Frage je Datei
  models/*.md        — der vertiefte "Wissensstand"-Block zu einem Modell
  tools.md            — Werkzeugkasten-Tabelle (ein Eintrag je Zeile)
  eras.md             — Modellepochen-Tabelle
  ideas.md            — Ideen-Tabelle für die Challenge-Aufgabe
template/
  index.template.html — HTML/CSS/JS-Gerüst mit Platzhaltern wie /*__NODES__*/
build.py              — validiert content/ und erzeugt timeline.html
timeline.html         — generiert, wird von GitHub Pages ausgeliefert
```

## Frontmatter-Felder

Jede Datei unter `content/events`, `content/questions` und `content/models`
beginnt mit einem Frontmatter-Block zwischen `---`-Zeilen. Zeichenketten
immer in doppelten Anführungszeichen, Listen als `- "eintrag"`-Zeilen.

### `content/events/<jahr>-<id>.md`

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `id` | ja | eindeutige Kennung, wird in `bezug`/`beantwortet_durch` referenziert |
| `jahr` | ja | Jahr (1785–1950) |
| `spur` | ja | `M` Modelle, `E` Atome/Elektronen, `S` Spektroskopie/Massen, `R` Radioaktivität/Kern, `C` Chemie, `P` Treffen |
| `art` | ja | `modell` \| `entdeckung` \| `hinweis` \| `treffen` |
| `kurz` | ja | kurzer Titel für den Zeitleisten-Chip |
| `personen` | ja | Urheber:in(nen) |
| `voraussetzungen` | nein | Liste: was dafür an Technik/Wissen nötig war |
| `bezug` | nein | Liste von `id`s verwandter Ereignisse |
| `lehrplan` | nein | `k` (Kernstoff) oder `p` (Profilbereich) — nur setzen, wenn `lehrplan_text` mitgegeben wird |
| `lehrplan_text` | mit `lehrplan` | Satz, der den LehrplanPLUS-Bezug nennt |
| `geprüft` | ja (Wert kann `null` sein) | `null` solange ungeprüft, sonst Datum `"JJJJ-MM-TT"` |

Darunter, nach der zweiten `---`-Zeile, der Fließtext (wird im Dialog
angezeigt).

### `content/questions/<von>-<id>.md`

`id`, `von`, `bis`, `kurz`, `beantwortet_durch` (die `id` des klärenden
Ereignisses), optional `lehrplan`/`lehrplan_text`, `geprüft`. Fließtext
darunter.

### `content/models/<jahr>-<id>.md`

`id` muss zu einem Ereignis mit `art: modell` in `content/events/` passen.
`verdict`, `resolved` (Liste von `id`s, die das Modell später ablösen),
optional `hinweis_titel`, `konkurrenz` (Liste), `geprüft`.

Body in festen Abschnitten:

```markdown
## Das wusste man
- Aufzählung

## Was das Modell gut konnte
Ein Absatz Fließtext.

## Fragen, die man noch nicht stellen konnte
- Aufzählung

## Voraussetzungen für ein besseres Modell
| Nötig für das bessere Modell | Setzt voraus | Zeitraum | Jahr |
|---|---|---|---|
| ... | ... | ... | 1912 |

## <hinweis_titel>      (optional, freier Titel)
Ein Absatz.

## Konkurrenz im selben Jahr      (optional, nur mit `konkurrenz`)
Ein Absatz.
```

### `tools.md`, `eras.md`, `ideas.md`

Jeweils nur ein `geprüft`-Feld im Frontmatter (für die ganze Tabelle) plus
eine Markdown-Tabelle mit fester Spaltenzahl — siehe die vorhandenen
Dateien als Vorlage. Zeilen einfach ergänzen, löschen oder umsortieren.

## Geprüft-Status ("✓"-Abzeichen)

`geprüft` ist entweder `null` (noch nicht von Sergio inhaltlich
gegengelesen) oder ein Datum wie `"2026-03-01"`. Die Seite zeigt das als
Abzeichen in jedem Dialog, als kleinen Punkt auf noch ungeprüften Chips/
Balken in der Zeitleiste, und als Zähler "N / Gesamt" über der Zeitleiste.
Der Schalter "Nur ungeprüfte anzeigen" blendet alles andere aus — praktisch,
um gezielt durch die Restarbeit zu gehen. Ein Modell-Block in
`content/models/` hat sein eigenes `geprüft`-Feld, unabhängig vom
`geprüft`-Feld des zugehörigen Ereignisses (die Kurzfassung in der
Zeitleiste und der vertiefte Wissensstand-Block können unterschiedlich weit
geprüft sein).

## Validierung durch `build.py`

Vor dem Schreiben von `timeline.html` prüft `build.py`:

- alle Pflichtfelder sind gesetzt,
- `id`s sind eindeutig (über Ereignisse, Fragen und Modelle hinweg so weit
  relevant),
- jede Referenz (`bezug`, `beantwortet_durch`, `resolved`, `konkurrenz`)
  zeigt auf eine tatsächlich existierende `id`,
- Jahre liegen zwischen 1785 und 1950,
- `lehrplan` ist, falls gesetzt, `k` oder `p` und hat einen `lehrplan_text`,
- der Modell-Body hat alle vier Pflichtabschnitte.

Jeder Fehler nennt die betroffene Datei und das Feld. Bei einem Fehler wird
`timeline.html` nicht überschrieben — die zuletzt funktionierende Version
bleibt online, bis der Fehler behoben ist.

## Offen / nächste Schritte

- Werkzeugkasten (`content/tools.md`) ist bisher nur die Tabelle aus der
  ursprünglichen Fassung; eine inhaltliche Erweiterung (z. B. je Werkzeug
  ein Satz zu Leistungsfähigkeit/Grenzen, Verlinkung zu den Ereignissen,
  die es benutzen) ist angedacht, aber noch nicht umgesetzt.
- `geprüft` ist für alle Inhalte aktuell `null` — die Review-Arbeit selbst
  steht noch aus.

## Lizenz

© 2026 Dr. Sergio Vargas, biodatum.io. Seiten, Texte, Abbildungen, Quellcode
und Daten stehen unter [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de)
(Namensnennung – Nicht kommerziell – Weitergabe unter gleichen Bedingungen),
vollständiger Text in `LICENSE`. Zur Namensnennung gehört verbindlich der
Verweis auf https://atoms.biodatum.io: „Chemie-Werkzeuge für den Unterricht“,
Dr. Sergio Vargas, biodatum.io, https://atoms.biodatum.io, CC BY-NC-SA 4.0.
Kommerzielle Nutzung nur mit gesonderter
Lizenz: info@biodatum.io. Ausgenommen ist die eingebettete Schrift Source
Sans 3 (SIL Open Font License 1.1). Die Inhalte werden ohne Gewähr
bereitgestellt; siehe `impressum.html` (Haftungsausschluss) und
`datenschutz.html`.

## Mitmachen

Fehler und Wünsche bitte als Issue melden:
https://github.com/SergioVargasRamirez/atoms/issues. Verbesserungen gern als
Pull Request. Ohne GitHub-Konto: info@biodatum.io.

Die Seiten dürfen nicht in andere Webseiten eingebettet werden. GitHub Pages
kann keine HTTP-Header wie `X-Frame-Options` setzen; deshalb blendet ein
Skript im Seitenmenü (`template/site/nav.html`) die Seite in fremden Rahmen
aus und zeigt nur einen Link.
