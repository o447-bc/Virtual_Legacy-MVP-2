import React from "react";
import { MessageSquare, Mic, Heart } from "lucide-react";
import HowItWorksCard from "./HowItWorksCard";

const HowItWorksSection: React.FC = () => {
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
          />
          <HowItWorksCard
            stepNumber={2}
            icon={<Mic className="w-6 h-6" />}
            title="Have an AI-Guided Conversation"
            description="Our AI interviewer asks follow-up questions to draw out the deeper story behind your answer."
          />
          <HowItWorksCard
            stepNumber={3}
            icon={<Heart className="w-6 h-6" />}
            title="Share with the People Who Matter"
            description="Choose who receives your stories and when — now, later, or when the time is right."
          />
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
