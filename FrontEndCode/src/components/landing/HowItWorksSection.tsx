import React, { useState } from "react";
import { MessageSquare, Mic, Heart } from "lucide-react";
import HowItWorksCard from "./HowItWorksCard";
import { trackEvent } from "@/lib/analytics";

const HowItWorksSection: React.FC = () => {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const handleToggle = (step: number) => {
    const isCollapsing = expandedStep === step;
    setExpandedStep(isCollapsing ? null : step);
    trackEvent(isCollapsing ? 'how_it_works_collapse' : 'how_it_works_expand', { step });
  };

  return (
    <section className="bg-legacy-lightPurple py-16">
      <div className="container mx-auto px-4 sm:px-8">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>

        <div className="grid md:grid-cols-3 gap-8">
          <HowItWorksCard
            stepNumber={1}
            icon={<MessageSquare className="w-6 h-6" />}
            title="Choose a Question"
            description="Pick from thoughtful questions about your life story, key events, and values."
            expandedDescription="Browse through curated questions organized by theme — from childhood memories to career milestones to the values that guide your life. Each question is designed to unlock a meaningful story."
            isExpanded={expandedStep === 1}
            onToggle={() => handleToggle(1)}
          />
          <HowItWorksCard
            stepNumber={2}
            icon={<Mic className="w-6 h-6" />}
            title="Just Talk — We'll Listen"
            description="Just talk naturally. We'll ask the right follow-up questions to help you uncover the moments that matter most."
            expandedDescription="There's no typing involved. Just press record and speak naturally. Our AI listens and asks thoughtful follow-up questions to help you go deeper — like a conversation with a good friend."
            isExpanded={expandedStep === 2}
            onToggle={() => handleToggle(2)}
          />
          <HowItWorksCard
            stepNumber={3}
            icon={<Heart className="w-6 h-6" />}
            title="Share with the People Who Matter"
            description="Choose who receives your stories and when — now, later, or when the time is right."
            expandedDescription="Decide who can see your stories and when. Share immediately, set a future date, or create a time capsule that opens when the time is right. Your stories, your rules."
            isExpanded={expandedStep === 3}
            onToggle={() => handleToggle(3)}
          />
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
