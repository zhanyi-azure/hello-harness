# -*- coding: utf-8 -*-
"""
04_stream_sdk.py —— SDK 版流式：两行参数开启打字机效果
对比 03_stream_raw.py：裸版要自己解析 SSE（剥前缀、认暗号、拼 JSON），
SDK 把这些全封装了 —— for 循环直接给你解析好的 chunk 对象。

本脚本额外演示一个知识点：
流式模式下 usage（token 用量）默认【不返回】，
必须加参数 stream_options={"include_usage": True}，
服务器才会在一个额外的小 chunk 里把 usage 带给你。
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("错误：没找到 DEEPSEEK_API_KEY，请检查 .env")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

print("正在请求 DeepSeek API（流式）...")
stream = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": "用一句话解释什么是流式输出"},
    ],
    stream=True,                               # 开启流式
    stream_options={"include_usage": True},    # ★ 让流里附带 usage
)

# stream 是一个迭代器：for 每转一圈，拿到一小块 chunk
print("\n回答：", end="")
usage = None   # 用来接住最后那个带用量的 chunk
for chunk in stream:
    # 两个"防御"缺一不可：
    # 1) 带 usage 的收尾 chunk，choices 是【空列表】——不判空会 IndexError
    # 2) 有些 chunk 只带角色信息，delta.content 是 None——不判 None 会打出 "None"
    if chunk.choices and chunk.choices[0].delta.content:
        # end="" 的作用：把 print 自带的换行符换成空串，小块才能拼成整段话
        # flush=True 的作用：Python 默认把输出攒在缓冲区、攒够才显示；
        #                   flush 强制立刻刷屏。不加它，"打字机"会变成
        #                   "憋半天、一次性蹦出一大坨"
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:          # usage 只在流的最末尾出现一次
        usage = chunk.usage

print("\n\n用量（来自流的最后一个 chunk，普通流式默认拿不到）:")
print(usage)
