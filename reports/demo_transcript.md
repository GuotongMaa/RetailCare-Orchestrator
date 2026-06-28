> ⚠️ **升级前基线结果**：本报告是 M1–M4 阶段的评估输出，早于 A/B/C 信任边界 + 结构化 state + 健壮性升级。数据集已对齐新架构；报告重跑待续（需模型 API）。

# Demo Transcript (`make demo`)

Refund hero flow: HITL confirmation + cross-session resume (real DeepSeek v4-flash).

```

================================================================
Scenario A — refund with HITL confirmation (single session)
================================================================
  ⏸  HITL interrupt: Confirm create_return_request for $29.0? (yes/no)
  👤 (customer types) yes
  🤖 Your return has been successfully created! Here's a summary:

📋 **Return Ticket:** `T27c8453a`
🛒 **Item:** Cotton T-Shirt (I1)
❓ **Reason:** Wrong size
💰 **Refund Amount:** **$29.00**
📌 **Status:** Created

Once we receive the item back in original condition, the refund will be processed. You should receive instructions for returning the item shortly. Is there anything else I can help you with?
  🧠 Ticket summary: order=O1001, item=I1, reason=wrong size, eligibility=ok, refund=$29.0, outcome=ticket_created, ticket=T27c8453a

================================================================
Scenario B — cross-session resume (customer returns next day)
================================================================
  Day 1 ⏸  paused awaiting confirmation on thread 'ticket-757acc' — customer leaves.
  ... next day, new session ...
  Day 2 🤖 Your return has been processed! Here's a summary:

| Detail | Info |
|--------|------|
| **Item** | Rain Jacket (I9) |
| **Order** | O1005 |
| **Reason** | Too big |
| **Refund Amount** | **$80.00** |
| **Return Ticket** | T87f15562 |
| **Status** | ✅ Created |

Please send the rain jacket back in its original condition. Once it's received, the refund will be issued. If you have any further questions, feel free to ask!
  🧠 Ticket summary: order=O1005, item=I9, reason=Too big - sizing issue, eligibility=ok, refund=$80.0, outcome=ticket_created, ticket=T87f15562

--- usage: {'calls': 8, 'prompt_tokens': 15344, 'completion_tokens': 1386, 'cost_usd': 0.004878} ---
```
