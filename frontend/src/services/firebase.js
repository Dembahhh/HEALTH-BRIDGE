// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// Import Authentication
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Check if configuration is valid and not placeholders
const hasConfig = !!firebaseConfig.apiKey &&
  firebaseConfig.apiKey !== "your-api-key" &&
  firebaseConfig.apiKey !== "";

let app;
let auth;
let googleProvider;
let analytics = null;

if (hasConfig) {
  try {
    app = initializeApp(firebaseConfig);
    if (typeof window !== 'undefined' && firebaseConfig.measurementId) {
      analytics = getAnalytics(app);
    }
    auth = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    console.log("Firebase initialized successfully");
  } catch (error) {
    console.error("Firebase initialization failed:", error);
  }
} else {
  console.warn("Firebase credentials missing or using placeholders. App may not function correctly. Please update frontend/.env");
  // Mock auth objects to prevent application crash
  auth = {
    onAuthStateChanged: (callback) => {
      // Simulate "no user" state so app can finish loading
      setTimeout(() => callback(null), 100);
      return () => { };
    }
  };
  googleProvider = {};
}

export { auth, googleProvider, hasConfig };
