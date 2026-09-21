# -*- coding: utf-8 -*-
"""
02_sdk.py —— SDK 版：用 openai 库调用 DeepSeek
原理：DeepSeek 的接口格式与 OpenAI 完全兼容，所以能直接用 openai 库，
     只需把 base_url 换成 DeepSeek 的地址。
对比 01_raw_http.py：不用手拼 url/headers/请求体，也不用手工解析 JSON，
     SDK 全部封装好了，返回值是对象属性，用"点"取值即可。
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI   # 库名叫 openai，但能连任何"OpenAI 兼容"的服务

# ---- 第 1 步：读 key（与脚本一相同）----
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("错误：没找到 DEEPSEEK_API_KEY。请先把 .env.example 复制为 .env 并填入真实 key。")
    sys.exit(1)

# ---- 第 2 步：构造客户端 ----
# api_key  —— 身份凭证（SDK 会自动帮你加到请求头里，不用手写 Authorization）
# base_url —— openai 库默认指向 OpenAI 官方地址，这里换成 DeepSeek 的地址，
#            一行代码完成"换供应商"，这就是接口兼容的好处
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ---- 第 3 步：发起对话请求 ----
# model 和 messages 与 01_raw_http.py 完全相同，方便对照两版的异同
# 背后发生的事：SDK 把这些参数组装成 JSON，POST 到 base_url + /chat/completions
print("正在请求 DeepSeek API ...")
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": "用一句话解释什么是 API"},
    ],
)

# ---- 第 4 步：打印结果 ----
# SDK 已把 JSON 解析成对象：用 resp.xxx 点出来，不用 resp["xxx"]["xxx"] 一层层取
print("\n回答：", resp.choices[0].message.content)
print("模型：", resp.model)   # 与脚本一对照：模型字段一致
print("用量：", resp.usage)   # token 消耗情况
