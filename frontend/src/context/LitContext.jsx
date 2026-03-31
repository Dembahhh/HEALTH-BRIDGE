/**
 * LitContext.jsx
 * React context provider for Lit Protocol encryption.
 * Wraps the entire app — initialises Lit on login, clears on logout.
 *
 * Exports:
 *   <LitProvider>       — wrap around <Router> in App.jsx
 *   useLitEncryption()  — returns { encryptField, decryptField, litReady, litError }
 */
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import {
  initLitClient,
  generateSessionSigs,
  encryptField as litEncrypt,
  decryptField as litDecrypt,
  clearLitSession,
} from '../services/litEncryption';

// ── Context ───────────────────────────────────────────────────────────────────
const LitContext = createContext({
  encryptField: async (plaintext) => plaintext,
  decryptField: async (ciphertext) => ciphertext,
  litReady: false,
  litError: null,
});

// ── Provider ──────────────────────────────────────────────────────────────────
export function LitProvider({ children }) {
  const [litReady, setLitReady] = useState(false);
  const [litError, setLitError] = useState(null);

  // Read uid from Redux auth state — adjust selector to match your authSlice shape
  const uid = useSelector((state) => state.auth?.user?.uid ?? null);

  useEffect(() => {
    if (!uid) {
      // User logged out — reset state
      setLitReady(false);
      setLitError(null);
      return;
    }

    let cancelled = false;

    async function initLit() {
      try {
        setLitReady(false);
        setLitError(null);
        await initLitClient();
        await generateSessionSigs(uid);
        if (!cancelled) setLitReady(true);
      } catch (err) {
        console.warn('[Lit] Init failed:', err);
        if (!cancelled) setLitError(err.message ?? 'Lit init failed');
      }
    }

    initLit();

    return () => {
      cancelled = true;
    };
  }, [uid]);

  // ── Bound helpers ─────────────────────────────────────────────────────────
  const encryptField = useCallback(
    async (plaintext) => {
      if (!litReady || !uid) return plaintext;
      try {
        return await litEncrypt(uid, plaintext);
      } catch (err) {
        console.warn('[Lit] Encrypt failed:', err);
        return plaintext; // fail open — store plaintext rather than crash
      }
    },
    [litReady, uid]
  );

  const decryptField = useCallback(
    async (ciphertext) => {
      if (!uid) return ciphertext;
      try {
        return await litDecrypt(uid, ciphertext);
      } catch (err) {
        console.warn('[Lit] Decrypt failed:', err);
        return ciphertext; // fail open — show raw blob rather than crash
      }
    },
    [uid]
  );

  return (
    <LitContext.Provider value={{ encryptField, decryptField, litReady, litError }}>
      {children}
    </LitContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useLitEncryption() {
  return useContext(LitContext);
}