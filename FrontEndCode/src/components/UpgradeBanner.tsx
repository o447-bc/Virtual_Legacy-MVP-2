import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Lock, X, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSubscription } from '@/contexts/SubscriptionContext';

const LOCKED_LEVELS = [
  { level: 2, name: 'Hobbies, Traditions & Holidays' },
  { level: 3, name: 'Love, Romance & Partnerships' },
  { level: 4, name: 'Work & Career' },
  { level: 5, name: 'Proudest Moments & Achievements' },
  { level: 6, name: 'Challenges & Hard Times' },
  { level: 7, name: 'Values & Guiding Principles' },
  { level: 8, name: 'Wisdom & Life Lessons' },
  { level: 9, name: 'Messages to Loved Ones' },
  { level: 10, name: 'Final Reflections' },
];

/* ─── HalfwayBanner ─────────────────────────────────────────────── */

export const HalfwayBanner: React.FC = () => {
  const { isPremium, level1CompletionPercent, level1CompletedAt } = useSubscription();
  const [dismissed, setDismissed] = useState(false);

  if (isPremium) return null;
  if (dismissed) return null;
  if (level1CompletionPercent < 50 || level1CompletedAt) return null;

  return (
    <div className="relative rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm" role="status">
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="absolute right-2 top-2 rounded-sm p-1 text-gray-400 hover:text-gray-600"
        aria-label="Dismiss banner"
      >
        <X className="h-4 w-4" />
      </button>
      <p className="pr-8 text-gray-700">
        You're halfway through Level 1. Premium unlocks 9 more levels of deeper questions.{' '}
        <Link to="/pricing" className="font-medium text-legacy-purple hover:underline">
          Learn more <ChevronRight className="inline h-3 w-3" />
        </Link>
      </p>
    </div>
  );
};

/* ─── PostCompletionBanner ──────────────────────────────────────── */

export const PostCompletionBanner: React.FC = () => {
  const { isPremium, level1CompletedAt } = useSubscription();

  if (isPremium) return null;
  if (!level1CompletedAt) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4" role="status">
      <h3 className="text-base font-semibold text-legacy-navy mb-3">
        Continue your legacy
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mb-4">
        {LOCKED_LEVELS.map(({ level, name }) => (
          <div key={level} className="flex items-center gap-2 text-sm text-gray-500">
            <Lock className="h-3.5 w-3.5 shrink-0 text-gray-400" aria-hidden="true" />
            <span>
              <span className="font-medium text-gray-600">L{level}</span> {name}
            </span>
          </div>
        ))}
      </div>

      <Button asChild className="bg-legacy-purple hover:bg-legacy-purple/90 text-white">
        <Link to="/pricing">
          Upgrade to Premium <ChevronRight className="h-4 w-4 ml-1" />
        </Link>
      </Button>
    </div>
  );
};

/* ─── BenefactorAwareBanner ─────────────────────────────────────── */

interface BenefactorAwareBannerProps {
  benefactorName?: string;
}

export const BenefactorAwareBanner: React.FC<BenefactorAwareBannerProps> = ({
  benefactorName,
}) => {
  const { isPremium, level1CompletedAt, benefactorCount } = useSubscription();

  if (isPremium) return null;
  if (!level1CompletedAt || benefactorCount <= 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm" role="status">
      <p className="text-gray-700">
        Your {benefactorName || 'family member'} can see your Level 1 stories. Upgrade to share
        the stories that really matter.{' '}
        <Link to="/pricing" className="font-medium text-legacy-purple hover:underline">
          Upgrade <ChevronRight className="inline h-3 w-3" />
        </Link>
      </p>
    </div>
  );
};

/* ─── LifeEventsTeaser ──────────────────────────────────────────── */

interface LifeEventsTeaserProps {
  questionCount: number;
}

export const LifeEventsTeaser: React.FC<LifeEventsTeaserProps> = ({
  questionCount,
}) => {
  const { isPremium, level1CompletedAt } = useSubscription();

  if (isPremium) return null;
  if (!level1CompletedAt) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm" role="status">
      <Link
        to="/pricing"
        className="flex items-center gap-2 text-gray-700 hover:text-legacy-purple transition-colors"
      >
        <Lock className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
        <span className="font-medium">{questionCount} personalized questions waiting for you</span>
        <ChevronRight className="h-4 w-4 ml-auto shrink-0" />
      </Link>
    </div>
  );
};
