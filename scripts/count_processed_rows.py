import csv, pathlib, collections
src = pathlib.Path('data/processed')
counts = {}
for p in src.glob('*.csv'):
    with open(p, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = [row for row in reader if row]
        # Filter out stock_sip asset_type (column index 1)
        filtered = [r for r in rows if len(r) > 1 and r[1] != 'stock_sip']
        counts[p.name] = len(filtered)
print('Processed file counts (excluding stock_sip):')
for name, cnt in counts.items():
    print(f"{name}: {cnt}")

