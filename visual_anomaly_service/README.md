# Visual anomaly service

Local, CPU-only PatchCore-style anomaly detection for the three fixed pullert
views and the stairs at Solstudio. The service learns normal appearance from the
existing Protect snapshot archive and returns an independent anomaly score plus
a heatmap.

The service never moves, aligns, scales or perspective-corrects source camera
frames. Fixed source pixels are cropped first. Small object regions are then
copied into a deterministic 512 px analysis atlas so the feature model retains
useful detail. The atlas is converted to locally contrast-normalized grayscale
before feature extraction so daylight, shadows and white balance have less
influence than physical structure.

Each profile combines its position-aware PatchCore score with a separate edge
geometry distance against the nearest normal historical image. The higher
threshold ratio controls AI status and both channels contribute to the
heatmap.

When a model is ready, Protect Ledger requires corroboration from both the
existing OpenCV comparison and this service before creating an alarm. If this
service is training, unavailable or unhealthy, monitoring automatically falls
back to the classical comparison so snapshot collection and notifications keep
working.

## Profiles

- `north-bollards`
- `front-bollards`
- `solstudio-bollards`
- `solstudio-stairs`

Models and metadata are stored below `/data/models`. Historical source images
are mounted read-only at `/snapshots`. Up to 240 samples distributed across the
archive are split into an 80 percent position-aware memory bank and a 20 percent
calibration set.
