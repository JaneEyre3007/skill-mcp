#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const parser = require('@babel/parser')
const traverse = require('@babel/traverse').default
const generator = require('@babel/generator').default
const t = require('@babel/types')

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

function cloneStatements(statements) {
  return statements.map((statement) => t.cloneNode(statement, true))
}

function isIdentifierName(value) {
  return /^[A-Za-z_$][0-9A-Za-z_$]*$/.test(value)
}

const visitors = {
  deleteExtra: {
    StringLiteral(path) {
      delete path.node.extra
    },
    NumericLiteral(path) {
      delete path.node.extra
    }
  },

  foldBinary: {
    BinaryExpression: {
      exit(path) {
        const evaluation = path.evaluate()
        if (!evaluation.confident) return
        if (typeof evaluation.value === 'function') return
        path.replaceWith(t.valueToNode(evaluation.value))
      }
    }
  },

  foldBooleanObfuscation: {
    UnaryExpression(path) {
      if (path.node.operator !== '!') return
      const arg = path.node.argument
      if (t.isArrayExpression(arg) && arg.elements.length === 0) {
        path.replaceWith(t.booleanLiteral(false))
        return
      }
      if (!t.isUnaryExpression(arg, { operator: '!' })) return
      const nested = arg.argument
      if (t.isArrayExpression(nested) && nested.elements.length === 0) {
        path.replaceWith(t.booleanLiteral(true))
      }
    }
  },

  mergeStrings: {
    BinaryExpression: {
      exit(path) {
        if (path.node.operator !== '+') return
        const left = path.node.left
        const right = path.node.right
        if (!t.isStringLiteral(left) || !t.isStringLiteral(right)) return
        path.replaceWith(t.stringLiteral(left.value + right.value))
      }
    }
  },

  normalizeMember: {
    MemberExpression(path) {
      if (!path.node.computed) return
      if (!t.isStringLiteral(path.node.property)) return
      const value = path.node.property.value
      if (!isIdentifierName(value)) return
      path.node.property = t.identifier(value)
      path.node.computed = false
    }
  },

  removeEmpty: {
    EmptyStatement(path) {
      path.remove()
    }
  },

  splitSequenceStatements: {
    ExpressionStatement(path) {
      if (!t.isSequenceExpression(path.node.expression)) return
      const statements = path.node.expression.expressions.map((expr) => t.expressionStatement(expr))
      path.replaceWithMultiple(statements)
    }
  },

  removeUnusedVariables: {
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
  },

  constantIf: {
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
  },

  awscVoid: {
    UnaryExpression(path) {
      if (path.node.operator === 'void') {
        path.replaceWith(path.node.argument)
      }
    }
  },

  awscLogicalToIf: {
    LogicalExpression(path) {
      if (path.node.operator !== '&&') return
      if (!path.parentPath.isExpressionStatement()) return
      path.parentPath.replaceWith(
        t.ifStatement(path.node.left, t.blockStatement([t.expressionStatement(path.node.right)]))
      )
    }
  },

  awscConditionalToIf: {
    ConditionalExpression(path) {
      if (!path.parentPath.isExpressionStatement()) return
      path.parentPath.replaceWith(
        t.ifStatement(
          path.node.test,
          t.blockStatement([t.expressionStatement(path.node.consequent)]),
          t.blockStatement([t.expressionStatement(path.node.alternate)])
        )
      )
    }
  },

  awscNormalizeBlocks: {
    IfStatement(path) {
      if (!t.isBlockStatement(path.node.consequent)) {
        path.node.consequent = t.blockStatement([path.node.consequent])
      }
      if (path.node.alternate && !t.isBlockStatement(path.node.alternate) && !t.isIfStatement(path.node.alternate)) {
        path.node.alternate = t.blockStatement([path.node.alternate])
      }
    },
    BlockStatement(path) {
      const nextBody = []
      let changed = false
      for (const statement of path.node.body) {
        if (t.isBlockStatement(statement)) {
          changed = true
          nextBody.push(...statement.body)
        } else {
          nextBody.push(statement)
        }
      }
      if (changed) {
        path.node.body = nextBody
      }
    }
  },

  whileSwitchUnwrap: {
    WhileStatement: {
      exit(path) {
        const body = path.node.body
        if (!t.isBlockStatement(body) || body.body.length === 0) return
        const first = body.body[0]
        if (!t.isSwitchStatement(first)) return

        const test = path.node.test
        const isForever =
          t.isBooleanLiteral(test, { value: true }) ||
          (t.isUnaryExpression(test, { operator: '!' }) && t.isNumericLiteral(test.argument, { value: 0 }))
        if (!isForever) return

        const discriminant = first.discriminant
        if (!t.isMemberExpression(discriminant)) return
        if (!t.isIdentifier(discriminant.object)) return

        let indexName = null
        if (t.isUpdateExpression(discriminant.property) && t.isIdentifier(discriminant.property.argument)) {
          indexName = discriminant.property.argument.name
        } else if (t.isIdentifier(discriminant.property)) {
          indexName = discriminant.property.name
        }
        if (!indexName) return

        const orderBinding = path.scope.getBinding(discriminant.object.name)
        if (!orderBinding) return
        const init = orderBinding.path.node.init
        if (!t.isCallExpression(init) || !t.isMemberExpression(init.callee)) return
        if (!t.isStringLiteral(init.callee.object)) return
        if (!t.isIdentifier(init.callee.property, { name: 'split' })) return
        if (init.arguments.length !== 1 || !t.isStringLiteral(init.arguments[0], { value: '|' })) return

        const order = init.callee.object.value.split('|')
        const caseMap = new Map()
        for (const switchCase of first.cases) {
          if (!switchCase.test) continue
          if (!t.isStringLiteral(switchCase.test) && !t.isNumericLiteral(switchCase.test)) continue
          caseMap.set(String(switchCase.test.value), switchCase)
        }

        const flattened = []
        for (const key of order) {
          const switchCase = caseMap.get(String(key))
          if (!switchCase) continue
          for (const statement of switchCase.consequent) {
            if (t.isContinueStatement(statement) || t.isBreakStatement(statement)) {
              break
            }
            flattened.push(t.cloneNode(statement, true))
            if (t.isReturnStatement(statement)) {
              break
            }
          }
        }

        if (flattened.length > 0) {
          path.replaceWithMultiple(flattened)
        }
      }
    }
  }
}

function runCommon(ast) {
  applyVisitors(ast, [
    visitors.deleteExtra,
    visitors.foldBinary,
    visitors.foldBooleanObfuscation,
    visitors.mergeStrings,
    visitors.normalizeMember,
    visitors.splitSequenceStatements,
    visitors.constantIf,
    visitors.removeEmpty,
    visitors.removeUnusedVariables
  ])
  return ast
}

function runAwsc(ast) {
  applyVisitors(ast, [
    visitors.awscVoid,
    visitors.awscConditionalToIf,
    visitors.awscLogicalToIf,
    visitors.awscNormalizeBlocks
  ])
  return runCommon(reparse(ast))
}

function runObfuscator(ast) {
  applyVisitors(ast, [
    visitors.whileSwitchUnwrap,
    visitors.normalizeMember
  ])
  return runCommon(reparse(ast))
}

function runSojson(ast) {
  // Template entry point only.
  // For a real target, add a dedicated decrypt bootstrap pass here.
  return runCommon(ast)
}

function familyScore(code) {
  return {
    sojson: countMatches(code, /_0x[0-9a-f]+/gi) + countMatches(code, /debugger/g),
    sojsonv7: countMatches(code, /_0x[0-9a-f]+/gi) + countMatches(code, /setInterval/g),
    obfuscator: countMatches(code, /split\('\|'\)/g) + countMatches(code, /while\s*\(\s*(?:true|!!\[\]|!0)\s*\)/g),
    awsc: countMatches(code, /void 0/g) + countMatches(code, /\?/g) + countMatches(code, /&&/g),
    jjencode: code.includes('$___') || code.includes('$$$') ? 10 : 0
  }
}

const plugins = [
  {
    name: 'sojsonv7',
    detect(code) {
      const score = familyScore(code)
      return score.sojsonv7 >= 3 && /_0x/i.test(code)
    },
    transform(code) {
      return generateCode(runSojson(parseCode(code)))
    }
  },
  {
    name: 'sojson',
    detect(code) {
      const score = familyScore(code)
      return score.sojson >= 2 && /_0x/i.test(code)
    },
    transform(code) {
      return generateCode(runSojson(parseCode(code)))
    }
  },
  {
    name: 'obfuscator',
    detect(code) {
      const score = familyScore(code)
      return score.obfuscator >= 2 || /_0x/i.test(code)
    },
    transform(code) {
      return generateCode(runObfuscator(parseCode(code)))
    }
  },
  {
    name: 'awsc',
    detect(code) {
      const score = familyScore(code)
      return score.awsc >= 6
    },
    transform(code) {
      return generateCode(runAwsc(parseCode(code)))
    }
  },
  {
    name: 'common',
    detect() {
      return true
    },
    transform(code) {
      return generateCode(runCommon(parseCode(code)))
    }
  }
]

function getArg(flag, fallback) {
  const index = process.argv.indexOf(flag)
  if (index === -1 || index + 1 >= process.argv.length) return fallback
  return process.argv[index + 1]
}

function main() {
  const inputFile = getArg('-i', 'input.js')
  const outputFile = getArg('-o', 'output.js')
  const code = fs.readFileSync(inputFile, 'utf8')

  let result = code
  let pluginUsed = 'common'

  for (const plugin of plugins) {
    if (!plugin.detect(code)) continue
    try {
      const candidate = plugin.transform(code)
      if (candidate && candidate !== code) {
        result = candidate
        pluginUsed = plugin.name
        break
      }
    } catch (error) {
      console.error(`[${plugin.name}] ${error.message}`)
    }
  }

  const banner = [
    '// generated by decode_action_scaffold',
    `// plugin: ${pluginUsed}`,
    `// input: ${path.basename(inputFile)}`,
    ''
  ].join('\n')

  fs.writeFileSync(outputFile, banner + result, 'utf8')
  console.log(`plugin=${pluginUsed}`)
  console.log(`output=${outputFile}`)
}

main()
