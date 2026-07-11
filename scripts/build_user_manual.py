from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static" / "manualer" / "sun2_driftsmanual.pdf"
LOGO = ROOT / "static" / "sun2-blue-transparent.png"
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

BLUE = colors.HexColor("#5292d6")
DARK_BLUE = colors.HexColor("#26323f")
LIGHT = colors.HexColor("#df705d")
VENT = colors.HexColor("#52a464")
CLEAN = colors.HexColor("#2f8fa3")
ENERGY = colors.HexColor("#f2b84b")
PURPLE = colors.HexColor("#726189")
MUTED = colors.HexColor("#64748b")
SOFT = colors.HexColor("#f5f7fb")
LINE = colors.HexColor("#dbe3ec")


def p(text: str, style: ParagraphStyle):
    return Paragraph(text, style)


def bullets(items: list[str], style: ParagraphStyle):
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=10) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=16,
        bulletFontSize=7,
    )


def table(rows, widths, header=True):
    tbl = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e8edf3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("LEADING", (0, 0), (-1, -1), 11),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ]
        )
    tbl.setStyle(TableStyle(style))
    return tbl


def callout(title: str, text: str, color=BLUE):
    rows = [[Paragraph(f"<b>{title}</b><br/>{text}", styles["Callout"])]]
    tbl = Table(rows, colWidths=[16.2 * cm], hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 0.7, color),
                ("LINEBEFORE", (0, 0), (0, -1), 5, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tbl


def section(title: str, subtitle: str | None = None, color=BLUE):
    items = [Spacer(1, 0.2 * cm), Paragraph(title, styles["H1"])]
    if subtitle:
        items.append(Paragraph(subtitle, styles["Subtitle"]))
    items.append(Spacer(1, 0.15 * cm))
    return KeepTogether(items)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 1.25 * cm, A4[0] - doc.rightMargin, 1.25 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT_REGULAR, 8)
    canvas.drawString(doc.leftMargin, 0.82 * cm, "SUN2 Lillehammer - Fibaro10 driftsmanual")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.82 * cm, f"Side {doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()


def register_fonts():
    global FONT_REGULAR, FONT_BOLD
    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), "ArialSUN2", "ArialSUN2-Bold"),
        (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf"), "SegoeSUN2", "SegoeSUN2-Bold"),
    ]
    for regular, bold, regular_name, bold_name in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont(regular_name, str(regular)))
            pdfmetrics.registerFont(TTFont(bold_name, str(bold)))
            FONT_REGULAR = regular_name
            FONT_BOLD = bold_name
            return


register_fonts()
styles.add(
    ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=28,
        leading=32,
        textColor=DARK_BLUE,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
)
styles.add(
    ParagraphStyle(
        "CoverSub",
        parent=styles["BodyText"],
        fontSize=12,
        leading=17,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=17,
        leading=21,
        textColor=DARK_BLUE,
        spaceBefore=10,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=15,
        textColor=DARK_BLUE,
        spaceBefore=9,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=9.4,
        leading=13.2,
        textColor=colors.HexColor("#26323f"),
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        "Subtitle",
        parent=styles["Body"],
        textColor=MUTED,
        fontSize=9.2,
        leading=12.5,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        "Callout",
        parent=styles["Body"],
        fontSize=9.1,
        leading=12.6,
        textColor=colors.HexColor("#26323f"),
    )
)
styles.add(
    ParagraphStyle(
        "Small",
        parent=styles["Body"],
        fontSize=8.2,
        leading=10.8,
        textColor=MUTED,
    )
)


def build_manual():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.9 * cm,
        rightMargin=1.9 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title="SUN2 driftsmanual",
        author="Fibaro10",
    )

    story = []
    if LOGO.exists():
        logo = Image(str(LOGO), width=5.1 * cm, height=1.45 * cm)
        logo.hAlign = "CENTER"
        story += [Spacer(1, 1.6 * cm), logo, Spacer(1, 1.0 * cm)]
    else:
        story += [Spacer(1, 2.2 * cm)]
    story += [
        Paragraph("Driftsmanual", styles["CoverTitle"]),
        Paragraph("Fibaro10 for SUN2 Lillehammer", styles["CoverSub"]),
        callout(
            "Hva denne manualen er",
            "Dette er en praktisk sluttbrukerveiledning for daglig bruk av appen: status, lys, ventilasjon, renhold, soling, energi, AI-søk og brukertilgang. Manualen er skrevet for deg som skal forstå hva systemet viser, og hva du bør sjekke når noe ser rart ut.",
            BLUE,
        ),
        Spacer(1, 0.45 * cm),
        table(
            [
                ["Versjon", "Dato", "Miljø"],
                ["1.0", datetime.now().strftime("%d.%m.%Y"), "QNAP 192.168.20.218:8110"],
            ],
            [4.2 * cm, 4.1 * cm, 7.9 * cm],
        ),
        PageBreak(),
    ]

    story += [
        section("1. Kort fortalt", "Appen samler drift, logger og historikk i ett grensesnitt som fungerer godt på mobil."),
        p(
            "Fibaro10 er laget for å gi rask oversikt for SUN2 Lillehammer. Den henter styringsdata fra HC3/Fibaro, logger egne hendelser for lys og ventilasjon, tar inn roboter fra Roborock_logger, importerer solingsstatistikk, og kan ta inn strømdata fra Elvia.",
            styles["Body"],
        ),
        callout(
            "Hovedprinsipp",
            "Start alltid på Status. Der ser du om dataene er ferske, om lys og vifter står slik de skal, og hvor du bør gå videre hvis noe virker feil.",
            BLUE,
        ),
        Spacer(1, 0.2 * cm),
        table(
            [
                ["Område", "Hva du bruker det til", "Når du typisk åpner det"],
                ["Status", "Nå-status, siste hendelser, dagslinje og hurtigvalg.", "Når du vil vite om alt går som det skal."],
                ["Lys", "Hendelser, luxlogg, dagsgraf, innstillinger og ntfy-varsel.", "Når utebelysningen skal kontrolleres."],
                ["Ventilasjon", "Viftehendelser, temperaturgraf, Yr-logg og styringsgrenser.", "Når temperatur eller lufting skal vurderes."],
                ["Renhold", "Robotstatus, neste jobb, batteri, vaskestatistikk og robotdetaljer.", "Når renholdsrobotene skal følges opp."],
                ["Soling", "Omsetning, solinger, topplister og ukesutvikling.", "Når du vil se salgs-/bruksutvikling."],
                ["Energi", "Import av Elvia-fil og oversikt over strømforbruk.", "Etter manuell månedsnedlasting fra Elvia."],
                ["Konto", "Bruker, tilgang, manual og utlogging.", "Når tilgang eller brukeradministrasjon skal håndteres."],
            ],
            [2.7 * cm, 7.4 * cm, 6.1 * cm],
        ),
    ]

    story += [
        section("2. Innlogging og meny", "Menyen er bygd for mobil først, men fungerer også på stor skjerm."),
        bullets(
            [
                "Logg inn med brukernavn og passord du har fått tildelt.",
                "Hovedmenyen viser de store områdene: Status, Lys, Ventilasjon, Renhold, Soling, Energi, AI og Konto.",
                "Når du åpner et hovedområde, vises undermenyen for akkurat dette området.",
                "På stor skjerm kan menyen krympes til bare ikoner med menyknappen.",
                "Aktivt hovedområde og aktiv underside markeres med fargen for området.",
            ],
            styles["Body"],
        ),
        callout(
            "Tilgangsnivå",
            "Master kan opprette og se brukere. Admin kan endre innstillinger. Lesetilgang kan bruke oversiktene uten å endre regler eller brukere.",
            PURPLE,
        ),
    ]

    story += [
        section("3. Status-dashboard", "Dette er forsiden og kontrollrommet."),
        p(
            "Status viser det viktigste akkurat nå: gjennomsnittlig innetemperatur, utetemperatur, lux og Yr-data. Kortene under viser ventilasjon, lys, siste hendelser og datastatus.",
            styles["Body"],
        ),
        table(
            [
                ["Felt", "Forklaring", "God bruk"],
                ["Innetemp", "Snitt av 1.etg, 2.etg og VIP. De tre enkeltverdiene vises ved siden av.", "Se raskt om lokalet er for varmt eller for kaldt."],
                ["Utetemp", "Snitt av uteverdi og Yr API når begge finnes.", "Nyttig når ventilasjon vurderer om uteluft kan brukes."],
                ["LUX", "Siste loggede lux-verdi fra lysstyringen.", "Forklarer hvorfor fasade- og inngångslys er på eller av."],
                ["Yr / Vær", "Værtype, temperatur, nedbør og fremtidig temperatur.", "Brukes for å vurdere lufting og forventet utvikling."],
                ["Datastatus", "Viser om temp, lux og Yr logger ferske data.", "Hvis en flis blir gul/rød, start feilsøking der."],
            ],
            [3.1 * cm, 7.4 * cm, 5.7 * cm],
        ),
        callout(
            "Nyttig ny snarvei",
            "Dashboardet har hurtigkort til Dagslinje, Lux mot i går, Temperaturgraf og denne manualen. De er laget for å spare trykk på mobil.",
            BLUE,
        ),
    ]

    story += [
        section("4. Lys", "Utebelysningen styres av lux, tid og regelsettet i HC3/Fibaro."),
        p(
            "Lysdelen viser bade hva som faktisk skjedde, og hva luxsensoren matte gjennom dagen. Dette gjør det lettere å se om lysene styrer etter hensikten, spesielt ved skiftende vær.",
            styles["Body"],
        ),
        table(
            [
                ["Side", "Hva du ser", "Tips"],
                ["Hendelser", "På/av-hendelser med lysnavn, lux og årsaken som ble logget.", "Bruk filter på enhet eller tekst når du leter etter en bestemt lampe."],
                ["Lux logg", "Rader fra 5-minutters loggingen.", "Best for detaljkontroll og eksport."],
                ["Dagslogg", "Graf over lux gjennom dagen.", "Huk av 'Sammenlign med dagen før' for å se om dagen skiller seg fra i går."],
                ["Innstillinger", "Synlige styringsverdier og id/navn-oppsett.", "Endre terskler forsiktig og test etterpa."],
            ],
            [3.1 * cm, 7.7 * cm, 5.4 * cm],
        ),
        callout(
            "Varsler på mobil",
            "Trykk 'Abonner varsler' under Lys på Status. Mobilen åpner ntfy-appen og abonnerer på lysvarsel. Da får du melding når lys slås på eller av.",
            LIGHT,
        ),
        p(
            "Dagsgrafen bruker en delt lux-skala: lave luxverdier får god plass, samtidig som sterke solverdier fortsatt kan vises. Dette gjør grafen mer lesbar enn en ren logåritmisk skala.",
            styles["Body"],
        ),
    ]

    story += [
        section("5. Ventilasjon", "Ventilasjonssiden forklarer hvorfor viftene starter og stopper."),
        p(
            "Ventilasjon bygger på temperatur inne, ute, loft, passiv innluft, effektforskjell og åpningstid. Tanken er å kjøle når det er nyttig, unngå unødig varmetap og samtidig unngå undertrykk når avtrekk går.",
            styles["Body"],
        ),
        table(
            [
                ["Vifte", "Rolle", "Hva du ser etter"],
                ["Innluft VIP", "Gir frisk luft til VIP-sonen.", "Forholder seg mest til VIP-temperatur og om uteluft er egnet."],
                ["Innluft 2.etg", "Gir frisk luft mot 1.etg/2.etg.", "Forholder seg mer til temperatur i 1.etg og 2.etg."],
                ["Avtrekk tak/loft", "Trekker varm luft ut fra loftet.", "Skal normalt ikke gå hvis det er for kaldt ute eller hvis vi vil spare varme."],
            ],
            [3.6 * cm, 6.2 * cm, 6.4 * cm],
        ),
        bullets(
            [
                "Hendelser viser akkurat hvilken vifte som skiftet status og hvorfor.",
                "Temp logg viser 5-minutters målinger av temperaturer, modus og viftestatus.",
                "Dagslogg temperatur viser flere temperaturkurver samtidig og vertikale streker for vifte på/av.",
                "Yr logg viser værdata fra Yr API når appen har hentet nytt varsel.",
                "Innstillinger viser grenseverdier slik at logikken er synlig uten å åpne HC3.",
            ],
            styles["Body"],
        ),
        callout(
            "Varsler på mobil",
            "Trykk 'Abonner varsler' under Ventilasjon på Status. Da får du ntfy-varsel når en vifte slar seg på eller av.",
            VENT,
        ),
    ]

    story += [
        section("6. Renhold", "Renhold viser robotene som Roborock_logger leser inn."),
        p(
            "Roborock_logger er laget som en egen lokal innlesningsapp. Den leser roboter som er delt med loggerkontoen, og poster status, planlagte jobber og jobbhistorikk videre til Fibaro10.",
            styles["Body"],
        ),
        table(
            [
                ["Felt", "Betydning"],
                ["Online/offline", "Om Roborock-clouden rapporterer roboten tilgjengelig."],
                ["Status", "Oversatt statuskode fra roboten, for eksempel klar, lader eller vasker."],
                ["Batteri", "Batterinivå i prosent."],
                ["Neste jobb", "Neste planlagte rengjøring i lesbar tekst."],
                ["WiFi-signal", "Signalstyrke, tidligere vist som RSSI. Svak verdi kan forklare ustabil status."],
                ["Siste vask", "Tidspunkt og areal fra siste registrerte jobb."],
            ],
            [4.3 * cm, 11.9 * cm],
        ),
        callout(
            "Når ny robot legges til",
            "Del roboten med roborock.sun2-kontoen, sjekk at Roborock_logger finner den, og kontroller deretter Renhold > Oversikt i Fibaro10.",
            CLEAN,
        ),
    ]

    story += [
        section("7. Soling", "Soling gir historikk, topplister og ukesutvikling."),
        p(
            "Soling bygger på importerte romstatistikker fra SUN2-systemet. Oversikten viser beste dager og måneder, totalt inntjent, antall solinger, soltid og en ukegraf der flere år kan sammenlignes.",
            styles["Body"],
        ),
        bullets(
            [
                "Bruk avhukingsboksene i ukegrafen til å velge hvilke år som skal vises.",
                "Velg Inntjent eller Solinger for å bytte måling i samme diagram.",
                "Detaljer-siden viser radene som ligger bak summeringene.",
                "Historikken kan bygges opp på nytt fra importfilene hvis datagrunnlaget skal ryddes.",
            ],
            styles["Body"],
        ),
        callout(
            "Forbedring i denne versjonen",
            "Valg av år i ukegrafen huskes i nettleseren, og år-velgeren håndterer nå tekst/tall konsekvent.",
            BLUE,
        ),
    ]

    story += [
        section("8. Energi og Elvia", "Energi er forelopig bygget rundt manuell Elvia-import."),
        p(
            "Elvia-data ligger bak BankID, derfor lastes filen ned manuelt og importeres i appen. Importen lagrer data per time, og samme fil kan importeres på nytt uten dobbeltelling.",
            styles["Body"],
        ),
        table(
            [
                ["Oppgåve", "Slik gjør du"],
                ["Last ned fil", "Logg inn hos Elvia, eksporter JSON for perioden du vil importere."],
                ["Importer", "Gå til Energi > Elvia, velg fil og trykk Importer."],
                ["Kontroller", "Se totalsummer, årsoppsummering, toppdager og toppmåneder."],
                ["Innevarende måned", "Det er greit å importere delvis måned. Appen markerer ufullstendige måneder i importresultatet."],
            ],
            [4.3 * cm, 11.9 * cm],
        ),
    ]

    story += [
        section("9. AI-søk", "AI-søk er laget for frie spørsmål mot datasettene."),
        p(
            "AI-søk kan bruke definerte datasett og SQL-spørringer med sikkerhetsbegrensninger. For at dette skal virke må OpenAI API-nøkkel og aktiv billing være på plass. ChatGPT Pro-abonnement er ikke det samme som API-kreditt.",
            styles["Body"],
        ),
        bullets(
            [
                "Legg inn API-nokkel under AI > Innstillinger.",
                "Still spørsmål som: 'Hvilke lys hadde flest hendelser siste 7 dager?'",
                "Bruk resultatene som analysehjelp, ikke som eneste sannhet ved feilsøking.",
                "Hvis du får quota-feil, må API-kontoen ha tilgjengelig kreditt/billing.",
            ],
            styles["Body"],
        ),
    ]

    story += [
        section("10. Feilsøking", "Start med det enkle: er data ferske, og finnes siste hendelse?"),
        table(
            [
                ["Symptom", "Sannsynlig årsak", "Forste kontroll"],
                ["Lys virker ikke riktig", "Luxverdi, tidsregel eller HC3-scene.", "Status > Lys, deretter Lys > Dagslogg."],
                ["Vifte starter ikke", "Temperaturgrense, åpningstid, ute for kaldt eller manglende styring.", "Ventilasjon > Hendelser og Dagslogg temperatur."],
                ["Datastatus er rød", "Logger poster ikke eller kilde er nede.", "Sjekk siste tidspunkt og aktuell logger/scene."],
                ["Robot mangler", "Ikke delt med loggerkonto, logger ikke startet eller nettverksproblem.", "Roborock_logger-status og Renhold > Oversikt."],
                ["Soling/energi er tregt", "Mye historikk eller stor import.", "Vent litt, bruk filter, og kontroller importstatus."],
                ["AI virker ikke", "API-nokkel/billing mangler.", "AI > Innstillinger og eventuell feilmelding."],
            ],
            [4.1 * cm, 6.0 * cm, 6.1 * cm],
        ),
        callout(
            "Tommelregel",
            "Hvis Status ser riktig ut, men en detaljside ser feil ut, er det ofte filter eller historikkvisning. Hvis Status er feil, er det oftere logging, HC3-scene eller ekstern kilde.",
            PURPLE,
        ),
    ]

    story += [
        PageBreak(),
        section("11. Daglig og månedlig rutine", "En enkel rutine gir rask trygghet uten å overstyre systemet."),
        table(
            [
                ["Når", "Hva du sjekker", "Hvor"],
                ["Daglig", "Nå-status, datastatus og siste hendelser.", "Status"],
                ["Ved morke/lys-feil", "Luxgraf og lys-hendelser.", "Lys > Dagslogg / Hendelser"],
                ["Ved varme/kulde", "Temperaturkurver, vifteendringer og modus.", "Ventilasjon > Dagslogg"],
                ["Ukentlig", "Robotstatus og kommende jobber.", "Renhold > Oversikt"],
                ["Manedlig", "Elvia-fil og solingstopplister.", "Energi > Elvia / Soling > Oversikt"],
                ["Ved regelendring", "Endre verdi, test og se etter ny hendelse/logg.", "Innstillinger + aktuell logg"],
            ],
            [3.1 * cm, 7.0 * cm, 6.1 * cm],
        ),
        Spacer(1, 0.25 * cm),
        callout(
            "Det viktigste for sluttbruker",
            "Du trenger ikke forstå all kode. Du trenger å vite hvor systemet viser status, hvor hendelser forklares, og hvor du ser om dataene er ferske. Resten kan du bruke når du skal grave dypere.",
            BLUE,
        ),
    ]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(build_manual())

