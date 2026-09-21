# -*- coding: utf-8 -*-
"""
call_llm.py —— 命令行 AI 问答工具 v0.1

把之前学过的零件（dotenv 读 key / OpenAI 兼容客户端 / 流式打字机 /
异常处理 / 退出码）组装成一个正式的命令行工具。

用法示例：
    python call_llm.py "用一句话解释什么是 API"           # 默认流式打字机效果
    python call_llm.py "解释递归" --system "你是高中编程老师"  # 换人设
    python call_llm.py "写首诗" --no-stream               # 关闭流式，一次性输出
约定：进程退出码 —— 成功 0，失败 1（方便其他脚本判断本次调用是否成功）
"""

import argparse   # Python 标准库：解析命令行参数，自动生成 --help
import os         # 读环境变量
import sys        # 控制退出码、把错误打到 stderr

from dotenv import load_dotenv
# 把 SDK 的异常类也 import 进来：按类型捕获，才能给出"人话"提示
from openai import (OpenAI, AuthenticationError, RateLimitError,
                    APITimeoutError, APIConnectionError, APIStatusError)


def parse_args():
    """定义并解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="命令行 AI 问答工具：向 DeepSeek 提问，默认流式打字机效果输出")
    # 位置参数：不加横杠，按位置对号入座；含空格时用引号包住整个问题
    parser.add_argument("question", help="你要问的问题（含空格请用引号包住）")
    # 可选参数：--system 换人设，--model 换模型，--no-stream 关流式
    parser.add_argument("--system", default="你是一个简洁的助手。",
                        help="系统提示词/人设（默认：你是一个简洁的助手。）")
    parser.add_argument("--model", default="deepseek-chat",
                        help="模型名（默认：deepseek-chat）")
    # store_true：这是个"开关"参数，写了就是 True。默认不写 → 流式开启
    parser.add_argument("--no-stream", action="store_true",
                        help="关闭流式，等全部生成完一次性输出")
    return parser.parse_args()


def main():
    args = parse_args()

    # ---- 读 key：只从环境变量/.env 来，代码里绝不出现真 key ----
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[错误] 没找到 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填入真实 key。",
              file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = [
        {"role": "system", "content": args.system},
        {"role": "user", "content": args.question},
    ]

    usage = None   # 用来接住 token 用量（流式来自收尾 chunk，非流式来自 resp.usage）
    try:
        if args.no_stream:
            # ---- 非流式：等全部生成完，一次性返回 ----
            resp = client.chat.completions.create(model=args.model, messages=messages)
            print(resp.choices[0].message.content)
            usage = resp.usage
        else:
            # ---- 流式：一块块到、一块块打（flush 立即刷屏，才有打字机效果）----
            # stream_options 让服务器在流末尾附带 usage（默认不带）
            stream = client.chat.completions.create(
                model=args.model, messages=messages,
                stream=True, stream_options={"include_usage": True})
            for chunk in stream:
                # 收尾的 usage chunk 的 choices 是空列表，先判空再取内容
                if chunk.choices and chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                if chunk.usage:
                    usage = chunk.usage
            print()   # 流结束，补一个换行，别让提示符黏在回答末尾

        if usage:
            print(f"\n[token 用量] 输入 {usage.prompt_tokens} + "
                  f"输出 {usage.completion_tokens} = 共 {usage.total_tokens}")
        sys.exit(0)   # 全程无异常 → 成功，退出码 0

    # ---- 按异常类型给"人话"提示（子类异常要写在父类前面）----
    except AuthenticationError:
        print("\n[错误 401] 认证失败：API key 无效或已过期。"
              "请检查 .env 里的 DEEPSEEK_API_KEY 是否填对。", file=sys.stderr)
        sys.exit(1)
    except RateLimitError:
        print("\n[错误 429] 请求过频或额度不足：休息一下再试，"
              "或去 DeepSeek 平台确认账户余额。", file=sys.stderr)
        sys.exit(1)
    except APITimeoutError:
        print("\n[错误 超时] 服务器迟迟没有响应：检查网络后重试。", file=sys.stderr)
        sys.exit(1)
    except APIConnectionError:
        print("\n[错误 网络] 连不上 DeepSeek 服务器：检查网络/代理设置。", file=sys.stderr)
        sys.exit(1)
    except APIStatusError as e:
        # 其余带状态码的 HTTP 错误（4xx/5xx）：把码和原文附上，方便排查
        print(f"\n[错误 {e.status_code}] 服务器返回异常，原文：{e.message}",
              file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # 兜底：没料到的异常也打出来，程序不能一声不吭地崩
        print(f"\n[错误 未知] 发生了意外异常：{type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
