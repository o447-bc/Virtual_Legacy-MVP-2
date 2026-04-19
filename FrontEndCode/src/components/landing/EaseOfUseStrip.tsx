import React from "react";
import { Mic, Monitor, Smartphone, Tablet } from "lucide-react";

const EaseOfUseStrip: React.FC = () => {
  return (
    <section className="bg-gray-50 py-4">
      <div className="container mx-auto px-4 sm:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Mic className="w-4 h-4 text-gray-400" />
            <span>No typing required — just press record and talk</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Monitor className="w-4 h-4 text-gray-400" />
            <Smartphone className="w-4 h-4 text-gray-400" />
            <Tablet className="w-4 h-4 text-gray-400" />
            <span>Works on computer, tablet, or phone</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default EaseOfUseStrip;
