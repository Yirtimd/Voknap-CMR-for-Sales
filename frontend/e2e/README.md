# Visual regression

Playwright stores deterministic light and dark baselines for Design System, Login, Home, Leads, Tasks and Analytics at 1440, 1024, 768 and 390 px: 48 screenshots total.

```sh
npm run test:visual
```

When an intentional UI change is reviewed, refresh baselines and immediately verify them:

```sh
npm run test:visual:update
npm run test:visual
```

Do not update baselines merely to silence a failure. Inspect the diff in `test-results` first. Generated reports and failure artifacts are ignored by Git; approved files in `e2e/visual.spec.ts-snapshots` are versioned.
