import csv
import json
import pathlib
from collections import Counter

# Paths
classified_path = pathlib.Path('data/exports/classified_mutual_fund_feedback.csv')
corpus_path = pathlib.Path('web/data/corpus.json')

# Load classified CSV
source_counts = Counter()
asset_counts = Counter()
classified_ids = set()
with classified_path.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        source_counts[row['source']] += 1
        asset_counts[row['asset_type']] += 1
        classified_ids.add(row['record_id'])

# Load corpus JSON (ignore decode errors)
with corpus_path.open(encoding='utf-8', errors='ignore') as f:
    corpus_data = json.load(f)
corpus_ids = {item['feedback_id'] for item in corpus_data}
corpus_source_counts = Counter(item['source'] for item in corpus_data)

# Compute differences
only_in_classified = classified_ids - corpus_ids
only_in_corpus = corpus_ids - classified_ids

print('--- Classified CSV source counts ---')
for src, cnt in source_counts.items():
    print(f'{src}: {cnt}')
print('\n--- Classified CSV asset_type counts ---')
for at, cnt in asset_counts.items():
    print(f'{at}: {cnt}')
print('\n--- Corpus source counts ---')
for src, cnt in corpus_source_counts.items():
    print(f'{src}: {cnt}')
print('\n--- IDs only in classified CSV (not in corpus) ---')
for id_ in sorted(only_in_classified)[:20]:
    print(id_)
print(f'... and {len(only_in_classified)-20} more' if len(only_in_classified)>20 else '')
print('\n--- IDs only in corpus (not in classified CSV) ---')
for id_ in sorted(only_in_corpus)[:20]:
    print(id_)
print(f'... and {len(only_in_corpus)-20} more' if len(only_in_corpus)>20 else '')

