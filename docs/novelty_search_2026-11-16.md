# Novelty search, 2026-11-16 (arXiv only)

Compared against: `ref_notes/v43/paper_v43.txt` (read locally, never sent anywhere).

Method of search: the arXiv export API (Atom) with generic technical terms only, plus public author names in `au:` for the three named papers. 72 API requests in total, including 4 `id_list` look-ups (some over the planned budget; see the query list). 7 PDFs were downloaded from arxiv.org/pdf and read with `pdftotext`. Every title, author list, year and id below comes from the arXiv record or the PDF. "Year" is the arXiv v1 submission year unless stated otherwise.

Evidence levels:
- **PDF read**: the relevant sections of the PDF were read.
- **abstract only**: only the arXiv abstract was read.
- **inferred**: the claim goes beyond the text that was read. It is flagged where it occurs.

Short reminder of the v43 ingredients compared below:
- (A) local problem `min beta_i f_i + sum_k Psi(s_ik)` with room `R_ik`.
- (B) `R_ik` is an EVaR bound under the agent's Bayesian belief about the neighbour, including whether it follows the convention.
- (C) the costate `lambda = -Psi'(s)` is read from the observed slack, the neighbour's costate is replicated from its observed action, and the pairwise agreements `r_ik` are updated without messages.
- (D) `beta_i` is the costate of the paid cost `W_i`, from a log-sum-exp (softmax) smoothing of the min-max fairness constraint ("equality of burden").

---

## Q1. Splitting a coupled constraint without messages by reading prices/duals from observed actions or physical signals

| Paper title | Authors | Year | arXiv id + link | Overlap with v43 | What novelty remains for us | Evidence |
|---|---|---|---|---|---|---|
| Design and Stability of Load-Side Primary Frequency Control in Power Systems | Changhong Zhao, Ufuk Topcu, Na Li, Steven Low | 2013 (PDF: "IEEE Trans. on Automatic Control, 2014 to appear") | [1305.0585](https://arxiv.org/abs/1305.0585) | **Strong conceptual overlap with (C).** A coupled constraint (network power balance) is met by agents that use no explicit communication. The swing dynamics act as a distributed primal-dual algorithm. The PDF states that "the frequency deviations ω_j(t) emerge as the Lagrange multipliers of OLC" and that local frequency "conveys exactly the right information about the global power imbalance". This is "price read from an observed quantity, no messages, and the equilibrium is the central optimum". | Their price is produced by the physics: a common frequency (one network-wide multiplier at steady state). There is no agent-held agreement, no pairwise split, and no reading of a *specific neighbour's* costate from that neighbour's slack. The setting is deterministic. There is no probabilistic certificate and no agent that breaks the rule. Our v43 Prop. "locality of readable prices" (a group-wide common price cannot be read locally without messages) is the opposite regime, which is a useful contrast to state. **We cannot claim "first to read the multiplier without communication"; we must cite this line.** | PDF read |
| Decentralized Primary Frequency Control in Power Networks | Changhong Zhao, Steven Low | 2014 | [1403.6046](https://arxiv.org/abs/1403.6046) | Same idea extended to generators plus loads with nonlinear flows. The control is a function of local frequency deviation only, and "no explicit communication" is needed. In the KKT proof the equilibrium frequency ω* equals the multiplier λ of power balance. | Same as above: the price is a physical common signal, the setting is deterministic, there is no pairwise agreement, no belief and no risk bound. | PDF read |
| Distributed optimization decomposition for joint economic dispatch and frequency regulation | Desmond Cai, Enrique Mallada, Adam Wierman | 2016 | [1605.07910](https://arxiv.org/abs/1605.07910) | Frequency regulation is framed as part of a decomposition of economic dispatch, a frequency-as-dual line of work. | Same physical-common-price regime. The abstract suggests a partly communicated slow layer (inferred). | abstract only |
| Inverse Safety Filtering: Inferring Constraints from Safety Filters for Decentralized Coordination | Minh Nguyen, Jingqi Li, Gechen Qu, Claire J. Tomlin | 2026 | [2604.02687](https://arxiv.org/abs/2604.02687) | **Strong overlap with the framing of (C).** It inverts the KKT stationarity of another agent's CBF-QP safety filter (Δu = λ∇_u h) from observed actions, "implicitly communicating safety constraints through actions", "without direct communication". Its scope is multi-agent, decentralized and CBF-based. | They infer a *constraint parameter* (obstacle position θ), not a multiplier used to split a shared constraint. They need the neighbour's *nominal* action as well as the filtered one (Problem formulation in Sec. III-B), a round-robin demonstrator/learner schedule known to all (Assumption VI.1), and only the demonstrator acts on private information. The setting is deterministic: no belief over whether others comply, no risk level, no allocation or optimality of the split, no fairness. **Partial overlap: we must position against it. "Reading the KKT of a neighbour's filter from its action, without messages" is no longer new by itself.** | PDF read |
| A continuous-time violation-free multi-agent optimization algorithm and its applications to safe distributed control | Xiao Tan, Changxin Liu, Karl H. Johansson, Dimos V. Dimarogonas | 2024 | [2404.07571](https://arxiv.org/abs/2404.07571) | Splits coupled linear (CBF) constraints with auxiliary decoupling variables, which is primal decomposition, the same structure as our agreements `r_ik`. v43 Thm (iii) says our law reduces to theirs when costates are communicated. | They use communication over a network (sensitivity and subgradient from neighbours). They have no belief, no risk certificate and no rule-breaking agents. Our novelty claim is "the same decomposition without messages and with certified rooms", which is plausible but depends on the assumption of public beliefs and exact observation. | abstract only |
| Achieving violation-free distributed optimization under coupling constraints | Changxin Liu, Xiao Tan, Xuyang Wu, Dimos V. Dimarogonas, Karl H. Johansson | 2024 | [2404.07609](https://arxiv.org/abs/2404.07609) | Same family: distributed optimization with coupling constraints and no violation. | Uses communication. Deterministic. | abstract only |
| Risk-aware Safe Control for Decentralized Multi-agent Systems via Dynamic Responsibility Allocation | Yiwei Lyu, Wenhao Luo, John M. Dolan | 2023 | [2305.13467](https://arxiv.org/abs/2305.13467) | Splits a pairwise CBF constraint into responsibility shares "without direct communications", using observed positions and velocities of all agents (PDF Sec. on problem setup). This is our "Risk ratio" baseline. | The share is a heuristic ratio of aggregate CBF-inspired risk, not a multiplier read from a slack. There is no exchange law, no optimality (equal-price) result, no belief over compliance, and the CVaR is on Gaussian motion noise (see Q2). | PDF read (partial: setup, risk and share sections) |
| Learning Responsibility Allocations for Safe Human-Robot Interaction with Applications to Autonomous Driving | Ryan K. Cosner, Yuxiao Chen, Karen Leung, Marco Pavone | 2023 | [2303.03504](https://arxiv.org/abs/2303.03504) | "Assumed responsibility allows interacting agents to maintain safety without explicit coordination". Responsibility-aware CBFs whose allocations are learned from data. | Allocations are learned offline from data. There is no online price reading, no exchange and no certification under a belief. | abstract only |
| Learning responsibility allocations for multi-agent interactions: A differentiable optimization approach with control barrier functions | Isaac Remy, David Fridovich-Keil, Karen Leung | 2024 | [2410.07409](https://arxiv.org/abs/2410.07409) | Infers responsibility allocations from observed behaviour through the CBF-QP (differentiable optimization), which is inference of the split from actions. | Offline and data-driven. No online agreement dynamics, no risk certificate, no handling of rule-breakers. | abstract only |
| Constraint Learning in Multi-Agent Dynamic Games from Demonstrations of Local Nash Interactions | Zhouyu Zhang, Chih-Yuan Chiu, Glen Chou | 2025 | [2508.19945](https://arxiv.org/abs/2508.19945) | Inverse KKT of multi-agent games: learns constraints from observed equilibrium interactions. | Offline (MILP over a demonstration dataset). Learns constraints, not shares or prices. | abstract only |
| Safety Barrier Certificates for Heterogeneous Multi-Robot Systems | Li Wang, Aaron Ames, Magnus Egerstedt | 2016 | [1609.00651](https://arxiv.org/abs/1609.00651) | Decentralized minimally invasive CBF collision avoidance. This is the source of the classical fixed split (our "Reciprocal" baseline). | Fixed split, no prices, no belief. | abstract only |

**Q1 verdict.** Two parts of (C) have prior art. "No messages, multiplier carried by an observed quantity" is established in power systems (Zhao/Low line). "Inverting a neighbour's CBF-QP KKT from its observed action" is established in 2026 (Nguyen et al.). We found no arXiv paper that does all of the following: reads a specific neighbour's costate from its observed slack, replicates the neighbour's room from public beliefs, and updates a conserved pairwise agreement to reach the equal-price (central-optimum) split without messages. Our novelty is that combination and its guarantees (conservation, energy descent, equal-price equilibrium). It is not the concept "price without communication".

---

## Q2. Bayesian belief over whether a neighbour cooperates or is rational, combined with a risk measure or chance constraint, to certify safety

| Paper title | Authors | Year | arXiv id + link | Overlap with v43 | What novelty remains for us | Evidence |
|---|---|---|---|---|---|---|
| Probabilistically Safe Robot Planning with Confidence-Based Human Predictions | Jaime F. Fisac, Andrea Bajcsy, Sylvia L. Herbert, David Fridovich-Keil, Steven Wang, Claire J. Tomlin, Anca D. Dragan | 2018 | [1806.00109](https://arxiv.org/abs/1806.00109) | **Strong overlap with (B).** Real-time Bayesian update (Eq. 5) of a belief over the Boltzmann rationality coefficient β ("model confidence"), driven by the observed human action. The predictions widen when the human does not follow the model. Planning is under a collision-probability threshold P_th (Eq. 4d, 1% in experiments). | One robot and one human. The robot takes all the avoidance and the human holds no share or agreement. The belief is over a continuous rationality coefficient, not a "follows the convention" hypothesis set. Safety is a chance constraint over reachable-set predictions with tracking-error bounds, not EVaR/KL-ball. There is no subadditive per-neighbour certificate, no split and no dual. **We cannot claim "first to use a Bayesian belief over the other agent's rationality for probabilistic safety".** | PDF read |
| Safety Assurances for Human-Robot Interaction via Confidence-aware Game-theoretic Human Models | Ran Tian, Liting Sun, Andrea Bajcsy, Masayoshi Tomizuka, Anca D. Dragan | 2021 | [2109.14700](https://arxiv.org/abs/2109.14700) | Infers "the degree to which a human is following the game-theoretic interaction model" (latent rationality and influence) and uses it to restrict the human's feasible controls in a safety monitor. This is close to our w(F), the "following mass". | A safety monitor (reachability) rather than a risk-measure room. The robot does not share a constraint with a cooperating peer. No exchange or agreements. | abstract only |
| Trust-based Rate-Tunable Control Barrier Functions for Non-Cooperative Multi-Agent Systems | Hardik Parwana, Dimitra Panagou | 2022 | [2204.04555](https://arxiv.org/abs/2204.04555) | Each agent forms "its own belief of how cooperative other agents are" (a trust metric) and adapts its CBF class-K rate. This is a multi-agent CBF with cooperative and non-cooperative agents. | Trust is a deterministic metric, not a Bayesian posterior. There is no probability level or risk measure. Assumption 1 assumes all agents observe the combined state (described as complete communication topology). No split optimality. | PDF read (partial: intro, assumptions, trust section headers) |
| Risk-aware Safe Control for Decentralized Multi-agent Systems via Dynamic Responsibility Allocation | Yiwei Lyu, Wenhao Luo, John M. Dolan | 2023 | [2305.13467](https://arxiv.org/abs/2305.13467) | CVaR (α=0.95) of Gaussian motion noise inside a pairwise CBF, a risk-aware decentralized split without communication. | The risk is over additive motion noise with known mean and covariance, not over the neighbour's type or compliance. No Bayesian update. The paper assumes the neighbour's safety margin and uncertainty distribution are "known or observable". | PDF read (partial) |
| When to Probe and When to Act: Clarity-Aware Risk-Adaptive Control for Interactive Driving | Youran Wang, Devodita Chakravarty, Yiwei Lyu | 2026 | [2611.02240](https://arxiv.org/abs/2611.02240) | Belief-space MPC over an unobservable human characteristic with a clarity-adaptive CVaR barrier. Conservatism tightens under ambiguity and relaxes as confidence grows, the same qualitative behaviour as our room shrinking with the posterior. **Very recent (Nov 2026).** | One ego vehicle, active probing, CVaR rather than EVaR. No shared-constraint split, no agreements and no dual reading. Whether "characteristic" includes cooperate vs. not is unknown from the abstract. | abstract only |
| Risk-Sensitive Motion Planning using Entropic Value-at-Risk | Anushri Dixit, Mohamadreza Ahmadi, Joel W. Burdick | 2020 | [2011.11211](https://arxiv.org/abs/2011.11211) | EVaR as the obstacle-avoidance constraint in MPC (distributionally robust form). This is prior use of EVaR for collision safety. | Randomly moving obstacles, not agents with a convention. No belief over compliance, no split. | abstract only |
| Response-Aware Risk-Constrained Control Barrier Function With Application to Vehicles | Qijun Liao, Jue Yang | 2026 | [2603.24598](https://arxiv.org/abs/2603.24598) | CVaR-constrained CBF with Bayesian (inverse-Wishart) online learning and per-step probabilistic safety bounds. | Single vehicle and model mismatch. No other agents. | abstract only |
| Multi-Robot Collision Avoidance under Uncertainty with Probabilistic Safety Barrier Certificates | Wenhao Luo, Wen Sun, Ashish Kapoor | 2019 | [1912.09957](https://arxiv.org/abs/1912.09957) | Chance-constrained multi-robot CBF under measurement and motion uncertainty. | No belief over compliance, no prices. | abstract only (truncated) |

**Q2 verdict.** Each piece exists separately:
- Bayesian belief over whether the other follows the model, used for probabilistic safety (Fisac 2018; Tian 2021).
- Trust/cooperativeness in multi-agent CBFs (Parwana 2022).
- CVaR/EVaR in barrier or MPC constraints (Lyu 2023; Dixit 2020; Wang 2026).

We found no arXiv paper that combines a posterior over "follows the convention vs. not" with an EVaR room whose subadditivity certifies a constraint shared with several neighbours, and that also feeds that room into a price exchange. This is **partial overlap per ingredient, novel as a combination** (subject to the search limits below).

---

## Q3. Equalising burden or fairness in multi-robot CBF or resource allocation by accumulated cost, with min-max or softmax weights

| Paper title | Authors | Year | arXiv id + link | Overlap with v43 | What novelty remains for us | Evidence |
|---|---|---|---|---|---|---|
| A Fairness-Oriented Control Framework for Safety-Critical Multi-Robot Systems: Alternative Authority Control | Lei Shi, Qichao Liu, Cheng Zhou, Xiong Li | 2024 | [2409.10749](https://arxiv.org/abs/2409.10749) | Fairness in multi-robot CBF control by dynamically rotating "control authority". | Discrete authority assignment. No cost-weighting multiplier, no accumulated-cost log-sum-exp. A coordinating allocator is likely (inferred). | abstract only |
| Fair and Safe: A Real-Time Hierarchical Control Framework for Intersections | Lei Shi, Yongju Kim, Xinzhi Zhong, Wissam Kontar, Qichao Liu, Soyoung Ahn | 2025 | [2511.05886](https://arxiv.org/abs/2511.05886) | Inequity aversion that uses **control history** and waiting time in a utility for allocating authority, combined with an HOCBF safety filter. This is history-aware fairness with CBFs. | Centralized allocation module and a discrete choice of one vehicle. There is no private per-agent multiplier and no min-max or softmax derivation. | abstract only |
| Exact Feasibility Certification and Optimal Responsibility Allocation for Multi-Robot CBF Safety Filters | Chandan Kumar Sah, Jishnu Keshavan | 2026 | [2609.14935](https://arxiv.org/abs/2609.14935) | Allocates shared CBF constraints by **maximizing the worst local feasibility margin**, a min-max over agents solved as an LP. | Min-max over an instantaneous feasibility margin, not over accumulated paid cost. It appears to be a central LP (inferred). No messages-free reading. | abstract only |
| Time-To-Reach Separation and Safety Filtering for Safe, Fair, and Efficient Multi-Agent Coordination | Matthew Low, Jasmine Jerry Aloor, Victoria Marie Tuck, Pierluigi Nuzzo, Jason J. Choi | 2026 | [2605.20625](https://arxiv.org/abs/2605.20625) | Fairness metric together with a priority-consistent safety filter. | Priorities come from time-to-reach, not from accumulated cost. HJ filter. | abstract only |
| Decentralized Social Navigation with Non-Cooperative Robots via Bi-Level Optimization | Rohan Chandra, Rahul Menon, Zayne Sprague, Arya Anantula, Joydeep Biswas | 2023 | [2306.08815](https://arxiv.org/abs/2306.08815) | A "fair and collision-free ordering" in a decentralized setting. | Ordering or priority, not a cost multiplier. No accumulated burden. | abstract only |
| FACA: Fair and Agile Multi-Robot Collision Avoidance in Constrained Environments with Dynamic Priorities | Jaskirat Singh, Rohan Chandra | 2025 | [2511.14024](https://arxiv.org/abs/2511.14024) | Fair multi-robot collision avoidance. | Communicates in natural language. Potential fields. No multiplier. | abstract only |
| Multi-Path Alpha-Fair Resource Allocation at Scale in Distributed Software Defined Networks | Zaid Allybokus, Konstantin Avrachenkov, Jérémie Leguay, Lorenzo Maggi | 2018 | [1809.01050](https://arxiv.org/abs/1809.01050) | Fairness through dual and distributed methods in resource allocation (α-fair). | Instantaneous-rate fairness with communicated prices. No accumulated-cost memory. | abstract only |
| Non Normalized Shared-Constraint Dynamic Games for Human-Robot Collaboration with Asymmetric Responsibility | Mark Pustilnik, Francesco Borrelli | 2025 | [2512.08688](https://arxiv.org/abs/2512.08688) | Unequal effort on a shared constraint through a non-normalized GNE: per-player scaling of the shared-constraint multiplier, mathematically close to our per-agent weight β_i on cost versus a common price. | The weights are a design choice, not driven by accumulated cost and not derived from min-max. Receding-horizon game, presumably with full knowledge (inferred). | abstract only |

**Q3 verdict.** We found no arXiv paper in multi-robot CBF that sets a per-agent cost weight β_i = softmax of accumulated paid cost, derived as the multiplier of a min-max (log-sum-exp-smoothed) fairness constraint, without messages. History-aware fairness (Shi et al. 2025) and min-max allocation (Sah and Keshavan 2026) exist. The log-sum-exp/softmax smoothing of a max and the "Gibbs weights" are textbook. Fairness through accumulated service is classic in scheduling (proportional-fair scheduling, Lyapunov virtual queues), which this search did not cover; see the last section. **Treat (D) as a modest, combination-level contribution.** Do not call softmax-of-accumulated-cost new in general.

---

## Q4. Responsibility-split or responsibility-allocation CBF papers, 2025–2026

| Paper title | Authors | Year | arXiv id + link | Overlap with v43 | What novelty remains for us | Evidence |
|---|---|---|---|---|---|---|
| Auction-Based Responsibility Allocation for Scalable Decentralized Safety Filters in Cooperative Multi-Agent Collision Avoidance | Johannes Autenrieb, Mark Spiller | 2025 | [2510.21546](https://arxiv.org/abs/2510.21546) | Allocates pairwise CBF enforcement asymmetrically among neighbours based on control-effort estimates. Decentralized HOCBF. | Agents "exchang[e] lightweight cost bids", so it needs communication. Without a link it falls back to assuming the neighbour's a_j = 0 (PDF Sec. 4). The responsibility graph is directed and binary, with no continuous split or price. No belief or risk. | PDF read (partial) |
| Combinatorial Safety-Critical Coordination of Multi-Agent Systems via Mixed-Integer Responsibility Allocation and Control Barrier Functions | Johannes Autenrieb, Mark Spiller, Hyo-Sang Shin, Namhoon Cho | 2026 | [2603.05762](https://arxiv.org/abs/2603.05762) | Assigns collision-avoidance responsibilities (an MILP coordination layer), then each agent solves a local QP. | A combinatorial coordination layer; a coordinator or communication is likely (inferred). Binary assignment. No belief or risk. | abstract only |
| Capability-Aware Heterogeneous Control Barrier Functions for Decentralized Multi-Robot Safe Navigation | Joonkyung Kim, Yanze Zhang, Wenhao Luo, Yiwei Lyu | 2026 | [2604.13245](https://arxiv.org/abs/2604.13245) | Decentralized, capability-aware distribution of pairwise avoidance responsibility (support-function capability metric) with feasibility clipping. | The split is set by a capability ratio, not by prices or optimality. The abstract does not say whether communication is used. No belief over compliance, no fairness over time. | abstract only |
| Exact Feasibility Certification and Optimal Responsibility Allocation for Multi-Robot CBF Safety Filters | Chandan Kumar Sah, Jishnu Keshavan | 2026 | [2609.14935](https://arxiv.org/abs/2609.14935) | "Optimally allocate shared safety constraints" by maximizing the worst local feasibility margin (an LP). This is an optimality claim on the split. | Optimizes feasibility margin, not total cost (our equal-price equilibrium). Centralized LP (inferred). No messages-free mechanism, no belief. | abstract only |
| Non Normalized Shared-Constraint Dynamic Games for Human-Robot Collaboration with Asymmetric Responsibility | Mark Pustilnik, Francesco Borrelli | 2025 | [2512.08688](https://arxiv.org/abs/2512.08688) | Asymmetric responsibility on shared constraints through non-normalized GNE multipliers. | See Q3. A game-theoretic MPC, not a messages-free exchange. | abstract only |
| Inverse Safety Filtering: Inferring Constraints from Safety Filters for Decentralized Coordination | Minh Nguyen, Jingqi Li, Gechen Qu, Claire J. Tomlin | 2026 | [2604.02687](https://arxiv.org/abs/2604.02687) | Not a responsibility split, but the closest 2026 CBF paper on "coordination without communication through the KKT of observed filtered actions" (see Q1). | See Q1. | PDF read |
| When to Probe and When to Act: Clarity-Aware Risk-Adaptive Control for Interactive Driving | Youran Wang, Devodita Chakravarty, Yiwei Lyu | 2026 | [2611.02240](https://arxiv.org/abs/2611.02240) | Same group as the "Risk ratio" baseline. Belief plus CVaR barrier (see Q2). | Not a responsibility split. | abstract only |

Pre-2025 responsibility papers found and used as context: Lyu, Luo, Dolan 2022 "Responsibility-associated Multi-agent Collision Avoidance with Social Preferences" ([2206.09030](https://arxiv.org/abs/2206.09030), abstract only); Lyu et al. 2023 ([2305.13467](https://arxiv.org/abs/2305.13467)); Cosner et al. 2023 ([2303.03504](https://arxiv.org/abs/2303.03504)); Remy et al. 2024 ([2410.07409](https://arxiv.org/abs/2410.07409)).

**Q4 verdict.** The 2025–2026 responsibility-allocation papers fall into four groups:
- communication-based: auction bids (2510.21546).
- combinatorial or central: MILP (2603.05762) and LP (2609.14935).
- heuristic and capability-based: 2604.13245.
- game-theoretic: non-normalized GNE (2512.08688).

None reads prices from slacks without messages, certifies against agents that may not comply, or equalises accumulated burden. 2609.14935 (an optimal split) and 2604.13245 (decentralized, capability-aware) should be cited and contrasted. 2604.13245 should also be checked for whether it uses communication (we did not read its PDF).

---

## The three named papers

### 1. "Zhao and Low 2014": frequency as the Lagrange multiplier

Two arXiv records match. Neither PDF prints the published venue on its first page, except the TAC note.

- **Exactly "Zhao and Low", 2014:** *Decentralized Primary Frequency Control in Power Networks*, Changhong Zhao and Steven Low, arXiv [1403.6046](https://arxiv.org/abs/1403.6046) (v1, 24 Mar 2014, cs.SY). **PDF read.**
  - Generator and load control are functions of local frequency deviation only.
  - "No explicit communication or information of system parameters is required" (Sec. III).
  - Theorem 1 shows that any closed-loop equilibrium solves the OFC problem (min generation cost + user disutility s.t. network power balance). In its proof the equilibrium frequency ω* coincides with the multiplier λ of the power-balance constraint (KKT eqs. (14)–(23)).
  - The published venue is not printed on the arXiv PDF and is **not verified** here.
- **The paper that states "frequency = Lagrange multiplier" verbatim:** *Design and Stability of Load-Side Primary Frequency Control in Power Systems*, Changhong Zhao, Ufuk Topcu, Na Li, Steven Low, arXiv [1305.0585](https://arxiv.org/abs/1305.0585) (v1 May 2013, v3 4 Dec 2013). The PDF footnote says "IEEE Trans. on Automatic Control, 2014 to appear". **PDF read.** The abstract says the swing dynamics with frequency-based load control "serve as a distributed primal-dual algorithm" and that "the local frequency deviations at each bus convey exactly the right information about the global power imbalance". Remark 4) says "the frequency deviations ω_j(t) emerge as the Lagrange multipliers of OLC" and "branch flow deviations P_ij(t) emerge as the Lagrange multipliers of DOLC". It has four authors, so if the intended citation is the TAC paper, cite it as Zhao, Topcu, Li and Low (2014), not "Zhao and Low".

**How v43 differs:**
1. Their multiplier is a physical, network-wide quantity, a single λ at steady state, that the dynamics compute. Ours is computed by each agent from its own slack and replicated per contact. Our v43 Prop. "locality of readable prices" says such a common group price is exactly what cannot be read locally without a physical carrier.
2. They have no agreements r_ik and no conservation across a contact.
3. They are deterministic, with no belief, no δ-certificate and no rule-breaking loads. Our "external load" is loosely analogous to their uncontrolled load step, but they have no compliance hypothesis.
4. They have no fairness over time.

**Risk:** a reviewer will say "price without communication = Zhao et al.". We must cite it and stress that in CBF collision avoidance there is no physical carrier like frequency, so the price has to be reconstructed from the neighbour's action under public rules.

### 2. Claire Tomlin's group, 2026: inverse inference from KKT conditions

*Inverse Safety Filtering: Inferring Constraints from Safety Filters for Decentralized Coordination*, Minh Nguyen, Jingqi Li, Gechen Qu, Claire J. Tomlin, arXiv [2604.02687](https://arxiv.org/abs/2604.02687) (v1, 3 Apr 2026, eess.SY). **PDF read** (Secs. I–VI).

This is the only 2026 paper by this group about KKT-based inverse inference among the 40 most recent `au:Tomlin` records. Contents:
- KKT stationarity of the discrete-time CBF-QP, Δu = u_safe − u_nom = λ∇_u h. This gives a closed form for the obstacle parameter θ (Thm IV.1).
- Identifiability conditions (λ>0, rank conditions; Thm IV.2) and global uniqueness for quadratic barriers (Cor. IV.3).
- A Newton solver with convergence when formation constraints are also active (Thm V.1).
- Round-robin decentralized inference and planning with a safety guarantee (Thm VI.2).
- Hardware tests on quadrupeds.

**How v43 differs:**
1. **Target of inference.** They infer the *constraint* (an obstacle's θ), which is a learning or information-sharing problem. We read the *multiplier or costate* of a constraint whose form is public, in order to split it.
2. **Observability.** They need the neighbour's nominal action u_nom as well as u_safe. We need only the observed term c_k(u_k), the public rule and our own agreement number.
3. **Coordination structure.** They use a common round-robin demonstrator/learner schedule known to all (Assumption VI.1). We use simultaneous action with a conserved pairwise agreement and an exchange law (energy descent, equal-price equilibrium).
4. **Uncertainty.** They are deterministic and assume teammates are cooperative. We use a Bayesian posterior over compliance and an EVaR room with a δ-certificate, and a non-follower is treated as a load.
5. They have no fairness term.

**Overlap to acknowledge:** "no messages; read the KKT of the neighbour's CBF filter from its observed action" is their stated idea (they call it implicit communication through actions). Our intro must not present that idea as new.

### 3. Fisac et al. 2018

Verified: *Probabilistically Safe Robot Planning with Confidence-Based Human Predictions*, Jaime F. Fisac, Andrea Bajcsy, Sylvia L. Herbert, David Fridovich-Keil, Steven Wang, Claire J. Tomlin, Anca D. Dragan, arXiv [1806.00109](https://arxiv.org/abs/1806.00109) (v1, 31 May 2018, cs.RO). **PDF read** (abstract, Secs. III–IV). The venue is not printed on the arXiv PDF and is not verified here.

Contents:
- A Boltzmann noisy-rational human model with coefficient β, called "model confidence".
- A real-time Bayesian update b_{t+1}(β) ∝ P(u_H | x_H; β, θ) b_t(β) from the observed human action (Eq. 5).
- A constrained planning problem with collision probability ≤ P_th (Eq. 4; 1% in experiments), combined with worst-case tracking-error bounds (FaSTrack) for a quadcopter.

**How v43 differs:**
1. They have one robot that takes all responsibility and a human that does not cooperate on a shared constraint. We have peers that share the constraint, hold agreements and exchange prices.
2. Their belief is over a continuous rationality parameter that scales prediction spread. Ours is over a hypothesis family with a "follows the convention" subset F, and the following mass w(F) also discounts the neighbour's price (estimated price ≤ w(F)·price).
3. Their safety is a collision-probability threshold over forward predictions. Ours is an EVaR (KL-ball) bound with subadditivity, so per-neighbour marginal beliefs certify a constraint shared with several neighbours without any dependence assumption.

**Overlap to acknowledge:** "Bayesian confidence in whether the other agent follows the model, which widens the safety margin and yields a probabilistic certificate" is theirs. Tian et al. 2021 ([2109.14700](https://arxiv.org/abs/2109.14700)) extends it to game-theoretic models.

---

## Exact queries used (arXiv API `search_query`, in order)

```
1  au:Zhao AND au:Low AND ti:frequency
2  au:Tomlin                                   (sortBy=submittedDate, 40 results)
3  au:Fisac AND ti:confidence
4  abs:"control barrier" AND abs:"without communication" AND abs:multi
5  abs:"dual decomposition" AND abs:"without communication"
6  abs:"control barrier function" AND abs:communication AND abs:responsibility
7  abs:"responsibility allocation" AND abs:"barrier"                     (sortBy=submittedDate)
8  abs:"responsibility" AND abs:"control barrier" AND abs:"multi-agent"  (sortBy=submittedDate)
9  ti:responsibility AND abs:"collision avoidance"                       (sortBy=submittedDate)
10 [id_list] 2604.13245,2510.21546,2609.14935,2603.05762,2512.08688,2305.13467
11 abs:"implicit coordination" AND abs:"barrier"
12 abs:"implicit communication" AND abs:"multi-agent" AND abs:safety
13 abs:"dual variable" AND abs:"observed" AND abs:"without communication"
14 abs:"communication-free" AND abs:"distributed optimization"
15 abs:"Lagrange multiplier" AND abs:"locally measurable"
16 abs:implicit AND abs:coordination AND abs:"control barrier"
17 abs:"implicit communication" AND abs:robots
18 abs:decentralized AND abs:"control barrier" AND abs:communication AND abs:"dual"
19 abs:price AND abs:"without communication"
20 abs:"coupled constraint" AND abs:"without communication"
21 au:Tan AND au:Dimarogonas AND abs:barrier
22 abs:"control barrier" AND abs:distributed AND abs:"constraint splitting"
23 abs:frequency AND abs:"Lagrange multiplier" AND abs:load AND abs:"no communication"
24 abs:"local frequency" AND abs:price AND abs:"demand response" AND abs:decentralized
25 abs:"control barrier" AND abs:"non-cooperative" AND abs:estimat AND abs:responsibility
26 abs:"control barrier" AND abs:cooperative AND abs:"uncooperative" AND abs:"online"
27 abs:"control barrier" AND abs:"cooperation level"
28 abs:"control barrier" AND abs:"Bayesian" AND abs:"multi-agent" AND abs:intent
29 abs:barrier AND abs:noncooperative AND abs:agents AND abs:safety AND abs:decentralized
30 abs:"barrier" AND abs:Bayesian AND abs:cooperative AND abs:agents
31 abs:"barrier" AND abs:"cooperativeness"
32 abs:"conditional value-at-risk" AND abs:"barrier" AND abs:"multi-agent"
33 abs:"control barrier" AND abs:"CVaR" AND (abs:agents OR abs:pedestrians)
34 abs:"entropic value-at-risk"
35 abs:"control barrier" AND abs:belief AND abs:"other agents"
36 abs:"control barrier" AND abs:"rationality"
37 abs:"model confidence" AND abs:"multi-agent" AND abs:safe
38 abs:"chance constraint" AND abs:Bayesian AND abs:"interaction" AND abs:"game"
39 abs:"risk" AND abs:"belief" AND abs:"uncooperative" AND abs:robots
40 abs:"distributionally robust" AND abs:"control barrier" AND abs:"multi-agent"
41 all:"confidence-aware" AND all:"game-theoretic"
42 all:"distributionally robust" AND all:"control barrier" AND all:agents
43 all:"cooperative" AND all:"adversarial" AND all:"control barrier" AND all:"belief"
44 [id_list] 2109.14700,2204.04555,2611.02240,2404.07571
45 all:fairness AND all:"control barrier"
46 all:fair AND all:"collision avoidance" AND all:"multi-robot" AND all:effort
47 all:"log-sum-exp" AND all:fairness AND all:"multi-agent"
48 all:"min-max" AND all:fairness AND all:"accumulated" AND all:cost AND all:agents
49 all:fairness AND all:"multi-robot" AND all:"collision avoidance"
50 all:"equitable" AND all:"collision avoidance"
51 all:"alpha-fair" AND all:"distributed" AND all:"dual decomposition"
52 all:fairness AND all:"long-term" AND all:"resource allocation" AND all:"Lyapunov" AND all:"virtual queue"
53 [id_list] 2511.14024,2409.10749,2511.05886,2306.08815
54 all:fairness AND all:"safety filter" AND all:agents
55 all:"cumulative cost" AND all:fairness AND all:"multi-agent" AND all:control
56 all:"burden" AND all:"multi-agent" AND all:"fair" AND all:control
57 all:"fair" AND all:"load shedding" AND all:"cumulative"
58 [id_list] 2605.20625,2410.07409,2303.03504
59 all:responsibility AND all:"barrier function"                  (sortBy=submittedDate, 30)
60 all:"responsibility" AND all:"safety filter" AND all:decentralized (sortBy=submittedDate, 30)
61 [id_list] 2603.24598
62 all:"feedback optimization" AND all:decentralized AND all:"dual" AND all:"without communication"
63 all:responsibility AND all:"online" AND all:infer AND all:"collision avoidance"
64 all:"reciprocal" AND all:"control barrier" AND all:"non-reciprocal"
65 all:"local voltage" AND all:"dual" AND all:"feedback" AND all:"reactive power" AND all:decentralized
66 all:frequency AND all:"price signal" AND all:"primal-dual" AND all:loads
67 all:"inverse game" AND all:"constraint" AND all:"online"
68 all:"generalized Nash" AND all:"shared constraint" AND all:"inverse"
69 all:"dynamic games" AND all:"infer" AND all:"constraints" AND all:"KKT"
70 au:Mallada AND all:frequency AND all:"economic dispatch"
71 all:"safety barrier certificates" AND all:"multi-robot"
72 all:"control barrier" AND all:"Lagrange multiplier" AND all:neighbors AND all:distributed
```

PDFs downloaded and read: 1403.6046, 1305.0585, 2604.02687, 1806.00109, 2305.13467 (partial), 2510.21546 (partial), 2204.04555 (partial).

---

## Could not find / could not verify

- **Many conjunctive phrase queries returned zero hits** (4, 5, 12–15, 18, 20, 22–28, 37–40, 42, 46–48, 52, 55, 57, 62, 66, 67, 72). arXiv's phrase matching on "without communication" and similar phrases is strict, so **zero hits is weak evidence of absence**, not proof of novelty.
- **No paper found** that reads a *specific neighbour's* dual/costate from its observed slack and runs a conserved pairwise agreement to the equal-price optimum without messages. Search-limited.
- **No paper found** that combines a Bayesian posterior over convention compliance with **EVaR** for multi-agent CBF or shared-constraint certification. EVaR hits were for single-agent MPC (2011.11211), finance and MDPs.
- **No paper found** that uses softmax or log-sum-exp of accumulated paid cost as a cost multiplier in multi-robot CBF. Not searched: proportional-fair scheduling, max-min fair rate control, Lyapunov drift-plus-penalty fairness. These are classic, accumulated-service fairness ideas that plausibly overlap conceptually with (D). Much of that literature predates or is outside arXiv.
- **Not searched or verified:** network congestion control, where an implicit price (loss/delay) is observed without explicit messages (Kelly-style rate control; Low–Lapsley optimization flow control). This is a strong conceptual precedent for Q1 "price from observed behaviour". These are classic papers likely not on arXiv and were not checked.
- **Zhao and Low 2014:** the published venue of 1403.6046 is not printed in the arXiv PDF and is not verified. The verbatim "frequency deviations emerge as the Lagrange multipliers" wording is in the four-author 1305.0585 (TAC, "2014 to appear" per its PDF), so it is ambiguous which one "Zhao and Low 2014" means.
- **Fisac et al. 2018:** title, authors and arXiv date verified. The publication venue is not printed on the arXiv PDF and is not verified.
- **Tomlin group 2026:** 2604.02687 is the only KKT-inverse paper among the 40 most recent `au:Tomlin` arXiv records. If a different (e.g. non-arXiv or later) paper was meant, it was not found.
- Abstract-only items should get a PDF check before being cited in the paper's related-work section, especially 2604.13245 (communication use), 2609.14935 (centralized or not), 2611.02240 (what the belief is over) and 2109.14700.
- Bujarbaruah et al. (cited by 2604.02687 as a demonstrator–learner constraint-learning precedent) was not searched.
