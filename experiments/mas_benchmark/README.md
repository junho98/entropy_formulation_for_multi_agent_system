# mas_benchmark

This is a collision-avoidance benchmark for "Sharing Coupled Constraints without Communication". It follows the PDF in `ref_notes/thermo_mas_v40.pdf`, Sections 11 and 12.

## Setup

    conda env create -f environment.yml      # env name: mas-bench (python 3.11, installs this package editable)
    conda activate mas-bench
    python scripts/smoke.py --horizon 10     # writes results/smoke.json
    python scripts/validate_refs.py          # baselines vs. the reference papers' claims -> results/validation.md
    python scripts/run_grid.py --workers 11  # Sec. 12.1 grid + following-prior sweep (4 x 17 x 6 seeds x 120 s) -> results/grid.jsonl, resumable
    python scripts/summarize_grid.py         # -> results/summary.md
    pytest tests

## Layout

- `src/mas_benchmark/core/`: the abstract layer. Realizations subclass these classes; nothing in `core/` knows the instance.
  - `Dynamics`: `step`, `input_polytope` (`A u <= b`), `position`.
  - `Specification`: the pairwise coupled constraint `c_ik = g_i(u_i) + g_k(u_k) <= 0`. It provides `own_term` (affine share), `safety`, `sensing_range`, `rho`.
  - `Scenario`: the world outside the solver. It provides `reset(rng)`, `weights`, `nominal_input`, `externals`, `advance`. All world randomness comes from the seed, so every method sees the same world.
  - `Solver`: one method. `act(obs) -> (U for all agents, info)`.
    - Methods without identification (Ours, PCCA, Reciprocal) read only `obs.local(i)`, a `LocalView`. It holds agent i's own state, nominal input and weight; the bodies it senses, each as an anonymous track with position and last velocity; and public constants. A test runs these methods on a proxy that exposes nothing else.
    - Track ids are a per-run random permutation (`Log.meta['tracks']`), so an id does not reveal team membership.
    - The privileged fields of `Observation` (`index`, `external`, `ext_*`, others' `u_nom` and `weights`) are for Tan and the oracle, which identify outsiders and communicate. RiskRatio also uses them, because its paper assumes global observation of positions and velocities.
  - `Analyzer`: `Log -> dict` of metrics.
  - `runner.simulate`: the closed loop, `scenario + dynamics + spec + solver -> Log`.
  - `types`: shared data types `Observation`, `Neighbour`, `Log`, `Affine`.
- `dynamics/`: `SingleIntegrator` (`||u|| <= 1.2` as 8 half-planes).
- `specs/`: `PairwiseBarrier` (Example 9.1, `kappa = 2`, `rho = 1`, sensing range 5).
- `scenarios/`: `CircleArena` plus the presets `S1`–`S4` (Sec. 12.1).
- `solvers/`:
  - `Reciprocal`: fixed half split, exact-penalty slack `M = 1000`.
  - `thermo/` (Ours, Sec. 11):
    - `bound.py`: the certified bound `A` on 400 log-spaced theta values in `[1e-4, 50]`, with closed-form MGFs.
    - `belief.py`: the temperature belief (tau in {1e-4, 1e-2, 1e-1, 1, inf}, prior 0.03 on inf, window 50).
    - `solver.py`: the room `R_ik = A[max(c_k, r_ik)]`, the QP with one layer and one wall row per neighbour, and costate reading from i's replica.
    - Exchange, `law='follow'` (default): `r_ik -= step (lam_i - w_ik(f) lam_hat_k)`.
      - `w_ik(f)` is i's posterior mass on the following (finite-tau) hypotheses.
      - Under exact replicas the copies drift to `r_ik + r_ki <= 0`. This is **not** the cautious direction: Prop. 2.7 needs `r_ik + r_ki >= 0` (the allowances `a = -sum r` must fit in the budget). A negative gap is covered only through the coverage term (v40 Remark 5.3).
      - `law='plain'` is v40 Sec. 11 as written.
    - Step: `step='half_ke'`, i.e. `1/(2 ke) = 0.025` (default, **used in all grid runs**; v40 Sec. 11). This is the non-overshoot step: the pair's costate difference is 2 ke-Lipschitz in the agreement, and the weight `w_ik(f) <= 1` only lowers that constant.
      - `step='kappa'` (`kappa dt = 0.04`) is kept as an option only.
      - The step of the earlier batch runs (noted as "0.2Δd") is unknown and is not used here.
    - The following prior `w0` (default 0.97) is swept over {1, 0.99, 0.97, 0.9} in the grid.
  - `Oracle`: one central QP over all team inputs, with full pair constraints and externals covered at `v_env`; every row has an exact-penalty slack.
  - `Tan`: arXiv:2404.07571, sparse form, Eq. (18).
    - Default update: the time-varying law, Eq. (26), with `sign` replaced by `sat` (slope 10 on ±0.1). This is the paper's own safe-control setting, Sec. VIII-B, with `k0 = 1`.
    - `tan_gradient` uses the static law, Eq. (21), instead.
    - Variables `y` and multipliers are exchanged among team pairs.
    - Externals are identified and covered at `v_env`.
  - `PCCA`: arXiv:2012.10261 Eq. (18)-(19) and arXiv:2008.12092 Eq. (21), at relative degree one.
    - Each agent keeps copies `u_ij` of every sensed body.
    - Corrector `w_j = u_j - u*_ij` with a one-step delay.
  - `RiskRatio`: arXiv:2305.13467 Eq. (3)-(7), deterministic (CVaR term = 0).
    - Responsibility share `omega_ik = R_k/(R_i+R_k)`.
  - `make_solver(name)` builds any solver from its name (`'ours_eps0.2'` etc.).
- `analyzers/`:
  - `Cost`: mean of `f_i`.
  - `Safety`: minimum distance and violation fraction, toward externals (`< 0.95 rho`) and among agents (`< rho`).
  - `AgreementGap`: `r_ik + r_ki` over team agreements. It reports the max of `|.|` and the most negative value.
  - `PriceImbalance` (S1):
    - Score: `|mu_i - mu_k|/(mu_i + mu_k)`, averaged per isolated encounter.
    - Isolated encounter: a run of steps where i's only active price is toward k and k's only active price is toward i.
    - Reported overall, and split into equal- and different-weight pairs.
    - Every solver reports `info['mu'][(i, track)]`: `ke p` for Ours and the QP multiplier for the others.
- `scenarios/encounter.py`: hand-placed encounters (fixed goals, constant-velocity externals), used to reproduce the papers' examples.
- `validation.py`: reproductions of the reference papers' claims; each check returns the measured value and pass/fail.
- `utils/qp.py`: small dense QP using Goldfarb-Idnani active-set (`quadprog`), with SLSQP as a fallback.

## Conventions and readings of v40

- **External heading noise:** 2 rad/sqrt(s) in S2–S4. The table is garbled for S2.
- **S2 avoidance:** each external adds `sum (q - p)/|q - p|^2` over bodies within distance 2 to its heading, then renormalises to its speed.
- **Targets:** uniform on the circle, at least one radius away from the agent. A new target is drawn when the agent is within 0.2 of the current one.
- **Violation fraction:** the fraction of steps in which *some* pair is below 0.95 rho, toward externals and among agents alike.
- **S1 `v_env`:** S1 has no externals, so `v_env` is set to 1.2 (the agents' own capability). It enters only the tau = inf hypothesis.

### Ours: readings of Sec. 11

These are choices made where v40 is open or ambiguous.

- **Costate:** `lam = ke * max(0, eps - s)`, the layer penetration of the QP, per pair. The estimated costate of k uses the observed `g_k(u_k)` and the replicated room `R_ki = A_{w_ki}[max(c_i, -r_ik)]`.
  - Here `w_ki` is k's belief about i, rebuilt by i from i's own approach speeds.
  - Team copies therefore stay exactly opposite (gap ~1e-15).
- **Linearisation `y = a u_bar + b`:** this is derived from the QP along the pair axis with unit weight.
  - Layer: `a = 1/(1 + ke alpha^2)` and `b = -ke alpha (eps + R - kappa h/2)/(1 + ke alpha^2)`.
  - v40 writes `a = alpha^2/(alpha^2 + ke)`; that formula is **not** used here.
  - Wall: `a = 0` and `b = (kappa h/2 - R)/alpha`.
  - The regime used is that of the *modelled responder* (k's replicated slack for i's belief about k).
- **Finite-tau predictive:** `c ~ N(min(alpha m - kappa h/2, r), alpha^2 (tau + v + sigma_o^2))`. The excess over `r` is `Bernoulli(Pr(c > r)) * Exp(M/tau)`.
- **Lifetime of agreements and windows:** they are created when a body enters sensing range and dropped when it leaves. Bodies are tracked by an anonymous id; the external flag is never read. Agreements are not clamped.

### Baselines: adaptations

All baselines use the same exact-penalty slack `M = 1000` on every safety row.

- **Tan:**
  - The constant `-kappa h` is split half-and-half between the two agents of a pair (the paper leaves `b^m` unassigned).
  - When an agent's local QP needs a slack (Slater, Assumption 3, fails), it reports no multipliers that step and its pairs' `y` are held. Otherwise the multipliers saturate at `M` and `y` diverges.
  - With the worst-case cover of non-yielding externals (S4), the local QP can stay infeasible for seconds. The slack then lands on team rows, and teammates can collide. This is observed and is not patched.
- **PCCA:**
  - Unit weights in the cost, as in Eq. (18). Others' weights are unknown to the host, so S1's weights do not enter PCCA's decisions; they still enter its measured cost.
  - The input polytope bounds only the agent's own input `u_ii`; copies are unbounded, which keeps the paper's feasibility argument.
  - Constraints among sensed bodies use each unordered pair once.
- **RiskRatio:**
  - `R_i` sums over the bodies within sensing range. The paper sums over all agents, which it assumes are all observed.
  - `c = 2 r_s (2 u_max) + kappa r_s^2 + 1`, the smallest constant that keeps `L_ik > 0` within sensing range `r_s`. The paper gives no value, and `c` does shift the ratio.
  - The paper's box input bound is replaced by the benchmark's 8-face polytope.

### Source check

The original PDFs are in `ref_notes/baselines/`. The code was checked against them; the equation numbers above refer to these versions.

- Tan: TAC version.
- PCCA: arXiv:2012.10261. The 2008.12092 equations, Eq. (21) and Prop. 1, are cited from the arXiv HTML only.
- Risk ratio: IROS version.

### Experimental exchange options (Ours; defaults unchanged)

`make_solver` name suffixes, e.g. `ours_eps0.1_mutual_region_iso_proj`. Results are in `results/` (`s1_price_region.md`, `s1_memory*.md`, `grid_{region,mutual,iso,proj}.jsonl`, `theory_checks.md`).

**Exchange laws**
- `_plain`: the v40 law, without the following weight.
- `_mutual`: both copies move by `w_ik(f) w_ki(f) · step · (λ_i − λ̂_k)`, so `r_ik + r_ki = 0` exactly.

**Step rules**
- `_s<x>`: scale the step by x.
- `_newton`: local-curvature step.
- `_region`: trust-region step, `D/(k_e(ā_i+ā_k))` clipped to the distance to the next regime breakpoint.
- `_iso`: use the fast `ā` only for isolated pairs, and cap the move by the speed headroom.
- `_damp`: divide the move by the number of active rows. Not replicable by the neighbour.

**Agreement bounds and memory**
- `_proj`: project `r_ik` onto `[U_ki − G_k, G_i − U_ik]`.
- `_mem`, `_mem<s>`: keep `r_ik` across exits (assumes re-identification), forever or for s seconds.

**Numerical symmetry.** Each agent computes its own slack for the exchange with the same expression its neighbour uses for the replica. This keeps the pair's numbers bitwise identical across regime switches and clipping, which the fast steps need.

**Summary (6 seeds × 120 s).**
- Fast steps equalise S1 prices: settled imbalance between agents with weights 1 vs 3 drops from 0.43 to 0.08–0.21.
- They lose part of the default step's safety in S2–S4.
- Isolation recovers most of it, but S4 violations toward externals stay at 2.7–3.6%, against 0.17–1.33% with the default step.
- Projection barely binds.
- Memory gives no gain.
