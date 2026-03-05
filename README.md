# 标点学堂 · Punctuation Academy

中文标点符号练习应用：从内置规范文章或自定义 TXT / 粘贴范文中选题，在空位处填入标点，提交后给出答案对比与错误高亮。

## 功能

- **题目来源**：内置规范段落；或上传 TXT、粘贴范文（支持从人民日报等复制）。粘贴后点击「解析并加入题库」会清空输入框。
- **题库规则**：若已上传 / 粘贴过题目，则**仅使用用户题库**；否则使用系统自带题目。题目做完后提示「现有题目均已做完」，可点击「再来一轮」重新练习。
- **解析方式**：
    - 显式标注：`【标点】` 表示挖空。
    - 纯段落：按句号分句，**用户上传时该句内所有标点全部挖空**，保证一题一句。
- **练习方式**：题干与空位同一行展示，按从左到右顺序填入标点（每格一个）。按 **Enter** 或 **空格** 提交。
- **结果展示**：显示完整正确答案与您的答案，错误标点标黄。

## 运行

纯前端，需通过 HTTP 访问（以便加载 `data/articles.json`）。

```bash
cd web
python -m http.server 8080
```

浏览器打开 <http://localhost:8080。>

**部署 GitHub Pages**：将 `web/` 目录内容发布为静态站点即可。无构建步骤，无额外依赖。

## 项目结构

```text
PunctuationAcademy/
├── README.md
├── web/
│   ├── index.html
│   ├── style.css
│   ├── app.js          # 界面与事件
│   ├── logic.js        # 纯逻辑（解析、对比、结果 HTML）
│   ├── data/
│   │   └── articles.json
│   └── tests/
│       └── logic.test.js
```

## 测试

```bash
node --test web/tests/logic.test.js
```

## 技术栈

HTML、CSS、JavaScript，静态资源，可部署至 GitHub Pages 等静态托管。
