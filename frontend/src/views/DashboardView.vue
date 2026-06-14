<template>
  <div class="dashboard-layout">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="header-title">Docker Dashboard</h1>
        <el-tag type="success" size="small" v-if="store.onlineCount > 0">
          {{ store.onlineCount }}/{{ store.hosts.length }} 在线
        </el-tag>
      </div>
      <div class="header-right">
        <el-button text @click="refresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button text @click="logout">
          <el-icon><SwitchButton /></el-icon>
          退出
        </el-button>
      </div>
    </header>

    <!-- Summary bar -->
    <section class="summary-bar">
      <div class="summary-item">
        <span class="summary-value">{{ store.onlineCount }}</span>
        <span class="summary-label">在线主机</span>
      </div>
      <div class="summary-item">
        <span class="summary-value">{{ store.runningContainers }}</span>
        <span class="summary-label">运行容器</span>
      </div>
      <div class="summary-item">
        <span class="summary-value">{{ store.totalContainers }}</span>
        <span class="summary-label">容器总数</span>
      </div>
      <div class="summary-item">
        <span class="summary-value">{{ store.updateCount }}</span>
        <span class="summary-label">可更新镜像</span>
      </div>
    </section>

    <!-- Loading indicator -->
    <div v-if="store.loading" class="loading-bar">
      <el-progress :percentage="100" :stroke-width="2" :show-text="false" />
    </div>

    <!-- Error alert -->
    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      show-icon
      closable
      class="error-alert"
    />

    <!-- Host grid -->
    <main class="host-grid">
      <HostCard
        v-for="host in store.hosts"
        :key="host.host_id"
        :host="host"
        @click="goToHost(host.host_id)"
      />
    </main>

    <!-- Empty state -->
    <el-empty
      v-if="!store.loading && store.hosts.length === 0"
      description="暂无主机配置"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { Refresh, SwitchButton } from "@element-plus/icons-vue";
import { useDashboardStore } from "@/stores/dashboard";
import { useAuthStore } from "@/stores/auth";
import HostCard from "@/components/HostCard.vue";

const router = useRouter();
const store = useDashboardStore();
const auth = useAuthStore();

onMounted(() => {
  store.startPolling(10000);
});

onUnmounted(() => {
  store.stopPolling();
});

function refresh() {
  store.fetchHosts();
}

function logout() {
  auth.logout();
  router.push("/login");
}

function goToHost(hostId: string) {
  router.push(`/hosts/${hostId}`);
}
</script>

<style scoped>
.dashboard-layout {
  min-height: 100vh;
  background: var(--bg-dark);
}
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}
.header-right {
  display: flex;
  gap: 8px;
}
.summary-bar {
  display: flex;
  gap: 1px;
  background: var(--bg-card);
  margin: 16px 24px;
  border-radius: 8px;
  overflow: hidden;
}
.summary-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: var(--bg-card);
}
.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.summary-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.loading-bar {
  padding: 0 24px;
}
.error-alert {
  margin: 12px 24px 0;
}
.host-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  padding: 16px 24px 24px;
}
</style>
