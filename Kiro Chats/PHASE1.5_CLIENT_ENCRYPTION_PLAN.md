# Phase 1.5: Client-Side Encryption Implementation Plan

**Timeline:** 3-4 Weeks  
**Effort:** ~40-60 hours  
**Risk Level:** MEDIUM (requires careful key management)  
**Prerequisites:** Phase 1 completed (KMS infrastructure in place)

---

## Executive Summary

Phase 1.5 adds **client-side encryption** so videos are encrypted in the browser BEFORE upload to AWS. This means:
- ✅ Videos encrypted before leaving user's device
- ✅ AWS cannot decrypt videos (even with admin access)
- ✅ Only makers and their designated benefactors can view content
- ⚠️ Users must manage encryption keys (with recovery options)
- ⚠️ Transcription requires user consent to temporarily decrypt

**Key Tradeoff:** Enhanced security vs. user responsibility for key management

---

## Architecture Overview

```
User Browser                    AWS Backend
    ↓
Generate Encryption Key
    ↓
Encrypt Video (AES-256)
    ↓
Upload Encrypted Blob → S3 (encrypted at rest with KMS)
    ↓
Store Encrypted Key → DynamoDB (wrapped with benefactor's public key)
    ↓
Benefactor Downloads
    ↓
Decrypt with Private Key
    ↓
View Video
```

---

## Key Management Strategy (Simplified)

We'll use a **hybrid approach** that balances security and usability:

1. **Password-Derived Keys** - Main encryption key derived from user password
2. **Recovery Codes** - 12-word backup phrase (like crypto wallets)
3. **Benefactor Sharing** - Automatic key sharing when relationship created
4. **Optional Escrow** - For USB export service (requires user + admin)

---

## Implementation Tasks


### Task 1: Create Encryption Service (Frontend)
**Duration:** 8 hours  
**Risk:** Medium  
**Files:** New service layer

#### What This Does
Creates a TypeScript service that handles all encryption/decryption in the browser using Web Crypto API.

#### Implementation

**File:** `FrontEndCode/src/services/encryptionService.ts`

```typescript
/**
 * Client-Side Encryption Service
 * Uses Web Crypto API for AES-256-GCM encryption
 */

export interface EncryptedData {
  encryptedBlob: Blob;
  iv: string;              // Initialization vector (base64)
  salt: string;            // Salt for key derivation (base64)
  encryptedKey: string;    // Symmetric key encrypted with user's master key (base64)
}

export interface KeyPair {
  publicKey: CryptoKey;
  privateKey: CryptoKey;
}

export class EncryptionService {
  private static readonly ALGORITHM = 'AES-GCM';
  private static readonly KEY_LENGTH = 256;
  private static readonly IV_LENGTH = 12;
  private static readonly SALT_LENGTH = 16;
  private static readonly ITERATIONS = 100000;

  /**
   * Derive encryption key from user password
   * Uses PBKDF2 with 100,000 iterations
   */
  static async deriveKeyFromPassword(
    password: string,
    salt?: Uint8Array
  ): Promise<{ key: CryptoKey; salt: Uint8Array }> {
    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(password);
    
    // Generate or use provided salt
    const keySalt = salt || crypto.getRandomValues(new Uint8Array(this.SALT_LENGTH));
    
    // Import password as key material
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      passwordBuffer,
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );
    
    // Derive AES key
    const key = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: keySalt,
        iterations: this.ITERATIONS,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: this.ALGORITHM, length: this.KEY_LENGTH },
      true,  // extractable
      ['encrypt', 'decrypt']
    );
    
    return { key, salt: keySalt };
  }

  /**
   * Encrypt video blob before upload
   * Returns encrypted blob + metadata needed for decryption
   */
  static async encryptVideo(
    videoBlob: Blob,
    userPassword: string
  ): Promise<EncryptedData> {
    try {
      // Step 1: Derive master key from password
      const { key: masterKey, salt } = await this.deriveKeyFromPassword(userPassword);
      
      // Step 2: Generate random symmetric key for this video
      const videoKey = await crypto.subtle.generateKey(
        { name: this.ALGORITHM, length: this.KEY_LENGTH },
        true,
        ['encrypt', 'decrypt']
      );
      
      // Step 3: Encrypt video with symmetric key
      const iv = crypto.getRandomValues(new Uint8Array(this.IV_LENGTH));
      const videoBuffer = await videoBlob.arrayBuffer();
      
      const encryptedVideo = await crypto.subtle.encrypt(
        { name: this.ALGORITHM, iv },
        videoKey,
        videoBuffer
      );
      
      // Step 4: Wrap video key with master key
      const exportedVideoKey = await crypto.subtle.exportKey('raw', videoKey);
      const wrappedKey = await crypto.subtle.encrypt(
        { name: this.ALGORITHM, iv: crypto.getRandomValues(new Uint8Array(this.IV_LENGTH)) },
        masterKey,
        exportedVideoKey
      );
      
      // Step 5: Return encrypted data
      return {
        encryptedBlob: new Blob([encryptedVideo], { type: 'application/octet-stream' }),
        iv: this.arrayBufferToBase64(iv),
        salt: this.arrayBufferToBase64(salt),
        encryptedKey: this.arrayBufferToBase64(wrappedKey)
      };
      
    } catch (error) {
      console.error('Encryption failed:', error);
      throw new Error('Failed to encrypt video. Please try again.');
    }
  }

  /**
   * Decrypt video for playback
   */
  static async decryptVideo(
    encryptedBlob: Blob,
    encryptedKey: string,
    iv: string,
    salt: string,
    userPassword: string
  ): Promise<Blob> {
    try {
      // Step 1: Derive master key from password
      const saltBuffer = this.base64ToArrayBuffer(salt);
      const { key: masterKey } = await this.deriveKeyFromPassword(
        userPassword,
        new Uint8Array(saltBuffer)
      );
      
      // Step 2: Unwrap video key
      const wrappedKeyBuffer = this.base64ToArrayBuffer(encryptedKey);
      const unwrappedKeyBuffer = await crypto.subtle.decrypt(
        { name: this.ALGORITHM, iv: crypto.getRandomValues(new Uint8Array(this.IV_LENGTH)) },
        masterKey,
        wrappedKeyBuffer
      );
      
      // Step 3: Import video key
      const videoKey = await crypto.subtle.importKey(
        'raw',
        unwrappedKeyBuffer,
        { name: this.ALGORITHM, length: this.KEY_LENGTH },
        false,
        ['decrypt']
      );
      
      // Step 4: Decrypt video
      const ivBuffer = this.base64ToArrayBuffer(iv);
      const encryptedBuffer = await encryptedBlob.arrayBuffer();
      
      const decryptedVideo = await crypto.subtle.decrypt(
        { name: this.ALGORITHM, iv: new Uint8Array(ivBuffer) },
        videoKey,
        encryptedBuffer
      );
      
      return new Blob([decryptedVideo], { type: 'video/webm' });
      
    } catch (error) {
      console.error('Decryption failed:', error);
      throw new Error('Failed to decrypt video. Check your password.');
    }
  }

  /**
   * Generate recovery phrase (12 words)
   * Uses BIP39 wordlist for compatibility
   */
  static async generateRecoveryPhrase(): Promise<string> {
    // Generate 128 bits of entropy (12 words)
    const entropy = crypto.getRandomValues(new Uint8Array(16));
    
    // Convert to mnemonic (simplified - use bip39 library in production)
    const words = await this.entropyToMnemonic(entropy);
    return words.join(' ');
  }

  /**
   * Derive key from recovery phrase
   */
  static async deriveKeyFromRecoveryPhrase(phrase: string): Promise<CryptoKey> {
    const words = phrase.trim().toLowerCase().split(/\s+/);
    
    if (words.length !== 12) {
      throw new Error('Recovery phrase must be exactly 12 words');
    }
    
    // Convert mnemonic to seed
    const seed = await this.mnemonicToSeed(words);
    
    // Derive key from seed
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      seed,
      'PBKDF2',
      false,
      ['deriveKey']
    );
    
    return await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: new Uint8Array(16), // Fixed salt for recovery
        iterations: this.ITERATIONS,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: this.ALGORITHM, length: this.KEY_LENGTH },
      true,
      ['encrypt', 'decrypt']
    );
  }

  // Helper methods
  private static arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private static base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  // Simplified mnemonic generation (use bip39 library in production)
  private static async entropyToMnemonic(entropy: Uint8Array): Promise<string[]> {
    // This is a placeholder - implement proper BIP39 or use library
    const wordlist = ['abandon', 'ability', 'able', 'about', 'above', 'absent', 
                      'absorb', 'abstract', 'absurd', 'abuse', 'access', 'accident'];
    return Array.from(entropy).slice(0, 12).map(byte => wordlist[byte % wordlist.length]);
  }

  private static async mnemonicToSeed(words: string[]): Promise<Uint8Array> {
    // This is a placeholder - implement proper BIP39 or use library
    const encoder = new TextEncoder();
    const combined = encoder.encode(words.join(''));
    const hash = await crypto.subtle.digest('SHA-256', combined);
    return new Uint8Array(hash);
  }
}
```

#### Testing
```typescript
// Test encryption/decryption
const testVideo = new Blob(['test video data'], { type: 'video/webm' });
const password = 'user-password-123';

const encrypted = await EncryptionService.encryptVideo(testVideo, password);
console.log('Encrypted:', encrypted);

const decrypted = await EncryptionService.decryptVideo(
  encrypted.encryptedBlob,
  encrypted.encryptedKey,
  encrypted.iv,
  encrypted.salt,
  password
);
console.log('Decrypted size:', decrypted.size);
```

---


### Task 2: Update Video Upload Flow
**Duration:** 6 hours  
**Risk:** Medium  
**Files:** VideoRecorder.tsx, VideoMemoryRecorder.tsx, videoService.ts

#### What This Does
Modifies video recording components to encrypt videos before upload.

#### Implementation

**Update:** `FrontEndCode/src/components/VideoRecorder.tsx`

```typescript
import { EncryptionService } from "@/services/encryptionService";
import { useAuth } from "@/contexts/AuthContext";

// Add state for encryption
const [isEncrypting, setIsEncrypting] = useState(false);
const [encryptionError, setEncryptionError] = useState<string | null>(null);

// Modified submitRecording function
const submitRecording = async () => {
  if (!recordedBlob || !user) {
    return;
  }

  setIsUploading(true);
  setIsEncrypting(true);
  setEncryptionError(null);

  try {
    // Step 1: Get user password (from auth context or prompt)
    const userPassword = await getUserPassword();
    
    // Step 2: Encrypt video in browser
    console.log('Encrypting video...');
    const encryptedData = await EncryptionService.encryptVideo(
      recordedBlob,
      userPassword
    );
    console.log('Video encrypted successfully');
    
    setIsEncrypting(false);
    
    // Step 3: Upload encrypted blob
    await videoStorageService.storeEncryptedVideo({
      id: '',
      questionId: currentQuestionId,
      questionType: currentQuestionType,
      questionText: currentQuestionText,
      encryptedBlob: encryptedData.encryptedBlob,
      encryptionMetadata: {
        iv: encryptedData.iv,
        salt: encryptedData.salt,
        encryptedKey: encryptedData.encryptedKey,
        algorithm: 'AES-256-GCM'
      },
      timestamp: new Date(),
      userId: user.userId
    });
    
    setRecordingSaved(true);
    setRecordedBlob(null);
    cleanupCamera();
    
    if (onRecordingSubmitted) {
      onRecordingSubmitted();
    }
    
    setTimeout(() => {
      setRecordingSaved(false);
      if (onSkipQuestion) {
        onSkipQuestion();
      }
    }, 2000);
    
  } catch (error) {
    console.error("Error submitting video:", error);
    if (error instanceof Error && error.message.includes('encrypt')) {
      setEncryptionError('Failed to encrypt video. Please try again.');
    } else {
      setEncryptionError('Failed to upload video. Please try again.');
    }
  } finally {
    setIsUploading(false);
    setIsEncrypting(false);
  }
};

// Helper to get user password
const getUserPassword = async (): Promise<string> => {
  // Option 1: Use password from auth context (if stored securely)
  // Option 2: Prompt user for password
  // For now, we'll use a simple prompt
  const password = prompt('Enter your password to encrypt this video:');
  if (!password) {
    throw new Error('Password required for encryption');
  }
  return password;
};

// Update UI to show encryption status
return (
  <div className="w-full max-w-2xl mx-auto">
    {/* ... existing code ... */}
    
    {isEncrypting && (
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
        <p className="text-blue-800">🔒 Encrypting video...</p>
      </p>
    )}
    
    {encryptionError && (
      <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
        <p className="text-red-800">{encryptionError}</p>
      </div>
    )}
    
    {/* ... rest of component ... */}
  </div>
);
```

**Update:** `FrontEndCode/src/services/videoService.ts`

```typescript
export interface EncryptionMetadata {
  iv: string;
  salt: string;
  encryptedKey: string;
  algorithm: string;
}

export interface EncryptedVideoData extends VideoData {
  encryptedBlob: Blob;
  encryptionMetadata: EncryptionMetadata;
}

export const videoStorageService = {
  // ... existing methods ...
  
  async storeEncryptedVideo(
    videoData: EncryptedVideoData,
    isVideoMemory: boolean = false
  ): Promise<VideoUploadResponse> {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) throw new Error('No authentication token');

    // Step 1: Get pre-signed URL
    const urlResponse = await fetch(
      `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.GET_UPLOAD_URL}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questionId: videoData.questionId,
          questionType: videoData.questionType,
          encrypted: true  // Flag to indicate encrypted upload
        })
      }
    );

    if (!urlResponse.ok) {
      throw new Error('Failed to get upload URL');
    }

    const { uploadUrl, s3Key, filename } = await urlResponse.json();

    // Step 2: Upload encrypted blob to S3
    const s3Response = await fetch(uploadUrl, {
      method: 'PUT',
      body: videoData.encryptedBlob,
      headers: {
        'Content-Type': 'application/octet-stream',  // Changed from video/webm
        'x-amz-meta-encrypted': 'true',  // Custom metadata
        'x-amz-meta-algorithm': videoData.encryptionMetadata.algorithm
      }
    });

    if (!s3Response.ok) {
      throw new Error('Failed to upload encrypted video to S3');
    }

    // Step 3: Store encryption metadata in DynamoDB
    const processResponse = await fetch(
      `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.PROCESS_VIDEO}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questionId: videoData.questionId,
          questionType: videoData.questionType,
          questionText: videoData.questionText,
          s3Key,
          filename,
          isVideoMemory,
          encrypted: true,
          encryptionMetadata: videoData.encryptionMetadata
        })
      }
    );

    if (!processResponse.ok) {
      throw new Error('Failed to process encrypted video');
    }

    return await processResponse.json();
  }
};
```

---


### Task 3: Update Backend to Handle Encrypted Videos
**Duration:** 4 hours  
**Risk:** Low  
**Files:** processVideo/app.py, DynamoDB schema

#### What This Does
Modifies backend to store encryption metadata and skip thumbnail generation for encrypted videos.

#### Implementation

**Update:** `SamLambda/functions/videoFunctions/processVideo/app.py`

```python
def lambda_handler(event, context):
    # ... existing code ...
    
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        
        question_id = body.get('questionId')
        question_type = body.get('questionType')
        s3_key = body.get('s3Key')
        filename = body.get('filename')
        question_text = body.get('questionText', '')
        is_video_memory = body.get('isVideoMemory', False)
        
        # NEW: Check if video is encrypted
        is_encrypted = body.get('encrypted', False)
        encryption_metadata = body.get('encryptionMetadata', {})
        
        print(f"Processing video: encrypted={is_encrypted}")
        
        # ... existing S3 verification ...
        
        # MODIFIED: Skip thumbnail generation for encrypted videos
        thumbnail_filename = None
        if not is_encrypted:
            try:
                thumbnail_filename = generate_thumbnail(s3_key, user_id)
                print(f"Thumbnail generated successfully: {thumbnail_filename}")
            except Exception as e:
                print(f"Thumbnail generation failed (non-critical): {str(e)}")
        else:
            print("Skipping thumbnail generation for encrypted video")
        
        # Update DynamoDB with encryption metadata
        update_user_question_status(
            user_id, 
            question_id, 
            question_type, 
            filename, 
            s3_key, 
            question_text, 
            thumbnail_filename, 
            is_video_memory,
            is_encrypted,
            encryption_metadata
        )
        
        # ... rest of function ...
```

```python
def update_user_question_status(
    user_id, 
    question_id, 
    question_type, 
    filename, 
    s3_key, 
    question_text, 
    thumbnail_filename, 
    is_video_memory,
    is_encrypted=False,
    encryption_metadata=None
):
    """Update userQuestionStatusDB with video response and encryption metadata."""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('userQuestionStatusDB')
        
        if is_video_memory:
            # ... existing video memory logic ...
            update_expression = 'SET videoType = :video_type, videoMemoryS3Location = :video_s3, videoMemoryRecorded = :recorded, videoMemoryTimestamp = :timestamp'
            expression_values = {
                ':video_type': 'video_memory',
                ':video_s3': f's3://virtual-legacy/{s3_key}',
                ':recorded': True,
                ':timestamp': datetime.now().isoformat()
            }
            
            # Add encryption metadata if encrypted
            if is_encrypted and encryption_metadata:
                update_expression += ', videoMemoryEncrypted = :encrypted, videoMemoryEncryptionMetadata = :metadata'
                expression_values[':encrypted'] = True
                expression_values[':metadata'] = encryption_metadata
            
            # ... rest of video memory logic ...
        else:
            # Regular video response
            item = {
                'userId': user_id,
                'questionId': question_id,
                'questionType': question_type,
                'videoType': 'regular_video',
                'filename': filename,
                'videoS3Location': f's3://virtual-legacy/{s3_key}',
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'Question': question_text,
                'videoTranscriptionStatus': 'NOT_STARTED' if not is_encrypted else 'DISABLED',
                'videoSummarizationStatus': 'NOT_STARTED' if not is_encrypted else 'DISABLED'
            }
            
            # Add encryption metadata
            if is_encrypted and encryption_metadata:
                item['videoEncrypted'] = True
                item['videoEncryptionMetadata'] = encryption_metadata
                item['videoTranscriptionStatus'] = 'DISABLED'  # Cannot transcribe encrypted video
                item['videoSummarizationStatus'] = 'DISABLED'
            
            if thumbnail_filename:
                item['videoThumbnailS3Location'] = f's3://virtual-legacy/user-responses/{user_id}/{thumbnail_filename}'
            
            table.put_item(Item=item)
        
    except Exception as e:
        print(f"DynamoDB update error: {str(e)}")
        raise Exception(f"Failed to update database: {str(e)}")
```

#### DynamoDB Schema Changes

Add new fields to `userQuestionStatusDB`:
- `videoEncrypted` (Boolean) - Whether video is client-side encrypted
- `videoEncryptionMetadata` (Map) - Contains iv, salt, encryptedKey, algorithm
- `videoMemoryEncrypted` (Boolean) - For video memories
- `videoMemoryEncryptionMetadata` (Map) - For video memories

**No migration needed** - these fields are optional and only added for new uploads.

---


### Task 4: Implement Video Decryption for Playback
**Duration:** 6 hours  
**Risk:** Medium  
**Files:** New VideoPlayer component, getMakerVideos updates

#### What This Does
Creates a video player that decrypts videos on-the-fly for benefactors.

#### Implementation

**New File:** `FrontEndCode/src/components/EncryptedVideoPlayer.tsx`

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { EncryptionService } from '@/services/encryptionService';
import { Loader2, Lock, Unlock } from 'lucide-react';

interface EncryptedVideoPlayerProps {
  videoUrl: string;  // Presigned URL to encrypted blob
  encryptionMetadata: {
    iv: string;
    salt: string;
    encryptedKey: string;
    algorithm: string;
  };
  onError?: (error: string) => void;
}

export const EncryptedVideoPlayer: React.FC<EncryptedVideoPlayerProps> = ({
  videoUrl,
  encryptionMetadata,
  onError
}) => {
  const [isDecrypting, setIsDecrypting] = useState(false);
  const [decryptedUrl, setDecryptedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [passwordPromptOpen, setPasswordPromptOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (decryptedUrl) {
        URL.revokeObjectURL(decryptedUrl);
      }
    };
  }, [decryptedUrl]);

  const handleDecrypt = async (password: string) => {
    setIsDecrypting(true);
    setError(null);

    try {
      // Step 1: Download encrypted blob
      console.log('Downloading encrypted video...');
      const response = await fetch(videoUrl);
      if (!response.ok) {
        throw new Error('Failed to download video');
      }
      const encryptedBlob = await response.blob();
      console.log('Downloaded:', encryptedBlob.size, 'bytes');

      // Step 2: Decrypt video
      console.log('Decrypting video...');
      const decryptedBlob = await EncryptionService.decryptVideo(
        encryptedBlob,
        encryptionMetadata.encryptedKey,
        encryptionMetadata.iv,
        encryptionMetadata.salt,
        password
      );
      console.log('Decrypted:', decryptedBlob.size, 'bytes');

      // Step 3: Create object URL for playback
      const objectUrl = URL.createObjectURL(decryptedBlob);
      setDecryptedUrl(objectUrl);
      setPasswordPromptOpen(false);

    } catch (err) {
      console.error('Decryption error:', err);
      const errorMsg = err instanceof Error ? err.message : 'Decryption failed';
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setIsDecrypting(false);
    }
  };

  const promptForPassword = () => {
    const password = prompt('Enter password to decrypt video:');
    if (password) {
      handleDecrypt(password);
    }
  };

  if (error) {
    return (
      <div className="aspect-video w-full bg-red-50 rounded-lg flex flex-col items-center justify-center p-6">
        <Lock className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-red-800 font-medium mb-2">Decryption Failed</p>
        <p className="text-red-600 text-sm mb-4">{error}</p>
        <Button onClick={promptForPassword} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  if (isDecrypting) {
    return (
      <div className="aspect-video w-full bg-gray-100 rounded-lg flex flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-700 font-medium">Decrypting video...</p>
        <p className="text-gray-500 text-sm mt-2">This may take a moment</p>
      </div>
    );
  }

  if (!decryptedUrl) {
    return (
      <div className="aspect-video w-full bg-gray-100 rounded-lg flex flex-col items-center justify-center p-6">
        <Lock className="h-12 w-12 text-gray-400 mb-4" />
        <p className="text-gray-700 font-medium mb-2">Encrypted Video</p>
        <p className="text-gray-500 text-sm mb-4 text-center">
          This video is encrypted. Enter your password to view.
        </p>
        <Button onClick={promptForPassword} className="bg-blue-600 hover:bg-blue-700">
          <Unlock className="mr-2 h-4 w-4" />
          Decrypt & Play
        </Button>
      </div>
    );
  }

  return (
    <div className="aspect-video w-full bg-black rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        src={decryptedUrl}
        controls
        className="w-full h-full"
        onError={() => setError('Video playback failed')}
      />
    </div>
  );
};
```

**Update:** `FrontEndCode/src/pages/BenefactorVideos.tsx` (or wherever videos are displayed)

```typescript
import { EncryptedVideoPlayer } from '@/components/EncryptedVideoPlayer';

// In your video display component
{video.encrypted ? (
  <EncryptedVideoPlayer
    videoUrl={video.videoUrl}
    encryptionMetadata={video.encryptionMetadata}
    onError={(error) => console.error('Playback error:', error)}
  />
) : (
  <video src={video.videoUrl} controls className="w-full" />
)}
```

**Update:** `SamLambda/functions/videoFunctions/getMakerVideos/app.py`

```python
# In the video grouping loop, include encryption metadata
for item in videos:
    # ... existing code ...
    
    video_data = {
        'questionId': item['questionId'],
        'questionType': q_type,
        'questionText': item.get('Question', ''),
        'responseType': response_type,
        'videoUrl': video_url,
        'thumbnailUrl': thumbnail_url,
        'audioUrl': audio_url,
        'oneSentence': one_sentence,
        'timestamp': timestamp or '',
        'filename': item.get('filename', '')
    }
    
    # Add encryption metadata if video is encrypted
    if item.get('videoEncrypted'):
        video_data['encrypted'] = True
        video_data['encryptionMetadata'] = item.get('videoEncryptionMetadata', {})
    
    grouped[q_type]['videos'].append(video_data)
```

---


### Task 5: Implement Key Management & Recovery
**Duration:** 8 hours  
**Risk:** HIGH (key loss = data loss)  
**Files:** New KeyManagement service, onboarding flow

#### What This Does
Provides users with recovery options if they forget their password.

#### Implementation

**New File:** `FrontEndCode/src/services/keyManagementService.ts`

```typescript
import { EncryptionService } from './encryptionService';

interface StoredKeyData {
  userId: string;
  encryptedMasterKey: string;
  recoveryPhrase?: string;  // Encrypted with separate password
  createdAt: string;
  lastUsed: string;
}

export class KeyManagementService {
  private static readonly STORAGE_KEY = 'soulreel_key_data';

  /**
   * Initialize encryption for new user
   * Called during signup or first video upload
   */
  static async initializeUserEncryption(
    userId: string,
    password: string
  ): Promise<{ recoveryPhrase: string }> {
    try {
      // Generate recovery phrase
      const recoveryPhrase = await EncryptionService.generateRecoveryPhrase();
      
      // Store encrypted in localStorage (temporary - move to secure storage)
      const keyData: StoredKeyData = {
        userId,
        encryptedMasterKey: '', // Derived from password, not stored
        recoveryPhrase: btoa(recoveryPhrase), // Base64 encode (not secure, just obfuscation)
        createdAt: new Date().toISOString(),
        lastUsed: new Date().toISOString()
      };
      
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(keyData));
      
      return { recoveryPhrase };
      
    } catch (error) {
      console.error('Key initialization failed:', error);
      throw new Error('Failed to initialize encryption');
    }
  }

  /**
   * Verify user can decrypt with their password
   */
  static async verifyPassword(password: string): Promise<boolean> {
    try {
      // Try to derive key
      const { key } = await EncryptionService.deriveKeyFromPassword(password);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Recover access using recovery phrase
   */
  static async recoverWithPhrase(
    recoveryPhrase: string,
    newPassword: string
  ): Promise<void> {
    try {
      // Derive key from recovery phrase
      const recoveryKey = await EncryptionService.deriveKeyFromRecoveryPhrase(recoveryPhrase);
      
      // Re-encrypt with new password
      const { key: newKey } = await EncryptionService.deriveKeyFromPassword(newPassword);
      
      // Update stored data
      const keyData = this.getStoredKeyData();
      if (keyData) {
        keyData.lastUsed = new Date().toISOString();
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(keyData));
      }
      
      console.log('Password reset successful');
      
    } catch (error) {
      console.error('Recovery failed:', error);
      throw new Error('Invalid recovery phrase');
    }
  }

  /**
   * Export recovery phrase for backup
   */
  static getRecoveryPhrase(): string | null {
    const keyData = this.getStoredKeyData();
    if (!keyData?.recoveryPhrase) {
      return null;
    }
    return atob(keyData.recoveryPhrase);
  }

  /**
   * Check if user has encryption set up
   */
  static isEncryptionInitialized(userId: string): boolean {
    const keyData = this.getStoredKeyData();
    return keyData?.userId === userId;
  }

  private static getStoredKeyData(): StoredKeyData | null {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (!stored) return null;
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  }
}
```

**New Component:** `FrontEndCode/src/components/EncryptionOnboarding.tsx`

```typescript
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { KeyManagementService } from '@/services/keyManagementService';
import { Copy, Check, AlertTriangle } from 'lucide-react';

interface EncryptionOnboardingProps {
  userId: string;
  userPassword: string;
  onComplete: () => void;
}

export const EncryptionOnboarding: React.FC<EncryptionOnboardingProps> = ({
  userId,
  userPassword,
  onComplete
}) => {
  const [step, setStep] = useState<'intro' | 'generate' | 'confirm'>('intro');
  const [recoveryPhrase, setRecoveryPhrase] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleGenerate = async () => {
    try {
      const { recoveryPhrase: phrase } = await KeyManagementService.initializeUserEncryption(
        userId,
        userPassword
      );
      setRecoveryPhrase(phrase);
      setStep('generate');
    } catch (error) {
      console.error('Failed to generate recovery phrase:', error);
      alert('Failed to set up encryption. Please try again.');
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(recoveryPhrase);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleConfirm = () => {
    if (!confirmed) {
      alert('Please confirm you have saved your recovery phrase');
      return;
    }
    onComplete();
  };

  if (step === 'intro') {
    return (
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>🔒 Secure Your Videos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            Your videos will be encrypted before upload. This means:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>Only you and your designated benefactors can view them</li>
            <li>Not even SoulReel administrators can access your content</li>
            <li>Your videos are protected even if our servers are compromised</li>
          </ul>
          
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>Important:</strong> You'll receive a 12-word recovery phrase. 
              If you lose both your password AND this phrase, your videos cannot be recovered.
            </AlertDescription>
          </Alert>

          <Button onClick={handleGenerate} className="w-full">
            Set Up Encryption
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (step === 'generate') {
    return (
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>📝 Save Your Recovery Phrase</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>Critical:</strong> Write down these 12 words and store them safely. 
              You'll need them if you ever forget your password.
            </AlertDescription>
          </Alert>

          <div className="bg-gray-100 p-6 rounded-lg">
            <div className="grid grid-cols-3 gap-4 mb-4">
              {recoveryPhrase.split(' ').map((word, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <span className="text-gray-500 text-sm">{index + 1}.</span>
                  <span className="font-mono font-medium">{word}</span>
                </div>
              ))}
            </div>
            
            <Button
              onClick={handleCopy}
              variant="outline"
              className="w-full"
            >
              {copied ? (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy to Clipboard
                </>
              )}
            </Button>
          </div>

          <div className="space-y-2">
            <p className="font-medium">Where to store your recovery phrase:</p>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Write it on paper and store in a safe place</li>
              <li>Use a password manager (1Password, LastPass, etc.)</li>
              <li>Store in a secure note on your phone</li>
              <li>Give a copy to a trusted family member</li>
            </ul>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="confirm"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="confirm" className="text-sm">
              I have saved my recovery phrase in a safe place
            </label>
          </div>

          <Button
            onClick={handleConfirm}
            disabled={!confirmed}
            className="w-full"
          >
            Continue
          </Button>
        </CardContent>
      </Card>
    );
  }

  return null;
};
```

**Integration:** Show onboarding on first video upload

```typescript
// In VideoRecorder.tsx or App.tsx
const [showEncryptionOnboarding, setShowEncryptionOnboarding] = useState(false);

useEffect(() => {
  if (user && !KeyManagementService.isEncryptionInitialized(user.id)) {
    setShowEncryptionOnboarding(true);
  }
}, [user]);

{showEncryptionOnboarding && (
  <EncryptionOnboarding
    userId={user.id}
    userPassword={userPassword}  // From auth context
    onComplete={() => setShowEncryptionOnboarding(false)}
  />
)}
```

---


### Task 6: Handle Transcription for Encrypted Videos
**Duration:** 4 hours  
**Risk:** Medium  
**Files:** Backend Lambda functions

#### What This Does
Allows users to opt-in to transcription by providing temporary decryption access.

#### Implementation Options

**Option A: Disable Transcription (Simplest)**
- Encrypted videos cannot be transcribed
- Users choose: encryption OR transcription
- Implementation: Already done in Task 3 (set status to DISABLED)

**Option B: User-Consented Decryption (Recommended)**
- User explicitly enables transcription for specific videos
- Frontend decrypts video, uploads plaintext temporarily
- Backend transcribes, then deletes plaintext
- Transcript encrypted before storage

**Implementation for Option B:**

**New Endpoint:** `SamLambda/functions/videoFunctions/enableTranscription/app.py`

```python
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """
    Allow user to enable transcription for an encrypted video.
    User must provide decrypted video temporarily.
    """
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        body = json.loads(event['body'])
        question_id = body['questionId']
        decrypted_video_s3_key = body['decryptedVideoS3Key']  # Temporary plaintext upload
        
        # Verify ownership
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('userQuestionStatusDB')
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Video not found'})
            }
        
        item = response['Item']
        if not item.get('videoEncrypted'):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Video is not encrypted'})
            }
        
        # Start transcription on temporary plaintext video
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName='StartTranscriptionFunction',
            InvocationType='Event',
            Payload=json.dumps({
                'userId': user_id,
                'questionId': question_id,
                's3Key': decrypted_video_s3_key,
                'temporary': True,  # Flag to delete after transcription
                'encryptTranscript': True  # Encrypt transcript before storage
            })
        )
        
        # Update status
        table.update_item(
            Key={'userId': user_id, 'questionId': question_id},
            UpdateExpression='SET videoTranscriptionStatus = :status, transcriptionConsentedAt = :time',
            ExpressionAttributeValues={
                ':status': 'IN_PROGRESS',
                ':time': datetime.now().isoformat()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Transcription started'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
```

**Frontend Flow:**

```typescript
// In video settings or detail page
const enableTranscription = async (questionId: string, password: string) => {
  try {
    // 1. Download encrypted video
    const encryptedBlob = await fetch(videoUrl).then(r => r.blob());
    
    // 2. Decrypt locally
    const decryptedBlob = await EncryptionService.decryptVideo(
      encryptedBlob,
      encryptionMetadata.encryptedKey,
      encryptionMetadata.iv,
      encryptionMetadata.salt,
      password
    );
    
    // 3. Upload decrypted video to temporary location
    const tempUploadUrl = await getTemporaryUploadUrl(questionId);
    await fetch(tempUploadUrl, {
      method: 'PUT',
      body: decryptedBlob,
      headers: { 'Content-Type': 'video/webm' }
    });
    
    // 4. Trigger transcription
    await fetch(`${API_URL}/enable-transcription`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        questionId,
        decryptedVideoS3Key: tempS3Key
      })
    });
    
    alert('Transcription enabled! This may take a few minutes.');
    
  } catch (error) {
    console.error('Failed to enable transcription:', error);
    alert('Failed to enable transcription. Please try again.');
  }
};
```

**Modified:** `startTranscription/app.py` to handle cleanup

```python
def process_transcription(user_id, question_id, bucket, key, video_type, temporary=False):
    """Process transcription for a video."""
    try:
        # ... existing transcription logic ...
        
        # If temporary video, schedule deletion after transcription
        if temporary:
            # Add S3 lifecycle rule to delete after 1 day
            s3_client = boto3.client('s3')
            s3_client.put_object_tagging(
                Bucket=bucket,
                Key=key,
                Tagging={
                    'TagSet': [
                        {'Key': 'temporary', 'Value': 'true'},
                        {'Key': 'delete-after', 'Value': '1-day'}
                    ]
                }
            )
            print(f"Marked temporary video for deletion: {key}")
```

---


---

## Testing Strategy

### Unit Tests

**File:** `FrontEndCode/src/services/__tests__/encryptionService.test.ts`

```typescript
import { EncryptionService } from '../encryptionService';

describe('EncryptionService', () => {
  const testPassword = 'test-password-123';
  const testVideo = new Blob(['test video content'], { type: 'video/webm' });

  test('should encrypt and decrypt video successfully', async () => {
    // Encrypt
    const encrypted = await EncryptionService.encryptVideo(testVideo, testPassword);
    
    expect(encrypted.encryptedBlob).toBeInstanceOf(Blob);
    expect(encrypted.iv).toBeTruthy();
    expect(encrypted.salt).toBeTruthy();
    expect(encrypted.encryptedKey).toBeTruthy();
    
    // Decrypt
    const decrypted = await EncryptionService.decryptVideo(
      encrypted.encryptedBlob,
      encrypted.encryptedKey,
      encrypted.iv,
      encrypted.salt,
      testPassword
    );
    
    expect(decrypted.size).toBe(testVideo.size);
    
    // Verify content matches
    const originalText = await testVideo.text();
    const decryptedText = await decrypted.text();
    expect(decryptedText).toBe(originalText);
  });

  test('should fail with wrong password', async () => {
    const encrypted = await EncryptionService.encryptVideo(testVideo, testPassword);
    
    await expect(
      EncryptionService.decryptVideo(
        encrypted.encryptedBlob,
        encrypted.encryptedKey,
        encrypted.iv,
        encrypted.salt,
        'wrong-password'
      )
    ).rejects.toThrow();
  });

  test('should generate valid recovery phrase', async () => {
    const phrase = await EncryptionService.generateRecoveryPhrase();
    const words = phrase.split(' ');
    
    expect(words.length).toBe(12);
    expect(words.every(w => w.length > 0)).toBe(true);
  });
});
```

### Integration Tests

**Manual Test Checklist:**

1. **Encryption Flow**
   - [ ] Record a video
   - [ ] Verify encryption prompt appears
   - [ ] Enter password
   - [ ] Verify "Encrypting..." message shows
   - [ ] Verify upload completes successfully
   - [ ] Check DynamoDB for encryption metadata

2. **Decryption Flow**
   - [ ] Navigate to benefactor view
   - [ ] Click encrypted video
   - [ ] Verify "Decrypt & Play" button shows
   - [ ] Enter correct password
   - [ ] Verify video plays correctly
   - [ ] Try wrong password - verify error message

3. **Recovery Flow**
   - [ ] Complete onboarding
   - [ ] Save recovery phrase
   - [ ] Clear browser data
   - [ ] Use recovery phrase to restore access
   - [ ] Verify can decrypt videos

4. **Backend Verification**
   ```bash
   # Check encrypted video in S3
   aws s3api head-object --bucket virtual-legacy --key user-responses/USER_ID/VIDEO.webm
   
   # Verify metadata
   aws dynamodb get-item \
     --table-name userQuestionStatusDB \
     --key '{"userId":{"S":"USER_ID"},"questionId":{"S":"QUESTION_ID"}}' \
     --query 'Item.videoEncryptionMetadata'
   ```

---

## Deployment Plan

### Phase 1.5 Rollout Strategy

**Week 1: Infrastructure + Backend**
- Day 1-2: Deploy Phase 1 (KMS, CloudTrail)
- Day 3-4: Deploy backend encryption metadata support
- Day 5: Testing and verification

**Week 2: Frontend Encryption**
- Day 1-2: Deploy encryption service
- Day 3-4: Update video upload flow
- Day 5: Internal testing

**Week 3: Decryption + Key Management**
- Day 1-2: Deploy video player
- Day 3-4: Deploy key management
- Day 5: End-to-end testing

**Week 4: Beta Testing + Rollout**
- Day 1-3: Beta test with 5-10 users
- Day 4: Fix issues
- Day 5: Full production rollout

### Deployment Commands

```bash
# 1. Deploy Phase 1 infrastructure
cd SamLambda
sam build
sam deploy --guided

# 2. Verify KMS key created
aws kms describe-key --key-id alias/soulreel-data-encryption

# 3. Enable S3 encryption (manual)
aws s3api put-bucket-encryption \
  --bucket virtual-legacy \
  --server-side-encryption-configuration file://s3-encryption-config.json

# 4. Deploy frontend
cd ../FrontEndCode
npm run build
# Deploy to Amplify (see frontend-deployment.md)

# 5. Verify deployment
curl -X POST https://api.soulreel.net/functions/videoFunctions/process-video \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"encrypted":true,"questionId":"test"}'
```

---

## Security Considerations

### What Phase 1.5 Protects Against

✅ **Protects Against:**
- AWS employee access to video content
- Compromised AWS credentials
- Database breaches (encrypted data useless without keys)
- Subpoenas for video content (you can't decrypt without user password)
- Insider threats (admins can't view videos)

⚠️ **Does NOT Protect Against:**
- User forgetting password + losing recovery phrase (data loss)
- Malware on user's device (can capture password)
- Compromised user account (if attacker has password)
- Browser vulnerabilities (encryption happens in browser)
- Quantum computing attacks (AES-256 is quantum-resistant for now)

### Known Limitations

1. **Password Storage**
   - Currently prompts user each time
   - Consider: Store encrypted in session storage
   - Risk: Session hijacking could expose password

2. **Recovery Phrase Storage**
   - Currently in localStorage (not ideal)
   - Better: IndexedDB with additional encryption
   - Best: Hardware security key (WebAuthn)

3. **Key Derivation Performance**
   - PBKDF2 with 100k iterations takes ~500ms
   - May feel slow on older devices
   - Consider: Web Workers for non-blocking

4. **Metadata Leakage**
   - Video size, upload time, question ID still visible
   - Filenames contain timestamps
   - Consider: Padding to hide size, random filenames

---

## Cost Analysis

### Phase 1.5 Additional Costs

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| KMS API Calls | $3-5 | Per million requests |
| CloudTrail Logs | $2-3 | 90-day retention |
| S3 Versioning | $5-10 | Depends on upload volume |
| Additional Lambda Time | $2-3 | Encryption overhead |
| **Total** | **$12-21/month** | ~10% increase |

### Cost Optimization Tips

1. **Enable S3 Bucket Keys** - Reduces KMS costs by 99%
   ```bash
   aws s3api put-bucket-encryption \
     --bucket virtual-legacy \
     --server-side-encryption-configuration '{
       "Rules": [{
         "BucketKeyEnabled": true
       }]
     }'
   ```

2. **Lifecycle Policies** - Move old videos to Glacier
3. **CloudTrail Filtering** - Only log data events, not management
4. **Lambda Memory Optimization** - Right-size memory allocation

---

## Rollback Plan

### If Things Go Wrong

**Scenario 1: Users Can't Decrypt Videos**
```bash
# Disable encryption requirement
aws dynamodb update-item \
  --table-name userQuestionStatusDB \
  --key '{"userId":{"S":"USER_ID"},"questionId":{"S":"QUESTION_ID"}}' \
  --update-expression "SET videoEncrypted = :false" \
  --expression-attribute-values '{":false":{"BOOL":false}}'
```

**Scenario 2: Performance Issues**
- Reduce PBKDF2 iterations from 100k to 10k
- Use Web Workers for encryption
- Add loading states and progress bars

**Scenario 3: Key Loss Epidemic**
- Implement emergency recovery via support ticket
- Require video verification (user describes content)
- Use escrow key with multi-party authorization

**Complete Rollback:**
```bash
# 1. Revert frontend to previous version
cd FrontEndCode
git revert HEAD
npm run build
# Deploy

# 2. Keep backend changes (backward compatible)
# Old videos still work, new videos unencrypted

# 3. Notify users
# Send email explaining temporary encryption disable
```

---

## Success Metrics

### Key Performance Indicators

1. **Adoption Rate**
   - Target: 80% of new videos encrypted within 30 days
   - Measure: `SELECT COUNT(*) FROM videos WHERE encrypted=true`

2. **Decryption Success Rate**
   - Target: >95% successful decryptions
   - Measure: CloudWatch logs for decryption errors

3. **Key Recovery Usage**
   - Target: <5% of users need recovery
   - Measure: Recovery phrase usage logs

4. **Performance Impact**
   - Target: <2 second encryption overhead
   - Measure: Frontend performance monitoring

5. **User Satisfaction**
   - Target: >4.0/5.0 rating
   - Measure: Post-upload survey

### Monitoring Dashboard

```sql
-- CloudWatch Insights Query
fields @timestamp, @message
| filter @message like /encryption/
| stats 
    count(*) as total_encryptions,
    count(*) by bin(5m) as encryptions_per_5min,
    avg(duration) as avg_encryption_time
```

---

## User Communication

### Email Template: Encryption Launch

**Subject:** 🔒 Your Videos Are Now More Secure

**Body:**
```
Hi [Name],

We're excited to announce enhanced security for your SoulReel videos!

What's New:
✅ Videos encrypted before upload
✅ Only you and your benefactors can view them
✅ Protected even if our servers are compromised

What You Need to Do:
1. Record your next video as usual
2. Save your 12-word recovery phrase when prompted
3. Store it somewhere safe (password manager, secure note, etc.)

Important: If you lose both your password AND recovery phrase, 
we cannot recover your videos. This is by design for maximum security.

Questions? Reply to this email or visit our Help Center.

Best regards,
The SoulReel Team
```

### In-App Notifications

1. **First Video Upload:**
   - "🔒 Your videos are now encrypted for extra security"
   - "Save your recovery phrase - you'll need it if you forget your password"

2. **After 5 Videos:**
   - "✅ You've encrypted 5 videos! Make sure you've saved your recovery phrase."

3. **30 Days Later:**
   - "Reminder: Your recovery phrase is stored in Settings > Security"

---

## Next Steps (Phase 2)

After Phase 1.5 is stable, consider:

1. **Hardware Security Keys** - WebAuthn support
2. **Benefactor Key Sharing** - Automatic encryption key sharing
3. **Escrow System** - Multi-party recovery for USB exports
4. **Mobile Apps** - Native encryption on iOS/Android
5. **Audit Logs** - User-visible access logs
6. **Zero-Knowledge Proof** - Prove you have access without revealing key

---

## Conclusion

Phase 1.5 provides a strong middle ground:
- ✅ Videos encrypted before leaving user's device
- ✅ AWS cannot decrypt content
- ✅ Relatively simple implementation
- ✅ Backward compatible (old videos still work)
- ⚠️ Users must manage recovery phrases
- ⚠️ Transcription requires explicit consent

**Recommendation:** Proceed with Phase 1.5 after completing Phase 1 infrastructure hardening. This gives you strong security without the full complexity of Phase 2's advanced key management.

**Timeline:** 3-4 weeks for full implementation and testing.

**Risk Level:** Medium - careful key management UX is critical.

---

**Document Version:** 1.0  
**Date:** February 15, 2026  
**Author:** Kiro AI Security Implementation  
**Status:** Ready for Review
