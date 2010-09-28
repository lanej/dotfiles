" Vim syntax file
" Language:     wiki
" Maintainer:   Adam Coddington <me@adamcoddington.net>
" Former Maintainer: Andreas Kneib <aporia@web.de>
" Last Change:  27 April 2010

" Quit if syntax file is already loaded
if version < 600
  syntax clear
elseif exists("b:current_syntax")
  finish
endif

if version < 508
  command! -nargs=+ WikiHiLink hi link <args>
else
  command! -nargs=+ WikiHiLink hi def link <args>
endif

syn match   wikiWord        "\<[A-Z][^A-Z ]\+[A-Z][^A-Z ][^A-Z ]*\>"
syn match   wikiLine        "^----$"
syn match   wikiTodo        "^TODO:.*$"
syn match   wikiQuote       "^>.*$"
syn match   wikiULList        "^[ ]\+[*]"
syn match   wikiOLList        "^[ ]\+[a-zA-Z0-9]\."
syn match   wikiTicketLink    "#\d\{1,10\}"
syn match   wikiReportLink    "{\d\{1,10\}}"
syn match   wikiRevisionLink  "r\d\{1,10\}"
syn match   wikiDefinition  "^[ ]\+[^:]*::$"
syn match   wikiLink    "\[\{1,3\}[^]]*\]\{1,3\}"
syn match   wikiBars    "[|]\{2\}"

syn region  wikiCurly       start="{\{3\}" end="}\{3\}"
syn region  wikiHead        start="^= " end="[=] *"
syn region  wikiSubhead     start="^== " end="==[ ]*"
syn region  wikiSubheadII     start="^=== " end="===[ ]*"
syn region  wikiSubheadIII     start="^==== " end="====[ ]*"
syn match   wikiCurlyError  "}"

syn region wikiItalic       start=+''+ end=+''+
syn region wikiBold         start=+'''+ end=+'''+
syn region wikiBoldItalic   start=+'''''+ end=+'''''+


" The default highlighting.
if version >= 508 || !exists("did_wiki_syn_inits")
  if version < 508
    let did_wiki_syn_inits = 1
  endif
  
  WikiHiLink wikiCurlyError  Error
  WikiHiLink wikiHead        PreProc
  WikiHiLink wikiSubhead     Identifier
  WikiHiLink wikiSubheadII   Function
  WikiHiLink wikiSubheadIII  Type
  WikiHiLink wikiCurly       Statement
  WikiHiLink wikiStar        String
  WikiHiLink wikiExtLink     Special
  WikiHiLink wikiLink        Special
  WikiHiLink wikiTicketLink  wikiLink
  WikiHiLink wikiReportLink  wikiLink
  WikiHiLink wikiRevisionLink  wikiLink
  WikiHiLink wikiLine        PreProc
  WikiHiLink wikiWord        Keyword
  WikiHiLink wikiBold        Constant
  WikiHiLink wikiItalic      Number
  WikiHiLink wikiBoldItalic  Conditional
  WikiHiLink wikiItalicBold  Conditional
  WikiHiLink wikiTodo        Todo
  WikiHiLink wikiQuote       Comment
  WikiHiLink wikiLink        Operator
  WikiHiLink wikiULList      Delimiter
  WikiHiLink wikiOLList      wikiULList
  WikiHiLink wikiDefinition  String
  WikiHiLink wikiBars        String
endif

delcommand WikiHiLink
  
let b:current_syntax = "wiki"

"EOF vim: tw=78:ft=vim:ts=8
