<template>
  <div class="login-page">
    <div class="login-visual">
      <div class="visual-kicker">{{ t('login.kicker') }}</div>
      <h1>{{ t('login.title') }}</h1>
      <p>{{ t('login.subtitle') }}</p>
      <div class="visual-grid" aria-hidden="true">
        <span v-for="n in 18" :key="n" />
      </div>
    </div>
    <div class="login-card">
      <div class="login-brand-mark" aria-hidden="true">
        <AppLogo />
      </div>
      <h2 class="login-title">{{ t('login.title') }}</h2>
      <p class="login-subtitle">{{ t('login.subtitle') }}</p>
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
            :placeholder="t('login.username')"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="t('login.password')"
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            class="ui-button ui-button--primary ui-button--large"
            type="primary"
            :loading="loading"
            style="width: 100%"
            size="large"
            @click="handleLogin"
          >
          {{ t('login.submit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { User, Lock } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import AppLogo from "@/components/AppLogo.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { t } = useI18n();

const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: t('login.usernameRequired'), trigger: "blur" }],
  password: [{ required: true, message: t('login.passwordRequired'), trigger: "blur" }],
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  align-items: center;
  gap: 36px;
  min-height: 100vh;
  padding: 48px;
  background:
    radial-gradient(circle at 18% 12%, rgba(37, 99, 235, 0.24), transparent 32rem),
    radial-gradient(circle at 88% 86%, rgba(34, 211, 238, 0.12), transparent 28rem),
    var(--surface-base);
}
.login-visual {
  max-width: 720px;
}
.visual-kicker {
  color: var(--accent-blue);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.login-visual h1 {
  margin: 12px 0 0;
  font-size: clamp(44px, 7vw, 92px);
  line-height: 0.92;
  color: var(--text-primary);
}
.login-visual p {
  max-width: 520px;
  margin: 20px 0 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.8;
}
.visual-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  max-width: 460px;
  margin-top: 34px;
}
.visual-grid span {
  height: 46px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--login-grid-bg);
}
.visual-grid span:nth-child(4n + 1) {
  background: var(--login-grid-accent);
}
.visual-grid span:nth-child(5n) {
  background: var(--login-grid-success);
}
.login-card {
  width: 100%;
  padding: 40px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--login-card-bg);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.38);
}
.login-brand-mark {
  width: 48px;
  height: 48px;
  margin-bottom: 18px;
}
.login-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
}
.login-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 32px;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
    padding: 28px;
  }

  .login-visual {
    display: none;
  }
}
</style>
