#ifndef PYSRCHILITE_HELPERS_H
#define PYSRCHILITE_HELPERS_H

#include <utility>
#include <string>
#include <vector>

#include "boost/shared_ptr.hpp"

#include "srchilite/formatter.h"


namespace pysrchilite {

typedef std::pair<std::string, std::string> TokenPair;
typedef std::vector<TokenPair> TokenPairs;
typedef boost::shared_ptr<TokenPairs> TokenPairsPtr;

extern TokenPairs ELEMS_TO_TOKENS;

void fill_elems_to_tokens_();

class LexerGetTokensFormatter: public srchilite::Formatter {
 private:
  std::string elem;
  TokenPairsPtr tokens;

 public:
  LexerGetTokensFormatter(const std::string &elem_, TokenPairsPtr tokens_) :
    elem(elem_),
    tokens(tokens_)
    {};

  virtual void format(const std::string &s,
                      const srchilite::FormatterParams *params = 0);
};

typedef boost::shared_ptr<LexerGetTokensFormatter> LexerGetTokensFormatterPtr;


TokenPairsPtr get_tokens(const std::string code, const std::string path,
                        const std::string file);

} // end pysrchilite
#endif