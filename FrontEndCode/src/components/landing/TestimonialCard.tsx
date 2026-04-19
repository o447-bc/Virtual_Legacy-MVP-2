import React from "react";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";

interface TestimonialCardProps {
  quote: string;
  name: string;
  relationship: string;
  avatarUrl?: string;
}

const TestimonialCard: React.FC<TestimonialCardProps> = ({
  quote,
  name,
  relationship,
  avatarUrl,
}) => {
  const initials = name.charAt(0).toUpperCase();

  return (
    <div className="border border-gray-200 rounded-lg p-6 shadow-sm">
      <Avatar className="h-12 w-12 mb-4">
        {avatarUrl && <AvatarImage src={avatarUrl} alt={name} />}
        <AvatarFallback className="bg-legacy-purple text-white">
          {initials}
        </AvatarFallback>
      </Avatar>
      <p className="text-gray-700 italic mb-4">&ldquo;{quote}&rdquo;</p>
      <p className="font-semibold text-legacy-navy">{name}</p>
      <p className="text-sm text-gray-500">{relationship}</p>
    </div>
  );
};

export default TestimonialCard;
