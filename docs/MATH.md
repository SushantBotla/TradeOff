# Mathematical model

All quantities are integer chip units in this tiny example. Costs are synthetic dollars. No batch rules or payments are modeled. Primary production cost is treated as committed/sunk. Alternative supply is capacity usable before day 5; the app does not solve a time-expanded scheduling problem.

## Full-information reference

For factory i, gross demand is d, safety stock s, replenishment cost r, mild-shortage threshold t, and marginal losses p1 <= p2. Choose external allocation x, stock draw u in [0,s], and shortage z=d-x-u >=0. Cost is:

`alternate_unit_cost*y + sum(r_i*u_i + p1_i*min(z_i,t_i) + p2_i*max(0,z_i-t_i))`

Subject to total external allocations <= primary_capacity+y and 0<=y<=alternate_capacity. The mandatory local service rule rejects severe-tier shortage, so the reference also requires z_i<=t_i. If those requirements conflict, its status is `infeasible_service_requirements`.

Baseline: A=(d600,s40,r45,t100,p1=90,p2=220), B=(d500,s50,r30,t150,p1=40,p2=110), primary800, alternative300 at unit95. Reference allocation A500/B300/y0 gives stock draws40/50 and shortages60/150, total14700. Both service rules are satisfied.

The separate oracle enumerates possible stock decisions and external quantity pairs; it is independent of the restricted optimizer. The supplied fixtures have stock draw cheaper than all shortage units. If extending this prototype to other local policies, preserve comparable local feasible sets in the oracle and candidate cost evaluator.

## Restricted coordinator

Factories initially submit only requested quantity q=d-s, a coarse priority b and a deadline. The coordinator minimizes:

`alternate_unit_cost*y + sum(b_i*(q_i-x_i))`

Subject to supply limits, 0<=x_i<=q_i and any previously authenticated minimum quantity floors. This objective is a surrogate and is displayed separately from true simulated cost.

For each possible A quantity, the B objective is linear below and above the primary-capacity kink. Checking the feasible B endpoints and that kink yields the exact integer optimum for this two-factory objective. It is bounded to small requests, not a scalable general supply-network engine. OS CBC via PuLP 3.x is an optional solver backend.

Round 1 A560/B240/y0 is physically feasible but rejected by B's service policy. B publishes only minimum external quantity300, not its reason/cost curve. Round2 preserves priorities165/75, enforces B>=300 and returns A560/B300/y60. True cost15000; gap2.040816% against14700. Feedback is itself a disclosure.

Primary capacity480: reference A460/B300/y280 at44900; restricted repair A480/B300/y300 at45000. Combined capacity480+150 cannot satisfy both service floors460+300, and coordination remains unresolved.

No-scarcity reference cost0 yields relative gapN/A. Coarse requests may still draw stock unnecessarily, so absolute regret is available. The system never forces a positive gap or promises a target percentage.
