## Imported Claude Cowork project instructions

面向电商售后/客服场景，构建一个可追踪、可评测、可恢复的多 Agent 系统，处理订单查询、物流、退换货、优惠券、商品推荐、投诉升级等多轮任务，并用真实 benchmark 和业务规则评估任务完成率、工具调用正确率和政策合规性。

## RetailCare core development doctrine

本项目的底层架构逻辑是 **ReAct-first, LangGraph State-governed, system-enforced safety**。后续任何设计、实现、重构和评测都必须保留这三条原则。

1. **ReAct 是核心业务推进机制**
   - 不把售后业务强行写死成固定 workflow。
   - Agent 通过 ReAct 在多轮对话中动态判断下一步业务动作，例如查订单、查物流、查政策、澄清信息、申请退款、发放补偿或升级投诉。
   - 订单、物流、退款、优惠券、投诉之间可以随用户对话自由切换；系统设计要支持复杂、多目标、跨订单、跨商品的售后对话，而不是只支持线性流程。

2. **LangGraph State 是核心可控机制**
   - LangGraph 的首要价值不是堆节点，而是用 state 维护对话和任务的持续状态。
   - State 必须记录 Agent 当前知道什么、正在尝试什么、之前做过什么、哪些事实已经由工具验证、哪些动作正在等待确认或恢复。
   - 长链路、多业务切换、HITL 中断、工具失败和恢复都必须依赖 state/checkpoint，让 ReAct 不迷路、不遗忘、不重复危险动作。
   - 后续升级优先增强 state schema 和状态恢复能力，再考虑增加复杂节点或子图。

3. **Agent 只提出请求，系统决定是否执行**
   - Agent 不是业务系统的最终操作者；Agent 的 tool call 只是对系统的请求、建议或操作意图。
   - 真正决定是否执行的是后端系统：Pydantic schema、权限校验、业务规则、policy check、guardrails、HITL、幂等和审计。
   - 所有高风险写操作必须在执行前经过确定性护栏；不能先执行再补救。
   - 如果 Agent 认为可以退款/补偿/升级，但系统规则判定不允许、不确定或需要人工，则以系统规则为准。

简短表达：RetailCare 不是纯固定 workflow，也不是裸 ReAct。它是一个 **state-grounded ReAct 售后 Agent**：模型负责智能推进，state 负责连续性和可恢复性，系统护栏负责最终安全边界。
