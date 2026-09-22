# mini_loop.py —— agent loop 成形 + 错误恢复版（v2）
# v1 只在"风和日丽"时能跑：模型编造工具名、参数不是合法 JSON、
# 把目录路径喂给 read_file，任何一样都会抛异常炸穿循环。
# v2 的核心原则：【错误是数据，不是终点】——
#   把错误当成回执喂回给模型，它下一轮就能自我纠正；
#   而异常一旦炸穿循环，整个对话死亡，模型"失忆"，谁也救不了。
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com")

MAX_ROUNDS = 10   # 安全阀：最多转几轮

# ---------- ① 工具函数（两件真家伙） ----------
def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 {path} 不存在"
    except IsADirectoryError:
        # v2 新增：把目录路径当文件读，open 抛的就是这个错。
        # 同样"返回文字不抛异常"，并顺带告诉模型正确的工具是谁——
        # 模型拿到这句回执，下一轮就会自己改用 list_dir（自愈）。
        return f"错误：{path} 是一个目录，不是文件。要看目录内容请改用 list_dir 工具"

def list_dir(path="."):
    try:
        return "\n".join(os.listdir(path))
    except FileNotFoundError:
        return f"错误：目录 {path} 不存在"

# ---------- ② 工具说明书 ----------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径的文本文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出目录下的文件与文件夹名",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，默认当前目录"}
                },
                "required": ["path"],
            },
        },
    }
]

# ---------- ③ 注册表：名字 → 函数 ----------
TOOL_FUNCS = {"read_file": read_file, "list_dir": list_dir}


# ---------- ③.5 安全执行器（v2 新增） ----------
def execute_tool(call):
    """接收一张工单（tool call 对象），安全地执行它。
    三步链条（解析参数 → 查注册表 → 执行）任何一步失败，
    都返回一句【错误描述字符串】而不是抛异常——错误是数据，不是终点：
    它会作为回执喂回模型，模型下一轮照常思考、自我纠正；
    若让它炸穿循环，对话直接死亡，前面所有轮次全部作废。"""

    name = call.function.name

    # 第 1 步：查注册表。必须用 .get()——查不到返回 None，
    # 而方括号下标 TOOL_FUNCS[name] 会抛 KeyError 炸穿循环。
    # 模型是概率系统，编造不存在的工具名（如 list_files）是常态不是事故。
    func = TOOL_FUNCS.get(name)
    if func is None:
        # 顺带报出可用工具清单，等于给模型递一张正确菜单
        return f"错误：没有名为 {name} 的工具。可用工具：read_file, list_dir"

    # 第 2 步：解析参数。arguments 是模型【生成】的字符串，
    # 概率系统可能吐出残缺/非法 JSON，json.loads 会抛 JSONDecodeError。
    try:
        args = json.loads(call.function.arguments)
    except json.JSONDecodeError:
        # 把原始 arguments 附在错误里回传：模型看到自己写的原句，
        # 下一轮就知道该怎么改
        return f"错误：参数不是合法 JSON：{call.function.arguments}"

    # 第 3 步：执行。前面两步都过了，执行仍可能翻车
    # （如 read_file 收到目录、参数名对不上等），用兜底 except 全接住。
    try:
        return func(**args)
    except Exception as e:
        # 异常类型 + 异常信息一起回传：模型需要"错在哪"才能修正下一步
        return f"错误：工具执行失败：{type(e).__name__}: {e}"


messages = [
    {"role": "system", "content": "你是一个简洁的助手。"},
    {"role": "user",
     "content": "lessons 目录下有哪些文件？如果有名字里带 agent-loop 的课件，读一下它开头讲了什么。"},
]

round_count = 0
final_content = None

# ---------- ④ 大循环 ----------
while True:
    round_count += 1
    print(f"--- 第 {round_count} 轮 ---")
    if round_count > MAX_ROUNDS:
        print("（安全阀：轮数超限，强制收工）")
        break

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=TOOLS_SCHEMA,
    )
    msg = resp.choices[0].message

    # [TODO-4] 唯一出口：模型没发工单时，把答案存进 final_content 并 break
    if not msg.tool_calls:
        final_content = msg.content
        break
    # 打印 tool_calls 数量，模型直接给答案（不开工单）的那次，这个值为0。

    # [TODO-5] 回填工单消息：不管里面有几张工单，append 几次？
    messages.append(msg)
    # 一轮开几张单都只 append 这一次：msg 是一条消息，工单全在它肚子里，
    # 一次就能全部提交上去（回执才是一单一报）。

    # [TODO-6] 循环头：逐张处理工单
    for call in msg.tool_calls:
        # v2 改造：每张工单两行——安全执行 + 回填回执。
        # 解析、查表、执行的全部风险都关在 execute_tool 里，
        # 它保证永远返回字符串，循环本体再也不会被异常炸穿。
        result = execute_tool(call)
        # call.id 是工单号：服务器靠它把每张回执对应回开单时的那张工单
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    # 循环自动回到顶部：带着变长的历史，再次请求

print(final_content)
