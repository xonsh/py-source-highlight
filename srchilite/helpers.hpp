#ifndef PYSRCHILITE_HELPERS_H
#define PYSRCHILITE_HELPERS_H

#include <utility>
#include <string>
#include <vector>

#include "boost/shared_ptr.hpp"

#include "srchilite/formatter.h"


namespace pysrchilite {

class LexerGetTokensFormatter: public srchilite::Formatter {
 public:
  LexerGetTokensFormatter();
  std::vector<std::pair<std::string, std::string> > tokens;
}

typedef boost::shared_ptr<LexerGetTokensFormatter> LexerGetTokensFormatterPtr;

} // end pysrchilite
#endif