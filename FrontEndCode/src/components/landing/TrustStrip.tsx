import React from "react";
import { Shield, Lock, EyeOff } from "lucide-react";

const TRUST_SIGNALS = [
  { icon: Shield, label: "End-to-end encryption" },
  { icon: Lock, label: "Your data, your control" },
  { icon: EyeOff, label: "Never shared with third parties" },
] as const;

const TrustStrip: React.FC = () => {
  return (
    <section className="py-8 bg-white">
      <div className="container mx-auto px-4 sm:px-8">
        <div className="flex flex-wrap justify-center gap-8 md:gap-12">
          {TRUST_SIGNALS.map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 text-gray-500">
              <Icon className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-500">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TrustStrip;
