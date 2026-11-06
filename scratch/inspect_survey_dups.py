import csv
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

path = Path('data/raw/google_form_sip_responses.csv')
with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
    reader = list(csv.reader(f))

headers = [h.strip() for h in reader[0]]
rows = reader[1:]

row_tuples = [tuple(c.strip() for c in r) for r in rows]
counts = Counter(row_tuples)
print('Total rows:', len(rows))
print('Unique rows:', len(counts))

print('\nIdentical-row occurrences:')
for r_tuple, count in counts.items():
    if count > 1:
        print(f'Count: {count}')
        print('  Q1:', r_tuple[0])
        print('  Q2:', r_tuple[1])
        print('  Q5 (SIP state):', r_tuple[4])
        print('  Q6 (Tenure):', r_tuple[5])
        print('  Q11 (Decision):', r_tuple[10])
