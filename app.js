/**
 * 标点学堂 · Punctuation Academy（纯前端）
 * 逻辑与 Python 版一致；纯逻辑在 logic.js，此处负责加载、DOM、事件。
 */
const MAX_BLANKS = 10;

// 使用 logic.js 暴露的 API（浏览器中由 logic.js 挂到 window.PunctuationLogic）
const PunctuationLogicApi = typeof PunctuationLogic !== "undefined" ? PunctuationLogic : (typeof require !== "undefined" ? require("./logic.js") : {});
const {
  parseUploadedTxt,
  getSegments,
  compareAnswers,
  pickRandomQuestion,
  buildResultHtml,
  formatStats,
  escapeHtml,
} = PunctuationLogicApi;

// ——— 数据加载 ———
async function loadBuiltinArticles() {
  try {
    const res = await fetch("data/articles.json");
    const data = await res.json();
    const questions = [];
    for (const art of data.articles || []) {
      for (const seg of art.segments || []) {
        if (seg.text && seg.blanks && seg.blanks.length) {
          questions.push({
            text: seg.text,
            blanks: seg.blanks,
            title: art.title || "",
            source: art.source || "",
          });
        }
      }
    }
    return questions;
  } catch (e) {
    console.warn("loadBuiltinArticles failed", e);
    return [];
  }
}

// ——— 应用状态与 DOM ———
let builtinQuestions = [];
let uploadedQuestions = [];
let currentQuestion = null;
let answeredCount = 0;
/** 本轮已做过的题目（用 text 作 key），用于提示「均已做完」 */
let answeredSet = new Set();

const els = {};

function getPool() {
  if (uploadedQuestions.length) return uploadedQuestions;
  return builtinQuestions;
}

/** 从题库中筛掉本轮已做过的题，用于抽「换一题」 */
function getUnansweredPool() {
  const pool = getPool();
  if (!pool.length) return [];
  return pool.filter((q) => !answeredSet.has(q.text));
}

function renderQuestionOneLine(q) {
  if (!q || !q.blanks || !q.blanks.length) {
    return { html: '<p class="question-line">暂无题目。</p>', numBlanks: 0 };
  }
  const segments = getSegments(q.text, q.blanks);
  const parts = [];
  for (let i = 0; i < segments.length; i++) {
    const seg = escapeHtml(segments[i]).replace(/\n/g, "<br>");
    parts.push(`<span class="q-segment">${seg}</span>`);
    if (i < q.blanks.length) {
      parts.push(`<input type="text" class="blank-input" data-index="${i}" maxlength="2" placeholder="" />`);
    }
  }
  return {
    html: `<div class="question-block"><div class="question-line" data-question>${parts.join("")}</div></div>`,
    numBlanks: q.blanks.length,
  };
}

function bindBlankInputs(container, numBlanks, onSubmit) {
  const inputs = container.querySelectorAll(".blank-input");
  inputs.forEach((input, i) => {
    if (i >= numBlanks) return;
    input.value = "";
    input.style.display = "";
    input.placeholder = "";
    input.onkeydown = (e) => {
      if (e.key === "Enter") onSubmit();
      if (e.key === " ") {
        e.preventDefault();
        onSubmit();
      }
    };
  });
  for (let i = numBlanks; i < inputs.length; i++) {
    inputs[i].style.display = "none";
  }
}

function collectUserAnswers(container, numBlanks) {
  const inputs = container.querySelectorAll(".blank-input");
  const out = [];
  for (let i = 0; i < numBlanks && i < inputs.length; i++) {
    out.push((inputs[i].value || "").trim());
  }
  return out;
}

function onFileChange(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) {
    els.uploadMsg.textContent = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = (ev) => {
    const content = ev.target.result;
    const questions = parseUploadedTxt(content);
    if (!questions.length) {
      els.uploadMsg.textContent = "未能解析出题目（请检查格式：显式标注用【标点】；纯段落将自动挖空）。";
      uploadedQuestions = [];
    } else {
      uploadedQuestions = questions;
      els.uploadMsg.textContent = `已解析，共 ${questions.length} 道题可练习。点击「开始 / 换一题」即可使用。`;
    }
  };
  reader.readAsText(file, "UTF-8");
}

function onPasteClick() {
  const content = (els.pasteBox.value || "").trim();
  if (!content) {
    els.uploadMsg.textContent = "请先粘贴范文内容。";
    return;
  }
  const questions = parseUploadedTxt(content);
  if (!questions.length) {
    els.uploadMsg.textContent = "未能解析出题目（请检查格式：显式标注用【标点】；纯段落将自动挖空）。";
    return;
  }
  uploadedQuestions = uploadedQuestions.concat(questions);
  els.uploadMsg.textContent = `本次解析 ${questions.length} 道题，已加入题库；当前共 ${uploadedQuestions.length} 道可练习。`;
  els.pasteBox.value = "";
  onStartClick();
}

function showAllDoneHint() {
  els.questionWrap.innerHTML = '<p class="question-line all-done-hint">现有题目均已做完。点击「再来一轮」可重新练习本题库。</p>';
  els.hint.style.display = "none";
  if (els.btnResetRound) els.btnResetRound.style.display = "";
}

function onStartClick() {
  const pool = getPool();
  const unanswered = getUnansweredPool();
  els.result.innerHTML = "";
  if (els.btnResetRound) els.btnResetRound.style.display = "none";

  if (!pool.length) {
    els.questionWrap.innerHTML = '<p class="question-line">暂无题目。请使用内置题目或上传/粘贴范文。</p>';
    els.stats.textContent = formatStats(builtinQuestions.length, answeredCount);
    currentQuestion = null;
    return;
  }

  if (!unanswered.length) {
    showAllDoneHint();
    els.stats.textContent = formatStats(pool.length, answeredCount);
    currentQuestion = null;
    return;
  }

  currentQuestion = pickRandomQuestion(unanswered, []);
  if (!currentQuestion) {
    els.questionWrap.innerHTML = '<p class="question-line">暂无符合长度要求的题目，可尝试上传更多范文。</p>';
    els.stats.textContent = formatStats(pool.length, answeredCount);
    currentQuestion = null;
    return;
  }
  const { html, numBlanks } = renderQuestionOneLine(currentQuestion);
  els.questionWrap.innerHTML = html;
  bindBlankInputs(els.questionWrap, numBlanks, onSubmitClick);
  els.stats.textContent = formatStats(pool.length, answeredCount);
  els.hint.textContent = "在题目空位处按顺序填入标点（每格一个）。按 Enter 或空格提交。";
  els.hint.style.display = "";
}

function onResetRoundClick() {
  answeredSet.clear();
  onStartClick();
}

function onSubmitClick() {
  if (!currentQuestion) {
    els.result.innerHTML = "<p class=\"no-question\">请先点击「开始 / 换一题」获取题目。</p>";
    return;
  }
  const userAnswers = collectUserAnswers(els.questionWrap, currentQuestion.blanks.length);
  const { correctCount, total, details } = compareAnswers(userAnswers, currentQuestion.blanks);
  const html = buildResultHtml(currentQuestion.text, currentQuestion.blanks, userAnswers, details);
  const summary = `<p class="submit-summary">结果：<span class="correct-num">${correctCount}/${total}</span> 正确</p>`;
  els.result.innerHTML = summary + html;
  answeredCount += 1;
  answeredSet.add(currentQuestion.text);
  const pool = getPool();
  els.stats.textContent = formatStats(pool.length, answeredCount);
}

function init() {
  els.uploadMsg = document.getElementById("upload-msg");
  els.pasteBox = document.getElementById("paste-box");
  els.questionWrap = document.getElementById("question-wrap");
  els.hint = document.getElementById("answer-hint");
  els.stats = document.getElementById("stats");
  els.result = document.getElementById("result");
  els.fileInput = document.getElementById("file-input");
  els.btnPaste = document.getElementById("btn-paste");
  els.btnStart = document.getElementById("btn-start");
  els.btnSubmit = document.getElementById("btn-submit");
  els.btnResetRound = document.getElementById("btn-reset-round");

  els.fileInput.addEventListener("change", onFileChange);
  els.btnPaste.addEventListener("click", onPasteClick);
  els.btnStart.addEventListener("click", onStartClick);
  els.btnSubmit.addEventListener("click", onSubmitClick);
  if (els.btnResetRound) els.btnResetRound.addEventListener("click", onResetRoundClick);

  loadBuiltinArticles().then((qs) => {
    builtinQuestions = qs;
    els.stats.textContent = formatStats(builtinQuestions.length, 0);
  });

  els.questionWrap.innerHTML = '<p class="question-line">点击「开始 / 换一题」加载题目。</p>';
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}
