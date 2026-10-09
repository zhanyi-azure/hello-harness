# mini_harness —— 手工复刻 agent 器官的练功包

不用任何 agent 框架，从裸 HTTP 开始，把 Claude Code 这类工具的核心"器官"逐个手搓出来：工具调用、权限闸门、上下文压缩、调用日志，全部自己写。当前版本：**v0.2**（里程碑②：包化重组）。

## 特性

- **agent loop**：`while` 大循环 + `for` 逐张处理并行工单 + 轮数安全阀
- **3 个工具**：`read_file` / `list_dir`（只读，自动放行）、`write_file`（有副作用）
- **权限闸门**：危险工具执行前人工 y/n 确认；拒绝以回执形式喂回模型（拒绝也是数据，fail-closed）
- **上下文压缩**：消息超 `CONTEXT_LIMIT` 自动把旧历史压成摘要（system + 摘要 + 最近 4 条）
- **调用日志**：每轮打印"模型调用 / 回执前 80 字符"，错误自愈全程可见
- **MCP 实验位**：`mcp_demo.py` + `test_mcp_client.py`——同一套工具的 MCP 标准化包装

## 架构

```text
python -m mini_harness "你的问题"
        │
        ▼
┌──────────────────────────────┐
│ cli.py                       │  argparse：question、--max-rounds
└──────────────┬───────────────┘
               ▼  core.run(question, max_rounds)
┌──────────────────────────────┐
│ core.py   while 大循环       │
│   ├─ 超限？compress_history()│──► 额外一次 API 调用生成摘要
│   ├─ 发请求（带工具说明书）  │
│   └─ for 逐张处理工单 ───────┼──► execute_tool(call)
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ tools.py                     │
│  解析参数 → .get() 查注册表  │
│  → 危险名单？人工 y/n 闸门   │
│  → 执行 read_file/list_dir/  │
│     write_file，永远返回字符串│
└──────────────┬───────────────┘
               ▼
       DeepSeek API（OpenAI 兼容）
```

## 安装

```bash
git clone https://github.com/zhanyi-azure/hello-harness.git
cd hello-harness
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env    # 然后填入你的 DeepSeek API key

# 可选：设置 agent 的工作区根——所有相对路径都锚定到这里（不设则默认为启动目录）
$env:MINI_HARNESS_ROOT = "D:\likeme"
```

## 使用

```bash
# 单轮直答
python -m mini_harness "1+1等于几"

# 多轮工具调用（模型会自己 list_dir → read_file）
python -m mini_harness "lessons 目录下有哪些文件？读一下带 agent-loop 的课件开头"

# 有副作用的操作会弹人工确认（y 放行 / n 拒绝）
python -m mini_harness "在 lessons 创建 m2.txt 内容为 milestone2"

# 调整轮数安全阀
python -m mini_harness "复杂任务" --max-rounds 15
```

> 提示：涉及 `lessons` 目录的问题请在 `D:\likeme` 下运行（lessons 与包目录平级），此时需
> `$env:PYTHONPATH = "D:\likeme\hello-harness"` 让包可被导入。

## 路线图

- **v0.2**：MCP 接入与子代理
- **v0.3**：Docker 与 eval
