<template>
  <div class="audit-layout">
    <header class="page-header">
      <el-button text @click="$router.push('/')">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2 class="page-title">操作审计</h2>
    </header>

    <el-table :data="logs" stripe style="width: 100%" v-if="logs.length > 0" :default-sort="{ prop: 'timestamp', order: 'descending' }">
      <el-table-column label="时间" prop="timestamp" width="170" sortable>
        <template #default="{ row }">
          {{ formatTime(row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column label="用户" prop="user" width="100" />
      <el-table-column label="操作" prop="action" width="140">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="主机" prop="host_id" width="120" />
      <el-table-column label="Stack" prop="stack_name" width="140">
        <template #default="{ row }">
          {{ row.stack_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="结果" prop="result" width="80">
        <template #default="{ row }">
          <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
            {{ row.result === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="IP" prop="ip_address" width="140" />
      <el-table-column label="详情" prop="detail" min-width="200">
        <template #default="{ row }">
          <span class="detail-text">{{ row.detail || '-' }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else description="暂无操作记录" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ArrowLeft } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";
import dayjs from "dayjs";

interface AuditEntry {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  host_id: string;
  stack_name?: string;
  result: string;
  detail?: string;
  ip_address?: string;
}

const logs = ref<AuditEntry[]>([]);
let limit = 50;

const actionLabels: Record<string, string> = {
  "stack.start": "启动 Stack",
  "stack.stop": "停止 Stack",
  "stack.restart": "重启 Stack",
  "stack.update": "更新 Stack",
  "update_checks.run": "检查更新",
};

const actionTypes: Record<string, string> = {
  "stack.start": "success",
  "stack.stop": "warning",
  "stack.restart": "",
  "stack.update": "primary",
  "update_checks.run": "info",
};

function actionLabel(action: string): string {
  return actionLabels[action] || action;
}

function actionType(action: string): string {
  return actionTypes[action] || "info";
}

function formatTime(ts: string): string {
  return dayjs(ts).format("YYYY-MM-DD HH:mm:ss");
}

async function fetchLogs() {
  try {
    const res = await apiClient.get("/api/audit-logs", {
      params: { limit, offset: 0 },
    });
    logs.value = res.data || [];
  } catch (e) {
    console.error("Failed to fetch audit logs:", e);
  }
}

onMounted(fetchLogs);
</script>

<style scoped>
.audit-layout {
  min-height: 100vh;
  background: var(--bg-dark);
  padding: 16px 24px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}
.detail-text {
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
}
</style>
