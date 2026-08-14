const parser = require('@babel/parser')
const traverse = require('@babel/traverse').default
const generator = require('@babel/generator').default

function parseCode(code) {
  return parser.parse(code, {
    sourceType: 'unambiguous',
    errorRecovery: true,
    plugins: ['jsx']
  })
}

function generateCode(ast) {
  return generator(ast, {
    comments: false,
    jsescOption: { minimal: true }
  }).code
}

function reparse(ast) {
  return parseCode(generateCode(ast))
}

function applyVisitors(ast, visitors) {
  for (const visitor of visitors) {
    traverse(ast, visitor)
  }
  return ast
}

function countMatches(code, regex) {
  const matches = code.match(regex)
  return matches ? matches.length : 0
}

function detectFamily(code) {
  const score = {
    sojson: countMatches(code, /_0x[0-9a-f]+/gi) + countMatches(code, /debugger/g),
    sojsonv7: countMatches(code, /_0x[0-9a-f]+/gi) + countMatches(code, /setInterval/g),
    obfuscator: countMatches(code, /split\('\|'\)/g) + countMatches(code, /while\s*\(\s*(?:true|!!\[\]|!0)\s*\)/g),
    awsc: countMatches(code, /void 0/g) + countMatches(code, /\?/g) + countMatches(code, /&&/g),
    jjencode: code.includes('$___') || code.includes('$$$') ? 10 : 0
  }

  if (score.sojsonv7 >= 3 && /_0x/i.test(code)) return 'sojsonv7'
  if (score.sojson >= 2 && /_0x/i.test(code)) return 'sojson'
  if (score.jjencode >= 10) return 'common'
  if (score.obfuscator >= 2 || /_0x/i.test(code)) return 'obfuscator'
  if (score.awsc >= 6) return 'awsc'
  return 'common'
}

module.exports = {
  applyVisitors,
  detectFamily,
  generateCode,
  parseCode,
  reparse
}
