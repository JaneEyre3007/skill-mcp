const t = require('@babel/types')

module.exports = {
  VariableDeclarator(path) {
    if (!t.isIdentifier(path.node.id)) return
    const binding = path.scope.getBinding(path.node.id.name)
    if (!binding || binding.referenced || !binding.constant) return
    const declaration = path.parentPath
    const parent = declaration.parentPath
    if (t.isForInStatement(parent?.node) || t.isForOfStatement(parent?.node)) return
    if (declaration.node.declarations.length === 1) {
      declaration.remove()
      declaration.scope.crawl()
      return
    }
    path.remove()
    path.scope.crawl()
  }
}
