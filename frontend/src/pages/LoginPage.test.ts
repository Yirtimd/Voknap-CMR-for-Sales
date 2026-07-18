import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import LoginPage from "./LoginPage.vue";

describe("LoginPage", () => {
  it("renders registration and login forms", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { template: "<div />" } }]
    });
    await router.push("/");
    await router.isReady();

    const wrapper = mount(LoginPage, {
      global: { plugins: [router] }
    });

    expect(wrapper.get("h1").text()).toBe("Вход в CRM");
    expect(wrapper.findAll("form")).toHaveLength(2);
    expect(wrapper.text()).toContain("Регистрация компании");
    expect(wrapper.text()).toContain("Войти");
    wrapper.unmount();
  });
});
