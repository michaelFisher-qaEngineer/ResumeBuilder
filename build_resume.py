import sys
import re

template = open("template.md").read()
summaries = open("summaries.md").read()
skills = open("skills.md").read()
blackrock = open("blackrock.md").read()
microsoft = open("microsoft.md").read()

summary_key = sys.argv[1]
skills_key = sys.argv[2]

summary = re.search(rf"\[{summary_key}\](.*?)\n\[", summaries, re.S)
if summary:
    summary = summary.group(1).strip()
else:
    summary = summaries.split(f"[{summary_key}]")[1].strip()

skills_section = re.search(rf"\[{skills_key}\](.*?)\n\[", skills, re.S)
if skills_section:
    skills_section = skills_section.group(1).strip()
else:
    skills_section = skills.split(f"[{skills_key}]")[1].strip()

resume = template.replace("{{SUMMARY}}", summary)
resume = resume.replace("{{SKILLS}}", skills_section)
resume = resume.replace("{{BLACKROCK}}", blackrock)
resume = resume.replace("{{MICROSOFT}}", microsoft)

with open("resume_generated.md", "w") as f:
    f.write(resume)

print("Resume markdown generated.")
