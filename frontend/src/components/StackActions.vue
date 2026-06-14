<template>
  <div class="stack-actions">
    <el-button
      size="small"
      text
      :loading="loading === 'start'"
      :disabled="loading !== null"
      @click="confirmAndRun('start', '启动')"
    >
      <el-icon><VideoPlay /></el-icon>
    </el-button>
    <el-button
      size="small"
      text
      :loading="loading === 'stop'"
      :disabled="loading !== null"
      @click="confirmAndRun('stop', '停止')"
    >
      <el-icon><VideoPause /></el-icon>
    </el-button>
    <el-button
      size="small"
      text
      :loading="loading === 'restart'"
      :disabled="loading !== null"
      @click="confirmAndRun('restart', '重启')"
    >
      <el-icon><Refresh /></el-icon>
    </el-button>
    <el-button
      size="small"
      text
      :loading="loading === 'update'"
      :disabled="loading !== null"
      @click="confirmAndRun('update', '更新')"
    >
      <el-icon><Top /></el-icon>
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { VideoPlay, VideoPause, Refresh, Top } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";

const props = defineProps<{
  hostId: string;
  stackName: string;
}>();

const emit = defineEmits<{ refresh: [] }>();

const loading = ref<string | null>(null);

const actionLabels: Record<string, string> = {
  start: "启动",
  stop: "停止",
  restart: "重启",
  update: "更新",
};

const actionRisks: Record<string, string> = {
  start: "启动已停止的 Stack。",
  stop: "停止 Stack 中的所有容器。正在运行的服务将被中断。",
  restart: "重启 Stack 中的所有容器。短暂中断后自动恢复。",
  update: "拉取最新镜像并重新创建容器。镜像拉取可能耗时。",
};

async function confirmAndRun(action: string, label: string) {
  try {
    await ElMessageBox.confirm(
      `确定要${label} Stack「${props.stackName}」吗？\n\n${actionRisks[action] || ""}`,
      `${label} Stack`,
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
  } catch {
    return; // User cancelled
  }

  loading.value = action;
  try {
    await apiClient.post(
      `/api/hosts/${props.hostId}/stacks/${props.stackName}/${action}`
    );
    ElMessage.success(`${label}成功`);
    emit("refresh");
  } catch (e: any) {
    ElMessage.error(`${label}失败: ${e.response?.data?.detail || e.message}`);
  } finally {
    loading.value = null;
  }
}
</script>

<style scoped>
.stack-actions {
  display: flex;
  gap: 2px;
}
</style>
