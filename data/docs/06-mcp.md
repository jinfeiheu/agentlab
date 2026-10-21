# MCP 模型上下文协议

## MCP 是什么
MCP（Model Context Protocol）是连接模型应用与外部能力的标准协议。Server 暴露工具、资源和提示，Client 发现并调用它们。它把“工具怎么实现”和“模型怎么使用”解耦，同一个 server 可以被不同 Agent 或 IDE 复用，减少为每个应用重复写集成代码。

## 传输方式
MCP 支持多种传输。stdio 通过标准输入输出与本地子进程通信，启动简单，适合本机工具；Streamable HTTP 通过 HTTP 连接远程 server，适合多用户和独立部署。选择时考虑部署位置、生命周期、认证和网络边界，本地私有工具通常优先 stdio。

## 工具暴露
用 FastMCP 可以快速定义 server：创建实例，用 `@mcp.tool` 装饰函数，类型注解生成参数 schema，docstring 作为描述，然后 run 启动。工具应保持单一职责，返回可序列化结果；高风险操作要在 server 内部做权限校验，不能只依赖模型自觉。

## 客户端接入
langchain-mcp-adapters 的 MultiServerMCPClient 可以配置多个 server，通过 get_tools() 把 MCP 工具转换成 LangChain 工具，再交给 create_agent 或 ToolNode。get_tools 是异步接口，通常在应用启动时调用一次。连接失败要给出可读错误，不要让整个 Agent 静默不可用。

## 权限边界
MCP 工具不应暴露用户私有数据，除非协议层能可靠传递并校验身份。更安全的做法是：MCP 只提供公共、只读能力，私有 ticket、记忆等留在本地工具，通过 runtime context 注入 user_id 并做 owner 校验。这样模型无法通过伪造参数越权。

## 版本兼容
MCP 生态仍在快速演进，版本约束很重要。langchain-mcp-adapters 0.3.x 依赖 mcp 1.x，安装 mcp 2.x 会导致导入失败，因此项目应固定 `mcp>=1.24,<2`。升级适配器前先看依赖声明和变更日志，并在本地跑通最小 client/server 示例。
