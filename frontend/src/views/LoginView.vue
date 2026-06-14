<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">Docker Dashboard</h1>
      <p class="login-subtitle">多主机 Docker 管理控制台</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @keyup.enter="handleLogin"
        label-width="0"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            size="large"
            @click="handleLogin"
          >
          登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter, useRoute } from "vue-router";
import { User, Lock } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin() {
  if (loading.value) return;
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    const ok = await auth.login(form.username, form.password);
    if (ok) {
      const redirect = (route.query.redirect as string) || "/";
      router.push(redirect);
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-dark);
}
.login-card {
  width: 380px;
  padding: 40px;
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}
.login-title {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}
.login-subtitle {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 32px;
}
</style>
