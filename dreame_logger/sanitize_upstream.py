from pathlib import Path


path = Path("/vendor/custom_components/dreame_vacuum/dreame/protocol.py")
source = path.read_text(encoding="utf-8")
analytics_endpoint = (
    "aHR0cHM6Ly93d3cuZ29vZ2xlLWFuYWx5dGljcy5jb20vbXAvY29sbGVjdD9tZWFzdXJlbWVudF9pZD1HLTcwN1g2N0MzWlAmYXBpX3NlY3JldD1jX2taVDJlV1N1Q3Q4Q2swTGdtaE1n"
)
disabled_endpoint = "aHR0cDovLzEyNy4wLjAuMTo5L2RyZWFtZS1hbmFseXRpY3MtZGlzYWJsZWQ="
if analytics_endpoint not in source:
    raise SystemExit("Expected upstream analytics endpoint was not found")
path.write_text(source.replace(analytics_endpoint, disabled_endpoint), encoding="utf-8")

