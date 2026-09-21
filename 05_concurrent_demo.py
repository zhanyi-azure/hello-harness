# -*- coding: utf-8 -*-
"""
05_concurrent_demo.py —— asyncio 并发演示：同时等 3 个快递 vs 等完一个再等下一个

先记住两个词：
- 协程（coroutine）：用 async def 定义的"可暂停函数"。执行到 await 就暂停，
  把控制权还给事件循环；事件循环趁机去推进别的协程。等待的时间被"叠"在一起了。
- asyncio.gather(协程A, 协程B, ...)：把多个协程同时跑起来，
  全部完成后按【传入顺序】（不是完成顺序！）把结果打包成一个列表返回。

本脚本用同样的 3 个问题各跑两遍：
  串行：发 1 个 -> 干等 -> 收到 -> 再发下一个     总耗时 = t1 + t2 + t3
  并发：3 个同时发出 -> 一起等 -> 全部收到        总耗时 ≈ max(t1, t2, t3)
为什么并发版 ≈ 最慢一次、而不是 1/3？
  因为单个请求该多久还是多久，asyncio 没有让网络变快，
  它只是让三段"干等网络"的时间重叠起来 —— 省掉的是排队，不是速度。
  前提：任务是 I/O 密集（等网络/磁盘）。若是 CPU 密集（纯计算），
  asyncio 帮不上忙：事件循环只有一个线程，该算多久还是多久。
"""

import os
import sys
import time
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI   # 注意：异步版客户端，类名带 Async 前缀

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("错误：没找到 DEEPSEEK_API_KEY，请检查 .env")
    sys.exit(1)

QUESTIONS = [
    "用一句话解释什么是 HTTP",
    "用一句话解释什么是 API",
    "用一句话解释什么是流式输出",
]

# ---- 定义协程 ----
# async def 的函数是"协程函数"：直接调用它并不会执行，
# 只会得到一个协程对象，要交给事件循环（asyncio.run / gather）才真正跑
async def ask(question: str) -> str:
    # async with：异步上下文管理器，代码块结束时自动关闭底层连接
    # 每次新建客户端：每次 asyncio.run 都是全新的事件循环，
    # 跨循环复用客户端连接会踩"Event loop is closed"的坑，新手期直接避开
    async with AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com") as client:
        resp = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个简洁的助手。"},
                {"role": "user", "content": question},
            ],
        )
        return resp.choices[0].message.content

# 并发版：gather 同时启动所有协程，await 等全部完成
async def ask_all(questions) -> list:
    return await asyncio.gather(*(ask(q) for q in questions))

# ---- 方式一：串行 ----
print("=" * 55)
print("方式一：串行（问完一个，再问下一个）")
print("=" * 55)
start = time.perf_counter()      # perf_counter：精度最高的计时器，适合测耗时
for q in QUESTIONS:
    # asyncio.run(协程)：启动事件循环，把这一个协程跑完并拿到返回值
    ans = asyncio.run(ask(q))
    print("问:", q)
    print("答:", ans, "\n")
seq_seconds = time.perf_counter() - start
print(f">>> 串行总耗时: {seq_seconds:.2f} 秒\n")

# ---- 方式二：并发 ----
print("=" * 55)
print("方式二：并发（3 个问题同时发出去）")
print("=" * 55)
start = time.perf_counter()
answers = asyncio.run(ask_all(QUESTIONS))
conc_seconds = time.perf_counter() - start
for q, a in zip(QUESTIONS, answers):
    print("问:", q)
    print("答:", a, "\n")
print(f">>> 并发总耗时: {conc_seconds:.2f} 秒\n")

# ---- 对比结论 ----
print("=" * 55)
print(f"对比：串行 {seq_seconds:.2f}s  vs  并发 {conc_seconds:.2f}s")
print("并发版 ≈ 最慢那一次的耗时，而不是串行的 1/3 ——")
print("三个'等网络'的时间重叠了，省掉的是排队，不是单个请求的速度。")
print("=" * 55)
