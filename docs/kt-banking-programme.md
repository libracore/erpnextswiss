# KT Banking: verbindliche Erweiterung des Plattformziels

Stand: 12.09.2026. Auftrag: Banking-Briefing vollstaendig in das aktive
Plattformziel integrieren, updatefest innerhalb der vorhandenen Swiss-App.
**Status: Spezifikation und erstes Codeinventar, keine aktivierte Bankanbindung.**

## Quelle und Vorrang

Verbindliche fachliche Quelle ist das vom Auftraggeber bereitgestellte
`KT_Banking_Projektplan_Entwicklerbriefing.md`, Version 1.0 vom 12.09.2026.
Original-SHA-256:
`6a2c05a18ccfc91be43f2487bcc6a32a5963cd222aefde6e7aafc509d45caebb`.
Die interne Originaldatei wird nicht in dieses oeffentliche Repository kopiert.
Die folgende Zuordnung dokumentiert den vollstaendigen Entwicklungsumfang ohne
interne Kontoidentitaeten, Bankzugangsdaten oder Geheimnisse zu publizieren.

Die anschliessende Nutzeranweisung ersetzt den vorgeschlagenen neuen App-Namen:
Integration in die vorhandene Swiss-App ist die Entwicklungsrichtung. Das lokale
Codeinventar identifiziert diese als `erpnextswiss`, Titel `Schweizer Buchhaltung`,
mit vorhandenem Arbeitsbereich `Zahlungsverkehr`. Kein zweites Hauptbuch, Login
oder paralleles Zahlungsprodukt anlegen. Neue Banking-Module innerhalb dieser
App kapseln; den PHP-Gateway als separat baubaren internen Dienst betreiben.
Neue API-Pfade werden im Schema-PR verbindlich festgelegt, nicht als bereits
existierende `kt_banking.api.v1`-Endpunkte ausgegeben. Bestehende Pfade bleiben
kompatibel. Die vorgeschlagenen Banking-DocTypes bleiben eigene Herkunfts- und
Pruefnachweise neben den fuehrenden nativen ERPNext-Objekten.

Die bisherigen **14 Plattformpakete bleiben vollstaendig offen beziehungsweise
mit ihren belegten Teilstaenden erhalten**. Banking ersetzt keines dieser Pakete.
Kein Funktions- oder Layoutverlust. Kein KI-Assistent/MCP-Chat in Android.
Kein Bankdatenzugriff fuer Kundenportal, Planer, Partner oder Techniker-App.
Neue Bankkommunikation ist durch die Planaufnahme nicht freigegeben.

## Releasegrenzen

- **1.0:** bestaetigtes AKB-H005-Profil, Einrichtung, camt.053.001.08 und
  camt.054.001.08, Originalarchiv, CHF/EUR, Salden, sichere Imports und nativer
  Bankabgleich. Derselbe Parser fuer manuelle Dateien und Gateway-Dateien.
  Gegenueber der Bank nur lesend; kontrollierte ERP-Importdatensaetze und Bank
  Transactions sind erlaubt. Keine autonome Hauptbuchbuchung, eingereichte
  Payment Entry oder Zahlungsuebermittlung. Bestehende Zahlungsbelege zuerst
  abgleichen; fehlende Zahlungen hoechstens in explizit freigegebenen Entwuerfen.
- **1.1:** camt.052.001.08 separat pruefen. Zunaechst Anzeige/Anreicherung;
  vorgemerkt und gebucht trennen, keine zweite Bank-Transaction-Erfassung.
- **2.0:** erst eigene Freigabe; bestehendes Payment Proposal, validierte
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
noch verworfen. Noch kein Live-Hook-/Server-Script-/Kontorechteaudit in BK-01.

| Befund im vorhandenen Code | Konsequenz fuer die Integration |
|---|---|
| `hooks.py`: vorhandene Swiss-App, Sidebar und taeglicher `ebics.sync`-Job | Wiederverwenden; pro Konto genau einen automatischen Transportbesitzer nachweisen |
| `pyproject.toml` und `ebics_connection.py`: vorhandener fintech-Transport | Nicht als kostenfreien neuen Gateway ausgeben; Lizenz/Bestandsnutzung separat inventarisieren |
| `ebicsConnection.get_transactions`: `confirm_download()` vor `stmt.insert()` und ERP-Commit | Neuer Gateway muss dauerhafte Speicherung vor positiver Bankquittung beweisen |
| Derselbe Pfad loescht Statements ohne Transaktionen | Neue Saldo-/Auszugsverarbeitung muss leere Auszuege mit Salden behalten |
| Derselbe Pfad ruft `stmt.process_transactions()` auf | Kein Aufruf aus dem neuen Release-1-Import |
| `ebicsStatement.process_transactions`: `auto_submit: 1` fuer Zahlungsbelege | Realer Nebenwirkungstest auf Gesamtinstallation, nicht nur auf neuem Parser |
| `ebicsStatement.parse_content`: erster passender Account, interpolierter SQL-Ausdruck und eigene Dublettenabfrage | Explizites kontorechtegebundenes Mapping, strukturierte Abfragen und neuer Dublettenvertrag erforderlich |
| Vorhandene native Zahlungs-/Importfunktionen | Nicht entfernen; Ausweichweg, Stichtag und Konflikterkennung dokumentieren |
| Vorhandene App-Lizenz AGPL | Lizenzhinweise beibehalten; MIT-Bibliothek macht die Gesamt-App nicht automatisch MIT |

Diese Befunde sind Quellcodebeobachtungen, kein Nachweis aktiver Bankverbindungen,
erfolgter Fehlbuchungen oder aktueller Produktiv-Hooks. Kein Bankabruf wurde gestartet.

## Arbeitspakete und Nachweise

Alle Pakete starten als **offen**, BK-01 ist durch das obige Inventar begonnen.
Ein Dokument oder gruener Unit-Test ersetzt keinen Bank-, Rollen- oder Restoretest.

| ID | Umfang und pruefbares Ende | Abhaengigkeit |
|---|---|---|
| BK-01 | Installierte Commits/Images/Laufzeiten, DocTypes, Bank Transaction Rules, Doc Events, Server Scripts, Controller, Scheduler, Kontomapping und bestehende Importpfade inventarisiert; Nebenwirkungen bekannt | keine |
| BK-02 | Vertrag, Kontoidentitaet/Inhaber/Waehrung, Host/Teilnehmerdaten, unabh. Fingerprints, Profile, Historienfenster, Frequenzen, Sammelbuchungsbeziehung und Banktestverfahren bestaetigt | Bank/Auftraggeber |
| BK-03 | Gekapseltes Modul in Swiss-App, additive Migration, eigener reproduzierbarer Gateway-Build mit Lockfiles; Installation ohne Bankaktion | BK-01 |
| BK-04 | mTLS-Identitaet/Sitebindung, Schluesselspeicher, explizites INI/HIA/HPB, Initialisierungsbrief, Fingerprintpruefung, Rotation und Sperren getestet | BK-03 |
| BK-05 | BTD 053/054, dauerhafter verschluesselter Dateieingang und Operationsjournal, Persistenz-vor-Quittung einschliesslich Abbruchtests | BK-02/04 fuer Banktest |
| BK-06 | Schema und Parser fuer Version-08-Nachrichten, manueller Import, XML-/ZIP-Grenzen, Quarantaene und Quellenbeziehungen | BK-03 |
| BK-07 | Datei-/Entry-Identitaet, Ueberlappungen, Sammelbuchungen, Reihenfolge, Widersprueche, Salden und Parallelitaet geprueft | BK-05/06 |
| BK-08 | Genau eine native Bank Transaction je gebuchter 053-Ntry, 054/TxDtls nur Anreicherung; keine neuen GL-/eingereichten Zahlungsbelege durch Import | BK-01/07 |
| BK-09 | Erklaerbare Vorschlaege mit bestehenden Belegen zuerst; Zustand/Rechte/Betragsreste unter Konkurrenz erneut pruefen; menschliche Anwendung nativer Methoden | BK-08 |
| BK-10 | Uebersicht, Kontobewegungen, Abgleich, Verbindungen, Protokolle, Sidebar, Rollen/Reports im bestehenden Desk; Light/Dark und schmale/breite Ansichten | BK-03/08 |
| BK-11 | Versionierte Konto-/Saldo-/Transaktions-/Sync-/Vorschau-API; FAC-Lesetools; gleiche Kontorechte auch ueber CRUD, Reports, Suche, Dateien und Exporte | BK-10 |
| BK-12 | Queue, Monitoring, Retry/Unterbrechung, verschluesselte Backups, isolierter Restore ohne Bank-Egress, Rollback/Deaktivierung, Securitytests | BK-04 bis 11 |
| BK-13 | Begrenzter freigegebener AKB-Lesetest und fachlicher Pilot fuer beide Waehrungen; G0-G3 bestanden, kontrollierter Release 1.0 | BK-02/12 |
| BK-14 | 052-Anreicherung, getrennte Vormerkungen und eindeutiger Uebergang zur Buchung ohne doppelte Wirkung | BK-13 |
| BK-15 | Payment-Proposal-Export, Schema-/Geschaeftsregeln, strukturierte Adressen, unveraenderlicher Freigabesnapshot und Doppelzahlungsschutz | separate Release-2-Freigabe |
| BK-16 | BTU, Statuskorrelation, T-/VEU-Pilot, Teilablehnung, verspaetete Meldungen und unklarer Upload ohne blinden Retry | BK-15 und Bankrechte |

## Verbindliche Fach- und Sicherheitsvertraege

1. Vorgeschlagene Settings, Connection/Account-Zuordnung, File, Statement, Entry,
   Sync Run, Audit Event und spaetere Submission als getrennte Verantwortlichkeiten.
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
9. Banktexte sind Daten, keine Anweisungen. Geplante Lesetools:
   `kt_bank_accounts`, `kt_bank_balances`, `kt_bank_transactions`,
   `kt_bank_sync_status`, `kt_bank_reconciliation_preview`.
   Keine KI-Werkzeuge fuer Sync-Initialisierung, Schluessel, Versand, Bankfreigabe
   oder endgueltigen Abgleich. Externe KI-Datenverarbeitung braucht Freigaberichtlinie.
10. API liest vorbereitete Daten mit Quelle/Datenstand; maximal 200 Transaktionen
    pro Seite. `request_sync` asynchron als berechtigter menschlicher POST;
    `apply_reconciliation` menschlicher POST mit erneuter Pruefung. Kein Bankabruf
    durch Seitenaufruf, keine beliebigen URLs/Ordercodes/XML/Shellpfade aus Requests.
11. Gateway intern, mTLS mit gebundener Identitaet, bestaetigte Egressziele/TLS,
    non-root, beschraenkte Capabilities, read-only Root und Ressourcenlimits.
    Verschluesselte private Keys nur im Gateway; dateibasierte Secrets, nie im
    Chat, normalen DocType, Log oder Repository. Bankfingerprintwechsel neu pruefen.
12. Kostenfreier PHP-Client als Kandidat, keine Premium-REST-/SaaS-Abhaengigkeit,
    keine eigene Kryptografie. Release/Commit, PHP-Anforderung, Storage-Callback,
    FPDF, transitive Lizenzen und Images tatsaechlich pruefen/pinnen; SBOM fuehren.
13. Alle neuen Sicherheitsflags initial aus: Gateway, Sync, Import, Abgleich,
    Payment Upload und Assistant Read. Migration/Neustart erzeugt keine Keys und
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
- Lieferumfang: installierbares Swiss-App-Modul, interner Gateway, Images/Lockfiles,
  Lizenzhinweise/SBOM, additive Migration, Desk/Sidebar, Rechte, REST-/Gateway-Vertrag,
  FAC-Adapter, geheimnisfreie Fixtures, Testnachweise, AKB-Einrichtungs-, Benutzer-,
  Betriebs- und Wiederherstellungsanleitung.
- BK-01 abschliessen; parallel BK-03 und offline BK-06/07. Bankfreigaben BK-02
  extern abhaengig, kein Grund fuer Stillstand der offline moeglichen Arbeit.
  Kein verbindlicher Kosten-/Terminwert vor Inventar und Bibliotheks-/Banktest.
- Je PR: aktuelle Quelle, Regression, gezielte Aenderung, echte relevante Tests,
  GitHub, reproduzierbares Image, Staging, kontrollierter Deploy, laufende Evidenz.
  Status getrennt nach implementiert, getestet, gepusht, deployed und fachlich abgenommen.

## Stand Dieses Inkrements

Nur diese Ziele/Abnahmen und das erste lesende Codeinventar sind hinzugefuegt.
Kein Produktionskonto gelesen, keine Finanzdaten geschrieben, kein Gateway oder
Banking-Modul implementiert, kein Bankkontakt oder Deploy. BK-01 bleibt teilweise
offen, BK-02 bis BK-16 offen. Die vollstaendige Plattform- und Banking-Abnahme fehlt.
