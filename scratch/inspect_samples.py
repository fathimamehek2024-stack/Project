import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Let's inspect some of the reviews to fine-tune our classification keywords
p_b1 = Path('data/processed/playstore_groww_reviews_batch1_cleaned.csv')
with open(p_b1, 'r', encoding='utf-8-sig') as f:
    b1_rows = list(csv.reader(f))[1:]

p_b2 = Path('data/processed/playstore_groww_reviews_batch2_cleaned.csv')
with open(p_b2, 'r', encoding='utf-8-sig') as f:
    b2_rows = list(csv.reader(f))[1:]

p_red = Path('data/processed/reddit_groww_concerns_cleaned.csv')
with open(p_red, 'r', encoding='utf-8-sig') as f:
    red_rows = list(csv.reader(f))[1:]

print('Batch 1 review samples (first 5):')
for r in b1_rows[:5]:
    print(' - ID:', r[0], 'Rating:', r[2], 'Text:', r[4][:80])

print('\nBatch 2 review samples (first 5):')
for r in b2_rows[:5]:
    print(' - ID:', r[0], 'Rating:', r[2], 'Text:', r[4][:80])

print('\nReddit samples (first 5):')
for r in red_rows[:5]:
    if r[6] not in ('[deleted]', '[removed]', ''):
        print(' - ID:', r[0], 'Text:', r[6][:80])
