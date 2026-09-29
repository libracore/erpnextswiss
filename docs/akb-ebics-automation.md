# AKB EBICS: sicherer Tagesabruf und enge automatische Buchung

Der Scheduler-Einstieg `erpnextswiss.erpnextswiss.ebics.sync` verwendet ab dieser
Version `ebics_automation`. Der alte `ebics Connection.get_transactions` darf
nicht als Tagesjob verwendet werden: Er quittiert vor der dauerhaften Ablage
und ruft einen Buchungspfad mit automatischem Differenzausgleich auf.

## Aktivierung

1. Bankseitige Freigabe, HPB und Schluesselaktivierung am konkreten Teilnehmer
   pruefen. Der Fingerabdruck der Bank-Authentifizierungs- und
   Verschluesselungsschluessel soll unabhaengig bestaetigt werden; eine bewusste
   Ausnahme ist gesondert zu dokumentieren.
2. In der **Site-Konfiguration**, nie im Repository, die exakten ERP-Bankkonten
   binden: `ebics_auto_accounts = {"version": 1, "bindings": {"<Connection-Name>":
   ["<CHF-Bankkonto>", "<EUR-Bankkonto>"]}}`. Fehlende, doppelte, deaktivierte
   oder fremde Konten blockieren den Abruf. Kein Konto wird aus einer Bankdatei
   als berechtigtes Ziel abgeleitet.
3. Ein Test auf dem isolierten Test-Site muss Migration, Download-Archiv,
   Bankquittung, Wiederanlauf, doppelte Transaktionen und mindestens je eine
   passende und unpassende Bankzeile abdecken. Die Tests duerfen keine echten
   Bank- oder Finanzdaten schreiben.
4. Produktionsbackup der Datenbank und des persistenten `sites`-Volumes pruefen.
   Erst danach `enable_sync` fuer die aktivierte H005/CH-Verbindung mit
   `statement_btf_version=08` setzen. Ein kontrollierter Einzelabruf und die
   Kontrolle der Buchungsbelege gehen dem unbeaufsichtigten Tageslauf voraus.

## Empfangs- und Buchungsgrenzen

- BTD/EOP/CH/ZIP/camt.053.001.08, maximal 14 vergangene Tage pro Lauf und
  initial hoechstens die letzten sieben Tage. Leere Banktage werden trotz
  Cursor-Fortschritt innerhalb eines rollierenden Sieben-Tage-Fensters erneut
  abgefragt, falls die Bank einen Auszug verspaetet bereitstellt. Bereits
  quittierte Tage werden anhand des Archivs uebersprungen.
- Vom Python-SDK gelieferte XML-Inhalte werden als UTF-8 in einem
  `EBICS Download`-Datensatz gespeichert. Das JSON-Envelope und sein SHA-256
  werden nach einem ERP-Commit rueckgelesen. Erst dann geht die EBICS-Quittung
  an die Bank. Der SDK-seitig entpackte XML-Inhalt ist erhalten; dessen urspruengliche
  Bytekodierung und das urspruengliche
  Bank-ZIP ist **nicht** Teil dieses Legacy-SDK-Pfads. Der gesonderte PHP-Gateway
  bleibt fuer den bytegenauen Original-ZIP-Empfang das langfristige Ziel.
- Ein offener Bank-Receipt wird vor einem neuen Download erneut quittiert.
  Scheitert der Receipt oder ist dessen Zustand unklar, erfolgt kein zweiter
  automatischer Abruf. Datensaetze mit `ack_state=Pending` erfordern Sichtung.
- Vor der Quittung werden **alle** XML-Dateien gegen das vorhandene camt-Schema
  und die explizit gebundenen Konten geprueft. Ungueltige oder uebergrosse
  Dateien werden nicht positiv quittiert.
- Eine Zahlung wird nur fuer einen einzelnen, gebuchten, nicht stornierten
  Bankeintrag mit stimmiger Auszugsbilanz, einem Kandidaten, einer eingereichten
  Rechnung derselben Firma/Partei/Waehrung und exakt gleichem offenen Betrag
  gebucht. Die Bankreferenz und Rechnungsreferenz muessen nachweisbar passen.
  Es gibt keinen automatischen Kurs-/Rundungs-Differenzausgleich. Sammelbuchungen,
  Spesen, Lohn, mehrdeutige Treffer und alle Fehler bleiben zur Pruefung.
- Es wird **kein** pain.001 versandt und kein Zahlungsvorschlag freigegeben.

## Betrieb und Ruecknahme

`EBICS Download` zeigt Empfangs-, Quittungs- und Buchungsstatus sowie die Anzahl
automatischer Buchungen und Prueffaelle. Fehlerlogs enthalten nur Fehlertypen,
keine Banknutzdaten. Bei Problemen zuerst `enable_sync=0` setzen. Archivierte
Bankdaten und bereits gebuchte `Payment Entry` bleiben bestehen und duerfen
nicht durch ein Code-Rollback automatisch geloescht oder storniert werden.
Unquittierte Downloads und unklare Buchungsbelege sind fachlich einzeln zu
pruefen, bevor der Tageslauf wieder aktiviert wird.
