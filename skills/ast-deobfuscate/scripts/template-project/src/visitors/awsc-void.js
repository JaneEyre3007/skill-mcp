module.exports = {
  UnaryExpression(path) {
    if (path.node.operator === 'void') {
      path.replaceWith(path.node.argument)
    }
  }
}
