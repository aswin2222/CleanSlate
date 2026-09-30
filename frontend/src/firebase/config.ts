import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import {
  getFirestore,
  collection,
  addDoc,
  getDocs,
  query,
  orderBy,
  limit,
  serverTimestamp,
  doc,
  setDoc,
} from 'firebase/firestore';

export const firebaseConfig = {
  apiKey: 'AIzaSyAWWv4W26C4mNeiKfzbMy8jMhsYi-pjKA0',
  authDomain: 'titan-d57bf.firebaseapp.com',
  projectId: 'titan-d57bf',
  storageBucket: 'titan-d57bf.firebasestorage.app',
  messagingSenderId: '894280304839',
  appId: '1:894280304839:web:9077b536a5f835a66596e2',
  measurementId: 'G-W4ME6V6VGR',
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

export interface FirestoreDataset {
  id: string;
  filename: string;
  rows: number;
  cols: number;
  format: string;
  canonical_hash: string;
  cloudinary_url?: string;
  created_at: string;
}

export interface FirestoreAuditLog {
  actor: string;
  event: string;
  dataset_id?: string;
  details?: any;
  timestamp: string;
}

/** Sync dataset metadata to Firestore */
export async function syncDatasetToFirestore(dataset: FirestoreDataset): Promise<void> {
  try {
    const datasetRef = doc(db, 'datasets', dataset.id);
    await setDoc(datasetRef, {
      ...dataset,
      updated_at: serverTimestamp(),
    }, { merge: true });
  } catch (err) {
    console.warn('Firestore syncDataset warning:', err);
  }
}

/** Record audit log in Firestore */
export async function logAuditToFirestore(log: FirestoreAuditLog): Promise<void> {
  try {
    await addDoc(collection(db, 'audit_logs'), {
      ...log,
      created_at: serverTimestamp(),
    });
  } catch (err) {
    console.warn('Firestore logAudit warning:', err);
  }
}

/** Retrieve live audit logs from Firestore */
export async function getFirestoreAuditLogs(maxLogs: number = 50): Promise<FirestoreAuditLog[]> {
  try {
    const q = query(collection(db, 'audit_logs'), orderBy('created_at', 'desc'), limit(maxLogs));
    const snapshot = await getDocs(q);
    return snapshot.docs.map((docSnap) => {
      const data = docSnap.data();
      return {
        actor: data.actor || 'system',
        event: data.event || 'UNKNOWN',
        dataset_id: data.dataset_id,
        details: data.details,
        timestamp: data.created_at?.toDate ? data.created_at.toDate().toISOString() : new Date().toISOString(),
      };
    });
  } catch (err) {
    console.warn('Firestore getAuditLogs warning:', err);
    return [];
  }
}
