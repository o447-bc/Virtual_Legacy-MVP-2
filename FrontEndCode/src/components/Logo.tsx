
import React from "react";

const Logo: React.FC<{ className?: string }> = ({ className = "" }) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-10 w-10 rounded-full bg-legacy-purple flex items-center justify-center text-white font-bold text-xl">
        VL
      </div>
      <span className="text-xl font-semibold bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
        Virtual Legacy
      </span>
    </div>
  );
};

export default Logo;
