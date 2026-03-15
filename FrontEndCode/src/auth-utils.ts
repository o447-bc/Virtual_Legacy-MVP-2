import CryptoJS from 'crypto-js';

export const calculateSecretHash = (username: string, clientId: string, clientSecret: string): string => {
  return CryptoJS.HmacSHA256(username + clientId, clientSecret).toString(CryptoJS.enc.Base64);
};