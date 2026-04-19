import React from "react";
import { Link } from "react-router-dom";
import SampleQuestionCard from "./SampleQuestionCard";
import { trackEvent } from "@/lib/analytics";

const SAMPLE_QUESTIONS = [
  {
    category: "Life Story",
    question: "What's the bravest thing you've ever done?",
  },
  {
    category: "Life Events",
    question: "Tell me about the day you became a parent.",
  },
  {
    category: "Values & Emotions",
    question: "What value do you most want to pass on to the next generation?",
  },
];

const SampleQuestionsSection: React.FC = () => {
  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4 sm:px-8">
        <h2 className="text-3xl font-bold text-center text-legacy-navy mb-4">
          Questions That Spark Your Story
        </h2>
        <p className="text-lg text-gray-600 text-center max-w-2xl mx-auto mb-12">
          Three paths to explore: your life story, the events that shaped you, and the values you hold dear.
        </p>
        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {SAMPLE_QUESTIONS.map((q) => (
            <SampleQuestionCard
              key={q.category}
              category={q.category}
              question={q.question}
            />
          ))}
        </div>
        <div className="text-center mt-10">
          <Link
            to="/discover"
            className="text-legacy-purple hover:underline font-medium"
            onClick={() => trackEvent('explore_questions_click')}
          >
            Explore more questions →
          </Link>
        </div>
      </div>
    </section>
  );
};

export default SampleQuestionsSection;
