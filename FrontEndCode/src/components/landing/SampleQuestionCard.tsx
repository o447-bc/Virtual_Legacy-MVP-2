import React from "react";

interface SampleQuestionCardProps {
  category: string;
  question: string;
}

const SampleQuestionCard: React.FC<SampleQuestionCardProps> = ({
  category,
  question,
}) => {
  return (
    <div className="border border-gray-200 rounded-lg p-6 border-l-4 border-l-legacy-purple transition-all hover:-translate-y-1 hover:shadow-lg">
      <p className="text-sm font-medium text-legacy-purple mb-3">{category}</p>
      <p className="text-gray-700 italic">&ldquo;{question}&rdquo;</p>
    </div>
  );
};

export default SampleQuestionCard;
