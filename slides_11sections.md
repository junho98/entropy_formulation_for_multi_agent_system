---
theme: default
title: Sharing Coupled Constraints without Communication
layout: cover
coverTitle: Sharing Coupled Constraints without Communication
author: Junho Kim
date: 2026-11-16
org: AAIL
logo: /images/aail-logo.png
---

<div class="subtitle">
A certified room, prices read from observation, and fairness over time
</div>

<!--
오늘 이야기는 하나의 질문에서 시작합니다. 여러 agent가 하나의 제약을 함께 지켜야 할 때, 서로 메시지를 주고받지 않고도 안전하게, 그리고 공정하게 그 제약을 나눌 수 있을까요?
답은 세 가지 재료로 이루어집니다. 자기 믿음으로 만든 인증된 room, 관측에서 읽어낸 가격으로 움직이는 합의, 그리고 시간에 걸친 공정성을 위한 비용 승수입니다.
-->

---
layout: outline
active: 0
items:
  - Introduction
  - Method at a glance
  - "Three blocks: local problem, belief and room, exchange"
  - Laws
  - Thermodynamic reading
  - The closed loop
  - Numerical study
  - Extensions and limits
---

<!--
순서는 논문 v43의 순서를 그대로 따릅니다. 서론에서 Tan 등의 통신 기반 방법과 선행연구를 먼저 보고, 방법 개요, 세 블록(국소 문제, 믿음과 room, 교환), 거기서 나오는 법칙들, 열역학적 해석, closed loop, 실험, 한계 순서로 갑니다.
-->

---
layout: section
---

# Introduction

<div class="subtitle">Sharing a constraint, and how it is done today</div>

---
layout: body
slideTitle: Agents share a coupled constraint
sub: one budget, many owners, nobody sees the others' decisions
---

Agents $i\in\mathcal I$ choose decisions $u_i$ with **private** convex costs $f_i$ and share

$$
c(u)=\sum_{j\in\mathcal I_c} c_j(u_j)\le 0,
$$

each $c_j$ convex, to be met with probability at least $1-\delta$.

- **No messages.** Each agent observes the others' terms $c_k(u_k)$ only after they act.
- **Unknown neighbours.** Some agents follow a common convention, some follow no rule, and which is which is not known.

<div class="box-soft">

**Running instance: collision avoidance.** For single integrators, $c=g_i+g_k$ with

$$
g_i=-2d_{ik}^\top u_i-\tfrac\kappa2 h_{ik},\qquad h_{ik}=\|d_{ik}\|^2-\rho^2,
$$

the barrier condition $\dot h_{ik}\ge-\kappa h_{ik}$, separable in the inputs at a given state.

</div>

<!--
설정입니다. 각 agent는 자기 결정과 자기만 아는 비용을 갖고, 모두가 하나의 합 형태 제약을 공유합니다. 이 제약을 확률 1-δ 이상으로 지켜야 합니다.
핵심 조건 두 가지: 메시지가 없고, 다른 agent의 항은 그들이 행동한 뒤에야 관측됩니다. 그리고 어떤 이웃은 규칙을 따르고 어떤 이웃은 따르지 않는데, 누가 누구인지 모릅니다.
예제로는 충돌 회피를 씁니다. 단일 적분기에서 barrier 조건 ḣ ≥ -κh가 두 agent의 입력에 대해 분리되는 합 꼴이 됩니다. 그래서 "한 쌍이 하나의 예산을 나누는" 문제가 됩니다.
-->

---
layout: body
slideTitle: Today the split is negotiated by messages
sub: Tan, Liu, Johansson, Dimarogonas — dual decomposition with communication
---

Each shared constraint $m$ gets an auxiliary variable $y_i^m$ per member; member $i$'s local problem uses the shift $\sum_{j\in N_i^m}(y_i^m-y_j^m)$ in its row.

Every step, over the communication link (their Algorithm 2):

1. **send** $y_i^m$, gather $y_j^m$ from every other member;
2. **solve** the local problem, get its multipliers $c_i^m\ge0$;
3. **send** $c_i^m$, gather $c_j^m$;
4. **update** $\dot y_i^m=-k_0\sum_{j\in N_i^m}(c_i^m-c_j^m)$.

<div class="box-soft">

Two messages per neighbour and step. Every member is known, follows the rule and communicates; there is no belief and no certified bound.

</div>

<div class="cite">X. Tan, C. Liu, K. H. Johansson, D. V. Dimarogonas, "A continuous-time violation-free multi-agent optimization algorithm and its applications to safe distributed control," arXiv:2404.07571v2, 2025 (Eq. 18, 21; Alg. 2).</div>

<!--
지금 이 문제를 푸는 대표적인 방법이 Tan 등의 방법입니다. 공유 제약마다 보조 변수 y를 두고, 각 agent의 국소 문제는 y 차이만큼 이동한 제약을 풉니다.
매 스텝 통신으로 두 번 메시지를 보냅니다. y를 보내고 받고, 국소 문제를 풀어 승수 c를 얻고, c를 보내고 받은 뒤, 승수 차이로 y를 갱신합니다.
모든 구성원이 알려져 있고 규칙을 따르고 통신한다는 가정이라서, 믿음이나 인증된 상한 같은 것이 없습니다.
-->

---
layout: body
slideTitle: Tan's step, as a data flow
sub: red boxes travel over the communication link
---

<div class="[&_img]:max-h-[370px] [&_img]:mx-auto">

![Tan et al. data flow](/images/alg_dataflow_tan.png)

</div>

<!--
같은 내용을 데이터 흐름으로 그렸습니다. 빨간 상자가 통신 링크로 오가는 값입니다. 위에서부터 관측, 교환, room, 국소 문제 층입니다. 이 배치는 뒤에서 볼 우리 방법의 그림과 같습니다.
오늘 발표는 이 빨간 상자들을 전부 관측으로 바꾸는 이야기입니다.
-->

---
layout: body
slideTitle: Related work, by what each agent may know
sub: information condition decides what can be shared
class: dense table
---

| information | method | what is shared or fixed | what it needs |
|---|---|---|---|
| A · central | oracle: one QP over all inputs | the full constraint | all states and costs at one node (upper bound) |
| B · communication | Tan et al. | allocations $y$, multipliers $c$, sent every step | messages; members known and following; local Slater |
| C · own obs. | PCCA (Jankovic & Santillo) | copies of everyone's inputs, corrected from observed behaviour | no communication |
| C · own obs. | risk ratio (Lyu, Luo & Dolan) | a responsibility share from a CBF-inspired risk measure | no direct communication |
| C · own obs. | reciprocal | a fixed half split | nothing |
| C · own obs. | **this work** | an agreement per contact, moved by prices read from observation | a public convention |

<div class="box-soft">

**Missing.** B needs messages every step and does not treat agents outside the team. A fixed split cannot move toward the agent that needs the budget more.

</div>

<div class="cite">Tan et al., arXiv:2404.07571, 2025 · Jankovic & Santillo, arXiv:2012.10261, 2020 · Lyu, Luo & Dolan, arXiv:2305.13467, 2023.</div>

<!--
선행연구를 정보 조건으로 정리했습니다.
A는 중앙 QP로, 모든 상태와 비용을 아는 상한입니다. 경쟁 방법이 아니라 기준선입니다.
B는 Tan 등의 통신 기반 쌍대 방법입니다. 매 스텝 메시지가 필요하고, 모든 구성원이 알려져 있고 규칙을 따른다고 가정합니다. 팀 밖 agent는 다루지 않고, 시간에 걸쳐 낸 비용 같은 개념도 없습니다.
C는 자기 관측만 쓰는 방법들입니다. PCCA는 모든 agent의 제어 입력 사본을 관측된 행동으로 보정하고, risk ratio는 CBF에서 영감을 받은 위험 척도로 책임 비율을 정하고, reciprocal은 반반으로 고정합니다. 고정 분할은 예산이 더 필요한 쪽으로 움직일 수 없습니다.
이 작업도 C에 속합니다. 접촉마다 합의 변수를 두고, 관측에서 읽은 가격으로 움직입니다.
-->

---
layout: body
slideTitle: The question, and what is shown
sub: requirements (a) safety, (b) optimal split, (c) no messages
class: dense
---

**Question.** Every agent solves one fixed local problem with a *room* $R_i$ it leaves to the others. What should $R_i$ be, and how should it be updated, so that

- (a) the constraint holds with probability $1-\delta$ although no agent knows the others' decisions,
- (b) agents that follow the convention reach the split that is optimal for all of them,
- (<span>c</span>) no messages are needed?

<div class="box-soft">

1. **A probabilistic model robust to unknown neighbours.** The room is a certified bound on the others' usage under the agent's own belief; one nonnegative slack certifies the whole constraint at level $\delta$, and a neighbour that follows no rule enters as a load the room always covers.
2. **A dual system without messages, with fairness.** The multiplier of each share is read from the observed slack and exchanged across each contact; the copies of an agreement stay opposite, total energy decreases, and equal prices are the optimum of the group. A second costate $\beta_i$, of the cost paid so far, is set from the agent's own ledger; at the equilibrium in paid cost all agents of a connected group pay at one common rate: equality of burden. Neither costate needs a message.
3. **A thermodynamic reading.** Agreements, costates, risk budgets and beliefs are wall positions, contact forces, entropies and heat, with a first and a second law.

</div>

<!--
질문은 이렇습니다. 각 agent가 다른 이들에게 남겨 두는 몫 R을 어떻게 정하고 갱신해야, (a) 남의 결정을 모르면서도 제약이 1-δ로 지켜지고, (b) 규칙을 따르는 agent들은 모두에게 최적인 분할에 도달하고, (c) 메시지가 필요 없게 될까요.
보이는 것은 세 가지입니다. 첫째, 모르는 이웃에 강건한 확률 모형: room은 자기 믿음 아래의 인증된 상한이고, 한 agent의 slack만 음이 아니면 전체 제약이 δ 수준으로 인증됩니다. 규칙을 따르지 않는 이웃은 load로 들어옵니다.
둘째, 메시지 없는 쌍대 시스템과 공정성. costate가 두 개입니다. 공유 제약의 costate λ는 관측한 slack에서 읽고, 누적 비용의 costate β는 자기 장부에서 정합니다. 누적 비용의 평형에서는 연결된 그룹 전체가 하나의 공통 비율로 비용을 냅니다. 이것을 부담의 평등이라고 부릅니다. 둘 다 메시지가 필요 없습니다. 이게 이 작업의 핵심 아이디어입니다. 셋째, 열역학적 해석입니다.
-->

---
layout: section
---

# Method at a glance

<div class="subtitle">One local problem, three blocks per step</div>

---
layout: body
slideTitle: Every agent solves one problem of fixed form
sub: Eq. (2) and Algorithm 1
class: dense
---

$$
E_i(R_i):=\min_{u_i}\ \beta_i f_i(u_i)+\sum_k\Psi(s_{ik}),\qquad s_{ik}=-\big(c^{(k)}_i(u_i)+R_{ik}\big)
$$

$R_{ik}$: room left to neighbour $k$ · $s_{ik}$: slack · $\Psi$: public convex nonincreasing price on the slack · $\beta_i$: private multiplier on the own cost · $E_i$: the agent's **energy**.

Per sensed neighbour $k$, executed in the order 3, 2, 1:

| block | what it computes |
|---|---|
| **3) Exchange** | $r_{ik}\leftarrow r_{ik}-m_{ik}(\lambda_{ik}-\hat\lambda_{ki})/(2k_e)$, with $\lambda_{ik}=k_e(\epsilon-s_{ik})_+$ and $\hat\lambda_{ki}=k_e(\epsilon-\hat s_{ki})_+$ from the slacks of step $t-1$ |
| **2) Belief (EVaR room)** | observe $y_k$ from $u_k(t-1)$ → posterior over $\tau$ → $R_{ik}=\mathcal A^\delta_{w_{ik}}[\max(c_k,r_{ik})]$; replica $\hat R_{ki}=\mathcal A^\delta_{\hat w_{ki}}[\max(c_i,-r_{ik})]$; $m_{ik}=w_{ik}(\mathcal F)\hat w_{ki}(\mathcal F)$ |
| **1) Local problem** | $\beta_i=\mathrm{clip}(e^{(W_i-\bar ft)/W_0},\tfrac18,8)$; $u_i\leftarrow\arg\min$ of (2); $W_i\leftarrow W_i+f_i\Delta t$ |

<div class="muted">

Contact opens: $r_{ik}=0$; contact closes: discard. Without the fairness multiplier, $\beta_i=1$.

</div>

<!--
방법의 전부가 이 식 하나입니다. 각 agent는 매 스텝 자기 비용과 slack에 대한 가격의 합을 최소화합니다. 이 최적값을 agent의 에너지라 부릅니다.
이웃마다 세 블록을 3, 2, 1 순서로 돌립니다. 3번 교환: 지난 스텝의 slack에서 자기 costate와 이웃 costate의 replica를 계산해서 합의 r을 움직입니다. 2번 믿음: 이웃의 접근 속도를 관측해서 사후분포를 갱신하고, 인증된 상한으로 room을 만듭니다. 이웃이 나에 대해 갖는 믿음도 똑같은 규칙으로 replica를 만듭니다. 1번 국소 문제: 공정성 승수 β를 정하고 문제를 풉니다.
-->

---
layout: body
slideTitle: Same variables as Tan, read instead of sent
sub: data flow of one step of agent i
---

<div class="[&_img]:max-h-[310px] [&_img]:mx-auto">

![Data flow of one step](/images/alg_dataflow_abstract.png)

</div>

<div class="muted">

Tan's messages $y$ and $c$ become the agreement $r_{ik}$ and the costate $\lambda_{ik}$; the neighbour's costate is the replica $\hat\lambda_{ki}$, computed from its observed term $c_k$ and the replicated room $\hat R_{ki}$.

</div>

<!--
이 그림이 우리 방법의 데이터 흐름입니다. 앞서 본 Tan의 그림과 같은 배치입니다. 맨 위 초록색이 관측, 그 아래 교환, 믿음과 room, 국소 문제 순서입니다.
대응 관계는 이렇습니다. Tan의 y 차이가 우리 합의 r, Tan의 승수 c가 우리 costate λ입니다. 차이는 빨간 메시지 상자가 없다는 것입니다. 이웃의 costate는 이웃이 실제로 한 행동, 즉 관측된 c_k와, 공개 규칙으로 복제한 이웃의 room에서 계산합니다.
-->

---
layout: section
---

# The local problem

<div class="subtitle">Block 1: energy, costate, price, multiplier</div>

---
layout: body
slideTitle: Energy and costate
sub: the price of the room an agent leaves to others
---

<div class="box-soft">

**Definition (costate).**
$$
\lambda_i:=E_i'(R_i)=-\Psi'(s_i)\big|_{\text{optimum of (2)}}\ \ge 0,
$$
the increase of the agent's energy per unit of room it leaves to the others.

</div>

**Example (corridor).** Two robots with speeds $v_0+v_1\le1.5$, $c_i=v_i-0.75$, cost $\tfrac12(v_i-\bar v_i)^2$, agreement $r_{01}$ and a hard wall. Robot $0$ is capped at $0.75-r_{01}$:

$$
E_0=\tfrac12(\bar v_0-0.75+r_{01})_+^2,\qquad \lambda_0=(\bar v_0-0.75+r_{01})_+ ,
$$

how far its wish lies beyond its share.

<!--
국소 문제의 최적값이 에너지이고, room에 대한 에너지의 미분이 costate입니다. 남에게 room을 한 단위 더 남겨 줄 때 내 에너지가 얼마나 늘어나는지입니다.
복도 예제: 두 로봇 속도 합이 1.5 이하. 로봇 0은 0.75-r까지로 제한되고, costate는 원하는 속도가 자기 몫을 얼마나 넘는지와 같습니다.
-->

---
layout: body
slideTitle: The price on the slack must be readable
sub: wall vs layer
---

<div class="box-soft">

**Proposition (readability).** (i) If $\Psi$ is a hard wall ($0$ on $s\ge0$, $+\infty$ below), an active share reveals only $\lambda_k s_k=0$, not $\lambda_k$. (ii) If $\Psi$ is strictly convex on $(0,\epsilon)$, then $\lambda_k=-\Psi'(s_k)$ is determined by $k$'s slack.

</div>

We take a layer of depth $\epsilon$ in front of the wall:

$$
\Psi(s)=\frac{k_e}{2}(\epsilon-s)_+^2+M(-s)_+ .
$$

- Solvable for every room $R_i$.
- Equal to the walled problem wherever that is feasible and $M$ exceeds its multipliers.
- The exchanged costate is the layer multiplier $\lambda_{ik}=k_e(\epsilon-s_{ik})_+$.

<!--
이웃의 costate를 읽으려면 가격이 slack에서 엄격히 볼록해야 합니다. 딱딱한 벽이면 제약이 활성일 때 λs=0만 드러나고 λ 값은 안 보입니다.
그래서 벽 앞에 깊이 ε의 층을 둡니다. 층 안에서는 가격이 2차라서 slack을 보면 costate가 정해집니다. 벽 아래는 기울기 M의 정확한 벌점입니다. 그래서 문제는 항상 풀리고, 벽 문제가 풀리는 곳에서는 그 해와 같습니다.
-->

---
layout: body
slideTitle: A multiplier on the cost gives fairness over time
sub: the multiplier of the agent's share of a min–max constraint
class: dense
---

$W_i(t)=\int_0^t f_i\,d\tau$ is the cost agent $i$ has paid so far (private). Fairness over time is one more shared constraint:

$$
\min_{\bar W,u}\ \bar W\quad\text{s.t.}\quad W_i\le\bar W\ (i\in\mathcal I),\qquad c(u)\le 0 .
$$

Stationarity in $u_i$ is the local problem (2) with $f_i$ replaced by $\beta_i f_i$, and $\beta_i(W_i-\bar W)=0$. Smoothing $\max_iW_i$ by $W_0\ln\sum_ie^{W_i/W_0}$ gives Gibbs weights, $\beta_i=\partial\Phi/\partial W_i$, $\beta_i/\beta_k=e^{(W_i-W_k)/W_0}$. As $\lambda_i=\partial E_i/\partial R_i$ is the costate of the room, $\beta_i$ is the costate of the paid cost.

<div class="box-soft">

**Definition (fairness multiplier).** Each agent keeps $W_i$ and solves (2) with the cost $\beta_if_i$,
$$
\beta_i:=e^{(W_i-\bar ft)/W_0},
$$
with public constants $W_0>0$, $\bar f\ge0$. Rooms, agreements, beliefs and the exchange law are unchanged; no agent reads the multiplier of another.

</div>

An agent with a larger $\beta_i$ yields less at the same room; its slack falls, its costate rises, and the exchange moves room to it.

<!--
평형은 매 순간 총비용을 최소화하지만 기억이 없습니다. 자주 양보한 agent가 다음에도 똑같이 양보합니다.
시간에 걸친 공정성을 하나의 공유 제약, 즉 모든 agent의 누적 비용이 공통 상한 이하라는 min-max 문제로 씁니다. 그 라그랑지안의 정상 조건이 바로 비용에 β를 곱한 국소 문제입니다. max를 부드럽게 하면 β의 비가 누적 비용 차이의 지수가 됩니다. λ가 room에 대한 에너지의 미분, 즉 room의 costate이듯, β는 Φ를 누적 비용으로 미분한 것, 즉 누적 비용의 costate입니다.
그래서 각 agent는 자기 누적 비용으로 β를 정하기만 하면 되고, 남의 β를 읽을 필요가 없습니다. β가 크면 같은 room에서 덜 양보하고, slack이 줄고 costate가 올라가서 교환이 room을 그쪽으로 옮깁니다.
-->

---
layout: section
---

# Belief and room

<div class="subtitle">Block 2: requirement (a), safety without knowing the others</div>

---
layout: body
slideTitle: The room must bound what the others use
sub: certified bound under the agent's own belief
class: dense
---

<div class="box-soft">

**Lemma.** If $\Pr\big(\sum_{k\ne i}c_k>R_i\big)\le\delta$, then $s_i\ge0$ implies $\Pr(c(u)>0)\le\delta$.

</div>

**Belief.** Agent $i$'s belief about $k$ is a distribution $w_{ik}$ over hypotheses; hypotheses under which $k$ follows the convention form the set $\mathcal F$, and $w_{ik}(\mathcal F)$ is the *following mass*.

**Certified bound.** With $S:=\ln(1/\delta)$,

$$
\mathcal A^\delta_w[X]:=\inf_{\theta>0}\Big[\theta\ln\mathbb E_w e^{X/\theta}+\theta S\Big],\qquad \theta^\star:\ \text{the decision temperature.}
$$

| property | statement |
|---|---|
| tail bound | $\Pr_w(X>\mathcal A^\delta_w[X])\le\delta$ |
| duality | $\mathcal A^\delta_w[X]=\sup\{\mathbb E_Q[X]:\mathrm{KL}(Q\|w)\le S\}$ |
| subadditivity | $\mathcal A^\delta_w[X+Y]\le\mathcal A^\delta_{w_X}[X]+\mathcal A^\delta_{w_Y}[Y]$, no assumption on dependence |

<!--
제약을 i 입장에서 다시 쓰면 c_i ≤ -Σ c_k입니다. 왼쪽은 i가 제어하고 오른쪽은 모릅니다. 그래서 room이 남들의 항을 확률적으로 덮으면, 자기 slack이 음이 아닐 때 제약이 δ로 지켜집니다.
덮는 도구가 인증된 상한 A입니다. 모멘트 생성함수로 정의되고, 꼬리 확률이 δ 이하라는 성질, KL 거리 S 안의 최악 평균이라는 쌍대 표현, 그리고 결합 분포를 몰라도 이웃별 상한의 합으로 전체를 덮을 수 있다는 준가법성이 핵심입니다. ln(1/δ)는 상대 엔트로피 예산입니다.
-->

---
layout: body
slideTitle: Agreements give the agents a quantity they share
sub: belief alone either over-covers or double-counts
class: dense
---

A room from beliefs alone is sound, but the predictions refer to each other: agents either cover the others' capability or claim the same budget twice (corridor: two agents that each allow themselves $0.85$ claim $1.7$).

<div class="box-soft">

**Definition (agreement, allowance).** For every other member $k$, agent $i$ holds a number $r_{ik}$, the share it leaves to $k$; its allowance is $a_i:=-\sum_{k\ne i}r_{ik}$, and it uses its own term within $c_i\le a_i$. Every $r_{ik}$ starts at $0$ and is updated by the rule of the convention.

</div>

<div class="box-soft">

**Proposition (agreements bound the cooperating members).** If $k$ follows the convention, it holds $r_{ki}$ updated by the same rule from the same observations, so
$$
r_{ik}+r_{ki}\ge0,
$$
with equality when observations are exact. If every member follows, $\sum_ka_k\le0$, hence $\sum_{k\ne i}c_k\le-a_i$.

</div>

Corridor: $r_{01}=0.1$, $r_{10}=-0.1$ give $v_0\le0.65$, $v_1\le0.85$, which exhaust the budget exactly.

<!--
믿음만으로 room을 만들면 안전하긴 하지만, 서로의 예측이 서로를 참조해서 공통 기준이 없습니다. 남의 능력 전체를 덮어서 예산을 낭비하거나, 낙관적으로 예측해서 같은 예산을 두 번 씁니다.
빠진 것은 agent들이 공유하는 양입니다. 그것이 합의 변수 r입니다. 이웃마다 하나씩 들고, 0에서 시작해서 공통 규칙으로 갱신합니다. 이웃이 규칙을 따르면 이웃도 같은 관측으로 같은 규칙을 적용하므로 두 사본의 합이 0 이상으로 유지되고, 모두의 허용량 합이 0 이하가 됩니다.
-->

---
layout: body
slideTitle: The room, and why one slack certifies the constraint
sub: Definition (room) and Theorem (soundness)
class: dense
---

<div class="box-soft">

**Definition (room).**
$$
R_i:=-a_i+\sum_{k\ne i}U_{ik},\qquad U_{ik}:=\mathcal A^\delta_{w_{ik}}\big[(c_k-a_k)_+\big].
$$
For two agents, $R_i=\mathcal A^\delta_{w_{ik}}\big[\max(c_k,r_{ik})\big]$.

</div>

The cooperating members' total $-a_i$, plus a **coverage** $U_{ik}$ of what each may use beyond its allowance. Certain followers: $R_i=-a_i$. No agreement and beliefs over the capability range: $R_i\to\sum_kc_k^{\max}$, worst-case robust control.

<div class="box-soft">

**Theorem (soundness).** $s_i\ge0$ implies $\Pr_{w_i}(c(u)>0)\le\delta$ under agent $i$'s beliefs; if its beliefs are correct, the probability is the true one.

</div>

A single agent's slack certifies the whole constraint, and only that agent's beliefs need be correct. Certification does not rest on the members following the convention; its **tightness** does.

<!--
room은 협력하는 구성원들의 몫 -a_i에, 각 이웃이 자기 허용량을 넘을 가능성에 대한 덮개 U를 더한 것입니다. 두 agent면 max(c_k, r)의 인증된 상한 하나로 정리됩니다.
양 끝을 보면, 모두가 확실히 규칙을 따른다고 믿으면 덮개가 0이고, 합의도 없고 믿음이 능력 범위 전체를 덮으면 최악 강건 제어가 됩니다.
정리: 한 agent의 slack이 음이 아니면 그 agent의 믿음 아래에서 전체 제약이 δ 수준으로 인증됩니다. 그 agent의 믿음만 맞으면 됩니다. 인증 자체는 남들이 규칙을 따르는지에 의존하지 않고, 얼마나 빡빡한지만 의존합니다.
-->

---
layout: body
slideTitle: A neighbour outside the convention is a load
sub: a limit of the belief, not a category in the rules
class: dense
---

**Hypothesis family.** A hypothesis is a behavioural temperature $\tau\in[0,\infty]$ and an intent held over a window: the neighbour acts as $p(a\mid\tau,\bar u_k)\propto\exp(-D_k(a;\bar u_k)/\tau)$, with $D_k$ the regret under the public self-model. Finite $\tau$ form $\mathcal F$; $\tau=\infty$ is uniform over a public capability range.

As the following mass $w_{ik}(\mathcal F)\to0$, the agreement freezes and the term of $k$ in the room tends to the **load**

$$
L_{ik}:=\mathcal A^\delta_{w_{ik}}\big[\max(c_k,r_{ik})\big]\ \to\ \mathcal A^\delta_{w_{ik}}[c_k].
$$

<div class="box-soft">

**Proposition (load).** For a neighbour whose following mass has vanished: (i) the room of $i$ contains $L_{ik}$, and safety against $k$ holds at level $\delta$ with no assumption on $k$ beyond its capability range; (ii) $L_{ik}$ depends on the belief only, not on any exchange; (iii) the room never fell below $\mathcal A[c_k]$ at any stage, so what was exchanged with $k$ while it was believed to follow affected only the share left to it, not safety.

</div>

<!--
규칙을 따르지 않는 이웃을 따로 분류하지 않습니다. 모든 이웃에게 같은 규칙을 적용하고, 그런 이웃은 믿음의 극한으로 나타납니다. 따르는 질량이 0으로 가면 합의가 얼어붙고, room 안의 그 이웃 항은 믿음만으로 정해지는 load가 됩니다.
명제: 그 이웃의 능력 범위 외에는 아무 가정 없이 δ 수준 안전이 성립하고, 교환과 무관하며, 믿음의 어느 단계에서도 room이 A[c_k] 아래로 내려간 적이 없어서 그동안 교환한 것은 안전에 영향을 주지 않았습니다.
-->

---
layout: section
---

# Exchange

<div class="subtitle">Block 3: requirement (c), no messages</div>

---
layout: body
slideTitle: The price of an agreement, read from the neighbour's slack
sub: Propositions (prices), (exact estimates), (locality)
class: dense
---

<div class="box-soft">

**Proposition (prices).** $\partial E_i/\partial\xi=\lambda_i\,\partial R_i/\partial\xi$ for every input $\xi$ of $R_i$, and
$$
\frac{\partial R_i}{\partial r_{ik}}=1-\tilde w_{ik}(c_k>a_k)=:\rho_{ik}\in[0,1],
$$
the **transmission**; the agreement costs agent $i$ the price $\lambda_i\rho_{ik}$.

</div>

**Public beliefs.** The hypothesis family, prior and update rule are part of the convention, and members observe each other's actions exactly.

<div class="box-soft">

**Proposition (exact estimates).** Under observable allowances and public beliefs, and if $w_{ik}(\mathcal F)=1$, the estimate $\mathbb E_{w_{ik}}[\lambda_k\rho_{ki}]$ equals $\lambda_k\rho_{ki}$: $k$'s belief about $i$ is replicated from $i$'s own actions, so $R_k$, $s_k$, $\lambda_k$ are determined.

</div>

**Locality.** For pairwise specifications $\lambda_{ki}$ is a function of $u_k$, $r_{ki}=-r_{ik}$ and $w_{ki}$, all available to $i$. An aggregate over $k$'s other contacts depends recursively on the whole connected group: public prices live on contacts.

<!--
합의의 가격은 costate 곱하기 전달률 ρ입니다. 이웃이 합의를 확실히 지키면 ρ=1입니다.
이웃의 costate를 메시지 없이 읽으려면 믿음의 규칙이 공개되어 있어야 합니다. 그러면 이웃이 나에 대해 갖는 믿음을 내 행동으로 복제할 수 있고, 이웃의 room, slack, costate가 정확히 정해집니다.
읽을 수 있는 가격의 범위도 정해집니다. 쌍별 제약에서는 접촉 하나의 가격은 읽을 수 있지만, 이웃의 다른 접촉에 의존하는 집계량은 연결된 그룹 전체에 재귀적으로 의존해서 국소적으로 읽을 수 없습니다. 공개 가격은 접촉 위에 삽니다.
-->

---
layout: body
slideTitle: Both copies move by one number
sub: Definition (exchange law) and Theorem (agreements and equilibria)
class: dense
---

<div class="box-soft">

**Definition (exchange law).**
$$
\dot r_{ik}=-\dot r_{ki}=-\kappa\, m_{ik}\big(\lambda_i\rho_{ik}-\lambda_k\rho_{ki}\big),\qquad m_{ik}:=w_{ik}(\mathcal F)\,w_{ki}(\mathcal F).
$$
The agent with the higher price leaves less room; the exchange is discounted by the doubt of either side.

</div>

<div class="box-soft">

**Theorem (agreements and equilibria).**
(i) Whatever the beliefs, $\tfrac{d}{dt}(r_{ik}+r_{ki})=0$.
(ii) If both follow, $\tfrac{d}{dt}(E_i+E_k)=-\kappa m_{ik}(\lambda_i\rho_{ik}-\lambda_k\rho_{ki})^2\le0$; stationary points have equal prices.
(iii) If all follow and are certain, the stationary points are the KKT points of $\min\sum_if_i$ s.t. $c\le0$ as $\Psi\to0$; with $r_{ik}=y_i-y_k$ and costates communicated it is the update $\dot y_i=-k_0\sum_k(c_i-c_k)$ of Tan et al.
(iv) Toward a neighbour with small following mass, $m_{ik}\to0$ and $\rho_{ik}\to0$: the agreement freezes, and safety is unaffected.

</div>

<!--
교환 법칙입니다. 두 사본이 같은 숫자만큼 반대 방향으로 움직입니다. 가격이 높은 쪽이 room을 덜 남기고, 양쪽의 신뢰 곱 m으로 할인합니다.
정리: (i) 믿음과 무관하게 두 사본의 합이 정확히 보존됩니다. (ii) 둘 다 규칙을 따르면 두 에너지의 합이 줄고, 정지점에서 가격이 같습니다. (iii) 모두 따르고 서로 확실하면 중앙 문제의 KKT점이고, 노드 변수로 쓰고 costate를 통신하면 정확히 Tan의 갱신식입니다. 즉 Tan의 방법은 이 법칙의 특수한 경우입니다. (iv) 믿지 못하는 이웃과는 합의가 얼어붙지만 안전에는 영향이 없습니다.
-->

---
layout: section
---

# Laws

<div class="subtitle">Requirement (b): what follows from the three blocks</div>

---
layout: body
slideTitle: Equal prices are the optimum of the group
sub: Theorem (equilibrium)
class: dense
---

<div class="box-soft">

**Theorem (equilibrium).** Fix the beliefs; let $P$ be the pairs of agents that follow the convention.
(i) The equilibria are the minimisers of the convex problem
$$
\min_r\ \sum_iE_i\big(R_i(r)\big)\quad\text{s.t.}\quad r_{ik}+r_{ki}=0\ \ ((i,k)\in P),
$$
the common price of a pair being the multiplier of its constraint.
(ii) Along the exchange law $\tfrac{d}{dt}\sum_iE_i=-\kappa\sum_{(i,k)\in P}(\lambda_i\rho_{ik}-\lambda_k\rho_{ki})^2\le0$; bounded agreements approach the set of equilibria.
(iii) If all follow and are certain about each other, the equilibrium solves $\min\sum_i\beta_if_i$ s.t. $c\le0$ as $\Psi\to0$, for fixed multipliers; with $\beta\equiv1$ this is the central problem $\min\sum_if_i$.
(iv) Otherwise it solves the certified problem $c_i(u_i)+R_i\le0$: the efficiency given up is the price of what the agents do not know.

</div>

As beliefs about cooperating neighbours concentrate, $U\to0$ and the equilibrium approaches the central optimum.

<!--
평형 정리입니다. 믿음을 고정하면 평형은 에너지 합을 합의 보존 제약 아래에서 최소화하는 볼록 문제의 해입니다. 교환 법칙을 따라 에너지 합이 단조 감소하고 평형 집합에 접근합니다.
모두 따르고 서로 확실하면, β를 고정했을 때 β로 가중한 비용의 중앙 최적이고 β가 모두 1이면 원래 중앙 문제입니다. 그렇지 않으면 인증된 문제의 해입니다. 포기하는 효율이 정확히 모르는 것의 가격입니다. 믿음이 집중하면 덮개가 0으로 가고 중앙 최적에 다가갑니다.
-->

---
layout: body
slideTitle: An outside load is shared by the group, at one price
sub: Theorem (equilibrium under external loads)
class: dense
---

Cooperating agents $C$, exchanged pairs $P$, total load $L_i=\sum_kL_{ik}$; for one constraint shared by the group, $R_i(r)=\sum_{j:(i,j)\in P}r_{ij}+\sum_jU_{ij}+L_i$.

<div class="box-soft">

**Theorem (one shared constraint).** (i) The equilibria minimise $\Phi(L):=\min_r\sum_{i\in C}E_i(R_i(r))$ s.t. $r_{ij}+r_{ji}=0$, and on every connected component $\Gamma$ of $(C,P)$ all costates equal a common $\lambda^\star_\Gamma$. (ii) An external agent pressing on one member raises the costate of every member of its component, and the exchange moves room toward that member. (iii) $\partial\Phi/\partial L_{ik}=\lambda^\star_{\Gamma(i)}$.

</div>

**Pairwise specifications.** Every contact has its own agreement and costate; there is no common costate on a component, and
$$
\frac{\partial\Phi}{\partial L_{ij}}=\lambda^\star_{ij},
$$
the force on that contact at equilibrium. The load is passed on along the contacts that lie opposite it (force chain), as the central certified problem does.

<!--
외부 load가 있는 평형입니다. 그룹이 하나의 제약을 공유하면, 연결된 성분마다 costate가 하나의 공통값이 되고, 외부 agent의 비용은 그 공통 가격으로 매겨집니다. 협력 그룹이 저수지처럼 load를 나눠 받습니다.
충돌 회피처럼 쌍별 제약이면 공통 costate는 없고, 접촉마다 힘이 다릅니다. load는 그 방향에 놓인 접촉들을 따라 전달됩니다. 이게 뒤에서 볼 force chain이고, 중앙 문제도 똑같이 합니다.
-->

---
layout: body
slideTitle: Fairness over time — two agents
sub: Proposition (two agents)
class: dense
---

Quadratic costs $f_i=\tfrac\omega2\|u_i-u_i^0\|^2$, one linear specification with gradients of equal norm $\gamma$, joint yield $D>0$, hard wall. At $\lambda_i=\lambda_k$:

$$
\|u_i-u_i^0\|=\frac{\beta_k}{\beta_i+\beta_k}\frac D\gamma,\qquad
\dot W_i=\frac b4(1-\chi_{ik})^2,\qquad b=\frac{\omega D^2}{2\gamma^2},\qquad \chi_{ik}=\frac{\beta_i-\beta_k}{\beta_i+\beta_k}=\tanh\frac{W_i-W_k}{2W_0},
$$

$$
\frac{d}{dt}(W_i-W_k)=-b\,\chi_{ik},\qquad \sinh\frac{d(t)}2=\sinh\frac{d(0)}2\,e^{-B(t)/(2W_0)},\quad d=\frac{W_i-W_k}{W_0}.
$$

- The agent that has paid more pays less from now on; the difference decays at a rate set by $W_0$.
- Without the multiplier both pay $b/4$ and $W_i-W_k$ does not change.
- The pair pays $\tfrac b2\chi_{ik}^2$ more than the least total cost while the multipliers differ: the price of fairness.

<!--
두 agent의 경우 공정성 동역학을 정확히 풀 수 있습니다. 평형에서 각자의 양보량은 상대 β의 비율이고, 누적 비용 차이는 tanh로 줄어듭니다. 비용을 더 낸 쪽이 앞으로 덜 내고, 그 차이는 W0가 정하는 속도로 지수적으로 줄어듭니다.
승수가 없으면 둘 다 b/4씩 내고 차이가 변하지 않습니다. 승수들이 다를 동안만 추가 비용이 들고, 같아지면 추가 비용이 없습니다. 이것이 공정성의 가격입니다.
-->

---
layout: body
slideTitle: "Equilibrium in paid cost: all pay at the same rate"
sub: Definition; the pair as a special case
class: dense
---

<div class="box-soft">

**Definition (equilibrium in paid cost).** A profile $W$ is an equilibrium in paid cost if the differences $W_i-W_k$ are stationary, that is $\dot W_i=\dot W_k$ for all $i,k$.

</div>

<div class="box-soft">

In general (fixed contacts, connected graph) the equilibrium is the balanced profile: it is unique and every solution converges to it, with $\beta_i/\beta_k=e^{d^\star_i-d^\star_k}$, and
$$
W_i(t)-W_k(t)\to\text{const},\qquad \dot W_i(t)-\dot W_k(t)\to0\qquad\text{for all }i,k,
$$
adjacent or not: all agents of a connected group come to pay at one common rate $v^\star$, so that $W_i/W_k\to1$. **The fairness reached is equality of burden**, whichever agent the contacts fall on.

</div>

**Special case: a pair** (Proposition, equal costates of paid cost). $\frac{d}{dt}(W_i-W_k)=-b\,\frac{\beta_i-\beta_k}{\beta_i+\beta_k}$, so the pair is at an equilibrium in paid cost if and only if $\beta_i=\beta_k$, if and only if $W_i=W_k$. Equal $\beta$ holds only for a pair, or for many agents when the loads $B_i$ are equal ($d^\star=0$).

<!--
누적 비용에도 평형을 정의할 수 있습니다. 누적 비용의 차이가 더 이상 변하지 않는 상태, 즉 모든 agent가 같은 비율로 비용을 내는 상태입니다.
일반적으로, 접촉이 고정되고 연결되어 있으면 이 평형은 다음 슬라이드의 균형 profile입니다. 유일하고 모든 해가 수렴하며, 인접하든 아니든 모든 쌍에서 누적 비용 차이는 상수로, 비용 비율 차이는 0으로 갑니다. 연결된 그룹의 모든 agent가 하나의 공통 비율 v*로 비용을 내게 되고, 누적 비용의 비는 1로 갑니다. 이렇게 도달하는 공정성을 부담의 평등(equality of burden)이라고 부릅니다. 접촉이 누구에게 몰리든 상관없습니다. β의 비는 일정하지만 같을 필요는 없습니다.
특수한 경우가 두 agent입니다. 차이의 변화율이 β 차이를 β 합으로 나눈 것에 비례하므로, 평형은 정확히 β가 같을 때, 즉 누적 비용이 같을 때입니다. 여러 agent에서도 load가 모두 같으면 β가 모두 같습니다.
-->

---
layout: body
slideTitle: Fairness over time — fixed contacts
sub: Proposition (fixed contacts)
class: dense
---

Summing over an agent's contacts with intensities $b_{ik}=b_{ki}\ge0$:
$$
\dot W_i=F_i(W):=\frac14\sum_kb_{ik}\Big(1-\tanh\frac{W_i-W_k}{2W_0}\Big)^2 .
$$

<div class="box-soft">

**Proposition (fixed contacts).** Constant intensities, connected graph, $B_i:=\sum_kb_{ik}$.
(i) For two solutions, $\max_i(W_i-W_i')-\min_i(W_i-W_i')$ is nonincreasing.
(ii) If a balanced profile exists, it is unique up to a shift and $W_i(t)-W_k(t)\to W_0(d^\star_i-d^\star_k)$, with $d^\star$ independent of $W_0$. Without the multiplier, $W_i-W_k$ grows as $\tfrac14(B_i-B_k)t$.
(iii) $F_i\le B_i$: a balanced profile requires $v^\star\le\min_iB_i$.

</div>

Without the multiplier the differences of paid cost grow with the difference of loads; with it they are bounded and proportional to $W_0$, as long as no agent is so rarely in contact that (iii) fails. The balanced profile of (ii) is the equilibrium in paid cost for many agents; there $\beta_i/\beta_k=e^{d^\star_i-d^\star_k}$, all one when the loads $B_i$ are equal.

<!--
접촉이 고정되어 있으면 여러 agent로 확장됩니다. 두 해의 차이의 범위가 줄어들고, 균형 profile이 있으면 누적 비용 차이가 W0에 비례하는 유한값으로 수렴합니다. 승수가 없으면 차이가 load 차이에 비례해서 선형으로 커집니다.
단, 어떤 agent가 너무 드물게 접촉하면 균형이 존재하지 않을 수 있습니다. 명제는 균형 profile의 필요조건만 줍니다.
이 균형 profile이 여러 agent에 대한 누적 비용 평형입니다. 거기서 β들의 비는 고정되고, load가 모두 같으면 모두 1입니다.
-->

---
layout: body
slideTitle: "Two costates: λ for the room, β for the paid cost"
sub: the two equilibria have the same form; neither costate needs a message
class: dense
---

| | room | paid cost |
|---|---|---|
| state | agreement $r_{ik}$ | $W_i=\int f_i\,dt$ |
| potential | $\sum_iE_i$ | $\Phi=W_0\ln\sum_ie^{W_i/W_0}$ |
| costate | $\lambda_i=\partial E_i/\partial R_i$ | $\beta_i=\partial\Phi/\partial W_i$ |
| constraint it prices | $r_{ik}+r_{ki}=0$ | $W_i\le\bar W$ |
| motion | $\dot r_{ik}=-\kappa(\lambda_i-\lambda_k)$ | $\frac d{dt}(W_i-W_k)=-b\,\frac{\beta_i-\beta_k}{\beta_i+\beta_k}$ |
| equilibrium | $\lambda_i=\lambda_k$ | $\dot W_i=\dot W_k$, $\beta_i/\beta_k$ constant; $\beta_i=\beta_k$ for a pair or equal loads |
| lives on | a contact | an agent |

<div class="box">

Neither costate is sent. The room's equilibrium is one per contact; the paid cost's is **equality of burden**, one for the whole group: $\beta_i$ is one scalar per agent, and all come to pay at one common rate. $\lambda$ is read from the observed slack and moves the room through the exchange law, fast. $\beta$ needs no law of its own: it enters the agent's own problem, and the difference of paid cost follows from the decisions, on the slower scale of the paid cost.

</div>

<!--
이 작업의 핵심 아이디어입니다. costate가 두 개입니다.
왼쪽은 room입니다. 상태는 합의 r, 퍼텐셜은 에너지 합, costate는 λ이고, 합의 보존 제약을 가격 매깁니다. 합의는 λ의 차이로 움직이고 λ가 같아지면 평형입니다.
오른쪽은 누적 비용입니다. 상태는 W, 퍼텐셜은 log-sum-exp Φ, costate는 β이고, 모두의 누적 비용이 공통 상한 이하라는 공정성 제약을 가격 매깁니다. 평형은 모두가 같은 비율로 비용을 내는 상태이고, 그때 β의 비가 일정합니다. β가 같아지는 것은 두 agent이거나 load가 같은 특수한 경우입니다. 마지막 행이 차이입니다. room의 costate는 접촉마다 하나이고, β는 agent마다 하나의 스칼라이며, 이 평형, 즉 부담의 평등은 그룹 전체에 하나입니다.
둘 다 메시지 없이 동작합니다. λ는 관측한 slack에서 읽어서 교환 법칙으로 빠르게 room을 옮깁니다. β는 별도 법칙이 필요 없습니다. 자기 국소 문제에 들어가고, 누적 비용 차이는 결정들에서 저절로, 더 느린 시간 척도로 따라옵니다.
-->

---
layout: section
---

# Thermodynamic reading

<div class="subtitle">Public quantities live on contacts, private summaries on agents</div>

---
layout: body
slideTitle: The construction reads as a packing of soft bodies
sub: dictionary
class: dense
---

| mechanics / thermodynamics | this construction |
|---|---|
| a ball (a system) | agent $i$, internal energy $E_i(R_i)$ |
| position of the wall | agreement $r_{ik}$ |
| conservation across a wall | $r_{ik}+r_{ki}\ge0$ |
| contact force (magnitude) | costate $\lambda_{ik}=-\Psi'(s_{ik})$, public |
| force balance of a ball | optimality of (2): $\beta_i\omega_i(u_i-u_i^0)=\sum_kf_{ik}$ |
| action and reaction | equal prices $\lambda_{ik}\rho_{ik}=\lambda_{ki}\rho_{ki}$ |
| pressure of a ball | virial $P_i=\tfrac12\sum_k\langle f_{ik},d_{ik}\rangle$ |
| entropy of a contact | $S_{ik}=\ln(1/\delta_{ik})$, relative entropy |
| temperature of a ball | $T_i:=\partial E_i/\partial S_i$ |
| decision temperature of a contact | $\theta^\star_{ik}$; in energy units $\lambda_{ik}\theta^\star_{ik}=T_ip_{ik}$ |
| heat | change of energy through the belief |
| external wall, heat source | neighbour outside the convention |

<!--
여기서부터는 같은 구성을 열역학으로 다시 읽습니다. 최적화와 위험만으로 만들었지만, 양들이 부드러운 공들의 packing처럼 대응합니다.
agent가 공, 합의가 벽의 위치, costate가 접촉력, 같은 가격이 작용과 반작용입니다. 위험 예산 ln(1/δ)가 엔트로피, 결정 온도가 온도, 믿음을 통한 에너지 변화가 열입니다. 규칙 밖의 이웃은 반응하지 않는 외부 벽, 즉 열원입니다.
원칙 하나: 공개 양은 접촉 위에, 사적인 요약은 agent 위에 있습니다.
-->

---
layout: body
slideTitle: A first and a second law
sub: Proposition (first law) and dissipation of the exchange
class: dense
---

<div class="box-soft">

**Proposition (first law).** At fixed state,
$$
dE_i=\underbrace{\sum_k\lambda_{ik}\rho_{ik}\,dr_{ik}}_{\text{work at the contacts}}+\underbrace{\sum_k\lambda_{ik}\theta^\star_{ik}\,dS_{ik}}_{\text{entropy budget}}+\underbrace{\sum_k\lambda_{ik}\Big\langle\frac{\partial U_{ik}}{\partial w_{ik}},dw_{ik}\Big\rangle}_{\text{heat: belief}}+\underbrace{f_i\,d\beta_i}_{\text{paid cost}},
$$
and at the internal equilibrium of the risk, $dE_i=\sum_k\lambda_{ik}\rho_{ik}\,dr_{ik}+T_i\,dS_i+\delta Q_i+f_i\,d\beta_i$, with $d\beta_i=\beta_i(f_i-\bar f)\,dt/W_0$.

</div>

The first term is moved by the agents, in pairs and conservatively; the second by the designer and the agent's allotment of risk; the third by observations; the fourth by the agent's own ledger of paid cost, and it vanishes when the agent pays at the mean rate, $f_i=\bar f$.

**Second law.** Exchange is dissipative, at fixed beliefs and fixed multipliers $\beta$:
$$
\frac{d}{dt}\sum_iE_i\Big|_{\text{exchange}}=-\kappa\sum_{(i,k)\in P}(\lambda_{ik}\rho_{ik}-\lambda_{ki}\rho_{ki})^2\le0,
$$
with equality only when every contact is balanced. A force difference across a wall always moves the wall toward the weaker side.

<!--
제1법칙: 에너지 변화는 네 항으로 나뉩니다. 접촉에서의 일, 엔트로피 예산, 믿음을 통한 열, 그리고 누적 비용 항 f dβ입니다. 첫째는 agent들이 쌍으로 보존적으로 움직이고, 둘째는 설계자와 agent의 위험 배분이, 셋째는 관측이, 넷째는 자기 누적 비용 장부가 움직입니다. 평균 비율로 비용을 내고 있으면 넷째 항은 0입니다.
제2법칙: 교환은 소산적입니다. 모든 접촉이 균형일 때만 에너지 감소가 멈춥니다. 벽 양쪽의 힘 차이는 항상 약한 쪽으로 벽을 밉니다.
-->

---
layout: body
slideTitle: Forces, pressure, and the force chain
sub: Proposition (force chain), checked numerically
class: dense
---

Contact force $f_{ik}:=-\lambda_{ik}\nabla_{u_i}g_{ik}=2\lambda_{ik}d_{ik}$, pointing away from $k$; away from the speed bound, $\beta_i\omega_i(u_i-u_i^0)=\sum_kf_{ik}$. Pressure (virial) $P_i=\sum_k\lambda_{ik}\|d_{ik}\|^2$.

<div class="box-soft">

**Proposition (force chain).** With the contacts $\mathcal K$ of agent $i$ in the layer and the speed bound inactive, $G$ the matrix of rows $\nabla_{u_i}g_{ik}^\top$:
$$
\frac{\partial\lambda_{i\cdot}}{\partial R_{i\cdot}}=k_e\,\omega_i(\omega_iI+k_eGG^\top)^{-1}.
$$
For two contacts $j,k$ the sign of $\partial\lambda_{ik}/\partial R_{ij}$ is that of $-\langle d_{ij},d_{ik}\rangle$. With the fairness multiplier, $\omega_i$ is replaced by $\beta_i\omega_i$.

</div>

| external agent $e$ pushes agent 0 | predicted $\partial\lambda_{01}/\partial R_{0e}$ | finite difference |
|---|---|---|
| toward teammate 1 | $+9.9155$ | $+9.9155$ |
| orthogonally | $0$ | $0$ |
| from the teammate's side | $-0.1238$ | $-0.1238$ |

A push is released along the agents that lie in its direction: grains, not gas.

<!--
충돌 회피에서 접촉력은 2λd로 상대에게서 멀어지는 방향입니다. agent가 원하는 움직임에서 벗어난 정도가 정확히 접촉력의 합력입니다.
force chain 명제: 한 접촉의 room이 다른 접촉의 costate에 주는 영향의 부호는 두 상대 방향의 내적의 부호와 반대입니다. 팀원 쪽으로 미는 외부 agent는 팀원과의 접촉력을 키우고, 직각이면 영향이 없고, 팀원 쪽에서 밀면 줄입니다.
표는 세 기하에서 예측과 유한 차분이 소수 넷째 자리까지 일치함을 보입니다. 압력이 그룹 전체에 같아지는 기체가 아니라, 방향을 따라 힘이 전달되는 알갱이입니다.
-->

---
layout: body
slideTitle: Temperature measures ignorance in units of the constraint
sub: Propositions (decision temperature) and (temperature of an agent)
class: dense
---

<div class="box-soft">

**Proposition.** With $S=\ln(1/\delta)$, $\mathcal A(S)=\sup_Q\{\mathbb E_Q[X]:\mathrm{KL}(Q\|w)\le S\}$; the supremum is attained by the tilted law $Q^\star\propto e^{x/\theta^\star}w$, and $d\mathcal A/dS=\theta^\star$.

</div>

For a Gaussian prediction with standard deviation $\sigma$: $\theta^\star=\sigma/\sqrt{2S}$, $U=\mu+\sigma\sqrt{2S}$ — a neighbour the agent knows poorly is hot.

Agent entropy and Boltzmann weights of the contacts:
$$
S_i:=\ln\frac1{\delta_i}=-\ln\sum_ke^{-S_{ik}},\qquad p_{ik}=\frac{\delta_{ik}}{\delta_i}.
$$

<div class="box-soft">

**Proposition (temperature of an agent).** If $\theta^\star_{ik}+d\theta^\star_{ik}/dS_{ik}\ge0$, the allotment minimising $E_i$ at fixed $S_i$ satisfies $\lambda_{ik}\theta^\star_{ik}=T_i\,p_{ik}$, $T_i:=\partial E_i^\star/\partial S_i\ge0$.

</div>

Risk flows to contacts that are pressed and poorly known. (The implementation uses the fixed allotment $\delta_{ik}=\delta$, which every neighbour can replicate.)

<!--
온도입니다. 엔트로피 예산 안에서 최악의 예측은 온도 θ*의 볼츠만 분포이고, θ*는 상한을 예산으로 미분한 값입니다. 정준 앙상블의 거울상입니다.
가우시안이면 θ*는 σ에 비례합니다. 잘 모르는 이웃은 뜨겁습니다. 접촉력 곱하기 온도가 그 무지의 비용입니다.
agent 하나의 엔트로피는 접촉 엔트로피들의 log-partition이고, 위험의 배분 비율이 볼츠만 가중치입니다. 최적 배분에서 모든 접촉의 온도가 agent 온도 곱하기 가중치가 됩니다. 구현에서는 이웃이 복제할 수 있도록 고정 배분을 씁니다.
-->

---
layout: body
slideTitle: Where the analogy stops
sub: what is not exchanged
---

- **Beliefs** are not conserved and not exchanged: there is no thermal equilibrium between agents, only inside an agent and between an agent and what it observes.
- **The fairness multiplier** is not exchanged either: it equalises over time, through the split of the constraint, not across a contact.
- **Risk** could be shared through a ledger of its own (an exchange of entropy, $T_i=T_k$ at equilibrium); that is not part of the construction.
- **Pressure** is equalised across a wall, not across a group: goal-directed agents are grains, not gas.

<div class="box">

Each agent is described as an elastic body is: a stress at its contacts, which is public, and an energy, pressure and temperature, which are its own.

</div>

<!--
비유가 멈추는 곳도 분명히 해 둡니다. 믿음은 보존되지도 교환되지도 않아서 agent 사이의 열평형은 없습니다. 공정성 승수도 교환되지 않고 시간에 걸쳐 같아집니다. 위험을 나누는 장부를 따로 두면 엔트로피 교환이 되겠지만 이 구성의 일부가 아닙니다. 압력은 벽을 사이에 두고만 같아지고 그룹 전체에서는 아닙니다.
요약하면 각 agent는 탄성체처럼, 접촉의 응력은 공개이고 에너지, 압력, 온도는 자기 것입니다.
-->

---
layout: section
---

# The closed loop

<div class="subtitle">State, agreements and beliefs move together</div>

---
layout: body
slideTitle: Safety along trajectories
sub: invariance among cooperating agents; per-step risk otherwise
---

<div class="box-soft">

**Theorem (invariance among cooperating agents).** Let the constraint be the barrier condition $\dot h\ge-\kappa h$, split as in the collision-avoidance example, and let all members follow the convention. If every local problem of a following agent has a solution with $s_i\ge0$ at every sampling instant, then with inputs held over each interval $h(p_t)\ge-O(\Delta t^2)$ whenever $h(p_0)\ge0$; in continuous time $\{h\ge0\}$ is forward invariant.

</div>

<div class="box-soft">

**Proposition (risk along a trajectory).** If at step $t$ the bound uses risk $\delta_t$, then under the agent's beliefs $\Pr(\exists\,t\le T:c(u_t)>0)\le\sum_{t\le T}\delta_t$; a trajectory-level risk $\varepsilon$ needs $\delta_t=\varepsilon/T$.

</div>

The per-step budget $\ln(1/\delta_t)$ is the share of a trajectory budget of relative entropy.

<!--
지금까지는 상태와 믿음을 고정했습니다. closed loop에서 남는 것을 봅니다.
모두가 규칙을 따르고 매 샘플링 시점에 국소 문제가 slack ≥ 0으로 풀리면, barrier 집합이 불변입니다. 이산 시간에서는 Δt² 차수의 오차만 있습니다.
규칙 밖의 agent에 대해서는 보장이 스텝별이고 확률적이며 누적됩니다. 궤적 전체 위험 ε를 원하면 스텝별 δ를 ε/T로 잡아야 합니다.
-->

---
layout: body
slideTitle: Agreements track the moving equilibrium
sub: Theorem (tracking), and what is not guaranteed
class: dense
---

<div class="box-soft">

**Theorem (tracking).** If $\Phi(r;p,w)$ is $\mu$-strongly convex in $r$, $r^\star$ is $L$-Lipschitz in $p$, and $\|\dot p\|\le\bar v$ while beliefs are constant, then along the exchange law
$$
\limsup_{t\to\infty}\|r_t-r^\star(p_t,w)\|\le\frac{L\bar v}{\kappa\mu}.
$$

</div>

When all follow and trust each other, $r^\star$ is the split of the central optimum: the closed loop is the central optimal controller up to a tracking error that decreases with the exchange rate $\kappa$.

**Energy balance.** $\tfrac{d}{dt}\sum_iE_i=$ exchange $(\le0)$ + motion + belief: $\sum_iE_i$ is a Lyapunov function for the exchange, not for the closed loop.

**Not guaranteed.** Liveness; recursive feasibility with agents outside the convention, which can surround a cooperating agent faster than it can escape; the coupling of fast agreements with beliefs that change abruptly.

<!--
합의는 움직이는 평형을 추적합니다. 추적 오차는 상태가 움직이는 속도에 비례하고 교환 속도에 반비례합니다. 모두 따르고 서로 믿으면 평형은 중앙 최적의 분할이므로, closed loop는 추적 오차를 빼면 중앙 최적 제어기입니다.
에너지 합은 교환에 대한 Lyapunov 함수이지 closed loop 전체에 대한 것은 아닙니다. 보장하지 않는 것: liveness, 외부 agent가 있을 때의 재귀적 실현 가능성, 그리고 믿음이 급변할 때의 결합입니다.
-->

---
layout: section
---

# Numerical study

<div class="subtitle">The experiments validate the theory</div>

---
layout: body
slideTitle: Implementation
sub: every choice left open, fixed for collision avoidance
class: dense
---

- **Agents.** Single integrators $\dot p_i=u_i$, $\Delta t=0.02$ s, $\|u_i\|\le1.2$ (eight half-planes); $f_i=\tfrac{\omega_i}2\|u_i-u_i^0\|^2$, $u_i^0$ the unit-speed velocity toward the current target; barrier with $\kappa=2$, $\rho=1$ for every neighbour within $5$.
- **Local problem.** $\Psi(s)=\tfrac{k_e}2(\epsilon-s)_+^2+M(-s)_+$, $k_e=20$, $M=1000$: a QP per step; $\lambda_{ik}=k_e(\epsilon-s_{ik})_+$.
- **Costates.** $\hat\lambda_{ki}=k_e(\epsilon-\hat s_{ki})_+$, $\hat s_{ki}=-(c_k+\hat R_{ki})$ from the replicated room; $m_{ik}=w_{ik}(\mathcal F)w_{ki}(\mathcal F)$; transmissions set to one.
- **Exchange.** $r_{ik}\leftarrow r_{ik}-m_{ik}(\lambda_{ik}-\hat\lambda_{ki})/(2k_e)$, so $r_{ki}=-r_{ik}$; the step $1/(2k_e)$ does not overshoot.
- **Belief.** Last $50$ approach speeds; $\tau\in\{10^{-4},10^{-2},10^{-1},1\}$ Gaussian in closed form, $\tau=\infty$ uniform on the capability range; prior $0.03$ on $\tau=\infty$.
- **Risk.** $\delta=0.05$ per contact per step; no trajectory-level guarantee is claimed.
- **Fairness multiplier.** $\beta_i=e^{(W_i-\bar ft)/W_0}$ clipped to $[1/8,8]$, every step, $W_0=4.22$, $\bar f$ the mean cost rate of ours without the multiplier in the same cell and $\epsilon$.

<!--
구현에서 열어 둔 선택을 모두 정합니다. 단일 적분기, 속도 1.2 제한, 감지 거리 5 안의 이웃마다 barrier 조건. 가격은 층 깊이 ε, 강성 k_e 20, 벽 기울기 1000이고 매 스텝 QP 하나를 풉니다.
이웃의 costate는 복제한 room으로 계산하고, 교환 스텝 1/(2k_e)는 넘어서지 않는 크기입니다. 믿음은 최근 50개 접근 속도로 네 개의 유한 온도와 무한 온도를 구분합니다. 위험은 접촉당 스텝당 0.05이고, 공정성 승수는 매 스텝 갱신하며 [1/8, 8]로 자릅니다.
-->

---
layout: two-cols-fig
slideTitle: Setup — a 2×3 grid, methods grouped by information
sub: 8 agents, targets on a circle, 24 seeds × 120 s
class: dense
---

- **Team.** HOM: all $\omega_i=1$. HET: $\omega_i$ alternating $1,3$.
- **External agents** (never identified, never yielding, speed $0.8$, heading noise $2$ rad/$\sqrt{\mathrm s}$): E0 none, E4 four, E8 eight. $v_{\mathrm{env}}=1.0$ (E0: $1.2$).
- **Methods.**
  - A · oracle: one central QP, every external agent at its capability bound — an upper bound, not a competitor.
  - B · Tan: multipliers exchanged by communication; it does not treat agents outside the team, so it is compared in E0 only.
  - C · own observation only: PCCA, reciprocal, risk ratio, ours ($\epsilon\in\{0.1,0.2\}$), ours $+\beta$.
- **Three axes.** Fairness (spread: std/mean of paid cost $W_i(120\,\mathrm s)$), cost (mean $f_i$), violations (time below $0.95\rho$, toward external agents and among agents). Same seeds for all methods; differences paired by seed.

::right::

![Four cells at t = 30 s](/images/scenes_cells.png)

<div class="cite">Snapshots at t = 30 s, ours. Disk diameter = ρ; dashed circle: sensing range of agent 0.</div>

<!--
실험 설정입니다. 8개 agent가 원 위의 목표점 사이를 오갑니다. 2×3 격자입니다. 행은 팀 구성: HOM은 모두 가중치 1, HET는 1과 3이 번갈아. 열은 외부 agent 수: E0 없음, E4 넷, E8 여덟. 외부 agent는 식별되지 않고 절대 양보하지 않습니다.
방법은 정보 조건으로 묶습니다. A 중앙 oracle은 상한, B Tan은 팀 밖 agent를 다루지 않으므로 E0에서만 비교, C는 자기 관측만 쓰는 방법들과 우리 방법입니다.
세 축: 공정성은 누적 비용의 표준편차/평균, 비용은 f의 평균, 위반은 0.95ρ 미만 시간 비율입니다. 같은 seed로 짝지어 비교합니다.
-->

---
layout: body
slideTitle: Three axes at a glance
sub: cost against violation (top) and against spread (bottom), per cell
---

![Three axes](/images/three_axes.png)

<div class="muted">

Mean ± s.e. over 24 seeds. Lower is better on every axis. Ours $+\beta$ has the lowest spread in every cell; Tan appears only in E0.

</div>

<!--
세 축을 한 그림에 담았습니다. 위쪽은 비용 대 위반, 아래쪽은 비용 대 공정성 지표입니다. 모든 축에서 낮을수록 좋습니다.
보라색 원과 마름모가 β를 붙인 우리 방법입니다. 아래 줄에서 모든 셀에서 가장 낮습니다. 위 줄에서 risk ratio(분홍)는 외부 agent가 있으면 위반이 34-57%이고, 우리 방법은 ε 0.2에서 oracle 수준에 있습니다.
-->

---
layout: body
slideTitle: HOM team — cost, violation, spread
sub: 24 seeds of 120 s, means
class: dense table
---

| | method | E0 cost | E0 spread | E4 cost | E4 ext. % | E4 spread | E8 cost | E8 ext. % | E8 spread | team % |
|---|---|---|---|---|---|---|---|---|---|---|
| A | oracle | .020 | .34 | .073 | .19 | .36 | .123 | .52 | .33 | 0 |
| B | Tan | .024 | .32 | — | — | — | — | — | — | .07 |
| C | PCCA | .042 | .29 | .157 | .24 | .34 | .292 | 1.80 | .24 | 0 |
| C | reciprocal | .052 | .28 | .117 | .75 | .34 | .187 | 2.59 | .31 | 0 |
| C | risk ratio | .033 | .35 | .078 | 35.1 | .42 | .104 | 56.7 | .29 | .10 |
| C | ours, $\epsilon=0.1$ | .037 | .31 | .141 | .01 | .35 | .227 | .76 | .28 | 0 |
| C | ours, $\epsilon=0.2$ | .041 | .28 | .141 | .06 | .32 | .241 | .37 | .27 | 0 |
| C | ours $+\beta$, $\epsilon=0.1$ | .038 | **.22** | .141 | .16 | **.27** | .216 | .48 | **.18** | 0 |
| C | ours $+\beta$, $\epsilon=0.2$ | .040 | **.21** | .144 | .09 | **.26** | .231 | .22 | **.20** | 0 |

<div class="cite">Ext. %: time below 0.95ρ toward external agents. Spread: std/mean of paid cost (lowest in bold). Team %: largest over E0–E8. Tan does not treat agents outside the team and is compared only in E0. Standard errors: cost ≤ 0.02, spread ≤ 0.04, ext. % ≤ 0.5 (split rules ≤ 1.4).</div>

<!--
HOM 표입니다. 공정성 지표는 β를 붙인 우리 방법이 모든 셀에서 가장 낮습니다. 외부 agent 위반은 ε 0.2에서 oracle과 같은 수준입니다. risk ratio는 싸지만 위반이 35-57%입니다. 팀 내 위반은 우리 방법이 0입니다.
-->

---
layout: body
slideTitle: HET team — cost, violation, spread
sub: 24 seeds of 120 s, means
class: dense table
---

| | method | E0 cost | E0 spread | E4 cost | E4 ext. % | E4 spread | E8 cost | E8 ext. % | E8 spread | team % |
|---|---|---|---|---|---|---|---|---|---|---|
| A | oracle | .034 | .35 | .132 | .10 | .51 | .235 | .58 | .51 | 0 |
| B | Tan | .045 | .38 | — | — | — | — | — | — | .17 |
| C | PCCA | .084 | .57 | .310 | .24 | .59 | .602 | 1.80 | .59 | 0 |
| C | reciprocal | .103 | .57 | .234 | .80 | .61 | .371 | 2.49 | .58 | .02 |
| C | risk ratio | .066 | .64 | .160 | 34.2 | .63 | .206 | 56.4 | .55 | .10 |
| C | ours, $\epsilon=0.1$ | .058 | .37 | .240 | .10 | .54 | .404 | 1.51 | .54 | .03 |
| C | ours, $\epsilon=0.2$ | .069 | .37 | .252 | .09 | .50 | .420 | .61 | .50 | 0 |
| C | ours $+\beta$, $\epsilon=0.1$ | .061 | **.26** | .243 | .34 | **.41** | .413 | 1.08 | **.41** | 0 |
| C | ours $+\beta$, $\epsilon=0.2$ | .066 | **.25** | .240 | .05 | **.30** | .396 | .75 | **.33** | .05 |

<div class="cite">Same columns as the HOM table. Among agents ours stays at or below 0.05% in every cell; Tan (E0) has 0.07 ± 0.06% (HOM) and 0.17 ± 0.11% (HET). Within group C ours costs less than PCCA in every cell.</div>

<!--
HET 표입니다. 가중치가 섞여 있어도 β가 모든 셀에서 공정성 지표를 가장 낮게 만듭니다. 그룹 C 안에서 우리 방법은 모든 셀에서 PCCA보다 쌉니다. reciprocal과 risk ratio는 외부 agent가 있을 때 더 싸지만 위반이 0.75-57%입니다. HET-E8 ε 0.1에서 외부 위반이 1.51%인데, ε 0.2로 깊게 하면 0.61%로 내려갑니다.
-->

---
layout: body
slideTitle: What the agents do not know costs at most a third of the gap
sub: gap to the oracle, and the part due to the coverage of uncertain neighbours
class: dense
---

The oracle is the lower bound. The gap of ours ($\epsilon=0.1$) to the oracle is $0.017$–$0.169$. Measured against ours with $U=0$ given full information, the coverage of uncertain neighbours accounts for at most a third of it.

| cell | gap to oracle | coverage: ours − ours with $U=0$ | share of the gap |
|---|---|---|---|
| HOM-E0 | 0.0165 ± 0.0015 | 0.0011 ± 0.0016 | 7 % |
| HOM-E4 | 0.0685 ± 0.0057 | 0.0223 ± 0.0066 | 33 % |
| HOM-E8 | 0.1042 ± 0.0053 | 0.0229 ± 0.0052 | 22 % |
| HET-E0 | 0.0245 ± 0.0021 | −0.0008 ± 0.0027 | −3 % |
| HET-E4 | 0.1081 ± 0.0112 | 0.0274 ± 0.0102 | 25 % |
| HET-E8 | 0.1686 ± 0.0120 | 0.0440 ± 0.0124 | 26 % |

<div class="cite">Paired over 24 seeds, mean ± s.e.; share = ratio of the means. Ours with U = 0 is a full-information reference, not implementable from own observation.</div>

<!--
oracle과의 비용 차이 중 얼마가 모르는 것 때문인지 봅니다. 완전 정보를 준 기준, 즉 덮개 U=0인 우리 방법과 비교하면, 덮개가 차지하는 몫은 외부 agent가 있는 셀에서 22-33%, 외부 agent가 없으면 거의 0입니다. 정리 (iv)에서 말한 "모르는 것의 가격"이 차이의 최대 3분의 1이라는 뜻입니다.
-->

---
layout: two-cols-fig
slideTitle: The multiplier bounds the spread over 600 s
sub: as Proposition (fixed contacts) predicts where its condition holds
class: dense
---

Spread of the paid cost at 600 s, ours → ours $+\beta$ (12 seeds):

| cell | $\epsilon=0.1$ | $\epsilon=0.2$ |
|---|---|---|
| HOM-E0 | .118 → .058 | .127 → .067 |
| HOM-E4 | .188 → .071 | .140 → .052 |
| HOM-E8 | .115 → .043 | .115 → .043 |
| HET-E0 | .212 → .074 | .247 → .087 |
| HET-E4 | .407 → .224 | .399 → .182 |
| HET-E8 | .443 → .298 | .411 → .233 |

Lower in all six cells at both depths, by $0.06$–$0.22$, each at least four standard errors. The range levels off in the HOM cells and HET-E0 (HOM-E8: $17$–$22$ from 240 s on), and keeps growing in HET-E4 and HET-E8 at $0.4$ to $0.7$ of the rate without; without the multiplier it grows throughout.

::right::

![Range of paid cost over 600 s](/images/range_vs_time.png)

<div class="cite">max W_i − min W_i over time, 12 seeds, s.e. bands; solid ε = 0.1, dashed ε = 0.2. Cost within ±0.04; violation among agents at most 0.02 %.</div>

<!--
600초 동안의 공정성입니다. 승수가 없으면 누적 비용의 범위가 계속 커집니다. 승수가 있으면 HOM 세 셀과 HET-E0에서 평평해집니다. 고정 접촉 명제가 예측한 대로입니다. HOM-E8에서는 240초 이후 17-22 사이에 머뭅니다.
HET-E4, E8에서는 계속 커지지만, 승수가 없을 때 속도의 0.4에서 0.7배입니다. 접촉이 생기고 끊기는 경우는 명제가 다루지 않고, 여기서는 수치적 근거만 있습니다. 비용 차이는 ±0.04 이내이고 팀 내 위반은 최대 0.02%입니다.
-->

---
layout: body
slideTitle: One agent's own view
sub: HET-E8, seed 2, agent 0 (w = 1), ours + β (ε = 0.1), 0–60 s
---

<video controls class="h-72 mx-auto">
  <source src="/videos/local_view_HET-E8_agent0.mp4" type="video/mp4" />
</video>

<div class="muted">

Left: the arena (ground truth). Right, agent 0's own quantities: (1) $T_i=\sum_k\lambda_{ik}\theta^\star_{ik}$, $P_i$; (2) following mass per neighbour; (3) prediction vs observation, bound $R_{ik}$, coverage; (4) $\beta_i$, $W_i$ vs $\bar ft$; (5) $r_{ik}$, $\lambda_{ik}$.

</div>

<!--
한 agent의 시점입니다. 외부 agent가 8명인 HET 셀입니다. 왼쪽은 실제 장면, 오른쪽은 agent 0이 스스로 보고 믿고 결정한 값들만입니다.
1번 패널은 온도와 압력, 2번은 이웃마다 "따라 준다"는 믿음입니다. 팀원은 1 근처, 외부 agent는 양보하지 않는 게 보이면 0으로 떨어집니다. 3번은 가장 강하게 묶인 이웃의 사용량 예측과 관측, 상한 R과 덮개입니다. 4번은 β와 누적 비용, 5번은 이웃별 합의와 가격입니다.
35초 근처에서 팀원과 외부 agent 사이에 끼면서 압력과 온도가 튀는 것을 보시면 됩니다.
-->

---
layout: body
slideTitle: The same agent under Tan, without outsiders
sub: HET-E0, seed 1, agent 6 (w = 1), 0–60 s — behaviour, cost and fairness
---

<video controls class="h-72 mx-auto">
  <source src="/videos/compare_tan_HET-E0_agent6.mp4" type="video/mp4" />
</video>

<div class="muted">

Top: ours $+\beta$ ($\epsilon=0.1$); bottom: Tan as published; same start, trajectories diverge. Violations are rare in E0, so this is about behaviour, cost and fairness. Seed 1, 120 s: ours cost .063, spread .25; Tan cost .042, spread .42.

</div>

<!--
같은 agent를 Tan으로 돌린 비교입니다. Tan은 팀 밖 agent를 다루지 않으므로 외부 agent가 없는 HET-E0입니다. E0에서는 위반이 드물어서 이 영상은 안전이 아니라 움직임, 비용, 공정성에 관한 것입니다.
2a와 2b를 비교해 보세요. 우리 방법은 이웃에 대한 믿음을 자기 관측으로 세우고, Tan은 각 팀원이 보내 주는 승수를 받습니다. 같은 역할을 하는 양을 하나는 읽고 하나는 받습니다.
-->

---
layout: two-cols-fig
slideTitle: The layer depth is the safety–cost knob
sub: E4 and E8, violation toward external agents against cost
---

An agent at rest already pays the price inside the distance $\sqrt{1+2\epsilon/\kappa}$ from a neighbour, an effective contact distance that gives a margin of anticipation against non-yielding agents.

- At $\epsilon=0.2$ ours is at $0.06$–$0.61\%$ toward external agents, at the level of the oracle ($0.10$–$0.58\%$).
- PCCA reaches $1.80\%$, the reciprocal split $2.6\%$, the risk ratio $34$–$57\%$.
- At $\epsilon=0.1$ ours reaches $1.51\%$ in HET-E8.

::right::

![Trade-off over the layer depth](/images/tradeoff_E4_E8.png)

<div class="cite">Ours at ε = 0.1, 0.2, 0.3 (line), ours + β at ε = 0.1, 0.2 (diamonds), baselines default (open) and tuned (filled). Mean ± s.e. over 24 seeds, symlog axis.</div>

<!--
층 깊이 ε가 안전과 비용 사이의 손잡이입니다. 정지한 agent도 이웃과 √(1+2ε/κ) 거리 안에서는 이미 가격을 냅니다. 이것이 유효 접촉 거리가 되어 양보하지 않는 agent에 대한 예측 여유를 줍니다.
ε 0.2에서 외부 위반은 oracle 수준인 0.06-0.61%이고, PCCA는 1.8%, reciprocal 2.6%, risk ratio는 34-57%입니다.
-->

---
layout: section
---

# Extensions and limits

<div class="subtitle">What the construction does not yet do</div>

---
layout: body
slideTitle: Extensions and limits
sub: from the paper's last section
class: dense
---

- **Joint feasibility.** Pairwise viability is a specification; the viability of a group is not separable. A cost-to-go energy $\min_{\pi_i}\mathbb E_{w_i}[\sum_t\gamma^t(f_i+\Psi(s_{i,t}))]$ would put future barrier payments into the present.
- **Time scale of fairness.** Before a share is active no rule can reflect private weights; the costate imbalance at first activation is at least $|\omega_a-\omega_b|/(\omega_a+\omega_b)$ for one ordering.

<div class="box-soft">

**Proposition (fairness and exposure).** For any rule that uses observations only,
$$
P_{\mathcal F}\big(r_{ik}(n)<m\big)+P_{\mathrm{out}}\big(r_{ik}(n)\ge m\big)\ \ge\ \tfrac12\exp(-\mathrm{KL}_n),\qquad T\cdot\frac{D}{\Delta t}\ge\ln\frac1{2P}.
$$
A neighbour can be treated fairly only as fast as its behaviour reveals whether it can be trusted.

</div>

- **Fairness over time.** The convergence result assumes fixed contacts and a balanced profile; with contacts that form and break the evidence is numerical; $\bar f$ must be public.
- **Liveness.** As for any one-step safety filter, the closed loop can rest at a point that is not a goal.
- **Open.** Readability without mutual trust; constraints shared by three or more agents that do not observe each other; non-separable constraints; second-order dynamics; allotting risk in closed loop; exchange of risk between agents.

<!--
한계입니다. 그룹 전체의 실현 가능성은 분리되지 않습니다. 비용-to-go 에너지로 미래 barrier 비용을 현재에 넣는 것이 확장 방향입니다.
공정성의 시간 척도에는 속도 제한이 있습니다. 관측만 쓰는 어떤 규칙도, 규칙을 따르는 이웃에게 공정하면서 동시에 아직 시험받지 않은 비협력 이웃에 대해 안전할 수 없습니다. 이웃의 행동이 신뢰 여부를 드러내는 속도만큼만 빨리 공정해질 수 있습니다. 시간-에너지 관계에서 에너지 역할을 정보가 합니다.
그 밖에 접촉이 생기고 끊기는 경우의 공정성 이론, liveness(교착), 상호 신뢰 없는 가독성 등이 열려 있습니다.
-->

---
layout: body
slideTitle: Summary
sub: sharing a constraint with no messages
---

<div class="box-soft">

1. **A probabilistic model robust to unknown neighbours.** The room is a certified bound under the agent's own belief; one nonnegative slack certifies the constraint at level $\delta$; a neighbour that follows no rule is a load the room always covers.
2. **Two costates, no messages.** $\lambda$, the costate of the room, is read from observed slack; the two copies of an agreement stay opposite and equal prices are the group optimum. $\beta$, the costate of the paid cost, is set from the agent's own ledger; at the equilibrium in paid cost all agents of a connected group pay at one common rate (equality of burden), and with fixed contacts the differences of paid cost stay bounded.
3. **A thermodynamic reading.** Walls, forces, entropies and heat, with a first and a second law.

</div>

In the 2×3 grid: violation among agents at most $0.05\%$, toward external agents at the oracle's level at $\epsilon=0.2$; the lowest spread of all methods in every cell with the multiplier; and the coverage of what the agents do not know is at most a third of the gap to the oracle.

<!--
정리합니다. 세 가지입니다. 모르는 이웃에 강건한 확률 모형, 메시지 없이 동작하는 두 costate, 즉 room의 λ와 누적 비용의 β, 그리고 β가 만드는 부담의 평등, 그리고 열역학적 해석입니다.
실험에서는 팀 내 위반이 최대 0.05%, 외부 위반은 ε 0.2에서 oracle 수준, β를 붙이면 모든 셀에서 가장 공정하고, 모르는 것의 비용은 oracle과의 차이의 최대 3분의 1이었습니다.
-->

---
layout: section
---

# Thank You

<div class="subtitle">AAIL</div>

---
layout: body
slideTitle: "Appendix A — properties of the certified bound"
sub: Lemma (properties) with one-line proofs
class: dense appendix
---

Let $X,Y$ be quantities with law $w$, $S=\ln(1/\delta)$, $\mathcal A^\delta_w[X]=\inf_{\theta>0}[\theta\ln\mathbb E_we^{X/\theta}+\theta S]$.

| | statement | proof |
|---|---|---|
| (i) | $\Pr_w(X>\mathcal A^\delta_w[X])\le\delta$ | Markov on $e^{X/\theta}$; the bound equals $\delta$ at $t(\theta)$; take the infimum |
| (ii) | $\mathcal A^\delta_w[X+a]=\mathcal A^\delta_w[X]+a$; $\mathcal A^\delta_w[a]=a$ | the constant leaves the log |
| (iii) | $X\le Y\Rightarrow\mathcal A[X]\le\mathcal A[Y]$; nonincreasing in $\delta$ | monotone MGF; objective nondecreasing in $S$ |
| (iv) | $\mathcal A^\delta_w[X]=\sup\{\mathbb E_Q[X]:\mathrm{KL}(Q\|w)\le S\}$ | strong duality and Donsker–Varadhan |
| (v) | $\mathcal A^\delta_w[X+Y]\le\mathcal A^\delta_{w_X}[X]+\mathcal A^\delta_{w_Y}[Y]$ | (iv) and data processing for the marginals |
| (vi) | convex: $\mathcal A[tX+(1-t)Y]\le t\mathcal A[X]+(1-t)\mathcal A[Y]$ | supremum of linear functionals |

**Soundness, sketch.** Pointwise $\sum_{k\ne i}c_k\le\sum_{k\ne i}a_k+\sum_{k\ne i}(c_k-a_k)_+$; allowances sum to zero under every hypothesis, so $\sum_{k\ne i}a_k=-a_i$; by (ii), (iii), (v) $\mathcal A[\sum_{k\ne i}c_k]\le R_i$ for any joint law with the marginals $w_{ik}$; (i) and the lemma on the room.

<!--
부록 A: 인증된 상한의 성질과 한 줄 증명, 그리고 안전성 정리의 증명 스케치입니다. 질문이 나오면 씁니다.
-->

---
layout: body
slideTitle: "Appendix B — parameters"
sub: implementation constants
class: dense appendix
---

| symbol | meaning | value | role |
|---|---|---|---|
| $\epsilon$ | layer depth of $\Psi$ | 0.1, 0.2 | readability; effective contact distance |
| $k_e$ | layer stiffness | 20 | readability; exchange step $1/(2k_e)$ |
| $M$ | barrier slope | 1000 | exact penalty |
| $\delta$ | risk level | 0.05 | certified bound |
| $T$ | belief window | 1 s | intent held fixed |
| $\kappa,\rho$ | barrier rate, radius | 2, 1 | specification |
| $v_{\mathrm{env}}$ | public capability of others | per scenario | range of the hypothesis $\tau=\infty$ |
| $W_0$ | scale of the fairness multiplier | 4.22 | $\beta_i=e^{(W_i-\bar ft)/W_0}$, clipped to $[1/8,8]$ |

Baselines tuned on the grid: oracle $\kappa=16$; PCCA $\kappa=1$, margin $0.2$; reciprocal $\kappa=16$, margin $0.2$; risk ratio $c=150$, $\kappa=4$; Tan as published (E0).

<!--
부록 B: 구현 상수와 baseline 튜닝 값입니다.
-->
