import csv
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

# 1. Survey
survey_path = Path('data/processed/google_form_sip_responses_cleaned.csv')
with open(survey_path, 'r', encoding='utf-8-sig') as f:
    survey_rows = list(csv.reader(f))[1:]

active_investors = [r for r in survey_rows if r[2] == 'Yes']
print(f'Total Survey Rows: {len(survey_rows)}, Active Investors: {len(active_investors)}')

# 2. Play Store
ps1_path = Path('data/processed/playstore_groww_reviews_batch1_cleaned.csv')
with open(ps1_path, 'r', encoding='utf-8-sig') as f:
    ps1_rows = list(csv.reader(f))[1:]

ps2_path = Path('data/processed/playstore_groww_reviews_batch2_cleaned.csv')
with open(ps2_path, 'r', encoding='utf-8-sig') as f:
    ps2_rows = list(csv.reader(f))[1:]
print(f'Play Store Batch 1: {len(ps1_rows)}, Batch 2: {len(ps2_rows)}')

# 3. Reddit Concerns
red_path = Path('data/processed/reddit_groww_concerns_cleaned.csv')
with open(red_path, 'r', encoding='utf-8-sig') as f:
    red_rows = list(csv.reader(f))[1:]
valid_reddit = [r for r in red_rows if r[6].strip() not in ('[deleted]', '[removed]', '')]
print(f'Reddit Concerns: {len(red_rows)}, Valid Text: {len(valid_reddit)}')
