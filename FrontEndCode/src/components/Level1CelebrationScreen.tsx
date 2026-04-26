import React from 'react';
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

interface Level1CelebrationScreenProps {
  onDismiss: () => void;
  storiesCount: number;
  lifeEventsQuestionCount?: number;
}

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

export const Level1CelebrationScreen: React.FC<Level1CelebrationScreenProps> = ({
  onDismiss,
  storiesCount,
  lifeEventsQuestionCount,
}) => {
  return (
    <Dialog open onOpenChange={(open) => { if (!open) onDismiss(); }}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader className="text-center">
          <DialogTitle className="text-2xl text-legacy-navy flex items-center justify-center gap-2">
            <span className="text-3xl" role="img" aria-label="celebration">🎉</span>
            Level 1 Complete!
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 pt-2">
            You've recorded {storiesCount} stories about your childhood, family, school days, and
            early friendships.
          </DialogDescription>
        </DialogHeader>

        {/* Locked level progression */}
        <div className="space-y-2 my-4">
          {LOCKED_LEVELS.map(({ level, name }) => (
            <div
              key={level}
              className="flex items-center gap-3 rounded-lg bg-gray-50 px-4 py-2.5 text-sm text-gray-500"
            >
              <Lock className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
              <span className="font-medium text-gray-700">Level {level}</span>
              <span className="text-gray-500">{name}</span>
            </div>
          ))}
        </div>

        {/* Life Events teaser */}
        {lifeEventsQuestionCount != null && lifeEventsQuestionCount > 0 && (
          <p className="text-sm font-medium text-legacy-purple text-center">
            Plus: {lifeEventsQuestionCount} personalized Life Events questions waiting for you
          </p>
        )}

        {/* CTA */}
        <div className="flex flex-col items-center gap-3 pt-2">
          <Button
            asChild
            className="w-full bg-legacy-purple hover:bg-legacy-purple/90 text-white"
          >
            <Link to="/pricing?plan=annual">
              Upgrade to Premium — $14.99/month or $149/year
            </Link>
          </Button>

          <button
            type="button"
            onClick={onDismiss}
            className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2"
          >
            Maybe Later
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
