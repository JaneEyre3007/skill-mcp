const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEBUG_DIR = path.join(ROOT_DIR, 'url-suffix-research', 'debug-output');
const EVAL_CODE_PATH = process.env.RS_EVAL_CODE || path.join(ROOT_DIR, 'cookie-t-pure-runtime', 'samples', 'eval_code.js');

function ensureDebugDir() {
    fs.mkdirSync(DEBUG_DIR, { recursive: true });
}

function debugPath(fileName) {
    ensureDebugDir();
    return path.join(DEBUG_DIR, fileName);
}

function readEvalCode() {
    return fs.readFileSync(EVAL_CODE_PATH, 'utf-8');
}

module.exports = {
    ROOT_DIR,
    DEBUG_DIR,
    EVAL_CODE_PATH,
    debugPath,
    readEvalCode,
};
