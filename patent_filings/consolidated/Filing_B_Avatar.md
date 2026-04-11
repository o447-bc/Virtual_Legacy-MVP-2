# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

AI Avatar Construction System with Structured Multimodal Data Collection, Psychological Profiling, and Advisory Reasoning

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to a co-pending provisional application titled "Digital Legacy Preservation Platform with AI-Guided Depth-Scored Conversation, Multi-Condition Access Control, and Dual-Persona User Management," filed concurrently herewith and incorporated by reference in its entirety. The related application describes the conversation engine, access control system, and user management system upon which the present invention builds.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to AI-powered digital avatar systems, and more particularly to: (a) a structured multimodal data collection pipeline that combines quality-controlled narrative elicitation with rapid-fire psychological profiling to collect data structured for AI avatar construction; (b) a timed psychological assessment system that produces continuous multi-dimensional personality vectors and domain-specific decision-making profiles; and (c) an advisory reasoning engine that generates personalized advisory responses grounded in an individual's documented experiences and measured decision-making patterns, with transparent attribution.

---

## BACKGROUND OF THE INVENTION

### Problems with Existing Avatar Data Collection

[0003] Creating a convincing AI avatar that can simulate a specific individual's personality, voice, visual likeness, and decision-making behavior requires extensive, high-quality data across multiple modalities. Existing approaches suffer from several limitations.

[0004] First, dedicated data collection sessions (voice cloning studios, 3D face scanning, structured interviews) require the subject to participate in activities whose sole purpose is data collection. This results in lower engagement, less authentic data, and a poor user experience. Subjects who know they are "training an AI" tend to perform rather than behave naturally.

[0005] Second, passive data collection from existing digital footprints (social media posts, emails, messaging history) produces unstructured data of highly variable quality. Social media posts are often performative, and the data lacks structured coverage across life domains.

[0006] Third, no existing system ensures collected narrative data meets a minimum depth or richness threshold suitable for avatar personality modeling. Existing platforms accept whatever the user provides, regardless of quality.

### Problems with Existing Psychological Assessment for AI

[0007] Fourth, traditional psychological assessments (Myers-Briggs, Big Five) produce categorical labels too coarse for individual-level decision-making simulation. Two people classified identically may make very different decisions.

[0008] Fifth, existing assessments are untimed, capturing deliberated self-reports that reflect how people want to be perceived rather than how they actually behave. For avatar calibration, actual behavioral patterns are far more valuable.

[0009] Sixth, existing assessments do not capture domain-specific variation. A person may be risk-averse financially but risk-seeking in relationships. Global trait scores average across domains, losing this information.

### Problems with Existing Posthumous AI Systems

[0010] Seventh, existing posthumous chatbots (trained on social media or messaging history) can reproduce communication style but cannot simulate decision-making. When asked "What would Mom do about this job offer?", these systems either refuse, generate generic advice, or hallucinate responses contradicting the individual's actual values.

[0011] Eighth, no existing system provides attribution for AI-generated advisory responses — no system cites the specific experiences or reasoning patterns that informed a particular piece of advice. Without attribution, users cannot evaluate whether the response is genuinely grounded in the individual's personality.

[0012] There is therefore a need for an integrated system that collects quality-controlled multimodal data as a byproduct of a meaningful activity, profiles the individual's decision-making patterns through timed assessment, and generates grounded advisory responses with transparent attribution.

---

## SUMMARY OF THE INVENTION

[0013] The present invention provides an AI avatar construction system operating in three phases. In Phase 1, a narrative collection engine conducts AI-moderated voice conversations with cumulative depth scoring across structured life-topic categories, simultaneously capturing voice audio and video recordings. In Phase 2, a psychological assessment engine administers rapid-fire timed questions to capture instinctive decision-making patterns, producing continuous personality vectors with latency-based weighting and domain-specific decision profiles. In Phase 3, an advisory reasoning engine performs dual-source retrieval from a personal knowledge graph and psychological profile to generate advisory responses with structured attribution.

[0014] All collected data is organized into a three-layer personal data graph: an experience layer (transcripts and summaries), a cognition layer (personality vectors and decision profiles), and a presence layer (voice and video recordings), with cross-layer metadata linking enabling holistic avatar construction.

---

## DETAILED DESCRIPTION OF THE INVENTION

### Part I — Phase 1: Quality-Controlled Narrative Collection for Avatar Data

#### I.1 — Dual-Purpose Pipeline Architecture

[0015] The present invention recognizes that a legacy preservation activity — where users answer guided life questions through AI-moderated voice conversations — simultaneously serves as a structured data collection pipeline for AI avatar construction. The user's primary motivation is memory preservation; the avatar training data is a byproduct. This dual-purpose design produces more authentic personality data than dedicated avatar data collection sessions because users are focused on sharing genuine memories rather than performing for an AI training system.

[0016] The narrative collection engine is described in detail in the related application "Digital Legacy Preservation Platform with AI-Guided Depth-Scored Conversation, Multi-Condition Access Control, and Dual-Persona User Management." The key features relevant to avatar data collection are summarized here.

#### I.2 — Depth Scoring as Data Quality Control

[0017] During each conversation, a scoring model evaluates the narrative depth of each user response and produces a numeric depth score. Scores accumulate across turns, and the conversation continues until a configurable quality threshold is met (e.g., cumulative score ≥ 12). This mechanism ensures that every collected narrative meets a minimum richness standard suitable for avatar personality modeling. Superficial, one-word answers are insufficient to reach the threshold — the system requires genuine depth and detail.

[0018] The depth scoring serves a dual purpose: for the user, it ensures their legacy narratives are meaningful and complete; for the avatar system, it ensures the training data contains sufficient personality signal for accurate simulation.

#### I.3 — Structured Question Categories for Personality Coverage

[0019] Questions are organized into life-topic categories (childhood, career, relationships, values, etc.) with per-category progress tracking and level progression. This structure ensures broad personality coverage — the user is guided to share experiences across all major life domains, not just the topics they find easiest to discuss. For avatar construction, this breadth is critical: an avatar trained only on career stories would be unable to advise on family matters.

#### I.4 — Multi-Modal Data Accumulation

[0020] Throughout Phase 1, the system accumulates four types of data per user:

[0021] (a) Conversation transcripts with per-turn depth scores across all life-topic categories, stored in encrypted cloud storage and indexed in a question status database.

[0022] (b) AI-generated summaries (one-sentence, detailed, thoughtfulness score) for each conversation, serving as pre-processed knowledge representations for the experience layer.

[0023] (c) Voice audio samples from each conversation turn, stored at hierarchical paths (conversations/{userId}/{questionId}/audio/turn-{N}-{timestamp}.webm). Across dozens of conversations, this accumulates hours of voice samples spanning different emotional contexts, topics, and speech patterns — diverse training data for voice synthesis.

[0024] (d) Video recordings (both direct video responses and supplementary video memories recorded after conversations), capturing the user's facial appearance, expressions, and mannerisms. Thumbnails are extracted via FFmpeg for indexing.

### Part II — Phase 2: Rapid-Fire Psychological Profiling

#### II.1 — Assessment Design Philosophy

[0025] Phase 1 captures what happened to a person and how they feel about it. Phase 2 captures how they make decisions. This distinction is critical for the advisory avatar mode ("What would they do?") — you cannot simulate someone's decision-making from their life stories alone. The rapid-fire assessment bridges the gap between "I know what this person experienced" and "I know how this person thinks."

[0026] The rapid-fire format is a deliberate design choice grounded in dual-process theory from cognitive psychology. Fast responses (System 1) reflect automatic, instinctive cognitive patterns, while slow responses (System 2) reflect deliberate, effortful reasoning. For avatar personality calibration, System 1 responses are more predictive of actual real-world behavior.

#### II.2 — Question Bank

[0027] The psychological assessment engine maintains a question bank organized into psychological dimension categories:

[0028] (a) Values-Conflict Questions: Scenarios requiring the user to prioritize between competing values (loyalty vs. honesty, individual vs. collective, tradition vs. innovation, security vs. freedom). Example: "Your best friend asks you to lie for them to protect them from consequences. Do you lie or tell the truth?"

[0029] (b) Risk-Calibration Questions: Scenarios with varying risk-reward tradeoffs segmented by life domain (financial, career, relationship, health). Example: "You have a stable job with good benefits. A startup offers you equity but lower salary. What do you do?"

[0030] (c) Moral-Reasoning Questions: Ethical dilemmas revealing the user's moral reasoning framework (utilitarian, deontological, virtue-based). Adapted from established moral psychology research for rapid-fire administration.

[0031] (d) Emotional-Tendency Questions: Stimuli revealing characteristic emotional responses (to criticism, praise, unexpected change, conflict). Example: "When someone criticizes your work in front of others, your first instinct is to: (A) defend yourself, (B) listen and reflect, (C) feel hurt but say nothing, (D) ask for specific examples."

[0032] (e) Decision-Style Questions: Questions revealing intuitive vs. analytical tendency, independent vs. consultative approach. Example: "When choosing between two job offers, you: (A) go with your gut, (B) create a comparison spreadsheet, (C) ask five trusted people, (D) sleep on it for a week."

[0033] Each question is associated with metadata: dimension_category, response_options, scoring_map (mapping responses to positions along psychological dimensions), max_response_time, and difficulty_level.

#### II.3 — Timed Assessment Administration

[0034] FIG. 2 illustrates the assessment administration flow.

[0035] The assessment interface presents questions in rapid succession with enforced maximum response times (e.g., 10 seconds for forced-choice, 20 seconds for short text). A visible countdown timer creates mild time pressure encouraging instinctive responses. Upon response or timeout, the next question appears immediately.

[0036] The first 3-5 questions serve as a calibration phase, establishing a baseline_latency for the user that accounts for individual differences in reading speed and device interaction.

[0037] For each question, the system captures: (a) the selected response, (b) the response latency in milliseconds (from question render to submission), (c) whether the question timed out, (d) the question's sequence position (for fatigue detection), and (e) device metadata.

#### II.4 — Trait Extraction with Latency Weighting

[0038] FIG. 3 illustrates the trait extraction process.

[0039] Step 1 — Response Mapping: Each non-timeout response is mapped via the scoring_map to positions along continuous psychological dimensions (0-1 scale). A single response may map to multiple dimensions.

[0040] Step 2 — Latency Weighting: Each mapped position is multiplied by a weight derived from the response latency:

    weight = 1 / (1 + ln(latency_ms / baseline_ms))

This produces weight > 1 for faster-than-baseline responses (instinctive, high authenticity), weight ≈ 1 for baseline responses, and weight < 1 for slower responses (deliberated, lower authenticity).

[0041] Step 3 — Timeout Handling: Timed-out questions are excluded from the vector calculation. The timeout rate is recorded as metadata — a high timeout rate on a specific dimension may indicate decision avoidance in that domain.

[0042] Step 4 — Aggregation: Weighted positions across all questions are aggregated per dimension to produce a multi-dimensional personality vector with continuous values along dimensions including: risk_tolerance_financial, risk_tolerance_career, risk_tolerance_relationship, empathy_orientation, analytical_vs_intuitive, loyalty_vs_independence, tradition_vs_innovation, family_priority, achievement_orientation, emotional_reactivity, openness_to_feedback, resilience, utilitarian_vs_deontological, independent_vs_consultative.

#### II.5 — Decision Pattern Modeling

[0043] The decision pattern modeler analyzes the personality vector to identify domain-specific reasoning patterns:

[0044] (a) Domain Clustering: Groups dimension scores by decision domain (financial, career, relationship, family, moral, health) and identifies dominant tendencies within each.

[0045] (b) Cross-Domain Comparison: Identifies dimensions where tendencies vary significantly across domains (e.g., risk-averse financially but risk-seeking in relationships).

[0046] (c) Values Hierarchy Construction: From values-conflict responses, constructs a ranked values hierarchy showing which values the user prioritizes when values conflict, contextualized by domain.

[0047] (d) Decision Style Profile: Identifies characteristic decision-making approach (intuitive vs. analytical, independent vs. consultative, fast vs. deliberate).

[0048] The output is a structured decision-making profile encoded as JSON with domain-specific sections.

#### II.6 — Adaptive Question Selection

[0049] The assessment engine selects questions adaptively based on: (a) narrative coverage — if the user completed career conversations in Phase 1, additional career-domain questions are included; and (b) response patterns — questions probing dimensions with inconsistent responses are prioritized to improve vector precision.

### Part III — The Three-Layer Personal Data Graph

[0050] FIG. 4 illustrates the three-layer architecture.

[0051] The unified data store maintains a personal data graph per user comprising:

[0052] (a) Experience Layer: Conversation transcripts with per-turn depth scores, AI-generated summaries (one-sentence, detailed, thoughtfulness score), organized by life-topic category. Stored across NoSQL database (metadata) and object storage (full transcripts, audio).

[0053] (b) Cognition Layer: Multi-dimensional personality vector, structured decision-making profile with domain-specific tendencies, raw assessment responses with latencies, assessment metadata (timeout rate, calibration baseline). Stored in NoSQL database.

[0054] (c) Presence Layer: Voice audio samples from conversation turns (accumulated across conversations, diverse emotional contexts), video recordings with thumbnails. Stored in encrypted object storage.

[0055] Cross-layer metadata linking via shared key structures (userId + questionId + questionType) enables retrieval of related data across layers. For example, given a career query, the system retrieves career narratives (experience), career risk tolerance (cognition), and career conversation audio (presence).

### Part IV — Phase 3: Avatar Construction and Advisory Reasoning

#### IV.1 — Avatar Model Components

[0056] An avatar construction engine processes the three-layer data graph to produce:

[0057] (a) Personality Simulation Model: Constructed from experience and cognition layers. Implemented as a retrieval-augmented generation (RAG) system where the experience layer serves as the retrieval corpus and the cognition layer provides calibration parameters. Personality attributes from higher-depth-score conversations are weighted more heavily.

[0058] (b) Voice Synthesis Model: Constructed from accumulated voice audio samples in the presence layer. The diverse samples across emotional contexts and topics provide rich training data.

[0059] (c) Visual Likeness Model: Constructed from video recordings in the presence layer, capturing facial appearance, expressions, and mannerisms.

#### IV.2 — Advisory Reasoning Engine ("What Would They Do?")

[0060] FIG. 5 illustrates the advisory reasoning flow.

[0061] When a beneficiary submits a situational query (e.g., "What would Dad do about this job offer?"), the system processes it as follows:

[0062] Step 1 — Access Verification: Verifies the beneficiary has been granted avatar interaction permission under the access control system described in the related application.

[0063] Step 2 — Query Parsing: Identifies the decision domain (career, financial, relationships, etc.), key factors, query type ("what would they do" / "what would they think"), and emotional context.

[0064] Step 3 — Dual-Source Retrieval:

[0065] (a) Knowledge Graph Retrieval: Queries the experience layer using semantic similarity to find relevant life experiences, stated opinions, and relationship context. Retrieved entries include their depth scores for weighting.

[0066] (b) Psychological Profile Retrieval: Queries the cognition layer to identify relevant decision-making dimensions for the query's domain (e.g., financial risk tolerance, career risk tolerance, family priority, decision style).

[0067] Step 4 — Reasoning and Response Generation: A reasoning LLM receives the query, retrieved experience entries (weighted by depth scores), and retrieved psychological dimensions. The model generates a response that: reflects how the individual would likely approach the situation; draws on documented experiences; is calibrated to measured decision-making patterns; acknowledges uncertainty where data is sparse; and maintains the individual's communication style.

[0068] Step 5 — Attribution Generation: The system produces a structured attribution component — a list of citations, each comprising: a source reference (specific conversation or assessment response), a relevance score (0-1), a natural-language explanation of how the cited data informed the advisory, and the data layer (experience or cognition). Attribution makes the avatar's reasoning transparent and auditable.

[0069] Step 6 — Confidence Scoring: A confidence score is computed based on: knowledge graph coverage (number and relevance of retrieved entries), psychological profile coverage (whether relevant dimensions have data), domain match (query domain vs. available data domains), and consistency (whether retrieved data points in a consistent direction). Low-confidence responses are flagged with qualifications.

[0070] Step 7 — Multimodal Delivery: The advisory is optionally delivered through voice synthesis (cloned from the individual's audio samples) and visual likeness rendering, in addition to text with attribution.

#### IV.3 — Safeguards

[0071] Responses are framed as "based on what [person] shared and their measured tendencies, they would likely..." rather than definitive statements. Low-confidence responses are clearly flagged. Attribution enables verification. Access is governed by the individual's pre-configured conditions.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0072] FIG. 1 is a block diagram illustrating the overall system architecture of the AI avatar construction system showing the three-phase pipeline.

[0073] FIG. 2 is a flow diagram illustrating the Phase 2 rapid-fire psychological assessment administration process.

[0074] FIG. 3 is a diagram illustrating the trait extraction process with response mapping, latency weighting, and aggregation into a personality vector.

[0075] FIG. 4 is a block diagram illustrating the three-layer personal data graph architecture with cross-layer metadata linking.

[0076] FIG. 5 is a flow diagram illustrating the Phase 3 advisory reasoning process with dual-source retrieval and attribution generation.

---

## DRAWINGS

### FIG. 1 — Three-Phase Avatar Construction Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: QUALITY-CONTROLLED NARRATIVE COLLECTION                │
│  (Implemented — see related application for full detail)         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ AI-Guided    │  │ Video Memory │  │ Summarization Engine   │ │
│  │ Conversation │  │ Recording    │  │ (1-sentence + detailed │ │
│  │ with Depth   │  │              │  │  + thoughtfulness)     │ │
│  │ Scoring      │  │              │  │                        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         │                 │                       │              │
│         ▼                 ▼                       ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Accumulated Data:                                        │    │
│  │ • Transcripts with depth scores (per category)           │    │
│  │ • Voice audio (hours across conversations)               │    │
│  │ • Video recordings + thumbnails                          │    │
│  │ • AI summaries (knowledge representations)               │    │
│  └─────────────────────────┬───────────────────────────────┘    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: RAPID-FIRE PSYCHOLOGICAL PROFILING                     │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Timed Question   │  │ Trait Extraction  │  │ Decision      │ │
│  │ Presentation     │  │ Engine           │  │ Pattern       │ │
│  │ (10-20s max)     │  │ (Latency-        │  │ Modeler       │ │
│  │                  │  │  weighted)        │  │ (Domain-      │ │
│  │ Response +       │  │                  │  │  specific)    │ │
│  │ Latency capture  │  │ Continuous       │  │               │ │
│  │                  │  │ personality      │  │ Structured    │ │
│  │                  │  │ vectors          │  │ profile       │ │
│  └──────┬───────────┘  └──────┬───────────┘  └──────┬────────┘ │
│         └──────────────────────┼──────────────────────┘         │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Psychological Profile:                                   │    │
│  │ • Multi-dimensional personality vector                   │    │
│  │ • Domain-specific decision tendencies                    │    │
│  │ • Values hierarchy                                       │    │
│  │ • Decision style profile                                 │    │
│  └─────────────────────────┬───────────────────────────────┘    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  THREE-LAYER PERSONAL DATA GRAPH                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ EXPERIENCE   │  │ COGNITION    │  │ PRESENCE               │ │
│  │ LAYER        │  │ LAYER        │  │ LAYER                  │ │
│  │              │  │              │  │                        │ │
│  │ Transcripts  │  │ Personality  │  │ Voice audio samples    │ │
│  │ Summaries    │  │ vectors      │  │ Video recordings       │ │
│  │ Depth scores │  │ Decision     │  │ Thumbnails             │ │
│  │ Per category │  │ profiles     │  │                        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         └──────────────────┼──────────────────────┘              │
│              Cross-layer metadata linking                        │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: AVATAR CONSTRUCTION + ADVISORY REASONING               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Avatar Model:                                             │   │
│  │ • Personality Simulation (RAG + cognition calibration)    │   │
│  │ • Voice Synthesis (from accumulated audio)                │   │
│  │ • Visual Likeness (from video recordings)                 │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────┼───────────────────────────────┐   │
│  │ Advisory Engine:          ▼                               │   │
│  │ "What would Dad do about this job offer?"                 │   │
│  │                                                           │   │
│  │ 1. Parse query → domain(s)                                │   │
│  │ 2. Retrieve from experience layer (semantic similarity)   │   │
│  │ 3. Retrieve from cognition layer (domain mapping)         │   │
│  │ 4. Reasoning LLM synthesizes → advisory response          │   │
│  │ 5. Generate attribution (citations + relevance + explain) │   │
│  │ 6. Compute confidence score                               │   │
│  │ 7. Deliver via text + voice clone + visual likeness       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### FIG. 3 — Trait Extraction with Latency Weighting

```
RESPONSES (Example)
┌──────────────────────────────────────────────────────────┐
│ Q1: Values-conflict    Response: B   Latency: 2100ms    │
│ Q2: Risk-calibration   Response: A   Latency: 1800ms    │
│ Q3: Moral-reasoning    Response: C   Latency: 4500ms    │
│ Q4: Emotional-tendency Response: B   Latency: 1200ms    │
│ Q5: Decision-style     Response: D   Latency: TIMEOUT   │
└──────────────────────────────────────────────────────────┘
         │
         ▼
STEP 1: RESPONSE MAPPING (scoring_map)
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
│ weight = 1 / (1 + ln(latency / baseline))                │
│                                                          │
│ Q1: 2100ms → weight = 0.95  (near baseline)              │
│ Q2: 1800ms → weight = 1.12  (fast → higher weight)       │
│ Q3: 4500ms → weight = 0.55  (slow → lower weight)        │
│ Q4: 1200ms → weight = 1.56  (very fast → highest weight) │
└──────────────────────────────────────────────────────────┘
         │
         ▼
STEP 3: WEIGHTED AGGREGATION → PERSONALITY VECTOR
┌──────────────────────────────────────────────────────────┐
│ loyalty:           0.8 × 0.95 = 0.76                     │
│ family_priority:   0.9 × 0.95 = 0.86                     │
│ risk_financial:    0.15 × 1.12 = 0.17                    │
│ deontological:     0.7 × 0.55 = 0.39  (deliberated →    │
│                                         lower weight)    │
│ openness_feedback: 0.8 × 1.56 = 1.25  (instinctive →    │
│                                         higher weight)   │
│ timeout_rate: 0.20                                       │
└──────────────────────────────────────────────────────────┘
```

### FIG. 5 — Advisory Reasoning with Dual-Source Retrieval

```
BENEFICIARY QUERY: "What would Dad do about this startup job offer?"
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ ACCESS CONTROL   │─NO─►│ Denied + unmet   │
│ VERIFICATION     │     │ conditions       │
└───────┬──────────┘     └──────────────────┘
        │ YES
        ▼
┌──────────────────┐
│ QUERY PARSER     │
│ Domains: career, │
│ financial,       │
│ relocation       │
└───────┬──────────┘
   ┌────┴────┐
   ▼         ▼
┌──────────────┐ ┌──────────────────┐
│ EXPERIENCE   │ │ COGNITION        │
│ LAYER        │ │ LAYER            │
│ RETRIEVAL    │ │ RETRIEVAL        │
│              │ │                  │
│ Career conv. │ │ Financial risk:  │
│ (score 4.2)  │ │   0.35 (cautious)│
│ Move story   │ │ Career risk:     │
│ (score 3.8)  │ │   0.62 (moderate)│
│ Family values│ │ Family priority: │
│ (score 4.8)  │ │   0.86 (high)    │
│ Career advice│ │ Decision style:  │
│ (score 3.5)  │ │   analytical+gut │
└──────┬───────┘ └────────┬─────────┘
       └────────┬─────────┘
                ▼
┌──────────────────────────────────────────┐
│ REASONING LLM                             │
│ Synthesizes query + experiences + profile  │
│ Maintains individual's communication style │
└──────────┬───────────────────────────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌──────┐┌──────┐┌──────────┐
│ATTRI-││CONFI-││MULTIMODAL│
│BUTION││DENCE ││DELIVERY  │
│      ││SCORE ││          │
│Cite: ││      ││Text +    │
│Conv. ││ 82%  ││Voice     │
│ref + ││(High)││clone +   │
│psych ││      ││Visual    │
│dim + ││      ││likeness  │
│expl. ││      ││          │
└──────┘└──────┘└──────────┘
```

---

## CLAIMS

### Claim Set A — Multimodal Data Collection for Avatar Construction

1. A computer-implemented system for collecting multimodal personal data structured for constructing an AI avatar capable of simulating a person's decision-making behavior, the system comprising:

   a narrative collection engine configured to conduct multi-turn voice conversations with a user across a plurality of life-topic categories, wherein for each conversation a scoring model evaluates narrative depth and produces a numeric depth score, depth scores accumulate into a cumulative score, and the conversation continues until the cumulative score meets or exceeds a configurable quality threshold;

   an audio and video capture subsystem configured to record the user's voice audio during each conversation turn and to record video of the user, storing recordings in association with corresponding conversation data;

   a psychological assessment engine configured to administer a rapid-fire assessment comprising questions presented in timed succession designed to elicit instinctive responses revealing decision-making patterns, values hierarchies, and cognitive tendencies, wherein the assessment engine captures both the user's response and a response latency for each question;

   a trait extraction engine configured to process the responses and response latencies to produce a multi-dimensional personality vector representing the user's position along a plurality of continuous psychological dimensions;

   a decision pattern modeler configured to analyze the personality vector and identify characteristic reasoning patterns, producing a structured decision-making profile; and

   a unified data store configured to maintain a personal data graph comprising an experience layer containing conversation transcripts and AI-generated summaries, a cognition layer containing the personality vector and decision-making profile, and a presence layer containing voice audio samples and video recordings, with cross-layer metadata linking.

2. The system of claim 1, wherein the psychological assessment engine presents questions from categories including values-conflict, risk-calibration, moral-reasoning, emotional-tendency, and decision-style questions, with separate dimension scores per category.

3. The system of claim 1, wherein the trait extraction engine weights responses with shorter latencies more heavily using an inverse logarithmic function of the latency normalized by a calibration baseline.

4. The system of claim 1, further comprising an avatar construction engine configured to construct a personality simulation model from the experience and cognition layers, a voice synthesis model from the presence layer audio, and a visual likeness model from the presence layer video, wherein the personality simulation model weights attributes from higher-depth-score conversations more heavily.

5. The system of claim 1, wherein the assessment engine selects questions adaptively based on life-topic categories for which the user has completed narrative conversations, enabling targeted profiling in domains where narrative data exists.

6. The system of claim 1, wherein the rapid-fire assessment enforces a maximum response time per question, records timeouts as excluded from the personality vector, and records the timeout rate as profile metadata.

7. The system of claim 1, wherein the decision pattern modeler identifies domain-specific reasoning patterns by computing separate tendency scores per decision domain, such that the profile encodes different tendencies for different domains.

### Claim Set B — Advisory Reasoning Engine

8. A computer-implemented method for generating an advisory response in the persona of a specific individual, the method comprising:

   receiving a situational query requesting advice attributed to a specific individual;

   retrieving, from a personal knowledge graph, relevant experience entries based on semantic similarity to the query, the knowledge graph constructed from depth-scored narrative conversations;

   retrieving, from a psychological profile, relevant decision-making dimensions based on the query's domain, the profile constructed from a rapid-fire assessment capturing instinctive responses;

   providing the query, retrieved experience entries, and retrieved decision-making dimensions to a reasoning language model;

   generating an advisory response grounded in the individual's experiences and calibrated to their measured decision-making patterns; and

   generating an attribution component identifying the specific experience entries and decision-making dimensions that informed the response.

9. The method of claim 8, further comprising computing a confidence score based on data density and relevance, and appending a qualification when confidence is below a threshold.

10. The method of claim 8, further comprising delivering the response through a voice synthesis model trained on the individual's audio samples.

11. The method of claim 8, wherein the attribution component is structured as citations each comprising a source reference, a relevance score, and a natural-language explanation.

12. The method of claim 8, further comprising verifying avatar interaction permission under an access control system evaluating conditions configured by the individual.

13. The method of claim 8, wherein retrieved experience entries are weighted by their depth scores when provided to the reasoning model.

### Claim Set C — Psychological Assessment System

14. A computer-implemented system for generating a structured decision-making profile for calibrating an AI avatar, the system comprising:

    a question bank storing assessment questions organized into psychological dimension categories;

    an assessment interface presenting questions in timed succession with enforced maximum response times, capturing both selected responses and response latencies;

    a trait extraction engine configured to map responses to continuous psychological dimensions, weight by latency, and aggregate into a multi-dimensional personality vector;

    a decision pattern modeler configured to identify domain-specific reasoning patterns from the personality vector; and

    a data store configured to store the profile in a cognition layer of a personal data graph linked to an experience layer from narrative conversations.

15. The system of claim 14, wherein the weighting function is an inverse logarithmic function of the latency normalized by a baseline established during a calibration phase.

16. The system of claim 14, wherein the personality vector comprises continuous values along at least: financial risk tolerance, career risk tolerance, relationship risk tolerance, empathy orientation, analytical versus intuitive tendency, loyalty versus independence, family priority, and emotional reactivity.

---

## ABSTRACT

An AI avatar construction system operating in three phases. Phase 1 conducts AI-moderated voice conversations with cumulative depth scoring across life-topic categories, simultaneously capturing voice audio and video as avatar training data. Phase 2 administers rapid-fire timed psychological assessments to capture instinctive decision-making patterns, producing continuous personality vectors with latency-based weighting and domain-specific decision profiles. Phase 3 performs dual-source retrieval from a personal knowledge graph and psychological profile to generate advisory responses with structured attribution and confidence scoring. All data is organized in a three-layer personal data graph (experience, cognition, presence) with cross-layer linking for holistic avatar construction.
