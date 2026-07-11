// Mock data sources for the demo dashboard.

export const nodes = [
  { name: "aurora-01", region: "eu-north", status: "online" },
  { name: "meridian-04", region: "us-east", status: "degraded" },
  { name: "kelvin-09", region: "ap-south", status: "online" },
  { name: "polaris-02", region: "sa-east", status: "offline" },
];

export const signals = [
  { source: "aurora-01", type: "telemetry", status: "online" },
  { source: "meridian-04", type: "heartbeat", status: "degraded" },
  { source: "kelvin-09", type: "telemetry", status: "online" },
];
