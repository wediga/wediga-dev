import { createHmac } from "node:crypto";

// Time-based one-time codes (RFC 6238) as authenticator apps compute them,
// with authentik's settings: SHA-1, 30-second steps, six digits.
const STEP_SECONDS = 30;
const DIGITS = 6;
const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const BITS_PER_BASE32_CHAR = 5;
const BITS_PER_BYTE = 8;
const COUNTER_BYTES = 8;
const MS_PER_SECOND = 1000;
// RFC 4226 dynamic truncation: the low four bits of the last byte pick the
// offset, and the top bit of the four bytes read there is dropped.
const OFFSET_MASK = 0x0f;
const DROP_SIGN_BIT = 0x7fffffff;

function base32Decode(secret: string): Buffer {
  let bits = "";

  for (const char of secret.replace(/=+$/, "").toUpperCase()) {
    const value = BASE32_ALPHABET.indexOf(char);

    if (value === -1) {
      throw new Error(`invalid base32 character "${char}"`);
    }

    bits += value.toString(2).padStart(BITS_PER_BASE32_CHAR, "0");
  }

  const bytes = bits.match(new RegExp(`.{${BITS_PER_BYTE}}`, "g")) ?? [];

  return Buffer.from(bytes.map((byte) => parseInt(byte, 2)));
}

export function totpCode(secret: string): string {
  const counter = Buffer.alloc(COUNTER_BYTES);
  const step = Math.floor(Date.now() / MS_PER_SECOND / STEP_SECONDS);
  counter.writeBigUInt64BE(BigInt(step));
  const hmac = createHmac("sha1", base32Decode(secret)).update(counter).digest();
  const offset = hmac[hmac.length - 1] & OFFSET_MASK;
  const code = (hmac.readUInt32BE(offset) & DROP_SIGN_BIT) % 10 ** DIGITS;

  return code.toString().padStart(DIGITS, "0");
}
