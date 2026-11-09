# Funktionstest: einmalige Aufgaben

Diese Checkliste wurde für die einmaligen Aufgaben in Version 0.7.0 verwendet.
Bei künftigen Änderungen gilt weiterhin: Ein gemeldeter Fehler stoppt Merge und
Veröffentlichung, bis die Korrektur erneut geprüft und bestätigt ist.

Bestätigt wurden Anlegen, Abhaken und Reaktivieren auch für vergangene Termine,
zukünftige Kalendertermine, Terminschutz, Verschieben, Archivieren/Verwerfen,
Integrations-Reload und HA-Neustart. Das normale Browserprofil benötigte einmal
„Disable cache“ beim Neuladen, bevor „Einmalig“ erschien; im privaten Profil war
die Option sofort verfügbar. Weitere automatische Kartenupdates müssen in der
laufenden Installation weiter beobachtet werden.

## Installation des Teststands

1. Vorher ein Home-Assistant-Backup erstellen.
2. Den kompletten Ordner `custom_components/family_tasks` des zu prüfenden Stands nach
   `/config/custom_components/family_tasks` kopieren. Gespeicherte Aufgabendaten
   in `.storage` nicht verändern. Der Ordner enthält auch `frontend.py`.
3. Home Assistant neu starten und das Dashboard vollständig neu laden.
4. Die bestehende Ressourcen-URL `/family_tasks/family-tasks-card.js` beibehalten,
   ohne Versionszusatz. In der Aufgabenverwaltung muss „Einmalig“ erscheinen.
   Das prüft gleichzeitig den Kartenupdate-Pfad von 0.6.2. Falls die Auswahl erst
   nach Cache-Löschen oder einer URL-Änderung erscheint, dieses Ergebnis melden.

Für die native Aufgabenliste bei Bedarf eine Dashboard-Karte ergänzen:

```yaml
type: todo-list
entity: todo.family_tasks
```

Die tatsächlichen Entitätsnamen können abweichen. Sie stehen in der Integration
oder unter Entwicklerwerkzeuge → Zustände.

## Prüffälle

1. **Heute anlegen und zurücknehmen**
   Eine Aufgabe „TEST Einmalig heute“ für eine vorhandene Person anlegen.
   „Einmalig“ wählen und das heutige Datum ausdrücklich auswählen. Standard ist
   „Offen lassen“. Genau ein Eintrag muss in Verwaltung, Board und To-do stehen.
   Im Board abhaken: Der Eintrag bleibt sichtbar und in To-do erledigt. Wieder
   öffnen: Beide Ansichten zeigen ihn offen. Leer gelassenes Datum darf nicht
   gespeichert werden.

2. **Verschieben und zukünftigen Kalendertermin prüfen**
   Die offene Aufgabe bearbeiten und auf morgen verschieben. Sie muss sofort
   aus Board/To-do verschwinden, in Verwaltung und Kalender aber genau einmal
   für morgen stehen. Anschließend auf heute und dann auf gestern verschieben.
   Sie erscheint jeweils sofort, zuletzt mit Überfälligkeit. Optional im
   Katalogsensor die `once_instance_id` vor und nach dem Verschieben vergleichen:
   Sie muss unverändert sein.

3. **Geschützte Termine und Aufgabenart**
   Die Aufgabe erledigen und ihre Definition bearbeiten. Das Datum ist nicht
   mehr verschiebbar, der Titel darf geändert werden. Nach Rücknahme der
   Erledigung darf wieder verschoben werden. Ein Wechsel zwischen „Einmalig“
   und einer Wiederholung ist gesperrt; bei einer bestehenden wiederkehrenden
   Aufgabe darf „Einmalig“ ebenfalls nicht gewählt werden.

4. **Vergangene Fälligkeit und Verhalten**
   Drei weitere Testdefinitionen mit gestrigem Datum anlegen:
   - „Offen lassen“: genau ein überfälliger Eintrag im Board und in To-do.
   - „Archivieren“: Definition bleibt sichtbar, Instanz hat im Katalogstatus
     `missed`, kein aktueller Board-/To-do-Eintrag.
   - „Verwerfen“: Definition bleibt sichtbar, kein aktueller Eintrag und keine
     erzeugte historische Instanz.
   Eine bewusst gewählte Einstellung muss nach erneutem Bearbeiten erhalten
   bleiben. Auch eine offene Aufgabe beim Verschieben auf gestern mit
   „Archivieren“ beziehungsweise „Verwerfen“ prüfen: Das Verhalten gilt sofort.

5. **Reload und Neustart**
   Integration neu laden, eine weitere einmalige Aufgabe anlegen und bearbeiten.
   Danach Home Assistant neu starten. Definitionen, Termine und Status bleiben
   erhalten; keine doppelten Einträge oder Folgeaufgaben entstehen. Eine
   zukünftige Aufgabe bleibt bis zur Fälligkeit aus den aktuellen Ansichten.

6. **Mehrfachberührung, Löschen und bestehende Aufgaben**
   Beim Anlegen den Speichern-Button schnell zweimal betätigen: Der laufende
   Aufruf sperrt weitere Übermittlungen. Eine Testdefinition darf nur einmal
   entstehen. Bewusst getrennt angelegte gleichnamige Aufgaben bleiben erlaubt.
   Testdefinitionen löschen: Sie verschwinden aus den Ansichten; bereits
   gespeicherte Instanzen werden wie bisher historisch erhalten. Vorhandene
   wiederkehrende Aufgaben müssen weiterhin normal funktionieren.

7. **Tageswechsel**
   Falls möglich am Folgetag prüfen: Eine erledigte einmalige Aufgabe wird nicht
   erneut angelegt. Ihr heutiger Board-Eintrag verschwindet beim nächsten
   Fünf-Minuten-Lauf nach dem Tageswechsel. Lange Ausfallzeiten und weitere
   Datumsgrenzen werden zusätzlich automatisiert geprüft.

## Rückmeldung

Bitte die Prüffälle mit „bestanden“, „Fehler“ oder „noch offen“ zurückmelden.
Bei Fehlern den konkreten Schritt, erwartetes/tatsächliches Verhalten und neue
`family_tasks`-Meldungen aus Einstellungen → System → Protokolle angeben.
Keine persönlichen Aufgabendaten oder Zugangsdaten veröffentlichen.

Automatisierte Tests verwenden künstliche Daten. HTTP- und Edge-Tests prüfen
echte Anfragen und Browser-DOM, ersetzen aber die Home-Assistant-Anbindung durch
Test-Schnittstellen und den Service Worker durch ein Modell seiner Cache-Regeln.
Sie ersetzen diesen Test in der laufenden Installation nicht.
