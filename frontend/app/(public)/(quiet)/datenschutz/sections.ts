// The text of the privacy policy after the section on who is responsible, which
// the page builds from the impressum. Every statement here describes what the
// code and the server actually do, so a change to sessions, logs, cookies or
// hosting has to change this text as well.

export const PRIVACY_POLICY_DATE = "November 2026";

export type PrivacySection = {
  heading: string;
  paragraphs: string[];
};

export const PRIVACY_SECTIONS: PrivacySection[] = [
  {
    heading: "Für welche Adressen diese Erklärung gilt",
    paragraphs: [
      "Sie gilt für www.wediga.dev, für die Anmeldung unter auth.wediga.dev und für den CR Predictor unter cr-prediction.wediga.dev. Alle drei laufen auf demselben Server, den ich selbst betreibe.",
    ],
  },
  {
    heading: "Hosting",
    paragraphs: [
      "Der Server steht bei der Hetzner Online GmbH, Industriestr. 25, 91710 Gunzenhausen, in einem Rechenzentrum in Falkenstein (Vogtland). Hetzner stellt nur den Server bereit, alle Dienste darauf betreibe ich selbst. Mit Hetzner besteht ein Vertrag zur Auftragsverarbeitung nach Art. 28 DSGVO, und deine Daten verlassen die Europäische Union nicht.",
    ],
  },
  {
    heading: "Verschlüsselung",
    paragraphs: [
      "Alle Adressen sind nur über HTTPS erreichbar, sodass die Verbindung zwischen deinem Browser und dem Server verschlüsselt ist. Ein Aufruf über HTTP wird auf HTTPS umgeleitet.",
    ],
  },
  {
    heading: "Was beim Aufruf der Seite passiert",
    paragraphs: [
      "Wenn du eine der Seiten aufrufst, schickt dein Browser technisch bedingt deine IP-Adresse, die aufgerufene Adresse, den Zeitpunkt und eine Kennung deines Browsers (User-Agent) mit. Ohne diese Angaben kann der Server die Seite nicht ausliefern. Durch die Art, wie die Dienste auf dem Server laufen, sehen sie deine IP-Adresse aber nicht, sondern nur eine interne Adresse des Servers, die für alle Besucher gleich ist. Deine IP-Adresse wird deswegen nirgends gespeichert.",
      "Die Dienste schreiben ein Protokoll mit Zeitpunkt, Art und Pfad der Anfrage, dem Ergebnis und Fehlermeldungen. Bei einer Anmeldung über auth.wediga.dev steht dort auch der Benutzername. Ich brauche diese Protokolle, um Fehler zu finden und Angriffe zu erkennen. Rechtsgrundlage ist mein berechtigtes Interesse an einem sicheren und funktionierenden Betrieb nach Art. 6 Abs. 1 lit. f DSGVO. Die Protokolle werden nach 180 Tagen automatisch gelöscht.",
      "Auf der Seite sind keine Dienste von Dritten eingebunden, also keine Analyse, keine Werbung, keine Videos oder Karten und keine Schriften von fremden Servern. Links zu GitHub oder LinkedIn sind einfache Links, und Daten gehen erst an diese Anbieter, wenn du einen davon anklickst.",
    ],
  },
  {
    heading: "Cookies und Speicher im Browser",
    paragraphs: [
      "Die Seite setzt nur ein einziges Cookie, wediga_session, und das auch nur, wenn du dich anmeldest oder einen persönlichen Link öffnest. Es enthält eine Zufallszahl, über die der Server deine Sitzung wiedererkennt, und sonst nichts. Dein Browser löscht es spätestens nach 7 Tagen.",
      "Zur Sitzung speichert der Server einen Hash dieser Zufallszahl, die Kennung deines Browsers, den Beginn und den letzten Aufruf und, wenn du angemeldet bist, dein Konto mit Namen. Eine Sitzung endet nach 2 Stunden ohne Aufruf, eine Anmeldung 8 Stunden nach dem Login und der Zugang über einen persönlichen Link 7 Tage nach dem Öffnen. Abgelaufene Sitzungen löscht der Server innerhalb einer Stunde.",
      "Zwei Einstellungen merkt sich die Seite im Speicher deines Browsers, ohne sie an den Server zu schicken. Im localStorage steht, ob du die Animation ein- oder ausgeschaltet hast, und im sessionStorage stehen die Farben der Startseite, damit die folgenden Seiten dazu passen. Die Einstellung zur Animation bleibt, bis du sie zurücksetzt oder den Speicher deines Browsers leerst, die Farben verschwinden, sobald du den Tab schließt.",
      "Für die Anmeldung unter auth.wediga.dev setzt die Anmeldesoftware authentik eigene Cookies, die deine Anmeldung dort halten und vor gefälschten Anfragen schützen.",
      "Alle diese Cookies und Einträge sind für die Funktion, die du aufrufst, unbedingt erforderlich und brauchen deswegen nach § 25 Abs. 2 Nr. 2 TDDDG keine Einwilligung. Für die Daten zur Sitzung ist die Rechtsgrundlage mein berechtigtes Interesse nach Art. 6 Abs. 1 lit. f DSGVO, geschützte Bereiche nur den Personen zu zeigen, für die sie bestimmt sind.",
    ],
  },
  {
    heading: "Persönliche Links für Bewerbungen",
    paragraphs: [
      "Für Bewerbungen verschicke ich persönliche Links, über die man den geschützten Teil des Portfolios mit Lebenslauf sieht. Zu jedem Link speichere ich, an welche Firma ich ihn geschickt habe, wann er angelegt wurde und wie lange er gilt. Wird der Link geöffnet, speichert der Server den Zeitpunkt und einen Herkunftswert. Dieser entsteht aus dem groben Netzbereich der Anfrage (bei IPv4 die ersten drei Blöcke), der zusammen mit einem geheimen Wert gehasht und gekürzt wird, sodass sich daraus keine Adresse zurückrechnen lässt. Er zeigt mir nur, ob ein Link mehrmals aus derselben Umgebung geöffnet wurde.",
      "So sehe ich, ob und wie oft meine Bewerbung angesehen wurde. Rechtsgrundlage ist mein berechtigtes Interesse nach Art. 6 Abs. 1 lit. f DSGVO, den Verlauf meiner Bewerbungen nachzuvollziehen. Die Aufrufe lösche ich, wenn das Bewerbungsverfahren abgeschlossen ist.",
    ],
  },
  {
    heading: "Konten für Freunde",
    paragraphs: [
      "Freunde, die ich einlade, bekommen ein Konto bei authentik unter auth.wediga.dev. Ein Konto lege nur ich selbst an, eine offene Registrierung gibt es nicht. Gespeichert werden Benutzername, Name, E-Mail-Adresse, ein Hash des Passworts, der zweite Faktor (Authenticator-App oder Sicherheitsschlüssel) und die Gruppen, die bestimmen, welche Dienste du siehst. Dazu protokolliert authentik Ereignisse wie Anmeldungen, fehlgeschlagene Anmeldungen und Änderungen am Konto mit Zeitpunkt und Browser-Kennung.",
      "Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, weil das Konto nötig ist, damit du die Dienste nutzen kannst, für die ich dich eingeladen habe. Das Konto bleibt bestehen, bis du mich um die Löschung bittest oder ich den Zugang beende, und die Ereignisse löscht authentik nach 365 Tagen.",
    ],
  },
  {
    heading: "CR Predictor",
    paragraphs: [
      "Der CR Predictor unter cr-prediction.wediga.dev berechnet aus den Werten, die du eingibst, eine Einschätzung. Die Werte werden nur für diese Berechnung verwendet und nicht gespeichert, Cookies setzt er keine. Für die Protokolle gilt, was oben unter „Was beim Aufruf der Seite passiert“ steht.",
    ],
  },
  {
    heading: "Kontakt per E-Mail",
    paragraphs: [
      "Schreibst du mir eine E-Mail, verarbeite ich deine Adresse und den Inhalt, um dir zu antworten. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO, bei einer Anfrage zu einer Zusammenarbeit oder Stelle Art. 6 Abs. 1 lit. b DSGVO. Ich lösche die E-Mail, wenn das Anliegen erledigt ist und keine Pflicht zur Aufbewahrung besteht.",
    ],
  },
  {
    heading: "Muss ich Daten angeben?",
    paragraphs: [
      "Nein, eine Pflicht dazu gibt es nicht. Ohne die technischen Angaben beim Aufruf kann der Server die Seite aber nicht ausliefern, und ohne Konto gibt es keinen Zugang zu den geschützten Bereichen. Eine automatisierte Entscheidung oder ein Profiling findet nicht statt.",
    ],
  },
  {
    heading: "Deine Rechte",
    paragraphs: [
      "Du hast das Recht auf Auskunft über deine Daten (Art. 15 DSGVO), auf Berichtigung (Art. 16), auf Löschung (Art. 17), auf Einschränkung der Verarbeitung (Art. 18) und auf Übertragung deiner Daten (Art. 20). Dafür reicht eine E-Mail an mich.",
      "Außerdem kannst du dich bei einer Aufsichtsbehörde für den Datenschutz beschweren (Art. 77 DSGVO). Für mich zuständig ist die Berliner Beauftragte für Datenschutz und Informationsfreiheit.",
    ],
  },
  {
    heading: "Dein Recht auf Widerspruch",
    paragraphs: [
      "Wo ich Daten auf Grundlage meines berechtigten Interesses verarbeite (Art. 6 Abs. 1 lit. f DSGVO), kannst du dem aus Gründen, die sich aus deiner besonderen Situation ergeben, jederzeit widersprechen (Art. 21 DSGVO). Ich verarbeite die Daten dann nicht mehr, es sei denn, ich kann zwingende schutzwürdige Gründe nachweisen, die deine Interessen überwiegen, oder die Verarbeitung dient der Geltendmachung, Ausübung oder Verteidigung von Rechtsansprüchen.",
    ],
  },
  {
    heading: "Änderungen",
    paragraphs: [
      "Ändert sich etwas an der Seite oder ihren Diensten, passe ich diese Erklärung an. Es gilt die Fassung, die hier steht.",
    ],
  },
];
