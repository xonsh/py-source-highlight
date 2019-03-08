#ifndef PYSRCHILITE_HELPERS_H
#define PYSRCHILITE_HELPERS_H

#include <utility>
#include <string>
#include <vector>

#include "boost/shared_ptr.hpp"

#include "srchilite/formatter.h"


namespace pysrchilite {

typedef boost::shared_ptr<std::vector<std::pair<std::string, std::string> > > GetTokensPtr;

class LexerGetTokensFormatter: public srchilite::Formatter {
 private:
  std::string elem;
  GetTokensPtr tokens;

 public:
  LexerGetTokensFormatter(const std::string &elem_, GetTokensPtr tokens_) :
    elem(elem_),
    tokens(tokens_)
    {};

  virtual void format(const std::string &s,
                      const srchilite::FormatterParams *params = 0);
};

typedef boost::shared_ptr<LexerGetTokensFormatter> LexerGetTokensFormatterPtr;


GetTokensPtr get_tokens(const std::string code, const std::string path,
                        const std::string file);

} // end pysrchilite
#endif