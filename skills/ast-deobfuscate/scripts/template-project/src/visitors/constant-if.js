const t = require('@babel/types')

function cloneStatements(statements) {
  return statements.map((statement) => t.cloneNode(statement, true))
}

module.exports = {
  IfStatement(path) {
    const evaluation = path.get('test').evaluate()
    if (!evaluation.confident) return
    if (evaluation.value) {
      if (t.isBlockStatement(path.node.consequent)) {
        path.replaceWithMultiple(cloneStatements(path.node.consequent.body))
      } else {
        path.replaceWith(path.node.consequent)
      }
      return
    }
    if (!path.node.alternate) {
      path.remove()
      return
    }
    if (t.isBlockStatement(path.node.alternate)) {
      path.replaceWithMultiple(cloneStatements(path.node.alternate.body))
    } else {
      path.replaceWith(path.node.alternate)
    }
  }
}
