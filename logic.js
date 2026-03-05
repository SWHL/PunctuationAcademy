/**
 * 标点学堂 - 纯逻辑（无 DOM），供 app.js 与单元测试共用。
 * 浏览器：挂到 window.PunctuationLogic；Node：module.exports
 */
(function (global) {
  const PUNCTUATION_TYPES = ["逗号", "句号", "顿号", "分号", "冒号", "引号", "括号", "省略号", "破折号"];
  const CN_PUNCTUATION = new Set("，。、；：\"\"''（）【】—…");
  const MAX_STEM_LENGTH = 220;

  function normalizeBlanks(blanks) {
    return blanks.map((b) => {
      const item = { ...b };
      if (!item.punctuation_type && item.hint) item.punctuation_type = item.hint;
      else if (!item.punctuation_type) item.punctuation_type = "其他";
      return item;
    });
  }

  function splitBySentence(text) {
    if (!text || !text.trim()) return [];
    let inBracket = false;
    const splitPositions = [-1];
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === "【") inBracket = true;
      else if (c === "】") inBracket = false;
      else if (c === "。" && !inBracket) splitPositions.push(i);
    }
    splitPositions.push(text.length);
    const out = [];
    for (let k = 0; k < splitPositions.length - 1; k++) {
      let s = text.slice(splitPositions[k] + 1, splitPositions[k + 1]).trim();
      if (!s) continue;
      if (!s.endsWith("。") && !s.endsWith("【。】")) s += "。";
      out.push(s);
    }
    return out;
  }

  function charToHint(char) {
    const m = { "，": "逗号", "。": "句号", "、": "顿号", "；": "分号", "：": "冒号", '"': "引号", "'": "引号", "（": "括号", "）": "括号", "【": "括号", "】": "括号", "—": "破折号", "…": "省略号" };
    return m[char] || "其他";
  }

  function parseExplicit(content) {
    const result = [];
    const paragraphs = content.split(/\n\n/).map((p) => p.trim()).filter(Boolean);
    const re = /【([^】]*)】/g;
    for (const para of paragraphs) {
      const sentences = splitBySentence(para);
      for (const sent of sentences) {
        if (!sent.includes("【") && !sent.includes("】")) continue;
        const matches = [...sent.matchAll(re)];
        if (!matches.length) continue;
        const fullText = sent.replace(/【([^】]*)】/g, "$1");
        const blanks = [];
        for (const m of matches) {
          const ans = (m[1] || " ").trim() || " ";
          const beforeSeg = sent.slice(0, m.index);
          const beforeFull = beforeSeg.replace(/【([^】]*)】/g, "$1");
          const posInFull = beforeFull.length;
          const ptype = ans.length === 1 ? charToHint(ans) : (PUNCTUATION_TYPES.includes(ans) ? ans : "其他");
          blanks.push({ pos: posInFull, char: ans, hint: ans, punctuation_type: ptype });
        }
        if (fullText && blanks.length) {
          result.push({ text: fullText, blanks: normalizeBlanks(blanks), title: "自定义上传", source: "用户上传" });
        }
      }
    }
    return result;
  }

  /** 用户上传：按句拆分，每句内所有标点全部挖空，保证一题一句。 */
  function parseAutoBlank(content) {
    const result = [];
    const paragraphs = content.split(/\n\n/).map((p) => p.trim()).filter(Boolean);
    for (const para of paragraphs) {
      const sentences = splitBySentence(para);
      for (const sent of sentences) {
        if (sent.length < 2) continue;
        const positions = [...sent].map((c, i) => [i, c]).filter(([, c]) => CN_PUNCTUATION.has(c));
        if (positions.length < 1) continue;
        const chosen = positions.sort((a, b) => a[0] - b[0]);
        const blanks = chosen.map(([pos, char]) => ({
          pos,
          char,
          hint: charToHint(char),
          punctuation_type: charToHint(char),
        }));
        result.push({ text: sent, blanks, title: "自定义上传", source: "用户上传" });
      }
    }
    return result;
  }

  function parseUploadedTxt(content) {
    if (!content || !content.trim()) return [];
    const s = content.trim();
    if (s.includes("【") || s.includes("】")) return parseExplicit(s);
    return parseAutoBlank(s);
  }

  /**
   * 将题目列表两两合并为「每道题两个连续句子」，中间换行。
   * 奇数条时最后一条不合并（舍去）。不足两条则返回空数组。
   */
  function buildTwoSentenceQuestions(questions) {
    if (!questions || !Array.isArray(questions) || questions.length < 2) return [];
    const out = [];
    const sep = "\n";
    for (let i = 0; i + 1 < questions.length; i += 2) {
      const q1 = questions[i];
      const q2 = questions[i + 1];
      const len1 = (q1.text || "").length;
      const text = (q1.text || "") + sep + (q2.text || "");
      const blanks1 = (q1.blanks || []).map((b) => ({ ...b }));
      const blanks2 = (q2.blanks || []).map((b) => ({ ...b, pos: b.pos + len1 + sep.length }));
      const blanks = normalizeBlanks([...blanks1, ...blanks2]);
      out.push({
        text,
        blanks,
        title: q1.title || "",
        source: q1.source || "",
      });
    }
    return out;
  }

  function getSegments(text, blanks) {
    if (!blanks || !blanks.length) return text ? [text] : [""];
    const sorted = [...blanks].sort((a, b) => a.pos - b.pos);
    const segments = [];
    let start = 0;
    for (const b of sorted) {
      segments.push(text.slice(start, b.pos));
      start = b.pos + 1;
    }
    segments.push(text.slice(start));
    return segments;
  }

  function compareAnswers(userAnswers, correctBlanks) {
    const correctChars = correctBlanks.map((b) => b.char);
    const total = correctChars.length;
    const details = [];
    for (let i = 0; i < total; i++) {
      const user = userAnswers[i] !== undefined ? userAnswers[i] : "";
      const correct = correctChars[i];
      details.push({ user, correct, ok: user.trim() === correct.trim() });
    }
    const correctCount = details.filter((d) => d.ok).length;
    return { correctCount, total, details };
  }

  function filterQuestionsByType(questions, selectedTypes) {
    if (!selectedTypes || !selectedTypes.length) return questions;
    return questions.filter((q) =>
      (q.blanks || []).some((b) => selectedTypes.includes(b.punctuation_type))
    );
  }

  function pickRandomQuestion(questions, selectedTypes = []) {
    const pool = filterQuestionsByType(questions, selectedTypes).filter(
      (q) => (q.text || "").length <= MAX_STEM_LENGTH
    );
    if (!pool.length) return null;
    return pool[Math.floor(Math.random() * pool.length)];
  }

  function escapeHtml(str) {
    if (str == null) return "";
    const s = String(str);
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildResultHtml(correctText, blanks, userAnswers, details) {
    const sorted = [...(blanks || [])].sort((a, b) => a.pos - b.pos);
    const parts = [];
    let idx = 0;
    for (let i = 0; i < sorted.length; i++) {
      const b = sorted[i];
      parts.push(escapeHtml(correctText.slice(idx, b.pos)));
      let userChar = userAnswers[i] !== undefined ? userAnswers[i] : "";
      if (!userChar.trim()) userChar = "？";
      if (details[i] && !details[i].ok) {
        parts.push(`<span class="wrong-char">${escapeHtml(userChar)}</span>`);
      } else {
        parts.push(escapeHtml(userChar));
      }
      idx = b.pos + 1;
    }
    parts.push(escapeHtml(correctText.slice(idx)));
    const userDisplay = parts.join("");
    const toDisplayText = (s) => escapeHtml(s).replace(/\n/g, "<br>");
    return `
    <div class="result-card">
      <div class="result-section">
        <div class="result-label correct-label">✓ 正确答案</div>
        <p class="result-text">${toDisplayText(correctText)}</p>
      </div>
      <div class="result-section">
        <div class="result-label">您的答案</div>
        <p class="result-text">${userDisplay.replace(/\n/g, "<br>")}</p>
      </div>
      <p class="result-hint">标黄处为错误标点</p>
    </div>`;
  }

  function formatStats(total, answered) {
    const remaining = Math.max(0, total - answered);
    return `总题数：${total}　剩余：${remaining}　已答：${answered}`;
  }

  const api = {
    normalizeBlanks,
    splitBySentence,
    charToHint,
    parseExplicit,
    parseAutoBlank,
    parseUploadedTxt,
    buildTwoSentenceQuestions,
    getSegments,
    compareAnswers,
    filterQuestionsByType,
    pickRandomQuestion,
    escapeHtml,
    buildResultHtml,
    formatStats,
    MAX_STEM_LENGTH,
    PUNCTUATION_TYPES,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    global.PunctuationLogic = api;
  }
})(typeof window !== "undefined" ? window : this);
