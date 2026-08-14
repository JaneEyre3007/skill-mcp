const t = require('@babel/types')

module.exports = {
  BinaryExpression: {
    exit(path) {
      const evaluation = path.evaluate()
      if (!evaluation.confident) return
      if (typeof evaluation.value === 'function') return
      path.replaceWith(t.valueToNode(evaluation.value))
    }
  }
}
