#include "helpers.h"

namespace pysrchilite {

virtual void LexerGetTokensFormatter::format(
    const std::string &s,
    const srchilite::FormatterParams *params = 0)
{
  // do not print anything string for empty strings
  if (!s.size())
    return;
             if (elem != "normal" || !s.size()) {
                 std::cout << elem << ": " << s;
                 if (params)
                     std::cout << ", start: " << params->start;
                 std::cout << std::endl;
             }
         }
};

} // end pysrchilite