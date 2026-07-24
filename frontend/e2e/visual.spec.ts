import { expect, test, type Page } from "@playwright/test";

const routes = [
  { path: "/home", name: "home" },
  { path: "/leads", name: "leads" },
  { path: "/tasks", name: "tasks" },
  { path: "/analytics", name: "analytics" }
];

async function stabilize(page: Page) {
  await page.addStyleTag({
    content: "*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}"
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
}

async function mockApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("cmr_token", "visual-token");
    localStorage.setItem("cmr_tenant_id", "00000000-0000-0000-0000-000000000001");
    localStorage.setItem("cmr_sidebar_mode", "full");
    localStorage.setItem("cmr_ui_density", "comfortable");
  });
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/me")) {
      await route.fulfill({
        json: {
          id: "visual-user",
          email: "visual@voknap.test",
          full_name: "Дмитрий Тестов",
          role: "owner",
          permissions: ["crm:read", "crm:write", "automations:manage", "approvals:manage"]
        }
      });
      return;
    }
    if (pathname.includes("/analytics/overview")) {
      await route.fulfill({
        json: {
          generated_at: "2026-07-24T09:30:00+03:00",
          forecast: {
            currency: "RUB",
            period_days: 90,
            open_pipeline: 0,
            due_in_period: 0,
            weighted_revenue: 0,
            commit_revenue: 0,
            best_case_revenue: 0,
            pipeline_revenue: 0,
            overdue_revenue: 0,
            won_revenue: 0,
            open_deals: 0
          },
          stage_conversion: [],
          stuck_deals: [],
          task_sla: {
            total: 0,
            open: 0,
            completed: 0,
            overdue: 0,
            completed_on_time: 0,
            completion_rate: 0,
            sla_rate: 0,
            average_resolution_hours: null,
            by_owner: []
          },
          manager_activity: [],
          company_health: [],
          risk_map: { high: 0, medium: 0, low: 0, revenue_at_risk: 0, deals: [] }
        }
      });
      return;
    }
    if (pathname.includes("/ai-agent/home/copilot")) {
      await route.fulfill({ json: null });
      return;
    }
    await route.fulfill({ json: [] });
  });
}

test("component library", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-07-24T09:30:00+03:00"));
  await mockApi(page);
  await page.goto("/settings");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Компоненты", exact: true }).click();
  await stabilize(page);
  await expect(page.getByTestId("design-system-page")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expect(page).toHaveScreenshot("design-system.png", { fullPage: true });
});

test("login", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-07-24T09:30:00+03:00"));
  await page.addInitScript(() => localStorage.clear());
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await stabilize(page);
  await expect(page.getByRole("heading", { name: "Продажи, которые двигаются сами" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expect(page).toHaveScreenshot("login.png", { fullPage: true });
});

for (const screen of routes) {
  test(`${screen.name} screen`, async ({ page }) => {
    await page.clock.setFixedTime(new Date("2026-07-24T09:30:00+03:00"));
    await mockApi(page);
    await page.goto(screen.path);
    await page.waitForLoadState("networkidle");
    await stabilize(page);
    await expect(page.locator(".app-shell")).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot(`${screen.name}.png`, { fullPage: true });
  });
}
