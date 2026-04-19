import React from "react";
import TestimonialCard from "./TestimonialCard";

const TESTIMONIALS = [
  {
    id: "1",
    quote:
      "I never thought my stories mattered until my grandchildren asked to hear them again.",
    name: "Margaret T.",
    relationship: "Grandmother, age 74",
  },
  {
    id: "2",
    quote:
      "Setting this up for my dad was the best gift I've ever given him. He lights up every time he records.",
    name: "David R.",
    relationship: "Son, set up for his father",
  },
];

const TestimonialSection: React.FC = () => {
  return (
    <section className="bg-legacy-lightPurple py-16">
      <div className="container mx-auto px-4 sm:px-8">
        <h2 className="text-3xl font-bold text-center text-legacy-navy mb-10">
          What Families Are Saying
        </h2>
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {TESTIMONIALS.map((testimonial) => (
            <TestimonialCard
              key={testimonial.id}
              quote={testimonial.quote}
              name={testimonial.name}
              relationship={testimonial.relationship}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default TestimonialSection;
