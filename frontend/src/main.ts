import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";
import "./design-system/theme";
import "./design-system/tokens.css";
import "./style.css";
import "./design-system/dark-theme.css";

createApp(App).use(router).mount("#app");
