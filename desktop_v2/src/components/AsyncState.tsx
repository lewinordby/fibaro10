import { Alert, Spin } from "antd";

export function LoadingBlock() {
  return (
    <div className="loading-block">
      <Spin size="large" />
    </div>
  );
}

export function ErrorBlock({ error }: { error: unknown }) {
  return (
    <Alert
      type="error"
      showIcon
      message="Kunne ikke hente data"
      description={error instanceof Error ? error.message : "Ukjent feil"}
    />
  );
}
