import { initializeApp } from "firebase/app";
import { getAuth, connectAuthEmulator, GoogleAuthProvider } from "firebase/auth";
import { getFirestore, connectFirestoreEmulator } from "firebase/firestore";

const firebaseConfig = {
  // These are demo values for local development with emulators
  apiKey: "demo-key",
  authDomain: "demo-monobank.firebaseapp.com",
  projectId: "demo-monobank",
  storageBucket: "demo-monobank.appspot.com",
  messagingSenderId: "demo-sender",
  appId: "demo-app"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

// Connect to emulators if running locally
if (import.meta.env.DEV) {
  connectAuthEmulator(auth, "http://127.0.0.1:9099");
  connectFirestoreEmulator(db, "localhost", 8080);
}

export { auth, db, googleProvider };

