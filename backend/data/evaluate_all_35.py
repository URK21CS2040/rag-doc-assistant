import urllib.request
import json
import time

QUESTIONS = [
    ("Q01", "What is the project name?", "Engineering Delivery and Defect Analytics (EDDA)"),
    ("Q02", "How many raw work-item observations were collected?", "12,000"),
    ("Q03", "How many repositories are represented?", "24"),
    ("Q04", "How many engineering teams are represented?", "8"),
    ("Q05", "What is the prediction target?", "production_defect_within_30d"),
    ("Q06", "What does a positive target label mean?", "linked production defect recorded within 30 days after release"),
    ("Q07", "How many rows remain after cleaning?", "11,760"),
    ("Q08", "How many positive labels are in the cleaned dataset?", "1,176"),
    ("Q09", "What is the positive target prevalence?", "10.0%"),
    ("Q10", "What is the selected model?", "Gradient Boosting (GradientBoostingClassifier)"),
    ("Q11", "What is the selected probability threshold?", "0.34"),
    ("Q12", "How many estimators are configured?", "160"),
    ("Q13", "What learning rate is configured?", "0.05"),
    ("Q14", "What is the maximum tree depth?", "3"),
    ("Q15", "What is the test ROC-AUC?", "0.88"),
    ("Q16", "What are the test precision and recall?", "Precision is 0.82 and recall is 0.68"),
    ("Q17", "What is the median lead time?", "3.8 days"),
    ("Q18", "What is the automated test pass rate?", "94.2%"),
    ("Q19", "How many linked production defect incidents were recorded?", "138"),
    ("Q20", "What threshold defines a large change?", "More than 300 total changed lines"),
    ("Q21", "How many negative labels are in the cleaned dataset?", "10,584"),
    ("Q22", "How many rows are in the test partition?", "1,764"),
    ("Q23", "How many true positives and false negatives appear in the test confusion matrix?", "120 true positives and 56 false negatives"),
    ("Q24", "Why is accuracy alone insufficient for this dataset?", "target is imbalanced: 90% records negative"),
    ("Q25", "Why are the 1,176 positive work items not the same as 138 production incidents?", "target assigned per work item while incidents counted separately"),
    ("Q26", "Which threshold was selected and what trade-off does it represent?", "0.34; balances alert precision and defect detection"),
    ("Q27", "What is the difference between code coverage and test pass rate?", "coverage measures proportion of code; pass rate measures passed test executions"),
    ("Q28", "Which features are derived from lines added and lines deleted?", "change_size = lines_added + lines_deleted"),
    ("Q29", "How is test_failure_rate calculated?", "test_failures divided by test_cases_run"),
    ("Q30", "What is the recommended use of model predictions?", "prioritize human review and targeted testing; do not automatically approve/reject"),
    ("Q31", "Which cloud provider hosts the CI platform?", "abstain: not specified in report"),
    ("Q32", "What is the name of the production database?", "abstain: not specified in report"),
    ("Q33", "Which programming language is used by the application?", "abstain: not specified in report"),
    ("Q34", "What is the annual engineering budget?", "abstain: not specified in report"),
    ("Q35", "What is the name of the company that owns the repositories?", "abstain: synthetic data / not specified")
]

def query_endpoint(question: str):
    req = urllib.request.Request(
        "http://localhost:8000/query",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"question": question}).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))

results = []
print(f"Starting test evaluation of all {len(QUESTIONS)} questions...\n")

for qid, qtext, expected in QUESTIONS:
    t0 = time.time()
    try:
        data = query_endpoint(qtext)
        elapsed = round(time.time() - t0, 2)
        answer = data.get("answer", "")
        route = data.get("route", "")
        sources = data.get("sources", [])
        is_failed = "AI model unavailable" in answer
        src_pages = [s.get("document_id", "") for s in sources]
        
        status = "FAIL (Unavailable)" if is_failed else "PASS"
        results.append({
            "qid": qid,
            "question": qtext,
            "expected": expected,
            "answer": answer,
            "route": route,
            "status": status,
            "sources": src_pages,
            "latency": elapsed
        })
        print(f"[{qid}] {status} in {elapsed}s | Route: {route} | Ans: {answer[:90].replace(chr(10), ' ')}")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"[{qid}] ERROR in {elapsed}s: {e}")
        results.append({
            "qid": qid,
            "question": qtext,
            "expected": expected,
            "answer": f"HTTP/Network Error: {e}",
            "route": "error",
            "status": "ERROR",
            "sources": [],
            "latency": elapsed
        })
    time.sleep(1.0) # small pause to keep well under TPM limits

with open("/app/data/eval_35_results.json", "w") as f:
    json.dump(results, f, indent=2)

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] != "PASS")
print(f"\n==========================================")
print(f"EVALUATION SUMMARY: Total={len(results)}, Passed={passed}, Failed={failed}")
print(f"==========================================")

