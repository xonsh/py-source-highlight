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

} // end pysrchilite