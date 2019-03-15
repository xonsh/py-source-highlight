from srchilite import Token, get_tokens


def test_get_tokens_python():
    code = "print('hello')\n" "x = 1\n"
    obs = get_tokens(code, "py")
    exp = [
        (Token.Keyword, "print"),
        (Token.Literal.String.Symbol, "("),
        (Token.Literal.String, "'hello'"),
        (Token.Literal.String.Symbol, ")"),
        (Token.Text, "\n"),
        (Token.Text, "x "),
        (Token.Literal.String.Symbol, "="),
        (Token.Text, " "),
        (Token.Literal.Number, "1"),
        (Token.Text, "\n"),
    ]
    assert obs == exp


if __name__ == "__main__":
    test_get_tokens_python()
