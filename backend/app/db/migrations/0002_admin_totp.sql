-- Admin second factor (TOTP): add the encrypted secret and the enabled flag to
-- the single admin row. The secret is stored as Fernet ciphertext and stays
-- empty until the admin completes setup; totp_enabled gates the login step.

ALTER TABLE admin ADD COLUMN totp_secret TEXT;

ALTER TABLE admin ADD COLUMN totp_enabled INTEGER NOT NULL DEFAULT 0;
