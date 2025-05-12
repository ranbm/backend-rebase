import zlib
import logging
from typing import Optional, Callable

class _Node:
    __slots__ = ("key", "value", "prev", "next")
    def __init__(self, key: str, value: int):
        self.key = key
        self.value = value
        self.prev: Optional[_Node] = None
        self.next: Optional[_Node] = None

class HashMap:
    def __init__(
        self,
        hash_function: Optional[Callable[[str], int]] = None,
        capacity: int = 100000,
        num_buckets: int = 100,
        max_bucket_size: Optional[int] = None,
    ) -> None:
        self.capacity = capacity
        self.size = 0
        self.bucket_count = num_buckets
        self.max_bucket_size = max_bucket_size or float("inf")

        def _default_hash(key: str) -> int:
            return zlib.crc32(key.encode("utf-8"))
        self._hash = hash_function or _default_hash

        self.buckets: list[Optional[_Node]] = [None] * self.bucket_count

    def _bucket_index(self, key: str) -> int:
        return self._hash(key) % self.bucket_count

    def _resize(self):
        old_buckets = self.buckets
        self.bucket_count *= 2
        self.buckets = [None] * self.bucket_count
        self.size = 0

        for head in old_buckets:
            node = head
            while node:
                self.put(node.key, node.value)
                node = node.next

    def put(self, key: str, value: int) -> None:
        idx = self._bucket_index(key)
        head = self.buckets[idx]

        node = head
        while node:
            if node.key == key:
                node.value = value
                return
            node = node.next

        depth = 0
        node = head
        while node:
            depth += 1
            if depth >= self.max_bucket_size:
                logging.warning(
                    f"Bucket {idx} reached depth {depth}, resizing..."
                )
                self._resize()
                idx = self._bucket_index(key)
                head = self.buckets[idx]
                break
            node = node.next

        if self.size + 1 > self.capacity:
            raise AssertionError(f"HashMap capacity of {self.capacity} reached.")

        new_node = _Node(key, value)
        new_node.next = head
        if head:
            head.prev = new_node
        self.buckets[idx] = new_node
        self.size += 1

    def get(self, key: str) -> Optional[int]:
        idx = self._bucket_index(key)
        node = self.buckets[idx]
        while node:
            if node.key == key:
                return node.value
            node = node.next
        return None

    def remove(self, key: str) -> None:
        idx = self._bucket_index(key)
        node = self.buckets[idx]
        while node:
            if node.key == key:
                if node.prev:
                    node.prev.next = node.next
                else:
                    self.buckets[idx] = node.next
                if node.next:
                    node.next.prev = node.prev
                self.size -= 1
                return
            node = node.next
