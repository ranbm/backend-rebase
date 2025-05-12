import itertools
import os
import sys
import logging
import argparse
import zlib
from typing import Callable, Optional

from HashMap import HashMap

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    force=True,
)

def get_memory_usage() -> int:
    """Return current process RSS memory usage in bytes (0 if psutil not installed)."""
    if psutil:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    return 0


def partition_file(input_path: str, bucket_dir: str, num_buckets: int) -> None:
    logging.info("Partitioning started")
    os.makedirs(bucket_dir, exist_ok=True)
    bucket_files = [
        open(
            os.path.join(bucket_dir, f"bucket_{i}.txt"),
            "w",
            buffering=1 << 20
        )
        for i in range(num_buckets)
    ]
    try:
        with open(input_path, "r") as fin:
            while True:
                # Read a chunk of lines to avoid memory issues (chunk max size can be 1GB)
                chunk = list(itertools.islice(fin, 100000))
                if not chunk:
                    break
                for line in chunk:
                    b_idx = zlib.crc32(line.encode("utf-8", "ignore")) % num_buckets
                    bucket_files[b_idx].write(line)
    finally:
        for f in bucket_files:
            f.close()
    logging.info("Finished partitioning")

def dedupe_bucket(
    bucket_path: str,
    deduped_path: str,
    bucket_index: int,
    hash_function: Optional[Callable[[str], int]] = None
) -> None:
    logging.info(
        f"Bucket #{bucket_index}: starting dedupe; memory before read: {get_memory_usage() / 1e6:.2f} MB"
    )
    with open(bucket_path, "r", buffering=1 << 20) as fin:
        lines = fin.readlines()
    logging.info(
        f"Bucket #{bucket_index}: read {len(lines)} lines; memory after read: {get_memory_usage() / 1e6:.2f} MB"
    )
    seen = HashMap(hash_function=hash_function)
    with open(deduped_path, "w", buffering=1 << 20) as fout:
        for idx, line in enumerate(lines, start=1):
            if seen.get(line) is None:
                seen.put(line, idx)
                fout.write(line)
    logging.info(
        f"Bucket #{bucket_index}: finished dedupe; "
        f"unique={seen.size}; memory after write: {get_memory_usage() / 1e6:.2f} MB"
    )


def dedupe_large_file(
    input_file: str,
    output_file: str,
    num_buckets: int = 100,
    hash_function: Optional[Callable[[str], int]] = None
) -> None:
    """
    remove duplicate lines from a large file by:
     1. partitioning into hash-based buckets.
     2. deduplicating each bucket in memory.
     3. merging the results.
    """
    output_dir = os.path.dirname(os.path.abspath(output_file)) or "."
    temp_root = os.path.join(output_dir, "temp_files")
    buckets_dir = os.path.join(temp_root, "buckets")
    deduped_dir = os.path.join(temp_root, "deduplicated")
    os.makedirs(deduped_dir, exist_ok=True)

    logging.info(f"Temporary files directory: {temp_root}")

    partition_file(input_file, buckets_dir, num_buckets)

    for i in range(num_buckets):
        b_in = os.path.join(buckets_dir, f"bucket_{i}.txt")
        b_out = os.path.join(deduped_dir, f"bucket_{i}.dedup.txt")
        dedupe_bucket(b_in, b_out, i, hash_function)

    logging.info("Merging deduplicated buckets...")
    with open(output_file, "w", buffering=1 << 20) as fout:
        for i in range(num_buckets):
            part_path = os.path.join(deduped_dir, f"bucket_{i}.dedup.txt")
            with open(part_path, "r", buffering=1 << 20) as fin:
                for line in fin:
                    fout.write(line)

    logging.info(f"Deduplicated output written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Remove duplicate lines from a large text file."
    )
    parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        type=str,
        help="Path to the large text file to deduplicate",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        required=True,
        type=str,
        help="Path where deduplicated lines will be written",
    )
    parser.add_argument(
        "-b",
        "--buckets",
        type=int,
        default=100,
        help="Number of hash buckets to use (more buckets → less RAM per bucket)",
    )
    args = parser.parse_args()

    if psutil is None:
        logging.warning(
            "psutil not installed; memory-logging disabled."
            " Install with `pip install psutil`."
        )

    dedupe_large_file(
        args.input_file,
        args.output_file,
        num_buckets=args.buckets,
    )
