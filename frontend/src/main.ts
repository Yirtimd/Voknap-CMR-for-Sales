import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";
import "./design-system/tokens.css";
import "./style.css";

createApp(App).use(router).mount("#app");
