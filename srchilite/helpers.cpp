#include <iostream>
#include "srchilite/langdefmanager.h"
#include "srchilite/regexrulefactory.h"
#include "srchilite/sourcehighlighter.h"
#include "srchilite/formattermanager.h"

#include "helpers.hpp"

namespace pysrchilite {

void LexerGetTokensFormatter::format(
    const std::string &s,
    const srchilite::FormatterParams *params)
{
  // do not add anything string for empty strings
  if (!s.size())
    return;
  tokens->push_back(std::make_pair(elem, s));
};


TokenPairs ELEMS_TO_TOKENS = TokenPairs();

void fill_elems_to_tokens_() {
  using std::pair;
  using std::make_pair;

  ELEMS_TO_TOKENS.push_back(make_pair("and_but", "Name.Builtin"));
  ELEMS_TO_TOKENS.push_back(make_pair("argument", "Name.Variable"));
  ELEMS_TO_TOKENS.push_back(make_pair("assignment", "Operator"));
  ELEMS_TO_TOKENS.push_back(make_pair("atom", "Name.Entity"));
  ELEMS_TO_TOKENS.push_back(make_pair("bgcolor", "Text"));
  ELEMS_TO_TOKENS.push_back(make_pair("bibtex", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("bold", "Generic.Strong"));
  ELEMS_TO_TOKENS.push_back(make_pair("cbracket", "Punctuation"));
  ELEMS_TO_TOKENS.push_back(make_pair("classname", "Name.Class"));
  ELEMS_TO_TOKENS.push_back(make_pair("code", "Generic"));
  ELEMS_TO_TOKENS.push_back(make_pair("colon", "Punctuation"));
  ELEMS_TO_TOKENS.push_back(make_pair("comment", "Comment"));
  ELEMS_TO_TOKENS.push_back(make_pair("context", "Name.Namespace"));
  ELEMS_TO_TOKENS.push_back(make_pair("context_property", "Name.Property"));
  ELEMS_TO_TOKENS.push_back(make_pair("constant", "Name.Constant"));
  ELEMS_TO_TOKENS.push_back(make_pair("costant", "Name.Constant"));
  ELEMS_TO_TOKENS.push_back(make_pair("cuketag", "Name.Tag"));
  ELEMS_TO_TOKENS.push_back(make_pair("date", "Literal.Date"));
  ELEMS_TO_TOKENS.push_back(make_pair("difflines", "Text"));
  ELEMS_TO_TOKENS.push_back(make_pair("dynamic", "Name.Variable.Instance"));
  ELEMS_TO_TOKENS.push_back(make_pair("error", "Generic.Error"));
  ELEMS_TO_TOKENS.push_back(make_pair("file", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("fixed", "Generic.Output"));
  ELEMS_TO_TOKENS.push_back(make_pair("function", "Name.Function"));
  ELEMS_TO_TOKENS.push_back(make_pair("gherken", "Name.Variable.Magic"));
  ELEMS_TO_TOKENS.push_back(make_pair("given", "Name.Entity"));
  ELEMS_TO_TOKENS.push_back(make_pair("header_variable", "Name.Variable.Magic"));
  ELEMS_TO_TOKENS.push_back(make_pair("ip", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("italics", "Generic.Emph"));
  ELEMS_TO_TOKENS.push_back(make_pair("key", "Name.Attribute"));
  ELEMS_TO_TOKENS.push_back(make_pair("keyquote", "Literal.String.Heredoc"));
  ELEMS_TO_TOKENS.push_back(make_pair("keyword", "Keyword"));
  ELEMS_TO_TOKENS.push_back(make_pair("label", "Name.Tag"));
  ELEMS_TO_TOKENS.push_back(make_pair("layout_object", "Name.Variable.Instance"));
  ELEMS_TO_TOKENS.push_back(make_pair("layout_property", "Name.Property"));
  ELEMS_TO_TOKENS.push_back(make_pair("libsource", "Literal.String.Escape"));
  ELEMS_TO_TOKENS.push_back(make_pair("lineno", "Generic.Prompt"));
  ELEMS_TO_TOKENS.push_back(make_pair("linenum", "Generic.Prompt"));
  ELEMS_TO_TOKENS.push_back(make_pair("lyric_command", "Name.Function.Magic"));
  ELEMS_TO_TOKENS.push_back(make_pair("math", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("meta", "Name.Attribute"));
  ELEMS_TO_TOKENS.push_back(make_pair("name", "Name"));
  ELEMS_TO_TOKENS.push_back(make_pair("newfile", "Generic.Inserted"));
  ELEMS_TO_TOKENS.push_back(make_pair("normal", "Text"));
  ELEMS_TO_TOKENS.push_back(make_pair("note_duration", "Literal.Date"));
  ELEMS_TO_TOKENS.push_back(make_pair("number", "Literal.Number"));
  ELEMS_TO_TOKENS.push_back(make_pair("oldfile", "Generic.Deleted"));
  ELEMS_TO_TOKENS.push_back(make_pair("optionalargument", "Name.Variable"));
  ELEMS_TO_TOKENS.push_back(make_pair("path", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("predef_func", "Name.Function"));
  ELEMS_TO_TOKENS.push_back(make_pair("predef_var", "Name.Variable"));
  ELEMS_TO_TOKENS.push_back(make_pair("preproc", "Comment.Preproc"));
  ELEMS_TO_TOKENS.push_back(make_pair("property", "Name.Property"));
  ELEMS_TO_TOKENS.push_back(make_pair("regexp", "Literal.String.Regex"));
  ELEMS_TO_TOKENS.push_back(make_pair("selector", "Name.Tag"));
  ELEMS_TO_TOKENS.push_back(make_pair("scheme", "Name.Builtin"));
  ELEMS_TO_TOKENS.push_back(make_pair("scheme_value", "Name.Variable"));
  ELEMS_TO_TOKENS.push_back(make_pair("selector", "Name.Property"));
  ELEMS_TO_TOKENS.push_back(make_pair("specialchar", "Literal.String.Escape"));
  ELEMS_TO_TOKENS.push_back(make_pair("special_fun", "Name.Function.Magic"));
  ELEMS_TO_TOKENS.push_back(make_pair("string", "Literal.String"));
  ELEMS_TO_TOKENS.push_back(make_pair("symbol", "Literal.String.Symbol"));
  ELEMS_TO_TOKENS.push_back(make_pair("table", "Name.Namespace"));
  ELEMS_TO_TOKENS.push_back(make_pair("then", "Name.Builtin"));
  ELEMS_TO_TOKENS.push_back(make_pair("time", "Literal.Date"));
  ELEMS_TO_TOKENS.push_back(make_pair("todo", "Comment.Special"));
  ELEMS_TO_TOKENS.push_back(make_pair("type", "Keyword.Type"));
  ELEMS_TO_TOKENS.push_back(make_pair("underline", "Generic.Subheading"));
  ELEMS_TO_TOKENS.push_back(make_pair("url", "Literal.String.Other"));
  ELEMS_TO_TOKENS.push_back(make_pair("usertype", "Keyword.Declaration"));
  ELEMS_TO_TOKENS.push_back(make_pair("value", "Literal"));
  ELEMS_TO_TOKENS.push_back(make_pair("variable", "Name.Variable"));
  ELEMS_TO_TOKENS.push_back(make_pair("warning", "Generic.Emph"));
  ELEMS_TO_TOKENS.push_back(make_pair("when", "Name.Builtin"));
}

TokenPairsPtr get_tokens(const std::string code, const std::string path,
                         const std::string file) {
  // some initial data setup
  srchilite::RegexRuleFactory rule_factory;
  srchilite::LangDefManager lang_def_manager(&rule_factory);
  srchilite::SourceHighlighter highlighter(lang_def_manager.getHighlightState(
    path, file));
  // make format manager
  TokenPairsPtr tokens (new TokenPairs);
  srchilite::FormatterManager formatter_manager(LexerGetTokensFormatterPtr(
    new LexerGetTokensFormatter("Other", tokens)));
  // fill up the format manager
  if (ELEMS_TO_TOKENS.size() == 0) {
    fill_elems_to_tokens_();
  }
  for (auto token_pair=ELEMS_TO_TOKENS.begin(); token_pair != ELEMS_TO_TOKENS.end(); ++token_pair) {
    formatter_manager.addFormatter(token_pair->first, LexerGetTokensFormatterPtr(
      new LexerGetTokensFormatter(token_pair->second, tokens)));
  }
  highlighter.setFormatterManager(&formatter_manager);

         // make sure it uses additional information
  //       srchilite::FormatterParams params;
  //       highlighter.setFormatterParams(&params);

  // we now highlight a line a time
  std::string line;
  std::stringstream codestream(code);
  while (std::getline(codestream, line)) {
    highlighter.highlightParagraph(line);
    tokens->back().second += "\n";
  }
  return tokens;
}

} // end pysrchilite