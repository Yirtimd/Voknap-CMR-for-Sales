# Voknap UI foundation

Implementation source of truth for P0–P1 design-system rules.

## Tokens

Import order is fixed in `src/main.ts`:

```ts
import "./design-system/tokens.css";
import "./style.css";
```

New components use only canonical variables from `tokens.css`.

Legacy aliases (`--bg`, `--brand`, `--cm-*`, `--tasks-*`, `--t-*`, `--drawer-*`) temporarily point to canonical tokens. Do not add new aliases or literal colors. Remove aliases as old selectors migrate.

## Components

Import primitives from `src/components/ui`:

```ts
import {
  UiAlert,
  UiBadge,
  UiButton,
  UiCard,
  UiDrawer,
  UiEmptyState,
  UiIcon,
  UiInput,
  UiModal,
  UiSelect,
  UiTable,
  UiTabs
} from "../components/ui";
```

Rules:

- extend a primitive before creating a screen-local duplicate;
- keep business logic outside primitives;
- use semantic variants, never color names;
- forward accessible labels to icon-only controls;
- use `UiDrawer` for contextual entity work;
- use `UiModal` for confirmation and short focused flows;
- use `UiAlert` for persistent feedback and errors;
- use `UiEmptyState` for an empty collection with a next action.

## Icons

`UiIcon` is the only product icon renderer. Paths live in `components/ui/icons.ts`.

```vue
<UiIcon name="search" :size="18" />
```

Do not add Unicode symbols or emoji as product icons. Keyboard notation such as `⌘K` remains text because it represents a physical shortcut.

## Backend status mapping

Use `statusDictionary.ts` before displaying a backend status:

```ts
const status = statusMeta(record.status, "deal");
```

```vue
<UiBadge :tone="status.tone">{{ status.label }}</UiBadge>
```

Domains currently cover common values, companies, leads, deals, tasks, documents, connectors, communications, AI actions, templates, automations, approvals, outbox messages, invitations, risks, priorities, and roles.

Unknown values fail safely to a neutral humanized label. Add an explicit mapping when a new backend enum becomes part of the product contract.

## P0 guardrails

Before merge:

1. no literal colors inside `components/ui`;
2. no alternative font stack;
3. no Unicode product icons;
4. backend statuses pass through the dictionary;
5. typecheck, tests, and production build pass.

## P1 contracts

- Body text starts at `--font-size-body` (14 px). 10–11 px is reserved for compact metadata.
- Components use only the canonical radius scale from `tokens.css`.
- Metric terminology comes from `metricVocabulary.ts`.
- Mobile navigation is persistent; drawers and workspace modals become fullscreen at 640 px.
- Automation action configuration is edited through form controls, never raw JSON.
