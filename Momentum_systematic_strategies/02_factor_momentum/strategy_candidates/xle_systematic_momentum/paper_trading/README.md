# Paper-trading preparation

`ibkr_paper_dry_run.py` is intentionally read-only and dry-run only. It reconstructs the frozen XLE systematic-momentum signal from Gold, probes only the local paper API ports, and records a blocked proposal in `ledger/dry_run_proposals.jsonl`. It contains no code path that submits an order.

The candidate contract is a verification request, not an approved contract identifier: `XLE`, `STK`, `SMART`, `USD`, primary exchange `ARCA`. The connection must return its contract details and `conId` before any later paper-order work.

The local `MANUAL_STOP` file is active by default. The future implementation must also confirm the paper account, available settled cash, current XLE position, and open orders before a human reviews any proposal. The hard limits are USD 10,000 maximum budget, non-negative cash, no margin, and no leverage.

IBKR documents paper defaults of port 7497 for TWS and 4002 for Gateway, and states that the TWS API Read-Only setting blocks orders. A Market-on-Open order exists, but a historical daily `open` is not evidence of an achievable paper or live fill; this requires a separate paper observation. See [IBKR API configuration](https://www.interactivebrokers.com/campus/trading-lessons/installing-configuring-tws-for-the-api/) and [IBKR order types](https://www.interactivebrokers.com/support/faq/content/order-types-interactive-brokers-offer-28225712).
