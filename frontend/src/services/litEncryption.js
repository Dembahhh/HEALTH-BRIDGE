/**
 * litEncryption.js
 * Lit Protocol singleton — client init, ephemeral wallet, session sigs,
 * encrypt/decrypt helpers.
 *
 * Requires Lit SDK v6.x — pinned via package.json.
 *
 * Design decisions (per spec):
 * - One LitNodeClient instance shared across the app (singleton)
 * - Each user gets an ephemeral Ethereum wallet derived from
 *   ethers.Wallet.createRandom(), persisted in localStorage
 * - No MetaMask required — works for Firebase Google/email users
 * - Session sigs cached for 23 hours
 * - Encrypted blobs prefixed with __lit_enc__: for detection
 */

import { LitNodeClient } from '@lit-protocol/lit-node-client';
import { LitNetwork } from '@lit-protocol/constants';
import {
  createSiweMessageWithRecaps,
  generateAuthSig,
  LitAbility,
  LitAccessControlConditionResource,
} from '@lit-protocol/auth-helpers';
import { encryptString, decryptToString } from '@lit-protocol/encryption';
import { ethers } from 'ethers';

// ── Constants ────────────────────────────────────────────────────────────────
const LIT_PREFIX = '__lit_enc__:';
const WALLET_KEY = (uid) => `hb_lit_wallet_${uid}`;
const SESSION_KEY = (uid) => `hb_lit_session_${uid}`;
const SESSION_TTL_MS = 23 * 60 * 60 * 1000; // 23 hours

// ── Singleton client ─────────────────────────────────────────────────────────
let _litClient = null;

/**
 * Connect to Lit DatilDev testnet (call once on app init).
 * Safe to call multiple times — returns existing client if already connected.
 */
export async function initLitClient() {
  if (_litClient) return _litClient;
  _litClient = new LitNodeClient({
    litNetwork: LitNetwork.DatilDev,
    debug: false,
  });
  await _litClient.connect();
  return _litClient;
}

// ── Ephemeral wallet ──────────────────────────────────────────────────────────
/**
 * Get or create an ephemeral wallet for a given Firebase UID.
 * Wallet private key is stored in localStorage — same wallet restored on
 * re-login so old encrypted data can still be decrypted.
 */
function getOrCreateWallet(uid) {
  const key = WALLET_KEY(uid);
  const stored = localStorage.getItem(key);
  if (stored) {
    return new ethers.Wallet(stored);
  }
  const wallet = ethers.Wallet.createRandom();
  localStorage.setItem(key, wallet.privateKey);
  return wallet;
}

// ── Session signatures ────────────────────────────────────────────────────────
/**
 * Get cached session sigs or generate fresh ones.
 * Session sigs authorise Lit nodes to serve decryption keys.
 * Cached for 23 hours under hb_lit_session_<uid>.
 */
export async function generateSessionSigs(uid) {
  // Return cached session if still valid
  const cached = localStorage.getItem(SESSION_KEY(uid));
  if (cached) {
    try {
      const { sigs, expiresAt } = JSON.parse(cached);
      if (Date.now() < expiresAt) return sigs;
    } catch {
      // Corrupted cache — regenerate
    }
  }

  const client = await initLitClient();
  const wallet = getOrCreateWallet(uid);

  const sessionSigs = await client.getSessionSigs({
    chain: 'ethereum',
    expiration: new Date(Date.now() + SESSION_TTL_MS).toISOString(),
    resourceAbilityRequests: [
      {
        resource: new LitAccessControlConditionResource('*'),
        ability: LitAbility.AccessControlConditionDecryption,
      },
    ],
    authNeededCallback: async ({ uri, expiration, resourceAbilityRequests }) => {
      const toSign = await createSiweMessageWithRecaps({
        uri,
        expiration,
        resources: resourceAbilityRequests,
        walletAddress: wallet.address,
        nonce: await client.getLatestBlockhash(),
        litNodeClient: client,
      });
      return generateAuthSig({
        signer: wallet,
        toSign,
      });
    },
  });

  // Cache session sigs
  localStorage.setItem(
    SESSION_KEY(uid),
    JSON.stringify({ sigs: sessionSigs, expiresAt: Date.now() + SESSION_TTL_MS })
  );

  return sessionSigs;
}

// ── Access control conditions ─────────────────────────────────────────────────
/**
 * Access control: only the user's own wallet address can decrypt.
 * This is a client-side constraint — the wallet is deterministic per uid.
 */
function buildAccessControlConditions(walletAddress) {
  return [
    {
      contractAddress: '',
      standardContractType: '',
      chain: 'ethereum',
      method: '',
      parameters: [':userAddress'],
      returnValueTest: {
        comparator: '=',
        value: walletAddress,
      },
    },
  ];
}

// ── Encrypt ───────────────────────────────────────────────────────────────────
/**
 * Encrypt a plaintext string for a given user.
 * Returns a prefixed base64 blob: "__lit_enc__:<base64json>"
 */
export async function encryptField(uid, plaintext) {
  if (!plaintext) return plaintext;
  const client = await initLitClient();
  const wallet = getOrCreateWallet(uid);
  const accessControlConditions = buildAccessControlConditions(wallet.address);

  const { ciphertext, dataToEncryptHash } = await encryptString(
    {
      accessControlConditions,
      dataToEncrypt: plaintext,
    },
    client
  );

  const blob = JSON.stringify({
    ciphertext,
    dataToEncryptHash,
    walletAddress: wallet.address,
  });
  return `${LIT_PREFIX}${btoa(blob)}`;
}

// ── Decrypt ───────────────────────────────────────────────────────────────────
/**
 * Decrypt a __lit_enc__: prefixed blob for a given user.
 * Returns plaintext string.
 */
export async function decryptField(uid, cipherblob) {
  if (!isEncrypted(cipherblob)) return cipherblob;
  const client = await initLitClient();
  const sessionSigs = await generateSessionSigs(uid);

  const raw = cipherblob.slice(LIT_PREFIX.length);
  const { ciphertext, dataToEncryptHash, walletAddress } = JSON.parse(atob(raw));
  const accessControlConditions = buildAccessControlConditions(walletAddress);

  const plaintext = await decryptToString(
    {
      accessControlConditions,
      ciphertext,
      dataToEncryptHash,
      sessionSigs,
      chain: 'ethereum',
    },
    client
  );

  return plaintext;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
/** Returns true if the value is a Lit-encrypted blob. */
export function isEncrypted(value) {
  return typeof value === 'string' && value.startsWith(LIT_PREFIX);
}

/** Call on logout — removes wallet and session from localStorage. */
export function clearLitSession(uid) {
  if (!uid) return;
  localStorage.removeItem(WALLET_KEY(uid));
  localStorage.removeItem(SESSION_KEY(uid));
}