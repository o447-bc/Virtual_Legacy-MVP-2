import { uploadData, downloadData, list, remove } from 'aws-amplify/storage';
import { getCurrentUser } from 'aws-amplify/auth';

export class S3Service {
  private static async getUserPrefix(): Promise<string> {
    const user = await getCurrentUser();
    return `users/${user.userId}/`;
  }

  static async uploadFile(file: File, fileName: string): Promise<string> {
    const prefix = await this.getUserPrefix();
    const key = `${prefix}${fileName}`;
    
    const result = await uploadData({
      key,
      data: file,
      options: {
        accessLevel: 'private'
      }
    }).result;
    
    return result.key;
  }

  static async downloadFile(fileName: string): Promise<Blob> {
    const prefix = await this.getUserPrefix();
    const key = `${prefix}${fileName}`;
    
    const result = await downloadData({
      key,
      options: {
        accessLevel: 'private'
      }
    }).result;
    
    return result.body as Blob;
  }

  static async listUserFiles(): Promise<string[]> {
    const prefix = await this.getUserPrefix();
    
    const result = await list({
      prefix,
      options: {
        accessLevel: 'private'
      }
    });
    
    return result.items.map(item => item.key?.replace(prefix, '') || '');
  }

  static async deleteFile(fileName: string): Promise<void> {
    const prefix = await this.getUserPrefix();
    const key = `${prefix}${fileName}`;
    
    await remove({
      key,
      options: {
        accessLevel: 'private'
      }
    });
  }
}