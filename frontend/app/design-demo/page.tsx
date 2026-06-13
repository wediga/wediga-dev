import Nav from "@/components/site/Nav";
import Kicker from "@/components/site/Kicker";
import DisplayHeading from "@/components/site/DisplayHeading";
import NodeEdge from "@/components/site/NodeEdge";
import MetaRow from "@/components/site/MetaRow";
import SkillRow from "@/components/site/SkillRow";
import TextLink from "@/components/site/TextLink";
import Footer from "@/components/site/Footer";
import FlightDeck from "@/components/flight/FlightDeck";
import FlightStation from "@/components/flight/FlightStation";

/**
 * /design-demo proves the whole V1 visual system in one place: the cosmos
 * (mounted in this surface's layout), the flight engine with four stations and every
 * base component. The Footer is handed to FlightDeck so it lives inside the same
 * scroll context as the stations, instead of sitting under the fixed stage. It
 * sits outside the route groups, is linked from no nav and is clearly separate
 * from the real landing. It does NOT import lib/content and does NOT touch the
 * real data flow, so the content E2E on / stays untouched.
 *
 * The copy is placeholder wording, final text comes from the admin later.
 */

const STATION_LABELS = ["Intro", "About", "Toolkit", "Access"];

export default function DesignDemoPage() {
  return (
    <main className="relative">
      <Nav />

      <FlightDeck labels={STATION_LABELS} footer={<Footer />}>
        <FlightStation>
          <Kicker>{"// machine learning engineer"}</Kicker>
          <div className="mt-5">
            <DisplayHeading as="h1">Alexander Wedig.</DisplayHeading>
          </div>
          <p className="mt-6 max-w-[52ch] text-lg text-muted">
            I build models and the systems around them, from the first
            notebook to the service that serves predictions, and I care about
            the parts that survive contact with production.
          </p>
          <MetaRow
            status="Open to ML and Data roles"
            location="Germany"
            stack="Python, PyTorch, FastAPI"
          />
        </FlightStation>

        <FlightStation>
          <NodeEdge label="about" />
          <p className="max-w-[54ch] text-2xl leading-snug text-ink">
            I like problems that sit between data and a real decision, where a
            model is only useful once it ships and someone trusts the answer.
          </p>
          <p className="mt-6 max-w-[54ch] text-muted">
            Most of my work starts messy, with data that does not match the
            documentation, and the interesting part is turning that into
            something measurable, deployed and quiet enough to forget about.
          </p>
        </FlightStation>

        <FlightStation>
          <NodeEdge label="toolkit" />
          <DisplayHeading as="h2">What I work with</DisplayHeading>
          <div className="mt-10">
            <SkillRow
              group="Machine learning"
              tools="PyTorch, scikit-learn, XGBoost, Optuna"
            />
            <SkillRow
              group="Data and backend"
              tools="Python, FastAPI, PostgreSQL, Polars"
            />
            <SkillRow
              group="Build and ship"
              tools="Docker, GitHub Actions, Caddy, Linux"
            />
          </div>
        </FlightStation>

        <FlightStation>
          <NodeEdge label="access" />
          <p className="max-w-[52ch] text-2xl leading-snug text-ink">
            Some of this site opens up once you are signed in.
          </p>
          <p className="mt-6 max-w-[52ch] text-muted">
            If you reached me through a personal link, it carries you straight
            to the parts meant for you, and the rest stays one click away
            behind a login.
          </p>
          <div className="mt-9 flex flex-wrap gap-7">
            <TextLink href="/login">Login</TextLink>
            <TextLink href="/login">Open recruiter link</TextLink>
          </div>
        </FlightStation>
      </FlightDeck>
    </main>
  );
}
