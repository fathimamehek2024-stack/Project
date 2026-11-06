"""Prototype for theme classifier to test accuracy and theme distributions."""
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Run prototype test on playstore and reddit to check distribution
p_b1 = Path('data/processed/playstore_groww_reviews_batch1_cleaned.csv')
with open(p_b1, 'r', encoding='utf-8-sig') as f:
    b1_rows = list(csv.reader(f))[1:]

p_b2 = Path('data/processed/playstore_groww_reviews_batch2_cleaned.csv')
with open(p_b2, 'r', encoding='utf-8-sig') as f:
    b2_rows = list(csv.reader(f))[1:]

p_red = Path('data/processed/reddit_groww_concerns_cleaned.csv')
with open(p_red, 'r', encoding='utf-8-sig') as f:
    red_rows = list(csv.reader(f))[1:]

valid_red = [r for r in red_rows if r[6].strip() not in ('[deleted]', '[removed]', '')]

print(f'Batch 1 reviews: {len(b1_rows)}')
print(f'Batch 2 reviews: {len(b2_rows)}')
print(f'Valid Reddit comments: {len(valid_red)}')
