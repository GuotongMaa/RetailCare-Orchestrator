# Baseline Report (M1 · L0 single agent)

- model: `deepseek-v4-flash`
- tasks: 32  |  passed: 32  |  **pass@1 = 1.0**
- usage: {'calls': 98, 'prompt_tokens': 179087, 'completion_tokens': 18127, 'cost_usd': 0.057758}

| id | intent | pass | called | missing | violated |
|---|---|---|---|---|---|
| T01 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |
| T02 | refund_non_returnable_giftcard | ✅ | check_return_eligibility, get_order, search_policy | — | — |
| T03 | refund_out_of_window | ✅ | check_return_eligibility, get_order | — | — |
| T04 | refund_high_value_defective | ✅ | check_return_eligibility, escalate_to_human, get_order | — | — |
| T05 | refund_high_value_plain | ✅ | check_return_eligibility, escalate_to_human, get_order | — | — |
| T06 | order_status | ✅ | get_order, get_shipment | — | — |
| T07 | shipping_exception | ✅ | get_order, get_shipment, search_policy | — | — |
| T08 | coupons | ✅ | get_coupon | — | — |
| T09 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |
| T10 | refund_boundary_under | ✅ | check_return_eligibility, create_return_request, get_order, search_policy | — | — |
| T11 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |
| T12 | refund_non_returnable_perishable | ✅ | check_return_eligibility, get_order, search_policy | — | — |
| T13 | refund_not_delivered | ✅ | check_return_eligibility, get_order, get_shipment | — | — |
| T14 | refund_boundary_over | ✅ | check_return_eligibility, escalate_to_human, get_order | — | — |
| T15 | refund_low_value_defective | ✅ | check_return_eligibility, escalate_to_human, get_order | — | — |
| T16 | refund_defective | ✅ | check_return_eligibility, escalate_to_human, get_order, get_shipment | — | — |
| T17 | order_status | ✅ | get_order, get_shipment | — | — |
| T18 | order_status | ✅ | get_order, get_shipment | — | — |
| T19 | shipping | ✅ | get_shipment | — | — |
| T20 | shipping | ✅ | get_order, get_shipment | — | — |
| T21 | coupons | ✅ | get_coupon | — | — |
| T22 | coupons | ✅ | get_coupon | — | — |
| T23 | policy_question | ✅ | search_policy | — | — |
| T24 | policy_question | ✅ | search_policy | — | — |
| T25 | compensation_small | ✅ | get_order, get_shipment, search_policy | — | — |
| T26 | escalation_complaint | ✅ | escalate_to_human, get_order | — | — |
| T27 | clarification_needed | ✅ | get_order | — | — |
| T28 | clarification_needed | ✅ | — | — | — |
| T29 | order_status_no_overescalate | ✅ | get_order, get_shipment | — | — |
| T30 | order_status_no_overescalate | ✅ | get_order, get_shipment | — | — |
| T31 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |
| T32 | refund_low_value | ✅ | check_return_eligibility, create_return_request, get_order | — | — |

> pass@1 is a single-run baseline. M3 reports multi-seed pass^k + CIs.
