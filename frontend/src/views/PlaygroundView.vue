<template>
  <div class="playground-root">
    <!-- 方案切换控制栏 (Playground 专属) -->
    <div class="playground-control-strip">
      <div class="control-left">
        <div class="ui-section-kicker">UI DESIGN PLAYGROUND</div>
        <h2 class="ui-page-title">符合项目原生风格的设置页方案</h2>
      </div>
      <div class="control-right">
        <el-radio-group v-model="activeLayout" size="small">
          <el-radio-button value="style-a">方案一：标准卡片式标签页 (ElTabs)</el-radio-button>
          <el-radio-button value="style-b">方案二：垂直卡片平铺流 (Vertical Panels)</el-radio-button>
          <el-radio-button value="style-c">方案三：左右并排对称栅格 (Split Grid)</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- ── 方案一：标准卡片标签页 (Style A) ── -->
    <div v-if="activeLayout === 'style-a'" class="style-container">
      <header class="ui-page-header">
        <div>
          <div class="ui-section-kicker">SYSTEM CONFIGURATION</div>
          <h2 class="ui-page-title">系统设置</h2>
        </div>
        <el-button class="ui-button ui-button--muted" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
      </header>

      <!-- 原生项目风格的 Tab 容器 -->
      <div class="tabs-container">
        <el-tabs type="card" class="custom-el-tabs">
          <!-- Tab 1: 运行参数 -->
          <el-tab-pane label="运行参数">
            <div class="ui-panel panel-padding">
              <div class="panel-header">
                <h3>监控数据轮询间隔</h3>
                <span class="panel-desc">管理各个后台监控任务的抓取周期，保存后热重载立即生效。</span>
              </div>
              <el-form label-position="top">
                <div class="form-row-2">
                  <el-form-item label="主循环轮询间隔 (DOCKER_POLL_INTERVAL)">
                    <el-input-number v-model="settings.docker_poll_interval" :min="1" :max="120" style="width: 100%" />
                    <span class="input-tip">单位：秒。定时同步堆栈列表与容器基础状态。</span>
                  </el-form-item>
                  <el-form-item label="实时指标流周期 (METRICS_STREAM_INTERVAL)">
                    <el-input-number v-model="settings.metrics_stream_interval" :min="1" :max="60" style="width: 100%" />
                    <span class="input-tip">单位：秒。在堆栈详情页流式推送指标的周期。</span>
                  </el-form-item>
                </div>
                <div class="form-row-2 mt-16">
                  <el-form-item label="自动检查更新周期 (UPDATE_CHECK_INTERVAL)">
                    <el-input-number v-model="settings.update_check_interval" :min="30" style="width: 100%" />
                    <span class="input-tip">单位：秒。后台检测容器镜像是否有新版本的频率。</span>
                  </el-form-item>
                  <el-form-item label="状态健康自检周期 (SYSTEM_CHECK_INTERVAL)">
                    <el-input-number v-model="settings.system_check_interval" :min="5" style="width: 100%" />
                    <span class="input-tip">单位：秒。自检 Agent 通信连通性的频率。</span>
                  </el-form-item>
                </div>
                <div class="form-actions">
                  <el-button class="ui-button ui-button--primary" type="primary" @click="saveSettings">
                    <el-icon><Check /></el-icon> 保存配置
                  </el-button>
                </div>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- Tab 2: 安全与密码 -->
          <el-tab-pane label="安全与密码">
            <div class="ui-panel panel-padding">
              <div class="panel-header">
                <h3>系统凭证与安全策略</h3>
                <span class="panel-desc">可写参数保存后生效。敏感密钥受环境安全策略保护，只读显示。</span>
              </div>
              <el-form label-position="top">
                <div class="form-row-2">
                  <el-form-item label="管理员账号 (ADMIN_USERNAME)">
                    <el-input v-model="settings.admin_username" />
                  </el-form-item>
                  <el-form-item label="JWT 会话有效期 (JWT_EXPIRE_HOURS)">
                    <el-input-number v-model="settings.jwt_expire_hours" :min="1" style="width: 100%" />
                  </el-form-item>
                </div>
                
                <div class="divider-line"></div>
                
                <div class="form-row-2 mt-16">
                  <el-form-item label="JWT 签名密钥 (JWT_SECRET)">
                    <el-input v-model="settings.jwt_secret" disabled type="password" show-password />
                    <span class="input-tip text-danger">只读字段，需修改环境变量并重启容器。</span>
                  </el-form-item>
                  <el-form-item label="凭证加密密钥 (CREDENTIALS_KEY)">
                    <el-input v-model="settings.credentials_key" disabled type="password" show-password />
                    <span class="input-tip text-danger">只读字段，需修改环境变量并重启容器。</span>
                  </el-form-item>
                </div>
                <div class="form-actions">
                  <el-button class="ui-button ui-button--primary" type="primary" @click="saveSettings">
                    <el-icon><Check /></el-icon> 保存安全设置
                  </el-button>
                </div>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- Tab 3: Host 节点管理 -->
          <el-tab-pane label="Host 节点管理">
            <div class="ui-panel panel-padding">
              <div class="panel-header flex-header">
                <div>
                  <h3>物理主机节点配置</h3>
                  <span class="panel-desc">编辑节点将自动实时重写至后台的 hosts.yaml 配置文件中。</span>
                </div>
                <el-button class="ui-button ui-button--primary" type="primary" :icon="Plus" @click="openAddHost">
                  新增 Host 节点
                </el-button>
              </div>

              <!-- 原生 table 风格 -->
              <el-table :data="hosts" stripe style="width: 100%" class="native-table-style">
                <el-table-column label="节点 ID (host_id)" prop="host_id" width="150" />
                <el-table-column label="显示名称" prop="display_name" width="160" />
                <el-table-column label="Agent 连接地址" prop="agent_url" min-width="200" />
                <el-table-column label="启用状态" width="100">
                  <template #default="{ row }">
                    <el-switch v-model="row.enabled" />
                  </template>
                </el-table-column>
                <el-table-column label="连接测试" width="130">
                  <template #default="{ row }">
                    <el-button 
                      size="small" 
                      :type="row.testStatus === 'success' ? 'success' : row.testStatus === 'error' ? 'danger' : 'info'"
                      :loading="row.testing"
                      plain
                      class="mini-btn-adjust"
                      @click="testConnection(row)"
                    >
                      {{ row.testStatus === 'success' ? '在线' : row.testStatus === 'error' ? '离线' : '测试连接' }}
                    </el-button>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="160" align="right">
                  <template #default="{ row }">
                    <div class="row-buttons">
                      <el-button size="small" link :icon="Edit" @click="openEditHost(row)">编辑</el-button>
                      <el-button size="small" link type="danger" :icon="Delete" @click="deleteHost(row)">删除</el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- ── 方案二：垂直卡片平铺流 (Style B) ── -->
    <div v-if="activeLayout === 'style-b'" class="style-container">
      <header class="ui-page-header">
        <div>
          <div class="ui-section-kicker">SYSTEM CONFIGURATION</div>
          <h2 class="ui-page-title">系统设置</h2>
        </div>
        <el-button class="ui-button ui-button--muted" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
      </header>

      <!-- 垂直分布的卡片流 -->
      <div class="vertical-stack-flow">
        <!-- 运行参数面板 -->
        <div class="ui-panel panel-padding">
          <div class="panel-header-title">
            <el-icon class="panel-icon"><Tools /></el-icon>
            <h3>监控数据轮询间隔</h3>
          </div>
          <el-form label-position="top">
            <div class="form-row-4">
              <el-form-item label="主循环轮询 (s)">
                <el-input-number v-model="settings.docker_poll_interval" :min="1" style="width: 100%" />
              </el-form-item>
              <el-form-item label="实时指标流 (s)">
                <el-input-number v-model="settings.metrics_stream_interval" :min="1" style="width: 100%" />
              </el-form-item>
              <el-form-item label="镜像检测周期 (s)">
                <el-input-number v-model="settings.update_check_interval" style="width: 100%" />
              </el-form-item>
              <el-form-item label="健康自检周期 (s)">
                <el-input-number v-model="settings.system_check_interval" style="width: 100%" />
              </el-form-item>
            </div>
            <div class="form-actions text-right">
              <el-button class="ui-button ui-button--primary" type="primary" @click="saveSettings">保存轮询间隔</el-button>
            </div>
          </el-form>
        </div>

        <!-- 安全凭证面板 -->
        <div class="ui-panel panel-padding mt-16">
          <div class="panel-header-title">
            <el-icon class="panel-icon"><Lock /></el-icon>
            <h3>安全与账号策略</h3>
          </div>
          <el-form label-position="top">
            <div class="form-row-2">
              <el-form-item label="管理员用户名 (ADMIN_USERNAME)">
                <el-input v-model="settings.admin_username" />
              </el-form-item>
              <el-form-item label="JWT 会话过期时间 (JWT_EXPIRE_HOURS)">
                <el-input-number v-model="settings.jwt_expire_hours" style="width: 100%" />
              </el-form-item>
            </div>
            <div class="form-actions text-right">
              <el-button class="ui-button ui-button--primary" type="primary" @click="saveSettings">保存安全策略</el-button>
            </div>
          </el-form>
        </div>

        <!-- Host 节点列表面板 -->
        <div class="ui-panel panel-padding mt-16">
          <div class="panel-header flex-header no-border">
            <div class="panel-header-title no-margin">
              <el-icon class="panel-icon"><Cpu /></el-icon>
              <h3>物理主机节点管理</h3>
            </div>
            <el-button class="ui-button ui-button--primary" type="primary" :icon="Plus" @click="openAddHost">
              新增 Host 节点
            </el-button>
          </div>

          <el-table :data="hosts" stripe style="width: 100%" class="native-table-style">
            <el-table-column label="节点 ID" prop="host_id" width="130" />
            <el-table-column label="名称" prop="display_name" width="150" />
            <el-table-column label="Agent 物理地址" prop="agent_url" min-width="220" />
            <el-table-column label="启用" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" />
              </template>
            </el-table-column>
            <el-table-column label="状态校验" width="120">
              <template #default="{ row }">
                <el-button 
                  size="small" 
                  :type="row.testStatus === 'success' ? 'success' : row.testStatus === 'error' ? 'danger' : 'info'"
                  :loading="row.testing"
                  plain
                  class="mini-btn-adjust"
                  @click="testConnection(row)"
                >
                  {{ row.testStatus === 'success' ? '连通正常' : row.testStatus === 'error' ? '连接失败' : '测试' }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column label="管理" width="140" align="right">
              <template #default="{ row }">
                <div class="row-buttons">
                  <el-button size="small" link :icon="Edit" @click="openEditHost(row)"></el-button>
                  <el-button size="small" link type="danger" :icon="Delete" @click="deleteHost(row)"></el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- ── 方案三：左右并排对称栅格 (Style C) ── -->
    <div v-if="activeLayout === 'style-c'" class="style-container">
      <header class="ui-page-header">
        <div>
          <div class="ui-section-kicker">SYSTEM CONFIGURATION</div>
          <h2 class="ui-page-title">系统设置</h2>
        </div>
        <el-button class="ui-button ui-button--muted" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
      </header>

      <div class="split-grid-layout">
        <!-- 左侧：参数与安全配置 (垂直排布) -->
        <div class="grid-left-col">
          <div class="ui-panel panel-padding">
            <div class="panel-header">
              <h3>运行参数</h3>
            </div>
            <el-form label-position="top">
              <el-form-item label="Docker 轮询监控频率 (秒)">
                <el-input-number v-model="settings.docker_poll_interval" style="width: 100%" />
              </el-form-item>
              <el-form-item label="指标数据流频率 (秒)">
                <el-input-number v-model="settings.metrics_stream_interval" style="width: 100%" />
              </el-form-item>
              <el-button class="ui-button ui-button--primary" style="width: 100%" @click="saveSettings">
                保存参数
              </el-button>
            </el-form>
          </div>

          <div class="ui-panel panel-padding mt-16">
            <div class="panel-header">
              <h3>安全配置</h3>
            </div>
            <el-form label-position="top">
              <el-form-item label="管理员账号">
                <el-input v-model="settings.admin_username" />
              </el-form-item>
              <el-form-item label="JWT 过期时间 (小时)">
                <el-input-number v-model="settings.jwt_expire_hours" style="width: 100%" />
              </el-form-item>
              <el-button class="ui-button ui-button--primary" style="width: 100%" @click="saveSettings">
                保存安全设置
              </el-button>
            </el-form>
          </div>
        </div>

        <!-- 右侧：完整的 Host 管理列表 -->
        <div class="grid-right-col">
          <div class="ui-panel panel-padding h-100">
            <div class="panel-header flex-header">
              <div>
                <h3>Host 节点配置</h3>
                <span class="panel-desc">管理集群物理节点连通性及状态</span>
              </div>
              <el-button class="ui-button ui-button--primary" type="primary" :icon="Plus" @click="openAddHost">
                新增节点
              </el-button>
            </div>

            <el-table :data="hosts" stripe style="width: 100%" class="native-table-style">
              <el-table-column label="节点 ID" prop="host_id" width="110" />
              <el-table-column label="显示名称" prop="display_name" min-width="120" />
              <el-table-column label="启用" width="80">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="测试连接" width="100">
                <template #default="{ row }">
                  <el-button 
                    size="small" 
                    :type="row.testStatus === 'success' ? 'success' : row.testStatus === 'error' ? 'danger' : 'info'"
                    :loading="row.testing"
                    plain
                    class="mini-btn-adjust"
                    @click="testConnection(row)"
                  >
                    {{ row.testStatus === 'success' ? '通' : row.testStatus === 'error' ? '断' : '测' }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="right">
                <template #default="{ row }">
                  <div class="row-buttons">
                    <el-button size="small" link :icon="Edit" @click="openEditHost(row)"></el-button>
                    <el-button size="small" link type="danger" :icon="Delete" @click="deleteHost(row)"></el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Host 节点编辑/新增弹窗 (项目统一规范对话框) ── -->
    <el-dialog
      v-model="hostDialogVisible"
      :title="hostForm.isEdit ? '编辑主机节点' : '新建主机节点'"
      width="460px"
      custom-class="native-themed-dialog"
    >
      <el-form label-position="top" :model="hostForm" class="dialog-form">
        <el-form-item label="节点唯一标识 (host_id)" required>
          <el-input v-model="hostForm.host_id" placeholder="如: node-production-1" :disabled="hostForm.isEdit" />
        </el-form-item>
        
        <el-form-item label="显示名称 (display_name)" required>
          <el-input v-model="hostForm.display_name" placeholder="如: 华北节点" />
        </el-form-item>

        <el-form-item label="Agent API 地址" required>
          <el-input v-model="hostForm.agent_url" placeholder="如: http://192.168.1.100:8000" />
        </el-form-item>

        <el-form-item label="访问密钥 Token (为空保持原密钥)">
          <el-input v-model="hostForm.agent_token" type="password" show-password placeholder="安全凭证密钥密码" />
        </el-form-item>

        <el-form-item label="是否启用此节点">
          <el-switch v-model="hostForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="ui-button ui-button--muted" @click="hostDialogVisible = false">取消</el-button>
          <el-button class="ui-button ui-button--primary" type="primary" @click="submitHostForm">确定保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import { 
  ArrowLeft,
  Check,
  Plus,
  Edit,
  Delete,
  Tools,
  Lock,
  Cpu
} from "@element-plus/icons-vue";

const router = useRouter();

// 激活哪套风格预览
const activeLayout = ref("style-a");

// 数据模拟
const settings = reactive({
  docker_poll_interval: 10,
  metrics_stream_interval: 2,
  update_check_interval: 3600,
  system_check_interval: 30,
  admin_username: "admin",
  jwt_expire_hours: 168,
  jwt_secret: "jwt-secret-string-environment-configured",
  credentials_key: "sqlite-encryption-key-for-credentials"
});

const hosts = ref([
  {
    host_id: "main-node",
    display_name: "本地开发节点",
    agent_url: "http://127.0.0.1:8000",
    enabled: true,
    testing: false,
    testStatus: "success"
  },
  {
    host_id: "hk-server",
    display_name: "云服务器 (HK)",
    agent_url: "http://47.240.11.23:8000",
    enabled: true,
    testing: false,
    testStatus: "success"
  },
  {
    host_id: "backup-node",
    display_name: "备用冷备节点",
    agent_url: "http://192.168.22.105:8000",
    enabled: false,
    testing: false,
    testStatus: "none"
  }
]);

// Host 节点表单
const hostDialogVisible = ref(false);
const hostForm = reactive({
  host_id: "",
  display_name: "",
  agent_url: "",
  agent_token: "",
  enabled: true,
  isEdit: false
});

function goBack() {
  router.push("/");
}

function saveSettings() {
  ElMessage.success("设置更新成功！参数已写入数据库，后台轮询器已重载。");
}

function testConnection(row: any) {
  row.testing = true;
  row.testStatus = "none";
  setTimeout(() => {
    row.testing = false;
    if (row.host_id === "backup-node") {
      row.testStatus = "error";
      ElMessage.error(`连接失败：节点 ${row.display_name} 超时未响应。`);
    } else {
      row.testStatus = "success";
      ElMessage.success(`连接成功！节点 ${row.display_name} 在线（延迟 28ms）。`);
    }
  }, 1000);
}

function openAddHost() {
  hostForm.host_id = "";
  hostForm.display_name = "";
  hostForm.agent_url = "";
  hostForm.agent_token = "";
  hostForm.enabled = true;
  hostForm.isEdit = false;
  hostDialogVisible.value = true;
}

function openEditHost(row: any) {
  hostForm.host_id = row.host_id;
  hostForm.display_name = row.display_name;
  hostForm.agent_url = row.agent_url;
  hostForm.agent_token = "";
  hostForm.enabled = row.enabled;
  hostForm.isEdit = true;
  hostDialogVisible.value = true;
}

function submitHostForm() {
  if (!hostForm.host_id || !hostForm.display_name || !hostForm.agent_url) {
    ElMessage.warning("请填写必填项");
    return;
  }

  if (hostForm.isEdit) {
    const item = hosts.value.find(h => h.host_id === hostForm.host_id);
    if (item) {
      item.display_name = hostForm.display_name;
      item.agent_url = hostForm.agent_url;
      item.enabled = hostForm.enabled;
    }
    ElMessage.success(`主机节点「${hostForm.display_name}」已更新并写回 hosts.yaml`);
  } else {
    if (hosts.value.some(h => h.host_id === hostForm.host_id)) {
      ElMessage.error("host_id 已经存在");
      return;
    }
    hosts.value.push({
      host_id: hostForm.host_id,
      display_name: hostForm.display_name,
      agent_url: hostForm.agent_url,
      enabled: hostForm.enabled,
      testing: false,
      testStatus: "none"
    });
    ElMessage.success(`新建主机节点「${hostForm.display_name}」成功，已同步写入 hosts.yaml`);
  }
  hostDialogVisible.value = false;
}

function deleteHost(row: any) {
  ElMessageBox.confirm(
    `确认删除主机节点「${row.display_name}」吗？此操作将同步删除 YAML 配置，不可撤销。`,
    "安全删除提示",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "error",
      confirmButtonClass: "el-button--danger"
    }
  ).then(() => {
    hosts.value = hosts.value.filter(h => h.host_id !== row.host_id);
    ElMessage.success("主机节点删除成功，hosts.yaml 配置已写回。");
  }).catch(() => {});
}
</script>

<style scoped>
.playground-root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.playground-control-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--ui-radius-lg, 8px);
  padding: 14px 18px;
  gap: 16px;
  flex-wrap: wrap;
}

.control-left h2 {
  margin: 4px 0 0;
  font-size: 16px;
  color: var(--text-primary);
}

.style-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: viewFade 0.2s ease-out;
}

@keyframes viewFade {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── UI 布局基础重定义 (符合线上 audit.css / updates.css 等规范) ── */
.panel-padding {
  padding: 18px 20px;
}

.panel-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-header.no-border {
  border-bottom: none;
  margin-bottom: 8px;
}

.panel-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
}

.panel-desc {
  font-size: 12px;
  color: var(--text-secondary);
  display: block;
  margin-top: 4px;
}

.panel-header.flex-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 12px;
}

.panel-header-title.no-margin {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.panel-header-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.panel-icon {
  font-size: 16px;
  color: var(--accent-blue);
}

/* Form 布局 */
.form-row-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.form-row-4 {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.input-tip {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  display: inline-block;
  line-height: 1.3;
}

.divider-line {
  height: 1px;
  background: var(--border-subtle);
  margin: 24px 0 16px;
}

.form-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: flex-end;
}

.form-actions.text-right {
  justify-content: flex-end;
}

.row-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.mini-btn-adjust {
  height: 24px;
  font-size: 11px;
  padding: 0 8px;
}

/* ────────────────────────────────────────────────────────
 * Style A: Tab 样式适配 (Element Plus 卡片 Tab 覆写)
 * ──────────────────────────────────────────────────────── */
.tabs-container {
  background: transparent;
}

.custom-el-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}

.custom-el-tabs :deep(.el-tabs__item) {
  font-size: 13px !important;
  font-weight: 700 !important;
  height: 38px !important;
  line-height: 38px !important;
  border-color: var(--border-subtle) !important;
}

.custom-el-tabs :deep(.el-tabs__item.is-active) {
  background: var(--surface-panel) !important;
  color: var(--accent-blue) !important;
  border-bottom-color: var(--surface-panel) !important;
}

.custom-el-tabs :deep(.el-tabs__content) {
  overflow: visible !important;
}

/* ────────────────────────────────────────────────────────
 * Style B: 垂直卡片平铺流 (Vertical Panels)
 * ──────────────────────────────────────────────────────── */
.vertical-stack-flow {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ────────────────────────────────────────────────────────
 * Style C: 左右并排对称栅格 (Split Grid)
 * ──────────────────────────────────────────────────────── */
.split-grid-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.grid-left-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.grid-right-col {
  min-height: 100%;
}

.h-100 {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.h-100 .native-table-style {
  flex: 1;
}

/* Table Style Alignment */
.native-table-style {
  background: transparent !important;
}

.native-table-style :deep(.el-table__header-wrapper) th {
  background: var(--surface-muted, rgba(15, 23, 42, 0.4)) !important;
  color: var(--text-primary) !important;
  font-weight: 700 !important;
  font-size: 12px;
}

.native-table-style :deep(.el-table__row) td {
  background: transparent !important;
  font-size: 12px;
}
</style>
