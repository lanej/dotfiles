module.exports = grammar({
  name: "bnf",

  extras: ($) => [/[ \t]+/, $.comment],

  rules: {
    source_file: ($) =>
      seq(
        repeat(choice(seq($.production, $._newline), $._newline)),
        optional($.production),
      ),
    production: ($) =>
      seq(field("name", $.nonterminal), "::=", field("body", $.expression)),
    expression: ($) =>
      seq($.sequence, repeat(seq($.alternative_separator, $.sequence))),
    alternative_separator: () => token(choice("|", /\r?\n[ \t]*\|/)),
    sequence: ($) => repeat1(choice($.nonterminal, $.terminal)),
    nonterminal: () => /<[^<>\r\n]+>/,
    terminal: () =>
      token(choice(/"([^"\\\r\n]|\\.)*"/, /'([^'\\\r\n]|\\.)*'/)),
    comment: () => token(/#[^\r\n]*/),
    _newline: () => /\r?\n/,
  },
});
