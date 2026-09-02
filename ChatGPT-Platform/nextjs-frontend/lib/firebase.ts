import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  UserCredential,
} from 'firebase/auth';

const envApiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY || '';
export const isFirebaseConfigured = !!(
  envApiKey &&
  envApiKey.length > 10 &&
  !envApiKey.includes('DemoDummy')
);

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: envApiKey || 'AIzaSyDemoDummyApiKeyForFirebaseAuth2026',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'chatgpt-platform-local.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'chatgpt-platform-local',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'chatgpt-platform-local.appspot.com',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '123456789012',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:123456789012:web:abcdef123456',
};

// Initialize Firebase App singleton
const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);

// Initialize Firebase Auth
export const auth = getAuth(app);

// Configure Google Auth Provider with account picker prompt
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account',
});
googleProvider.addScope('email');
googleProvider.addScope('profile');

export interface GoogleAuthResult {
  credential: string; // Firebase ID Token
  firebase_uid: string;
  email: string;
  name: string;
  avatar_url: string;
}

/**
 * Triggers Google popup sign-in via Firebase Auth.
 * Always prompts the user to select from their available Google accounts.
 */
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
    // Map Firebase auth errors to readable messages
    if (err.code === 'auth/popup-closed-by-user') {
      const error = new Error('Sign-in cancelled. The Google sign-in window was closed.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/cancelled-popup-request') {
      const error = new Error('Sign-in request was cancelled.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/popup-blocked') {
      const error = new Error('Popup blocked by your browser. Please allow popups for this site and try again.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/network-request-failed') {
      const error = new Error('Network error during Google sign-in. Please check your internet connection.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/unauthorized-domain') {
      const error = new Error('This domain is not authorized for OAuth operations in Firebase Console.');
      (error as any).code = err.code;
      throw error;
    }
    if (err.code === 'auth/invalid-api-key' || err.code === 'auth/api-key-not-valid') {
      const error = new Error('Invalid Firebase API key. Please check your .env.local configuration.');
      (error as any).code = err.code;
      throw error;
    }
    throw err;
  }
}

/**
 * Signs out from Firebase Authentication.
 */
export async function signOutFirebase(): Promise<void> {
  try {
    await signOut(auth);
  } catch (err) {
    console.warn('Firebase signOut warning:', err);
  }
}
