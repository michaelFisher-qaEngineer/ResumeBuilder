import re
import subprocess
import csv
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# ----------------------------
# Config: your variant keys
# ----------------------------
SUMMARY_KEYS = {
    "AUTOMATION": "AUTOMATION",
    "BALANCED": "BALANCED",
    "FUNCTIONAL": "FUNCTIONAL",
}

SKILLS_KEYS = {
    "AUTOMATION": "AUTOMATION",
    "FUNCTIONAL": "FUNCTIONAL",
    "MODERN": "MODERN",
}

VALID_SUMMARY_PROFILES = {"automation", "balanced", "functional"}
VALID_SKILLS_PROFILES = {"automation", "functional", "modern", "api"}

SUMMARY_PROFILE_MAP = {
    "automation": "AUTOMATION",
    "balanced": "BALANCED",
    "functional": "FUNCTIONAL",
}

SKILLS_PROFILE_MAP = {
    "automation": "AUTOMATION",
    "functional": "FUNCTIONAL",
    "modern": "MODERN",
    "api": "AUTOMATION",   # maps api -> existing AUTOMATION skills block
}

DEFAULT_SUMMARY = "BALANCED"
DEFAULT_SKILLS = "AUTOMATION"

# Keywords to influence selection (simple + editable)
AUTOMATION_HINTS = [
    "automation", "selenium", "cypress", "playwright", "framework", "ci/cd", "pipeline",
    "jenkins", "github actions", "gitlab", "circleci", "testng", "junit", "cucumber",
    "rest-assured", "postman", "api", "microservices", "regression suite"
]

FUNCTIONAL_HINTS = [
    "manual", "exploratory", "uat", "test plans", "test cases", "defect triage",
    "accessibility", "documentation", "stakeholder", "reporting", "metrics", "test strategy"
]

MODERN_WEB_HINTS = [
    "typescript", "javascript", "react", "next.js", "node", "frontend", "browser devtools"
]

FRAMEWORK_OWNERSHIP_HINTS = [
    "architect", "architecture", "own the framework", "build framework from scratch",
    "tooling decisions", "staff", "principal"
]

# ----------------------------
# Helpers
# ----------------------------
def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_tag_value(text: str, tag: str, default: str) -> str:
    """
    Optional: allow putting these lines at top of JD file:
      COMPANY: Acorns
      ROLE: Senior QA Engineer
    """
    m = re.search(rf"^\s*{tag}\s*:\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def score_keywords(text: str, keywords: list[str]) -> int:
    t = text.lower()
    score = 0
    for kw in keywords:
        if kw in t:
            score += 1
    return score


def choose_variants(jd_text: str) -> tuple[str, str, str]:
    """
    Returns (summary_key, skills_key, confidence_note)
    """
    t = jd_text.lower()

    auto = score_keywords(jd_text, AUTOMATION_HINTS)
    func = score_keywords(jd_text, FUNCTIONAL_HINTS)
    web = score_keywords(jd_text, MODERN_WEB_HINTS)
    framework_own = score_keywords(jd_text, FRAMEWORK_OWNERSHIP_HINTS)

    # Extra lightweight signals
    pythonish = ("python" in t) or ("pytest" in t)
    csharpish = ("c#" in t) or (".net" in t) or ("specflow" in t) or ("reqnroll" in t)
    javaish = "java" in t
    js_tsish = (
        ("javascript" in t) or ("typescript" in t) or ("node" in t)
        or ("cypress" in t) or ("playwright" in t)
    )

    manualish = (
        ("manual testing" in t) or ("uat" in t) or ("test executor" in t)
        or ("execute test cases" in t)
    )

    flags = []

    if framework_own >= 2 and auto >= 4:
        flags.append("framework-ownership heavy (review fit)")

    if func >= auto + 2 and manualish:
        flags.append("manual-heavy leaning JD (review fit)")

    if pythonish and not (javaish or js_tsish):
        flags.append("possible Python-only JD (review fit)")
    if csharpish and not (javaish or js_tsish):
        flags.append("possible C#/.NET-only JD (review fit)")

    confidence = "OK" if not flags else "FLAG: " + "; ".join(flags)

    if auto >= func + 2:
        summary = "AUTOMATION"
        skills = "AUTOMATION"
        if web >= 2 and ("cypress" in t or "playwright" in t):
            skills = "MODERN"
        return summary, skills, confidence

    if func > auto:
        return "BALANCED", "FUNCTIONAL", confidence

    return DEFAULT_SUMMARY, DEFAULT_SKILLS, confidence


def pull_block(library_text: str, key: str) -> str:
    """
    Expects blocks like:
    [AUTOMATION]
    ...content...

    [BALANCED]
    ...content...
    """
    pattern = re.compile(rf"\[{re.escape(key)}\]\s*(.*?)(?=\n\[[A-Z0-9_]+\]\s*|\Z)", re.S)
    m = pattern.search(library_text)
    if not m:
        raise ValueError(f"Could not find block [{key}] in library file.")
    return m.group(1).strip()


def safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def infer_role(jd_text: str) -> str | None:
    m = re.search(r"^\s*Job\s*Title\s*:\s*(.+?)\s*$", jd_text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip()

    m = re.search(r"^\s*([A-Z][^\n|]{6,80})\s*\|\s*[A-Z].+$", jd_text, re.MULTILINE)
    if m:
        return m.group(1).strip()

    m = re.search(r"\bseeking\s+(?:an|a)\s+([A-Z][A-Za-z0-9 /&()\-]{6,80})", jd_text)
    if m:
        return m.group(1).strip()

    m = re.search(r"\bAs\s+(?:an|a)\s+([A-Z][A-Za-z0-9 /&()\-]{6,80})\s*,\s+you\s+will\b", jd_text)
    if m:
        return m.group(1).strip()

    return None


def infer_company(jd_text: str) -> str | None:
    m = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{2,50})\b", jd_text)
    if m:
        candidate = m.group(1).strip()
        if not candidate.lower().startswith("least"):
            return candidate

    m = re.search(
        r"\b([A-Z][A-Za-z0-9&.\- ]{2,50})\s+(?:is|are)\s+(?:seeking|hiring|looking)\b",
        jd_text
    )
    if m:
        return m.group(1).strip()

    m = re.search(r"^\s*About\s+([A-Z][A-Za-z0-9&.\- ]{2,50})\s*$", jd_text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip()

    m = re.search(r"^\s*Company\s*:\s*(.+?)\s*$", jd_text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip()

    return None


def confirm_value(label: str, value: str, default: str) -> str:
    if not value:
        value = default

    user_input = input(f"{label} detected as '{value}'. Press Enter to accept or type a new value: ").strip()

    if user_input:
        return user_input

    return value


def read_jd_from_terminal():
    print("\nPaste the Job Description.")
    print("When finished, type 'EOF' on a new line and press Enter.\n")

    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip() == "EOF":
            break

        lines.append(line)

    return "\n".join(lines)


SKIP_RULES = [
    ("timezone_restriction", r"\b(EST|CST)\b.*\bonly\b|\b(Eastern|Central)\s*time\s*zone\b", 3,
     "Time-zone restricted (EST/CST-only)."),

    ("clearance_public_trust", r"\b(public trust|clearance)\b", 3,
     "Public Trust / clearance mentioned."),

    ("framework_from_scratch", r"\b(from scratch|architect|architecture|own(ing)?\s+the\s+framework|build.*framework)\b", 2,
     "Heavy framework ownership / architecture language."),

    ("staff_principal", r"\b(staff|principal)\b", 2,
     "Senior level (Staff/Principal) wording."),

    ("typescript_primary", r"\b(TypeScript)\b.*\b(must|required|primary|strongly preferred)\b", 2,
     "TypeScript emphasized as primary/required."),

    ("csharp_primary", r"\b(C#)\b.*\b(must|required|strongly preferred)\b", 2,
     "C# emphasized as primary/required."),

    ("mobile_native_required", r"\b(Kotlin|Espresso|Swift|XCUITest|XCUI)\b", 2,
     "Native mobile automation (Kotlin/Swift) appears required."),

    ("healthcare_reg_standards", r"\b(HIPAA|HL7|X12|FHIR|21\s*CFR\s*Part\s*11)\b", 2,
     "Regulated healthcare standards emphasized (possible stretch unless you have domain)."),
]

FIT_BONUS_RULES = [
    ("java_selenium", r"\b(Java)\b.*\b(Selenium|TestNG|JUnit|Cucumber)\b|\b(Selenium)\b.*\b(Java)\b", -2,
     "Java + Selenium stack match."),
    ("api_postman_sql", r"\b(Postman)\b|\b(REST|API)\b|\bSQL\b", -2,
     "API/Postman/SQL match."),
    ("ci_cd", r"\b(Jenkins|Azure DevOps|GitHub Actions|GitLab CI|CI/CD)\b", -1,
     "CI/CD match."),
    ("cypress_playwright", r"\b(Cypress|Playwright)\b", -1,
     "Modern web automation match."),
]


def assess_fit(jd_text: str) -> tuple[bool, int, list[str]]:
    t = jd_text
    score = 0
    reasons = []

    for _, pattern, pts, reason in SKIP_RULES:
        if re.search(pattern, t, re.IGNORECASE):
            score += pts
            reasons.append(reason)

    for _, pattern, pts, _ in FIT_BONUS_RULES:
        if re.search(pattern, t, re.IGNORECASE):
            score += pts

    should_prompt = score >= 3
    return should_prompt, score, reasons


def confirm_continue_fit(score: int, reasons: list[str]) -> bool:
    print("\nFIT CHECK: This may be a stretch.")
    print(f"Risk score: {score}")
    if reasons:
        for r in reasons[:6]:
            print(f"- {r}")
    ans = input("Continue anyway? (y/N): ").strip().lower()
    return ans == "y"


def derive_blackrock_overlay(jd_text: str) -> str:
    t = jd_text.lower()

    if "performance" in t or "load testing" in t or "jmeter" in t:
        return "- CollabPartnered with engineering teams to assess application behavior under load and build practical experience with JMeter performance testing."

    if "accessibility" in t or "wcag" in t:
        return "- Supported accessibility validation efforts by evaluating UI behavior and identifying usability and accessibility gaps."

    if "mobile" in t or "cross-browser" in t:
        return "- Validated cross-browser application behavior across modern browser environments to ensure consistent user experience."

    return ""


def clean_filename(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text)
    text = text.strip().replace(" ", "_")
    return text


@dataclass
class GateResult:
    ok: bool
    prompt: bool
    reason: str
    notes: list[str]


def _count_hits(text: str, terms: list[str]) -> int:
    t = text.lower()
    return sum(1 for term in terms if term in t)


def evaluate_job_gate(jd_text: str) -> GateResult:
    t = jd_text.lower()

    automation_terms = [
        "automation", "automated", "selenium", "cypress", "playwright", "restassured",
        "testng", "junit", "framework", "ci/cd", "pipeline", "jenkins", "github actions",
        "api testing", "rest api", "microservices"
    ]
    manual_terms = [
        "manual testing", "manual tester", "uat", "test executor", "execute test cases",
        "test case execution", "test scripts", "regression testing", "functional testing",
        "test plan", "test documentation", "testrail", "zephyr", "qtest"
    ]

    python_only_terms = ["python", "pytest", "robot framework"]
    java_terms = ["java", "spring", "testng", "junit", "restassured", "rest assured"]
    csharp_terms = ["c#", ".net", "specflow", "reqnroll"]
    js_ts_terms = ["javascript", "typescript", "node", "cypress", "playwright"]

    must_python = bool(re.search(r"\b(must have|required)\b.*\bpython\b", t))
    must_csharp = bool(re.search(r"\b(must have|required)\b.*\b(c#|\.net|specflow|reqnroll)\b", t))
    must_java = bool(re.search(r"\b(must have|required)\b.*\bjava\b", t))

    build_framework_terms = [
        "build.*framework", "framework from scratch", "architect.*framework",
        "design.*framework", "create.*framework"
    ]
    framework_from_scratch = any(re.search(pat, t) for pat in build_framework_terms)

    auto_hits = _count_hits(t, automation_terms)
    manual_hits = _count_hits(t, manual_terms)

    python_hits = _count_hits(t, python_only_terms)
    java_hits = _count_hits(t, java_terms)
    csharp_hits = _count_hits(t, csharp_terms)
    js_hits = _count_hits(t, js_ts_terms)

    notes = []
    notes.append(f"automation_hits={auto_hits}")
    notes.append(f"manual_hits={manual_hits}")
    notes.append(f"lang_hits: java={java_hits}, js/ts={js_hits}, python={python_hits}, c#={csharp_hits}")
    if framework_from_scratch:
        notes.append("framework_from_scratch_signal=YES")
    if must_java:
        notes.append("must_java_signal=YES")

    if must_python and java_hits == 0 and js_hits == 0:
        return GateResult(
            ok=False, prompt=True,
            reason="JD looks Python-required with no Java/JS/TS signal. Prompt before generating.",
            notes=notes
        )

    if must_csharp and java_hits == 0 and js_hits == 0:
        return GateResult(
            ok=False, prompt=True,
            reason="JD looks C#/.NET-required with no Java/JS/TS signal. Prompt before generating.",
            notes=notes
        )

    if manual_hits >= 6 and auto_hits <= 2:
        return GateResult(
            ok=False, prompt=True,
            reason="JD appears heavily manual/test-execution oriented (manual high, automation low). Prompt before generating.",
            notes=notes
        )

    if framework_from_scratch:
        return GateResult(
            ok=False, prompt=True,
            reason="JD emphasizes building/architecting a framework (from scratch). Prompt before generating.",
            notes=notes
        )

    return GateResult(ok=True, prompt=False, reason="Pass", notes=notes)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", choices=sorted(VALID_SUMMARY_PROFILES))
    parser.add_argument("--skills", choices=sorted(VALID_SKILLS_PROFILES))
    parser.add_argument("--no-ask", action="store_true")
    parser.add_argument("jd_file", nargs="?", help="Optional path to a JD text file")
    return parser.parse_args()


# ----------------------------
# Main
# ----------------------------
def main():
    args = parse_args()
    jd_text = ""

    if args.jd_file:
        jd_path = Path(args.jd_file).expanduser().resolve()
    elif Path("jd.txt").exists():
        jd_path = Path("jd.txt").resolve()
    else:
        jd_path = None

    if jd_path:
        if not jd_path.exists():
            print(f"JD file not found: {jd_path}")
            raise SystemExit(2)
        jd_text = read_file(jd_path)
    else:
        jd_text = read_jd_from_terminal()

    if not jd_text.strip():
        print("No JD text provided.")
        raise SystemExit(2)

    gate = evaluate_job_gate(jd_text)

    if gate.prompt and not args.no_ask:
        print("\n=== JD FIT CHECK (needs your call) ===")
        print(gate.reason)
        for n in gate.notes:
            print(" -", n)

        ans = input("Generate anyway? (y/N): ").strip().lower()
        if ans not in ("y", "yes"):
            print("SKIPPED")
            raise SystemExit(0)

    should_prompt, score, reasons = assess_fit(jd_text)

    if should_prompt and not args.no_ask:
        if not confirm_continue_fit(score, reasons):
            print("SKIPPED (per fit check).")
            raise SystemExit(0)

    company = extract_tag_value(jd_text, "COMPANY", "")
    role = extract_tag_value(jd_text, "ROLE", "")

    if not company:
        company = infer_company(jd_text)
    if not role:
        role = infer_role(jd_text)

    company = confirm_value("Company", company, "TargetCompany")
    role = confirm_value("Role", role, "QA Automation Engineer")

    summary_key, skills_key, note = choose_variants(jd_text)

    if args.summary:
        summary_key = SUMMARY_PROFILE_MAP[args.summary]

    if args.skills:
        skills_key = SKILLS_PROFILE_MAP[args.skills]

    override_bits = []
    if args.summary:
        override_bits.append(f"summary override={summary_key}")
    if args.skills:
        override_bits.append(f"skills override={skills_key}")
    if override_bits:
        note = f"{note} | " + "; ".join(override_bits)

    template = read_file(Path("template.md"))
    cover_template = read_file(Path("cover_template.md"))
    summaries = read_file(Path("summaries.md"))
    skills = read_file(Path("skills.md"))
    blackrock = read_file(Path("blackrock.md"))
    microsoft = read_file(Path("microsoft.md"))

    summary_text = pull_block(summaries, SUMMARY_KEYS[summary_key])
    skills_text = pull_block(skills, SKILLS_KEYS[skills_key])

    overlay_bullet = derive_blackrock_overlay(jd_text)

    blackrock_section = blackrock.strip()
    if overlay_bullet:
        blackrock_section = blackrock_section + "\n" + overlay_bullet

    resume_md = template
    resume_md = resume_md.replace("{{SUMMARY}}", summary_text)
    resume_md = resume_md.replace("{{SKILLS}}", skills_text)
    resume_md = resume_md.replace("{{BLACKROCK}}", blackrock_section)
    resume_md = resume_md.replace("{{MICROSOFT}}", microsoft.strip())

    cover_md = cover_template
    cover_md = cover_md.replace("{{COMPANY}}", company)
    cover_md = cover_md.replace("{{ROLE}}", role)

    stamp = datetime.now().strftime("%Y%m%d")
    time_stamp = datetime.now().strftime("%H%M%S")

    role_clean = clean_filename(role)
    company_clean = clean_filename(company)

    resume_base = f"Michael_Fisher_{role_clean}_{company_clean}_{stamp}"
    cover_base = f"Michael_Fisher_Cover_{company_clean}_{stamp}"

    resume_md_path = Path(f"{resume_base}.md")
    resume_pdf_path = Path(f"{resume_base}.pdf")
    cover_md_path = Path(f"{cover_base}.md")
    cover_pdf_path = Path(f"{cover_base}.pdf")

    log_path = Path(f"LOG_{company_clean}_{role_clean}_{stamp}_{time_stamp}.txt")
    csv_log_path = Path("applications_log.csv")

    resume_md_path.write_text(resume_md, encoding="utf-8")
    cover_md_path.write_text(cover_md, encoding="utf-8")

    css_path = Path("resume.css").resolve()

    if not css_path.exists():
        print("Warning: resume.css not found; PDF will be generated without CSS.")
        css_args = []
    else:
        css_args = [f"--css={str(css_path)}"]

    run([
        "pandoc",
        str(resume_md_path),
        "-o", str(resume_pdf_path),
        *css_args,
        "--pdf-engine=weasyprint",
    ])

    run([
        "pandoc",
        str(cover_md_path),
        "-o", str(cover_pdf_path),
        *css_args,
        "--pdf-engine=weasyprint",
    ])

    log_contents = f"""Run Timestamp: {datetime.now().isoformat(timespec='seconds')}
Company: {company}
Role: {role}
Selected Summary: {summary_key}
Selected Skills: {skills_key}
Fit Note: {note}
Resume Markdown: {resume_md_path}
Resume PDF: {resume_pdf_path}
Cover Markdown: {cover_md_path}
Cover PDF: {cover_pdf_path}
"""

    log_path.write_text(log_contents, encoding="utf-8")

    csv_exists = csv_log_path.exists()

    with open(csv_log_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        if not csv_exists:
            writer.writerow([
                "timestamp",
                "company",
                "role",
                "summary_used",
                "skills_used",
                "fit_note",
                "resume_md",
                "resume_pdf",
                "cover_md",
                "cover_pdf",
                "run_log"
            ])

        writer.writerow([
            datetime.now().isoformat(timespec='seconds'),
            company,
            role,
            summary_key,
            skills_key,
            note,
            str(resume_md_path),
            str(resume_pdf_path),
            str(cover_md_path),
            str(cover_pdf_path),
            str(log_path)
        ])

    print("DONE")
    print(f"Selected SUMMARY: {summary_key}")
    print(f"Selected SKILLS:  {skills_key}")
    print(f"Note: {note}")
    print(f"MD:  {resume_md_path}")
    print(f"PDF: {resume_pdf_path}")
    print(f"MD:  {cover_md_path}")
    print(f"PDF: {cover_pdf_path}")
    print(f"LOG: {log_path}")
    print(f"CSV: {csv_log_path}")


if __name__ == "__main__":
    main()