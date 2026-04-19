import React, { useState } from "react";
import { trackEvent } from "@/lib/analytics";

const EmailCaptureSection: React.FC = () => {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const parts = email.split("@");
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
      setError("Please enter a valid email address");
      return;
    }

    setSubmitted(true);
    setEmail("");
    trackEvent("email_capture_submit");
  };

  return (
    <section className="bg-gray-50 py-10">
      <div className="container mx-auto px-4 sm:px-8 max-w-xl text-center">
        <p className="text-lg text-gray-600 mb-4">
          Not ready yet? Get a free sample question delivered to your inbox.
        </p>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-legacy-purple focus:border-transparent"
          />
          <button
            type="submit"
            className="px-6 py-2 bg-legacy-purple text-white rounded-md text-sm font-medium hover:bg-legacy-navy transition-colors"
          >
            Subscribe
          </button>
        </form>
        {submitted && (
          <p className="text-green-600 text-sm mt-2">You're on the list!</p>
        )}
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>
    </section>
  );
};

export default EmailCaptureSection;
