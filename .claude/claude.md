# Claude Code 项目规范

> 本文件仅为 Claude Code 兼容入口。**完整规则以根目录 `AGENTS.md` 为准。**

---

## 执行顺序

1. 先读取 `AGENTS.md` 的"最高优先级执行协议"与"长规范调用门禁"。
2. 按任务类型读取 `AGENTS.md` 指定的长规范（`docs/ai-rules/`）。
3. 未读取对应长规范前，不得生成报告、提取财报数据、更新网页索引或修改模拟组合数据。

## 项目速览

- 类型：港股/A股个股投资分析模板系统
- 版本以 `AGENTS.md` 为准（本文件不单独声明版本号）
- 语言：简体中文
- LLM 提供商：DeepSeek (deepseek-chat)，API Key 已配置

## 投资报告任务

生成/更新投资分析报告时，必须先读取：

- `docs/ai-rules/01-报告生成SOP.md`（含 6 关筛选 + 七大缺口 + 阶段门禁）
- `docs/ai-rules/02-数据溯源门禁.md`
- `readPDF.md`

进入报告写作前必须运行并贴出返回码：

```bash
python scripts/check_report_ready.py {股票代码}
```

溯源表不存在 / 核心数据缺页码 / 未解决🔴≠0 → 禁止写报告。

## Claude Code 专用：写入验证

修改关键文件后，必须立即用 grep 搜索本次新增的特征关键词，确认写入成功，并把结果展示给用户。

> 为什么：Edit/Write 返回 success 不代表磁盘写入成功（IDE缓存/编码/零散编辑累积偏差）。只有 grep 到新内容才算数。陕西煤业会话中文件曾被还原到旧版本。

```
grep -c "本次新增的特征文字" 文件路径
```

结果 >0 = 写入成功；=0 = 写入失败，立即排查。

## 禁止

除非用户明确要求，不得执行 `git commit` 或 `git push`。

---

*Claude Code 兼容层，更新于 2026-06-03。完整规范见 `AGENTS.md` 与 `docs/ai-rules/`。*
