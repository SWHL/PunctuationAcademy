/**
 * 标点学堂 web 端 - logic.js 单元测试
 * 运行：在项目根目录执行 node web/tests/logic.test.js
 * 或：cd web && node tests/logic.test.js
 */
const { describe, it } = require("node:test");
const assert = require("node:assert");

const L = require("../logic.js");

const {
  parseUploadedTxt,
  buildTwoSentenceQuestions,
  getSegments,
  compareAnswers,
  filterQuestionsByType,
  pickRandomQuestion,
  escapeHtml,
  buildResultHtml,
  formatStats,
  splitBySentence,
  parseExplicit,
  MAX_STEM_LENGTH,
} = L;

// ----- parseUploadedTxt / parseExplicit：显式标注 -----
describe("parseUploadedTxt / parseExplicit", () => {
  it("显式标注单句：【，】【。】解析为一段，pos 与 char 正确", () => {
    const content = "春天来了【，】花园里的花都开了【。】";
    const result = parseUploadedTxt(content);
    assert.strictEqual(result.length, 1);
    const q = result[0];
    assert.strictEqual(q.text, "春天来了，花园里的花都开了。");
    assert.strictEqual(q.blanks.length, 2);
    assert.strictEqual(q.blanks[0].char, "，");
    assert.strictEqual(q.blanks[0].pos, 4);
    assert.strictEqual(q.blanks[1].char, "。");
    assert.strictEqual(q.blanks[1].pos, 13);
  });

  it("显式标注多段：按空行分段落，按句号分句", () => {
    const content = "第一段【，】结束。\n\n第二段【。】";
    const result = parseUploadedTxt(content);
    assert.strictEqual(result.length, 2);
    assert.strictEqual(result[0].text, "第一段，结束。");
    assert.strictEqual(result[1].text, "第二段。");
  });

  it("空【】解析为空格占位", () => {
    const content = "有【】空";
    const result = parseUploadedTxt(content);
    assert.strictEqual(result.length, 1);
    assert(result[0].text.includes("有") && result[0].text.includes("空"));
  });

  it("无【】时走自动挖空分支", () => {
    const content = "春天来了，花园里的花都开了。";
    const result = parseUploadedTxt(content);
    assert.strictEqual(result.length, 1);
    const q = result[0];
    assert.strictEqual(q.text, content);
    assert(q.blanks.length >= 2 && q.blanks.length <= 5);
    q.blanks.forEach((b) => {
      assert(b.pos >= 0 && b.pos < content.length);
      assert.strictEqual(content[b.pos], b.char);
    });
  });

  it("空内容返回空数组", () => {
    assert.deepStrictEqual(parseUploadedTxt(""), []);
    assert.deepStrictEqual(parseUploadedTxt("   \n  "), []);
  });
});

// ----- splitBySentence -----
describe("splitBySentence", () => {
  it("按句号分句，【】内句号不参与分割", () => {
    const text = "第一句。【第二句。】第三句。";
    const out = splitBySentence(text);
    assert(out.length >= 2);
    assert(out.some((s) => s.includes("第一句")));
    assert(out.some((s) => s.includes("第三句")));
  });

  it("空字符串返回空数组", () => {
    assert.deepStrictEqual(splitBySentence(""), []);
    assert.deepStrictEqual(splitBySentence("   "), []);
  });
});

// ----- buildTwoSentenceQuestions -----
describe("buildTwoSentenceQuestions", () => {
  it("两两合并为两道题，中间换行", () => {
    const questions = [
      { text: "第一句。", blanks: [{ pos: 3, char: "。" }] },
      { text: "第二句。", blanks: [{ pos: 3, char: "。" }] },
      { text: "第三句。", blanks: [{ pos: 3, char: "。" }] },
      { text: "第四句。", blanks: [{ pos: 3, char: "。" }] },
    ];
    const out = buildTwoSentenceQuestions(questions);
    assert.strictEqual(out.length, 2);
    assert.strictEqual(out[0].text, "第一句。\n第二句。");
    assert.strictEqual(out[1].text, "第三句。\n第四句。");
    assert.strictEqual(out[0].blanks.length, 2);
    assert.strictEqual(out[0].blanks[1].pos, 3 + 1 + 4);
  });

  it("不足两条返回空数组", () => {
    assert.deepStrictEqual(buildTwoSentenceQuestions([]), []);
    assert.deepStrictEqual(buildTwoSentenceQuestions([{ text: "一。", blanks: [] }]), []);
  });
});

// ----- getSegments -----
describe("getSegments", () => {
  it("按 blanks 的 pos 拆成 len(blanks)+1 段", () => {
    const text = "句子内部并列词语之间用顿号，例如：苹果、香蕉、橙子。";
    const blanks = [{ pos: 13 }, { pos: 16 }, { pos: 19 }, { pos: 22 }, { pos: 25 }];
    const segs = getSegments(text, blanks);
    assert.strictEqual(segs.length, 6);
    assert.strictEqual(segs[0], "句子内部并列词语之间用顿号");
    assert.strictEqual(segs[1], "例如");
    assert.strictEqual(segs[2], "苹果");
    assert.strictEqual(segs[3], "香蕉");
    assert.strictEqual(segs[4], "橙子");
    assert.strictEqual(segs[5], "");
  });

  it("无 blanks 返回整段", () => {
    assert.deepStrictEqual(getSegments("hello", []), ["hello"]);
  });
});

// ----- compareAnswers -----
describe("compareAnswers", () => {
  it("全对", () => {
    const user = ["，", "。"];
    const blanks = [{ pos: 4, char: "，" }, { pos: 13, char: "。" }];
    const { correctCount, total, details } = compareAnswers(user, blanks);
    assert.strictEqual(correctCount, 2);
    assert.strictEqual(total, 2);
    assert(details.every((d) => d.ok));
  });

  it("部分对", () => {
    const user = ["，", "x"];
    const blanks = [{ pos: 4, char: "，" }, { pos: 13, char: "。" }];
    const { correctCount, total, details } = compareAnswers(user, blanks);
    assert.strictEqual(correctCount, 1);
    assert.strictEqual(total, 2);
    assert.strictEqual(details[0].ok, true);
    assert.strictEqual(details[1].ok, false);
    assert.strictEqual(details[1].user, "x");
    assert.strictEqual(details[1].correct, "。");
  });

  it("用户答案少于空位数", () => {
    const user = ["，"];
    const blanks = [{ pos: 4, char: "，" }, { pos: 13, char: "。" }];
    const { correctCount, total, details } = compareAnswers(user, blanks);
    assert.strictEqual(total, 2);
    assert.strictEqual(correctCount, 1);
    assert.strictEqual(details[1].user, "");
    assert.strictEqual(details[1].ok, false);
  });
});

// ----- filterQuestionsByType / pickRandomQuestion -----
describe("filterQuestionsByType & pickRandomQuestion", () => {
  it("空题型返回原列表", () => {
    const questions = [{ text: "a。", blanks: [{ punctuation_type: "句号" }] }];
    const filtered = filterQuestionsByType(questions, []);
    assert.strictEqual(filtered.length, questions.length);
  });

  it("按题型筛选", () => {
    const questions = [
      { text: "一，二。", blanks: [{ punctuation_type: "逗号" }, { punctuation_type: "句号" }] },
      { text: "只有句号。", blanks: [{ punctuation_type: "句号" }] },
    ];
    const filtered = filterQuestionsByType(questions, ["句号"]);
    assert(filtered.length >= 1);
    filtered.forEach((q) => {
      const types = new Set(q.blanks.map((b) => b.punctuation_type));
      assert(types.has("句号"));
    });
  });

  it("无题目时返回 null", () => {
    assert.strictEqual(pickRandomQuestion([], []), null);
  });

  it("选题长度不超过 MAX_STEM_LENGTH", () => {
    const longText = "一".repeat(MAX_STEM_LENGTH + 1);
    const shortText = "春天来了，花开了。";
    const questions = [
      { text: longText, blanks: [{ pos: 0, char: "，", punctuation_type: "逗号" }] },
      { text: shortText, blanks: [{ pos: 4, char: "，", punctuation_type: "逗号" }, { pos: 7, char: "。", punctuation_type: "句号" }] },
    ];
    for (let i = 0; i < 10; i++) {
      const q = pickRandomQuestion(questions, []);
      assert(q != null);
      assert.strictEqual(q.text, shortText);
      assert(q.text.length <= MAX_STEM_LENGTH);
    }
  });
});

// ----- escapeHtml -----
describe("escapeHtml", () => {
  it("转义 & < > \"", () => {
    assert.strictEqual(escapeHtml("a<b>c"), "a&lt;b&gt;c");
    assert.strictEqual(escapeHtml('"x"'), "&quot;x&quot;");
    assert.strictEqual(escapeHtml("&"), "&amp;");
  });
});

// ----- buildResultHtml -----
describe("buildResultHtml", () => {
  it("包含正确答案与用户答案，错误标点有 wrong-char class", () => {
    const correctText = "春天来了，花开了。";
    const blanks = [{ pos: 4, char: "，" }, { pos: 10, char: "。" }];
    const userAnswers = ["，", "x"];
    const details = [{ ok: true }, { ok: false }];
    const html = buildResultHtml(correctText, blanks, userAnswers, details);
    assert(html.includes("春天来了，花开了。"));
    assert(html.includes("wrong-char"));
    assert(html.includes("result-card"));
  });
});

// ----- formatStats -----
describe("formatStats", () => {
  it("总题数、剩余、已答格式正确", () => {
    const s = formatStats(10, 0);
    assert(s.includes("总题数：10"));
    assert(s.includes("剩余：10"));
    assert(s.includes("已答：0"));

    const s2 = formatStats(5, 2);
    assert(s2.includes("总题数：5"));
    assert(s2.includes("剩余：3"));
    assert(s2.includes("已答：2"));
  });

  it("已答超过总题时剩余为 0", () => {
    const s = formatStats(5, 10);
    assert(s.includes("剩余：0"));
    assert(s.includes("已答：10"));
  });
});
