import { initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth, GoogleAuthProvider } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";

const isDev = import.meta.env.DEV;

// In dev we allow placeholder values because we connect to emulators.
// In prod we REQUIRE real Firebase config to be provided at build time.
const firebaseConfig = isDev
  ? {
      apiKey: "demo-key",
      authDomain: "demo-monobank.firebaseapp.com",
      projectId: "demo-monobank",
      storageBucket: "demo-monobank.appspot.com",
      messagingSenderId: "demo-sender",
      appId: "demo-app",
    }
  : {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    };

if (!isDev) {
  const missing = Object.entries(firebaseConfig)
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (missing.length) {
    // Fail loudly so prod never silently falls back to emulator/demo config.
    throw new Error(
      `Missing Firebase config (${missing.join(
        ", "
      )}). Ensure deploy embeds VITE_FIREBASE_* env vars at build time.`
    );
  }
}

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

// Connect to emulators if running locally
if (isDev) {
  connectAuthEmulator(auth, "http://127.0.0.1:9099");
  connectFirestoreEmulator(db, "localhost", 8080);
}

export { auth, db, googleProvider };

