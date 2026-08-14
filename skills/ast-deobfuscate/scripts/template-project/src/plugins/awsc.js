const { applyVisitors, reparse } = require('../lib/core')
const runCommon = require('./common')

const awscVoid = require('../visitors/awsc-void')
const awscLogicalToIf = require('../visitors/awsc-logical-to-if')
const awscConditionalToIf = require('../visitors/awsc-conditional-to-if')
const awscNormalizeBlocks = require('../visitors/awsc-normalize-blocks')

module.exports = function runAwsc(ast) {
  applyVisitors(ast, [
    awscVoid,
    awscConditionalToIf,
    awscLogicalToIf,
    awscNormalizeBlocks
  ])
  return runCommon(reparse(ast))
}
