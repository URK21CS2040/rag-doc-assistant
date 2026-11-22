import fitz

doc = fitz.open('/app/data/uploads/software_engineering_post_eda_rag_test_report.pdf')
for p in [10, 11]:
    tabs = doc[p].find_tables()
    for tab in tabs:
        df = tab.extract()
        for row in df:
            if row and row[0] and row[0].startswith("Q"):
                q = " ".join((row[1] or "").split())
                a = " ".join((row[2] or "").split())
                print(f'{row[0]}: {q} -> {a}')

