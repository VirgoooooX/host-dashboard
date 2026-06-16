<template>
  <section class="operation-terminal" :class="[`is-${status}`, { compact }]">
    <div class="terminal-head">
      <div class="terminal-title">
        <span class="terminal-mark">[_]</span>
        <strong>{{ actionTitle }}</strong>
        <span class="stack-name">{{ stackName }}</span>
      </div>

      <div class="terminal-tools">
        <span v-if="status !== 'running'" class="terminal-state" :class="`state-${status}`">
          <el-icon v-if="status === 'success'"><SuccessFilled /></el-icon>
          <el-icon v-else-if="status === 'error'"><WarningFilled /></el-icon>
          {{ statusLabel }}
        </span>
        <el-button v-if="lines.length > 0" size="small" text @click.stop="copyOutput">
          {{ copied ? "已复制" : "复制" }}
        </el-button>
        <el-button size="small" text aria-label="关闭操作输出" @click.stop="$emit('close')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <div ref="terminalRef" class="terminal-surface" />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { Close, SuccessFilled, WarningFilled } from "@element-plus/icons-vue";
import { Terminal as XtermTerminal, type ITheme } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

const props = withDefaults(defineProps<{
  stackName: string;
  action?: string;
  lines: string[];
  status: "running" | "success" | "error" | "idle";
  message: string;
  compact?: boolean;
}>(), {
  action: "",
  compact: false,
});

defineEmits<{ close: [] }>();

const terminalRef = ref<HTMLElement | null>(null);
const copied = ref(false);
let terminal: XtermTerminal | null = null;
let fitAddon: FitAddon | null = null;
let renderedSignature = "";
let resizeObserver: ResizeObserver | null = null;
let themeObserver: MutationObserver | null = null;

const darkTerminalTheme: ITheme = {
  background: "#000000",
  foreground: "#f8fbff",
  cursor: "#f8fbff",
  black: "#000000",
  blue: "#3b82f6",
  cyan: "#22d3ee",
  green: "#22c55e",
  red: "#ef4444",
  yellow: "#f59e0b",
  white: "#f8fbff",
};

const lightTerminalTheme: ITheme = {
  background: "#f8fafc",
  foreground: "#0f172a",
  cursor: "#0f172a",
  black: "#0f172a",
  blue: "#2563eb",
  cyan: "#0891b2",
  green: "#16a34a",
  red: "#dc2626",
  yellow: "#d97706",
  white: "#f8fafc",
};

const actionTitle = computed(() => {
  const labels: Record<string, string> = {
    start: "Starting",
    stop: "Stopping",
    restart: "Restarting",
    update: "Updating",
  };
  return labels[props.action] || "Operation";
});

const statusLabel = computed(() => {
  if (props.status === "success") return "完成";
  if (props.status === "error") return "失败";
  if (props.status === "idle") return "结束";
  return "";
});

onMounted(() => {
  terminal = new XtermTerminal({
    convertEol: true,
    cursorBlink: false,
    fontFamily: "'JetBrains Mono', 'Cascadia Code', Consolas, monospace",
    fontSize: 13,
    lineHeight: 1.2,
    rows: props.compact ? 7 : 10,
    scrollback: 800,
    theme: currentTerminalTheme(),
  });

  fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);

  if (terminalRef.value) {
    terminal.open(terminalRef.value);
    flushLines(true);
    nextTick(fitTerminal);

    resizeObserver = new ResizeObserver(() => fitTerminal());
    resizeObserver.observe(terminalRef.value);

    themeObserver = new MutationObserver(() => applyTerminalTheme());
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "class"],
    });
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  themeObserver?.disconnect();
  themeObserver = null;
  terminal?.dispose();
  terminal = null;
  fitAddon = null;
});

watch(
  () => [props.stackName, props.action],
  () => {
    renderedSignature = "";
    terminal?.clear();
    flushLines(true);
  },
);

watch(
  () => props.lines,
  () => {
    flushLines();
  },
  { deep: true, flush: "post" },
);

function fitTerminal() {
  try {
    fitAddon?.fit();
  } catch {
    // xterm can throw while the element is being mounted or hidden.
  }
}

function currentTerminalTheme(): ITheme {
  return document.documentElement.dataset.theme === "light"
    ? lightTerminalTheme
    : darkTerminalTheme;
}

function applyTerminalTheme() {
  if (!terminal) return;
  terminal.options.theme = currentTerminalTheme();
}

function flushLines(force = false) {
  if (!terminal) return;
  if (force && props.lines.length === 0) {
    renderedSignature = "__waiting__";
    terminal.clear();
    terminal.write("\x1b[2mWaiting for Dockge output...\x1b[0m\r\n");
    return;
  }

  const displayLines = formatDockgeOutput(props.lines);
  const signature = displayLines.join("\n");
  if (!force && signature === renderedSignature) return;

  renderedSignature = signature;
  terminal.clear();
  terminal.reset();
  terminal.options.theme = currentTerminalTheme();
  for (const line of displayLines) {
    terminal.write(normalizeTerminalLine(line));
  }
  fitTerminal();
}

function normalizeTerminalLine(line: string): string {
  const text = line.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  return `${text.replace(/\n/g, "\r\n")}\r\n`;
}

function formatDockgeOutput(lines: string[]): string[] {
  const output: string[] = [];
  const pullLineIndexes = new Map<string, number>();
  let activePullGroup = false;
  let lastPullKey: string | null = null;

  for (const rawLine of lines) {
    const splitLines = String(rawLine || "")
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .split("\n");

    for (const splitLine of splitLines) {
      const line = splitLine.trimEnd();
      if (!line) continue;

      const pullKey = dockgePullLineKey(line);
      if (pullKey) {
        const index = pullLineIndexes.get(pullKey);
        if (index === undefined) {
          pullLineIndexes.set(pullKey, output.length);
          output.push(line);
        } else {
          output[index] = line;
        }
        activePullGroup = true;
        lastPullKey = pullKey;
        continue;
      }

      const duration = pullDuration(line);
      if (activePullGroup && duration && lastPullKey) {
        const index = pullLineIndexes.get(lastPullKey);
        if (index !== undefined && !pullDuration(output[index])) {
          output[index] = `${output[index]}        ${duration}`;
        }
        continue;
      }

      if (activePullGroup && isTransientPullNoise(line)) {
        continue;
      }

      activePullGroup = false;
      lastPullKey = null;
      output.push(line);
    }
  }

  return output.slice(-120);
}

function dockgePullLineKey(line: string): string | null {
  const clean = stripAnsi(line).trim();
  if (/^\[\+\]\s+Pulling\b/.test(clean)) return "pull-summary";

  const serviceMatch = clean.match(/^[^\w.-]*([\w.-]+)\s+.*\bPulling\b/);
  if (serviceMatch) return `pull-service:${serviceMatch[1]}`;

  return null;
}

function isTransientPullNoise(line: string): boolean {
  const clean = stripAnsi(line).trim();
  return clean === "Pulling";
}

function pullDuration(line: string): string | null {
  return stripAnsi(line).trim().match(/^(\d+(?:\.\d+)?s)$/)?.[1] || null;
}

function stripAnsi(value: string): string {
  return value.replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "");
}

async function copyOutput() {
  try {
    await navigator.clipboard.writeText(props.lines.join("\n"));
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 1800);
  } catch {
    ElMessage.warning("复制失败");
  }
}
</script>

<style scoped>
.operation-terminal {
  overflow: hidden;
  border: 1px solid rgba(34, 197, 94, 0.74);
  border-radius: 7px;
  background: #000000;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.12);
}

:global([data-theme="light"] .operation-terminal) {
  background: #f8fafc;
  border-color: rgba(22, 163, 74, 0.42);
  box-shadow: 0 0 0 1px rgba(22, 163, 74, 0.08);
}

.operation-terminal.is-error {
  border-color: rgba(248, 113, 113, 0.86);
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.16);
}

:global([data-theme="light"] .operation-terminal.is-error) {
  border-color: rgba(220, 38, 38, 0.46);
  box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.10);
}

.operation-terminal.is-idle {
  border-color: var(--border-strong);
  box-shadow: none;
}

.terminal-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 0 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  background: #050914;
}

:global([data-theme="light"] .terminal-head) {
  border-bottom-color: rgba(60, 72, 88, 0.14);
  background: #eef2f7;
}

.terminal-title,
.terminal-tools,
.terminal-state {
  display: inline-flex;
  align-items: center;
  min-width: 0;
}

.terminal-title {
  gap: 8px;
  color: #f8fbff;
  font-family: var(--font-mono);
  font-size: 12px;
}

:global([data-theme="light"] .terminal-title) {
  color: #0f172a;
}

.terminal-title strong {
  font-weight: 800;
}

.terminal-mark {
  color: #3b82f6;
  font-weight: 900;
}

.stack-name {
  overflow: hidden;
  color: #f8fbff;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global([data-theme="light"] .stack-name) {
  color: #0f172a;
}

.terminal-tools {
  gap: 10px;
}

.terminal-tools :deep(.el-button) {
  min-height: 26px;
  padding: 0 2px !important;
  color: #8aa0b7 !important;
}

:global([data-theme="light"] .terminal-tools) :deep(.el-button) {
  color: #64748b !important;
}

.terminal-state {
  gap: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.state-success {
  color: var(--success);
}

.state-error {
  color: var(--danger);
}

.terminal-surface {
  height: 180px;
  padding: 12px 14px;
  background: #000000;
}

:global([data-theme="light"] .terminal-surface) {
  background: #f8fafc;
}

.operation-terminal.compact .terminal-surface {
  height: 142px;
}

.terminal-surface :deep(.xterm) {
  height: 100%;
}

.terminal-surface :deep(.xterm-viewport) {
  background: #000000 !important;
}

:global([data-theme="light"] .terminal-surface) :deep(.xterm-viewport) {
  background: #f8fafc !important;
}

.terminal-surface :deep(.xterm-screen) {
  padding-bottom: 1px;
}

@media (max-width: 720px) {
  .terminal-head {
    grid-template-columns: 1fr;
    padding: 8px 12px;
  }

  .terminal-tools {
    justify-content: space-between;
  }
}
</style>
