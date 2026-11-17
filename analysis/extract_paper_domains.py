"""Extract the 20-domain label per task from Table 5 of the SWE-bench Science paper.

Input: text produced by `pdftotext -layout -f 16 -l 24 <paper.pdf> table5.txt`.
Output: analysis/data/paper-domains.csv (task, paper_domain), checked against Table 4 counts.
Usage: python -I analysis/extract_paper_domains.py table5.txt analysis/data/paper-domains.csv
The paper (arXiv 2608.19799v2) is CC BY 4.0; the labels are reproduced with attribution (NOTICE.md).
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

FIRST_WORD = {
    "Chemistry": "Chemistry", "Materials": "Materials Science and Engineering", "Biology": "Biology",
    "Biomedical": "Biomedical Engineering", "Physics": "Physics", "Mathematics": "Mathematics",
    "Astronomy": "Astronomy", "Atmospheric": "Atmospheric Science", "Civil": "Civil Engineering",
    "Surveying": "Surveying and Mapping Science and Technology", "Geophysics": "Geophysics",
    "Mechanics": "Mechanics", "Electrical": "Electrical Engineering", "Marine": "Marine Science",
    "Geography": "Geography", "Aeronautical": "Aeronautical and Astronautical Science and Technology",
    "Nuclear": "Nuclear Science and Technology", "Computer": "Computer Science and Technology",
    "Statistics": "Statistics", "Information": "Information and Communication Engineering",
}
TABLE4 = {
    "Chemistry": 24, "Materials Science and Engineering": 16, "Biology": 13, "Biomedical Engineering": 12,
    "Physics": 11, "Mathematics": 7, "Astronomy": 7, "Atmospheric Science": 5, "Civil Engineering": 5,
    "Surveying and Mapping Science and Technology": 3, "Geophysics": 3, "Mechanics": 3,
    "Electrical Engineering": 2, "Marine Science": 2, "Geography": 1,
    "Aeronautical and Astronautical Science and Technology": 1, "Nuclear Science and Technology": 1,
    "Computer Science and Technology": 1, "Statistics": 1, "Information and Communication Engineering": 1,
}


def main(text_path: str, out_path: str) -> None:
    rows = {}
    for line in Path(text_path).read_text().splitlines():
        m = re.match(r"^\s{0,8}(\d{3})\s+([A-Z][a-z]+)", line)
        if m and 1 <= int(m.group(1)) <= 119 and m.group(2) in FIRST_WORD:
            rows.setdefault(m.group(1), FIRST_WORD[m.group(2)])
    missing = [f"{i:03d}" for i in range(1, 120) if f"{i:03d}" not in rows]
    counts = Counter(rows.values())
    mismatch = {d: (counts.get(d, 0), n) for d, n in TABLE4.items() if counts.get(d, 0) != n}
    print(f"parsed {len(rows)} tasks; missing {missing}; Table 4 mismatches {mismatch}")
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["task", "paper_domain"])
        for t in sorted(rows):
            w.writerow([t, rows[t]])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
