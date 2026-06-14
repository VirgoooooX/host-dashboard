<template>
  <el-tag :type="tagType" size="small" effect="dark">
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  status: string;
}>();

const label = computed(() => {
  const labels: Record<string, string> = {
    up_to_date: "最新",
    updatable: "可更新",
    needs_auth: "需认证",
    check_failed: "检查失败",
  };
  return labels[props.status] || props.status;
});

const tagType = computed(() => {
  const types: Record<string, string> = {
    up_to_date: "success",
    updatable: "danger",
    needs_auth: "warning",
    check_failed: "info",
  };
  return types[props.status] || "info";
});
</script>
