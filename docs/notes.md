# Presentation Notes

> The implementer reads this file first. Trust only what is filled in; if a
> field is blank, do NOT fill it arbitrarily — ask. In particular, if the
> "Slide mapping" is empty, do NOT build slides.

## Meta

- Title: Sharing Coupled Constraints without Communication
- Presenter: Junho Kim (AAIL)
- Audience: lab meeting
- Duration (min): about 30
- Delivery: [x] dev server  [ ] PDF export  [ ] SPA deploy
  (videos play only in the dev server)

## Goal

The audience leaves knowing how agents can split a shared constraint safely and fairly with no messages: a certified room from their own belief, an agreement moved by prices read from observation, and a multiplier on the cost for fairness over time.

## Key messages (max 3)

1. A probabilistic model robust to unknown neighbours: the room is a certified bound; one nonnegative slack certifies the constraint at level δ; a neighbour that follows no rule enters as a load.
2. Two costates without messages: λ (costate of the room) is read from observed slack, the two copies of an agreement stay opposite, equal prices are the group optimum; β (costate of the paid cost) is set from the agent's own ledger, and at the equilibrium in paid cost all pay at the same rate with constant β ratios (equality of burden; equal β only for a pair or equal loads). This is the key idea of the work.
3. A thermodynamic reading: agreements, costates, risk budgets and beliefs are walls, forces, entropies and heat, with a first and a second law.

## Sources

- Paper: `ref_notes/v43/paper_v43.txt` (draft v43, 2026-11-16). Every equation, statement and number on the slides comes from it or from `ref_notes/v43/tables.txt` (per-step β rows only; Tan only in E0).
- Baselines: PDFs in `ref_notes/baselines/` (titles, authors, years read from the PDFs).

## Slide mapping

Four sections (one divider each, subsections listed on the divider); the subsection is shown on each content slide by `tag:`. Slide order is that of v43. The 11-section version is kept as `slides_11sections.md`. Figures are relative to `public/`.

| # | subsection | message/title | layout | figure/video |
|---|---|---|---|---|
| 1 | — | Title | cover | — |
| 2 | — | Outline (4 sections) | outline | — |
| 3 | — | Section: Introduction | section | — |
| 4 | 1.1 Problem | Agents share a coupled constraint: the central problem min Σ f_i s.t. Σ c_j ≤ 0 (Eq. 1), and why no agent can solve it; running instance (collision avoidance) in the same form | body | — |
| 5 | 1.2 Related work | Today the split is negotiated by messages: Tan (split by y, local problem, each step; why a multiplier, guarantees, requires) | body | — |
| 6 | 1.2 Related work | Tan's step, as a data flow | body | images/alg_dataflow_tan.png |
| 7 | 1.2 Related work | Related work: three boxes (Messages — Tan; Prediction — PCCA; Burden sharing — risk ratio) + Ours line | body | — |
| 8 | 1.3 Question and contributions | The question: (a) safety, (b) optimality, (c) no messages | body | — |
| 9 | 1.3 Question and contributions | What this work does: certified room; two costates; thermodynamic reading | body | — |
| 10 | — | Section: Method | section | — |
| 11 | 2.1 At a glance | Every agent solves one problem of fixed form: Local problem box (min, Slack) + Each step (Observe, Exchange, Room, Solve) + "Sent: nothing", parallel to Tan slide 5 | body | — |
| 12 | 2.1 At a glance | Same variables as Tan, read instead of sent | body | images/alg_dataflow_abstract.png |
| 13 | 2.2 Block 1: the local problem | Energy and costate | body | — |
| 14 | 2.2 Block 1: the local problem | The price on the slack must be readable: why box + readability + wall vs layer figure | body | images/readability_wall_vs_layer.png |
| 15 | 2.2 Block 1: the local problem | A multiplier on the cost gives fairness over time: min–max problem, Lagrangian, stationarity | body | — |
| 16 | 2.2 Block 1: the local problem | A smooth max makes the multiplier local: Gibbs weights, drop the common factor, definition of β, effect | body | — |
| 17 | 2.3 Block 2: belief and room | The room must bound what the others use | body | — |
| 18 | 2.3 Block 2: belief and room | Agreements give the agents a quantity they share | body | — |
| 19 | 2.3 Block 2: belief and room | The room, and why one slack certifies the constraint | body | — |
| 20 | 2.3 Block 2: belief and room | A neighbour outside the convention is a load | body | — |
| 21 | 2.4 Block 3: exchange | An agreement's price, read from the neighbour | body | — |
| 22 | 2.4 Block 3: exchange | Both copies move by one number | body | — |
| 23 | 2.4 Block 3: exchange | The whole step, once more (recap of the slide 12 figure) | body | /images/alg_dataflow_abstract.png |
| 24 | — | Section: Theory | section | — |
| 25 | 3.1 Equilibrium | Equal prices are the optimum of the group | body | — |
| 26 | 3.1 Equilibrium | An outside load is shared by the group, at one price | body | — |
| 27 | 3.2 Fairness | Fairness over time — two agents | body | — |
| 28 | 3.2 Fairness | Equilibrium in paid cost: all pay at the same rate | body | — |
| 29 | 3.2 Fairness | Fairness over time — fixed contacts | body | — |
| 30 | 3.2 Fairness | Two costates: λ for the room, β for the paid cost | body | — |
| 31 | 3.3 Thermodynamic reading | The construction reads as a packing of soft bodies | body | — |
| 32 | 3.3 Thermodynamic reading | A first and a second law | body | — |
| 33 | 3.3 Thermodynamic reading | Forces, pressure, and the force chain | body | — |
| 34 | 3.3 Thermodynamic reading | Temperature measures ignorance in units of the constraint | body | — |
| 35 | 3.3 Thermodynamic reading | Where the analogy stops | body | — |
| 36 | 3.4 Closed loop | Safety along trajectories | body | — |
| 37 | 3.4 Closed loop | Agreements track the moving equilibrium | body | — |
| 38 | — | Section: Numerical study | section | — |
| 39 | 4.1 Setup | Implementation | body | — |
| 40 | 4.1 Setup | Setup — a 2×3 grid, methods grouped by information | two-cols-fig | images/scenes_cells.png |
| 41 | 4.2 Results on three axes | Three axes at a glance | body | images/three_axes.png |
| 42 | 4.2 Results on three axes | HOM team — cost, violation, spread | body | — |
| 43 | 4.2 Results on three axes | HET team — cost, violation, spread | body | — |
| 44 | 4.2 Results on three axes | What the agents do not know costs at most a third of the gap | body | — |
| 45 | 4.2 Results on three axes | The layer depth is the safety–cost knob | two-cols-fig | images/tradeoff_E4_E8.png |
| 46 | 4.3 Fairness over 600 s | The multiplier bounds the spread over 600 s | two-cols-fig | images/range_vs_time.png |
| 47 | 4.4 Agent view | One agent's own view | body | videos/local_view_HET-E8_agent0.mp4 |
| 48 | 4.4 Agent view | The same agent under Tan, without outsiders | body | videos/compare_tan_HET-E0_agent6.mp4 |
| 49 | — | Extensions and limits | body | — |
| 50 | — | Summary | body | — |
| 51 | — | Closing | section | — |
| 52 | — | Appendix A — properties of the certified bound | body | — |
| 53 | — | Appendix B — parameters | body | — |
| D | — | Appendix D — Algorithm 1 in full (moved from slide 11) | body (dense appendix) | — |
| C | — | Appendix C — Tan et al.: multiplier and guarantees (detail moved from slide 6) | body (dense appendix) | — |

## Asset list

- `public/images/readability_wall_vs_layer.png` from `figures/plot_readability.py` (matplotlib).

- Data-flow figures are built from TikZ sources in `figures/` with `figures/build.sh` (pdflatex + pdftoppm, 200 dpi): `alg_dataflow_{tan,abstract}_slide.tex` → `public/images/alg_dataflow_{tan,abstract}.png` (slide versions, no prose above or below; captions are on the slides); `alg_dataflow_{tan,abstract}.tex` are the paper versions (`*_paper.png`).

- `public/images/`: aail-logo.png, alg_dataflow_tan.png, alg_dataflow_abstract.png, scenes_cells.png, three_axes.png, range_vs_time.png, tradeoff_E4_E8.png (also present, not used: scene_*.png, alg_dataflow_v42.png)
- `public/videos/`: local_view_HET-E8_agent0.mp4, compare_tan_HET-E0_agent6.mp4

## Tone/style notes

- English slides, Korean speaker notes (HTML comments), as in the certification deck.
- One message per slide; formulas shown, proofs only as one-line sketches.
- Experiments are presented as validation of the theory. Oracle is an upper bound, not a competitor. Tan only in E0.
- No exploratory or abandoned variants.
- One idea per box: an equation or a short phrase. Details go to the Korean notes or an appendix slide.
- Indices (paper v43 final): agents j, k; constraint m (superscript), 𝓜_i the constraints of i, 𝓘_m the members of m. Per constraint: R_i^m, s_i^m, λ_i^m, λ̂_k^m, ŝ_k^m, R̂_k^m, c_i^m (instance g_i^m, whole constraint c^m), S_i^m, δ_i^m, θ_i^{m⋆}, ν_i^m (Boltzmann weight), φ_i^m (contact force). Per member: r_ik^m, U_ik^m, ρ_ik^m, L_ik^m, δQ_ik^m. Unchanged: w_ik, ŵ_ki, d_ik, h_ik, α_ik, b_ik, χ_ik. Mutual trust η_ik; noise gap Δ_ik. The index m is never omitted (user decision 2026-11-16), also in the single-constraint sections (slides 13–28); the vector form R_i = (R_i^m)_m, λ_i = (λ_i^m)_m is stated once on slide 25 (slide 13 also gives R_i = (R_i^m)_m where E_i(R_i) first appears). Hat only for i's replicas of the neighbour's quantities.

- 2026-11-16 Locality (ii) changed in the paper: the price λ^m_k is readable when all members of 𝓘_m observe each other, and this holds automatically for 𝓘_m = {i,k} (the implementation). It is not "impossible beyond two members." Slide 21 uses this wording. The local copy ref_notes/v43/paper_v43.txt is stale at this point because the new paper sentence is not available here yet.
- 2026-11-16 Method slides 13 and 17–22 were rewritten in box style. Detail that came off the slides is in the Korean notes of each slide, marked "(슬라이드에서 뺀 상세)".
