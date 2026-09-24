# Frontend

Vue 3.5 single-page app in [`frontend/`](../../frontend), built with Vite 8 and served by nginx, which also
proxies `/api` to the API and serves `/tiles/`.

| Concern | Choice |
|---|---|
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`), design tokens as CSS variables in `src/styles/app.css` |
| Components | Reka UI primitives, wrapped shadcn-style in `src/components/ui` (source lives in the repo) |
| Server state | Pinia Colada (`useQuery`/`useMutation`: caching, dedupe, invalidation) |
| Client state | Pinia (`src/stores/auth.ts`) |
| Routing | Vue Router 5, lazy-loaded pages |
| Maps | MapLibre GL 6, Protomaps basemap from a PMTiles file, H3 (`h3-js`) for hexagon aggregation |
| Icons, type | Lucide, Geist and Geist Mono (self-hosted) |

## Pages

| Route | Page | For the visitor |
|---|---|---|
| `/` | Home | A 3D hexagon map of one city. Height and colour both show the chosen metric: gross yield, $/sq ft or price cuts. It comes with city medians and the listings with the best yields. No marketing copy |
| `/explore` | Explore | Filters (city, type, beds, price, yield, price cut) in a row above a map and list, kept in sync. Sort by yield or $/sq ft |
| `/listings/:id` | Listing | Fair value with its comps on a map, editable cash flow, price history and neighbourhood facts |
| `/analyze` | Analyze | The same analysis for a property found elsewhere. The address lookup pre-fills from the assessment roll when one is loaded |
| `/portfolio` | Portfolio | Saved listings with notes and the assumptions they were analysed with |
| `/data` | Data | Which sources are loaded, when, under which licence |
| `/admin` | Admin | Queue data loads and recomputes, and see worker and data status (admins only) |

Principles: show numbers people act on (price vs. comps, monthly cash flow, yield, what the neighbourhood is
like), say where each number comes from, and label demo data as demo data. Every assumption is an input,
not a hidden constant.

## Components

- `components/ui` — Button, Badge, Panel, Stat, Segmented (toggle group), SliderField, Field, InfoTip, Skeleton.
- `components/map` — `HexMap3D` (home), `ListingsMap` (explore), `CompsMap` (subject plus comps).
- `components/analysis` — `FairValue`, `CashFlowPanel`, `PriceHistory`, `NeighbourhoodFacts`.
- `lib/` — `api.ts` (fetch wrapper with cookie auth and refresh), `map.ts` (style, map factory, ramps),
  `hex.ts` (H3 aggregation), `metrics.ts`, `format.ts` (CAD, percentages), `theme.ts` (dark/light,
  reduced motion).

## Colour

Two files hold all colour:

- [`src/styles/app.css`](../../frontend/src/styles/app.css) — UI tokens (surface, ink, border, accent) for
  dark and light.
- [`src/theme/palette.ts`](../../frontend/src/theme/palette.ts) — map and data colours: basemap flavour
  overrides, the sequential ramp (magnitude), the diverging pair (below/above fair value), subject and comp
  markers.

The map follows a dark, low-contrast basemap, so the data layers carry the contrast. Current values:

| Role | Dark | Light |
|---|---|---|
| Sequential (low → high) | `#115e59 #0f766e #0d9488 #14b8a6 #2dd4bf #5eead4` | `#14b8a6 #0d9488 #0f766e #115e59` |
| Diverging below / above | `#0d9488` / `#e5484d` | `#0d9488` / `#d03b3b` |
| Subject / comp markers | `#3987e5` / `#199e70` | `#2a78d6` / `#1baf7a` |

These were checked for step visibility, colour-vision-deficiency separation and contrast against the map
surface. When you change them, re-check with any palette validator (for example, a CVD simulator plus a WCAG
contrast check against the basemap `earth` colour). Colour is never the only channel: the hex map encodes
the metric in height too, and verdicts carry text labels.

## Maps

- MapLibre 6 is ESM-only and imported by name. Its worker is loaded through Vite
  (`maplibre-gl-worker.mjs?worker&url` + `setWorkerUrl`, `worker.format: 'es'`).
- A map container must have a definite height. MapLibre forces `position: relative` on it, so pages put the
  map inside an absolutely positioned parent at full width and height.
- With `VITE_PMTILES_URL` unset, maps render data on a plain background. See
  [Operations → Basemap](../operations.md#basemap) for self-hosting the tiles.
- The home map orbits slowly until the user interacts, and stays still when `prefers-reduced-motion` is set.
- Market points come from `/api/v1/markets/{city}/points` as compact arrays and are aggregated into H3 cells
  in the browser.

## Commands

```bash
npm run dev          # Vite dev server on :5173, proxies /api to :8000 (VITE_API_PROXY to change)
npm run typecheck    # vue-tsc
npm run build        # typecheck + production build to dist/
```
