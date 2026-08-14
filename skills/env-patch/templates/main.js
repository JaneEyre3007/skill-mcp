'use strict';

const fs = require('fs');
const path = require('path');
const { installEnv } = require('./mod');

function readJsonArg() {
  const raw = process.argv[2] || '{}';
  try {
    return JSON.parse(raw);
  } catch (error) {
    return { url: raw };
  }
}

function loadTarget() {
  const targetPath = path.join(__dirname, 'js_reverse_cache', 'target', 'raw.js');
  if (fs.existsSync(targetPath)) {
    require(targetPath);
  }
}

function getEncryptedParams(input) {
  installEnv(input.profile || undefined);
  loadTarget();

  // Replace this block with the verified target entry call.
  // Keep stdout as JSON only, because main.py parses it.
  return {
    url: input.url || '',
    sign: '',
  };
}

if (require.main === module) {
  try {
    const result = getEncryptedParams(readJsonArg());
    process.stdout.write(JSON.stringify(result));
  } catch (error) {
    process.stderr.write(error && error.stack || String(error));
    process.exit(1);
  }
}

module.exports = getEncryptedParams;
