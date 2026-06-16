# Baseline Report (M1 · L0 single agent)

- model: `deepseek-v4-flash`
- tasks: 8  |  passed: 8  |  **pass@1 = 1.0**
- usage: {'calls': 25, 'prompt_tokens': 46467, 'completion_tokens': 4664, 'cost_usd': 0.01497}

| id | intent | pass | called | missing | violated |
|---|---|---|---|---|---|
| T01 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |
| T02 | refund_non_returnable | ✅ | check_return_eligibility, get_order, search_policy | — | — |
| T03 | refund_out_of_window | ✅ | check_return_eligibility, get_order | — | — |
| T04 | refund_high_value_defective | ✅ | check_return_eligibility, escalate_to_human, get_order, search_policy | — | — |
| T05 | refund_high_value_plain | ✅ | check_return_eligibility, escalate_to_human, get_order | — | — |
| T06 | order_status | ✅ | get_order, get_shipment | — | — |
| T07 | shipping | ✅ | get_order, get_shipment | — | — |
| T08 | coupons | ✅ | get_coupon | — | — |

> pass@1 is a single-run baseline. M3 reports multi-seed pass^k + CIs.
