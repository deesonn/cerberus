import { Injectable } from '@angular/core';

// Blob layout: "CRB1" (4 bytes) | salt (16) | iv (12) | AES-GCM ciphertext+tag
const MAGIC = new Uint8Array([0x43, 0x52, 0x42, 0x31]);
const PBKDF2_ITERATIONS = 310_000;

export class WrongPasswordError extends Error {
  constructor() {
    super('Incorrect password, or this file is corrupted.');
  }
}

@Injectable({ providedIn: 'root' })
export class CryptoService {
  private async deriveKey(password: string, salt: Uint8Array): Promise<CryptoKey> {
    const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, [
      'deriveKey',
    ]);
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
      material,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt'],
    );
  }

  async encrypt(plain: ArrayBuffer, password: string): Promise<Uint8Array> {
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await this.deriveKey(password, salt);
    const cipher = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, plain));
    const out = new Uint8Array(MAGIC.length + salt.length + iv.length + cipher.length);
    out.set(MAGIC, 0);
    out.set(salt, MAGIC.length);
    out.set(iv, MAGIC.length + salt.length);
    out.set(cipher, MAGIC.length + salt.length + iv.length);
    return out;
  }

  async decrypt(blob: ArrayBuffer, password: string): Promise<ArrayBuffer> {
    const bytes = new Uint8Array(blob);
    const headerLen = MAGIC.length + 16 + 12;
    if (bytes.length <= headerLen || !MAGIC.every((b, i) => bytes[i] === b)) {
      throw new WrongPasswordError();
    }
    const salt = bytes.slice(MAGIC.length, MAGIC.length + 16);
    const iv = bytes.slice(MAGIC.length + 16, headerLen);
    const key = await this.deriveKey(password, salt);
    try {
      // AES-GCM authenticates, so a wrong password fails loudly instead of returning garbage.
      return await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, bytes.slice(headerLen));
    } catch {
      throw new WrongPasswordError();
    }
  }
}
