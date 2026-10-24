const state = {
  bootstrap: null,
  selectedImage: null,
  outputDir: "",
  lastJobStatus: "idle",
  timer: 0,
  lastLogs: "",
};

function api(method, ...args) {
  if (
    !window.pywebview ||
    !window.pywebview.api ||
    typeof window.pywebview.api[method] !== "function"
  ) {
    return Promise.resolve({ ok: false, error: "客户端接口还没有准备好。" });
  }
  return window.pywebview.api[method](...args);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("is-error", Boolean(isError));
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(
    () => toast.classList.remove("is-visible"),
    3400,
  );
}

function setActiveStep(step) {
  document.querySelectorAll(".sidebar-step").forEach((item) => {
    item.classList.toggle("is-active", Number(item.dataset.step) === step);
  });
}

function setStatus(status, text) {
  const pill = document.getElementById("globalStatus");
  pill.textContent = text;
  pill.classList.remove("is-running", "is-completed", "is-failed");
  if (status === "running") pill.classList.add("is-running");
  if (status === "completed") pill.classList.add("is-completed");
  if (status === "failed") pill.classList.add("is-failed");
}

function guessSongFromName(name) {
  const stem = String(name || "").replace(/\.[^.]+$/, "");
  const match = stem.match(/^\s*(\d{1,4})[\s._-]+(.+?)\s*$/);
  if (match) return { number: match[1], title: match[2] };
  return { number: "", title: stem };
}

function applyImage(image) {
  state.selectedImage = image;
  const selected = document.getElementById("selectedImage");
  const preview = document.getElementById("imagePreview");
  const name = document.getElementById("imageName");
  const meta = document.getElementById("imageMeta");
  preview.src = image.url || "";
  name.textContent = image.name || "已选择歌谱";
  name.title = image.path || "";
  meta.textContent = "正在读取图片…";
  const probe = new Image();
  probe.onload = () => {
    meta.textContent = `${probe.naturalWidth} × ${probe.naturalHeight}`;
  };
  probe.onerror = () => {
    meta.textContent = "图片已选择";
  };
  probe.src = image.url || "";
  selected.hidden = false;
  document.getElementById("fileState").textContent = "已选择歌谱";
  const guessed = guessSongFromName(image.name);
  if (!document.getElementById("songNumber").value.trim()) {
    document.getElementById("songNumber").value = guessed.number;
  }
  if (!document.getElementById("songTitle").value.trim()) {
    document.getElementById("songTitle").value = guessed.title;
  }
  setActiveStep(2);
}

function clearImage() {
  state.selectedImage = null;
  document.getElementById("selectedImage").hidden = true;
  document.getElementById("imagePreview").src = "";
  document.getElementById("fileState").textContent = "支持 PNG / JPG / WEBP";
  setActiveStep(1);
}

function renderSamples(samples) {
  const root = document.getElementById("sampleList");
  if (!samples || !samples.length) {
    root.innerHTML = '<div class="log-line"><span>暂无内置示例。</span></div>';
    return;
  }
  root.innerHTML = samples
    .map(
      (sample) => `
        <button class="sample-item" type="button"
          data-path="${escapeHtml(sample.path)}"
          data-url="${escapeHtml(sample.url)}"
          data-name="${escapeHtml(sample.name)}">
          <img src="${escapeHtml(sample.url)}" alt="">
          <span>${escapeHtml(sample.name.replace(/\.[^.]+$/, ""))}</span>
          <em>试用</em>
        </button>
      `,
    )
    .join("");
}

function renderLogs(logs) {
  const root = document.getElementById("logList");
  const serialized = JSON.stringify(logs || []);
  if (serialized === state.lastLogs) return;
  state.lastLogs = serialized;
  if (!logs || !logs.length) {
    root.innerHTML =
      '<div class="log-line"><span class="log-dot"></span><span>准备就绪。</span></div>';
    return;
  }
  root.innerHTML = logs
    .map((item) => {
      const level =
        item.title === "出错了"
          ? "is-error"
          : item.title === "生成完成"
            ? "is-success"
            : "";
      return `
        <div class="log-line ${level}">
          <span class="log-dot"></span>
          <span>${escapeHtml(item.title)} · ${escapeHtml(item.message)}</span>
        </div>
      `;
    })
    .join("");
}

function renderPreviews(result) {
  const grid = document.getElementById("previewGrid");
  const empty = document.getElementById("previewEmpty");
  const previews = result?.previews || [];
  document.getElementById("resultCount").textContent = previews.length
    ? `已生成 ${previews.length} 张`
    : "还没有生成";
  if (!previews.length) {
    grid.hidden = true;
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  grid.hidden = false;
  grid.innerHTML = previews
    .map(
      (item) => `
        <button class="preview-item" type="button" data-path="${escapeHtml(item.path)}">
          <img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.name)}">
          <strong>${escapeHtml(item.name)}</strong>
        </button>
      `,
    )
    .join("");
}

function applyJob(job) {
  const status = job?.status || "idle";
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const progressTitle = document.getElementById("progressTitle");
  const progressMessage = document.getElementById("progressMessage");
  const openOutput = document.getElementById("openOutput");

  if (status === "running") {
    progressWrap.hidden = false;
    progressBar.style.width = `${Math.max(4, Number(job.progress || 0))}%`;
    progressTitle.textContent = "正在制作…";
    progressMessage.textContent = job.message || "请稍等片刻";
    setStatus("running", "制作中");
    setActiveStep(3);
  } else {
    progressWrap.hidden = status !== "completed" && status !== "failed";
    progressBar.style.width = `${Number(job.progress || 0)}%`;
    progressTitle.textContent = status === "failed" ? "制作没有完成" : "制作完成";
    progressMessage.textContent = job.error || job.message || "";
    if (status === "completed") {
      setStatus("completed", "已完成");
      setActiveStep(3);
    } else if (status === "failed") {
      setStatus("failed", "需要检查");
    } else {
      setStatus("idle", "等待制作");
    }
  }

  const result = job?.result || {};
  if (result.output_dir) {
    state.outputDir = result.output_dir;
    openOutput.disabled = false;
  }
  renderPreviews(result);
  renderLogs(job?.logs || []);
}

async function pollJob() {
  const response = await api("get_job_state");
  if (response.ok) applyJob(response.job);
}

async function bootstrap() {
  const response = await api("get_bootstrap");
  if (!response.ok) {
    showToast(response.error || "软件初始化失败。", true);
    return;
  }
  state.bootstrap = response;
  document.getElementById("versionLabel").textContent = `v${response.version || ""}`;
  document.getElementById("outputRoot").value =
    response.default_output_root || "";
  const settings = response.settings || {};
  const boldMode = settings.bold_mode || "none";
  document.querySelectorAll("#boldMode button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.value === boldMode);
  });
  if (settings.keep_metadata_first_page === false) {
    document.getElementById("keepMetadata").checked = false;
  }
  if (settings.make_chorus_page === false) {
    document.getElementById("makeChorus").checked = false;
  }
  renderSamples(response.samples || []);
}

async function chooseImage() {
  const response = await api("choose_image");
  if (!response.ok) {
    showToast(response.error || "选择图片失败。", true);
    return;
  }
  if (response.path) {
    applyImage({
      path: response.path,
      url: response.url,
      name: response.path.split(/[\\/]/).pop(),
    });
  }
}

async function chooseOutput() {
  const response = await api("choose_output_dir");
  if (!response.ok) {
    showToast(response.error || "选择目录失败。", true);
    return;
  }
  if (response.path) {
    document.getElementById("outputRoot").value = response.path;
  }
}

function getBoldMode() {
  return (
    document.querySelector("#boldMode button.is-active")?.dataset.value || "none"
  );
}

async function startBuild() {
  if (!state.selectedImage?.path) {
    showToast("请先选择一张歌谱图片。", true);
    setActiveStep(1);
    return;
  }
  const outputRoot = document.getElementById("outputRoot").value.trim();
  if (!outputRoot) {
    showToast("请先选择输出目录。", true);
    return;
  }

  const response = await api(
    "start_build",
    state.selectedImage.path,
    document.getElementById("songNumber").value.trim(),
    document.getElementById("songTitle").value.trim(),
    outputRoot,
    getBoldMode(),
    document.getElementById("keepMetadata").checked,
    document.getElementById("makeChorus").checked,
  );
  if (!response.ok) {
    showToast(response.error || "无法开始制作。", true);
    return;
  }
  applyJob({
    status: "running",
    message: "正在准备歌谱…",
    progress: 4,
    logs: [{ title: "开始制作", message: "正在读取图片" }],
    result: {},
  });
}

async function checkUpdates() {
  showToast("正在检查更新…");
  const response = await api("check_updates");
  if (!response.ok) {
    showToast(response.error || "暂时无法检查更新。", true);
    return;
  }
  if (response.has_update) {
    showToast(`发现新版本 v${response.latest}，正在打开更新页。`);
    await api("open_url", response.release_url);
  } else {
    showToast(`已是最新版本 v${response.current}。`);
  }
}

function bindDropZone() {
  const zone = document.getElementById("imageDrop");
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("is-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    zone.classList.remove("is-over");
    const response = await api("on_drop", event);
    if (!response.ok) {
      showToast(response.error || "无法读取拖入的图片。", true);
      return;
    }
    applyImage(response);
  });
}

function bindEvents() {
  document.getElementById("chooseImage").addEventListener("click", chooseImage);
  document.getElementById("clearImage").addEventListener("click", clearImage);
  document.getElementById("chooseOutput").addEventListener("click", chooseOutput);
  document.getElementById("startBuild").addEventListener("click", startBuild);
  document.getElementById("checkUpdate").addEventListener("click", checkUpdates);
  document.getElementById("blessingButton").addEventListener("click", () => {
    showToast("愿你的服侍成为祝福，也愿每一次投影都让人更清楚地看见诗歌。");
  });
  document.getElementById("openProject").addEventListener("click", () => {
    const projectDir = state.bootstrap?.project_dir;
    if (projectDir) api("open_path", projectDir);
  });
  document.getElementById("openOutput").addEventListener("click", () => {
    if (state.outputDir) api("open_path", state.outputDir);
  });
  document.getElementById("toggleLog").addEventListener("click", () => {
    const panel = document.getElementById("logPanel");
    const collapsed = panel.classList.toggle("is-collapsed");
    document.getElementById("toggleLog").textContent = collapsed ? "展开" : "收起";
  });
  document.querySelectorAll("#boldMode button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("#boldMode button").forEach((item) => {
        item.classList.toggle("is-active", item === button);
      });
    });
  });
  document.getElementById("sampleList").addEventListener("click", (event) => {
    const button = event.target.closest(".sample-item");
    if (!button) return;
    applyImage({
      path: button.dataset.path,
      url: button.dataset.url,
      name: button.dataset.name,
    });
  });
  document.getElementById("previewGrid").addEventListener("click", (event) => {
    const button = event.target.closest(".preview-item");
    if (button) api("open_path", button.dataset.path);
  });
  document.addEventListener("dragover", (event) => event.preventDefault());
  document.addEventListener("drop", (event) => {
    if (!event.target.closest("#imageDrop")) event.preventDefault();
  });
}

let initialized = false;

async function initialize() {
  if (initialized) return;
  initialized = true;
  bindDropZone();
  bindEvents();
  await bootstrap();
  window.clearInterval(state.timer);
  state.timer = window.setInterval(pollJob, 700);
}

function waitForApi() {
  if (window.pywebview && window.pywebview.api) {
    initialize();
    return;
  }
  window.setTimeout(waitForApi, 50);
}

window.addEventListener("pywebviewready", initialize);
waitForApi();
