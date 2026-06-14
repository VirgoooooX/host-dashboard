<template>
  <el-card class="host-card" shadow="hover" @click="$emit('click')">
    <div class="card-header">
      <div class="card-header-left">
        <StatusIcon :status="host.status" />
        <span class="host-name">{{ host.display_name }}</span>
      </div>
      <el-tag v-if="host.update_count > 0" type="danger" size="small">
        {{ host.update_count }} 更新
      </el-tag>
    </div>

    <!-- Metrics -->
    <div class="card-metrics" v-if="host.metrics">
      <div class="metric">
        <span class="metric-label">CPU</span>
        <el-progress
          :percentage="Math.round(host.metrics.cpuPercent)"
          :stroke-width="6"
          :show-text="false"
          :color="cpuColor"
        />
        <span class="metric-value">{{ host.metrics.cpuPercent.toFixed(1) }}%</span>
      </div>
      <div class="metric">
        <span class="metric-label">内存</span>
        <el-progress
          :percentage="memPercent"
          :stroke-width="6"
          :show-text="false"
          :color="memColor"
        />
        <span class="metric-value">{{ formatBytes(host.metrics.memoryUsed) }}/{{ formatBytes(host.metrics.memoryTotal) }}</span>
      </div>
      <div class="metric">
        <span class="metric-label">磁盘</span>
        <el-progress
          :percentage="diskPercent"
          :stroke-width="6"
          :show-text="false"
          :color="diskColor"
        />
        <span class="metric-value">{{ formatBytes(host.metrics.diskUsed) }}/{{ formatBytes(host.metrics.diskTotal) }}</span>
      </div>
    </div>

    <!-- Docker summary -->
    <div class="card-footer">
      <div class="docker-stat">
        <span class="stat-icon running-dot" /> {{ host.container_running }} 运行
      </div>
      <div class="docker-stat">
        <span class="stat-icon stopped-dot" /> {{ host.container_stopped }} 停止
      </div>
      <div class="docker-stat">
        <el-icon :size="14"><Monitor /></el-icon> {{ host.image_count }} 镜像
      </div>
      <div class="docker-stat" v-if="host.docker_version">
        <el-icon :size="14"><Coin /></el-icon> v{{ host.docker_version }}
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Monitor, Coin } from "@element-plus/icons-vue";
import StatusIcon from "./StatusIcon.vue";
import type { HostSummary } from "@/stores/dashboard";

const props = defineProps<{ host: HostSummary }>();
defineEmits<{ click: [] }>();

const memPercent = computed(() => {
  const m = props.host.metrics;
  if (!m) return 0;
  return m.memoryTotal > 0 ? Math.round((m.memoryUsed / m.memoryTotal) * 100) : 0;
});

const diskPercent = computed(() => {
  const m = props.host.metrics;
  if (!m) return 0;
  return m.diskTotal > 0 ? Math.round((m.diskUsed / m.diskTotal) * 100) : 0;
});

function cpuColor(pct: number) {
  if (pct > 80) return "#f56c6c";
  if (pct > 50) return "#e6a23c";
  return "#67c23a";
}

function memColor(pct: number) {
  if (pct > 80) return "#f56c6c";
  if (pct > 60) return "#e6a23c";
  return "#67c23a";
}

function diskColor(pct: number) {
  if (pct > 85) return "#f56c6c";
  if (pct > 70) return "#e6a23c";
  return "#67c23a";
}

function formatBytes(bytes: number | undefined): string {
  if (!bytes) return "0";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(1)}${units[i]}`;
}
</script>

<style scoped>
.host-card {
  cursor: pointer;
  transition: transform 0.1s;
}
.host-card:hover {
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.host-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
.card-metrics {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.metric {
  display: flex;
  align-items: center;
  gap: 8px;
}
.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  width: 32px;
  flex-shrink: 0;
}
.metric-value {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  width: 120px;
  text-align: right;
}
.card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}
.docker-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}
.running-dot, .stopped-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.running-dot {
  background: var(--el-color-success);
}
.stopped-dot {
  background: var(--el-color-danger);
}
</style>
