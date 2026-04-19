import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import Logo from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import SignupModal from "@/components/landing/SignupModal";
import { trackEvent } from "@/lib/analytics";
import {
  Shield,
  Lock,
  EyeOff,
  Monitor,
  Smartphone,
  Tablet,
  MessageCircle,
  Mic,
  Heart,
  BookOpen,
  Calendar,
  Sparkles,
} from "lucide-react";

const Discover = () => {
  const { user } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalVariant, setModalVariant] = useState<"create-legacy" | "start-their-legacy">("create-legacy");

  const heroRef = useRef<HTMLElement>(null);
  const closingCtaRef = useRef<HTMLElement>(null);
  const [showFloatingCta, setShowFloatingCta] = useState(false);

  // 9.2 — Floating CTA visibility via IntersectionObserver
  useEffect(() => {
    if (!('IntersectionObserver' in window)) {
      setShowFloatingCta(true);
      return;
    }

    let heroPassed = false;
    let closingVisible = false;

    const heroObserver = new IntersectionObserver(([entry]) => {
      heroPassed = !entry.isIntersecting;
      setShowFloatingCta(heroPassed && !closingVisible);
    }, { threshold: 0 });

    const closingObserver = new IntersectionObserver(([entry]) => {
      closingVisible = entry.isIntersecting;
      setShowFloatingCta(heroPassed && !closingVisible);
    }, { threshold: 0 });

    if (heroRef.current) heroObserver.observe(heroRef.current);
    if (closingCtaRef.current) closingObserver.observe(closingCtaRef.current);

    return () => {
      heroObserver.disconnect();
      closingObserver.disconnect();
    };
  }, []);

  // 9.4 — SEO meta tags + 9.6 — page view tracking
  useEffect(() => {
    trackEvent('discover_page_view');

    const prevTitle = document.title;
    document.title = "Preserve Family Stories | Record Memories with SoulReel";

    let metaDesc = document.querySelector('meta[name="description"]') as HTMLMetaElement | null;
    const hadMeta = !!metaDesc;
    if (!metaDesc) {
      metaDesc = document.createElement('meta');
      metaDesc.name = 'description';
      document.head.appendChild(metaDesc);
    }
    const prevContent = metaDesc.content;
    metaDesc.content = "Preserve your family's stories with SoulReel. Record video memories through natural AI-guided conversations. No typing required.";

    return () => {
      document.title = prevTitle;
      if (hadMeta && metaDesc) {
        metaDesc.content = prevContent;
      } else if (metaDesc) {
        metaDesc.remove();
      }
    };
  }, []);

  // 9.6 — Section scroll tracking
  useEffect(() => {
    if (!('IntersectionObserver' in window)) return;

    const viewedSections = new Set<string>();

    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const section = (entry.target as HTMLElement).dataset.section;
          if (section && !viewedSections.has(section)) {
            viewedSections.add(section);
            trackEvent('discover_section_view', { section });
          }
        }
      });
    }, { threshold: 0 });

    const sections = document.querySelectorAll('[data-section]');
    sections.forEach((el) => sectionObserver.observe(el));

    return () => {
      sectionObserver.disconnect();
    };
  }, []);

  const openSignup = (variant: "create-legacy" | "start-their-legacy") => {
    setModalVariant(variant);
    setModalOpen(true);
    trackEvent("discover_persona_cta_click", { persona: variant === "create-legacy" ? "for-you" : "for-loved-one" });
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* HEADER */}
      <header className="w-full border-b sticky top-0 z-50 bg-white/95 backdrop-blur-sm">
        <div className="container mx-auto px-4 sm:px-8 py-4 flex justify-between items-center">
          <Link to="/">
            <Logo />
          </Link>
          <div className="flex gap-4">
            {user ? (
              <Link to="/dashboard">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="outline">Log In</Button>
                </Link>
                <Link to="/legacy-create-choice">
                  <Button className="bg-legacy-purple hover:bg-legacy-navy">Sign Up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* HERO / INTRO */}
        <section ref={heroRef} data-section="hero" className="py-16 sm:py-24 bg-gradient-to-b from-legacy-lightPurple to-white">
          <div className="container mx-auto px-4 sm:px-8 text-center max-w-3xl">
            <h1 className="text-4xl sm:text-5xl font-extrabold text-legacy-navy mb-6">
              Discover SoulReel — Preserve the Stories That Matter Most
            </h1>
            <p className="text-lg text-gray-600 leading-relaxed">
              SoulReel is a legacy video recording platform that helps you preserve family stories,
              record memories, and capture the wisdom of the people you love — through natural,
              guided conversations powered by AI.
            </p>
          </div>
        </section>

        {/* CONTENT PATHS */}
        <section data-section="content-paths" className="py-16 sm:py-20">
          <div className="container mx-auto px-4 sm:px-8">
            <h2 className="text-3xl font-bold text-center text-legacy-navy mb-4">
              Three Paths to Explore
            </h2>
            <p className="text-lg text-gray-600 text-center max-w-2xl mx-auto mb-12">
              Choose how you want to record memories and preserve your legacy — each path offers
              a unique way to capture what matters most.
            </p>
            <div className="grid md:grid-cols-3 gap-8">
              {/* Life Story Reflections */}
              <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100 hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-legacy-lightPurple rounded-xl flex items-center justify-center mb-4">
                  <BookOpen className="w-6 h-6 text-legacy-purple" />
                </div>
                <h3 className="text-xl font-semibold text-legacy-navy mb-3">Life Story Reflections</h3>
                <p className="text-gray-600 mb-4">
                  Explore the moments that shaped your life through guided questions about your
                  childhood, career, relationships, and personal growth.
                </p>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Sample Questions</p>
                  <p className="text-sm text-gray-500 italic">"What's the bravest thing you've ever done?"</p>
                  <p className="text-sm text-gray-500 italic">"What was your first job like?"</p>
                </div>
              </div>

              {/* Life Events */}
              <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100 hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-legacy-lightPurple rounded-xl flex items-center justify-center mb-4">
                  <Calendar className="w-6 h-6 text-legacy-purple" />
                </div>
                <h3 className="text-xl font-semibold text-legacy-navy mb-3">Life Events</h3>
                <p className="text-gray-600 mb-4">
                  Capture the milestones that defined you — becoming a parent, moving to a new city,
                  overcoming a challenge. Each event gets its own set of personalized questions.
                </p>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Sample Questions</p>
                  <p className="text-sm text-gray-500 italic">"Tell me about the day you became a parent."</p>
                  <p className="text-sm text-gray-500 italic">"What was the hardest decision you ever made?"</p>
                </div>
              </div>

              {/* Values & Emotions Deep Dive */}
              <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100 hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-legacy-lightPurple rounded-xl flex items-center justify-center mb-4">
                  <Sparkles className="w-6 h-6 text-legacy-purple" />
                </div>
                <h3 className="text-xl font-semibold text-legacy-navy mb-3">Values &amp; Emotions Deep Dive</h3>
                <p className="text-gray-600 mb-4">
                  Go beyond the surface with psychology-based assessments that reveal the values,
                  beliefs, and emotional patterns that make you who you are.
                </p>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Sample Questions</p>
                  <p className="text-sm text-gray-500 italic">"What value do you most want to pass on?"</p>
                  <p className="text-sm text-gray-500 italic">"What does courage mean to you?"</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW THE CONVERSATION WORKS */}
        <section id="how-it-works" data-section="how-it-works" className="py-16 sm:py-20 bg-gray-50">
          <div className="container mx-auto px-4 sm:px-8 max-w-3xl text-center">
            <h2 className="text-3xl font-bold text-legacy-navy mb-6">
              How the Conversation Works
            </h2>
            <p className="text-lg text-gray-600 leading-relaxed mb-8">
              Recording your legacy video is as easy as having a conversation with a good friend.
              No typing, no complicated setup — just press record and talk.
            </p>
            <div className="grid sm:grid-cols-3 gap-8 text-left">
              <div className="flex flex-col items-center text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mb-4">
                  <Mic className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">Just Talk</h3>
                <p className="text-sm text-gray-600">
                  Press record and answer the question in your own words. There's no wrong answer —
                  just your story, your way.
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mb-4">
                  <MessageCircle className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">AI Follows Up</h3>
                <p className="text-sm text-gray-600">
                  Our AI listens and asks thoughtful follow-up questions to help you go deeper —
                  like talking to someone who genuinely wants to hear more.
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mb-4">
                  <Heart className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">Stories Preserved</h3>
                <p className="text-sm text-gray-600">
                  Your recordings are saved securely, building a library of grandparent stories,
                  family history, and personal wisdom for future generations.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* WHO IS SOULREEL FOR? */}
        <section data-section="who-is-it-for" className="py-16 sm:py-20">
          <div className="container mx-auto px-4 sm:px-8">
            <h2 className="text-3xl font-bold text-center text-legacy-navy mb-12">
              Who Is SoulReel For?
            </h2>
            <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
              {/* For You */}
              <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100 text-center">
                <h3 className="text-2xl font-semibold text-legacy-navy mb-4">For You</h3>
                <p className="text-gray-600 mb-6">
                  You want to preserve your own stories, memories, and wisdom for the people who
                  matter most. Record your life on your own terms.
                </p>
                <Button
                  className="bg-legacy-purple hover:bg-legacy-navy"
                  onClick={() => openSignup("create-legacy")}
                >
                  Preserve Your First Memory
                </Button>
              </div>

              {/* For Someone You Love */}
              <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100 text-center">
                <h3 className="text-2xl font-semibold text-legacy-navy mb-4">For Someone You Love</h3>
                <p className="text-gray-600 mb-6">
                  You want to set it up for a parent, grandparent, or loved one. You'll manage the
                  account — they'll record their stories.
                </p>
                <Button
                  className="bg-legacy-purple hover:bg-legacy-navy"
                  onClick={() => openSignup("start-their-legacy")}
                >
                  Help Them Preserve Theirs
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* SECURITY & PRIVACY */}
        <section data-section="security" className="py-16 sm:py-20 bg-gray-50">
          <div className="container mx-auto px-4 sm:px-8">
            <h2 className="text-3xl font-bold text-center text-legacy-navy mb-12">
              Your Stories Are Safe With Us
            </h2>
            <div className="grid sm:grid-cols-3 gap-8 max-w-4xl mx-auto">
              <div className="text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mx-auto mb-4">
                  <Shield className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">Encrypted &amp; Protected</h3>
                <p className="text-sm text-gray-600">
                  All your recordings and data are encrypted in transit and at rest using
                  industry-standard security practices.
                </p>
              </div>
              <div className="text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mx-auto mb-4">
                  <Lock className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">You Own Your Data</h3>
                <p className="text-sm text-gray-600">
                  Your stories belong to you. You have full control over your data, including the
                  right to export or delete it at any time.
                </p>
              </div>
              <div className="text-center">
                <div className="w-14 h-14 bg-legacy-lightPurple rounded-full flex items-center justify-center mx-auto mb-4">
                  <EyeOff className="w-7 h-7 text-legacy-purple" />
                </div>
                <h3 className="font-semibold text-legacy-navy mb-2">Never Shared</h3>
                <p className="text-sm text-gray-600">
                  We never share your data with third parties. Your memories are private —
                  only you decide who gets to see them.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* DEVICE COMPATIBILITY */}
        <section data-section="device-compatibility" className="py-16 sm:py-20">
          <div className="container mx-auto px-4 sm:px-8 text-center max-w-3xl">
            <h2 className="text-3xl font-bold text-legacy-navy mb-4">
              Record From Anywhere
            </h2>
            <p className="text-lg text-gray-600 mb-10">
              All you need is a device with a camera. SoulReel works on any modern browser —
              no app download required.
            </p>
            <div className="flex justify-center gap-12 sm:gap-16">
              <div className="flex flex-col items-center gap-2">
                <Monitor className="w-10 h-10 text-legacy-purple" />
                <span className="text-sm text-gray-600">Computer</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Smartphone className="w-10 h-10 text-legacy-purple" />
                <span className="text-sm text-gray-600">Phone</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Tablet className="w-10 h-10 text-legacy-purple" />
                <span className="text-sm text-gray-600">Tablet</span>
              </div>
            </div>
          </div>
        </section>

        {/* CLOSING CTA */}
        <section ref={closingCtaRef} data-section="closing-cta" className="py-16 sm:py-20 bg-gradient-to-b from-legacy-lightPurple to-white">
          <div className="container mx-auto px-4 sm:px-8 text-center max-w-2xl">
            <h2 className="text-3xl font-bold text-legacy-navy mb-4">
              Ready to Preserve Your Story?
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              Every family has stories worth keeping. Start your legacy video recording today —
              it only takes a few minutes.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                className="bg-legacy-purple hover:bg-legacy-navy"
                onClick={() => {
                  trackEvent("discover_closing_cta_click");
                  openSignup("create-legacy");
                }}
              >
                Get Started Free — Preserve Your First Memory
              </Button>
              <Button
                size="lg"
                variant="outline"
                asChild
              >
                <a href="#how-it-works">See How It Works</a>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* FLOATING CTA */}
      {showFloatingCta && (
        <div className="fixed bottom-0 left-0 right-0 z-40 p-3 bg-white/95 backdrop-blur-sm border-t sm:bg-transparent sm:border-0 sm:p-0 sm:bottom-6 sm:right-6 sm:left-auto">
          <Button
            className="w-full sm:w-auto bg-legacy-purple hover:bg-legacy-navy text-white shadow-lg"
            onClick={() => {
              trackEvent('discover_floating_cta_click');
              openSignup('create-legacy');
            }}
          >
            Sign Up Free
          </Button>
        </div>
      )}

      {/* FOOTER */}
      <footer className="bg-legacy-navy text-white py-8">
        <div className="container mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row justify-between">
            <div>
              <Logo className="text-white" />
              <p className="mt-4 text-gray-300">
                Preserving your stories for future generations.
              </p>
            </div>

            <div className="mt-6 md:mt-0">
              <h3 className="font-semibold mb-2">Quick Links</h3>
              <ul className="space-y-1">
                <li>
                  <Link to="/" className="text-gray-300 hover:text-white">Home</Link>
                </li>
                <li>
                  <Link to="/login" className="text-gray-300 hover:text-white">Log In</Link>
                </li>
                <li>
                  <Link to="/legacy-create-choice" className="text-gray-300 hover:text-white">Sign Up</Link>
                </li>
                <li>
                  <Link to="/pricing" className="text-gray-300 hover:text-white">Pricing</Link>
                </li>
                <li>
                  <Link to="/your-data" className="text-gray-300 hover:text-white">Privacy &amp; Your Data</Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-700 mt-8 pt-6 text-center text-gray-400">
            <p>&copy; {new Date().getFullYear()} SoulReel. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* SIGNUP MODAL */}
      <SignupModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        variant={modalVariant}
      />
    </div>
  );
};

export default Discover;
