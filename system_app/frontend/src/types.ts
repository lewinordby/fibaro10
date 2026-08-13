export type SystemNotificationChannel = {
  key: string;
  title: string;
  area: string;
  description: string;
  triggers: string[];
  priority: string;
  configured: boolean;
  publishingEnabled: boolean;
  subscribeUrl?: string;
  webUrl?: string;
};
export type SystemNotificationsData = {
  provider: string;
  providerUrl?: string;
  privacy: string;
  summary: { channels: number; configured: number; publishing: number };
  subscriptions: SystemNotificationChannel[];
  setup: string[];
};

export type SystemSubsystem = {
  component: string;
  title: string;
  area: string;
  role: string;
  runtime: string;
  compose_service?: string;
  status: string;
  criticality: string;
  access: "external" | "local" | "internal";
  primary_url?: string;
  links: Array<{ kind: "public" | "local" | "health"; label: string; url: string }>;
};

export type SystemSubsystemsData = {
  summary: { components: number; active: number; critical: number; web_interfaces: number };
  subsystems: SystemSubsystem[];
};
