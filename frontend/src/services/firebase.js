// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// Import Authentication
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCfT3Ln7GM5koSGQKCujtSI7NxfVeOIVbE",
  authDomain: "health-bridge-one.firebaseapp.com",
  projectId: "health-bridge-one",
  storageBucket: "health-bridge-one.firebasestorage.app",
  messagingSenderId: "1001053560281",
  appId: "1:1001053560281:web:a2c00710c54b9e74060dc8",
  measurementId: "G-0VNHDWDR4K"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

// Initialize Firebase Authentication and export it
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();