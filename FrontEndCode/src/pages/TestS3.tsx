import React, { useState } from 'react';
import { S3Service } from '../services/s3Service';

export const TestS3: React.FC = () => {
  const [files, setFiles] = useState<string[]>([]);
  const [status, setStatus] = useState<string>('');

  const testUpload = async () => {
    const testFile = new File(['Hello from user!'], 'test.txt', { type: 'text/plain' });
    try {
      setStatus('Uploading...');
      await S3Service.uploadFile(testFile, 'test.txt');
      setStatus('Upload successful!');
    } catch (error) {
      setStatus(`Upload failed: ${error}`);
    }
  };

  const testList = async () => {
    try {
      setStatus('Listing files...');
      const userFiles = await S3Service.listUserFiles();
      setFiles(userFiles);
      setStatus(`Found ${userFiles.length} files`);
    } catch (error) {
      setStatus(`List failed: ${error}`);
    }
  };

  const testDownload = async () => {
    try {
      setStatus('Downloading...');
      const blob = await S3Service.downloadFile('test.txt');
      const text = await blob.text();
      setStatus(`Downloaded: ${text}`);
    } catch (error) {
      setStatus(`Download failed: ${error}`);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>S3 User Access Test</h2>
      
      <div style={{ marginBottom: '10px' }}>
        <button onClick={testUpload}>Upload Test File</button>
        <button onClick={testList} style={{ marginLeft: '10px' }}>List My Files</button>
        <button onClick={testDownload} style={{ marginLeft: '10px' }}>Download Test File</button>
      </div>

      <div>Status: {status}</div>
      
      {files.length > 0 && (
        <div>
          <h3>Your Files:</h3>
          <ul>
            {files.map(file => <li key={file}>{file}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
};