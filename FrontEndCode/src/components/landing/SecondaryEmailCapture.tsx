import React, { useState } from "react";
import { trackEvent } from "@/lib/analytics";
import { EMAIL_CAPTURE_URL } from "@/config/api";

const SecondaryEmailCapture: React.FC = () => {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const alreadyCaptured = sessionStorage.getItem("sr_email_captured") === "true";

  if (alreadyCaptured && !submitted) {
    return (
      <section className="bg-transparent py-6">
        <div className="container mx-auto px-4 sm:px-8 max-w-xl text-center">
          <p className="text-sm text-gray-500">You're already on the list!</p>
        </div>
      </section>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const parts = email.split("@");
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
      setError("Please enter a valid email address");
      return;
    }

    setLoading(true);

    try {
      const referredBy = sessionStorage.getItem("sr_referral_hash") || undefined;

      const res = await fetch(EMAIL_CAPTURE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "founder-story", ...(referredBy ? { referredBy } : {}) }),
      });

      if (res.ok) {
        setSubmitted(true);
        setEmail("");
        sessionStorage.setItem("sr_email_captured", "true");
        trackEvent("email_capture_submit");
      } else if (res.status === 429) {
        setError("Too many requests. Please try again later.");
      } else if (res.status >= 400 && res.status < 500) {
        const data = await res.json().catch(() => null);
        setError(data?.error || "Please check your input and try again.");
      } else {
        setError("Something went wrong. Please try again later.");
      }
    } catch {
      setError("Something went wrong. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-transparent py-6">
      <div className="container mx-auto px-4 sm:px-8 max-w-xl text-center">
        <p className="text-sm text-gray-600 mb-3">
          Moved by this story? We'll send you a question to think about.
        </p>
        {submitted ? (
          <p className="text-green-600 text-sm">
            Check your inbox — your first question is on its way!
          </p>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-legacy-purple focus:border-transparent"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 bg-legacy-purple text-white rounded-md text-sm font-medium hover:bg-legacy-navy transition-colors disabled:opacity-50"
              >
                {loading ? "Sending..." : "Send me a question"}
              </button>
            </form>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </>
        )}
      </div>
    </section>
  );
};

export default SecondaryEmailCapture;
