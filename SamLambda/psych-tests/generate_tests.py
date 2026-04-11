#!/usr/bin/env python3
"""Generate the three test definition JSON files for the psych testing framework."""
import json
import os

LIKERT5_OPTIONS = ["Very Inaccurate", "Moderately Inaccurate", "Neither", "Moderately Accurate", "Very Accurate"]
LIKERT5_HINT = "Rate how accurately this statement describes you on a 5-point scale."
BIG5_THRESHOLDS = [
    {"min": 1.0, "max": 2.5, "label": "Low"},
    {"min": 2.5, "max": 3.5, "label": "Average"},
    {"min": 3.5, "max": 5.0, "label": "High"},
]

def q(qid, text, reverse, domain, facet, page_break=False, video_freq=None):
    """Build a question dict."""
    item = {
        "questionId": qid,
        "text": text,
        "responseType": "likert5",
        "options": LIKERT5_OPTIONS,
        "reverseScored": reverse,
        "scoringKey": domain,
        "groupByFacet": facet,
        "pageBreakAfter": page_break,
        "accessibilityHint": LIKERT5_HINT,
    }
    if video_freq is not None:
        item["videoPromptFrequency"] = video_freq
    return item

def qb(qid, text, reverse, domain, facet, page_break=False, video_freq=None):
    """Build a bipolar5 question dict."""
    item = {
        "questionId": qid,
        "text": text,
        "responseType": "bipolar5",
        "options": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"],
        "reverseScored": reverse,
        "scoringKey": domain,
        "groupByFacet": facet,
        "pageBreakAfter": page_break,
        "accessibilityHint": "Select the point on the scale that best represents your preference.",
    }
    if video_freq is not None:
        item["videoPromptFrequency"] = video_freq
    return item


def generate_ipip_neo_60():
    questions = [
        # Openness - imagination (positive, q1-q6)
        q("neo60-q1", "I have a vivid imagination.", False, "openness", "imagination", video_freq=20),
        q("neo60-q2", "I believe in the importance of art.", False, "openness", "imagination"),
        q("neo60-q3", "I tend to vote for liberal political candidates.", False, "openness", "imagination"),
        q("neo60-q4", "I enjoy hearing new ideas.", False, "openness", "imagination"),
        q("neo60-q5", "I enjoy thinking about things.", False, "openness", "imagination"),
        q("neo60-q6", "I carry the conversation to a higher level.", False, "openness", "imagination"),
        # Openness - artistic_interests (reverse, q7-q12)
        q("neo60-q7", "I do not like art.", True, "openness", "artistic_interests"),
        q("neo60-q8", "I avoid philosophical discussions.", True, "openness", "artistic_interests"),
        q("neo60-q9", "I do not enjoy going to art museums.", True, "openness", "artistic_interests"),
        q("neo60-q10", "I tend to vote for conservative political candidates.", True, "openness", "artistic_interests"),
        q("neo60-q11", "I am not interested in abstract ideas.", True, "openness", "artistic_interests"),
        q("neo60-q12", "I have difficulty understanding abstract ideas.", True, "openness", "artistic_interests", page_break=True),
        # Conscientiousness - self_efficacy (positive, q13-q18)
        q("neo60-q13", "I am always prepared.", False, "conscientiousness", "self_efficacy"),
        q("neo60-q14", "I pay attention to details.", False, "conscientiousness", "self_efficacy"),
        q("neo60-q15", "I get chores done right away.", False, "conscientiousness", "self_efficacy"),
        q("neo60-q16", "I carry out my plans.", False, "conscientiousness", "self_efficacy"),
        q("neo60-q17", "I make plans and stick to them.", False, "conscientiousness", "self_efficacy"),
        q("neo60-q18", "I complete tasks successfully.", False, "conscientiousness", "self_efficacy"),
        # Conscientiousness - orderliness (reverse, q19-q24)
        q("neo60-q19", "I waste my time.", True, "conscientiousness", "orderliness"),
        q("neo60-q20", "I find it difficult to get down to work.", True, "conscientiousness", "orderliness"),
        q("neo60-q21", "I do just enough work to get by.", True, "conscientiousness", "orderliness", video_freq=20),
        q("neo60-q22", "I don't see things through.", True, "conscientiousness", "orderliness"),
        q("neo60-q23", "I shirk my duties.", True, "conscientiousness", "orderliness"),
        q("neo60-q24", "I leave a mess in my room.", True, "conscientiousness", "orderliness", page_break=True),
        # Extraversion - friendliness (positive, q25-q30)
        q("neo60-q25", "I am the life of the party.", False, "extraversion", "friendliness"),
        q("neo60-q26", "I feel comfortable around people.", False, "extraversion", "friendliness"),
        q("neo60-q27", "I start conversations.", False, "extraversion", "friendliness"),
        q("neo60-q28", "I talk to a lot of different people at parties.", False, "extraversion", "friendliness"),
        q("neo60-q29", "I make friends easily.", False, "extraversion", "friendliness"),
        q("neo60-q30", "I know how to captivate people.", False, "extraversion", "friendliness"),
        # Extraversion - gregariousness (reverse, q31-q36)
        q("neo60-q31", "I don't talk a lot.", True, "extraversion", "gregariousness"),
        q("neo60-q32", "I keep in the background.", True, "extraversion", "gregariousness"),
        q("neo60-q33", "I have little to say.", True, "extraversion", "gregariousness"),
        q("neo60-q34", "I don't like to draw attention to myself.", True, "extraversion", "gregariousness"),
        q("neo60-q35", "I am quiet around strangers.", True, "extraversion", "gregariousness"),
        q("neo60-q36", "I would describe my experiences as somewhat dull.", True, "extraversion", "gregariousness", page_break=True),
        # Agreeableness - trust (positive, q37-q42)
        q("neo60-q37", "I sympathize with others' feelings.", False, "agreeableness", "trust"),
        q("neo60-q38", "I have a good word for everyone.", False, "agreeableness", "trust"),
        q("neo60-q39", "I am interested in people.", False, "agreeableness", "trust"),
        q("neo60-q40", "I take time out for others.", False, "agreeableness", "trust"),
        q("neo60-q41", "I feel others' emotions.", False, "agreeableness", "trust", video_freq=20),
        q("neo60-q42", "I make people feel at ease.", False, "agreeableness", "trust"),
        # Agreeableness - altruism (reverse, q43-q48)
        q("neo60-q43", "I am not really interested in others.", True, "agreeableness", "altruism"),
        q("neo60-q44", "I insult people.", True, "agreeableness", "altruism"),
        q("neo60-q45", "I am not interested in other people's problems.", True, "agreeableness", "altruism"),
        q("neo60-q46", "I feel little concern for others.", True, "agreeableness", "altruism"),
        q("neo60-q47", "I am hard to get to know.", True, "agreeableness", "altruism"),
        q("neo60-q48", "I cut others to pieces.", True, "agreeableness", "altruism", page_break=True),
        # Neuroticism - anxiety (positive, q49-q54)
        q("neo60-q49", "I get stressed out easily.", False, "neuroticism", "anxiety"),
        q("neo60-q50", "I worry about things.", False, "neuroticism", "anxiety"),
        q("neo60-q51", "I am easily disturbed.", False, "neuroticism", "anxiety"),
        q("neo60-q52", "I get upset easily.", False, "neuroticism", "anxiety"),
        q("neo60-q53", "I change my mood a lot.", False, "neuroticism", "anxiety"),
        q("neo60-q54", "I have frequent mood swings.", False, "neuroticism", "anxiety"),
        # Neuroticism - self_consciousness (reverse, q55-q60)
        q("neo60-q55", "I seldom feel blue.", True, "neuroticism", "self_consciousness"),
        q("neo60-q56", "I am relaxed most of the time.", True, "neuroticism", "self_consciousness"),
        q("neo60-q57", "I am not easily bothered by things.", True, "neuroticism", "self_consciousness"),
        q("neo60-q58", "I rarely get irritated.", True, "neuroticism", "self_consciousness"),
        q("neo60-q59", "I seldom get mad.", True, "neuroticism", "self_consciousness"),
        q("neo60-q60", "I am very pleased with myself.", True, "neuroticism", "self_consciousness", page_break=True),
    ]

    scoring_rules = {}
    for domain in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        scoring_rules[domain] = {"formula": "mean", "thresholds": BIG5_THRESHOLDS}

    interp = {
        "openness": [
            {"min": 1.0, "max": 2.5, "text": "Your Openness score is low, suggesting you prefer practical, conventional approaches and are comfortable with familiar routines rather than seeking out novel experiences."},
            {"min": 2.5, "max": 3.5, "text": "Your Openness score is average, indicating a balanced mix of curiosity and practicality. You appreciate new ideas while also valuing tried-and-true methods."},
            {"min": 3.5, "max": 5.0, "text": "Your Openness score is high, reflecting a strong intellectual curiosity, vivid imagination, and appreciation for art, ideas, and unconventional perspectives."},
        ],
        "conscientiousness": [
            {"min": 1.0, "max": 2.5, "text": "Your Conscientiousness score is low, suggesting a flexible, spontaneous approach to life. You may prefer to keep your options open rather than follow strict plans."},
            {"min": 2.5, "max": 3.5, "text": "Your Conscientiousness score is average, indicating a reasonable balance between organization and flexibility in your daily life."},
            {"min": 3.5, "max": 5.0, "text": "Your Conscientiousness score is high, reflecting strong self-discipline, organization, and a goal-oriented approach to life."},
        ],
        "extraversion": [
            {"min": 1.0, "max": 2.5, "text": "Your Extraversion score is low, suggesting you prefer quieter, more solitary activities and may find large social gatherings draining."},
            {"min": 2.5, "max": 3.5, "text": "Your Extraversion score is average, indicating comfort in both social and solitary settings."},
            {"min": 3.5, "max": 5.0, "text": "Your Extraversion score is high, reflecting an energetic, sociable nature. You thrive in social situations and draw energy from interacting with others."},
        ],
        "agreeableness": [
            {"min": 1.0, "max": 2.5, "text": "Your Agreeableness score is low, suggesting you tend to be more competitive and skeptical in your interactions with others."},
            {"min": 2.5, "max": 3.5, "text": "Your Agreeableness score is average, indicating a balance between cooperation and assertiveness."},
            {"min": 3.5, "max": 5.0, "text": "Your Agreeableness score is high, reflecting a compassionate, cooperative nature. You value harmony and are considerate of others' feelings."},
        ],
        "neuroticism": [
            {"min": 1.0, "max": 2.5, "text": "Your Neuroticism score is low, suggesting strong emotional stability. You tend to remain calm under pressure."},
            {"min": 2.5, "max": 3.5, "text": "Your Neuroticism score is average, indicating a typical range of emotional responses to life's challenges."},
            {"min": 3.5, "max": 5.0, "text": "Your Neuroticism score is high, reflecting a tendency to experience stress and mood fluctuations more intensely."},
        ],
    }

    return {
        "testId": "ipip-neo-60",
        "testName": "IPIP-NEO-60",
        "description": "A 60-item measure of the Big Five personality domains: Openness, Conscientiousness, Extraversion, Agreeableness, and Neuroticism, based on the International Personality Item Pool.",
        "version": "1.0.0",
        "estimatedMinutes": 15,
        "consentBlock": {
            "title": "IPIP-NEO-60 Personality Assessment",
            "bodyText": "This assessment contains 60 statements about your personality. For each statement, indicate how accurately it describes you on a scale from Very Inaccurate to Very Accurate. There are no right or wrong answers. Your responses will be used to generate a personality profile as part of your Legacy Portrait. Your data is stored securely and encrypted. This instrument uses items from the International Personality Item Pool (ipip.ori.org), which is in the public domain.",
            "requiredCheckboxLabel": "I understand this is a self-report personality assessment and consent to my responses being stored and scored."
        },
        "disclaimerText": "This assessment is for personal insight and legacy-building purposes only. It is not a clinical diagnostic tool. Items are from the public-domain International Personality Item Pool (ipip.ori.org).",
        "questions": questions,
        "scoringRules": scoring_rules,
        "compositeRules": {},
        "interpretationTemplates": interp,
        "bedrockConfig": {
            "useBedrock": True,
            "maxTokens": 1024,
            "temperature": 0.7,
            "cacheResultsForDays": 30
        },
        "videoPromptTrigger": "Take a moment to reflect on the questions you just answered. Record a brief video sharing your thoughts about how these traits show up in your daily life.",
        "saveProgressEnabled": True,
        "analyticsEnabled": True,
        "exportFormats": ["PDF", "JSON", "CSV"]
    }


def generate_oejts():
    """Generate the Open Extended Jungian Type Scales test definition."""
    # 4 dimensions x 15 items = 60 items
    # E/I, S/N, T/F, J/P
    # Each dimension: items scored toward one pole or the other
    # bipolar5 response type

    ei_items = [
        ("oejts-q1", "At a party, you tend to interact with many people, including strangers.", False, "EI", "extraversion_pole"),
        ("oejts-q2", "You prefer to be in the thick of things rather than on the sidelines.", False, "EI", "extraversion_pole"),
        ("oejts-q3", "You feel energized after spending time with a large group of people.", False, "EI", "extraversion_pole"),
        ("oejts-q4", "You enjoy being the center of attention.", False, "EI", "extraversion_pole"),
        ("oejts-q5", "You find it easy to introduce yourself to new people.", False, "EI", "extraversion_pole"),
        ("oejts-q6", "You tend to think out loud.", False, "EI", "extraversion_pole"),
        ("oejts-q7", "You are more of a talker than a listener.", False, "EI", "extraversion_pole"),
        ("oejts-q8", "You prefer to spend your free time alone or with one close friend.", True, "EI", "introversion_pole"),
        ("oejts-q9", "You need time alone to recharge after social events.", True, "EI", "introversion_pole"),
        ("oejts-q10", "You prefer deep conversations with one person over group discussions.", True, "EI", "introversion_pole"),
        ("oejts-q11", "You tend to think things through before speaking.", True, "EI", "introversion_pole"),
        ("oejts-q12", "You find small talk draining.", True, "EI", "introversion_pole"),
        ("oejts-q13", "You prefer written communication over phone calls.", True, "EI", "introversion_pole"),
        ("oejts-q14", "You feel drained after attending large social gatherings.", True, "EI", "introversion_pole"),
        ("oejts-q15", "You prefer working independently rather than in a team.", True, "EI", "introversion_pole"),
    ]

    sn_items = [
        ("oejts-q16", "You focus on the details and specifics of a situation.", False, "SN", "sensing_pole"),
        ("oejts-q17", "You prefer practical, hands-on learning experiences.", False, "SN", "sensing_pole"),
        ("oejts-q18", "You trust your direct experience more than theories.", False, "SN", "sensing_pole"),
        ("oejts-q19", "You prefer step-by-step instructions over general guidelines.", False, "SN", "sensing_pole"),
        ("oejts-q20", "You pay close attention to what is happening around you right now.", False, "SN", "sensing_pole"),
        ("oejts-q21", "You prefer dealing with facts rather than possibilities.", False, "SN", "sensing_pole"),
        ("oejts-q22", "You are more interested in what is real than what is possible.", False, "SN", "sensing_pole"),
        ("oejts-q23", "You are drawn to the big picture and future possibilities.", True, "SN", "intuition_pole"),
        ("oejts-q24", "You enjoy exploring abstract concepts and theories.", True, "SN", "intuition_pole"),
        ("oejts-q25", "You often think about what could be rather than what is.", True, "SN", "intuition_pole"),
        ("oejts-q26", "You trust your gut feelings and hunches.", True, "SN", "intuition_pole"),
        ("oejts-q27", "You prefer learning new skills over perfecting existing ones.", True, "SN", "intuition_pole"),
        ("oejts-q28", "You are more interested in patterns and connections than individual facts.", True, "SN", "intuition_pole"),
        ("oejts-q29", "You enjoy brainstorming and generating new ideas.", True, "SN", "intuition_pole"),
        ("oejts-q30", "You are more imaginative than practical.", True, "SN", "intuition_pole"),
    ]

    tf_items = [
        ("oejts-q31", "You make decisions based on logic and objective analysis.", False, "TF", "thinking_pole"),
        ("oejts-q32", "You value fairness and consistency over individual circumstances.", False, "TF", "thinking_pole"),
        ("oejts-q33", "You prefer to be direct and honest, even if it might hurt feelings.", False, "TF", "thinking_pole"),
        ("oejts-q34", "You believe the best decisions are made with the head, not the heart.", False, "TF", "thinking_pole"),
        ("oejts-q35", "You tend to analyze problems objectively without getting emotionally involved.", False, "TF", "thinking_pole"),
        ("oejts-q36", "You are more convinced by logical arguments than emotional appeals.", False, "TF", "thinking_pole"),
        ("oejts-q37", "You prioritize truth over tact in conversations.", False, "TF", "thinking_pole"),
        ("oejts-q38", "You consider how decisions will affect people's feelings.", True, "TF", "feeling_pole"),
        ("oejts-q39", "You value harmony and try to avoid conflict.", True, "TF", "feeling_pole"),
        ("oejts-q40", "You are more interested in people than in systems or processes.", True, "TF", "feeling_pole"),
        ("oejts-q41", "You make decisions based on your personal values and how others will be affected.", True, "TF", "feeling_pole"),
        ("oejts-q42", "You are sensitive to others' needs and emotions.", True, "TF", "feeling_pole"),
        ("oejts-q43", "You prefer to encourage and support rather than critique.", True, "TF", "feeling_pole"),
        ("oejts-q44", "You believe compassion is more important than objectivity.", True, "TF", "feeling_pole"),
        ("oejts-q45", "You find it difficult to give negative feedback.", True, "TF", "feeling_pole"),
    ]

    jp_items = [
        ("oejts-q46", "You prefer to have a plan and stick to it.", False, "JP", "judging_pole"),
        ("oejts-q47", "You like to have things decided and settled.", False, "JP", "judging_pole"),
        ("oejts-q48", "You prefer a structured and organized environment.", False, "JP", "judging_pole"),
        ("oejts-q49", "You feel uncomfortable when things are left open-ended.", False, "JP", "judging_pole"),
        ("oejts-q50", "You like to make lists and check things off.", False, "JP", "judging_pole"),
        ("oejts-q51", "You prefer to finish one project before starting another.", False, "JP", "judging_pole"),
        ("oejts-q52", "You are punctual and expect others to be as well.", False, "JP", "judging_pole"),
        ("oejts-q53", "You prefer to keep your options open and stay flexible.", True, "JP", "perceiving_pole"),
        ("oejts-q54", "You enjoy spontaneity and going with the flow.", True, "JP", "perceiving_pole"),
        ("oejts-q55", "You tend to start many projects but may not finish all of them.", True, "JP", "perceiving_pole"),
        ("oejts-q56", "You prefer to adapt to situations as they arise.", True, "JP", "perceiving_pole"),
        ("oejts-q57", "You find deadlines more motivating than stressful.", True, "JP", "perceiving_pole"),
        ("oejts-q58", "You enjoy exploring new possibilities rather than following a set plan.", True, "JP", "perceiving_pole"),
        ("oejts-q59", "You are comfortable with ambiguity and uncertainty.", True, "JP", "perceiving_pole"),
        ("oejts-q60", "You prefer a flexible schedule over a rigid routine.", True, "JP", "perceiving_pole"),
    ]

    all_items = ei_items + sn_items + tf_items + jp_items
    questions = []
    for i, (qid, text, reverse, domain, facet) in enumerate(all_items):
        page_break = (i + 1) % 15 == 0
        vf = 20 if (i + 1) % 20 == 0 else None
        questions.append(qb(qid, text, reverse, domain, facet, page_break=page_break, video_freq=vf))

    dim_thresholds = [
        {"min": 1.0, "max": 2.5, "label": "Strong"},
        {"min": 2.5, "max": 3.5, "label": "Moderate"},
        {"min": 3.5, "max": 5.0, "label": "Strong"},
    ]

    scoring_rules = {
        "EI": {"formula": "mean", "thresholds": dim_thresholds},
        "SN": {"formula": "mean", "thresholds": dim_thresholds},
        "TF": {"formula": "mean", "thresholds": dim_thresholds},
        "JP": {"formula": "mean", "thresholds": dim_thresholds},
    }

    # 16 type interpretations
    types = ["ISTJ","ISFJ","INFJ","INTJ","ISTP","ISFP","INFP","INTP",
             "ESTP","ESFP","ENFP","ENTP","ESTJ","ESFJ","ENFJ","ENTJ"]
    type_descriptions = {
        "ISTJ": "Quiet, serious, dependable. Value traditions and loyalty.",
        "ISFJ": "Quiet, friendly, responsible. Committed to meeting obligations.",
        "INFJ": "Seek meaning and connection in ideas. Committed to firm values.",
        "INTJ": "Independent, determined. High standards of competence for self and others.",
        "ISTP": "Tolerant and flexible. Interested in cause and effect, efficient problem-solving.",
        "ISFP": "Quiet, friendly, sensitive. Enjoy the present moment and what is going on around them.",
        "INFP": "Idealistic, loyal to values. Seek to understand people and help them fulfill potential.",
        "INTP": "Seek logical explanations. Theoretical and abstract, interested in ideas.",
        "ESTP": "Flexible and tolerant. Focus on immediate results. Enjoy material comforts.",
        "ESFP": "Outgoing, friendly. Enjoy working with others and making things happen.",
        "ENFP": "Enthusiastic, imaginative. See life as full of possibilities. Make connections between events.",
        "ENTP": "Quick, ingenious, stimulating. Adept at generating conceptual possibilities.",
        "ESTJ": "Practical, realistic, matter-of-fact. Decisive, focused on getting results efficiently.",
        "ESFJ": "Warmhearted, conscientious, cooperative. Want harmony in their environment.",
        "ENFJ": "Warm, empathetic, responsive. Attuned to the emotions and needs of others.",
        "ENTJ": "Frank, decisive, assume leadership readily. Well-informed, enjoy expanding knowledge.",
    }

    interp = {}
    for dim in ["EI", "SN", "TF", "JP"]:
        if dim == "EI":
            interp[dim] = [
                {"min": 1.0, "max": 2.5, "text": "You show a clear preference for Extraversion, drawing energy from social interaction and external activity."},
                {"min": 2.5, "max": 3.5, "text": "You show a balanced preference between Extraversion and Introversion."},
                {"min": 3.5, "max": 5.0, "text": "You show a clear preference for Introversion, drawing energy from solitude and internal reflection."},
            ]
        elif dim == "SN":
            interp[dim] = [
                {"min": 1.0, "max": 2.5, "text": "You show a clear preference for Sensing, focusing on concrete facts and present realities."},
                {"min": 2.5, "max": 3.5, "text": "You show a balanced preference between Sensing and Intuition."},
                {"min": 3.5, "max": 5.0, "text": "You show a clear preference for Intuition, focusing on patterns, possibilities, and future potential."},
            ]
        elif dim == "TF":
            interp[dim] = [
                {"min": 1.0, "max": 2.5, "text": "You show a clear preference for Thinking, making decisions based on logic and objective analysis."},
                {"min": 2.5, "max": 3.5, "text": "You show a balanced preference between Thinking and Feeling."},
                {"min": 3.5, "max": 5.0, "text": "You show a clear preference for Feeling, making decisions based on personal values and how others will be affected."},
            ]
        elif dim == "JP":
            interp[dim] = [
                {"min": 1.0, "max": 2.5, "text": "You show a clear preference for Judging, preferring structure, planning, and decisiveness."},
                {"min": 2.5, "max": 3.5, "text": "You show a balanced preference between Judging and Perceiving."},
                {"min": 3.5, "max": 5.0, "text": "You show a clear preference for Perceiving, preferring flexibility, spontaneity, and keeping options open."},
            ]

    return {
        "testId": "oejts",
        "testName": "Open Extended Jungian Type Scales",
        "description": "A 60-item assessment producing a 16-type personality classification based on Jungian psychological types, measuring Extraversion/Introversion, Sensing/Intuition, Thinking/Feeling, and Judging/Perceiving dimensions.",
        "version": "1.0.0",
        "estimatedMinutes": 15,
        "consentBlock": {
            "title": "Open Extended Jungian Type Scales (OEJTS)",
            "bodyText": "This assessment contains 60 statements about your preferences and tendencies. For each statement, indicate how much you agree or disagree. There are no right or wrong answers. Your responses will be used to determine your Jungian personality type as part of your Legacy Portrait. Your data is stored securely and encrypted. This instrument is based on open-source items from Open Source Psychometrics Project.",
            "requiredCheckboxLabel": "I understand this is a self-report personality type assessment and consent to my responses being stored and scored."
        },
        "disclaimerText": "This assessment is for personal insight and legacy-building purposes only. It is not a clinical diagnostic tool. Based on open-source items from the Open Source Psychometrics Project (openpsychometrics.org).",
        "questions": questions,
        "scoringRules": scoring_rules,
        "compositeRules": {},
        "interpretationTemplates": interp,
        "bedrockConfig": {
            "useBedrock": True,
            "maxTokens": 1024,
            "temperature": 0.7,
            "cacheResultsForDays": 30
        },
        "videoPromptTrigger": "Reflect on the preferences you just indicated. Record a brief video sharing how these tendencies show up in your relationships and daily decisions.",
        "saveProgressEnabled": True,
        "analyticsEnabled": True,
        "exportFormats": ["PDF", "JSON", "CSV"]
    }


def generate_personality_ei():
    """Generate the Personality-Based Emotional Intelligence test definition."""
    # 4 EI dimensions: Self-Awareness, Self-Management, Social Awareness, Relationship Management
    # 10 items per dimension = 40 items total
    hint = "Rate how accurately this statement describes you on a 5-point scale."

    items_data = [
        # Self-Awareness (q1-q10)
        ("pei-q1", "I am aware of my emotions as I experience them.", False, "self_awareness", "emotional_recognition"),
        ("pei-q2", "I know why my emotions change.", False, "self_awareness", "emotional_recognition"),
        ("pei-q3", "I can accurately identify what I am feeling at any given moment.", False, "self_awareness", "emotional_recognition"),
        ("pei-q4", "I understand what makes me feel the way I do.", False, "self_awareness", "emotional_recognition"),
        ("pei-q5", "I recognize how my feelings affect my performance.", False, "self_awareness", "emotional_recognition"),
        ("pei-q6", "I have trouble figuring out my own feelings.", True, "self_awareness", "self_assessment"),
        ("pei-q7", "I am often confused about what emotion I am feeling.", True, "self_awareness", "self_assessment"),
        ("pei-q8", "I find it hard to describe how I feel to others.", True, "self_awareness", "self_assessment"),
        ("pei-q9", "I am surprised by my emotional reactions.", True, "self_awareness", "self_assessment"),
        ("pei-q10", "I don't pay much attention to my emotions.", True, "self_awareness", "self_assessment"),
        # Self-Management (q11-q20)
        ("pei-q11", "I can calm myself down when I feel anxious or upset.", False, "self_management", "emotional_regulation"),
        ("pei-q12", "I can control my temper and handle difficulties rationally.", False, "self_management", "emotional_regulation"),
        ("pei-q13", "I think before I act when I am angry.", False, "self_management", "emotional_regulation"),
        ("pei-q14", "I can pull myself together quickly after a setback.", False, "self_management", "emotional_regulation"),
        ("pei-q15", "I stay composed under pressure.", False, "self_management", "emotional_regulation"),
        ("pei-q16", "I have difficulty controlling my emotions.", True, "self_management", "adaptability"),
        ("pei-q17", "I tend to overreact to minor problems.", True, "self_management", "adaptability"),
        ("pei-q18", "I find it hard to let go of negative feelings.", True, "self_management", "adaptability"),
        ("pei-q19", "I get overwhelmed by strong emotions.", True, "self_management", "adaptability"),
        ("pei-q20", "I act impulsively when I am emotional.", True, "self_management", "adaptability"),
        # Social Awareness (q21-q30)
        ("pei-q21", "I can tell when someone is feeling sad even if they don't say so.", False, "social_awareness", "empathy"),
        ("pei-q22", "I am good at reading other people's body language.", False, "social_awareness", "empathy"),
        ("pei-q23", "I can sense the mood of a group when I walk into a room.", False, "social_awareness", "empathy"),
        ("pei-q24", "I notice when someone is uncomfortable in a social situation.", False, "social_awareness", "empathy"),
        ("pei-q25", "I understand why people feel the way they do.", False, "social_awareness", "empathy"),
        ("pei-q26", "I find it hard to understand why people react the way they do.", True, "social_awareness", "organizational_awareness"),
        ("pei-q27", "I often miss emotional cues from others.", True, "social_awareness", "organizational_awareness"),
        ("pei-q28", "I have difficulty seeing things from another person's perspective.", True, "social_awareness", "organizational_awareness"),
        ("pei-q29", "I am not very good at sensing what others are feeling.", True, "social_awareness", "organizational_awareness"),
        ("pei-q30", "I tend to focus on my own feelings rather than noticing others'.", True, "social_awareness", "organizational_awareness"),
        # Relationship Management (q31-q40)
        ("pei-q31", "I am good at resolving conflicts between people.", False, "relationship_management", "influence"),
        ("pei-q32", "I can inspire and motivate others.", False, "relationship_management", "influence"),
        ("pei-q33", "I help others feel better when they are upset.", False, "relationship_management", "influence"),
        ("pei-q34", "I am effective at building rapport with new people.", False, "relationship_management", "influence"),
        ("pei-q35", "I can express my emotions in a way that others understand.", False, "relationship_management", "influence"),
        ("pei-q36", "I find it difficult to maintain close relationships.", True, "relationship_management", "conflict_management"),
        ("pei-q37", "I struggle to express my feelings to others.", True, "relationship_management", "conflict_management"),
        ("pei-q38", "I have trouble working through disagreements constructively.", True, "relationship_management", "conflict_management"),
        ("pei-q39", "I find it hard to comfort someone who is upset.", True, "relationship_management", "conflict_management"),
        ("pei-q40", "I tend to avoid emotional conversations.", True, "relationship_management", "conflict_management"),
    ]

    questions = []
    for i, (qid, text, reverse, domain, facet) in enumerate(items_data):
        page_break = (i + 1) % 10 == 0
        vf = 20 if (i + 1) % 20 == 0 else None
        questions.append(q(qid, text, reverse, domain, facet, page_break=page_break, video_freq=vf))

    ei_thresholds = [
        {"min": 1.0, "max": 2.5, "label": "Low"},
        {"min": 2.5, "max": 3.5, "label": "Average"},
        {"min": 3.5, "max": 5.0, "label": "High"},
    ]

    scoring_rules = {
        "self_awareness": {"formula": "mean", "thresholds": ei_thresholds},
        "self_management": {"formula": "mean", "thresholds": ei_thresholds},
        "social_awareness": {"formula": "mean", "thresholds": ei_thresholds},
        "relationship_management": {"formula": "mean", "thresholds": ei_thresholds},
    }

    interp = {
        "self_awareness": [
            {"min": 1.0, "max": 2.5, "text": "Your Self-Awareness score is low, suggesting you may benefit from paying more attention to your emotional states and what triggers them."},
            {"min": 2.5, "max": 3.5, "text": "Your Self-Awareness score is average, indicating a reasonable understanding of your own emotions and their causes."},
            {"min": 3.5, "max": 5.0, "text": "Your Self-Awareness score is high, reflecting a strong ability to recognize and understand your own emotions as they occur."},
        ],
        "self_management": [
            {"min": 1.0, "max": 2.5, "text": "Your Self-Management score is low, suggesting you may find it challenging to regulate your emotional responses in difficult situations."},
            {"min": 2.5, "max": 3.5, "text": "Your Self-Management score is average, indicating a reasonable ability to manage your emotions in most situations."},
            {"min": 3.5, "max": 5.0, "text": "Your Self-Management score is high, reflecting strong emotional regulation skills and the ability to stay composed under pressure."},
        ],
        "social_awareness": [
            {"min": 1.0, "max": 2.5, "text": "Your Social Awareness score is low, suggesting you may sometimes miss emotional cues from others or find it hard to read social situations."},
            {"min": 2.5, "max": 3.5, "text": "Your Social Awareness score is average, indicating a reasonable ability to perceive and understand others' emotions."},
            {"min": 3.5, "max": 5.0, "text": "Your Social Awareness score is high, reflecting strong empathy and an ability to read social dynamics and others' emotional states."},
        ],
        "relationship_management": [
            {"min": 1.0, "max": 2.5, "text": "Your Relationship Management score is low, suggesting you may find it challenging to navigate emotional aspects of relationships and conflicts."},
            {"min": 2.5, "max": 3.5, "text": "Your Relationship Management score is average, indicating a reasonable ability to manage relationships and handle emotional interactions."},
            {"min": 3.5, "max": 5.0, "text": "Your Relationship Management score is high, reflecting strong skills in building rapport, resolving conflicts, and inspiring others."},
        ],
    }

    return {
        "testId": "personality-ei",
        "testName": "Personality-Based Emotional Intelligence Test",
        "description": "A 40-item assessment measuring four dimensions of emotional intelligence: Self-Awareness, Self-Management, Social Awareness, and Relationship Management.",
        "version": "1.0.0",
        "estimatedMinutes": 10,
        "consentBlock": {
            "title": "Personality-Based Emotional Intelligence Test",
            "bodyText": "This assessment contains 40 statements about how you perceive and manage emotions. For each statement, indicate how accurately it describes you. There are no right or wrong answers. Your responses will be used to generate an emotional intelligence profile as part of your Legacy Portrait. Your data is stored securely and encrypted. This instrument is based on open-source items from the Open Source Psychometrics Project.",
            "requiredCheckboxLabel": "I understand this is a self-report emotional intelligence assessment and consent to my responses being stored and scored."
        },
        "disclaimerText": "This assessment is for personal insight and legacy-building purposes only. It is not a clinical diagnostic tool. Based on open-source items from the Open Source Psychometrics Project (openpsychometrics.org).",
        "questions": questions,
        "scoringRules": scoring_rules,
        "compositeRules": {},
        "interpretationTemplates": interp,
        "bedrockConfig": {
            "useBedrock": True,
            "maxTokens": 1024,
            "temperature": 0.7,
            "cacheResultsForDays": 30
        },
        "videoPromptTrigger": "Reflect on the emotional situations described in the questions you just answered. Record a brief video sharing how you typically handle emotions in your relationships.",
        "saveProgressEnabled": True,
        "analyticsEnabled": True,
        "exportFormats": ["PDF", "JSON", "CSV"]
    }


def add_composite_rules(ipip, oejts, pei):
    """Add compositeRules to each test definition for Legacy Portrait generation."""
    # IPIP-NEO-60 composites: reference OEJTS and EI
    ipip["compositeRules"] = {
        "legacy_portrait_personality": {
            "sources": [
                {"testId": "ipip-neo-60", "domain": "openness"},
                {"testId": "ipip-neo-60", "domain": "conscientiousness"},
                {"testId": "ipip-neo-60", "domain": "extraversion"},
                {"testId": "ipip-neo-60", "domain": "agreeableness"},
                {"testId": "ipip-neo-60", "domain": "neuroticism"},
                {"testId": "oejts", "domain": "EI"},
                {"testId": "personality-ei", "domain": "self_awareness"}
            ],
            "formula": "mean"
        }
    }

    # OEJTS composites: reference Big Five and EI
    oejts["compositeRules"] = {
        "legacy_portrait_type": {
            "sources": [
                {"testId": "oejts", "domain": "EI"},
                {"testId": "oejts", "domain": "SN"},
                {"testId": "oejts", "domain": "TF"},
                {"testId": "oejts", "domain": "JP"},
                {"testId": "ipip-neo-60", "domain": "extraversion"},
                {"testId": "personality-ei", "domain": "social_awareness"}
            ],
            "formula": "mean"
        }
    }

    # Personality-EI composites: reference Big Five and OEJTS
    pei["compositeRules"] = {
        "legacy_portrait_emotional": {
            "sources": [
                {"testId": "personality-ei", "domain": "self_awareness"},
                {"testId": "personality-ei", "domain": "self_management"},
                {"testId": "personality-ei", "domain": "social_awareness"},
                {"testId": "personality-ei", "domain": "relationship_management"},
                {"testId": "ipip-neo-60", "domain": "agreeableness"},
                {"testId": "oejts", "domain": "TF"}
            ],
            "formula": "mean"
        }
    }


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    ipip = generate_ipip_neo_60()
    oejts = generate_oejts()
    pei = generate_personality_ei()

    # Add composite rules (task 14.4)
    add_composite_rules(ipip, oejts, pei)

    for name, data in [("ipip-neo-60.json", ipip), ("oejts.json", oejts), ("personality-ei.json", pei)]:
        path = os.path.join(out_dir, name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Generated {path} ({len(data['questions'])} questions)")


if __name__ == "__main__":
    main()