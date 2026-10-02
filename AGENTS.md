# 教材协作规则

先读 README.md，保持源码版本、摘录、行号与证据状态可追溯。普通文字和阅读器修改不要重新导入案例或用最新上游提交替换冻结来源。

正文从 content/cases.json、content/reading-guides.json、tools/book_content.py 修改。dist 与 BOOK.md 由 tools/build.py 生成，不作为独立手改稿维护。

本仓库是完整教材的可构建发布快照；publication.json 记录本次来源哈希。本机主稿更新后，由发布工具重新导出；若 GitHub 有独立修改，先正常拉取并审阅合并，不强推，不静默覆盖。

运行 `python3 tools/build.py`、`node --check dist/assets/book.js` 与 `python3 tools/validate_publication.py`。修改正文源后同步更新来源清单或从主稿重新导出；未经处理的来源哈希变化应让核验失败。

发布核验检查相对链接、页面与离线文件，不读取本机上游检出，也不冒充上游源码重新运行。新增真实实验需单独记录版本、环境、日志、失败与范围。

不保存凭据、Cookie、SSH 私钥或个人账户材料。原始引用和许可证保留；不把浏览记录、答案点击或教学模型通过写成学习者掌握或生产 Runtime 通过。
