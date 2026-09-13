# KT Banking: verbindliche Erweiterung des Plattformziels

Stand: 13.09.2026. Auftrag: Bankanbindung anhand des Banking-Briefings verbessern,
updatefest innerhalb der vorhandenen Swiss-App. Bestehenden Zahlungsabgleich und
bestehende Zahlungsvorschlaege integrieren, nicht neu entwickeln.
**Status: Spezifikation, lesendes Laufzeitinventar und offline getesteter
Empfangskern; keine aktivierte Bankanbindung.**

## Quelle und Vorrang

Verbindliche fachliche Quelle ist das vom Auftraggeber bereitgestellte
`KT_Banking_Projektplan_Entwicklerbriefing.md`, Version 1.0 vom 12.09.2026.
Original-SHA-256:
`6a2c05a18ccfc91be43f2487bcc6a32a5963cd222aefde6e7aafc509d45caebb`.
Die interne Originaldatei wird nicht in dieses oeffentliche Repository kopiert.
Die folgende Zuordnung dokumentiert den durch die nachstehenden Nutzeranweisungen
eingegrenzten Entwicklungsumfang, ohne interne Kontoidentitaeten, Bankzugangsdaten
oder Geheimnisse zu publizieren. Neuere Nutzeranweisungen haben Vorrang vor dem
urspruenglichen Briefing und frueheren Planformulierungen.

Die anschliessende Nutzeranweisung ersetzt den vorgeschlagenen neuen App-Namen:
Integration in die vorhandene Swiss-App ist die Entwicklungsrichtung. Das lokale
Codeinventar identifiziert diese als `erpnextswiss`, Titel `Schweizer Buchhaltung`,
mit vorhandenem Arbeitsbereich `Zahlungsverkehr`. Kein zweites Hauptbuch, Login
oder paralleles Zahlungsprodukt anlegen. Neue Banking-Module innerhalb dieser
App kapseln; den PHP-Gateway als separat baubaren internen Dienst betreiben.
Neue API-Pfade werden im Schema-PR verbindlich festgelegt, nicht als bereits
existierende `kt_banking.api.v1`-Endpunkte ausgegeben. Bestehende Pfade bleiben
kompatibel. Zusaetzliche Banking-DocTypes nur fuer fehlende Herkunfts- und
Pruefnachweise neben den fuehrenden nativen ERPNext-Objekten einfuehren.

### Verbindliche Umfangskorrektur: Bestehendes anbinden

Der Auftraggeber hat anschliessend ausdruecklich klargestellt: **Zahlungsabgleich
und Zahlungsvorschlaege gibt es bereits. Nur die Bankanbindung perfektionieren.**
Diese Funktionen sind Bestand, keine noch zu entwickelnden Banking-Funktionen.

- Bestehende Abgleichverfahren, Payment Proposals, Zahlungs-/Exportlogik, Belege,
  Freigaben, Rechte und Oberflaechen wiederverwenden und erhalten.
- Umfang ist die zuverlaessige Bankverbindung: Einrichtung, Transport, sicherer
  Dateiempfang, Formatkompatibilitaet, Importuebergabe, Dublettenschutz, Status,
  Fehlerbehandlung, Wiederanlauf, Betrieb und nachgewiesene Integration.
- Vor jedem Adapter zuerst bestehende Einstiegspunkte und Tests inventarisieren.
  Nur eine belegte Luecke an der Bankanbindung rechtfertigt eine enge Erweiterung;
  kein paralleler Parser, Abgleichmotor, Zahlungsvorschlagsprozess oder Desk.
- BK-09/10/11/15 sind Integrations- und Regressionspruefungen vorhandener Funktionen,
  keine Neuentwicklungsauftraege. Neue APIs, DocTypes oder Anzeigen nur bei einer
  nachgewiesenen Integrationsluecke; ein eigener FAC-/KI-Ausbau ist kein Muss.
- Spaeterer bankseitiger Zahlungsversand bleibt ein separat freizugebender Adapter
  fuer die vorhandenen Zahlungsvorschlaege. Keine neue Zahlungsverwaltung und
  keine Bankaktion allein durch diesen Plan. Der erste Leseanschluss wird nicht
  durch fehlende Freigabe dieser optionalen Versandstufe als unfertig behandelt.

Die bisherigen **14 Plattformpakete bleiben vollstaendig offen beziehungsweise
mit ihren belegten Teilstaenden erhalten**. Banking ersetzt keines dieser Pakete.
Kein Funktions- oder Layoutverlust. Kein KI-Assistent/MCP-Chat in Android.
Kein Bankdatenzugriff fuer Kundenportal, Planer, Partner oder Techniker-App.
Neue Bankkommunikation ist durch die Planaufnahme nicht freigegeben.

## Releasegrenzen

- **1.0:** bestaetigtes AKB-H005-Profil, Einrichtung, camt.053.001.08 und
  camt.054.001.08, Originalarchiv, CHF/EUR, Salden, sichere Imports mit
  Uebergabe an den vorhandenen Bankabgleich. Bestehenden geeigneten Parser fuer
  manuelle Dateien und Gateway-Dateien wiederverwenden und gezielt ergaenzen.
  Gegenueber der Bank nur lesend; kontrollierte ERP-Importdatensaetze und Bank
  Transactions sind erlaubt. Keine autonome Hauptbuchbuchung, eingereichte
  Payment Entry oder Zahlungsuebermittlung. Bestehende Zahlungsbelege zuerst
  abgleichen; fehlende Zahlungen hoechstens in explizit freigegebenen Entwuerfen.
- **1.1:** camt.052.001.08 separat pruefen. Zunaechst Anzeige/Anreicherung;
  vorgemerkt und gebucht trennen, keine zweite Bank-Transaction-Erfassung.
- **2.0 (separat freizugebende Anschlussstufe):** vorhandenes Payment Proposal, validierte
  pain.001.001.09, BTU mit bestaetigtem T-Recht, pain.002.001.10, getrennte
  menschliche Bank-/VEU-Freigabe. Keine KI-Zahlung, kein eigener Signaturersatz,
  kein automatisch aktivierter Lohnversand. Transport, Verarbeitung, Bankfreigabe,
  Ausfuehrung und Abgleich bleiben getrennte Statusdimensionen.

Die Bankparameter und regulatorischen/Formatangaben des Briefings sind vor
Implementierung/Pilot an den aktuellen primaeren Quellen und bei der AKB zu
bestaetigen. Keine frei erfundenen Produktions- oder Sandbox-Endpunkte.

Zu bestaetigendes Profil aus dem Briefing, **keine bereits aktive Verbindung**:

| Nachricht | Richtung | Service | Scope | Container | BTF-Version |
|---|---|---|---|---|---|
| camt.053.001.08 | BTD | EOP | CH | ZIP | 08 |
| camt.054.001.08 | BTD | REP | CH | ZIP | 08 |
| camt.052.001.08, 1.1 | BTD | STM | CH | ZIP | 08 |
| pain.001.001.09, 2.0 | BTU | MCT | CH | keiner | 09 |
| pain.002.001.10, 2.0 | BTD | PSR | CH | ZIP | 10 |

H005/EBICS 3.0, geplantes A006 und bankbestaetigte X002/E002-/Schluesselparameter
gegen AKB-Unterlagen verifizieren. Der im Briefing gelesene PHP-Client `3.x` /
Composer-Version `3.2.1` mit PHP `^8.5` ist kein unabhaengiger Release-Nachweis;
erst ein tatsaechlich verfuegbarer, getesteter Tag/Commit wird Buildgrundlage.
Primaerquellen fuer die nachfolgende Verifikation: AKB EBICS-/Roadmap-Seiten,
AKB `ebics-3.0-umstellung.pdf` und `ebics-api/ebics-client-php` inklusive LICENSE,
Composer-Lock und Storage-Callback-Changelog. Keine Premium-Produktabhaengigkeit.

## Erstes BK-01-Codeinventar

Gepruefter unveraenderter Basiscommit: `e102c3279394aaf5e54bad8a29700f4bf8940f2d`.
Die fremden/uncommitted Aenderungen im Hauptcheckout werden weder uebernommen
noch verworfen. Das nachfolgende Laufzeitinventar ergaenzt diese Quellpruefung;
ein vollstaendiger personenbezogener Kontorechte-/Seiteneffekttest bleibt offen.

| Befund im vorhandenen Code | Konsequenz fuer die Integration |
|---|---|
| `hooks.py`: vorhandene Swiss-App, Sidebar und taeglicher `ebics.sync`-Job | Wiederverwenden; pro Konto genau einen automatischen Transportbesitzer nachweisen |
| `pyproject.toml` und `ebics_connection.py`: vorhandener fintech-Transport | Nicht als kostenfreien neuen Gateway ausgeben; Lizenz/Bestandsnutzung separat inventarisieren |
| `ebicsConnection.get_transactions`: `confirm_download()` vor `stmt.insert()` und ERP-Commit | Neuer Gateway muss dauerhafte Speicherung vor positiver Bankquittung beweisen |
| Derselbe Pfad loescht Statements ohne Transaktionen | Neue Saldo-/Auszugsverarbeitung muss leere Auszuege mit Salden behalten |
| Derselbe Pfad ruft `stmt.process_transactions()` auf | Kein Aufruf aus dem neuen Release-1-Import |
| `ebicsStatement.process_transactions`: `auto_submit: 1` fuer Zahlungsbelege | Realer Nebenwirkungstest auf Gesamtinstallation, nicht nur auf neuem Parser |
| `ebicsStatement.parse_content`: erster passender Account, interpolierter SQL-Ausdruck und eigene Dublettenabfrage | Explizites kontorechtegebundenes Mapping, strukturierte Abfragen und neuer Dublettenvertrag erforderlich |
| Vorhandener Zahlungsabgleich und vorhandene Payment Proposals samt Zahlungs-/Importfunktionen | Bestand, nicht neu entwickeln; Bankadapter daran anbinden, Ausweichweg, Stichtag und Konflikterkennung dokumentieren |
| Vorhandene App-Lizenz AGPL | Lizenzhinweise beibehalten; MIT-Bibliothek macht die Gesamt-App nicht automatisch MIT |

Diese Befunde sind Quellcodebeobachtungen, kein Nachweis aktiver Bankverbindungen,
erfolgter Fehlbuchungen oder aktueller Produktiv-Hooks. Kein Bankabruf wurde gestartet.

### Vorhandene Uebergabepunkte: keine Neuentwicklung

Weiteres lesendes Inventar am selben Basiscommit; keine Ausfuehrung einer der
nachfolgenden Finanz- oder Bankmethoden. Pfade sind relativ zum Repository.

| Bestand | Konkreter Einstieg | Bedeutung fuer den Bankanschluss |
|---|---|---|
| Bank-Wizard samt Vorschau | `erpnextswiss/erpnextswiss/page/bank_wizard/bank_wizard.py`: `read_camt053_meta`, `read_camt053`, `read_camt_transactions`, `render_transactions` | Bereits vorhandene Auszugs-/Vorschlagsaufbereitung und Oberflaeche pruefen und anbinden; keine zweite Abgleichseite |
| Manueller Bankimport, Vorlagen und camt.053/054 | `erpnextswiss/erpnextswiss/page/bankimport/bankimport.py`: `parse_file`, `parse_by_template`, `read_camt053`, `read_camt054` | Rueckfallweg erhalten; vor Wiederverwendung Parser und buchende Seiteneffekte trennen, `auto_submit=False` allein ist kein Nachweis eines schreibfreien Parsers |
| Zahlungsabgleich | `erpnextswiss/erpnextswiss/page/match_payments/match_payments.py`: `match`, `auto_match`, `submit`, `submit_all` | Bestehende Zuordnungs-/Freigabeschritte erhalten; neue Bankdaten daran beziehungsweise an den eingesetzten nativen Abgleich uebergeben, nicht erneut implementieren |
| Zahlungsvorschlaege | `erpnextswiss/erpnextswiss/doctype/payment_proposal/payment_proposal.py`: `create_payment_proposal`, `PaymentProposal.create_bank_file` | Vorhandene Vorschlaege und Export bleiben fuehrend. Der Export liefert bereits `content`, `file_name`, `message_id` |
| pain.001.001.09-Export | `PaymentProposal.create_bank_file`, `pain-001-001-09.html`, `pain-001-001-09_single_payment.html` im selben DocType-Verzeichnis | Version 09 und Einzel-/Sammelmodus sind bereits vorhanden; Bankkompatibilitaet und unveraenderte Wiederholung pruefen, keinen zweiten Exporter schreiben |
| Export bestehender Zahlungsbelege | `erpnextswiss/erpnextswiss/page/payment_export/payment_export.py`: `generate_payment_file`, `generate_pain001` | Ebenfalls Bestand; keine neue Belegerzeugung nur fuer den Banktransport |
| EBICS-Verbindung und Tagesjob | `erpnextswiss/erpnextswiss/doctype/ebics_connection/ebics_connection.py`: `get_client`, `get_transactions`, `execute_payment`; `erpnextswiss/erpnextswiss/ebics.py` | Den vorhandenen Anschluss ersetzen/haerten, pro Konto keinen zweiten gleichzeitigen Transport aktivieren |
| Nachrichtenschemas | `erpnextswiss/public/xsd/`: unter anderem `camt.053.001.08.xsd`, `camt.054.001.08.xsd`, `camt.054.001.08.ch.02.xsd` | Version-08-Schemadateien sind bereits enthalten; Vorhandensein beweist noch keine aktuelle Verwendung oder bestandene Bankabnahme |

Weitere konkret beobachtete Anschlussrisiken, **noch nicht repariert oder live
nachgewiesen**:

1. `payment_proposal.js:154` ruft in `transmit_ebics` den Pfad mit dem Tippfehler
   `ebics_conncetion` auf. Der vorhandene Server-Einstieg `execute_payment` ist zudem
   eine DocType-Instanzmethode, keine gleichnamige Modulfunktion. Vor Anbindung den
   tatsaechlichen berechtigten Dokumentmethoden-Aufruf testen; nicht nur den Tippfehler
   ersetzen und dadurch ungeprueften Zahlungsversand aktivieren.
2. `ebics_connection.py:178` bezeichnet den Vorgang als Upload, ruft aber
   `client.BTD(CCT, xml_transaction)` auf. Die konkrete Sendemethode und ihre
   Bestaetigungs-/Fehlervertraege am gewaehlten Client und Bankprofil verifizieren.
   Dieser Befund beruht auf Code, nicht auf einem ausgefuehrten Bankversuch.
3. `PaymentProposal.create_bank_file` erzeugt bei jedem Aufruf `create_message_id()`.
   Der spaetere Versandadapter muss exakt die geprueften Exportbytes und diese ID
   speichern. Bei unklarem Upload nicht durch erneuten Export neue Identitaeten
   erzeugen. Die bestehende Exportfunktion wird dafuer nicht verdoppelt.
4. `bank_wizard.read_camt053_meta` liest Salden als `float`; `read_camt053` ersetzt
   die Kontowahl durch den ersten IBAN-Treffer und faellt ohne Treffer auf `n/a`
   mit `skip_company_filter=True` zurueck. Vor automatischer Bankuebergabe braucht
   dieser Pfad explizites berechtigtes Konto-/Waehrungsmapping und exakte Betraege.
5. Bestehende Lese-/Match-Endpunkte und aktive Hooks muessen auf der Gesamtinstallation
   mit Kontorechten geprueft werden. Eine neue sichere Gateway-Verbindung allein
   beweist keine sichere Weitergabe ueber bereits vorhandene Reports oder APIs.

BK-01 bleibt offen fuer das Live-Inventar, tatsaechliche Benutzer-/Kontorechte und
die Auswahl des eingesetzten Abgleichwegs. Diese Liste ersetzt keinen Banktest.

## Arbeitspakete und Nachweise

Die Integrationsnachweise starten als **offen**, BK-01 ist durch das obige Inventar
begonnen. Dies bedeutet nicht, dass Zahlungsabgleich oder Zahlungsvorschlaege fehlen.
Ein Dokument oder gruener Unit-Test ersetzt keinen Bank-, Rollen- oder Restoretest.

| ID | Umfang und pruefbares Ende | Abhaengigkeit |
|---|---|---|
| BK-01 | Installierte Commits/Images/Laufzeiten, DocTypes, Bank Transaction Rules, Doc Events, Server Scripts, Controller, Scheduler, Kontomapping und bestehende Importpfade inventarisiert; Nebenwirkungen bekannt | keine |
| BK-02 | Vertrag, Kontoidentitaet/Inhaber/Waehrung, Host/Teilnehmerdaten, unabh. Fingerprints, Profile, Historienfenster, Frequenzen, Sammelbuchungsbeziehung und Banktestverfahren bestaetigt | Bank/Auftraggeber |
| BK-03 | Gekapseltes Modul in Swiss-App, additive Migration, eigener reproduzierbarer Gateway-Build mit Lockfiles; Installation ohne Bankaktion | BK-01 |
| BK-04 | mTLS-Identitaet/Sitebindung, Schluesselspeicher, explizites INI/HIA/HPB, Initialisierungsbrief, Fingerprintpruefung, Rotation und Sperren getestet | BK-03 |
| BK-05 | BTD 053/054, dauerhafter verschluesselter Dateieingang und Operationsjournal, Persistenz-vor-Quittung einschliesslich Abbruchtests | BK-02/04 fuer Banktest |
| BK-06 | Bestehenden Parser/manuellen Import auf Version-08-Nachrichten pruefen; nur fehlende Formatunterstuetzung, XML-/ZIP-Grenzen, Quarantaene und Quellenbeziehungen ergaenzen | BK-01/03 |
| BK-07 | Datei-/Entry-Identitaet, Ueberlappungen, Sammelbuchungen, Reihenfolge, Widersprueche, Salden und Parallelitaet geprueft | BK-05/06 |
| BK-08 | Genau eine native Bank Transaction je gebuchter 053-Ntry, 054/TxDtls nur Anreicherung; keine neuen GL-/eingereichten Zahlungsbelege durch Import | BK-01/07 |
| BK-09 | Vorhandenen Zahlungsabgleich mit Bankimport testen: bestehende Belege zuerst, aktuelle Rechte/Betragsreste, Konkurrenz und menschliche Anwendung; nur nachgewiesene Anbindungsluecken beheben | BK-08 |
| BK-10 | Bankverbindung und notwendige Status-/Fehleranzeigen in bestehendem Desk integrieren; Zahlungsabgleich, Zahlungsvorschlaege, Sidebar, Rollen und Layout unveraendert erhalten | BK-03/08 |
| BK-11 | Bestehende API-/Rechtevertraege fuer angebundene Bankdaten pruefen; nur notwendige Adapter ergaenzen, gleiche Grenzen bei CRUD, Reports, Suche, Dateien und Exporten; kein eigener FAC-Neubau als Pflicht | BK-10 |
| BK-12 | Queue, Monitoring, Retry/Unterbrechung, verschluesselte Backups, isolierter Restore ohne Bank-Egress, Rollback/Deaktivierung, Securitytests | BK-04 bis 11 |
| BK-13 | Begrenzter freigegebener AKB-Lesetest und fachlicher Pilot fuer beide Waehrungen; G0-G3 bestanden, kontrollierter Release 1.0 | BK-02/12 |
| BK-14 | 052-Anreicherung, getrennte Vormerkungen und eindeutiger Uebergang zur Buchung ohne doppelte Wirkung | BK-13 |
| BK-15 | Vorhandenen Payment-Proposal-Export bankseitig validieren; nur noetige Kompatibilitaets-/Uebergabepruefungen samt Freigabebindung und Doppelversandschutz ergaenzen, keine neue Vorschlags- oder Zahlungslogik | separate Release-2-Freigabe |
| BK-16 | Separat freigegebener BTU-/Statusadapter fuer bestehende Zahlungsvorschlaege, T-/VEU-Pilot, Teilablehnung, verspaetete Meldungen und unklarer Upload ohne blinden Retry | BK-15 und Bankrechte |

## Verbindliche Fach- und Sicherheitsvertraege

1. Settings, Connection/Account-Zuordnung, File, Statement, Entry, Sync Run,
   Audit Event und spaetere Submission zuerst auf vorhandene Objekte abbilden;
   neue DocTypes nur fuer nachgewiesene Luecken der Bankanbindung. Verantwortlichkeiten
   getrennt halten, keine bereits vorhandene Zahlungsverwaltung duplizieren.
   Originalquellen append-only zuordnen; vorhandene Custom Fields nicht ueberschreiben.
2. Bankreferenzen sind keine selbst erfundenen Hashes. Hash fuer identische Dateien;
   belastbare Bank-ID nur im Konto-/Company-/Site-Kontext. Ohne sichere ID nur
   Duplikatverdacht. Gleich hohe echte Zahlungen nicht zusammenlegen. Abweichender
   Inhalt bei gleicher Bank-ID wird quarantiniert.
3. Eine gebuchte 053-Ntry entspricht einer Bank Transaction. Sammelbetrag plus
   Einzelbetraege nicht doppelt importieren. 054 darf vor oder nach 053 eintreffen;
   Beziehungen pruefbar und betragskonsistent halten, Unsicherheit nicht verschweigen.
4. Decimal fuer Geld; JSON-Dezimalstrings; CHF/EUR und Saldoarten getrennt. Buchungs-
   und Valutadatum getrennt, Zeitwerte mit Zone, Darstellung Europe/Zurich.
   Eroeffnung + Gutschriften - Belastungen = Schluss nur bei passenden vollstaendigen
   Saldoarten pruefen. NoData ist kein erfundener unveraenderter Saldo.
5. Pro Site/Connection kontrollierte Jobs, pro Teilnehmer serieller Banktransport.
   Nachvollziehbare Request-ID, atomare Persistenz, paginierter Dateiabgleich,
   Recovery fuer Journal/Spool und wiederholbare Uebertragung mit einmaliger
   fachlicher Wirkung. Keine Exactly-once-Netzwerkbehauptung.
6. Parserlimits fuer Groesse, Kompression, Pfade und XML; keine externen Entitaeten
   oder Netzwerknachladung. Fehlerhafte Dateien isolieren, Originale erhalten.
7. Bestehende eingereichte Payment/Journal Entries zuerst. Name/Betrag allein ist
   keine automatische Zuordnung. Teilzahlung, Sammelzahlung, Spesen, Gutschrift,
   Vorschuss, interne Transfers und Fremdwaehrung separat pruefen. Keine erfundenen
   Differenzbuchungen oder automatische Oeffnung geschlossener Perioden.
8. Kontorechte fuer Viewer/Operator/Admin, spaeter Payment Preparer, kein pauschales
   Rollenupgrade. Auch Child-Daten, Suchtreffer, Exporte, generische APIs und Jobs
   unterliegen Company-/Kontorechten und aktuellen Berechtigungen.
9. Banktexte sind Daten, keine Anweisungen. Optionale, nicht abnahmeverpflichtende
   Lesetool-Kandidaten aus dem Briefing; vorhandene Schnittstellen zuerst pruefen:
   `kt_bank_accounts`, `kt_bank_balances`, `kt_bank_transactions`,
   `kt_bank_sync_status`, `kt_bank_reconciliation_preview`.
   Keine KI-Werkzeuge fuer Sync-Initialisierung, Schluessel, Versand, Bankfreigabe
   oder endgueltigen Abgleich. Externe KI-Datenverarbeitung braucht Freigaberichtlinie.
10. API liest vorbereitete Daten mit Quelle/Datenstand; maximal 200 Transaktionen
    pro Seite. `request_sync` asynchron als berechtigter menschlicher POST;
    eine vorhandene Abgleichaktion bleibt menschlich mit erneuter Pruefung; kein
    zweiter `apply_reconciliation`-Endpunkt als Pflicht. Kein Bankabruf
    durch Seitenaufruf, keine beliebigen URLs/Ordercodes/XML/Shellpfade aus Requests.
11. Gateway intern, mTLS mit gebundener Identitaet, bestaetigte Egressziele/TLS,
    non-root, beschraenkte Capabilities, read-only Root und Ressourcenlimits.
    Verschluesselte private Keys nur im Gateway; dateibasierte Secrets, nie im
    Chat, normalen DocType, Log oder Repository. Bankfingerprintwechsel neu pruefen.
12. Kostenfreier PHP-Client als Kandidat, keine Premium-REST-/SaaS-Abhaengigkeit,
    keine eigene Kryptografie. Release/Commit, PHP-Anforderung, Storage-Callback,
    FPDF, transitive Lizenzen und Images tatsaechlich pruefen/pinnen; SBOM fuehren.
13. Nur neue Anbindungsflags initial aus: Gateway, Sync, Import und gegebenenfalls
    Payment Upload/Assistant Read. Bestehenden Zahlungsabgleich, Zahlungsvorschlaege
    und deren Freigaben dadurch nicht abschalten. Migration/Neustart erzeugt keine Keys und
    fuehrt keine Bankaktion aus. Alten Kontotransport nicht parallel aktivieren.
14. Monitoring trennt Bankkontakt, bereitgestellte Daten und Importabschluss.
    Retry begrenzt mit Backoff/Jitter; keine Endlosschleife. Alarmierung ohne sensible
    Transaktionsdetails; Luecken, Datenalter, Quarantaene, Speicher, Schluesselablauf
    und unklare Uebermittlungen sichtbar.
15. Backup umfasst passende DB-/Datei-/Keyring-/Journal-/Konfigurationsstaende und
    gesicherte Recovery-Secrets. Restore ohne Bank-Egress, keine Neuinitialisierung.
    Rollback nur bei Schema-Kompatibilitaet; keine pauschale ERP-Ruecksicherung mit
    Verlust neuer Geschaeftsvorgaenge. Deaktivierung statt Historienloeschung;
    Aufbewahrung und Deinstallation brauchen dokumentierte Archiventscheidung.
16. Release 2 prueft Konto/Rechte, Empfaenger/IBAN/QR-SCOR, offene Betraege,
    Ausfuehrungsdatum und bisherige Uebermittlungen. Snapshot- oder Zustandsaenderung
    entwertet Freigabe; laufende Zahlungen gegen Doppelversand reservieren, legitime
    Teilzahlungen erlauben. Timeout nach Upload bleibt unklar; erst abgleichen,
    kein neuer Versand mit erfundenen IDs. Upload ist nicht Bankfreigabe oder Zahlung.

## Abnahmematrix (vollstaendig aus Briefing Abschnitt 15)

| Gruppe | Zu belegende Faelle |
|---|---|
| Installation/Upgrade | Frische Installation ohne Bank-/Hintergrundaktion; bestehende Site ohne Layout-/Funktionsverlust migrierbar |
| Bestandsintegration | Vorhandener Zahlungsabgleich und vorhandene Zahlungsvorschlaege samt Export, Rechten und Freigaben funktionieren vor/nach Anschluss unveraendert; keine parallelen Prozesse oder Oberflaechen |
| Schluessel | Identischer Keyring nach Neustart; falscher Bankfingerprint blockiert |
| Dauerhaftigkeit | Disk voll vor Bankquittung; ERP-Ausfall nach Gateway-Empfang; spaetere Wiederverarbeitung ohne Datenverlust |
| Dubletten | Identische Datei zehnmal; anders verpackte XML; gleich hohe echte Zahlungen; 053/054-Ueberlappung; jede Eingangsreihenfolge; Bank-ID mit geaendertem Betrag |
| Konten/Salden | Fremdes/unzugeordnetes Konto blockiert; CHF/EUR korrekt getrennt; leerer Auszug mit Saldo erhalten; vorgemerkt spaeter gebucht ohne Doppelwirkung |
| Abgleich | Vorhandener Payment Entry statt zweiter Zahlung; Teil-/Sammelzahlung, Spesen und Gutschrift; aktive Hooks/Regeln erzeugen keine ungeprueften Buchungen |
| Konkurrenz | Gleichzeitige Syncs/Imports/Zuordnungen; keine doppelte Aktivitaet oder ueberhoehte Zuordnung; veralteter Vorschlag blockiert |
| Eingangsangriffe | XXE, gefaehrliche ZIPs und Pfade ohne unerlaubtes Netzwerk-/Dateisystemlesen |
| Rechte | Portal/Planer/Techniker verweigert bei Seite/API/Datei/Export; manipulierte Company-/Konto-ID; gleiche Grenzen bei allgemeinen KI-/CRUD-Tools |
| Recovery | Verschluesseltes Backup isoliert konsistent wiederhergestellt; keine Bankaktion beim Start |
| Release 2 | Timeout nach Upload ohne Auto-Resend; geaenderter Vorschlag entwertet Freigabe; Teilablehnung/verspaetete Statusdatei; Upload niemals allein bezahlt/freigegeben |
| Pilot | Echte CHF-/EUR-Auszugswerte vollstaendig mit Bankdarstellung und nativer ERP-Bankaktivitaet vergleichen; fehlende Randfaelle synthetisch/anonymisiert testen |

Offene Abgleichfaelle sind ein regulaerer Zustand. Keine Behauptung eines
100-prozentigen automatischen Matchings oder rechtlich gepruefter Revisionssicherheit.

## Freigaben, Artefakte und Reihenfolge

- G0: Architektur, Code-/Rechteinventar, Bibliotheksentscheidung, Datenrichtlinie,
  Bankantrag. G1: sichere Initialisierung, echter Lesetest, dauerhafte Originale,
  keine Zahlungsrechte. G2: Imports ohne Dubletten/Saldofehler/Finanznebenwirkungen.
  G3: Rechte/API/Dateien, Betrieb/Restore, fachliche CHF/EUR-Abnahme.
  G4: separate Zahlungsfreigabe, T/VEU, Export, Timeout-/Doppelzahlungsschutz und
  ueberwachte Testzahlung. Nutzerauftrag ersetzt keine Bankzeichnungsrechte.
- Lieferumfang: Bankadapter innerhalb der Swiss-App, interner Gateway, Images/Lockfiles,
  Lizenzhinweise/SBOM, erforderliche additive Migration, bestehende Desk-/API-Anbindung,
  Rechte, Gateway-Vertrag, geheimnisfreie Fixtures, Testnachweise, AKB-Einrichtungs-, Benutzer-,
  Betriebs- und Wiederherstellungsanleitung.
- BK-01 abschliessen; parallel BK-03 und offline BK-06/07. Bankfreigaben BK-02
  extern abhaengig, kein Grund fuer Stillstand der offline moeglichen Arbeit.
  Kein verbindlicher Kosten-/Terminwert vor Inventar und Bibliotheks-/Banktest.
- Je PR: aktuelle Quelle, Regression, gezielte Aenderung, echte relevante Tests,
  GitHub, reproduzierbares Image, Staging, kontrollierter Deploy, laufende Evidenz.
  Status getrennt nach implementiert, getestet, gepusht, deployed und fachlich abgenommen.

## Stand Dieses Inkrements

Die Umfangskorrektur bleibt verbindlich: Zahlungsabgleich und Zahlungsvorschlaege
sind vorhanden; neu zu liefern ist deren Bankanbindung, nicht deren Neuerstellung.

- BK-01: `scripts/banking_readiness_inventory.py` wurde in einer explizit
  READ-ONLY-Datenbanktransaktion im laufenden Frappe-Container ausgefuehrt, danach
  Rollback/Verbindungsabbau. Bericht enthaelt App-Versionen, Quellhashes,
  DocType-/Rechtemetadaten, relevante Hooks/Scheduler und aggregierte Kontopruefung.
  Keine Zugangsdaten, IBANs, Einzelbetraege oder Bank-/Parteibezeichnungen werden
  ausgegeben. Es erfolgt kein EBICS-Clientimport oder Bankkontakt.
- Laufzeitbestand bestaetigt Payment Proposals und Payment Entries sowie gueltig
  zugeordnete CHF-/EUR-Firmenbankkonten. Keine EBICS-Verbindung ist angelegt oder
  aktiviert. Native Bank Transaction Rules haben einen bestehenden Scheduler;
  Payment Entry ist durch HRMS ueberschrieben und durch Projekt-/Spesenhooks
  ergaenzt. Damit bleiben echte integrationsweite Seiteneffekttests erforderlich.
  Git-Commits sind im Produktionsimage nicht vorhanden; Versionen/Quellhashes
  werden nicht als gleichwertiger Release-Commitnachweis ausgegeben.
- BK-03/05 teilweise: `gateway/ebics` enthaelt einen inaktiven Bibliothekskern mit
  festem BTD-Leseprofil, verschluesseltem transaktionalem Originaljournal,
  Teilnehmer-Prozesssperre und Wiederanlauf ohne automatischen Wiederabruf.
  Speicherung samt unabhaengiger Ruecklesepruefung erfolgt vor positiver Quittung.
- Offline bestanden: 133 PHP-Pruefungen mit echter gepinnter EBICS-Bibliothek,
  signierter simulierter Bank, unabhaengigen Prozessen und SIGKILL; zusaetzlich
  echter SQLITE_FULL-Test in einem isolierten 1-MiB-tmpfs mit erfolgreicher
  Wiederaufnahme. Vier Python-Tests pruefen das lesende Inventar. Eine eigene
  GitHub-CI prueft diese Grenzen ohne Bankzugang; ihr Laufstatus ist separat vom
  lokal/isoliert erbrachten Testnachweis zu fuehren.
- Der allgemeine Mutation-Guard meldete im Empfangskern-Commit und im separat
  exportierten Ausgangscommit `fc44290` den alten Wartungsendpunkt
  `scripts/item_tools.py:purge_supplier_hints_from_item_descriptions`.
  Eine getrennte Reparatur beschraenkt ihn auf POST und System Manager,
  beruecksichtigt die Leserechte und prueft alle Schreibrechte vor dem ersten
  Schreibzugriff. Interne Teil-Commits entfallen; die aufrufende Frappe-Transaktion
  bleibt verantwortlich. Fuenf isolierte Tests bestehen; native Frappe-Tests fuer
  HTTP-Methoden, Gastverweigerung und Rollback sind als eigener CI-Schritt ergaenzt.
  Ihre Ausfuehrung ist separat nachzuweisen. Fremde Zahlungs-/MCP-Aenderungen im
  Hauptcheckout werden nicht uebernommen. Kein Zahlungsworkflow wird neu gebaut.
- Die spaeter abgeschlossene Gesamt-CI von `7940eca` hat eine neue
  Paketierungsregression aufgedeckt: Setuptools hielt `gateway` fuer ein zweites
  Python-Paket und brach die editable Installation ab. Die explizite
  Paketzuordnung umfasst jetzt nur `erpnextswiss` samt Unterpaketen. Der PHP-Dienst
  wird weiterhin separat gebaut, nicht aus dem Python-Paket importiert.
  Der neue Artefaktpruefer prueft Wheel und Quellarchiv auf bytegleiche,
  vollstaendige App-Ressourcen und verbietet den Gateway im Python-Paket.
  Er deckte zusaetzlich bisher fehlende XSD-, Schrift-, WASM-, SQL- und
  Vorlagendateien in Wheels auf; die vorhandenen Dateien werden jetzt mitgeliefert.
  Isoliert auf Python 3.14 bestanden: 774 Ressourcen in beiden Artefakten,
  bytegleicher Erhalt aller App-Dateien aus dem Ausgangswheel sowie erfolgreiche
  editable Installation mit Import aus dem neuen Checkout. Die neue CI-Stufe
  prueft diese Paketgrenze bei jedem PR; ihre Ausfuehrung ist separat nachzuweisen.
- GitHub-Nachweis fuer `d3f0864`: Banking-CI `34723810494` und Python-Paketierung
  in der allgemeinen CI `34723810516` sind erfolgreich. Die Gesamtinstallation
  erreicht jetzt den Swiss-Installationshook, scheitert dort aber an einer
  Workspace-/Page-Routenkollision. Das ist ein eigener offener Update-/Installations-
  befund, kein gruener Gesamtstatus und keine Berechtigung, den Installationscheck
  zu ueberspringen. Bankkontakt, Produktivmigration und Deploy bleiben aus.
- SDK 3.2.1 und Git-Commit wurden tatsaechlich geprueft und gepinnt. Abweichende
  Packagist-/Git-Referenzen wurden erkannt; Lockfile und Referenztest verhindern
  eine unbemerkte Abweichung. MIT-Lizenz und benoetigte PHP-Erweiterungen geprueft;
  kein kostenpflichtiger Gateway-Service oder zusaetzlicher PDF-Generator noetig.

Details, Quellen, Testbefehle und Grenzen: [Empfangskern](../gateway/ebics/README.md).
Der lokale Laufzeitbericht bleibt ausserhalb des oeffentlichen Repositories.
Keine Finanzdaten geschrieben, kein Produktionslayout/-ablauf geaendert, kein
Bankkontakt und kein Deploy. Es gibt noch keinen nutzbaren HTTP-Gateway oder
ERP-Importadapter. BK-01, sichere Konfiguration/Schluessel, mTLS, Transportlimits,
ZIP/XML/Importuebergabe, Rechte, Restore und Bankpilot bleiben offen. BK-15/16
setzen eine separate Freigabe voraus. Die vollstaendige Plattform- und
Bankanbindungs-Abnahme fehlt; dieser Teilnachweis ersetzt sie nicht.

## Weiterer Nachweis: Update-Vertrag und begrenzter Empfang

Am 13.09.2026 ist die allgemeine Swiss-CI fuer `3eb0cfc12c7be89d3c65ad6e074e52706ac504c3`
in Lauf `34728622121` vollstaendig erfolgreich abgeschlossen; die getrennte
Offline-Bank-CI `34728622125` ebenfalls. Die vorher dokumentierten
Installations-/Workspace-/Fixture-Fehler sind damit korrigiert und in nativen
Neuinstallations-, Migrations-, HRMS- und Browserpruefungen abgesichert.
[Feld-/Update-Nachweise](fixture-upgrade-contract.md) und
[Workspace-Nachweise](workspace-route-upgrade.md) grenzen den Testumfang ab.
Die lesende Produktivpruefung bestaetigt 41 vollstaendige, unveraenderte
Quell-Felddefinitionen; das ersetzt keine Produktivmigration oder Vollabnahme.

Der folgende isoliert getestete Empfangsschritt schliesst die zuvor offene
aeussere zlib-Grenze: Der erforderliche `ReadClient` bindet einen begrenzten
Decoder ueber die native SDK-Erweiterung ein. Maximal 10 MiB komprimierte Daten
und exakt 32 MiB Ergebnis, keine Quittung bei ungueltigen/zu grossen Daten.
Ein echter 96-MiB-PHP-Unterprozess reproduziert den Speicherabbruch des alten
SDK-Decoders bei synthetischer 256-MiB-Expansion; die Begrenzung weist dieselben
Daten kontrolliert ab und behaelt gueltige Daten an der oberen Grenze vollstaendig.
Auch die beobachtete PHP-Puffertoleranz oberhalb von `max_length` wird durch eine
zusaetzliche exakte Laengenpruefung und Regressionstests abgefangen.

Isoliert bestanden: 167 PHP-Pruefungen, echter SQLITE_FULL-Wiederanlauf und
vollstaendiger 32-MiB-Empfang mit Verschluesselung, unabhaengiger Ruecklesepruefung,
Quittierung und lokalem Replay. Fuer den kompletten grossen Transfer gemessener
PHP-Spitzenbedarf: 171.986.944 Bytes; hierfuer getestet mit 256 MiB PHP,
512 MiB Container und 128 MiB tmpfs. Das kleine 128-MiB-Testprofil ist kein
geeignetes Worker-Profil fuer diese Maximaldatei. Neue CI-Ausfuehrung dieses
Empfangsschritts separat nachweisen; ein hinzugefuegter Test ist kein CI-Erfolg.

Zahlungsabgleich, Zahlungsvorschlaege, Exporte und Oberflaechen bleiben Bestand.
Keine Produktivquelle oder Finanzdaten geaendert und keine Bankaktion ausgefuehrt.
Weiter offen sind insbesondere HTTP-/Segmentgrenzen, innere ZIP-/XML-Pruefung,
vertrauenswuerdige Konfiguration/Keys/mTLS, vorhandene ERP-Importuebergabe,
Konto-/Rechtenachweise, Restore, Bankpilot und kontrollierter Deploy. Die
urspruenglichen 14 Plattformpakete bleiben unveraendert Bestandteil des Ziels.

## Weiterer Nachweis: HTTPS und aeussere Antwortpruefung

Fuer `b2e27fc0e7cb4d0ea1bc65901b7bf4107b29fa44` sind anschliessend sowohl
Swiss-CI `34729190953` als auch Bank-CI `34729190868` erfolgreich abgeschlossen.
Der nachfolgende HTTPS-Schritt wurde isoliert gegen einen echten TLS-Testserver
auf Loopback, bei abgeschaltetem externem Container-Netzwerk, umgesetzt und geprueft.

- `ReadClient::https()` verwendet verifiziertes HTTPS mit festem Server-Endpunkt,
  ohne Weiterleitung, Umgebungsproxy, HTTP-Entpackung oder automatische Wiederholung.
  1 MiB Request, 64 KiB Header, 8 MiB Body; der Body wird im cURL-Callback vor
  DOM-Aufbau begrenzt. Ungueltige Zertifikate/Hostnamen und Chunked-Uebergroessen
  sind getestete Fehlerfaelle. Konfiguration und Berechtigung bleiben getrennt.
- Die native SDK-Entity-Ersetzung wurde mit einer rein synthetischen lokalen Datei
  reproduziert. Die neue Antwortpruefung nutzt native XMLReader-/DOM-APIs mit
  NO_XXE/NONET, verbietet DTDs und begrenzt Tiefe, Knoten und Attribute. Bei den
  Angriffstests inklusive UTF-16 gab es keinen Aufruf des instrumentierten
  externen Entity-Loaders. Keine XML-/Serverinhalte in Fehlermeldungen.
- Eine verpflichtende Download-Huelle begrenzt alle SDK-Austausche auf 64 Segmente,
  65 Requests und 20 MiB serialisierte Antworten pro Vorgang. Ein monotones
  120-Sekunden-Budget wird an HTTP-Grenzen geprueft; einzelne HTTPS-Aufrufe dauern
  hoechstens 30 Sekunden. Kein harter Prozess-Timeout fuer lokale Kryptografie
  oder Dateisysteme behauptet. Bei spaeter Quittungsantwort bleibt das Original
  vorhanden, der Status unbestaetigt und die Wiederholung lokal.
- Isoliert bestanden: 193 Empfangspruefungen, 87 TLS-/XML-Pruefungen, wirklicher
  SQLITE_FULL-Wiederanlauf und kompletter 32-MiB-Pfad. Zusaetzlich 27 lokale
  Python-Tests. Ein voll signierter SDK-Download lief durch echtes cURL/TLS,
  inklusive Quittung und bytegleichem Original. Das ist keine Bankabnahme.

Der Code aendert weder Zahlungsabgleich noch Zahlungsvorschlaege, Exporte, ERP-Daten
oder Layouts. Keine Bankverbindung wurde konfiguriert oder aktiviert. Weiter offen:
innere ZIP-/camt-Pruefung und vorhandene Importuebergabe, vertrauenswuerdige
Kontobindung/Schluessel, DNS/Egress und internes mTLS, kombinierte Worst-Case-
Kapazitaet, Betriebsstatus/Restore, Kontorechte, Bankpilot und kontrollierter Deploy.
Die Original-Plattformpakete bleiben unveraendert im Ziel. Details und Befehle:
[Transport-Nachweise](../gateway/ebics/README.md).
