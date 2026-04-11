# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction," "Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination," "Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation," and "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to AI-powered advisory systems, and more particularly to a computer-implemented system and method for generating advisory responses in the persona of a specific individual, wherein the responses are grounded in the individual's documented life experiences and calibrated to their empirically-measured decision-making patterns, with transparent attribution of the sources informing each advisory response.

---

## BACKGROUND OF THE INVENTION

[0003] The loss of a family member, mentor, or trusted advisor creates a permanent gap in the decision-making support network of those left behind. When facing important life decisions, people frequently wish they could ask a deceased parent, grandparent, or mentor for guidance. This need is particularly acute for decisions in domains where the deceased individual had significant experience or wisdom.

[0004] Existing AI chatbot and avatar systems are fundamentally inadequate for this purpose due to several critical limitations.

[0005] First, existing posthumous chatbot systems (such as those trained on social media posts or messaging history) can reproduce a person's communication style but cannot simulate their decision-making. When asked "What would Mom do about this job offer?", these systems either refuse to answer, generate generic advice unrelated to the specific individual, or hallucinate responses that may contradict the individual's actual values and reasoning patterns. The fundamental problem is that these systems lack a model of the individual's decision-making framework.

[0006] Second, existing AI advisory systems (such as general-purpose chatbots or life coaching applications) provide generic advice based on population-level best practices. They cannot personalize advice to reflect a specific individual's values, risk tolerance, moral reasoning, or life experiences. The advice they generate is indistinguishable from advice that could be given to any person.

[0007] Third, no existing system provides attribution for AI-generated advisory responses — that is, no system cites the specific experiences, values, or reasoning patterns that informed a particular piece of advice. Without attribution, users cannot evaluate whether the AI's response is genuinely grounded in the individual's actual personality or is a hallucination. This lack of transparency is a fundamental barrier to trust.

[0008] Fourth, existing systems do not combine experiential knowledge (what a person lived through) with cognitive profiling (how a person makes decisions) when generating advisory responses. Life stories alone are insufficient for decision simulation because they capture outcomes but not the reasoning processes that led to those outcomes. Psychological profiles alone are insufficient because they lack the contextual richness of lived experience.

[0009] There is therefore a need for a system that can generate advisory responses genuinely grounded in a specific individual's documented experiences and measured decision-making patterns, with transparent attribution that enables users to evaluate the basis for each advisory response.

---

## SUMMARY OF THE INVENTION

[0010] The present invention provides a computer-implemented system and method for generating advisory responses in the persona of a specific individual. A requesting user (beneficiary) submits a situational query in the form "What would [person] do about [situation]?" to an advisory reasoning engine.

[0011] The engine performs dual-source retrieval: it queries a personal knowledge graph derived from the individual's depth-scored narrative conversations to identify relevant life experiences, and it queries a psychological profile derived from a rapid-fire assessment to identify relevant decision-making dimensions. A reasoning language model synthesizes the retrieved data with the query context to generate an advisory response calibrated to the specific individual.

[0012] Each response includes an attribution component that cites the specific experiences and psychological traits that informed the advisory, making the reasoning transparent and auditable. The response is optionally delivered through a voice synthesis model and visual likeness model replicating the individual's physical presence.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture Overview

[0013] Referring now to the drawings, FIG. 1 illustrates the overall system architecture of the advisory response generation system according to an embodiment of the present invention. The system comprises an advisory interface (110), a query parser (120), a knowledge graph retrieval engine (130), a psychological profile retrieval engine (140), a reasoning language model (150), an attribution generator (160), a confidence scorer (170), and a multimodal delivery engine (180).

[0014] The advisory interface (110) is a component of a client application through which a requesting user (beneficiary) submits situational queries and receives advisory responses. The interface accepts natural language queries and presents responses in text, audio, and optionally video format.

[0015] The query parser (120) analyzes the situational query to identify the decision domain (e.g., career, relationships, financial, health, family, moral/ethical), key entities and relationships mentioned in the query, the type of advice sought (e.g., "what would they do," "what would they think," "how would they feel"), and contextual factors relevant to retrieval.

[0016] The knowledge graph retrieval engine (130) queries the personal knowledge graph (the experience layer of the individual's personal data graph) to retrieve relevant experience entries based on semantic similarity to the situational query.

[0017] The psychological profile retrieval engine (140) queries the individual's psychological profile (the cognition layer of the personal data graph) to retrieve relevant decision-making dimensions based on the identified decision domain.

[0018] The reasoning language model (150) synthesizes the query, retrieved experience entries, and retrieved psychological dimensions to generate an advisory response.

[0019] The attribution generator (160) produces a structured attribution component identifying the specific data sources that informed the advisory response.

[0020] The confidence scorer (170) evaluates the density and relevance of available data to produce a confidence score for the advisory response.

[0021] The multimodal delivery engine (180) optionally renders the advisory response through voice synthesis and visual likeness models.

### 2. The Personal Knowledge Graph (Experience Layer)

[0022] The personal knowledge graph is constructed from the individual's depth-scored narrative conversations as described in the related application "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction." The knowledge graph contains:

[0023] (a) Conversation entries organized by life-topic category (e.g., childhood, career, relationships, values), each containing the full conversation transcript, per-turn depth scores, AI-generated one-sentence and detailed summaries, and thoughtfulness scores.

[0024] (b) Extracted entities and relationships, including people mentioned by the individual (family members, colleagues, mentors), places, organizations, and events.

[0025] (c) Stated opinions and values expressed during conversations, tagged by topic and confidence level (derived from depth scores — higher-scored responses indicate more deeply held views).

[0026] (d) Semantic embeddings of conversation summaries enabling vector similarity search for retrieval.

### 3. The Psychological Profile (Cognition Layer)

[0027] The psychological profile is constructed from the individual's rapid-fire assessment as described in the related application "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation." The profile contains:

[0028] (a) A multi-dimensional personality vector with continuous values along dimensions including risk tolerance, empathy orientation, analytical vs. intuitive tendency, loyalty vs. independence, tradition vs. innovation, and others.

[0029] (b) A structured decision-making profile encoding domain-specific tendencies (e.g., risk-averse in financial decisions, risk-seeking in relationship decisions).

[0030] (c) Values hierarchy data derived from values-conflict assessment questions, indicating which values the individual prioritizes when values conflict.

[0031] (d) Moral reasoning framework indicators (utilitarian, deontological, virtue-based tendencies) derived from moral-reasoning assessment questions.

### 4. Query Processing and Dual-Source Retrieval

[0032] FIG. 2 illustrates the query processing and dual-source retrieval flow according to an embodiment of the present invention.

[0033] When a requesting user submits a situational query (e.g., "What would Dad do about this job offer from a startup? I'd have to move across the country and take a pay cut, but the equity could be worth a lot."), the system processes the query as follows:

[0034] Step 1 — Access Verification: Before processing the query, the system verifies that the requesting user has been granted avatar interaction permission under the access control system governing the individual's digital legacy. The access control system evaluates one or more access conditions configured by the individual (immediate, time-delayed, inactivity-triggered, or manual release). If access is not granted, the query is rejected with an appropriate message indicating which conditions remain unmet.

[0035] Step 2 — Query Parsing: The query parser analyzes the natural language query to identify: (a) the decision domain — in this example, "career" and "financial" and "relocation"; (b) key factors — "startup equity," "pay cut," "cross-country move"; (c) the query type — "what would they do" (advisory/decision); (d) emotional context — implied uncertainty and desire for guidance.

[0036] Step 3 — Knowledge Graph Retrieval: The knowledge graph retrieval engine queries the personal knowledge graph using the identified decision domain and key factors. The retrieval process uses semantic similarity search to find experience entries relevant to the query. In this example, the engine might retrieve: (a) a conversation about the individual's own career changes and what motivated them; (b) a conversation about the individual's views on financial risk and security; (c) a conversation about the individual's experience with geographic moves; (d) a conversation about the individual's advice to their children about career decisions. Each retrieved entry includes its depth score and thoughtfulness score, which are used to weight its influence on the advisory response.

[0037] Step 4 — Psychological Profile Retrieval: The psychological profile retrieval engine identifies which dimensions of the personality vector and decision-making profile are most relevant to the query's decision domain. In this example, the engine retrieves: (a) the individual's financial risk tolerance score (e.g., 0.35 — moderately risk-averse); (b) the individual's career risk tolerance score (e.g., 0.62 — moderately risk-seeking); (c) the individual's values hierarchy showing family proximity ranked highly; (d) the individual's decision style showing a tendency toward analytical decision-making with gut-check validation.

[0038] Step 5 — Reasoning and Response Generation: The reasoning language model receives the original query, the retrieved experience entries (with depth scores), and the retrieved psychological dimensions as a structured prompt. The model is instructed to generate a response that: (a) reflects how the specific individual would likely approach this situation; (b) draws on their documented experiences where relevant; (c) is calibrated to their measured decision-making patterns; (d) acknowledges uncertainty where data is sparse; and (e) maintains the individual's characteristic communication style as observed in their conversation transcripts.

[0039] In this example, the model might generate a response such as: "Your dad was someone who valued financial security — he scored on the cautious side when it came to money decisions. But when it came to career moves, he was more willing to take a chance, especially when he believed in what he was doing. He talked about how his own move to [city] early in his career was scary but ended up being the best decision he made. He also said he always wished he'd taken more risks when he was young. That said, family was everything to him — being far from the people he loved would have weighed heavily. He'd probably tell you to really think about whether the startup's mission excites you, because that's what would make the sacrifice worth it to him."

### 5. Attribution Generation

[0040] FIG. 3 illustrates the attribution generation process according to an embodiment of the present invention.

[0041] The attribution generator produces a structured attribution component for each advisory response. The attribution serves two critical purposes: (a) it makes the avatar's reasoning transparent, enabling the requesting user to evaluate whether the advice is genuinely grounded in the individual's personality; and (b) it distinguishes the system from generic AI advisors by demonstrating that each piece of advice is traceable to specific data.

[0042] The attribution component is structured as a list of citations, each citation comprising:

[0043] (a) A source reference identifying the specific conversation transcript, assessment response, or psychological dimension that informed the advisory. For example: "Career Conversation, Question: 'Tell me about a time you took a professional risk' — Depth Score: 4.2/5."

[0044] (b) A relevance score (0-1) indicating how strongly the cited source influenced the advisory response.

[0045] (c) A natural-language explanation of how the cited data informed the advisory. For example: "In this conversation, [person] described their move to [city] as 'the scariest and best decision' of their career, suggesting they valued career growth over geographic stability when they believed in the opportunity."

[0046] (d) The data layer from which the citation was drawn (experience layer or cognition layer), enabling the user to understand whether the advice is based on the individual's stated experiences or their measured cognitive patterns.

[0047] In a preferred embodiment, the attribution is presented to the requesting user in a collapsible section below the advisory response, allowing users who want transparency to examine the sources while not overwhelming users who simply want the advice.

### 6. Confidence Scoring

[0048] The confidence scorer evaluates the advisory response based on the density and relevance of available data:

[0049] (a) Knowledge Graph Coverage: The number and relevance of experience entries retrieved for the query's decision domain. More relevant entries with higher depth scores increase confidence.

[0050] (b) Psychological Profile Coverage: Whether the relevant psychological dimensions have been assessed. If the individual completed the rapid-fire assessment and the relevant dimensions have data, confidence increases.

[0051] (c) Domain Match: Whether the query's decision domain matches domains where the individual provided substantial narrative data. A query about career decisions when the individual completed multiple career-related conversations has higher confidence than a query about a domain with sparse data.

[0052] (d) Consistency: Whether the retrieved experience entries and psychological profile dimensions point in a consistent direction. Conflicting signals reduce confidence.

[0053] When the confidence score is below a configurable threshold, the system appends a qualification to the advisory response. For example: "Note: [Person] didn't share much about financial investment decisions specifically, so this advice is based more on their general approach to risk rather than specific experience in this area."

### 7. Multimodal Response Delivery

[0054] The multimodal delivery engine optionally renders the advisory response through:

[0055] (a) Voice Synthesis: The text advisory is converted to speech using a voice synthesis model trained on the individual's accumulated voice audio samples (from the presence layer of the personal data graph). The synthesized speech approximates the individual's vocal characteristics including pitch, cadence, accent, and speech patterns.

[0056] (b) Visual Likeness: The advisory is optionally delivered through a visual likeness model that renders the individual's face synchronized with the synthesized speech, creating the experience of receiving advice from the individual in person.

[0057] (c) Text with Attribution: The advisory text is always available, along with the structured attribution component, regardless of whether audio or video delivery is used.

### 8. Safeguards and Ethical Considerations

[0058] The system implements several safeguards:

[0059] (a) The system does not claim to know what the individual would actually do — responses are framed as "based on what [person] shared and their measured tendencies, they would likely..." rather than definitive statements.

[0060] (b) The confidence scoring mechanism ensures that low-confidence responses are clearly flagged, preventing the system from generating authoritative-sounding advice in domains where data is sparse.

[0061] (c) The attribution mechanism enables users to verify the basis for each advisory response, providing accountability and transparency.

[0062] (d) Access to the advisory system is governed by the individual's pre-configured access conditions, ensuring that only authorized beneficiaries can interact with the avatar.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0063] FIG. 1 is a block diagram illustrating the overall system architecture of the advisory response generation system.

[0064] FIG. 2 is a flow diagram illustrating the query processing and dual-source retrieval process.

[0065] FIG. 3 is a block diagram illustrating the attribution generation process and output structure.

---

## DRAWINGS

### FIG. 1 — System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              ADVISORY INTERFACE (110)                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │ "What would Dad do about this job offer from    │    │
│  │  a startup? I'd have to move across the         │    │
│  │  country and take a pay cut..."                  │    │
│  └──────────────────────┬──────────────────────────┘    │
└─────────────────────────┼───────────────────────────────┘
                          ▼
                 ┌────────────────┐
                 │ ACCESS CONTROL │
                 │ VERIFICATION   │
                 └───────┬────────┘
                         ▼
                 ┌────────────────┐
                 │ QUERY PARSER   │
                 │ (120)          │
                 │ Domain: career │
                 │ + financial    │
                 │ + relocation   │
                 └───────┬────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
┌──────────────────────┐ ┌──────────────────────┐
│ KNOWLEDGE GRAPH      │ │ PSYCHOLOGICAL PROFILE │
│ RETRIEVAL (130)      │ │ RETRIEVAL (140)       │
│                      │ │                       │
│ Retrieved:           │ │ Retrieved:            │
│ - Career risk conv.  │ │ - Financial risk: 0.35│
│ - Move experience    │ │ - Career risk: 0.62   │
│ - Family values conv.│ │ - Family priority: hi │
│ - Career advice conv.│ │ - Decision style:     │
│                      │ │   analytical+gut      │
│ [With depth scores]  │ │ [With latency weights]│
└──────────┬───────────┘ └──────────┬────────────┘
           └──────────┬─────────────┘
                      ▼
           ┌──────────────────────┐
           │ REASONING LANGUAGE   │
           │ MODEL (150)          │
           │                      │
           │ Synthesizes:         │
           │ - Query context      │
           │ - Experience entries  │
           │ - Psych dimensions   │
           │ - Communication style│
           └──────────┬───────────┘
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
┌────────────┐ ┌───────────┐ ┌──────────────┐
│ATTRIBUTION │ │CONFIDENCE │ │MULTIMODAL    │
│GENERATOR   │ │SCORER     │ │DELIVERY      │
│(160)       │ │(170)      │ │ENGINE (180)  │
│            │ │           │ │              │
│Citations:  │ │Score: 0.82│ │- Text        │
│- Conv. ref │ │(High)     │ │- Voice clone │
│- Psych dim │ │           │ │- Visual      │
│- Relevance │ │           │ │  likeness    │
└────────────┘ └───────────┘ └──────────────┘
```

### FIG. 2 — Query Processing and Dual-Source Retrieval Flow

```
┌──────────────────┐
│ Beneficiary      │
│ Submits Query    │
└────────┬─────────┘
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Verify Access    │─NO─►│ Return: Access    │
│ Permissions      │     │ Denied + Unmet   │
└────────┬─────────┘     │ Conditions       │
         │ YES           └──────────────────┘
         ▼
┌──────────────────┐
│ Parse Query      │
│ - Domain(s)      │
│ - Key factors    │
│ - Query type     │
│ - Emotional ctx  │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Retrieve│ │Retrieve│
│from    │ │from    │
│Knowledge│ │Psych   │
│Graph   │ │Profile │
│        │ │        │
│Semantic│ │Domain  │
│similar-│ │mapping │
│ity     │ │to dims │
│search  │ │        │
└───┬────┘ └───┬────┘
    └────┬─────┘
         ▼
┌──────────────────┐
│ Construct        │
│ Reasoning Prompt │
│ - Query          │
│ - Experiences    │
│   (weighted by   │
│    depth score)  │
│ - Psych dims     │
│ - Style guidance │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Generate         │
│ Advisory Response│
└────────┬─────────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
┌──────┐┌────┐┌───────┐
│Attri-││Conf││Multi- │
│bution││idence│modal │
│      ││Score││Render │
└──┬───┘└──┬─┘└──┬────┘
   └───────┼─────┘
           ▼
┌──────────────────┐
│ Deliver Response │
│ + Attribution    │
│ + Confidence     │
│ + Voice/Visual   │
└──────────────────┘
```

### FIG. 3 — Attribution Structure

```
┌─────────────────────────────────────────────────────────┐
│                 ADVISORY RESPONSE                        │
│                                                          │
│  "Your dad was someone who valued financial security..." │
│  [Full advisory text]                                    │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  CONFIDENCE: 82% (High)                                  │
│  Based on 4 relevant conversations and 3 psych dims      │
├─────────────────────────────────────────────────────────┤
│  ATTRIBUTION:                                            │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Citation 1                                         │  │
│  │ Source: Career Conversation — "Tell me about a     │  │
│  │   time you took a professional risk"               │  │
│  │ Layer: Experience                                  │  │
│  │ Depth Score: 4.2/5                                 │  │
│  │ Relevance: 0.91                                    │  │
│  │ Explanation: "Described move to [city] as          │  │
│  │   'scariest and best decision' — suggests          │  │
│  │   willingness to take career risks when            │  │
│  │   believing in the opportunity."                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Citation 2                                         │  │
│  │ Source: Psychological Profile — Financial Risk      │  │
│  │ Layer: Cognition                                   │  │
│  │ Dimension Score: 0.35 (risk-averse)                │  │
│  │ Relevance: 0.85                                    │  │
│  │ Explanation: "Instinctive responses showed          │  │
│  │   caution with financial decisions, consistent      │  │
│  │   with narrative about valuing stability."          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Citation 3                                         │  │
│  │ Source: Family Values Conversation — "What          │  │
│  │   matters most to you in life?"                    │  │
│  │ Layer: Experience                                  │  │
│  │ Depth Score: 4.8/5                                 │  │
│  │ Relevance: 0.78                                    │  │
│  │ Explanation: "Ranked family proximity as a top      │  │
│  │   priority — cross-country move would conflict      │  │
│  │   with this value."                                │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## CLAIMS

1. A computer-implemented method for generating an advisory response in the persona of a specific individual, the method comprising:

   receiving, from a requesting user, a situational query requesting advice attributed to a specific individual;

   retrieving, from a personal knowledge graph associated with the individual, one or more relevant experience entries based on semantic similarity between the situational query and the individual's documented life experiences, the knowledge graph having been constructed from depth-scored narrative conversations with the individual;

   retrieving, from a psychological profile associated with the individual, one or more relevant decision-making dimensions based on a domain of the situational query, the psychological profile having been constructed from a rapid-fire assessment capturing the individual's instinctive responses to forced-choice questions;

   providing the situational query, the retrieved experience entries, and the retrieved decision-making dimensions as input to a reasoning language model;

   generating, by the reasoning language model, an advisory response that reflects how the individual would likely approach the situation described in the query, the advisory response being grounded in the individual's specific experiences and calibrated to their measured decision-making patterns; and

   generating an attribution component identifying the specific experience entries and decision-making dimensions that informed the advisory response.

2. The method of claim 1, further comprising:
   computing a confidence score for the advisory response based on a density of relevant entries in the personal knowledge graph and a coverage of relevant dimensions in the psychological profile;
   when the confidence score is below a threshold, appending a qualification to the advisory response indicating limited data availability in the relevant domain.

3. The method of claim 1, further comprising delivering the advisory response through a voice synthesis model trained on audio samples of the individual's voice, such that the advisory is spoken in a synthesized approximation of the individual's vocal characteristics.

4. The method of claim 1, wherein the psychological profile comprises a multi-dimensional personality vector produced by a trait extraction engine that processed the individual's rapid-fire assessment responses, and wherein retrieving relevant decision-making dimensions comprises identifying which dimensions of the personality vector are most predictive for the domain of the situational query.

5. The method of claim 1, wherein the attribution component is structured as a list of citations, each citation comprising a reference to a specific conversation transcript or assessment response, a relevance score, and a natural-language explanation of how the cited data informed the advisory response.

6. The method of claim 1, further comprising:
   prior to generating the advisory response, verifying that the requesting user has been granted avatar interaction permission under an access control system governing the individual's digital legacy;
   wherein the access control system evaluates one or more access conditions configured by the individual, the conditions selected from a set comprising immediate access, time-delayed access, inactivity-triggered access, and manual release.

7. The method of claim 1, wherein the retrieved experience entries are weighted by their associated depth scores when provided to the reasoning language model, such that experiences documented with greater narrative depth have greater influence on the advisory response.

8. A computer-implemented system for generating advisory responses in the persona of a specific individual, the system comprising:

   an advisory interface configured to receive situational queries from a requesting user;

   a knowledge graph retrieval engine configured to query a personal knowledge graph associated with the individual and retrieve relevant experience entries based on semantic similarity to the situational query;

   a psychological profile retrieval engine configured to query a psychological profile associated with the individual and retrieve relevant decision-making dimensions based on a domain of the situational query;

   a reasoning language model configured to receive the situational query, the retrieved experience entries, and the retrieved decision-making dimensions, and to generate an advisory response reflecting how the individual would likely approach the described situation; and

   an attribution generator configured to produce a structured attribution component identifying the specific data sources that informed the advisory response.

---

## ABSTRACT

A computer-implemented system and method for generating advisory responses in the persona of a specific individual. A requesting user submits a situational query, and the system performs dual-source retrieval from a personal knowledge graph (documenting the individual's life experiences) and a psychological profile (capturing their decision-making patterns). A reasoning language model synthesizes the retrieved data to generate an advisory response calibrated to the individual's personality. Each response includes an attribution component citing the specific experiences and psychological traits that informed the advice, making the reasoning transparent and auditable.
