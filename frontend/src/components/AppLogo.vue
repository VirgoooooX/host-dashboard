<template>
  <svg
    class="app-logo"
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="app-logo-shell" x1="11" y1="13" x2="54" y2="52" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#8fd0ff" />
        <stop offset="0.52" stop-color="#78c8f2" />
        <stop offset="1" stop-color="#8de7b1" />
      </linearGradient>
      <linearGradient id="app-logo-core" x1="24" y1="19" x2="48" y2="42" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#60a5fa" />
        <stop offset="0.58" stop-color="#38bdf8" />
        <stop offset="1" stop-color="#22d3ee" />
      </linearGradient>
      <filter id="app-logo-depth" x="-18%" y="-14%" width="136%" height="142%" color-interpolation-filters="sRGB">
        <feDropShadow dx="0" dy="4.2" stdDeviation="2.4" flood-color="#334155" flood-opacity="0.28" />
        <feDropShadow dx="0" dy="1.4" stdDeviation="0.9" flood-color="#64748b" flood-opacity="0.22" />
        <feDropShadow dx="0" dy="-0.7" stdDeviation="0.35" flood-color="#ffffff" flood-opacity="0.30" />
      </filter>
    </defs>
    <g class="app-logo__mark" filter="url(#app-logo-depth)">
      <path
        class="app-logo__shell"
        d="M44.67 15.82c5.57 4.08 10.5 10.92 11.31 18.29.8 7.37-2.54 15.26-9.72 19.16-7.18 3.89-18.2 3.78-26.2-.18-8.01-3.96-13-11.76-12.18-19.77.81-8.01 7.43-16.23 15.53-20 8.1-3.78 15.69-1.58 21.26 2.5Z"
      />
      <path
        class="app-logo__core"
        d="M41.96 25.03c4.23 3.2 8.28 8.98 7.02 12.92-1.26 3.95-7.84 6.07-14.18 6.46-6.34.4-12.45-.95-15.46-4.78-3.01-3.84-2.92-10.17.55-14.19 3.48-4.02 10.34-5.73 16.32-3.93 2.02.61 3.96 1.64 5.75 3.52Z"
      />
      <path class="app-logo__highlight" d="M22.4 20.2c4.77-2.32 10.11-2.56 15.16-.67" />
      <circle class="app-logo__spark" cx="43.5" cy="31.5" r="2.6" />
    </g>
  </svg>
</template>

<style scoped>
.app-logo {
  display: block;
  width: 100%;
  height: 100%;
  background: transparent;
}

.app-logo__shell {
  fill: url("#app-logo-shell");
}

.app-logo__core {
  fill: url("#app-logo-core");
  opacity: 0.94;
}

.app-logo__highlight {
  fill: none;
  stroke: rgba(255, 255, 255, 0.56);
  stroke-linecap: round;
  stroke-width: 3;
}

.app-logo__spark {
  fill: rgba(255, 255, 255, 0.82);
}
</style>
