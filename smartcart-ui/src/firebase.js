// src/firebase.js
// Firebase app initialization and auth exports for SmartCart AI.
// All config values are pulled from environment variables — never hard-code them.
// For Create React App: prefix with REACT_APP_
// For Vite:            prefix with VITE_ (and use import.meta.env.VITE_* below)

import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey:            process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain:        process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId:         process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket:     process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId:             process.env.REACT_APP_FIREBASE_APP_ID,
};

const missingConfig = Object.entries(firebaseConfig)
  .filter(([, value]) => !value)
  .map(([key]) => key);

if (missingConfig.length > 0) {
  throw new Error(
    `Missing Firebase environment variables: ${missingConfig.join(", ")}. ` +
      "Add them to .env or a supported CRA env file and restart the dev server."
  );
}

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();

// Optional: force account picker on every sign-in (useful during dev/testing)
// provider.setCustomParameters({ prompt: "select_account" });
