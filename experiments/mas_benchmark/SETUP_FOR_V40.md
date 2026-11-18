# Setup details to add to thermo_mas v40 (Sec. 10–12)

This document collects what the `mas_benchmark` implementation fixes beyond, or differently from, the v40 text. It is written for updating the paper and the slides.

Status as of 2026-11-12:
- The exchange step for Ours is still under study for S1 (see §4); no final Ours numbers yet.
- Baselines S1 are done and S2–S4 are running.
- All code is in `experiments/mas_benchmark/`.

---

## 1. Corrections to v40

| Where | v40 text | Implementation |
|---|---|---|
| Sec. 11 "Belief", layer regime | `a = α²/(α² + k_e)` | **`a = w/(w + k_e α²)`**, with `w = 1` (the public self-model). Derived from the pair-axis QP `w/2 (y−ū)² + k_e/2 (αy − const)²`. Confirmed by the author; the old simulation code (`win_regime`) had the same error. |
| Sec. 11 "Belief", regime | "the regime of its own response" | **"the regime of the modelled response of k"**: unconstrained, in the layer, or at the wall, evaluated from i's replica of k's slack. |
| Sec. 11 "Exchange" | `r_ik ← r_ik − (λ_i − λ̂_k)/(2k_e)` | **Following-mass weighted:** `r_ik ← r_ik − (λ_i − w_ik(f) λ̂_k)/(2k_e)` (see §2). |

## 2. Ours: choices v40 leaves open

**Information.** Each agent uses only its own observation:
- its own state, nominal input and weight;
- for each sensed body, an anonymous track id with its position and last velocity;
- the public constants (`v_env`, the convention, `w = 1` in the self-model).

Every estimated neighbour price is read from i's replica of that neighbour. Track ids are a random permutation per run, so an id reveals nothing about team membership. A test enforces that Ours touches nothing but this local view.

**Linearisation `y = a ū + b`** (`α = 2‖d_ik‖`, `R` = the responder's room):

| Regime | `a` | `b` |
|---|---|---|
| Unconstrained | 1 | 0 |
| In the layer | `1/(1 + k_e α²)` | `−k_e α (ε + R − κh/2)/(1 + k_e α²)` |
| At the wall | 0 | `(κh/2 − R)/α` |

**Finite-τ predictive.** The neighbour's term is `c ~ N(min(α m − κh/2, r), α²(τ + v + σ_o²))`, where `m` and `v` are the posterior mean and variance of `ū`. The excess over the agreement is `Bernoulli(Pr(c > r)) × Exp(M/τ)`, which gives a closed-form MGF.

**Infinite τ.** Uniform on `[g_min, g_max]`, with `g = −κh/2 ± α v_env`.

**Bound.** The minimisation is over 400 log-spaced values of θ in `[1e-4, 50]`, with δ = 0.05.

**Prior.**
- Following mass `w0 = 0.97`, split `(0.4, 0.4, 0.15, 0.05)` over `τ ∈ {1e-4, 1e-2, 1e-1, 1}`.
- `τ = ∞` gets `1 − w0`.
- Sensitivity sweep: `w0 ∈ {1, 0.99, 0.97, 0.9}`.

**Exchange.**

    r_ik ← r_ik − step · (λ_i − w_ik(f) λ̂_k),   λ = k_e (ε − s)_+

- `w_ik(f)` is i's posterior mass on the following (finite-τ) hypotheses about k.
- Under exact replicas, `d/dt (r_ik + r_ki) = −κ[(1−w_ki(f)) λ_i + (1−w_ik(f)) λ_k] ≤ 0`. **Correction (2026-11-12): this is not the cautious direction.** Prop. 2.7 needs `r_ik + r_ki ≥ 0`: the allowances `a = −Σ r` must fit in the budget. A negative gap lets the pair's allowances exceed it, and safety then rests on the coverage term (Remark 5.3). Measured with the default step: `r_ik + r_ki ∈ [−0.04, 0]`, and exactly 0 with the unweighted law.
- Step `1/(2k_e) = 0.025`, the largest step that never overshoots (the pair's costate difference is `2k_e`-Lipschitz in r with inputs held).
- The step of earlier batch runs ("0.2Δd") is unrecorded and is not used.

**Agreements.**
- Created at 0 when a body enters sensing range; dropped, together with both belief windows, when it leaves.
- Not clamped.
- Transmissions are set to one.

**S1 `v_env`.** S1 has no external agents, so `v_env = 1.2` (the agents' own capability). It enters only the τ = ∞ hypothesis.

## 3. Sec. 12.1 Testbed, made precise

**Arena.**
- Agents start evenly spaced on the radius-6 circle.
- Each target is uniform on that circle, at least 6 away from the agent's current position. A new target is drawn on arrival (within 0.2).
- `u0` has unit speed toward the target.
- Pair constraints are applied within sensing range 5, for every method.

**External agents.**
- Initial positions are uniform in the radius-7 disc, at least 2 from every other body.
- Heading is a random walk with noise 2 rad/√s in S2–S4. The S2 cell of the v40 table is garbled.
- Specular reflection at radius 7.
- S2 avoidance: the heading vector gets `Σ (q − p)/‖q − p‖²` over bodies within 2 added to it, then is renormalised to the agent's speed.

**Scenarios.**

| | Externals | Speed | Behaviour | `v_env` | Weights |
|---|---|---|---|---|---|
| S1 | 0 | – | – | 1.2 | 1, 3 alternating |
| S2 | 8 | 0.8 | reactive | 1.0 | 1 |
| S3 | 4 | 0.5 | never yield | 0.6 | 1 |
| S4 | 8 | 0.8 | never yield | 1.0 | 1 |

**Protocol.**
- 6 seeds × 120 s per scenario and method.
- One seed fixes the initial conditions, the targets and the external trajectories for all methods. The track permutation uses a separate stream.

**QPs.** Goldfarb–Idnani active set (quadprog). Every safety row of every method is softened by the exact penalty `M = 1000`.

**Baselines** (adaptations to single integrators; equation numbers refer to the PDFs in `ref_notes/baselines/`):
- **Oracle:** one central QP over all team inputs. It applies the full pair constraint, and every external agent is covered at `v_env`.
- **Tan** (Tan, Liu, Johansson, Dimarogonas, IEEE TAC 2025, arXiv:2404.07571):
  - sparse local QP, Eq. (18);
  - update: the time-varying law, Eq. (26), with `sign` replaced by `sat` (slope 10 on ±0.1) and `k0 = 1`, as in their Sec. VIII-B;
  - `−κh` is split equally (the paper leaves `b^m` unassigned);
  - `y` and the multipliers are exchanged between team pairs; externals are identified and covered at `v_env`;
  - an agent whose local QP needs a slack (Assumption 3 fails) reports no multipliers that step.
- **PCCA** (Janković, Santillo, Wang, IEEE TCST 2024, arXiv:2012.10261; Santillo & Janković, arXiv:2008.12092):
  - Eq. (18)–(19) at relative degree one: `a = κh`, `b = 2dᵀ`;
  - unit cost weights, as in Eq. (18);
  - copies of every sensed body, corrector `ŵ_j = u_j − u*_ij` with a one-sample delay;
  - only the agent's own input is bounded.
- **Risk ratio** (Lyu, Luo, Dolan, IROS 2023, arXiv:2305.13467):
  - Eq. (3)–(7), deterministic (the CVaR term is 0);
  - `ω_ik = R_k/(R_i + R_k)`;
  - `R` is summed over bodies within sensing range;
  - `c = 2 r_s (2 u_max) + κ r_s² + 1 = 75`, the smallest value that keeps `L > 0` (the paper gives none);
  - octagonal input bound instead of a box.
- **Reciprocal:** a fixed half split of the shares.

**Metrics.**
- **Cost:** mean of `f_i`.
- **Minimum distance:** among agents and to external agents (the minimum over seeds).
- **Fraction of time in violation:** the fraction of steps in which some pair is below `0.95ρ`, with the same threshold for agents and externals. Contact at `ρ` within `O(Δt²)` is not counted.
- **Agreement gap:** `r_ik + r_ki`, reported as its maximum `|·|` and its most negative value.
- **Price imbalance (S1):**
  - Score: `|μ_i − μ_k|/(μ_i + μ_k)`.
  - Isolated encounter: the maximal run of steps in which i's only active price is toward k and vice versa.
  - μ is `k_e p` for Ours and the QP multiplier of that pair row for the baselines.
  - Averaged per encounter, then over encounters; split into equal and different weights, and into the first 0.2 s and the settled remainder.
  - Number of encounters is reported.
- **Planned:**
  - per-seed comparison against the oracle (Q1/Q2);
  - the ε / w0 trade-off figure (Q4);
  - fraction of time below speed 0.15 (stops and deadlock).

## 4. Findings so far (preliminary; for the text and the slides)

**Baseline checks against their papers** (`results/validation.md`): 8 of 8 pass.
- Tan converges to the central optimum and every iterate is feasible (frozen state).
- PCCA reproduces the central solution for two cooperating agents and keeps `h ≥ O(Δt)` against a non-cooperating one.
- In the risk ratio, `ω_ij + ω_ji = 1`.
- PCCA and the risk ratio stay collision-free in a 6-agent swap.

**Tan outside its Assumption 3.** In the swap and in S2–S4, local QPs become infeasible: up to 5 active rows on 2 inputs, or worst-case external cover. Team distances then fall below ρ (0.77–0.91 in S2–S4 at 30 s). This is a limit of the method outside its assumption, not a coding error.

**CBF deadlock.** Oracle, S1, seed 2: several agents stop head-on for about 80 s (cost 0.34 vs about 0.05). This is the known liveness gap of CBF-QPs (v40 Sec. 13), which v40 does not address.

**Price equalisation (S1).**
- Frozen two-agent check, weights 1 vs 3, distance 1.4: the first activation imbalance is 0.48, consistent with the bound `|w_a − w_b|/(w_a + w_b) = 0.5`.
  - With step `1/(2k_e)` the exchange equalises prices: 0.29 after 1 s, 0.004 after 8 s.
  - A local-curvature (Newton) step does it in about 1 s.
- Closed loop (one seed, 30 s): imbalance stays about 0.44, because encounters last 1–2 s, shorter than the convergence time.
- Larger fixed steps (×10 and up) destabilise: copies drift, and at ×30 or more agents collide.
- The 6-seed S1 analysis (default vs Newton step) is pending.
