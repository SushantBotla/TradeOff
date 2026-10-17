"use strict";
fetch("site-config.json").then(r => r.json()).then(config => {
  if (config.mode === "live") document.getElementById("home-mode").textContent = "Connected runtime · Open the workspace to authenticate and run coordination";
}).catch(() => {});
