import hashlib
import re

BODY_PATTERN = r'(?s)\*\*\* START OF[^\r\n]*\*\*\*(.*?)\*\*\* END OF'
TOKEN_PATTERN = r'[a-z]+'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def features(text):
    match = re.search(BODY_PATTERN, text)
    if not match or not match.group(1).strip():
        raise ValueError("Missing or empty START/END literary body")
    body = match.group(1)
    tokens = re.findall(TOKEN_PATTERN, body.lower())
    return {"body_char_count": len(body), "word_count": len(tokens),
            "alice_mentions": tokens.count("alice"), "monster_mentions": tokens.count("monster")}
