/* 포트폴리오 설계 모드: 상품 구성 → 비교 시뮬레이션
   API: GET /api/product-types, POST /api/simulate-portfolio (docs/07 참고) */

let PRODUCT_TYPES = {};
let lastResult = null;
let chartNet = null;
let chartAssets = null;

function formatWon(value) {
  const n = Math.round(Number(value) || 0);
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  const eok = Math.floor(abs / 100_000_000);
  const man = Math.floor((abs % 100_000_000) / 10_000);
  const rest = abs % 10_000;
  let parts = [];
  if (eok) parts.push(eok.toLocaleString("ko-KR") + "억");
  if (man) parts.push(man.toLocaleString("ko-KR") + "만");
  if (!eok && !man) return sign + abs.toLocaleString("ko-KR") + " 원";
  if (rest) parts.push(rest.toLocaleString("ko-KR"));
  return sign + parts.join(" ") + " 원";
}

const num = (id) => Number(document.getElementById(id).value) || 0;

// ── 금액칸 한글 단위 표시 (id 기반 큰 입력칸) ──────────────
function attachMoneyDisplays() {
  document.querySelectorAll("input.money").forEach((input) => {
    if (input.dataset.bound) return;
    input.dataset.bound = "1";
    const display = document.createElement("p");
    display.className = "money-display";
    input.insertAdjacentElement("afterend", display);
    const update = () => {
      const v = Number(input.value);
      display.textContent = v > 0 ? "= " + formatWon(v) : "";
    };
    input.addEventListener("input", update);
    update();
  });
}

// ── 상품 보유 행 ──────────────────────────────────────────
function buildTypeOptions(select) {
  select.innerHTML = "";
  for (const [code, meta] of Object.entries(PRODUCT_TYPES)) {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = meta.label;
    select.appendChild(opt);
  }
}

function addHolding(holdingsEl, preset = {}) {
  const tpl = document.getElementById("holding-template");
  const row = tpl.content.firstElementChild.cloneNode(true);
  const typeSel = row.querySelector(".h-type");
  const labelInput = row.querySelector(".h-label");
  const amountInput = row.querySelector(".h-amount");
  const yieldInput = row.querySelector(".h-yield");
  const incomeSpan = row.querySelector(".h-income");
  const noteEl = document.createElement("p");
  noteEl.className = "h-note";

  buildTypeOptions(typeSel);
  if (preset.product_type) typeSel.value = preset.product_type;
  if (preset.label) labelInput.value = preset.label;
  if (preset.amount) amountInput.value = preset.amount;
  if (preset.annual_yield_pct != null) yieldInput.value = preset.annual_yield_pct;

  const refresh = () => {
    const income = Math.round((Number(amountInput.value) || 0) * (Number(yieldInput.value) || 0) / 100);
    incomeSpan.textContent = "연 " + formatWon(income);
    noteEl.textContent = (PRODUCT_TYPES[typeSel.value] || {}).note || "";
    updatePortfolioSubtotal(holdingsEl.closest(".portfolio-card"));
  };
  typeSel.addEventListener("change", refresh);
  amountInput.addEventListener("input", refresh);
  yieldInput.addEventListener("input", refresh);
  row.querySelector(".h-del").addEventListener("click", () => {
    const card = holdingsEl.closest(".portfolio-card");
    row.remove();
    noteEl.remove();
    updatePortfolioSubtotal(card);
  });

  holdingsEl.appendChild(row);
  holdingsEl.appendChild(noteEl);
  refresh();
}

function updatePortfolioSubtotal(card) {
  if (!card) return;
  let total = 0;
  card.querySelectorAll(".holding-row").forEach((r) => {
    total += Number(r.querySelector(".h-amount").value) || 0;
  });
  card.querySelector(".pf-subtotal").textContent = "평가액 합계: " + formatWon(total);
}

// ── 포트폴리오 카드 ───────────────────────────────────────
let portfolioCount = 0;

function addPortfolio(preset = {}) {
  if (document.querySelectorAll(".portfolio-card").length >= 3) return;
  portfolioCount++;
  const card = document.createElement("div");
  card.className = "portfolio-card";
  card.innerHTML = `
    <div class="pf-head">
      <input class="pf-name" type="text" value="${preset.label || "포트폴리오 " + portfolioCount}">
      <button class="pf-del" title="이 포트폴리오 삭제">✕ 삭제</button>
    </div>
    <div class="holdings"></div>
    <div class="pf-foot">
      <button class="add-holding add-btn">＋ 상품 추가</button>
      <span class="pf-subtotal"></span>
    </div>`;
  const holdingsEl = card.querySelector(".holdings");
  card.querySelector(".add-holding").addEventListener("click", () => addHolding(holdingsEl));
  card.querySelector(".pf-del").addEventListener("click", () => {
    card.remove();
    toggleAddPortfolioBtn();
  });

  document.getElementById("portfolios").appendChild(card);
  (preset.holdings || [{}]).forEach((h) => addHolding(holdingsEl, h));
  updatePortfolioSubtotal(card);
  toggleAddPortfolioBtn();
}

function toggleAddPortfolioBtn() {
  document.getElementById("btn-add-portfolio").style.display =
    document.querySelectorAll(".portfolio-card").length >= 3 ? "none" : "";
}

// ── 입력 수집 ──────────────────────────────────────────────
function collectInput() {
  const portfolios = [];
  document.querySelectorAll(".portfolio-card").forEach((card) => {
    const holdings = [];
    card.querySelectorAll(".holding-row").forEach((r) => {
      const amount = Number(r.querySelector(".h-amount").value) || 0;
      if (amount <= 0) return;
      holdings.push({
        product_type: r.querySelector(".h-type").value,
        label: r.querySelector(".h-label").value,
        amount,
        annual_yield_pct: Number(r.querySelector(".h-yield").value) || 0,
      });
    });
    portfolios.push({ label: card.querySelector(".pf-name").value, holdings });
  });
  return {
    basic: {
      current_age: num("current_age"),
      target_age: num("target_age"),
      married: document.getElementById("married").checked,
      insurance_status: document.getElementById("insurance_status").value,
      public_pension_start_age: num("public_pension_start_age"),
      annual_living_expense: num("annual_living_expense"),
    },
    pension: {
      public_annual: num("public_annual"),
      private_annual: num("private_annual"),
      tax_free_annual: num("tax_free_annual"),
      housing_monthly: num("housing_monthly"),
    },
    property: {
      real_estate_tax_base: num("real_estate_tax_base"),
      rent_monthly: num("rent_monthly"),
    },
    portfolios,
  };
}

// ── API 호출 ──────────────────────────────────────────────
document.getElementById("btn-simulate").addEventListener("click", async () => {
  const errorBox = document.getElementById("error-box");
  errorBox.classList.add("hidden");
  const input = collectInput();
  if (input.portfolios.every((p) => p.holdings.length === 0)) {
    errorBox.textContent = "⚠️ 상품을 1개 이상 입력해 주세요 (평가금액과 수익률 필요).";
    errorBox.classList.remove("hidden");
    return;
  }
  const btn = document.getElementById("btn-simulate");
  btn.disabled = true; btn.textContent = "계산 중...";
  try {
    const res = await fetch("/api/simulate-portfolio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      throw new Error(res.status === 422
        ? "입력값을 확인해 주세요 (나이 범위, 수익률 0~100%)."
        : "서버 오류 (" + res.status + ")");
    }
    lastResult = await res.json();
    renderResults(lastResult);
    document.getElementById("result-section").classList.remove("hidden");
    document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    errorBox.textContent = "⚠️ " + e.message;
    errorBox.classList.remove("hidden");
  } finally {
    btn.disabled = false; btn.textContent = "📊 비교 계산하기";
  }
});

// ── 결과 렌더링 ────────────────────────────────────────────
function renderResults(r) {
  const ps = r.portfolios;
  // 비교 표
  const head = `<tr><th>항목</th>${ps.map((p) => `<th>${escapeHtml(p.label)}</th>`).join("")}</tr>`;
  const rowsDef = [
    ["평가액 합계", (p) => formatWon(p.total_value)],
    ["연 금융소득", (p) => formatWon(p.financial_income_total)],
    ["금융소득종합과세", (p) => p.aggregate_subject
      ? `<span class="bad-text">⚠️ 대상</span>`
      : `<span class="good-text">✅ 비대상</span>`],
    [`${r.target_age}세 예상 세금(연)`, (p) => formatWon(p.target_snapshot.income_tax.total_tax)],
    [`${r.target_age}세 월 건보료`, (p) => formatWon(p.target_snapshot.health_insurance.monthly_premium)],
    ["피부양자 유지", (p) => p.target_snapshot.health_insurance.dependent_eligible
      ? "✅ 유지" : `<span class="bad-text">불가</span>`],
    [`${r.target_age}세 순현금흐름(연)`, (p) => formatWon(p.target_snapshot.net)],
    ["자산 소진", (p) => p.asset_depletion_age
      ? `<span class="bad-text">${p.asset_depletion_age}세</span>` : "90세까지 유지 ✅"],
    ["90세 자산 잔액", (p) => formatWon(p.cashflow_by_age[p.cashflow_by_age.length - 1].remaining_assets)],
  ];
  const body = rowsDef.map(([label, fn]) =>
    `<tr><td class="row-label">${label}</td>${ps.map((p) => `<td>${fn(p)}</td>`).join("")}</tr>`
  ).join("");
  document.getElementById("compare-table").innerHTML = head + body;

  // 금융소득 내역 카드
  document.getElementById("breakdowns").innerHTML = ps.map((p) => {
    const items = Object.entries(p.income_breakdown)
      .map(([k, v]) => `<li>${escapeHtml(k)}: <strong>${formatWon(v)}</strong></li>`).join("");
    const tf = p.tax_free_income > 0
      ? `<li class="good-text">분리과세·비과세(금융소득 제외): ${formatWon(p.tax_free_income)}</li>` : "";
    return `<div class="card"><h4>${escapeHtml(p.label)}</h4><ul class="breakdown">${items}${tf}</ul></div>`;
  }).join("");

  // 상세 드롭다운
  const pick = document.getElementById("detail-pick");
  pick.innerHTML = ps.map((p, i) => `<option value="${i}">${escapeHtml(p.label)}</option>`).join("");
  renderDetailTable(ps[0]);

  renderCharts(ps);

  document.getElementById("disclaimer-list").innerHTML =
    r.disclaimers.map((d) => `<li>${escapeHtml(d)}</li>`).join("");
}

const COLORS = ["#1e3a8a", "#059669", "#d97706"];

function renderCharts(ps) {
  const ages = ps[0].cashflow_by_age.map((r) => r.age);
  const makeDatasets = (field) => ps.map((p, i) => ({
    label: p.label,
    data: p.cashflow_by_age.map((r) => r[field]),
    borderColor: COLORS[i], backgroundColor: COLORS[i],
    tension: 0.2, pointRadius: 0, borderWidth: 2,
  }));
  const options = {
    responsive: true,
    interaction: { mode: "index", intersect: false },
    plugins: {
      tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${formatWon(c.parsed.y)}` } },
      legend: { labels: { boxWidth: 14 } },
    },
    scales: {
      x: { title: { display: true, text: "나이" } },
      y: { ticks: { callback: (v) => (v / 100_000_000).toFixed(1) + "억" } },
    },
  };
  if (chartNet) chartNet.destroy();
  chartNet = new Chart(document.getElementById("chart-net"),
    { type: "line", data: { labels: ages, datasets: makeDatasets("net") }, options });
  if (chartAssets) chartAssets.destroy();
  chartAssets = new Chart(document.getElementById("chart-assets"),
    { type: "line", data: { labels: ages, datasets: makeDatasets("remaining_assets") }, options });
}

function renderDetailTable(p) {
  const rows = p.cashflow_by_age.map((r) => `<tr>
    <td>${r.age}세</td><td>${r.status}</td><td>${formatWon(r.income)}</td>
    <td>${formatWon(r.tax)}</td><td>${formatWon(r.insurance)}</td>
    <td>${formatWon(r.net)}</td><td>${formatWon(r.remaining_assets)}</td></tr>`).join("");
  document.getElementById("detail-table").innerHTML =
    `<tr><th>나이</th><th>건보 자격</th><th>총수입</th><th>세금</th><th>건보료(연)</th><th>순현금흐름</th><th>자산 잔액</th></tr>` + rows;
}

document.getElementById("detail-pick").addEventListener("change", (e) => {
  if (lastResult) renderDetailTable(lastResult.portfolios[Number(e.target.value)]);
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ── 초기화 ────────────────────────────────────────────────
document.getElementById("btn-add-portfolio").addEventListener("click", () => addPortfolio());

(async function init() {
  attachMoneyDisplays();
  try {
    PRODUCT_TYPES = await (await fetch("/api/product-types")).json();
  } catch (e) {
    PRODUCT_TYPES = { domestic_stock: { label: "국내 주식 (배당주)", note: "" } };
  }
  // 예시 2개 프리필: 배당주 중심 vs ETF 중심
  addPortfolio({
    label: "배당주 중심",
    holdings: [
      { product_type: "domestic_stock", label: "고배당주", amount: 400000000, annual_yield_pct: 4.5 },
      { product_type: "reits", label: "리츠", amount: 200000000, annual_yield_pct: 6 },
    ],
  });
  addPortfolio({
    label: "ETF 중심",
    holdings: [
      { product_type: "domestic_equity_etf", label: "국내 주식형 ETF", amount: 400000000, annual_yield_pct: 1.5 },
      { product_type: "foreign_etf", label: "해외 상장 ETF", amount: 200000000, annual_yield_pct: 1.2 },
    ],
  });
})();
