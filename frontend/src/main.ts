import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import en from "element-plus/es/locale/lang/en";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";

import App from "./App.vue";
import router from "./router";
import { i18n, getStoredLocale } from "./i18n";
import type { Locale } from "./i18n";
import "./styles/dashboard.css";
import "./styles/themes.css";
import "./styles/ui.css";
import "./styles/confirm-dialog.css";

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(i18n);

// Element Plus locale — initial value synced with i18n locale
const elLocales: Record<Locale, typeof zhCn> = {
  "zh-CN": zhCn,
  "en-US": en,
};

app.use(ElementPlus, { locale: elLocales[getStoredLocale()] });

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.mount("#app");
