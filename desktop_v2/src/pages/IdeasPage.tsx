import { Card, Space, Tag, Typography } from "antd";
import { Navigate, useParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { defaultModuleView, MODULE_VIEWS } from "../moduleViews";
import "../styles/ideas.css";

type IdeaStatus = "Klar å bygge" | "Bør vurderes" | "Krever datagrunnlag" | "Eksperiment";
type IdeaImpact = "Høy" | "Middels" | "Lav";
type IdeaArea = "Omsetning" | "Parkering" | "Soling" | "Energi" | "Drift" | "Admin" | "AI";

type Idea = {
  id: string;
  title: string;
  summary: string;
  area: IdeaArea;
  status: IdeaStatus;
  impact: IdeaImpact;
  target: string;
  reason: string;
  build: string[];
  checks: string[];
  icon: string;
};

const ideaStatusClass: Record<IdeaStatus, string> = {
  "Klar å bygge": "ready",
  "Bør vurderes": "review",
  "Krever datagrunnlag": "data",
  Eksperiment: "experiment",
};

const impactClass: Record<IdeaImpact, string> = {
  Høy: "high",
  Middels: "medium",
  Lav: "low",
};

const ideas: Idea[] = [
  {
    id: "revenue-change-ledger",
    title: "Endringsforklaring for omsetning",
    summary: "Vis hvorfor dagens omsetning endret seg siden forrige oppdatering, med kilde og før/etter-tall.",
    area: "Omsetning",
    status: "Klar å bygge",
    impact: "Høy",
    target: "Omsetning og Dashboard",
    reason:
      "Når EasyPark eller Sun2 oppdaterer gamle rader kan totalen flytte seg uten nye hendelser. Dette bør være synlig direkte på kortet.",
    build: [
      "Lagre periodiske snapshots av nøkkeltall.",
      "Sammenligne siste snapshot mot forrige per kilde.",
      "Vise hvilke importjobb(er) som endret sum, antall og beløp.",
    ],
    checks: [
      "Må skille mellom ny rad, oppdatert rad og korrigert beløp.",
      "Må bruke samme kuttetidspunkt som dashboard-kortene.",
    ],
    icon: "OK",
  },
  {
    id: "settlement-control-center",
    title: "Oppgjørskontroll samlet",
    summary: "Ett kontrollbilde som viser parkering, soling og produkter mot innleste oppgjør.",
    area: "Omsetning",
    status: "Bør vurderes",
    impact: "Høy",
    target: "Omsetning",
    reason:
      "Oppgjør ligger i dag på ulike fagområder. En samlet kontrollflate gjør det enklere å se om måneden er ferdig avstemt.",
    build: [
      "Samle kontrollstatus fra Parkering/Oppgjør og Soling/Oppgjør.",
      "Legge inn avvik per måned, status og lenke til originalbilag.",
      "Markere manglende bilag, manglende systemgrunnlag og mistenkelige avvik.",
    ],
    checks: [
      "Må ikke erstatte detaljsidene for parkering og soling.",
      "Bør kunne filtreres på år og status.",
    ],
    icon: "OP",
  },
  {
    id: "parking-source-reconciliation",
    title: "Parkeringskilde-avstemming",
    summary: "Kontroller EasyPark, Flowbird/ParkNordic, biloppslag og område mot hverandre.",
    area: "Parkering",
    status: "Klar å bygge",
    impact: "Høy",
    target: "Parkering",
    reason:
      "Mangler i område, kjøretøydata og kilde kan gi feil analyser. Dette samler avvikene i en operativ arbeidsliste.",
    build: [
      "Liste biler uten område, kjøretøy eller eierdata.",
      "Skille SVV, Sverige og Danmark som egne kilder.",
      "Vise siste forsøk, neste forsøk og konkret feilmelding per bil.",
    ],
    checks: [
      "Må unngå at eksterne oppslag trigges direkte fra visningssiden.",
      "Bør ha tydelig manuell overstyring der oppslag ikke finner bilen.",
    ],
    icon: "PK",
  },
  {
    id: "sun-image-review-queue",
    title: "Bildekontroll-kø for soltimer",
    summary: "En rask arbeidsflate for soltimer som mangler eller har usikkert hovedbilde.",
    area: "Soling",
    status: "Klar å bygge",
    impact: "Middels",
    target: "Soling",
    reason:
      "Bildene er viktige for etterkontroll, men dagens detaljvisning er tung når mange timer skal kontrolleres etter hverandre.",
    build: [
      "Kø sortert på nyeste soltimer med manglende/usikkert bilde.",
      "Fast bildevisning med fem kandidater og tastaturstyring.",
      "Handlinger for sett hovedbilde, hopp over og marker ok.",
    ],
    checks: [
      "Må ikke endre arkivbilder uten eksplisitt lagring.",
      "Må vise Sun2-id, rom og klokkeslett tydelig.",
    ],
    icon: "BI",
  },
  {
    id: "link-confidence-lab",
    title: "Koblingslab for parkering og soling",
    summary: "Forklar hvorfor en bil og en Sun2-id sannsynligvis hører sammen.",
    area: "AI",
    status: "Eksperiment",
    impact: "Høy",
    target: "Koble",
    reason:
      "Koblingsmotoren gir verdi først når det er raskt å forstå hvorfor et forslag er godt eller svakt.",
    build: [
      "Vis tidslinje per kandidat med parkering og soltimer på samme akse.",
      "Score kriterier: antall treff, tidsavstand, gjentakelse, motbevis og siste observasjon.",
      "La bekreftede koblinger brukes som treningsgrunnlag for bedre scoring.",
    ],
    checks: [
      "Må vise både positive og negative indikasjoner.",
      "Må aldri automatisk bekrefte koblinger uten manuell beslutning.",
    ],
    icon: "KO",
  },
  {
    id: "import-calendar",
    title: "Importkalender og forventet neste kjøring",
    summary: "En kalender/linje som viser planlagte og faktiske importer med avvik.",
    area: "Drift",
    status: "Klar å bygge",
    impact: "Middels",
    target: "Admin og Dashboard",
    reason:
      "Når en import ikke har kjørt, eller neste import ikke stemmer med forventning, bør det være synlig uten å lese logg.",
    build: [
      "Samle planlagte tidspunkter fra hver jobb.",
      "Vise faktisk kjørt, varighet, status og forsinkelse.",
      "Varsle når en kilde er eldre enn forventet.",
    ],
    checks: [
      "Må skille faste tidspunkt fra intervallbaserte jobber.",
      "Bør vise lokal tid konsekvent.",
    ],
    icon: "TI",
  },
  {
    id: "energy-revenue-model",
    title: "Energi mot inntekt",
    summary: "Koble strøm, Elvia, soltimer og omsetning for å se margin og avvik.",
    area: "Energi",
    status: "Krever datagrunnlag",
    impact: "Middels",
    target: "Energi",
    reason:
      "Når strømforbruk per seng og inntekt kan sees sammen, blir det enklere å oppdage feil i måling, drift eller prising.",
    build: [
      "Beregne kostnad per dag/time/seng fra egne målere og Elvia.",
      "Koble forbruk mot faktisk soltid og omsetning.",
      "Vise avvik mellom forventet og målt forbruk.",
    ],
    checks: [
      "Må håndtere umålte laster og kjente differanser.",
      "Må bruke kvalitetsscore når energigrunnlaget er ufullstendig.",
    ],
    icon: "EN",
  },
  {
    id: "data-quality-inbox",
    title: "Datakvalitet som innboks",
    summary: "En felles innboks for ting som må rettes, bekreftes eller følges opp.",
    area: "Admin",
    status: "Bør vurderes",
    impact: "Høy",
    target: "Admin",
    reason:
      "Mange gode funksjoner ender som lister på ulike sider. En innboks kan gjøre daglig rydding mer effektivt.",
    build: [
      "Generere oppgaver fra manglende område, manglende kjøretøydata, oppgjørsavvik og importfeil.",
      "Gi hver oppgave ansvar, alvorlighet og lenke til riktig skjerm.",
      "Arkivere oppgaver automatisk når datagrunnlaget er rettet.",
    ],
    checks: [
      "Må ikke bli en ny parallell datamodell for alt.",
      "Må støtte raske massehandlinger.",
    ],
    icon: "DQ",
  },
  {
    id: "prognose-explainer",
    title: "Forklarbar prognose",
    summary: "Vis hvilke faktorer som trekker prognosen opp eller ned.",
    area: "Omsetning",
    status: "Eksperiment",
    impact: "Middels",
    target: "Omsetning, Parkering og Soling",
    reason:
      "Prognoser blir mer nyttige når man ser hvorfor de endrer seg, spesielt vær, ukedag, historikk og importstatus.",
    build: [
      "Lage faktorbidrag per prognosekjøring.",
      "Vise endring fra forrige prognose.",
      "Markere når prognosen er svekket av ferskhetsproblemer i datakilder.",
    ],
    checks: [
      "Må ikke gi falsk presisjon.",
      "Bør starte som forklaringsvisning før selve modellen gjøres mer avansert.",
    ],
    icon: "PR",
  },
  {
    id: "alert-rules",
    title: "Varslingsregler",
    summary: "Egne regler for avvik: import stoppet, omsetning faller, biloppslag feiler eller energi avviker.",
    area: "Drift",
    status: "Bør vurderes",
    impact: "Middels",
    target: "Admin",
    reason:
      "Systemet har mange gode data, men feil må bli operative varsler før de blir oppdaget tilfeldig.",
    build: [
      "Regelmotor med terskel, stillhetstid og alvorlighet.",
      "Varsler i appen først, senere e-post/push.",
      "Historikk over lukkede varsler og falske positive.",
    ],
    checks: [
      "Må være lett å dempe støy.",
      "Bør bruke datakilde-ferskhet og kjente åpningstider.",
    ],
    icon: "VA",
  },
  {
    id: "audit-safe-actions",
    title: "Sikker handlingslogg",
    summary: "Logg manuelle endringer, hvem som gjorde dem og hva som ble endret.",
    area: "Admin",
    status: "Klar å bygge",
    impact: "Høy",
    target: "Admin",
    reason:
      "Når mer redigering flyttes inn i V2 bør endringer være sporbare, spesielt rundt bildata, oppgjør og manuelle koblinger.",
    build: [
      "Felles audit-tabell for manuelle endringer.",
      "Vis historikk på detaljsider.",
      "Støtte for før/etter-verdi og teknisk kilde.",
    ],
    checks: [
      "Må ikke logge hemmeligheter eller tokens.",
      "Bør kobles til eksisterende innlogging.",
    ],
    icon: "AU",
  },
  {
    id: "api-health-map",
    title: "Avhengighetskart for datakilder",
    summary: "Vis hvilke tjenester, containere, API-er og jobber hver side er avhengig av.",
    area: "Drift",
    status: "Bør vurderes",
    impact: "Lav",
    target: "Admin",
    reason:
      "Når noe feiler er det raskere å forstå konsekvensen hvis appen viser hvilke sider som påvirkes.",
    build: [
      "Kartlegge hver ekstern og intern datakilde.",
      "Vise tilstand, siste feil og berørte moduler.",
      "Lenke fra datakildedetalj til relevante sider.",
    ],
    checks: [
      "Må vedlikeholdes sammen med nye jobber.",
      "Bør starte med de viktigste importene.",
    ],
    icon: "API",
  },
];

const viewConfig: Record<
  string,
  {
    title: string;
    description: string;
    filter?: (idea: Idea) => boolean;
  }
> = {
  oversikt: {
    title: "Idéoversikt",
    description: "Forslag som kan vurderes før de flyttes inn i riktig modul.",
  },
  kontroll: {
    title: "Kontroll og avvik",
    description: "Funksjoner som gjør tall, importer og oppgjør enklere å etterprøve.",
    filter: (idea) =>
      ["revenue-change-ledger", "settlement-control-center", "parking-source-reconciliation", "data-quality-inbox", "audit-safe-actions"].includes(
        idea.id,
      ),
  },
  innsikt: {
    title: "Analyse og innsikt",
    description: "Forslag som gjør historikk, prognoser og sammenhenger mer nyttige.",
    filter: (idea) =>
      ["energy-revenue-model", "prognose-explainer", "link-confidence-lab", "settlement-control-center"].includes(idea.id),
  },
  automatisering: {
    title: "Automatisering",
    description: "Forslag som reduserer manuelt arbeid, men fortsatt holder kontrollen synlig.",
    filter: (idea) =>
      ["import-calendar", "alert-rules", "sun-image-review-queue", "parking-source-reconciliation", "data-quality-inbox"].includes(idea.id),
  },
  arbeidsflyt: {
    title: "Arbeidsflyt",
    description: "Skjermer og køer som gjør daglige oppgaver raskere å gjennomføre.",
    filter: (idea) =>
      ["sun-image-review-queue", "data-quality-inbox", "link-confidence-lab", "api-health-map", "audit-safe-actions"].includes(idea.id),
  },
};

function areaTone(area: IdeaArea): string {
  if (area === "Omsetning") return "revenue";
  if (area === "Parkering") return "parking";
  if (area === "Soling") return "sun2";
  if (area === "Energi") return "energy";
  if (area === "Drift") return "vent";
  if (area === "AI") return "ideas";
  return "status";
}

function IdeaCard({ idea }: { idea: Idea }) {
  return (
    <Card className={`idea-card idea-area-${areaTone(idea.area)}`}>
      <div className="idea-card-head">
        <div className="idea-icon" aria-hidden="true">
          <span>{idea.icon}</span>
        </div>
        <div className="idea-title-block">
          <Typography.Text className="idea-area">{idea.area}</Typography.Text>
          <Typography.Title level={3}>{idea.title}</Typography.Title>
        </div>
        <div className="idea-tags">
          <Tag className={`idea-impact ${impactClass[idea.impact]}`}>{idea.impact} nytte</Tag>
          <Tag className={`idea-status ${ideaStatusClass[idea.status]}`}>{idea.status}</Tag>
        </div>
      </div>
      <Typography.Paragraph className="idea-summary">{idea.summary}</Typography.Paragraph>
      <div className="idea-target">
        <span>Flyttes trolig til</span>
        <strong>{idea.target}</strong>
      </div>
      <div className="idea-detail-grid">
        <div>
          <Typography.Text className="idea-section-label">Hvorfor</Typography.Text>
          <p>{idea.reason}</p>
        </div>
        <div>
          <Typography.Text className="idea-section-label">Må bygges</Typography.Text>
          <ul>
            {idea.build.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <Typography.Text className="idea-section-label">Kontrollpunkter</Typography.Text>
          <ul>
            {idea.checks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

function IdeaSummaryStrip({ visibleIdeas }: { visibleIdeas: Idea[] }) {
  const ready = visibleIdeas.filter((idea) => idea.status === "Klar å bygge").length;
  const high = visibleIdeas.filter((idea) => idea.impact === "Høy").length;
  const data = visibleIdeas.filter((idea) => idea.status === "Krever datagrunnlag").length;
  const areas = new Set(visibleIdeas.map((idea) => idea.area)).size;

  return (
    <div className="ideas-summary-grid">
      <div className="ideas-summary-card">
        <span>Forslag</span>
        <strong>{visibleIdeas.length}</strong>
      </div>
      <div className="ideas-summary-card">
        <span>Klar å bygge</span>
        <strong>{ready}</strong>
      </div>
      <div className="ideas-summary-card">
        <span>Høy nytte</span>
        <strong>{high}</strong>
      </div>
      <div className="ideas-summary-card">
        <span>Områder</span>
        <strong>{areas}</strong>
      </div>
      <div className="ideas-summary-card">
        <span>Krever datagrunnlag</span>
        <strong>{data}</strong>
      </div>
    </div>
  );
}

function NextMovePanel({ visibleIdeas }: { visibleIdeas: Idea[] }) {
  const topIdeas = [...visibleIdeas]
    .sort((a, b) => {
      const impactRank = { Høy: 0, Middels: 1, Lav: 2 };
      const statusRank = { "Klar å bygge": 0, "Bør vurderes": 1, Eksperiment: 2, "Krever datagrunnlag": 3 };
      return impactRank[a.impact] - impactRank[b.impact] || statusRank[a.status] - statusRank[b.status];
    })
    .slice(0, 3);

  return (
    <Card className="ideas-next-card">
      <div className="ideas-next-head">
        <span className="ideas-next-symbol" aria-hidden="true">ID</span>
        <div>
          <Typography.Title level={3}>Forslag til neste grep</Typography.Title>
          <Typography.Text type="secondary">Prioritert etter nytte og hvor klart det er å bygge.</Typography.Text>
        </div>
      </div>
      <div className="ideas-next-list">
        {topIdeas.map((idea, index) => (
          <div className="ideas-next-row" key={idea.id}>
            <span className="ideas-next-rank">{index + 1}</span>
            <div>
              <strong>{idea.title}</strong>
              <span>{idea.target}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function IdeasPage() {
  const params = useParams();
  const view = params.view ?? defaultModuleView("ideer");
  const viewItems = MODULE_VIEWS.ideer ?? [];
  const isKnownView = viewItems.some((item) => item.key === view);
  const config = viewConfig[view] ?? viewConfig.oversikt;

  if (!isKnownView) return <Navigate to="/ideer/oversikt" replace />;

  const visibleIdeas = config.filter ? ideas.filter(config.filter) : ideas;

  return (
    <Space direction="vertical" size={14} className="page-stack ideas-page">
      <PageHeader
        eyebrow="Utvikling"
        title={config.title}
        description={config.description}
        meta={<Tag className="ideas-lab-tag">Vurderingsflate</Tag>}
      />
      <IdeaSummaryStrip visibleIdeas={visibleIdeas} />
      <NextMovePanel visibleIdeas={visibleIdeas} />
      <div className="ideas-card-grid">
        {visibleIdeas.map((idea) => (
          <IdeaCard idea={idea} key={idea.id} />
        ))}
      </div>
    </Space>
  );
}
