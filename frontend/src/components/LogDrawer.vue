<template>
  <el-drawer
    :model-value="visible"
    :title="`日志: ${stackName}`"
    direction="rtl"
    size="50%"
    @close="$emit('close')"
  >
    <div class="log-container">
      <div class="log-toolbar">
        <el-button size="small" @click="loadLogs" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-input-number
          v-model="tail"
          :min="50"
          :max="5000"
          :step="100"
          size="small"
          style="width: 120px"
        />
        <span class="log-hint">行</span>
      </div>
      <div class="log-content" ref="logContent">
        <div v-if="loading" class="log-loading">
          <el-icon class="is-loading"><Loading /></el-icon> 加载中...
        </div>
        <pre v-else-if="logs" class="log-text">{{ logs }}</pre>
        <el-empty v-else description="无日志" />
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Refresh, Loading } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";

const props = defineProps<{
  visible: boolean;
  hostId: string;
  stackName: string;
}>();

defineEmits<{ close: [] }>();

const loading = ref(false);
const logs = ref("");
const tail = ref(200);

async function loadLogs() {
  loading.value = true;
  try {
    const res = await apiClient.get(
      `/api/hosts/${props.hostId}/stacks/${props.stackName}/logs`,
      { params: { tail: tail.value } }
    );
    logs.value = res.data.logs || "";
  } catch (e: any) {
    logs.value = `Failed to fetch logs: ${e.response?.data?.detail || e.message}`;
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  (v) => {
    if (v) loadLogs();
  }
);
</script>

<style scoped>
.log-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.log-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.log-hint {
  font-size: 12px;
  color: var(--text-secondary);
}
.log-content {
  flex: 1;
  overflow: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
}
.log-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  padding: 16px;
}
.log-text {
  margin: 0;
  font-family: "Cascadia Code", "Fira Code", monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
