# BFCL-style Function-Calling Report (M2)

- **tool_call_accuracy = 0.8**  |  **argument_accuracy = 0.8**  (n=10)

| id | tool_ok | args_ok | trajectory |
|---|---|---|---|
| B01 | ✅ | ✅ | get_order, get_shipment |
| B02 | ✅ | ✅ | get_order, get_shipment |
| B03 | ✅ | ✅ | get_coupon |
| B04 | ❌ | ❌ | get_order |
| B05 | ❌ | ❌ | — |
| B06 | ✅ | ✅ | get_order, get_shipment |
| B07 | ✅ | ✅ | get_order |
| B08 | ✅ | ✅ | get_coupon |
| B09 | ✅ | ✅ | get_order, check_return_eligibility |
| B10 | ✅ | ✅ | get_shipment |

> Trajectory-presence metric (ReAct may fetch the order first). Domain-adapted BFCL methodology over the project's MCP tools; full external BFCL-v4 corpus integration is a stretch goal.
