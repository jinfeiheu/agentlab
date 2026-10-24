# 安全策略

## 身份与令牌

demo 登录使用 HS256 JWT,默认有效期 3600 秒。user_id 只从服务端校验后的 token 读取,请求体不能指定 user_id。API 的 thread_id 固定为 user_id:session_id。

## 工具白名单

允许的工具为 search_docs、calculator、get_ticket、send_report、save_memory、search_memory、list_sources、doc_stats、word_count。白名单之外的任何工具调用都会被拒绝并返回 ToolMessage。

## 注入检测

输入包含“忽略之前的指令”“ignore previous instructions”“system prompt”“泄露提示词”“你现在是”等模式时直接拒绝。拒绝发生在进入图之前,不会调用模型。

## PII 脱敏

日志、SSE 工具参数/结果和 trace span 属性统一脱敏:邮箱替换为 [EMAIL],手机号替换为 [PHONE],18 位身份证替换为 [ID],16-19 位银行卡替换为 [CARD]。先匹配身份证再匹配银行卡。

## 工单权限

get_ticket 只允许查询当前用户自己的工单。跨用户查询统一返回“未找到或无权限”,不泄露工单是否存在。工单保存在 tickets 表,字段为 ticket_id、user_id、subject、status。

## 限流与超时

每个用户每分钟最多 30 个请求,超过返回 429。单轮请求超时 REQUEST_TIMEOUT=60 秒,超时返回可读错误。

## 演示用户

共有 alice、bob、carol 三个演示用户,user_id 分别为 user_alice、user_bob、user_carol。演示密码仅供本地演示,生产必须替换 AUTH_SECRET。

## 已知边界

JWT 只签名不加密,payload 可被读取;demo 密码写在内存字典里。生产环境需要真正的用户库、密钥轮换和 HTTPS。
