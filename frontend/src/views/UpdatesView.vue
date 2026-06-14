<template>
  <div class="updates-layout">
    <header class="page-header">
      <el-button text @click="$router.push('/')">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2 class="page-title">镜像更新检测</h2>
      <el-button type="primary" :loading="checking" @click="runCheck">
        <el-icon><Refresh /></el-icon> 立即检查
      </el-button>
    </header>

    <div v-if="checking" class="loading-center">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>正在检查镜像更新...</p>
    </div>

    <div v-else>
      <el-table :data="results" stripe style="width: 100%" v-if="results.length > 0">
        <el-table-column label="主机" prop="host_id" width="120" />
        <el-table-column label="镜像" prop="image" min-width="300">
          <template #default="{ row }">
            <code class="image-ref">{{ row.image }}</code>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <UpdateBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="当前 Digest" prop="current_digest" min-width="200">
          <template #default="{ row }">
            <span class="digest-text">{{ row.current_digest ? row.current_digest.slice(0, 19) + '...' : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="仓库 Digest" prop="registry_digest" min-width="200">
          <template #default="{ row }">
            <span class="digest-text">{{ row.registry_digest ? row.registry_digest.slice(0, 19) + '...' : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="暂无更新检测结果" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ArrowLeft, Refresh, Loading } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";
import UpdateBadge from "@/components/UpdateBadge.vue";

interface UpdateResult {
  host_id: string;
  image: string;
  current_digest?: string;
  registry_digest?: string;
  status: string;
}

const results = ref<UpdateResult[]>([]);
const checking = ref(false);

async function fetchResults() {
  checking.value = true;
  try {
    const res = await apiClient.get("/api/update-checks");
    results.value = res.data || [];
  } catch (e) {
    console.error("Failed to fetch update checks:", e);
  } finally {
    checking.value = false;
  }
}

async function runCheck() {
  checking.value = true;
  try {
    const res = await apiClient.post("/api/update-checks/run");
    results.value = res.data.results || [];
  } catch (e) {
    console.error("Failed to run update check:", e);
  } finally {
    checking.value = false;
  }
}

onMounted(fetchResults);
</script>

<style scoped>
.updates-layout {
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
  flex: 1;
  color: var(--text-primary);
}
.loading-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px;
  gap: 16px;
  color: var(--text-secondary);
}
.image-ref {
  font-size: 13px;
  background: var(--bg-dark);
  padding: 2px 6px;
  border-radius: 4px;
}
.digest-text {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
