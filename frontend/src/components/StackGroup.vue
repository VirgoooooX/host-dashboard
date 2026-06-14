<template>
  <div class="stack-list">
    <el-card
      v-for="stack in stacks"
      :key="stack.name"
      class="stack-card"
      shadow="never"
    >
      <div class="stack-header">
        <div class="stack-header-left">
          <el-icon :size="18">
            <FolderOpened />
          </el-icon>
          <span class="stack-name">{{ stack.name }}</span>
          <StatusIcon :status="stackStatusType(stack.status)" />
          <el-tag :type="stackTagType(stack.status)" size="small">
            {{ stack.status }}
          </el-tag>
        </div>
        <div class="stack-header-right">
          <span class="stack-service-count">
            {{ stack.running_count }} / {{ stack.service_count }} 运行
          </span>
          <StackActions
            :host-id="hostId"
            :stack-name="stack.name"
            @refresh="$emit('refresh')"
          />
          <el-button size="small" text @click="openLogs(stack.name)">
            <el-icon><Document /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Services -->
      <div v-if="stack.services && stack.services.length > 0" class="stack-services">
        <div
          v-for="svc in stack.services"
          :key="svc.name"
          class="service-row"
        >
          <StatusIcon :status="svc.state === 'running' ? 'online' : 'offline'" />
          <span class="service-name">{{ svc.name }}</span>
          <span class="service-status">{{ svc.status }}</span>
        </div>
      </div>
    </el-card>
  </div>

  <!-- Log drawer -->
  <LogDrawer
    v-if="logDrawerVisible"
    :visible="logDrawerVisible"
    :host-id="hostId"
    :stack-name="currentLogStack"
    @close="logDrawerVisible = false"
  />
</template>

<script setup lang="ts">
import { ref } from "vue";
import { FolderOpened, Document } from "@element-plus/icons-vue";
import StatusIcon from "./StatusIcon.vue";
import StackActions from "./StackActions.vue";
import LogDrawer from "./LogDrawer.vue";

export interface StackService {
  name: string;
  container_id?: string;
  state: string;
  status: string;
}

export interface StackSummary {
  name: string;
  status: string;
  compose_file?: string;
  service_count: number;
  running_count: number;
  services: StackService[];
}

const props = defineProps<{
  stacks: StackSummary[];
  hostId: string;
}>();

defineEmits<{ refresh: [] }>();

const logDrawerVisible = ref(false);
const currentLogStack = ref("");

function stackStatusType(status: string): string {
  if (status === "running") return "online";
  if (status === "stopped") return "offline";
  return "degraded";
}

function stackTagType(status: string): "success" | "warning" | "info" | "danger" {
  if (status === "running") return "success";
  if (status === "stopped") return "danger";
  if (status === "partially running") return "warning";
  return "info";
}

function openLogs(stackName: string) {
  currentLogStack.value = stackName;
  logDrawerVisible.value = true;
}
</script>

<style scoped>
.stack-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stack-card {
  border: 1px solid var(--border-color);
}
.stack-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.stack-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stack-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stack-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.stack-service-count {
  font-size: 12px;
  color: var(--text-secondary);
}
.stack-services {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.service-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
  font-size: 13px;
}
.service-name {
  color: var(--text-primary);
  font-weight: 500;
}
.service-status {
  color: var(--text-secondary);
  font-size: 12px;
}
</style>
