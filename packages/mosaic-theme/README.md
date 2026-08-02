# Lilletorget Mosaic theme

Felles Mosaic-designgrunnlag for mikroappene på port 8150 og oppover.

Pakken inneholder:

- Mosaic-farger, typografi og responsive bruddpunkter
- felles knappe-, skjema- og hjelpeklasser
- Inter som lokal variabel WOFF2-font, uten kall til Google Fonts
- lyst og mørkt tema fra samme kilde

## Bruk i en ny mikroapp

Legg inn pakken fra frontend-katalogen:

```json
"@lilletorget/mosaic-theme": "file:../../packages/mosaic-theme"
```

Lag en minimal `src/style.css` som starter Tailwind fra appens egen katalog og
deretter henter hele designgrunnlaget:

```css
@import 'tailwindcss';
@import '@lilletorget/mosaic-theme/style.css';

@plugin "@tailwindcss/forms" {
  strategy: base;
}
```

Importer den lokale fonten og bygginngangen i applikasjonens inngangspunkt:

```ts
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";
```

Docker-bygget må ha repository-roten som kontekst og kopiere
`packages/mosaic-theme` før `npm ci` kjøres. Hver app får fortsatt en egen,
minimert CSS-pakke som bare inneholder Tailwind-klassene appen bruker.
