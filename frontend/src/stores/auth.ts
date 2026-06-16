import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiClient } from "@/api/client";
import { ElMessage } from "element-plus";
import { t } from "@/i18n";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("token") || "");
  const username = ref(localStorage.getItem("username") || "");

  const isAuthenticated = computed(() => !!token.value);

  async function login(user: string, pass: string): Promise<boolean> {
    try {
      const res = await apiClient.post("/api/login", {
        username: user,
        password: pass,
      });
      token.value = res.data.token;
      username.value = user;
      localStorage.setItem("token", res.data.token);
      localStorage.setItem("username", user);
      return true;
    } catch (e: any) {
      if (e.response?.status === 429) {
        ElMessage.error(t("login.tooManyAttempts"));
      } else {
        ElMessage.error(t("login.invalidCredentials"));
      }
      return false;
    }
  }

  function logout() {
    token.value = "";
    username.value = "";
    localStorage.removeItem("token");
    localStorage.removeItem("username");
  }

  return { token, username, isAuthenticated, login, logout };
});
