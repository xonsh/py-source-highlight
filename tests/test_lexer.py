from srchilite import get_tokens


def test_get_tokens_python():
    code = (
        "print('hello')\n"
        "x = 1\n"
    )
    obs = get_tokens(code, "/home/scopatz/miniconda/share/source-highlight/python.lang")
    print(obs)


if __name__ == "__main__":
    test_get_tokens_python()
