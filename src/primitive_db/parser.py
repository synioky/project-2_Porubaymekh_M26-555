import shlex


def tokenize(text):
    """Разбивает команду на части, сохраняя кавычки вокруг строк."""
    lexer = shlex.shlex(text, posix=False, punctuation_chars="(),=")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = []
    for token in lexer:
        if all(char in "(),=" for char in token):
            tokens.extend(token)
        else:
            tokens.append(token)
    return tokens


def parse_value(token):
    """Определяет значение и его тип: str, int или bool."""
    if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
        return token[1:-1]
    if token.lower() in ("true", "false"):
        return token.lower() == "true"
    if token.lstrip("-").isdigit() and not token.startswith("--"):
        return int(token)
    raise ValueError(f"{token!r}: строки нужно заключать в кавычки")


def parse_assignments(tokens):
    """Разбирает присваивания вида столбец = значение."""
    result = {}
    while tokens:
        if len(tokens) < 3 or tokens[1] != "=" or not tokens[0].isidentifier():
            raise ValueError("ожидается столбец = значение")
        column, _, value = tokens[:3]
        if column in result:
            raise ValueError(f"столбец {column!r} указан повторно")
        result[column] = parse_value(value)
        tokens = tokens[3:]
        if tokens:
            if tokens[0] != "," or len(tokens) == 1:
                raise ValueError("между присваиваниями нужна запятая")
            tokens = tokens[1:]
    if not result:
        raise ValueError("пустое условие")
    return result


def parse_where(tokens):
    """Разбирает одно условие равенства после where."""
    result = parse_assignments(tokens)
    if len(result) != 1:
        raise ValueError("where поддерживает одно условие равенства")
    return result


def parse_values(tokens):
    """Разбирает значения в скобках после values."""
    if len(tokens) < 2 or tokens[0] != "(" or tokens[-1] != ")":
        raise ValueError("после values нужны значения в скобках")
    inner = tokens[1:-1]
    if not inner:
        return []
    if len(inner) % 2 == 0 or any(t != "," for t in inner[1::2]):
        raise ValueError("значения нужно разделять запятыми")
    return [parse_value(token) for token in inner[::2]]


def parse_command(text):
    """Возвращает название команды и её аргументы."""
    tokens = tokenize(text)
    if not tokens:
        return "empty", ()
    command = tokens[0].lower()
    match command:
        case "help" | "exit" | "list_tables" if len(tokens) == 1:
            return command, ()
        case "create_table" if len(tokens) >= 3:
            return command, (tokens[1], tokens[2:])
        case "drop_table" | "info" if len(tokens) == 2:
            return command, (tokens[1],)
        case "insert" if len(tokens) >= 6:
            if tokens[1].lower() == "into" and tokens[3].lower() == "values":
                return command, (tokens[2], parse_values(tokens[4:]))
        case "select" | "delete" if len(tokens) >= 3:
            if tokens[1].lower() == "from":
                if command == "select" and len(tokens) == 3:
                    return command, (tokens[2], None)
                if len(tokens) > 4 and tokens[3].lower() == "where":
                    return command, (tokens[2], parse_where(tokens[4:]))
        case "update" if len(tokens) >= 10:
            if tokens[2].lower() == "set":
                # Слово where в кавычках остаётся частью значения.
                split = next(
                    (i for i in range(3, len(tokens)) if tokens[i].lower() == "where"),
                    None,
                )
                if split is not None:
                    return command, (
                        tokens[1],
                        parse_assignments(tokens[3:split]),
                        parse_where(tokens[split + 1 :]),
                    )
        case _:
            if command not in {
                "help",
                "exit",
                "list_tables",
                "create_table",
                "drop_table",
                "info",
                "insert",
                "select",
                "update",
                "delete",
            }:
                return "unknown", (tokens[0],)
    raise ValueError("неверный синтаксис команды, см. help")
