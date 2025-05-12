# Large-File Deduplication Script

A utility for removing duplicate lines from large text files (e.g., 50 GB+). It partitions the input into hash-based buckets, deduplicates each bucket in memory, then merges the results.

## Requirements

* Python 3.11+
* (Optional) [psutil](https://pypi.org/project/psutil/) for memory-usage logs:

  ```bash
  pip install psutil
  ```
* The `HashMap` class (imported from `HashMap.py` in the same directory).

No other external libraries are needed.

---

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:ranbm/backend-rebase.git
   ```
2. (Optional) Create and activate a virtual environment:

   ```bash
   python -m venv assignment1
   source assignment1/bin/activate
   ```
3. Install `psutil` if you want memory-usage logs:

   ```bash
   pip install psutil
   ```

---

## Usage

```bash
cd assignment_1
python assignment_1.py \
  -i /path/to/input.txt \
  -o /path/to/output.txt \
  -b 100
```

| Option              | Description                                                           | Default      |
| ------------------- | --------------------------------------------------------------------- |--------------|
| `-i, --input_file`  | Path to the large text file to deduplicate                            | **Required** |
| `-o, --output_file` | Path where deduplicated lines will be written                         | **Required** |
| `-b, --buckets`     | Number of hash buckets to use (more buckets → smaller per-bucket RAM) | `100`        |

---

## How It Works

1. **Partition** (`partition_file`):

   * Reads each line from the input.
   * Computes a fast CRC32 hash of the line.
   * Writes the line into one of the bucket files based on `crc32(line) % buckets`.

2. **Deduplicate** (`dedupe_bucket`):

   * For each bucket file, loads lines sequentially.
   * Uses a `HashMap` to track seen lines by hash.
   * Writes each unseen line to the deduplicated bucket file.

3. **Merge**:

   * Concatenates all deduplicated bucket files in order into the final output.

---
