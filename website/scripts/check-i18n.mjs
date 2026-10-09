import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const i18nDir = resolve(__dirname, '../src/i18n');

const en = JSON.parse(readFileSync(resolve(i18nDir, 'en.json'), 'utf8'));
const de = JSON.parse(readFileSync(resolve(i18nDir, 'de.json'), 'utf8'));

function collectKeys(obj, prefix = '') {
  const keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object') {
      keys.push(...collectKeys(value, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

const enKeys = collectKeys(en).sort();
const deKeys = collectKeys(de).sort();

const enSet = new Set(enKeys);
const deSet = new Set(deKeys);

const onlyInEn = enKeys.filter((k) => !deSet.has(k));
const onlyInDe = deKeys.filter((k) => !enSet.has(k));

const enDraft = enKeys.filter((k) => k.includes('_draft'));
const deDraft = deKeys.filter((k) => k.includes('_draft'));

let ok = true;

if (onlyInEn.length > 0 || onlyInDe.length > 0) {
  ok = false;
  for (const k of onlyInEn) console.log(`Only in en.json: ${k}`);
  for (const k of onlyInDe) console.log(`Only in de.json: ${k}`);
}

const draftsSymmetric = JSON.stringify(enDraft) === JSON.stringify(deDraft);
if (!draftsSymmetric) {
  ok = false;
  console.log('_draft keys differ between en.json and de.json');
}

console.log(`EN keys: ${enKeys.length}`);
console.log(`DE keys: ${deKeys.length}`);
console.log(`_draft keys — EN: ${enDraft.length}, DE: ${deDraft.length}`);

if (ok) {
  console.log('PASS');
  process.exit(0);
} else {
  console.log('FAIL');
  process.exit(1);
}
