Git repository / Git 仓库地址:
https://github.com/Ruiyu-X/coding-agent

运行方式:
安装 Python 3.10+ 后，在仓库根目录运行稳定演示：
python main.py "Fix the calculator implementation, add safe divide, extend tests, and verify everything." --mock

如需调用真实模型，在当前终端临时设置 OPENAI_API_KEY、OPENAI_MODEL 和可选的 OPENAI_BASE_URL，然后运行：
python main.py "Add a power(a, b) function to the calculator, add tests inside CalculatorTests, verify that test_power is discovered, and verify all tests pass." --workspace demo_workspace --max-steps 30

特色功能:
本项目实现了一个简化编程智能体，未使用 LangChain、AutoGen、OpenAI Agents SDK 等 agent 框架，也未依赖服务端托管的代码执行或文件工具。程序自行维护对话历史，要求模型输出 JSON 动作，解析后在本地执行工具，包括工作区摘要、列文件、读写文件、精确替换、命令执行、Python 语法检查、unittest 测试发现校验和 diff 审计。每次运行会生成本地 JSON transcript，便于追踪模型决策、工具参数和观察结果。API key 仅通过环境变量提供，不写入仓库、README 或视频。
