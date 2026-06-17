<template>
  <canvas ref="canvasRef" class="cluster-health-bg" />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";

const canvasRef = ref<HTMLCanvasElement | null>(null);
let animationId = 0;
let resizeObserver: ResizeObserver | null = null;

interface Blob {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  targetRadius: number;
  angle: number;
  speed: number;
}

// Beautiful premium blue & cyan & purple palette
const LIGHT_THEME_BLOBS = [
  { color: "rgba(37, 99, 235, 0.22)" },  // Royal Blue
  { color: "rgba(6, 182, 212, 0.18)" },  // Neon Cyan
  { color: "rgba(139, 92, 246, 0.18)" }, // Soft Violet
  { color: "rgba(59, 130, 246, 0.25)" }  // Sky Blue
];

const DARK_THEME_BLOBS = [
  { color: "rgba(37, 99, 235, 0.45)" },  // Royal Blue
  { color: "rgba(6, 182, 212, 0.35)" },  // Neon Cyan
  { color: "rgba(99, 102, 241, 0.40)" }, // Indigo
  { color: "rgba(139, 92, 246, 0.30)" }  // Violet
];

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let w = 0;
  let h = 0;
  let dpr = window.devicePixelRatio || 1;
  let blobs: Blob[] = [];

  function initBlobs() {
    blobs = [];
    const isDark = document.documentElement.getAttribute("data-theme") !== "light";
    const blobConfigs = isDark ? DARK_THEME_BLOBS : LIGHT_THEME_BLOBS;

    for (let i = 0; i < blobConfigs.length; i++) {
      const config = blobConfigs[i];
      // Random position around the canvas bounds
      const angle = Math.random() * Math.PI * 2;
      const speed = 0.4 + Math.random() * 0.4;
      
      blobs.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: Math.min(w, h) * (0.6 + Math.random() * 0.4),
        color: config.color,
        targetRadius: Math.min(w, h) * (0.6 + Math.random() * 0.4),
        angle: angle,
        speed: speed
      });
    }
  }

  function resize() {
    if (!canvas) return;
    const rect = canvas.parentElement!.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    w = rect.width;
    h = rect.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

    initBlobs();
  }

  resize();

  // Watch for theme changes dynamically
  const themeObserver = new MutationObserver(() => {
    initBlobs();
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"]
  });

  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas.parentElement!);

  function draw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    // Apply color blending
    ctx.globalCompositeOperation = "screen";

    for (const b of blobs) {
      // Slow organic movement with sine waves
      b.angle += 0.002;
      b.x += b.vx + Math.sin(b.angle) * 0.15;
      b.y += b.vy + Math.cos(b.angle) * 0.15;

      // Soft boundary bounce
      if (b.x < -b.radius * 0.2) { b.vx = Math.abs(b.vx); }
      if (b.x > w + b.radius * 0.2) { b.vx = -Math.abs(b.vx); }
      if (b.y < -b.radius * 0.2) { b.vy = Math.abs(b.vy); }
      if (b.y > h + b.radius * 0.2) { b.vy = -Math.abs(b.vy); }

      // Slow pulse radius
      b.radius += (b.targetRadius - b.radius) * 0.01;
      if (Math.abs(b.radius - b.targetRadius) < 1) {
        b.targetRadius = Math.min(w, h) * (0.6 + Math.random() * 0.4);
      }

      // Draw soft gradient blob
      const gradient = ctx.createRadialGradient(
        b.x, b.y, 0,
        b.x, b.y, b.radius
      );
      gradient.addColorStop(0, b.color);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    // Restore composite operation for content rendering stability
    ctx.globalCompositeOperation = "source-over";

    animationId = requestAnimationFrame(draw);
  }

  animationId = requestAnimationFrame(draw);

  onBeforeUnmount(() => {
    themeObserver.disconnect();
  });
});

onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId);
  if (resizeObserver) resizeObserver.disconnect();
});
</script>

<style scoped>
.cluster-health-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
  border-radius: inherit;
  filter: blur(40px); /* Smooth fluid merging */
  opacity: 0.85;
}
</style>
