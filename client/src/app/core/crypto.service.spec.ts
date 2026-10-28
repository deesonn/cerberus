import { TestBed } from '@angular/core/testing';
import { CryptoService, WrongPasswordError } from './crypto.service';

const enc = (s: string) => new TextEncoder().encode(s);
const bytesOf = (b: ArrayBuffer) => new Uint8Array(b);
// Copy into a fresh ArrayBuffer so TypeScript is happy about the buffer type.
const toBuf = (u: Uint8Array): ArrayBuffer => u.slice().buffer as ArrayBuffer;

describe('CryptoService', () => {
  let svc: CryptoService;
  const SECRET = 'Account number 000-111-222. Do not share.';

  beforeEach(() => {
    TestBed.configureTestingModule({});
    svc = TestBed.inject(CryptoService);
  });

  it('round-trips text with the right password', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'pw-one');
    const plain = await svc.decrypt(toBuf(blob), 'pw-one');
    expect(new TextDecoder().decode(plain)).toBe(SECRET);
  });

  it('round-trips binary data containing every byte value', async () => {
    const all = new Uint8Array(256).map((_, i) => i);
    const blob = await svc.encrypt(toBuf(all), 'pw-bin');
    expect(bytesOf(await svc.decrypt(toBuf(blob), 'pw-bin'))).toEqual(all);
  });

  it('round-trips an empty file', async () => {
    const blob = await svc.encrypt(new ArrayBuffer(0), 'pw-empty');
    expect((await svc.decrypt(toBuf(blob), 'pw-empty')).byteLength).toBe(0);
  });

  it('accepts a password with unicode characters', async () => {
    const pw = 'pässwörd-日本語-🔐';
    const blob = await svc.encrypt(toBuf(enc(SECRET)), pw);
    expect(new TextDecoder().decode(await svc.decrypt(toBuf(blob), pw))).toBe(SECRET);
  });

  it('starts every blob with the CRB1 header', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    expect(new TextDecoder().decode(blob.slice(0, 4))).toBe('CRB1');
  });

  it('does not leave the plaintext visible in the encrypted bytes', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    const asLatin1 = Array.from(blob, (b) => String.fromCharCode(b)).join('');
    expect(asLatin1.includes('000-111-222')).toBeFalse();
    expect(asLatin1.includes('Account number')).toBeFalse();
  });

  it('fails with WrongPasswordError for the wrong password', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'right');
    await expectAsync(svc.decrypt(toBuf(blob), 'wrong')).toBeRejectedWithError(WrongPasswordError);
  });

  it('fails if a single ciphertext byte is changed (tamper detection)', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    blob[blob.length - 5] ^= 0x01;
    await expectAsync(svc.decrypt(toBuf(blob), 'pw')).toBeRejectedWithError(WrongPasswordError);
  });

  it('fails if the salt is changed', async () => {
    const blob = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    blob[6] ^= 0xff;
    await expectAsync(svc.decrypt(toBuf(blob), 'pw')).toBeRejectedWithError(WrongPasswordError);
  });

  it('rejects data that is too short to be a Cerberus file', async () => {
    await expectAsync(svc.decrypt(toBuf(enc('CRB1')), 'pw')).toBeRejectedWithError(WrongPasswordError);
  });

  it('rejects data that does not start with the CRB1 header', async () => {
    const junk = new Uint8Array(200).fill(7);
    await expectAsync(svc.decrypt(toBuf(junk), 'pw')).toBeRejectedWithError(WrongPasswordError);
  });

  it('produces a different blob each time for the same file and password (fresh salt + IV)', async () => {
    const a = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    const b = await svc.encrypt(toBuf(enc(SECRET)), 'pw');
    expect(a).not.toEqual(b);
    expect(a.slice(4, 20)).not.toEqual(b.slice(4, 20)); // salts differ
    expect(a.slice(20, 32)).not.toEqual(b.slice(20, 32)); // IVs differ
  });
});
