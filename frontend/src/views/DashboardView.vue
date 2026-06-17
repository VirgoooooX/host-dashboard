<template>
  <div class="dashboard-layout">
    <section class="command-strip">
      <div class="command-copy">
        <ClusterHealthBg />
        <div class="command-copy-content">
          <div class="ui-section-kicker">{{ t('dashboard.kicker') }}</div>
          <h2>{{ t('dashboard.title') }}</h2>
          <p>{{ t('dashboard.description') }}</p>
        </div>
        <img src="/cloud_banner.png" alt="Cloud Banner" class="command-banner" />
      </div>
      <div class="summary-grid">
        <div class="summary-tile">
          <span class="summary-label">
            <el-icon><Monitor /></el-icon>
            {{ t('dashboard.onlineHosts') }}
          </span>
          <strong>{{ store.onlineCount }}</strong>
          <small>/ {{ store.hosts.length }}</small>
        </div>
        <div class="summary-tile">
          <span class="summary-label">
            <el-icon><CircleCheckFilled /></el-icon>
            {{ t('dashboard.runningContainers') }}
          </span>
          <strong>{{ store.runningContainers }}</strong>
          <small>{{ t('dashboard.running') }}</small>
        </div>
        <div class="summary-tile">
          <span class="summary-label">
            <el-icon><CircleCloseFilled /></el-icon>
            {{ t('dashboard.stoppedContainers') }}
          </span>
          <strong>{{ stoppedContainers }}</strong>
          <small>{{ t('dashboard.stopped') }}</small>
        </div>
        <button class="summary-tile critical" type="button" @click="router.push('/updates')">
          <span class="summary-label">
            <el-icon><Download /></el-icon>
            {{ t('dashboard.updatableImages') }}
          </span>
          <strong>{{ store.updateCount }}</strong>
          <small>{{ t('dashboard.updates') }}</small>
        </button>
      </div>
    </section>

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      show-icon
      closable
      class="error-alert"
    />

    <main class="host-grid" :aria-label="t('dashboard.title')">
      <HostCard
        v-for="host in sortedHosts"
        :key="host.host_id"
        :host="host"
        :update-count="store.getHostUpdateCount(host.host_id)"
        @click="goToHost(host.host_id)"
        @updates="goToHost(host.host_id)"
      />
    </main>

    <el-empty
      v-if="!store.loading && store.hosts.length === 0"
      :description="t('dashboard.noHosts')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useDashboardStore } from "@/stores/dashboard";
import HostCard from "@/components/HostCard.vue";
import ClusterHealthBg from "@/components/ClusterHealthBg.vue";
import { Monitor, CircleCheckFilled, CircleCloseFilled, Download } from "@element-plus/icons-vue";

const router = useRouter();
const store = useDashboardStore();
const { t } = useI18n();

const stoppedContainers = computed(() =>
  store.hosts.reduce((sum, host) => sum + host.container_stopped, 0)
);

const sortedHosts = computed(() => store.hosts);

function goToHost(hostId: string) {
  router.push(`/hosts/${hostId}`);
}
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.command-strip {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(520px, 1.4fr);
  align-items: stretch;
  gap: 16px;
}

.command-copy {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--dash-command-bg);
  padding: 18px;
}

.command-copy {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
  overflow: hidden;
  isolation: isolate;
  transform: translateZ(0);
  background: var(--dash-command-bg);
}

.command-copy-content {
  position: relative;
  z-index: 1;
}

.command-banner {
  position: absolute;
  right: -10px;
  bottom: -15px;
  height: 100%;
  width: auto;
  pointer-events: none;
  opacity: 0.95;
  z-index: 0;
  transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.command-copy:hover .command-banner {
  transform: scale(1.06) translate(-4px, -4px) rotate(-1deg);
}


.command-copy h2 {
  margin: 0;
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.15;
  color: var(--text-primary);
}

.command-copy p {
  max-width: 420px;
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 500px) {
  .command-banner {
    opacity: 0.5;
    height: 100%;
    right: -10px;
    bottom: -15px;
  }
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-tile {
  min-height: 150px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--dash-tile-bg);
  color: var(--text-primary);
  padding: 16px 14px;
  text-align: left;
}

button.summary-tile {
  cursor: pointer;
}

.summary-tile:hover {
  border-color: var(--border-strong);
  background: var(--dash-tile-hover-bg);
}

.summary-tile.critical {
  border-color: rgba(248, 113, 113, 0.28);
  background: var(--dash-tile-critical-bg);
}

.summary-tile strong {
  font-size: 31px;
  line-height: 1;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-label {
  color: var(--text-secondary);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.summary-label .el-icon {
  font-size: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
}

.summary-tile small {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
}

.summary-tile.critical strong,
.summary-tile.critical small {
  color: var(--danger);
}

.error-alert {
  margin: 0;
}

.host-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 14px;
}

@media (max-width: 1100px) {
  .command-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .host-grid {
    grid-template-columns: 1fr;
  }
}
</style>
