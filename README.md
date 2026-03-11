# Resume Builder

A lightweight Python-based resume and cover letter generator for tailoring application materials to a specific job description.

This project builds customized resume and cover letter outputs by mixing and matching reusable content blocks such as summary variants, skills sections, and experience bullets. It can also infer a company name and role from a pasted job description, choose an appropriate resume profile, and export polished PDFs using Pandoc + WeasyPrint.

**Note**
This repo was built for my own resume/job-search workflow, so parts of it are intentionally personalized. That said, the underlying setup is reusable: swap in your own content files, update the script logic to match your background, and it should be pretty straightforward to adapt.

## Features

- Generate resumes from reusable markdown content blocks
- Select different summary and skills profiles depending on the role
- Paste in a job description and let the script:
  - infer company and role
  - choose a best-fit resume variant
  - flag possible poor-fit jobs before generating
- Generate both:
  - tailored resume markdown + PDF
  - tailored cover letter markdown + PDF
- Maintain a local application log for personal job search tracking

## Project Structure

```text
.
├── build_resume.py            # Simple block-based resume builder
├── build_from_jd.py           # Main job-description-driven generator
├── build_from_clipboard.py    # macOS helper: reads JD from clipboard
├── template.md                # Resume template
├── cover_template.md          # Cover letter template
├── summaries.md               # Reusable summary blocks
├── skills.md                  # Reusable skills blocks
├── blackrock.md               # Experience bullets
├── microsoft.md               # Experience bullets
├── resume.css                 # PDF styling
├── jd.txt                     # Optional local JD input file
└── applications_log.csv       # Local output tracking (should stay private)
```

## How It Works

The generator uses a modular content approach:

- `summaries.md` stores multiple summary variants such as:
  - `AUTOMATION`
  - `BALANCED`
  - `FUNCTIONAL`
- `skills.md` stores multiple skills-section variants
- `template.md` combines those blocks with fixed experience sections
- `build_from_jd.py` scans a job description for keywords and chooses the most relevant summary/skills combination

It then writes:

- resume markdown
- cover letter markdown
- resume PDF
- cover letter PDF
- local run log
- optional CSV application log entry

## Requirements

- Python 3.10+
- [Pandoc](https://pandoc.org/)
- WeasyPrint

You’ll also need any native dependencies required by WeasyPrint on your OS.

## Installation

Clone the repo:

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

Install Pandoc and WeasyPrint.

Example Python package install:

```bash
pip install weasyprint
```

## Usage

### 1. Generate from an existing JD file

If `jd.txt` exists in the project root:

```bash
python3 build_from_jd.py
```

Or pass a specific file:

```bash
python3 build_from_jd.py path/to/job_description.txt
```

### 2. Override the auto-selected profile

You can manually choose summary and skills variants:

```bash
python3 build_from_jd.py --summary automation --skills automation jd.txt
```

Available summary profiles:

- `automation`
- `balanced`
- `functional`

Available skills profiles:

- `automation`
- `functional`
- `modern`
- `api`

### 3. Skip interactive fit prompts

```bash
python3 build_from_jd.py --no-ask jd.txt
```

### 4. Generate from clipboard (macOS)

This helper reads the current clipboard contents using `pbpaste`:

```bash
python3 build_from_clipboard.py
```

## Simple Resume Build

For a simpler block-based resume generation flow:

```bash
python3 build_resume.py AUTOMATION AUTOMATION
```

This writes:

```text
resume_generated.md
```

## Output

Typical generated files include:

- `candidate_resume_<role>_<company>_<date>.md`
- `candidate_resume_<role>_<company>_<date>.pdf`
- `candidate_cover_<company>_<date>.md`
- `candidate_cover_<company>_<date>.pdf`
- `LOG_<company>_<role>_<timestamp>.txt`

## Fit Checks

`build_from_jd.py` includes lightweight guardrails to detect roles that may be a poor match, such as:

- heavily manual-only QA roles
- Python-only or C#-only roles
- framework-from-scratch / architect-level expectations
- clearance-heavy roles
- strong timezone restrictions

These checks are only heuristics, but they can help avoid generating materials for roles that are likely outside your target range.

## Customization

You can tailor this repo by editing:

- `summaries.md` for alternate summary styles
- `skills.md` for different skills emphasis
- `blackrock.md` / `microsoft.md` for experience bullet libraries
- `template.md` for resume layout
- `cover_template.md` for cover letter format
- `resume.css` for PDF styling


## Future Improvements

Possible next steps:

- add a config file for personal details
- separate reusable content into a `content/` directory
- support Windows/Linux clipboard input
- add tests for keyword matching and block extraction
- add a dry-run mode
- generate generic filenames not tied to a real identity

## License

Add a license if you plan to share or reuse this publicly.