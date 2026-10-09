# mini_harness/tools.py —— 工具层：说明书、注册表、危险名单、安全执行器
# 收编自 mini_loop.py（Day 11-12 的加固成果原样迁入，逻辑未动）。
import json
import os


# ---------- 工具函数（三件真家伙） ----------
def read_file(path):
    """读取文本文件；目录路径会得到自愈提示（错误是数据，不是终点）"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件 {path} 不存在"
    except IsADirectoryError:
        # 告诉模型正确的工具是谁——模型拿到这句回执，下一轮自己换（自愈）
        return f"错误：{path} 是一个目录，不是文件。要看目录内容请改用 list_dir 工具"


def list_dir(path="."):
    """列出目录下的文件与文件夹名"""
    try:
        return "\n".join(os.listdir(path))
    except FileNotFoundError:
        return f"错误：目录 {path} 不存在"


def write_file(path, content):
    """有副作用的工具：写入/覆盖文本文件。执行前必须过权限闸门（见 execute_tool）。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入 {path}({len(content)} 字符)"


# ---------- 工具说明书：发给模型的"菜单" ----------
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
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入/覆盖文本文件，有副作用（会创建或覆盖目标文件，被覆盖的内容无法恢复）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目标文件路径"},
                    "content": {"type": "string", "description": "要写入的完整文本内容"}
                },
                "required": ["path", "content"],
            },
        },
    },
]

# ---------- 注册表：名字 → 函数 ----------
TOOL_FUNCS = {"read_file": read_file, "list_dir": list_dir, "write_file": write_file}

# 危险名单：出现在这里的工具会改动真实世界（磁盘），
# 每次执行前必须获得人工放行（y）。读类工具不需要——看一眼世界是安全的。
RISK_TOOLS = {"write_file"}


# ---------- 安全执行器 ----------
def execute_tool(call):
    """接收一张工单（tool call 对象），安全地执行它。
    三步链条（解析参数 → 查注册表 → 权限闸门 → 执行）任何一步失败，
    都返回一句【错误描述字符串】而不是抛异常——错误是数据，不是终点：
    它会作为回执喂回模型，模型下一轮照常思考、自我纠正；
    若让它炸穿循环，对话直接死亡，前面所有轮次全部作废。"""

    name = call.function.name

    # 第 1 步：查注册表。必须用 .get()——查不到返回 None，
    # 方括号下标会抛 KeyError 炸穿循环。模型是概率系统，
    # 编造不存在的工具名是常态不是事故。
    func = TOOL_FUNCS.get(name)
    if func is None:
        # 顺带报出可用工具清单，等于给模型递一张正确菜单
        return f"错误：没有名为 {name} 的工具。可用工具：{', '.join(TOOL_FUNCS)}"

    # 第 2 步：解析参数。arguments 是模型生成的字符串，可能不是合法 JSON。
    try:
        args = json.loads(call.function.arguments)
    except json.JSONDecodeError:
        # 把原始 arguments 附在错误里回传：模型看到自己写的原句，下一轮就会改
        return f"错误：参数不是合法 JSON：{call.function.arguments}"

    # 第 2.5 步：权限闸门。危险工具在执行前先过人这一关——
    # 模型是概率系统，它"想写"不等于"该写"；改动真实世界的决定，人最终拍板。
    if name in RISK_TOOLS:
        # 参数摘要打出来给人看（内容太长截断），人要知道自己在放行什么
        args_view = ", ".join(f"{k}={str(v)[:60]!r}" for k, v in args.items())
        print(f"⚠ 即将执行 {name}({args_view})，允许吗？(y/n)")
        try:
            answer = input("> ").strip().lower()
            # Windows 坑：PowerShell 5.1 管道喂入的文本自带 UTF-8 BOM 前缀
            # （U+FEFF），它不是空白字符，上面的 strip() 去不掉——
            # 不剥掉它，BOM+y 永远不等于 y，放行永远会被误判成拒绝。
            answer = answer.replace(chr(65279), "")   # 65279 = U+FEFF
        except EOFError:
            # 没人可问（输入流已关闭）时视为拒绝：宁可错杀不可放行（fail-closed）
            answer = ""
        if answer != "y":
            # 【拒绝也是数据】拒绝不抛异常、不退出程序，而是返回说明文字：
            # 这句话作为正常回执进入对话，模型读到"被拒绝"，
            # 下一轮自己调整方案（换路径/改问用户），对话继续活着；
            # 若抛异常则炸穿 while 循环——对话死亡，模型连"为什么被拒"都不知道。
            return "用户拒绝了本次 write_file 操作，请改用其他方案或询问用户"

    # 第 3 步：执行。前面都过了仍可能翻车（路径不存在、参数名对不上等），
    # 用兜底 except 全接住，把"错在哪"翻译给模型。
    try:
        return func(**args)
    except Exception as e:
        return f"错误：工具执行失败：{type(e).__name__}: {e}"
