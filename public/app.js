const form = document.querySelector("#review-form");
const output = document.querySelector("#review-output");
const count = document.querySelector("#char-count");
const copyButton = document.querySelector("#copy-button");
const clearButton = document.querySelector("#clear-button");
const generateButton = document.querySelector("#generate-button");
const statusPill = document.querySelector("#status-pill");
const history = document.querySelector("#history");

let currentReview = "";
let selected = {
  scene: "朋友聚餐",
  tone: "真诚自然",
  sentiment: "正向好评"
};

document.querySelectorAll(".segments").forEach((group) => {
  group.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;

    group.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selected[group.dataset.name] = button.dataset.value;
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  setLoading(true);
  output.classList.remove("error");
  output.textContent = "生成中...";
  setCount("");

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, ...selected })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "生成失败，请稍后再试。");
    }

    showReview(data.review);
    addHistory(data.review);
  } catch (error) {
    currentReview = "";
    output.classList.add("error");
    output.textContent = error.message;
    copyButton.disabled = true;
  } finally {
    setLoading(false);
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentReview) return;

  await navigator.clipboard.writeText(currentReview);
  copyButton.textContent = "已复制";
  window.setTimeout(() => {
    copyButton.textContent = "复制";
  }, 1100);
});

clearButton.addEventListener("click", () => {
  currentReview = "";
  output.classList.remove("error");
  output.innerHTML = "<p>生成后的评价会出现在这里。</p>";
  setCount(0);
  copyButton.disabled = true;
});

checkHealth();

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();

    statusPill.classList.toggle("ready", data.hasApiKey);
    statusPill.classList.toggle("error", !data.hasApiKey);
    statusPill.textContent = data.hasApiKey ? data.model : "待配置";
  } catch {
    statusPill.classList.add("error");
    statusPill.textContent = "离线";
  }
}

function showReview(review) {
  currentReview = review;
  output.textContent = review;
  setCount(Array.from(review).length);
  copyButton.disabled = false;
}

function addHistory(review) {
  const item = document.createElement("button");
  item.className = "history-item";
  item.type = "button";
  item.textContent = review;
  item.addEventListener("click", () => showReview(review));

  history.prepend(item);

  while (history.children.length > 5) {
    history.lastElementChild.remove();
  }
}

function setCount(value) {
  count.textContent = value;
}

function setLoading(isLoading) {
  generateButton.disabled = isLoading;
  generateButton.classList.toggle("loading", isLoading);
  generateButton.querySelector("span:last-child").textContent = isLoading
    ? "生成中"
    : "生成评价";
}
