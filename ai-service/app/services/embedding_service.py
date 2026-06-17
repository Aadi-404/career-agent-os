import hashlib
import math
import re


VECTOR_SIZE = 256


def embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    tokens = _tokens(text)
    features = []
    features.extend(tokens)
    features.extend(" ".join(tokens[index : index + 2]) for index in range(max(0, len(tokens) - 1)))
    features.extend(_char_ngrams(" ".join(tokens), size=4))

    for feature in features:
        index = _stable_index(feature)
        vector[index] += 1.0

    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def cosine_similarity(left: str, right: str) -> float:
    left_vector = embed_text(left)
    right_vector = embed_text(right)
    return sum(left_value * right_value for left_value, right_value in zip(left_vector, right_vector))


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    normalized = normalized.replace("ci/cd", "cicd")
    normalized = normalized.replace("c#", "csharp")
    return re.findall(r"[a-z0-9+#.]+", normalized)


def _char_ngrams(text: str, size: int) -> list[str]:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) < size:
        return [compact] if compact else []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]


def _stable_index(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % VECTOR_SIZE
