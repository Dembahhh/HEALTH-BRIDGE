/**
 * useLitDecryptedMessages.js
 * Batch async decrypt hook for message arrays in ChatPage.
 *
 * Usage:
 *   const decryptedMessages = useLitDecryptedMessages(messages, uid);
 *
 * - Runs decryptField on every message where isEncrypted(content) is true
 * - Returns a decrypted copy of the messages array
 * - Safe to call before Lit is ready — returns original array until ready
 * - Re-runs whenever messages array or uid changes
 */

import { useState, useEffect } from 'react';
import { isEncrypted, decryptField } from '../services/litEncryption';

export default function useLitDecryptedMessages(messages, uid) {
  const [decryptedMessages, setDecryptedMessages] = useState(messages);

  useEffect(() => {
    if (!uid || !messages?.length) {
      setDecryptedMessages(messages);
      return;
    }

    let cancelled = false;

    async function decryptAll() {
      const results = await Promise.all(
        messages.map(async (msg) => {
          if (!isEncrypted(msg.content)) return msg;
          try {
            const plaintext = await decryptField(uid, msg.content);
            return { ...msg, content: plaintext };
          } catch {
            return msg; // fail open — show raw blob rather than crash
          }
        })
      );

      if (!cancelled) setDecryptedMessages(results);
    }

    decryptAll();

    return () => {
      cancelled = true;
    };
  }, [messages, uid]);

  return decryptedMessages;
}