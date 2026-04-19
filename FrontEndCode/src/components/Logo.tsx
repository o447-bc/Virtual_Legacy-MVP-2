import React from "react";

const Logo: React.FC<{ className?: string }> = ({ className = "" }) => {
  const isWhite = className.includes('text-white');
  const textClasses = isWhite
    ? 'text-2xl font-extrabold'
    : 'text-2xl font-extrabold bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent';
  return (
    <span className={`${textClasses} ${className}`}>SoulReel</span>
  );
};

export default Logo;
