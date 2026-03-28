import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { getMakerVideos, VideosByType } from "@/services/videoService";
import { ProgressBar } from "@/components/ProgressBar";
import { getUserProgress, ProgressData } from "@/services/progressService";

const ResponseViewer: React.FC = () => {
  const { makerId } = useParams<{ makerId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const makerEmail = location.state?.makerEmail || makerId;
  const makerFirstName = location.state?.makerFirstName;
  const makerLastName = location.state?.makerLastName;
  const makerDisplayName = makerFirstName && makerLastName 
    ? `${makerFirstName} ${makerLastName}` 
    : makerEmail;
  const [videos, setVideos] = useState<VideosByType>({});
  const [activeTab, setActiveTab] = useState<string>('');
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [selectedAudio, setSelectedAudio] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    const fetchVideos = async () => {
      if (!makerId) return;
      try {
        const data = await getMakerVideos(makerId);
        setVideos(data);
        const types = Object.keys(data);
        if (types.length > 0) setActiveTab(types[0]);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchVideos();
  }, [makerId]);

  useEffect(() => {
    const fetchProgress = async () => {
      if (!makerId) return;
      const data = await getUserProgress(makerId);
      setProgress(data);
    };
    fetchProgress();
  }, [makerId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading videos...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  const questionTypes = Object.keys(videos);
  const activeVideos = videos[activeTab]?.videos || [];
  
  const handleResponseClick = (video: any) => {
    if (video.responseType === 'audio') {
      if (video.audioUrl) {
        setSelectedAudio(video.audioUrl);
      }
      return;
    }
    setSelectedVideo(video.videoUrl);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header />
      
      {/* Page-specific context bar */}
      <div className="bg-white border-b">
        <div className="container mx-auto py-3 px-4">
          <div className="flex justify-between items-center mb-3">
            {/* Page Title */}
            <h2 className="text-lg font-medium text-legacy-navy">{makerDisplayName}</h2>

            {/* Return to Dashboard */}
            <Button variant="outline" onClick={() => navigate('/benefactor-dashboard')}>
              Back to Dashboard
            </Button>
          </div>
          
          {/* Progress Bar */}
          {progress && (
            <ProgressBar 
              completed={progress.completed}
              total={progress.total}
              className="max-w-2xl mx-auto"
            />
          )}
        </div>
      </div>

      {/* Question Type Tabs */}
      <div className="bg-white border-b">
        <div className="container mx-auto overflow-x-auto">
          <div className="flex">
            {questionTypes.map(type => (
              <button
                key={type}
                onClick={() => setActiveTab(type)}
                className={`px-6 py-3 font-medium whitespace-nowrap min-w-[100px] ${
                  activeTab === type
                    ? 'border-b-2 border-legacy-purple text-legacy-purple'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                aria-label={`View ${videos[type].friendlyName} videos`}
              >
                {videos[type].friendlyName}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Video Grid */}
      <main className="container mx-auto px-4 py-8">
        
        {activeVideos.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No videos available for this category yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeVideos.map(video => (
              <div
                key={video.questionId}
                onClick={() => handleResponseClick(video)}
                className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-lg transition-shadow"
                role="button"
                tabIndex={0}
                aria-label={`View response: ${video.questionText}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleResponseClick(video);
                  }
                }}
              >
                {/* Thumbnail or Icon */}
                {video.responseType === 'audio' ? (
                  <div className="w-full h-40 bg-gradient-to-br from-blue-50 to-blue-100 rounded mb-2 flex flex-col items-center justify-center">
                    <svg className="w-16 h-16 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    <span className="text-sm text-blue-600 mt-2 font-medium">Audio Response</span>
                  </div>
                ) : video.thumbnailUrl ? (
                  <img 
                    src={video.thumbnailUrl} 
                    alt={`Thumbnail for ${video.questionText}`}
                    className="w-full h-40 object-cover rounded mb-2"
                  />
                ) : (
                  <div className="w-full h-40 bg-gray-200 rounded mb-2 flex items-center justify-center text-gray-400">
                    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                )}
                
                {/* Question Text */}
                <p className="font-medium text-sm line-clamp-2 mb-1 text-center">{video.questionText}</p>
                
                {/* Timestamp */}
                <p className="text-xs text-gray-500 text-center">
                  {new Date(video.timestamp).toLocaleDateString()}
                </p>
                
                {/* Response Type Label */}
                {video.responseType === 'video_memory' && (
                  <p className="text-xs text-purple-600 mt-1 text-center font-medium">
                    Video Memory
                  </p>
                )}
                
                {/* AI Summary */}
                {video.oneSentence && (
                  <p 
                    className="text-xs text-gray-600 mt-2 px-2 line-clamp-2 text-center italic"
                    title={video.oneSentence}
                  >
                    "{video.oneSentence}"
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Video Player Modal */}
      {selectedVideo && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedVideo(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Video player"
        >
          <div className="relative w-full max-w-4xl" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setSelectedVideo(null)}
              className="absolute -top-12 right-0 text-white text-3xl hover:text-gray-300 w-10 h-10 flex items-center justify-center"
              aria-label="Close video player"
            >
              &times;
            </button>
            <video 
              src={selectedVideo} 
              controls 
              autoPlay 
              className="w-full rounded"
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSelectedVideo(null);
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Audio Player Modal */}
      {selectedAudio && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedAudio(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Audio player"
        >
          <div className="relative w-full max-w-2xl" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setSelectedAudio(null)}
              className="absolute -top-12 right-0 text-white text-3xl hover:text-gray-300 w-10 h-10 flex items-center justify-center"
              aria-label="Close audio player"
            >
              &times;
            </button>
            <audio 
              src={selectedAudio} 
              controls 
              autoPlay 
              className="w-full"
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSelectedAudio(null);
                }
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseViewer;
