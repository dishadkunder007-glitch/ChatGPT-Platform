import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  UserCredential,
} from 'firebase/auth';

const env = (import.meta as any).env || {};
const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY || 'AIzaSyANbpnyWD3U6EfckyuEF0z6Xs8WDG1Pr04',
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || 'chatgpt-platform-c65c6.firebaseapp.com',
  projectId: env.VITE_FIREBASE_PROJECT_ID || 'chatgpt-platform-c65c6',
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET || 'chatgpt-platform-c65c6.firebasestorage.app',
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID || '234064504966',
  appId: env.VITE_FIREBASE_APP_ID || '1:234064504966:web:9b29011440f0b7696f4907',
};

const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account',
});
googleProvider.addScope('email');
googleProvider.addScope('profile');

export interface GoogleAuthResult {
  credential: string;
  firebase_uid: string;
  email: string;
  name: string;
  avatar_url: string;
}

export async function signInWithGooglePopup(): Promise<GoogleAuthResult> {
  try {
    const result: UserCredential = await signInWithPopup(auth, googleProvider);
    const user = result.user;
    const idToken = await user.getIdToken();

    return {
      credential: idToken,
      firebase_uid: user.uid,
      email: user.email || '',
      name: user.displayName || user.email?.split('@')[0] || 'Google User',
      avatar_url: user.photoURL || '',
    };
  } catch (err: any) {
    if (err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
      const error = new Error('Sign-in cancelled. The Google sign-in window was closed.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/popup-blocked') {
      const error = new Error('Popup blocked by your browser. Please allow popups for this site and try again.');
      (error as any).code = err.code;
      throw error;
    }
    throw err;
  }
}
