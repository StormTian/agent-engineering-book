# Agent 工程拆解

一本中文 Agent 源码教程：从执行循环、上下文、工具、编排、记忆、恢复与权限，走进十二个固定版本的真实项目。

[在线阅读](https://stormtian.github.io/agent-engineering-book/) · [整本 Markdown](BOOK.md) · [构建与部署](#本地阅读与部署)

包含十章工程主线、十二个源码案例、179个概念与199个精确概念锚点，另保留原八项目52章交互课程。主线和案例均有阅读目标、必要前提、阅读步骤、闭卷问题与判断标准；源码和答案可以分别展开。

案例：mini-SWE-agent、Pi、LangGraph、Eino、OpenHands Agent SDK、DeerFlow、Inspect AI、Codex、OpenAI Agents SDK、smolagents、Letta Code、browser-use。

## 本地阅读与部署

Python 3.10+，构建不需要安装第三方 Python 包。

```bash
git clone git@github.com:StormTian/agent-engineering-book.git
cd agent-engineering-book
python3 tools/build.py
python3 tools/validate_publication.py --output verification/publication-audit.json
python3 -m http.server 8000 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8000/dist/`。Markdown 与离线 ZIP 从站点的来源页下载。四个独立教学实验可运行 `python3 tools/labs.py --output verification/labs.json`。

GitHub Pages 使用 `.github/workflows/pages.yml`：每次推送 main 或手动触发时，重新构建、检查页面与下载，再部署 dist。仓库首次需要在 Settings → Pages → Build and deployment 将 Source 设置为 GitHub Actions。Git 通过本机 SSH 身份连接；部署工作流不需要个人 SSH key 或额外密钥。

## 文件职责

- `content/cases.json`：固定案例、解释、引用、练习与原证据范围。
- `content/reading-guides.json`：十章、十二案例的阅读任务和判断标准。
- `tools/book_content.py`：工程主线与后续候选。
- `content/courses/`：保留的原交互课程。
- `tools/build.py`：生成站点、Markdown、来源清单与离线包。
- `tools/validate_publication.py`：发布来源哈希、子路径链接、页面与下载核验。
- `publication.json`：本次导出的来源版本、文件哈希、统计与官方 workflow 版本。

## 来源与证据

引用保留完整提交、路径、行号与文件哈希。DeerFlow 使用本地 fork 加工作区快照，远端基础提交可能没有全部本地改动。源码观察、教学实验与真实项目运行分别标明，静态引用不能证明生产 Runtime 行为。

新增四项目未执行真实模型、Cloud、鉴权或生产环境。四个教学实验是独立模型；Eino 的原六个真实框架案例使用脚本模型，其他原项目沿用各自已有证据范围。本次部署不升级这些证据。

参考 [bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book) 以工程问题组织章节的思路。教程与练习独立编写，原短源码引用和上游许可见 `content/licenses/`，旧课程附加许可见 `content/course-licenses/`。本仓库没有替上游作品重新授权。
