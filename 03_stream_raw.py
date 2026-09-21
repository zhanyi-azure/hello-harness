# -*- coding: utf-8 -*-
"""
03_stream_raw.py —— 裸版流式：用 requests 手工解析 SSE 流
目的：看穿"打字机效果"的魔法 —— 它不是什么高级技术，
     就是服务器把整段回答切成很多小块（chunk），一块一块推过来。

SSE（Server-Sent Events，服务器推送事件）是什么：
     普通 HTTP 响应是"攒完一次给你"；SSE 是连接不断开，
     服务器持续往响应体里一行行写文本，格式约定：
       data: {"...": "..."}    <- 每条消息以 "data: " 开头
       （空行）                 <- 空行是消息之间的分隔符
       data: [DONE]            <- 固定结束暗号（OpenAI 系的约定）
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# ---- 第 1 步：读 key（和 01 完全相同）----
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("错误：没找到 DEEPSEEK_API_KEY，请检查 .env")
    sys.exit(1)

# ---- 第 2 步：组装请求（同 01，只多一个 stream 开关）----
url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": "用一句话解释什么是流式输出"},
    ],
    "stream": True,   # ★ 唯一的新增：告诉服务器"别攒完，一块块推给我"
}

# ---- 第 3 步：发请求 ----
# stream=True 是 requests 侧的开关：收到响应头就返回，
# 响应体不再自动下载完，留给 iter_lines() 一段一段地读
print("正在请求 DeepSeek API（流式）...")
resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
print("HTTP 状态码:", resp.status_code)
if resp.status_code != 200:
    print("请求失败，响应内容：")
    print(resp.text)
    sys.exit(1)

# 从响应头能验证这确实是个 SSE 流
print("响应类型:", resp.headers.get("Content-Type"))

# ---- 第 4 步：一行一行读流 ----
# iter_lines() 按换行符切分响应体，每次给一行（bytes 类型，要自己解码）
print("\n回答：", end="")
for raw_line in resp.iter_lines():
    line = raw_line.decode("utf-8")          # bytes -> str

    if not line:                             # 空行 = 事件分隔符，跳过
        continue
    if not line.startswith("data: "):        # 只处理数据行（顺便挡掉注释行等杂音）
        continue

    data_str = line[len("data: "):]          # 剥掉前缀，剩下的才是 JSON

    if data_str == "[DONE]":                 # 固定暗号：流结束
        break

    chunk = json.loads(data_str)             # 每一小块自身也是完整 JSON
    delta = chunk["choices"][0].get("delta", {})
    content = delta.get("content")           # 增量内容 = 这一小块"新增"的字
    if content:                              # 第一个 chunk 往往只带角色、不带内容
        # end=""：print 默认输出完自动加换行，换成空串让小块接在同一行
        # flush=True：强制立刻显示到屏幕，不然缓冲区攒着，没有流的效果
        print(content, end="", flush=True)

resp.close()   # 用完主动关连接（流式连接不关会一直挂着）
print("\n\n[流结束] 上面这些字是一块一块到达的，不是一次到达的")
