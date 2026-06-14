<template>
  <span class="status-icon" :class="`status-${status}`">
    <el-tooltip :content="statusLabel" placement="top">
      <span class="status-dot" />
    </el-tooltip>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ status: string }>();

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    online: "在线",
    offline: "离线",
    degraded: "指标异常",
    unknown: "状态未知",
  };
  return labels[props.status] || props.status;
});
</script>

<style scoped>
.status-icon {
  display: inline-flex;
  align-items: center;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.status-online .status-dot {
  background: var(--el-color-success);
  box-shadow: 0 0 6px var(--el-color-success);
}
.status-offline .status-dot {
  background: var(--el-color-danger);
}
.status-degraded .status-dot {
  background: var(--el-color-warning);
}
.status-unknown .status-dot {
  background: var(--el-color-info);
}
</style>
