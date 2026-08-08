# AppKit Mobile theme foundation

This directory contains the shared mobile theme used by the Lilletorget mobile
applications.

Source package:

- `themeforest-F2VmYRaW-appkit-mobile.zip`
- Purchased by the repository owner and imported on 2026-08-08.
- Original vendor CSS is kept in `vendor/` so later upgrades can be compared
  against the purchased package.

`lilletorget-appkit.css` and `lilletorget-appkit.js` are the local integration
layer. Application-specific CSS should contain layout and domain components,
while typography, colors, safe-area handling, headers, navigation, cards,
buttons, forms and theme switching belong here.

The package is mounted at `/appkit-assets` by each mobile FastAPI application.

Current consumers:

- `online_dashboard`
- `maintenance_mobile`
- `alarm_mobile`

The integration preserves each application's API and workflow. AppKit owns the
shared visual foundation, while domain colors and task-specific components stay
inside each application. The theme follows the device preference by default and
stores an explicit light/dark choice in `localStorage`.

Local visual QA with safe preview data:

```powershell
python scripts/mobile_appkit_preview.py maintenance --port 18112
python scripts/mobile_appkit_preview.py alarm --port 18114
```
