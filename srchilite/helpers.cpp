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


GetTokensPtr get_tokens(const std::string code, const std::string path,
                        const std::string file) {
  // some initial data setup
  srchilite::RegexRuleFactory ruleFactory;
  srchilite::LangDefManager langDefManager(&ruleFactory);
  srchilite::SourceHighlighter highlighter(langDefManager.getHighlightState(
    path, file));
  // make format manager
  GetTokensPtr tokens;
  srchilite::FormatterManager formatterManager(LexerGetTokensFormatterPtr(
    new LexerGetTokensFormatter("Unknown", tokens)));
  // fill up the format manager
  formatterManager.addFormatter("string", LexerGetTokensFormatterPtr(
    new LexerGetTokensFormatter("String", tokens)));
/*
         formatterManager.addFormatter("type", keywordFormatter);
         formatterManager.addFormatter("comment", InfoFormatterPtr(
                 new InfoFormatter("comment")));
         formatterManager.addFormatter("symbol", InfoFormatterPtr(new InfoFormatter(
                 "symbol")));
         formatterManager.addFormatter("number", InfoFormatterPtr(new InfoFormatter(
                 "number")));
         formatterManager.addFormatter("preproc", InfoFormatterPtr(
                 new InfoFormatter("preproc")));
*/
  highlighter.setFormatterManager(&formatterManager);

         // make sure it uses additional information
  //       srchilite::FormatterParams params;
  //       highlighter.setFormatterParams(&params);

  // we now highlight a line a time
  std::string line;
  std::stringstream codestream(code);
  while (std::getline(codestream, line)) {
    highlighter.highlightParagraph(line);
  }
  return tokens;
}

} // end pysrchilite