from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


class ServerTimestamp:
    """Sentinel used to mimic google.cloud.firestore.SERVER_TIMESTAMP."""


SERVER_TIMESTAMP = ServerTimestamp()


def _resolve_server_timestamps(value: Any) -> Any:
    if value is SERVER_TIMESTAMP:
        return datetime.now(timezone.utc)
    if isinstance(value, dict):
        return {k: _resolve_server_timestamps(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_server_timestamps(v) for v in value]
    return value


@dataclass
class FakeDocumentSnapshot:
    id: str
    _data: Optional[Dict[str, Any]]

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        if self._data is None:
            return None
        # Return a shallow copy to avoid test mutation leaks.
        return dict(self._data)


class FakeDocumentRef:
    def __init__(self, collection: "FakeCollectionRef", doc_id: str):
        self._collection = collection
        self._id = doc_id

    def collection(self, name: str) -> "FakeCollectionRef":
        # Support subcollections by treating the fully-qualified collection path as the key.
        # Example: users/u1/accounts
        path = f"{self._collection._name}/{self._id}/{name}"
        return FakeCollectionRef(self._collection._db, path)

    def get(self) -> FakeDocumentSnapshot:
        data = self._collection._docs.get(self._id)
        return FakeDocumentSnapshot(id=self._id, _data=data)

    def set(self, data: Dict[str, Any]) -> None:
        self._collection._docs[self._id] = _resolve_server_timestamps(data)

    def update(self, updates: Dict[str, Any]) -> None:
        if self._id not in self._collection._docs:
            raise KeyError(f"Document {self._id} does not exist")
        current = self._collection._docs[self._id]
        current.update(_resolve_server_timestamps(updates))

    def delete(self) -> None:
        self._collection._docs.pop(self._id, None)


class FakeQuery:
    def __init__(self, collection: FakeCollectionRef):
        self._collection = collection
        self._where_clauses: List[tuple] = []
        self._order_by_clauses: List[tuple] = []
        self._limit_n: Optional[int] = None

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        self._where_clauses.append((field, op, value))
        return self

    def order_by(self, field: str, direction: str = "ASCENDING") -> FakeQuery:
        self._order_by_clauses.append((field, direction))
        return self

    def limit(self, n: int) -> FakeQuery:
        self._limit_n = n
        return self

    def stream(self) -> Iterable[FakeDocumentSnapshot]:
        docs = [(doc_id, dict(data)) for doc_id, data in self._collection._docs.items()]

        # Apply WHERE
        for field, op, value in self._where_clauses:
            if op == "==":
                docs = [d for d in docs if d[1].get(field) == value]
            elif op == ">=":
                docs = [d for d in docs if d[1].get(field) >= value]
            elif op == "<=":
                docs = [d for d in docs if d[1].get(field) <= value]
            elif op == ">":
                docs = [d for d in docs if d[1].get(field) > value]
            elif op == "<":
                docs = [d for d in docs if d[1].get(field) < value]

        # Apply ORDER BY (naive, supports only first order_by for now)
        if self._order_by_clauses:
            field, direction = self._order_by_clauses[0]
            reverse = (direction == "DESCENDING")
            # Filter out docs missing the field before sorting to avoid TypeError
            docs = sorted(
                [d for d in docs if field in d[1]],
                key=lambda x: x[1][field],
                reverse=reverse
            )

        # Apply LIMIT
        if self._limit_n is not None:
            docs = docs[: self._limit_n]

        for doc_id, data in docs:
            yield FakeDocumentSnapshot(id=doc_id, _data=data)


class FakeCollectionRef:
    def __init__(self, db: "FakeFirestore", name: str):
        self._db = db
        self._name = name
        self._docs: Dict[str, Dict[str, Any]] = db._collections.setdefault(name, {})

    def document(self, doc_id: str) -> FakeDocumentRef:
        return FakeDocumentRef(self, doc_id)

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(self).where(field, op, value)

    def order_by(self, field: str, direction: str = "ASCENDING") -> FakeQuery:
        return FakeQuery(self).order_by(field, direction)

    def limit(self, n: int) -> FakeQuery:
        return FakeQuery(self).limit(n)

    def stream(self) -> Iterable[FakeDocumentSnapshot]:
        return FakeQuery(self).stream()


class FakeFirestore:
    def __init__(self):
        self._collections: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollectionRef:
        return FakeCollectionRef(self, name)
