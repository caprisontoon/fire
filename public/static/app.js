/* 단계 이동 · 금액 표시 · API 호출 · 결과 렌더링
   입력/출력 JSON 구조는 docs/03_데이터모델_API스펙.md 참고 */

const TOTAL_STEPS = 6;
let currentStep = 1;
let lastResult = null;
let chartNet = null;
let chartAssets = null;

// ── 금액을 "1억 2,000만 원" 식으로 읽기 쉽게 ──────────────
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

// ── 단계 이동 ──────────────────────────────────────────────
function showStep(step) {
  currentStep = step;
  document.querySelectorAll(".step").forEach((s) => s.classList.add("hidden"));
  document.getElementById("step-" + step).classList.remove("hidden");
  document.querySelectorAll("#step-nav button").forEach((b) => {
    b.classList.toggle("active", Number(b.dataset.step) === step);
  });
  document.getElementById("btn-prev").classList.toggle("hidden", step === 1);
  const next = document.getElementById("btn-next");
  next.classList.toggle("hidden", step >= 5); // 5단계는 [계산하기], 6단계는 끝
  window.scrollTo({ top: 0 });
}

document.getElementById("btn-prev").addEventListener("click", () => showStep(currentStep - 1));
document.getElementById("btn-next").addEventListener("click", () => showStep(currentStep + 1));
document.querySelectorAll("#step-nav button").forEach((b) => {
  b.addEventListener("click", () => {
    if (!b.disabled) showStep(Number(b.dataset.step));
  });
});

// ── 금액 입력칸 아래에 읽기 쉬운 단위 표시 ────────────────
document.querySelectorAll("input.money").forEach((input) => {
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

// ── 입력 수집 ──────────────────────────────────────────────
const num = (id) => Number(document.getElementById(id).value) || 0;

function collectInput() {
  return {
    basic: {
      current_age: num("current_age"),
      retire_age: num("retire_age"),
      married: document.getElementById("married").checked,
      insurance_status: document.getElementById("insurance_status").value,
      public_pension_start_age: num("public_pension_start_age"),
      annual_living_expense: num("annual_living_expense"),
    },
    income: { earned: num("earned"), business: num("business"), other: num("other") },
    financial: {
      interest: num("interest"),
      dividend_domestic: num("dividend_domestic"),
      dividend_foreign: num("dividend_foreign"),
      etf_domestic_equity_dist: num("etf_domestic_equity_dist"),
      etf_domestic_other_dist_and_gain: num("etf_domestic_other_dist_and_gain"),
      etf_foreign_dist: num("etf_foreign_dist"),
      capital_gain_foreign: num("capital_gain_foreign"),
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
      financial_assets: num("financial_assets"),
    },
  };
}

// ── API 호출 ──────────────────────────────────────────────
document.getElementById("btn-simulate").addEventListener("click", async () => {
  const errorBox = document.getElementById("error-box");
  errorBox.classList.add("hidden");
  const btn = document.getElementById("btn-simulate");
  btn.disabled = true;
  btn.textContent = "계산 중...";
  try {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectInput()),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(
        res.status === 422
          ? "입력값에 문제가 있습니다. 나이 범위(19~89세)와 음수 여부를 확인해 주세요."
          : "서버 오류가 발생했습니다 (" + res.status + ")"
      );
    }
    lastResult = await res.json();
    document.querySelector('#step-nav button[data-step="6"]').disabled = false;
    renderResults(lastResult);
    showStep(6);
  } catch (e) {
    errorBox.textContent = "⚠️ " + (e.message || "계산 요청에 실패했습니다. 서버가 켜져 있는지 확인해 주세요.");
    errorBox.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "📊 계산하기";
  }
});

// ── 결과 렌더링 ────────────────────────────────────────────
function renderResults(r) {
  renderCards(r);
  renderScenarioTable(r.scenarios);
  renderCharts(r.scenarios);
  renderDetailTable(r.scenarios[document.getElementById("detail-scenario").value]);
}

function renderCards(r) {
  const agg = r.aggregate_financial_tax;
  const tax = r.income_tax;
  const hi = r.health_insurance;

  const aggCard = agg.subject
    ? card("bad", "금융소득종합과세", "대상입니다",
        `금융소득 ${formatWon(agg.total)} — 기준선(2,000만 원)을 ${formatWon(-agg.margin)} 초과했습니다.`)
    : card("good", "금융소득종합과세", "대상이 아닙니다",
        `금융소득 ${formatWon(agg.total)} — 기준선까지 ${formatWon(agg.margin)} 여유가 있습니다.`);

  const taxCard = card("", "예상 연간 세금 합계", formatWon(tax.total_tax),
    `종합소득세 ${formatWon(tax.aggregate_income_tax)}` +
    (tax.financial_withholding_tax ? ` · 금융소득 원천징수 ${formatWon(tax.financial_withholding_tax)}` : "") +
    (tax.private_pension_tax ? ` · 연금소득세 ${formatWon(tax.private_pension_tax)}` : "") +
    (tax.foreign_capital_gain_tax ? ` · 해외 양도세 ${formatWon(tax.foreign_capital_gain_tax)}` : ""));

  let hiDesc = `적용 자격: ${hi.status_applied}`;
  if (hi.dependent_fail_reasons.length) {
    hiDesc += ` · 피부양자 불가 사유: ${hi.dependent_fail_reasons.join(", ")}`;
  } else if (hi.dependent_eligible) {
    hiDesc += " · 피부양자 유지 가능";
  }
  const hiCard = card(hi.dependent_eligible || hi.monthly_premium === 0 ? "good" : "",
    "예상 월 건강보험료", formatWon(hi.monthly_premium), hiDesc + " (장기요양 포함)");

  document.getElementById("result-cards").innerHTML = aggCard + taxCard + hiCard;
}

function card(cls, title, value, desc) {
  return `<div class="card ${cls}"><h4>${title}</h4><div class="value">${value}</div><div class="desc">${desc}</div></div>`;
}

function renderScenarioTable(scenarios) {
  const rows = Object.entries(scenarios).map(([key, s]) => {
    const retire = s.retire_year_snapshot;
    const retireRow = retire
      ? s.cashflow_by_age.find((r) => r.age === retire.age)
      : s.cashflow_by_age[0];
    const last = s.cashflow_by_age[s.cashflow_by_age.length - 1];
    return `<tr>
      <td><strong>${key}</strong><br><span style="font-size:0.78em">${s.label}</span></td>
      <td>${formatWon(s.financial_income_total)}</td>
      <td>${s.aggregate_subject ? "⚠️ 대상" : "✅ 비대상"}</td>
      <td>${formatWon(retireRow.insurance)}</td>
      <td>${formatWon(retireRow.net)}</td>
      <td>${s.asset_depletion_age ? s.asset_depletion_age + "세 ⚠️" : "90세까지 유지 ✅"}</td>
      <td>${formatWon(last.remaining_assets)}</td>
    </tr>`;
  });
  document.getElementById("scenario-table").innerHTML =
    `<tr><th>시나리오</th><th>금융소득(연)</th><th>종합과세</th><th>은퇴 첫해<br>건보료(연)</th><th>은퇴 첫해<br>순현금흐름</th><th>자산 소진</th><th>90세 자산 잔액</th></tr>` +
    rows.join("");
}

const SCENARIO_COLORS = { A: "#1e3a8a", B: "#059669", C: "#d97706" };

function renderCharts(scenarios) {
  const ages = scenarios.A.cashflow_by_age.map((r) => r.age);
  const makeDatasets = (field) =>
    Object.entries(scenarios).map(([key, s]) => ({
      label: `${key}: ${s.label}`,
      data: s.cashflow_by_age.map((r) => r[field]),
      borderColor: SCENARIO_COLORS[key],
      backgroundColor: SCENARIO_COLORS[key],
      tension: 0.2,
      pointRadius: 0,
      borderWidth: 2,
    }));

  const options = {
    responsive: true,
    interaction: { mode: "index", intersect: false },
    plugins: {
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatWon(ctx.parsed.y)}` } },
      legend: { labels: { boxWidth: 14 } },
    },
    scales: {
      x: { title: { display: true, text: "나이" } },
      y: { ticks: { callback: (v) => (v / 100_000_000).toFixed(1) + "억" } },
    },
  };

  if (chartNet) chartNet.destroy();
  chartNet = new Chart(document.getElementById("chart-net"), {
    type: "line",
    data: { labels: ages, datasets: makeDatasets("net") },
    options,
  });

  if (chartAssets) chartAssets.destroy();
  chartAssets = new Chart(document.getElementById("chart-assets"), {
    type: "line",
    data: { labels: ages, datasets: makeDatasets("remaining_assets") },
    options,
  });
}

function renderDetailTable(scenario) {
  const rows = scenario.cashflow_by_age.map(
    (r) => `<tr>
      <td>${r.age}세</td><td>${r.status}</td>
      <td>${formatWon(r.income)}</td><td>${formatWon(r.tax)}</td>
      <td>${formatWon(r.insurance)}</td><td>${formatWon(r.net)}</td>
      <td>${formatWon(r.remaining_assets)}</td>
    </tr>`
  );
  document.getElementById("detail-table").innerHTML =
    `<tr><th>나이</th><th>건보 자격</th><th>총수입</th><th>세금</th><th>건보료(연)</th><th>순현금흐름</th><th>자산 잔액</th></tr>` +
    rows.join("");
}

document.getElementById("detail-scenario").addEventListener("change", (e) => {
  if (lastResult) renderDetailTable(lastResult.scenarios[e.target.value]);
});

showStep(1);
