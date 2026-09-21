# call_llm —— 命令行 AI 问答工具

在终端里直接向 DeepSeek 提问，默认流式"打字机"效果输出，结束后报告本轮 token 用量。

**当前版本：v0.1**

## 安装

```bash
git clone https://github.com/zhanyi-azure/hello-harness.git
cd hello-harness
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell（macOS/Linux: source .venv/bin/activate）
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux 用 cp
```

## 配置 API Key

1. 到 [DeepSeek 开放平台](https://platform.deepseek.com) 注册并创建 API Key；
2. 编辑 `.env`，把 key 填到 `DEEPSEEK_API_KEY=` 后面；
3. `.env` 已被 `.gitignore` 排除，不会进 git。**key 不要发给任何人。**

## 用法

```bash
# 基础提问（默认流式打字机效果）
python call_llm.py "用一句话解释什么是 Git"

# 换人设：--system 指定系统提示词
python call_llm.py "什么是递归" --system "你是面向高中生的编程老师，爱用生活比喻"

# 关闭流式 + 换模型：--no-stream 等全部生成完一次性输出
python call_llm.py "天空什么颜色" --no-stream --model deepseek-chat

# 查看全部参数
python call_llm.py --help
```

示例输出片段：

```text
$ python call_llm.py "用一句话解释什么是 Git"
Git 是一个分布式版本控制系统，用来跟踪代码或文件的历史修改，方便多人协作和版本管理。

[token 用量] 输入 16 + 输出 22 = 共 38

$ python call_llm.py "你好"        # key 填错时会看到：
[错误 401] 认证失败：API key 无效或已过期。请检查 .env 里的 DEEPSEEK_API_KEY 是否填对。
```

## 退出码

成功 `0`；失败 `1`（401 key 无效 / 429 请求过频 / 超时 / 网络不通 / 其他，均有中文提示，错误详情输出到 stderr）。
