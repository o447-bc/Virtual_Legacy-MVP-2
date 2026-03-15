import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Info, Target, Flame, Play } from "lucide-react";

const STORAGE_KEY = 'vl-dashboard-info-seen';

export const DashboardInfoPanel = () => {
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    // Check if user has seen this panel before
    const hasSeenInfo = localStorage.getItem(STORAGE_KEY);
    if (hasSeenInfo === 'true') {
      setIsOpen(false);
    }
  }, []);

  const handleToggle = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    
    // Save to localStorage when user collapses
    if (!newState) {
      localStorage.setItem(STORAGE_KEY, 'true');
    }
  };

  return (
    <Collapsible open={isOpen} onOpenChange={handleToggle} className="w-full">
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow-sm border border-blue-100">
        {/* Header with toggle */}
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full flex items-center justify-between p-4 hover:bg-white/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5 text-legacy-purple" />
              <h3 className="text-lg font-semibold text-legacy-navy">
                Getting Started Guide
              </h3>
            </div>
            {isOpen ? (
              <ChevronUp className="h-5 w-5 text-gray-500" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-500" />
            )}
          </Button>
        </CollapsibleTrigger>

        {/* Content */}
        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-4">
            {/* Understanding Progress */}
            <div className="flex gap-3">
              <Target className="h-5 w-5 text-legacy-purple flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Understanding Your Progress</h4>
                <p className="text-sm text-gray-600">
                  Questions are organized into 10 levels, from light memories to deep reflections. 
                  Complete all categories at your current level to advance to the next.
                </p>
              </div>
            </div>

            {/* Question Themes */}
            <div className="flex gap-3">
              <Info className="h-5 w-5 text-legacy-purple flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Question Themes</h4>
                <p className="text-sm text-gray-600">
                  Questions span 12 life themes—from childhood memories to messages for loved ones. 
                  Each theme appears across multiple levels.{" "}
                  <Link 
                    to="/question-themes" 
                    className="text-legacy-purple hover:text-legacy-navy font-medium underline"
                  >
                    View all themes
                  </Link>
                </p>
              </div>
            </div>

            {/* Daily Streaks */}
            <div className="flex gap-3">
              <Flame className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Daily Streaks</h4>
                <p className="text-sm text-gray-600">
                  Record at least one video daily to build your streak. 
                  Consistent recording helps preserve your legacy and unlock rewards.
                </p>
              </div>
            </div>

            {/* Getting Started */}
            <div className="flex gap-3">
              <Play className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Ready to Start?</h4>
                <p className="text-sm text-gray-600">
                  Click any progress bar below to begin recording responses for that category. 
                  Take your time and speak from the heart.
                </p>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
};
