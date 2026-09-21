# tool_demo.py —— 一次工具调用的全链路（填空版）
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com")

# ---------- ① 真正干活的功能函数（给你了） ----------
def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 {path} 不存在"

# ---------- ② 工具定义：告诉模型"你有什么工具可用" ----------
TOOLS = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取指定路径的文本文件内容",   # 模型靠这句决定何时用它
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"],
        },
    },
}]

messages = [
    {"role": "system", "content": "你是一个简洁的助手。"},
    {"role": "user", "content": "当前目录的README.md里写了什么？"},
]

# ---------- ③ 第一次请求：带上工具定义 ----------
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=TOOLS
)

msg = resp.choices[0].message

# ---------- ④ 三件套：模型要用工具时 ----------
if msg.tool_calls:
    call = msg.tool_calls[0]
    args = json.loads(call.function.arguments)
    result = read_file(args["path"])

    messages.append(msg)
    # 因为api是无状态的需要把模型的回复再次发送给模型
    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    # 需要加上call_id才知道工具调用情况

    # [TODO-6] 三件套最后一件：再发一次请求（参数和第一次完全一样）
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools = TOOLS)
    msg = resp.choices[0].message

# ---------- ⑤ 最终回答 ----------
print(msg.content)
