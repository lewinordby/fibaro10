import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MosaicIcon } from "../../packages/microapp-ui/src/components/MosaicIcon";
import { SummaryStrip } from "../../operations_app/frontend/src/components/doors/shared";

describe("critical shared microapp components", () => {
  it("renders an accessible icon without leaking layout text", () => {
    const markup = renderToStaticMarkup(<MosaicIcon name="door" />);
    expect(markup).toContain("aria-hidden=\"true\"");
    expect(markup).toContain("<svg");
  });

  it("renders every door summary value and explanation", () => {
    const markup = renderToStaticMarkup(
      <SummaryStrip items={[
        { label: "Solrom ledige", value: 8, detail: "av 12 rom", color: "green" },
        { label: "Krever kontroll", value: 1, detail: "sensor mangler", color: "yellow" },
      ]} />,
    );
    expect(markup).toContain("Solrom ledige");
    expect(markup).toContain("av 12 rom");
    expect(markup).toContain("Krever kontroll");
    expect(markup).toContain("sensor mangler");
  });
});
