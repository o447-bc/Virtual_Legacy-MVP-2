import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { PRIMARY_CTA_CLASSES } from "./colorConfig";
import VideoEmbed from "./VideoEmbed";

interface HeroSectionProps {
  user: any | null;
  videoSrc?: string;
}

const HeroSection: React.FC<HeroSectionProps> = ({ user, videoSrc }) => {
  return (
    <section className="py-12 md:py-20">
      <div className="container mx-auto px-4 sm:px-8">
        <div className="grid md:grid-cols-2 gap-8 md:gap-12 items-center">
          {/* Text column */}
          <div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
              Preserve Your Legacy
            </h1>
            <p className="text-lg md:text-xl text-gray-600 mb-8">
              Record video responses to thoughtful questions and create a timeless
              collection of your experiences, wisdom, and personality.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              {user ? (
                <Link to="/record">
                  <Button className={`text-lg py-6 px-8 ${PRIMARY_CTA_CLASSES}`}>
                    Start Recording
                  </Button>
                </Link>
              ) : (
                <>
                  <div className="flex flex-col items-center">
                    <Link to="/signup-create-legacy">
                      <Button className={`text-lg py-6 px-8 ${PRIMARY_CTA_CLASSES}`}>
                        Start Free
                      </Button>
                    </Link>
                    <p className="text-sm text-gray-500 mt-2">
                      Preserve your own stories and memories
                    </p>
                  </div>
                  <div className="flex flex-col items-center">
                    <Link to="/signup-start-their-legacy">
                      <Button
                        variant="outline"
                        className="text-lg py-6 px-8 border-legacy-purple text-legacy-purple hover:bg-legacy-purple hover:text-white"
                      >
                        Start Their Legacy
                      </Button>
                    </Link>
                    <p className="text-sm text-gray-500 mt-2">
                      Set it up for a parent, grandparent, or loved one
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Video column */}
          <div>
            <VideoEmbed src={videoSrc} />
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
