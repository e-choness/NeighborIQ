---
title: Cash-flow calculator
description: The NeighborIQ cash-flow calculator, running in your browser.
---

# Cash-flow calculator

This is the calculator from the app, running in your browser. It uses the same formulas as the API,
and a shared test fixture keeps the two in sync. Change any input; the link updates so you can share
the scenario.

<CashFlowCalculator />

## What it assumes

- **Mortgage.** Fixed rate, compounded semi-annually as Canadian law requires. With less than 20% down,
  the CMHC premium is added to the loan.
- **Closing costs.** Land transfer tax for the city's province (Toronto adds its municipal tax), plus
  $2,000 for legal and inspection.
- **Year one only.** No rent growth, appreciation, income tax or rate renewal. It screens deals; it
  does not forecast them.

The full definitions are in the [Methodology](/methodology#cash-flow).
