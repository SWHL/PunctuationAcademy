# 标点学堂 · Punctuation Academy

中文标点符号练习应用：从内置规范文章或自定义 TXT/粘贴范文中随机选句，挖空标点后由用户在空位处填写，提交后给出答案对比与错误高亮。

## 功能

- **题目来源**：内置若干规范段落；或上传 TXT、粘贴范文（支持从人民日报等复制）。
- **题库规则**：若已上传/粘贴过题目，则**仅使用用户题库**；否则使用系统自带题目。
- **解析方式**：支持「显式标注 `【标点】`」或「纯段落按句号分句、自动挖空」。
- **练习方式**：题目整句以 `___` 表示空位，下方一排输入框按从左到右顺序填入标点（每格一个）。
- **结果展示**：显示完整正确答案、您的答案，错误标点标黄。

## 运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（默认 http://127.0.0.1:7860）
python app.py
```

使用指定 Python 环境（如 conda）：

```bash
conda activate py310
pip install -r requirements.txt
python app.py
```

或直接指定解释器：

```bash
/path/to/python -m pip install -r requirements.txt
/path/to/python app.py
```

## 项目结构

```
PunctuationAcademy/
├── app.py              # Gradio 界面入口
├── utils.py            # 题目加载、TXT 解析、填空与对比逻辑
├── data/
│   └── articles.json   # 内置规范文章与挖空题目
├── tests/
│   ├── test_app.py     # 界面逻辑单元测试
│   └── test_utils.py    # 核心逻辑单元测试
└── requirements.txt
```

## 测试

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## 技术栈

- **Python 3**
- **Gradio**：Web 界面
- 可选部署：Hugging Face Spaces、自有服务器等
