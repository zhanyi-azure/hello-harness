# mini_harness/core.py —— agent loop 主循环（while + 上下文压缩 + 调用日志）
import os

from dotenv import load_dotenv
from openai import OpenAI

from .tools import TOOLS_SCHEMA, execute_tool

CONTEXT_LIMIT = 8   # messages（含 system）总条数上限，超过就触发历史压缩

# 压缩摘要话术：必须点明"保留用户硬性要求"——
# 用户的原始要求是整个任务的验收标准，摘要丢了约束，模型就会偏离目标。
SUMMARY_PROMPT = ("请把以下对话历史压缩成一段『此前进展摘要』，必须保留："
                  "用户的全部硬性要求、已完成的步骤、重要发现。摘要：")


def compress_history(messages, client):
    """每轮发请求前调用。消息总数超过 CONTEXT_LIMIT 时，
    把中间的旧消息压缩成一段摘要，只留【system + 摘要 + 最近几条】。
    代价：多发起一次 API 调用（请模型亲自写摘要——它最懂哪些内容重要）。"""

    if len(messages) <= CONTEXT_LIMIT:
        return messages   # 没超限，原样返回（零成本）

    old_count = len(messages)
    # 为什么 system 永远保留？Day 8 的教训：API 无状态，剧本每轮全量重发。
    # system 一旦被压缩掉，人设和规则就从剧本里消失——模型立刻"人格漂移"。
    system = messages[0]

    # 为什么保留最近 4 条？它们是【正在进行的上下文】：
    # 模型决定"下一步干什么"靠的是刚发生的事。老消息可以模糊（进摘要），
    # 最近的必须保真（原文保留）。
    start = old_count - 4

    # 边界修复（Day 9 的 400 教训）：如果"最近几条"的第一条是 tool 回执，
    # 说明它配对的工单消息（assistant）落在被压缩区——回执不能没有母亲，
    # 否则压缩完的剧本结构断裂，下次请求直接 400。往前扩到配对消息为止。
    while start > 1 and isinstance(messages[start], dict) \
            and messages[start].get("role") == "tool":
        start -= 1

    middle = messages[1:start]     # 被压缩区
    recent = messages[start:]      # 保真区

    if not middle:
        return messages   # 边界修复吃掉了全部中间段——没得压，原样返回

    # 把中间旧消息序列化成纯文字。注意：assistant 工单消息是 SDK 对象不是 dict，
    # 用 hasattr 区分（它肚子里可能有多张工单，逐张点名）
    lines = []
    for m in middle:
        if hasattr(m, "tool_calls"):
            calls = ", ".join(
                f"{c.function.name}({c.function.arguments})" for c in (m.tool_calls or []))
            lines.append(f"[assistant 发起工具调用] {calls}")
        else:
            lines.append(f"[{m.get('role', '?')}] {m.get('content', '')}")
    history_text = "\n".join(lines)

    # 额外的一次 API 调用：请模型亲自写摘要
    summary_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个简洁的助手。"},
            {"role": "user", "content": SUMMARY_PROMPT + "\n" + history_text},
        ],
    )
    summary = summary_resp.choices[0].message.content

    new_messages = [system,
                    {"role": "user", "content": "【此前对话摘要】" + summary}] + recent
    print(f"【上下文压缩】旧 {old_count} 条 → 新 {len(new_messages)} 条")
    return new_messages


def run(question: str, max_rounds: int = 10) -> str:
    """跑一轮完整的 agent 任务，返回模型的最终回答。

    流程：while 大循环 ── 发请求（带工具说明书）── 模型要么给最终答案（退出），
    要么开工单（for 逐张：日志 → execute_tool 安全执行 → 回执回填）── 再请求。
    环境类错误（如缺 API key）抛 RuntimeError，由入口层（cli）负责提示。"""
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("没找到 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填入真实 key。")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    messages = [
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": question},
    ]

    round_count = 0
    final_content = None

    while True:
        round_count += 1
        print(f"--- 第 {round_count} 轮 ---")
        if round_count > max_rounds:
            print("（安全阀：轮数超限，强制收工）")
            break

        # 每轮发请求前检查上下文长度——超限就先压缩历史再请求
        messages = compress_history(messages, client)

        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = resp.choices[0].message

        # 唯一出口：模型没发工单 = 直接给了最终答案
        if not msg.tool_calls:
            final_content = msg.content
            break

        # 回填工单消息：不管肚子里有几张工单，append 都只有一次
        # （msg 是一条消息，工单全在它肚子里；回执才是一单一报）
        messages.append(msg)

        # 逐张处理工单：日志 → 安全执行 → 回执回填
        for call in msg.tool_calls:
            print(f"[第{round_count}轮] 模型调用: {call.function.name}({call.function.arguments})")
            result = execute_tool(call)
            print(f"[第{round_count}轮] 回执: {result[:80]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return final_content
