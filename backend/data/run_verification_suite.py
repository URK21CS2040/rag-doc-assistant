import urllib.request
import json
import time

TEST_CASES = [
    {
        "id": "SQL-Q1",
        "question": "Can DDL statements be rolled back in PostgreSQL according to the documentation?",
        "expected_route": "generation",
        "expected_doc": "SQL Fundamentals Technical Reference.pdf",
        "expected_page": "2",
        "must_contain": ["transactional", "rollback", "begin"]
    },
    {
        "id": "SQL-Q2",
        "question": "What is the difference between RANK() and DENSE_RANK() window functions?",
        "expected_route": "generation",
        "expected_doc": "SQL Fundamentals Technical Reference.pdf",
        "expected_page": "7",
        "must_contain": ["gap", "rank"]
    },
    {
        "id": "SQL-Q3",
        "question": "Why does storing department_city in the employees table violate Third Normal Form (3NF)?",
        "expected_route": "generation",
        "expected_doc": "SQL Fundamentals Technical Reference.pdf",
        "expected_page": "9",
        "must_contain": ["transitive", "dependency"]
    },
    {
        "id": "SQL-Q4",
        "question": "How many rows are produced by a FULL OUTER JOIN between the employees and departments tables?",
        "expected_route": "generation",
        "expected_doc": "SQL Fundamentals Technical Reference.pdf",
        "expected_page": "6",
        "must_contain": ["8 rows", "8"]
    },
    {
        "id": "SQL-Q5",
        "question": "Why does the total departmental base payroll differ from the company-wide total base salary by $105,000?",
        "expected_route": "generation",
        "expected_doc": "SQL Fundamentals Technical Reference.pdf",
        "expected_page": "10",
        "must_contain": ["Marcus Vance", "NULL"]
    },
    {
        "id": "OUT-OF-DOC",
        "question": "Who won the 2024 ICC Men's T20 World Cup?",
        "expected_route": "web_search",
        "expected_doc": "[Web]",
        "expected_page": None,
        "must_contain": ["India"]
    }
]

print("Starting verification suite across all test cases...\n")

results = []
for tc in TEST_CASES:
    qid = tc["id"]
    q = tc["question"]
    print(f"[{qid}] Querying: '{q}'...")
    t0 = time.time()
    req = urllib.request.Request(
        "http://localhost:8000/query",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"question": q, "session_id": f"test_{qid}"}).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = round(time.time() - t0, 2)
        route = data.get("route", "")
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        src_docs = [s.get("document_id", "") for s in sources]
        
        # Check assertions
        route_ok = route == tc["expected_route"]
        src_ok = any(tc["expected_doc"] in s for s in src_docs)
        text_ok = any(m.lower() in answer.lower() for m in tc["must_contain"])
        
        status = "PASS" if (route_ok and src_ok and text_ok) else "FAIL"
        
        print(f"  Status: {status} ({elapsed}s)")
        print(f"  Route: {route} (Expected: {tc['expected_route']})")
        print(f"  Sources: {src_docs}")
        print(f"  Answer: {answer[:180].replace(chr(10), ' ')}")
        print()
        results.append({
            "id": qid,
            "status": status,
            "route": route,
            "sources": src_docs,
            "answer": answer,
            "latency": elapsed
        })
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"  Status: ERROR ({elapsed}s): {e}\n")
        results.append({
            "id": qid,
            "status": "ERROR",
            "error": str(e),
            "latency": elapsed
        })
    time.sleep(1.0)

print("=" * 60)
print(f"SUMMARY: {sum(1 for r in results if r['status'] == 'PASS')} / {len(results)} Passed")
print("=" * 60)
