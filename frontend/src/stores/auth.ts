import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiClient } from "@/api/client";
import { ElMessage } from "element-plus";

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
        ElMessage.error("登录尝试过于频繁，请稍后再试");
      } else {
        ElMessage.error("用户名或密码错误");
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
