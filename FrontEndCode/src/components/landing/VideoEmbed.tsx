import React from "react";
import { Play } from "lucide-react";

interface VideoEmbedProps {
  src?: string;
  posterUrl?: string;
  title?: string;
}

const VideoEmbed: React.FC<VideoEmbedProps> = ({
  src,
  posterUrl,
  title = "SoulReel Demo",
}) => {
  const hasVideo = Boolean(src && src.trim());

  if (hasVideo) {
    return (
      <div
        data-state="video"
        className="aspect-video rounded-xl shadow-lg overflow-hidden"
      >
        <iframe
          src={src}
          title={title}
          allow="autoplay; encrypted-media"
          allowFullScreen
          className="w-full h-full"
        />
      </div>
    );
  }

  const placeholderStyle: React.CSSProperties = posterUrl
    ? {
        backgroundImage: `url(${posterUrl})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }
    : {};

  return (
    <div
      data-state="placeholder"
      className={`aspect-video rounded-xl shadow-lg flex flex-col items-center justify-center ${
        posterUrl ? "" : "bg-gradient-to-br from-legacy-lightPurple to-legacy-purple"
      }`}
      style={placeholderStyle}
    >
      <Play className="w-16 h-16 text-white mb-2" />
      <span className="text-white text-lg font-medium">
        Watch how it works
      </span>
    </div>
  );
};

export default VideoEmbed;
