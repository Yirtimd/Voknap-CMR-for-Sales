import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import { crmStore } from "../../stores/crm";
import type { Lead } from "../../types";
import EntityCrudDrawer from "./EntityCrudDrawer.vue";

const lead: Lead = {
  id: "lead-1",
  company_id: "company-1",
  title: "Новый запрос",
  source: "site",
  status: "new",
  contact_id: null,
  owner_id: "user-1",
  is_archived: false,
  deleted_at: null,
  version: 3
};

beforeEach(() => {
  crmStore.me.value = {
    user_id: "user-1",
    email: "rep@example.test",
    full_name: "Менеджер",
    tenant_id: "tenant-1",
    role: "sales_rep",
    permissions: ["crm:read", "crm:write"]
  };
  crmStore.companies.value = [{
    id: "company-1",
    name: "Компания",
    website: null,
    industry: null,
    description: null,
    status: "active",
    company_type: null,
    client_since: null,
    created_at: "2026-01-01T00:00:00Z"
  }];
});

describe("EntityCrudDrawer", () => {
  it("shows record CRUD and lead lifecycle actions inside the familiar page drawer", async () => {
    const wrapper = mount(EntityCrudDrawer, {
      props: { entityType: "leads", record: lead },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } }
    });

    expect(wrapper.text()).toContain("Редактировать");
    expect(wrapper.text()).toContain("История");
    expect(wrapper.text()).toContain("В архив");
    expect(wrapper.text()).toContain("В корзину");
    expect(wrapper.text()).toContain("Квалифицировать");
    expect(wrapper.text()).toContain("Дисквалифицировать");
  });

  it("renders a create form with context defaults", async () => {
    const wrapper = mount(EntityCrudDrawer, {
      props: { entityType: "contacts", initialMode: "create", initialValues: { company_id: "company-1" } },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } }
    });
    await flushPromises();

    expect(wrapper.get("form").element.tagName).toBe("FORM");
    expect(wrapper.text()).toContain("Новый контакт");
    expect(wrapper.get('select').element.value).toBe("company-1");
    expect(wrapper.text()).toContain("Создать");
  });
});
