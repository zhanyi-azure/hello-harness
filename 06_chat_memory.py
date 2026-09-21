# -*- coding: utf-8 -*-
"""
06_chat_memory.py —— 多轮对话命令行程序：亲眼看见 AI 的"记忆"是怎么来的

本课灵魂（先记住这句话）：
    API 是【无状态】的！服务器不保存你上一次请求的任何内容。
    所谓"多轮对话记忆"，是客户端每轮把【全部历史消息】重新发一遍，
    AI 的"记性"，其实是我们一句一句喂给它的。
"""

import os
import sys
from dotenv import load_dotenv
from openai import (OpenAI, AuthenticationError, RateLimitError,
                    APITimeoutError, APIConnectionError, APIStatusError)


def main():
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：没找到 DEEPSEEK_API_KEY，请检查 .env")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # messages 就是 AI 每轮能看到的"完整剧本"。
    # 开场先放一条 system 消息定人设；之后每一句对话都会追加进来。
    messages = [
        {"role": "system", "content": "你是一个简洁的助手。"}
    ]
    print("多轮对话开始（输入 q 或直接回车退出）")
    print(f"初始 messages 长度: {len(messages)}\n")

    while True:
        # ---- 读取用户输入；空内容或 q 退出 ----
        try:
            user_input = input("你: ").strip()
        except EOFError:
            # 输入流结束（比如 Ctrl+Z / 管道喂完了）也当作退出
            print("\n再见！")
            break
        if not user_input or user_input.lower() == "q":
            print("再见！")
            break

        # ---- 第 1 步：把用户这句话追加进剧本 ----
        messages.append({"role": "user", "content": user_input})

        # ---- 第 2 步：非流式调用 API ----
        # ★ 注意：发的是 messages 这个【完整列表】，不是只有这一句话！
        # 为什么每轮要重发全部历史？因为服务器是"金鱼"——上次请求结束
        # 就全忘了，想让它"记得"，就只能把到目前为止的所有对话再发一次。
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
            )
        except AuthenticationError:
            print("\n[错误 401] API key 无效，请检查 .env")
            break
        except RateLimitError:
            print("\n[错误 429] 请求过频或额度不足，稍后再试")
            break
        except APITimeoutError:
            print("\n[错误 超时] 服务器响应超时，请重试")
            continue   # 超时是临时故障，不退出对话，允许重试
        except APIConnectionError:
            print("\n[错误 网络] 连不上服务器，请检查网络")
            continue
        except APIStatusError as e:
            print(f"\n[错误 {e.status_code}] {e.message}")
            break
        except Exception as e:
            print(f"\n[错误 未知] {type(e).__name__}: {e}")
            break

        answer = resp.choices[0].message.content
        print(f"AI: {answer}")

        # ---- 第 3 步：★★ 灵魂行：把 AI 的回答也回填进剧本 ★★ ----
        # 为什么要回填 assistant 消息？因为 API 无状态，AI 只能"看见"
        # messages 列表里的东西。如果不把它的回答记进去，下一轮重发
        # 历史时剧本里就缺了这一段——AI 对自己说过的话一无所知。
        # （它没有别的任何渠道"想起"自己说过什么！）
        # ★★★ 失忆实验：注释掉下面这一行，AI 就会忘掉自己说过的话 ★★★
        messages.append({"role": "assistant", "content": answer})

        # ---- 第 4 步：每轮报告 ----
        # messages 长度：每轮 +2（一条 user + 一条 assistant）
        # prompt_tokens：本轮作为"输入"发给服务器的 token 数。
        # 为什么逐轮变大？因为每轮都要把之前全部历史重发一遍——
        # 剧本越来越长，"入场费"自然一轮比一轮高（这就是长对话的成本曲线）。
        print(f"[messages 长度: {len(messages)}] "
              f"[本轮 prompt_tokens: {resp.usage.prompt_tokens}]\n")


if __name__ == "__main__":
    main()
