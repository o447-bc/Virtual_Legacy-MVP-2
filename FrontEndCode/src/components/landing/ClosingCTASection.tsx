import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { PRIMARY_CTA_CLASSES, CLOSING_CTA_GRADIENT } from "./colorConfig";
import { trackEvent } from "@/lib/analytics";

interface ClosingCTASectionProps {
  user: any | null;
}

const ClosingCTASection: React.FC<ClosingCTASectionProps> = ({ user }) => {
  return (
    <section className={`${CLOSING_CTA_GRADIENT} py-16`}>
      <div className="container mx-auto px-4 sm:px-8 text-center">
        <p className="text-base italic text-gray-500 mb-2">
          Every day holds stories worth preserving. Don't wait for someday.
        </p>
        <h2 className="text-3xl font-bold text-legacy-navy mb-4">
          Ready to preserve your story?
        </h2>
        <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
          Start capturing your experiences, wisdom, and personality today.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {user ? (
            <Link to="/pricing">
              <Button
                className={`text-lg py-5 px-8 ${PRIMARY_CTA_CLASSES}`}
                onClick={() => trackEvent('closing_cta_click', { button: 'primary' })}
              >
                View Plans
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/legacy-create-choice">
                <Button
                  className={`text-lg py-5 px-8 ${PRIMARY_CTA_CLASSES}`}
                  onClick={() => trackEvent('closing_cta_click', { button: 'primary' })}
                >
                  Get Started Free
                </Button>
              </Link>
              <Link to="/pricing">
                <Button
                  variant="outline"
                  className="text-lg py-5 px-8 border-legacy-purple text-legacy-purple hover:bg-legacy-purple hover:text-white"
                  onClick={() => trackEvent('closing_cta_click', { button: 'secondary' })}
                >
                  View Plans
                </Button>
              </Link>
            </>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-3">No credit card required</p>
      </div>
    </section>
  );
};

export default ClosingCTASection;
