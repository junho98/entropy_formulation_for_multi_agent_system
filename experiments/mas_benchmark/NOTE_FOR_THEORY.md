# Note for theory discussion: pressure transfer and price equalisation (thermo_mas v40, simulation findings)

Implementation: `experiments/mas_benchmark/`, solver `Thermo` (Ours). All numbers are from the benchmark as of 2026-11-12. Setup details are in `SETUP_FOR_V40.md`.

## 1. Pressure from an outsider reaches a teammate only through the pair constraint between them

**Setup.** Agent 0 is at the origin and teammate 1 at (1.3, 0); both hold position. A non-yielding external agent approaches agent 0 from the left at speed 0.5.

| Method | t = 8 s | t = 9 s |
|---|---|---|
| Ours (ε = 0.1) | μ_0e = 1.08, μ_01 = 0.84, μ_10 = 0.01; r_01 → −0.35 | Agent 1 moves aside (x₁: 1.30 → 1.50); μ_01 = 0.14, μ_10 = 0.22; r_01 = −0.65 |
| Oracle | – | x₁ → 1.57; common multiplier 0.32 |
| Reciprocal | – | Agent 1 never moves; d_0e falls to 0.71 (violation) |

**Mechanism.** Every pair constraint is its own specification with its own slack and costate (v40 Sec. 9: one Ψ per specification; Sec. 5: "the exchange on an agreement uses the costates of that specification"). The outsider's load therefore enters μ_0e, not μ_01.

It reaches the (0, 1) agreement only through geometry: the outsider moves agent 0 toward agent 1, the (0, 1) slack shrinks, μ_01 rises, and the exchange moves room to agent 1. This is physically right, since agent 1 can relieve agent 0 only by giving room on c_01. Load is therefore shared only along the directions in which the teammate can actually help.

**Question 1.** Thm 7.2 (a common costate λ*_Γ on a component) is stated for a single shared constraint, where agent i has one room R_i containing all loads L_ik. In the collision instance each pair is a separate specification.
- What is the right statement of load sharing for a family of pairwise specifications coupled only through each agent's input?
- Is there a common price on a component? Our guess: no single λ*, but a KKT-coupled family. The oracle multipliers on the different rows of one agent differ.
- Should v40 state Thm 7.2 for this case, or call the multi-specification case an extension?

## 2. Price equalisation in S1 is limited by tracking, not by the estimates

**Frozen two-agent test.** Weights 1 vs 3, distance 1.4, positions held fixed, only the exchange iterated.
- The first-activation imbalance is 0.48, consistent with the lower bound |w_a − w_b|/(w_a + w_b) = 0.5.
- With step 1/(2k_e): 0.29 after 1 s and 0.004 after 8 s.
- So the stationary point equalises prices, as Thm 5.2(ii) predicts.

**Closed loop.** S1, 6 seeds × 120 s, isolated two-agent encounters, mean imbalance |μ_i − μ_k|/(μ_i + μ_k).

| Method | Imbalance after the first 0.2 s, weights 1 vs 3 | Equal weights |
|---|---|---|
| Ours | 0.43 | 0.32 |
| PCCA | 0.11 | – |
| Tan (with communication) | 0.17 | – |

Encounters last 3–4 s. In the price traces the two prices cross instead of meeting: a lagging integrator.

**Ruled out:**
- *Estimation error:* the replicated λ̂_k matches the true value to about 0.01.
- *The following-mass weight:* its median and 5th percentile during active encounters are both 1.0.

**Step size:**
- A smaller step (×0.5) is worse: 0.43 → 0.50.
- Larger fixed steps (×10 and up) are unstable, with collisions from ×30. The effective ∂λ/∂r reaches k_e at the wall or the input bound, not only the interior value k_e·w/(w + k_e α²).
- A local-curvature (Newton) step chatters and does not help overall.

**Agreements are forgotten when a neighbour leaves range** (v40 Sec. 11: "identities are not known"), so every encounter restarts at r = 0. A side experiment that keeps r_ik across exits, assuming re-identification by observation, is queued.

**Question 2.** Is the S1 claim (Q3: "how close to equal prices, without messages") meant for the stationary equilibrium, or along trajectories?
- Along trajectories, Thm 8.4 gives a tracking error L v̄/(κμ). With encounter-scale geometry change, that appears to be what the 0.43 measures.
- Should the claim be restated, or should the exchange change? Candidates: an adaptive damped step whose curvature includes the wall and input-bound regimes; a PI-type exchange; keeping agreements across encounters.

**Question 3.** The non-overshoot step 1/(2k_e) relies on |∂s/∂r| ≤ 1 with inputs held. In closed loop the costate's sensitivity to r is regime-dependent: about k_e w/(w + k_e α²) inside the layer when the input responds, and up to k_e at the wall or input bound.
- Is there a step rule that keeps the non-overshoot guarantee and is not 100× too slow in the interior regime?
- Can i and k compute it from public quantities only, so that their copies stay antisymmetric?

## 3. Things the theory may want to know

- **Linearisation coefficient:** a = w/(w + k_e α²), with w = 1 as the public self-model (author-confirmed correction of v40 Sec. 11).
- **Following-mass weighted exchange:** under exact replicas it gives r_ik + r_ki ≤ 0; measured range [−0.04, 0].
  - This is *not* the cautious direction. Prop. 2.7 needs r_ik + r_ki ≥ 0, so the pair's allowances then exceed the budget and only the coverage term protects it (Remark 5.3).
  - The gap also feeds back into the replica, which assumes r_ki = −r_ik (Assumption 2.10).
  - Combined with a large exchange step, the follow law makes the copies diverge: in S1, |r_ik + r_ki| up to 2.6. With the unweighted law, the copies stay exact.
- **Oracle deadlock in S1:** several agents stop for about 80 s, an instance of the liveness gap in v40 Sec. 13.
- **Tan outside its Assumption 3:** teammates collide, even in S1 with no externals, because local Slater fails with more than 2 active rows on 2 inputs.
