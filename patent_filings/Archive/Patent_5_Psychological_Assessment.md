# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction," "Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution," "Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination," and "Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to psychological assessment systems, and more particularly to a computer-implemented system for administering timed psychological assessments that produce continuous multi-dimensional personality vectors and domain-specific decision-making profiles structured for calibrating AI avatar personality simulation models.

---

## BACKGROUND OF THE INVENTION

[0003] Psychological assessment instruments have been used for decades to categorize personality traits, cognitive styles, and behavioral tendencies. Well-known instruments include the Myers-Briggs Type Indicator (MBTI), the Big Five (OCEAN) personality inventory, the DISC assessment, and various values inventories. These instruments were designed for clinical, organizational, or educational purposes — to help individuals understand themselves or to help organizations make hiring and team-building decisions.

[0004] However, these existing instruments are fundamentally unsuitable for calibrating AI avatar personality models for several reasons.

[0005] First, existing instruments produce categorical outputs (e.g., "INTJ," "high openness," "dominant-influential"). These categories are too coarse for individual-level decision-making simulation. Two people classified as "INTJ" may make very different decisions in the same situation because the categorical label obscures the continuous variation within the category.

[0006] Second, existing instruments are untimed — respondents can take as long as they wish to consider each question. Research in cognitive psychology demonstrates that deliberated self-reports often reflect how people want to be perceived (their "ideal self") rather than how they actually behave (their "real self"). For AI avatar calibration, the actual behavioral patterns are far more valuable than the idealized self-image.

[0007] Third, existing instruments do not capture domain-specific variation in decision-making. A person may be risk-averse in financial decisions but risk-seeking in career decisions. Existing instruments produce global trait scores that average across domains, losing this critical domain-specific information.

[0008] Fourth, existing instruments are not designed to integrate with narrative life data. They operate in isolation, producing a personality profile disconnected from the individual's actual life experiences. For AI avatar construction, the psychological profile must be linked to and contextualized by the individual's documented experiences.

[0009] There is therefore a need for a psychological assessment system that produces continuous (not categorical) personality vectors, captures instinctive (not deliberated) responses through timed administration, identifies domain-specific decision-making patterns, and integrates with narrative life data for AI avatar personality calibration.

---

## SUMMARY OF THE INVENTION

[0010] The present invention provides a computer-implemented system for administering a rapid-fire psychological assessment and processing the results into a structured decision-making profile suitable for calibrating an AI avatar's personality simulation. The system presents timed questions, captures responses and latencies, produces multi-dimensional continuous personality vectors with latency-based weighting, and identifies domain-specific reasoning patterns.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture

[0011] FIG. 1 illustrates the system architecture according to an embodiment of the present invention. The system comprises a question bank (110), an assessment interface (120), a response capture engine (130), a trait extraction engine (140), a decision pattern modeler (150), and a profile store (160).

### 2. Question Bank Design

[0012] The question bank (110) stores assessment questions organized into psychological dimension categories. Each question is associated with metadata including: dimension_category (the psychological dimension being assessed), response_options (for forced-choice questions), scoring_map (mapping each response option to positions along one or more psychological dimensions), max_response_time (the maximum allowed response time in seconds), and difficulty_level (for adaptive question selection).

[0013] In a preferred embodiment, the question bank includes questions in the following dimension categories:

[0014] (a) Values-Conflict Dimension: Questions presenting scenarios where two or more values are in tension, requiring the user to reveal their values hierarchy. Each question maps to positions along multiple values dimensions (e.g., loyalty vs. honesty, individual vs. collective, tradition vs. innovation, security vs. freedom). Example: "Your company asks you to relocate for a promotion. Your aging parent needs your help nearby. Do you: (A) Take the promotion and arrange remote care, (B) Decline and stay near your parent, (C) Negotiate a compromise, (D) Ask your parent what they want?" Each response maps to different positions on the family-priority, career-ambition, and autonomy dimensions.

[0015] (b) Risk-Calibration Dimension: Questions presenting scenarios with varying risk-reward tradeoffs, segmented by life domain (financial, career, relationship, health, adventure). Example: "You have $50,000 in savings. A friend's startup needs investment and could 10x your money or lose it all. Do you: (A) Invest nothing, (B) Invest $5,000, (C) Invest $25,000, (D) Invest it all?" Each response maps to a position on the financial risk tolerance scale.

[0016] (c) Moral-Reasoning Dimension: Ethical dilemmas calibrated to reveal the user's moral reasoning framework (utilitarian, deontological, virtue-based, care-based). Questions are adapted from established moral psychology research but reformulated for rapid-fire administration. Example: "A self-driving car must choose between hitting one pedestrian or swerving into a wall, injuring its three passengers. What should it do?" Responses map to positions on the utilitarian-deontological spectrum.

[0017] (d) Emotional-Tendency Dimension: Questions revealing characteristic emotional responses to common stimuli (criticism, praise, unexpected change, conflict, loss). Example: "You receive harsh feedback on a project you worked hard on. Your first instinct is to: (A) Push back and defend your work, (B) Feel hurt but listen carefully, (C) Ask for specific examples to improve, (D) Dismiss it and move on." Responses map to positions on emotional reactivity, openness to feedback, and resilience dimensions.

[0018] (e) Decision-Style Dimension: Questions revealing the user's characteristic approach to decision-making (intuitive vs. analytical, independent vs. consultative, fast vs. deliberate, risk-aware vs. opportunity-focused). Example: "When choosing between two job offers, you: (A) Go with your gut feeling about which team felt right, (B) Create a detailed comparison spreadsheet, (C) Ask five trusted people for their opinion, (D) Sleep on it for a week." Responses map to positions on the intuitive-analytical and independent-consultative dimensions.

### 3. Assessment Administration

[0019] FIG. 2 illustrates the assessment administration flow according to an embodiment of the present invention.

[0020] The assessment interface (120) presents questions to the user in rapid succession. The interface is designed for speed and instinctive response:

[0021] (a) Visual Design: Each question occupies the full screen with large, clearly labeled response options. The interface minimizes cognitive load by presenting one question at a time with no distracting elements.

[0022] (b) Timer Display: A visible countdown timer shows the remaining response time for each question. The timer creates mild time pressure that encourages instinctive rather than deliberated responses.

[0023] (c) Maximum Response Time: Each question enforces a maximum response time (e.g., 10 seconds for forced-choice questions with 2-4 options, 20 seconds for short text responses). The maximum time is calibrated to allow reading and comprehension but discourage extended deliberation.

[0024] (d) Transition: Upon response submission or timeout, the next question appears immediately with minimal transition animation, maintaining the rapid-fire cadence.

[0025] (e) Calibration Phase: The first 3-5 questions serve as a calibration phase. The response latencies from these questions establish a baseline_latency for the user, accounting for individual differences in reading speed, device interaction speed, and general response time. This baseline is used in the latency weighting function.

### 4. Response Capture

[0026] The response capture engine (130) records, for each question:

[0027] (a) The question identifier and dimension category.

[0028] (b) The user's selected response (for forced-choice) or text input (for short response).

[0029] (c) The response latency in milliseconds, measured from the moment the question is fully rendered on screen to the moment the user submits their response.

[0030] (d) Whether the question timed out (no response within the maximum time).

[0031] (e) The question's position in the assessment sequence (to detect fatigue effects).

[0032] (f) Device metadata (screen size, input method) that may affect response latency.

### 5. Trait Extraction with Latency Weighting

[0033] FIG. 3 illustrates the trait extraction process according to an embodiment of the present invention.

[0034] The trait extraction engine (140) processes the captured responses to produce a multi-dimensional personality vector:

[0035] Step 1 — Response Mapping: For each non-timeout response, the scoring_map associated with the question maps the selected response to one or more positions along continuous psychological dimensions. Each position is a floating-point value on a 0-1 scale. A single response may map to positions on multiple dimensions (e.g., a values-conflict response may simultaneously indicate positions on loyalty, honesty, and family-priority dimensions).

[0036] Step 2 — Latency Weighting: Each mapped position is multiplied by a weight derived from the response latency. In a preferred embodiment, the weighting function is:

    weight = 1 / (1 + ln(latency_ms / baseline_ms))

where baseline_ms is the median latency from the calibration phase. This function produces:
- Weight > 1 for responses faster than baseline (instinctive, high confidence)
- Weight ≈ 1 for responses near baseline (normal)
- Weight < 1 for responses slower than baseline (deliberated, lower authenticity)
- Weight approaching 0 for very slow responses (near timeout)

[0037] The rationale for latency weighting is grounded in dual-process theory from cognitive psychology: fast responses (System 1) reflect automatic, instinctive cognitive patterns, while slow responses (System 2) reflect deliberate, effortful reasoning. For avatar personality calibration, System 1 responses are more predictive of the individual's actual behavior in real-world situations where decisions are often made quickly and intuitively.

[0038] Step 3 — Timeout Handling: Questions that timed out are excluded from the personality vector calculation. The timeout rate (proportion of questions that timed out) is recorded as a metadata attribute. A high timeout rate on a specific dimension category may indicate decision avoidance in that domain, which is itself informative for the decision-making profile.

[0039] Step 4 — Aggregation: For each psychological dimension, the weighted positions from all relevant questions are aggregated (e.g., weighted average) to produce a single dimension score. The collection of all dimension scores forms the multi-dimensional personality vector. In a preferred embodiment, the vector includes at least the following dimensions: risk_tolerance_financial, risk_tolerance_career, risk_tolerance_relationship, empathy_orientation, analytical_vs_intuitive, loyalty_vs_independence, tradition_vs_innovation, family_priority, achievement_orientation, emotional_reactivity, openness_to_feedback, resilience, utilitarian_vs_deontological, independent_vs_consultative.

### 6. Decision Pattern Modeling

[0040] The decision pattern modeler (150) analyzes the personality vector to identify domain-specific reasoning patterns:

[0041] (a) Domain Clustering: The modeler groups dimension scores by decision domain (financial, career, relationship, family, moral/ethical, health). Within each domain, it identifies the dominant tendencies.

[0042] (b) Cross-Domain Comparison: The modeler identifies dimensions where the user's tendency varies significantly across domains. For example, a user might score 0.28 on financial risk tolerance but 0.81 on relationship risk tolerance — this cross-domain variation is a key feature of the decision-making profile.

[0043] (c) Values Hierarchy Construction: From the values-conflict responses, the modeler constructs a ranked values hierarchy showing which values the user prioritizes when values conflict. This hierarchy is domain-contextualized (e.g., "prioritizes honesty over loyalty in professional contexts, but loyalty over honesty in family contexts").

[0044] (d) Decision Style Profile: From the decision-style responses, the modeler identifies the user's characteristic decision-making approach, including their information-gathering pattern, their reliance on intuition vs. analysis, and their tendency toward independent vs. consultative decision-making.

[0045] The output is a structured decision-making profile encoded as a JSON object with domain-specific sections, each containing relevant dimension scores, dominant tendencies, and natural-language descriptions.

### 7. Adaptive Question Selection

[0046] In a preferred embodiment, the assessment engine selects questions adaptively based on two factors:

[0047] (a) Narrative Coverage: If the user has completed narrative conversations (Phase 1) in specific life-topic categories, the assessment engine includes additional questions targeting the corresponding psychological dimensions. For example, if the user has completed career-related narrative conversations, the assessment includes additional career risk-calibration and career decision-style questions. This enables targeted profiling in domains where narrative experience data exists, improving the quality of the combined experience + cognition data for avatar construction.

[0048] (b) Response Patterns: As the assessment progresses, the engine may adaptively select questions that probe dimensions where the user's responses have been inconsistent or where additional data points would improve the precision of the personality vector. This adaptive selection is constrained to maintain coverage across all dimension categories.

### 8. Integration with Personal Data Graph

[0049] The psychological profile (personality vector + decision-making profile) is stored in the cognition layer of the user's personal data graph, as described in the related application "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction." Cross-layer metadata linking connects the cognition layer entries to corresponding experience layer entries from the same life-topic domains, enabling the avatar construction engine to draw on both experiential knowledge and cognitive patterns when generating responses.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0050] FIG. 1 is a block diagram illustrating the system architecture of the psychological assessment system.

[0051] FIG. 2 is a flow diagram illustrating the assessment administration process including timed question presentation and response capture.

[0052] FIG. 3 is a diagram illustrating the trait extraction process including response mapping, latency weighting, and aggregation into a personality vector.

---

## DRAWINGS

### FIG. 3 — Trait Extraction with Latency Weighting

```
QUESTION RESPONSES (Example: 5 questions)
┌──────────────────────────────────────────────────────────┐
│ Q1: Values-conflict    Response: B   Latency: 2100ms    │
│ Q2: Risk-calibration   Response: A   Latency: 1800ms    │
│ Q3: Moral-reasoning    Response: C   Latency: 4500ms    │
│ Q4: Emotional-tendency Response: B   Latency: 1200ms    │
│ Q5: Decision-style     Response: D   Latency: TIMEOUT   │
└──────────────────────────────────────────────────────────┘
         │
         ▼
STEP 1: RESPONSE MAPPING (scoring_map lookup)
┌──────────────────────────────────────────────────────────┐
│ Q1-B → loyalty: 0.8, honesty: 0.3, family: 0.9          │
│ Q2-A → risk_financial: 0.15                              │
│ Q3-C → utilitarian: 0.4, deontological: 0.7             │
│ Q4-B → emotional_reactivity: 0.4, openness: 0.8         │
│ Q5   → EXCLUDED (timeout)                                │
└──────────────────────────────────────────────────────────┘
         │
         ▼
STEP 2: LATENCY WEIGHTING (baseline = 2000ms)
┌──────────────────────────────────────────────────────────┐
│ Q1: weight = 1/(1+ln(2100/2000)) = 0.95  (near baseline)│
│ Q2: weight = 1/(1+ln(1800/2000)) = 1.12  (fast=higher)  │
│ Q3: weight = 1/(1+ln(4500/2000)) = 0.55  (slow=lower)   │
│ Q4: weight = 1/(1+ln(1200/2000)) = 1.56  (very fast)    │
│ Q5: EXCLUDED                                              │
└──────────────────────────────────────────────────────────┘
         │
         ▼
STEP 3: WEIGHTED AGGREGATION → PERSONALITY VECTOR
┌──────────────────────────────────────────────────────────┐
│ loyalty:           0.8 × 0.95 = 0.76                     │
│ honesty:           0.3 × 0.95 = 0.29                     │
│ family_priority:   0.9 × 0.95 = 0.86                     │
│ risk_financial:    0.15 × 1.12 = 0.17                    │
│ utilitarian:       0.4 × 0.55 = 0.22  (low weight:       │
│ deontological:     0.7 × 0.55 = 0.39   deliberated)      │
│ emotional_react:   0.4 × 1.56 = 0.62  (high weight:      │
│ openness_feedback: 0.8 × 1.56 = 1.25   instinctive)      │
│                                                           │
│ timeout_rate: 0.20 (1/5 questions)                        │
│ Metadata: decision-style dimension has sparse data        │
└──────────────────────────────────────────────────────────┘
```

---

## CLAIMS

1. A computer-implemented system for generating a structured decision-making profile of a user for calibrating an AI avatar, the system comprising:

   a question bank storing a plurality of assessment questions organized into psychological dimension categories, each question designed to reveal a decision-making tendency of the user;

   an assessment interface configured to present the assessment questions to the user in timed succession, enforcing a maximum response time per question, and to capture for each question both a selected response and a response latency;

   a trait extraction engine configured to:
   - map each selected response to one or more positions along continuous psychological dimensions,
   - weight each mapped position by a function of the response latency, wherein shorter latencies receive higher weights, and
   - aggregate the weighted positions across all questions to produce a multi-dimensional personality vector;

   a decision pattern modeler configured to analyze the personality vector and identify domain-specific reasoning patterns, producing a structured decision-making profile encoding the user's characteristic tendencies across a plurality of decision domains; and

   a data store configured to store the decision-making profile in a cognition layer of a personal data graph associated with the user, the personal data graph further comprising an experience layer containing data from narrative conversations with the user.

2. The system of claim 1, wherein the psychological dimension categories include at least:
   - values-conflict questions presenting scenarios requiring the user to prioritize between competing values;
   - risk-calibration questions presenting scenarios with varying risk-reward tradeoffs;
   - moral-reasoning questions presenting ethical dilemmas;
   - emotional-tendency questions identifying the user's characteristic emotional responses to stimuli; and
   - decision-style questions identifying whether the user tends toward intuitive or analytical decision-making.

3. The system of claim 1, wherein the assessment interface records questions for which the user does not respond within the maximum response time as timeouts, excludes timeout responses from the personality vector calculation, and records a timeout rate as a metadata attribute of the decision-making profile.

4. The system of claim 1, wherein the decision pattern modeler identifies domain-specific reasoning patterns by clustering the user's responses by decision domain and computing separate tendency scores for each domain, such that the structured decision-making profile encodes different tendencies for different domains.

5. The system of claim 1, wherein the assessment interface selects questions based in part on life-topic categories for which the user has completed narrative conversations stored in the experience layer, enabling targeted profiling of decision-making patterns in domains where narrative experience data exists.

6. The system of claim 1, further comprising an avatar calibration engine configured to:
   - receive the structured decision-making profile and the experience layer data;
   - construct a personality simulation model that, when presented with a novel situational query, retrieves relevant experience entries from the experience layer and relevant decision-making dimensions from the decision-making profile; and
   - generate an advisory response reflecting how the user would likely approach the situation, the response being grounded in the user's documented experiences and calibrated to their measured decision-making patterns.

7. The system of claim 1, wherein the weighting function is an inverse logarithmic function of the response latency normalized by a baseline latency established during a calibration phase of the assessment, such that responses faster than the baseline receive weights greater than one and responses slower than the baseline receive weights less than one.

8. The system of claim 1, wherein the multi-dimensional personality vector comprises continuous values along at least the following dimensions: financial risk tolerance, career risk tolerance, relationship risk tolerance, empathy orientation, analytical versus intuitive tendency, loyalty versus independence, tradition versus innovation, family priority, and emotional reactivity.

---

## ABSTRACT

A computer-implemented system for administering timed psychological assessments that produce continuous multi-dimensional personality vectors for AI avatar calibration. Questions are presented in rapid-fire succession with enforced time limits to capture instinctive responses. For each question, both the response and response latency are captured. A trait extraction engine maps responses to continuous psychological dimensions and weights them by latency, with faster responses receiving higher weights. A decision pattern modeler identifies domain-specific reasoning patterns. The resulting profile is stored in a cognition layer of a personal data graph and integrated with narrative experience data for holistic avatar personality construction.
