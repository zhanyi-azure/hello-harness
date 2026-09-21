# -*- coding: utf-8 -*-
"""
01_raw_http.py —— 裸 HTTP 版：不用任何 SDK，直接用 requests 手工发 HTTP 请求
作用：让你看清"调用大模型 API"的本质 —— 其实就是发一个 HTTP POST 请求
"""

# ---- 第 1 步：导入需要的库 ----
import os      # 读环境变量（.env 的内容会被加载进环境变量）
import sys     # 出错时以非 0 状态码退出程序（0 表示成功，1 表示失败）
import requests                  # 发 HTTP 请求的库
from dotenv import load_dotenv   # 从 .env 文件读配置的小工具

# ---- 第 2 步：加载 .env，拿到 API key ----
# load_dotenv() 把项目根目录 .env 文件里的每一行"名字=值"写进环境变量
# 好处：key 不写死在代码里（不硬编码），代码可以放心传到 git
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    # 防呆检查：如果 .env 没建或没填 key，给人话提示后退出
    print("错误：没找到 DEEPSEEK_API_KEY。请先把 .env.example 复制为 .env 并填入真实 key。")
    sys.exit(1)

# ---- 第 3 步：组装请求 ----
url = "https://api.deepseek.com/chat/completions"

# headers 里声明两件事：
# 1) Authorization：证明"我是谁"（固定写法 Bearer + 空格 + 你的 key）
# 2) Content-Type：告诉服务器"我发的请求体是 JSON 格式"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

# 请求体：一个普通 Python 字典，发出去时会被转成 JSON 字符串
# - model：用哪个模型
# - messages：对话历史，列表里每条消息有 role（角色）和 content（内容）
#   * system：给 AI 的"人设/规则"，一般放最前面
#   * user：用户说的话
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": "用一句话解释什么是 API"},
    ],
}

# ---- 第 4 步：发请求 ----
# json=payload 会自动把字典转成 JSON 文本再发送
# timeout=60：最多等 60 秒，防止网络卡住时程序永远挂起
print("正在请求 DeepSeek API ...")
resp = requests.post(url, headers=headers, json=payload, timeout=60)

# ---- 第 5 步：检查结果 ----
# 先看状态码：200 成功；4xx 是我们这边的错（key 无效、参数错等）；5xx 是服务器出错
print("HTTP 状态码:", resp.status_code)

if resp.status_code != 200:
    # 失败：把服务器返回的错误原文打出来，方便排查（key 错了会在这里看到 401）
    print("请求失败，响应内容：")
    print(resp.text)
    sys.exit(1)

# ---- 第 6 步：解析成功响应 ----
data = resp.json()  # 把响应的 JSON 文本解析成 Python 字典

# 响应的结构（由 DeepSeek 的 API 文档规定）大致长这样：
# {
#   "choices": [ {"message": {"role": "assistant", "content": "……回答……"}, ...} ],
#   "model": "deepseek-chat",
#   "usage": {"prompt_tokens": …, "completion_tokens": …, "total_tokens": …},
#   ...
# }
print("\n回答：", data["choices"][0]["message"]["content"])
print("模型：", data["model"])
print("用量：", data["usage"])
