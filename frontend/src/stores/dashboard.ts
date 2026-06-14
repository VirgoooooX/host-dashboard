import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiClient } from "@/api/client";

export interface HostSummary {
  host_id: string;
  display_name: string;
  status: "online" | "offline" | "degraded" | "unknown";
  metrics?: {
    hostname: string;
    timestamp: string;
    cpuPercent: number;
    memoryUsed: number;
    memoryTotal: number;
    diskUsed: number;
    diskTotal: number;
    loadavg: number[];
    uptime: number;
  };
  docker_version?: string;
  api_version?: string;
  os_info?: string;
  architecture?: string;
  docker_root_dir?: string;
  container_running: number;
  container_stopped: number;
  container_total: number;
  image_count: number;
  docker_disk_images?: number;
  docker_disk_containers?: number;
  docker_disk_volumes?: number;
  docker_disk_build_cache?: number;
  update_count: number;
}

export const useDashboardStore = defineStore("dashboard", () => {
  const hosts = ref<HostSummary[]>([]);
  const loading = ref(false);
  const error = ref("");

  const onlineCount = computed(() => hosts.value.filter((h) => h.status === "online").length);
  const runningContainers = computed(() =>
    hosts.value.reduce((s, h) => s + h.container_running, 0)
  );
  const totalContainers = computed(() =>
    hosts.value.reduce((s, h) => s + h.container_total, 0)
  );
  const totalStacks = computed(() => 0); // Will be populated via detail
  const updateCount = computed(() =>
    hosts.value.reduce((s, h) => s + h.update_count, 0)
  );

  let pollTimer: ReturnType<typeof setTimeout> | null = null;

  async function fetchHosts() {
    if (loading.value) return;
    loading.value = true;
    error.value = "";
    try {
      const res = await apiClient.get("/api/hosts");
      hosts.value = res.data.hosts || [];
    } catch (e: any) {
      error.value = e.message || "Failed to fetch hosts";
    } finally {
      loading.value = false;
    }
  }

  function startPolling(intervalMs = 10000) {
    stopPolling();
    pollTimer = setInterval(() => {
      // Pause when tab is hidden
      if (!document.hidden) {
        fetchHosts();
      }
    }, intervalMs);
    fetchHosts();
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  return {
    hosts,
    loading,
    error,
    onlineCount,
    runningContainers,
    totalContainers,
    totalStacks,
    updateCount,
    fetchHosts,
    startPolling,
    stopPolling,
  };
});
