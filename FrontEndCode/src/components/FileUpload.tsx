import React, { useState } from 'react';
import { S3Service } from '../services/s3Service';

export const FileUpload: React.FC = () => {
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await S3Service.uploadFile(file, file.name);
      console.log('File uploaded successfully');
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input 
        type="file" 
        onChange={handleFileUpload} 
        disabled={uploading}
      />
      {uploading && <p>Uploading...</p>}
    </div>
  );
};