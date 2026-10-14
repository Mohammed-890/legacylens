import { cpSync, mkdirSync } from 'node:fs';

// The hosted showcase contains static assets only; the Python API runs locally.
mkdirSync('dist', { recursive: true });
cpSync('web', 'dist', { recursive: true });
