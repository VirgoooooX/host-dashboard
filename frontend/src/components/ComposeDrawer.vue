<template>
  <el-drawer
    :model-value="visible"
    size="72%"
    class="compose-drawer"
    :with-header="false"
    @close="$emit('close')"
  >
    <div class="compose-editor">
      <header class="compose-editor__header">
        <div>
          <div class="compose-editor__kicker">{{ t('compose.kicker') }}</div>
          <h2 v-if="!createMode">{{ stackName }}</h2>
          <el-input
            v-else
            v-model="newStackName"
            class="stack-name-input"
            :placeholder="t('compose.stackNamePlaceholder')"
            maxlength="64"
            clearable
          />
          <p>{{ composeFileName }}</p>
          <p v-if="managed" class="compose-editor__managed">{{ t('compose.managedByDockge') }}</p>
        </div>
        <div class="compose-editor__actions">
          <el-button class="ui-button ui-button--muted" :disabled="loading || saving" @click="$emit('close')">
            {{ t('compose.close') }}
          </el-button>
          <el-button
            class="ui-button"
            :loading="saving === 'save'"
            :disabled="!canSubmit || loading || !!saving"
            @click="save(false)"
          >
            {{ t('compose.saveDraft') }}
          </el-button>
          <el-button
            class="ui-button ui-button--primary"
            type="primary"
            :loading="saving === 'deploy'"
            :disabled="!canSubmit || loading || !!saving"
            @click="save(true)"
          >
            {{ t('compose.saveAndDeploy') }}
          </el-button>
        </div>
      </header>

      <el-alert
        v-if="!canSubmit && !loading"
        :title="emptyAlert"
        type="warning"
        show-icon
        :closable="false"
        class="compose-alert"
      />

      <div v-if="loading" class="compose-loading">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
      </div>

      <el-tabs
        v-else-if="saving !== 'deploy'"
        v-model="activeTab"
        class="compose-tabs"
      >
        <el-tab-pane :label="composeFileName" name="yaml">
          <el-input
            v-model="composeYaml"
            type="textarea"
            :disabled="!canUseEditor || !!saving"
            :autosize="{ minRows: 24, maxRows: 42 }"
            spellcheck="false"
            class="compose-textarea code"
          />
        </el-tab-pane>
        <el-tab-pane label=".env" name="env">
          <el-input
            v-model="composeEnv"
            type="textarea"
            :disabled="!canUseEditor || !!saving"
            :autosize="{ minRows: 16, maxRows: 32 }"
            spellcheck="false"
            class="compose-textarea code"
          />
        </el-tab-pane>
      </el-tabs>

      <div v-if="saving === 'deploy'" class="deploy-terminal">
        <div class="deploy-terminal-header">{{ t('compose.deployOutput') }}</div>
        <div class="deploy-terminal-viewport" ref="deployViewportRef">
          <div
            v-for="(line, i) in deployLines"
            :key="i"
            class="deploy-terminal-line"
          >{{ line }}</div>
          <div v-if="deployStreamActive" class="deploy-terminal-cursor">▊</div>
        </div>
      </div>

      <div v-if="operationStatus" class="compose-operation-status" :class="`op-${operationStatus.status}`">
        <el-icon v-if="operationStatus.status === 'running'" class="is-loading"><Loading /></el-icon>
        <el-icon v-else-if="operationStatus.status === 'success'"><SuccessFilled /></el-icon>
        <el-icon v-else-if="operationStatus.status === 'error'"><WarningFilled /></el-icon>
        <span class="op-message">{{ operationStatus.message }}</span>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { Loading, SuccessFilled, WarningFilled } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";
import { streamSse } from "@/api/sse";

const props = defineProps<{
  visible: boolean;
  hostId: string;
  stackName: string;
  createMode?: boolean;
}>();

const emit = defineEmits<{ close: []; saved: [] }>();

const { t } = useI18n();

const loading = ref(false);
const saving = ref<"save" | "deploy" | null>(null);
const activeTab = ref("yaml");
const composeYaml = ref("");
const composeEnv = ref("");
const composeFileName = ref("compose.yaml");
const newStackName = ref("");
const managed = ref(false);
const operationStatus = ref<{
  status: string;
  message: string;
  logTail?: string;
} | null>(null);

const deployLines = ref<string[]>([]);
const deployStreamActive = ref(false);
const deployViewportRef = ref<HTMLElement | null>(null);

const DEFAULT_COMPOSE_YAML = `services:
  app:
    image: nginx:latest
    restart: unless-stopped
`;

const createMode = computed(() => !!props.createMode);
const targetStackName = computed(() =>
  createMode.value ? newStackName.value.trim() : props.stackName
);
const hasValidStackName = computed(() =>
  !createMode.value || /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(targetStackName.value)
);
const canUseEditor = computed(() => createMode.value || !!composeYaml.value.trim());
const canSubmit = computed(() =>
  !!composeYaml.value.trim() && !!targetStackName.value && hasValidStackName.value
);
const emptyAlert = computed(() =>
  !targetStackName.value
    ? t("compose.emptyNameAlert")
    : !hasValidStackName.value
      ? t("compose.invalidNameAlert")
      : composeYaml.value.trim()
        ? ""
        : createMode.value
          ? t("compose.emptyYamlAlert")
          : t("compose.noComposeAlert")
);

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      operationStatus.value = null;
      deployLines.value = [];
      deployStreamActive.value = false;
      if (createMode.value) {
        initializeCreateCompose();
      } else {
        fetchCompose();
      }
    }
  },
  { immediate: true }
);

watch(
  () => deployLines.value.length,
  async () => {
    await nextTick();
    if (deployViewportRef.value) {
      deployViewportRef.value.scrollTop = deployViewportRef.value.scrollHeight;
    }
  }
);

function initializeCreateCompose() {
  loading.value = false;
  activeTab.value = "yaml";
  newStackName.value = "";
  composeYaml.value = DEFAULT_COMPOSE_YAML;
  composeEnv.value = "";
  composeFileName.value = "compose.yaml";
  managed.value = true;
}

async function fetchCompose() {
  loading.value = true;
  activeTab.value = "yaml";
  try {
    const res = await apiClient.get(
      `/api/hosts/${props.hostId}/stacks/${encodeURIComponent(props.stackName)}/compose`
    );
    composeYaml.value = res.data.compose_yaml || "";
    composeEnv.value = res.data.compose_env || "";
    composeFileName.value = res.data.compose_file_name || "compose.yaml";
    managed.value = !!res.data.is_managed_by_dockge;
  } catch (e: any) {
    managed.value = false;
    composeYaml.value = "";
    composeEnv.value = "";
    ElMessage.error(t("compose.readFailed", { detail: e.response?.data?.detail || e.message }));
  } finally {
    loading.value = false;
  }
}

async function save(deploy: boolean) {
  const stackNameForRequest = targetStackName.value;
  if (!stackNameForRequest) {
    ElMessage.error(t("compose.nameRequired"));
    return;
  }
  if (!hasValidStackName.value) {
    ElMessage.error(t("compose.nameInvalid"));
    return;
  }
  if (!composeYaml.value.trim()) {
    ElMessage.error(t("compose.emptyYamlAlert"));
    return;
  }

  const actionLabel = createMode.value ? t("compose.createAction") : t("compose.saveAction");
  try {
    await ElMessageBox.confirm(
      deploy
        ? t("compose.confirmDeploy", { action: actionLabel, name: stackNameForRequest })
        : t("compose.confirmSave", { action: actionLabel, name: stackNameForRequest }),
      deploy
        ? t("compose.confirmDeployTitle", { action: actionLabel })
        : t("compose.confirmSaveTitle", { action: actionLabel }),
      {
        confirmButtonText: deploy
          ? t("compose.confirmDeployTitle", { action: actionLabel })
          : actionLabel,
        cancelButtonText: t("compose.cancel"),
        type: deploy ? "warning" : "info",
      }
    );
  } catch {
    return;
  }

  if (!deploy) {
    saving.value = "save";

    operationStatus.value = {
      status: "running",
      message: t("compose.saving"),
    };

    try {
      const url = `/api/hosts/${props.hostId}/stacks/${encodeURIComponent(stackNameForRequest)}/compose`;
      const res = await apiClient.request({
        method: "put",
        url,
        data: {
          compose_yaml: composeYaml.value,
          compose_env: composeEnv.value,
          is_add: createMode.value,
        },
        timeout: 60000,
      });

      operationStatus.value = {
        status: "success",
        message: createMode.value ? t("compose.draftCreated") : t("compose.draftSaved"),
        logTail: res.data?.log_tail || undefined,
      };

      ElMessage.success(createMode.value ? t("compose.draftCreated") : t("compose.draftSaved"));
      emit("saved");
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message;

      operationStatus.value = {
        status: "error",
        message: t("compose.saveFailed", { detail }),
        logTail: e.response?.data?.log_tail || undefined,
      };

      ElMessage.error(t("compose.saveFailed", { detail }));
    } finally {
      saving.value = null;
    }
    return;
  }

  saving.value = "deploy";
  deployLines.value = [];
  deployStreamActive.value = true;

  operationStatus.value = {
    status: "running",
    message: t("compose.deploying"),
  };

  const url = `/api/hosts/${props.hostId}/stacks/${encodeURIComponent(stackNameForRequest)}/compose/deploy`;
  let completed = false;

  try {
    await streamSse({
      url,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      timeoutMs: 300000,
      body: JSON.stringify({
        compose_yaml: composeYaml.value,
        compose_env: composeEnv.value,
        is_add: createMode.value,
      }),
      onTimeout: () => {
        completed = true;
        deployStreamActive.value = false;
        operationStatus.value = {
          status: "error",
          message: t("compose.deployTimeout"),
        };
        ElMessage.warning(operationStatus.value.message);
      },
      onEvent: (ev) => {
        if (ev.event === "line") {
          deployLines.value.push(ev.data?.text ?? ev.rawData);
        } else if (ev.event === "complete") {
          completed = true;
          deployStreamActive.value = false;
          const data = ev.data || {};
          const success = data.status === "success";

          operationStatus.value = {
            status: success ? "success" : "error",
            message: data.message || (success ? t("compose.deploySuccess") : t("compose.deployFailed", { detail: "" })),
          };

          if (success) {
            ElMessage.success(createMode.value ? t("compose.createdAndDeployed") : t("compose.deployedAndSaved"));
            emit("saved");
          } else {
            ElMessage.error(t("compose.deployFailed", { detail: data.message || t("compose.unknownError") }));
          }
        } else if (ev.event === "error") {
          completed = true;
          deployStreamActive.value = false;
          const data = ev.data || {};
          operationStatus.value = {
            status: "error",
            message: t("compose.deployFailed", { detail: data.message || t("compose.unknownError") }),
          };
          ElMessage.error(operationStatus.value.message);
        }
      },
    });

    if (!completed && deployStreamActive.value) {
      deployStreamActive.value = false;
      operationStatus.value = {
        status: "success",
        message: t("compose.deployCompleted"),
      };
      ElMessage.success(createMode.value ? t("compose.createdAndDeployed") : t("compose.deployedAndSaved"));
      emit("saved");
    }
  } catch (e: any) {
    if (completed) return;
    deployStreamActive.value = false;
    const detail = e.message || t("compose.unknownError");
    operationStatus.value = {
      status: "error",
      message: t("compose.deployFailed", { detail }),
    };
    ElMessage.error(t("compose.deployFailed", { detail }));
  } finally {
    saving.value = null;
  }
}
</script>

<style scoped>
.compose-editor {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
}

.compose-editor__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 14px;
}

.compose-editor__kicker {
  color: var(--accent-blue);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.compose-editor h2 {
  margin: 4px 0 0;
  color: var(--text-primary);
  font-size: 20px;
}

.stack-name-input {
  width: min(360px, 62vw);
  margin-top: 4px;
}

.stack-name-input :deep(.el-input__wrapper) {
  background: var(--surface-base);
  border-radius: 6px;
  box-shadow: 0 0 0 1px var(--border-subtle) inset;
}

.compose-editor p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
}

.compose-editor__managed {
  color: var(--success) !important;
  font-family: var(--font-mono);
  font-size: 11px;
  margin-top: 4px;
}

.compose-editor__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.compose-alert {
  margin: 0;
}

.compose-loading {
  display: grid;
  place-items: center;
  min-height: 300px;
}

.compose-tabs {
  min-height: 0;
}

.compose-textarea :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.55;
  tab-size: 2;
}

.deploy-terminal {
  border: 1px solid #30363d;
  border-radius: 6px;
  overflow: hidden;
}

.deploy-terminal-header {
  padding: 6px 12px;
  background: #161b22;
  color: #8b949e;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid #30363d;
}

.deploy-terminal-viewport {
  background: #0d1117;
  padding: 12px;
  max-height: 60vh;
  overflow-y: auto;
  font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-all;
}

.deploy-terminal-line {
  color: #e6edf3;
  min-height: 1.55em;
}

.deploy-terminal-cursor {
  display: inline-block;
  color: #58a6ff;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.compose-operation-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
}
.compose-operation-status.op-running {
  background: rgba(59, 130, 246, 0.10);
  color: var(--accent-blue);
}
.compose-operation-status.op-success {
  background: rgba(22, 163, 74, 0.10);
  color: var(--success);
}
.compose-operation-status.op-error {
  background: rgba(220, 38, 38, 0.10);
  color: var(--danger);
}
.op-message {
  flex: 1;
  min-width: 0;
}

@media (max-width: 900px) {
  .compose-editor__header {
    flex-direction: column;
  }
}
</style>
