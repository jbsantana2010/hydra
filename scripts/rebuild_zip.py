"""Sprint 2.7 — Rebuild delivery ZIP with correct filename + START_HERE.txt."""
import sys
import zipfile
from pathlib import Path

PROD = Path('/app/products/product_43')
ZIP_OUT = PROD / 'Real_Estate_AI_Mastery_Kit.zip'

# Write START_HERE.txt
start_here = PROD / 'START_HERE.txt'
start_here.write_text("""\
====================================================
  REAL ESTATE AI MASTERY KIT — 2026 EDITION
  Reading Guide & Quick Start
====================================================

Thank you for your purchase. This kit contains 8 professional
documents covering AI implementation for real estate agents.

RECOMMENDED READING ORDER
--------------------------
00 Quick Start Guide           Start here. Your first AI win in 30 min.
01 AI Tools Setup Guide        Set up ChatGPT/Claude correctly.
02 Listing Description System  Write listings in under 10 minutes.
03 Lead Follow-Up Pack         18+ email & text templates by stage.
04 Client Onboarding System    AI-assisted consultation prep.
05 Social Media Content Engine 30-day content calendar.
06 Negotiation Support Pack    Counter-offer language & objections.
07 Reputation & Review System  Automate your review pipeline.

MASTER_Complete_Kit.pdf        All 8 documents in one file.

GETTING STARTED
---------------
1. Open Document 00 (Quick Start Guide).
2. Follow the 30-minute implementation session.
3. You will write your first AI-assisted listing description today.

====================================================
""", encoding='utf-8')
print(f"  ✓ START_HERE.txt written ({start_here.stat().st_size} bytes)")

# Remove old ZIPs
for old in PROD.glob('*.zip'):
    old.unlink()
    print(f"  removed old: {old.name}")

# Files to include at root of ZIP
root_files = [
    'START_HERE.txt',
    '00_Quick_Start_Guide.pdf',
    '01_AI_Tools_Setup_Guide.pdf',
    '02_Listing_Description_System.pdf',
    '03_Lead_Follow-Up_Communication_Pack.pdf',
    '04_Client_Onboarding_System.pdf',
    '05_Social_Media_Content_Engine.pdf',
    '06_Negotiation_Support_Pack.pdf',
    '07_Reputation_&_Review_System.pdf',
    'MASTER_Complete_Kit.pdf',
]

with zipfile.ZipFile(ZIP_OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Root PDF files + START_HERE
    for fname in root_files:
        fpath = PROD / fname
        if fpath.exists():
            zf.write(fpath, fname)
            print(f"  + {fname}")
        else:
            print(f"  MISSING: {fname}")

    # SVG covers
    covers_dir = PROD / 'covers'
    for svg in sorted(covers_dir.glob('*.svg')):
        zf.write(svg, f'covers/{svg.name}')
        print(f"  + covers/{svg.name}")

size_kb = ZIP_OUT.stat().st_size // 1024
print(f"\nBuilt: {ZIP_OUT.name} ({size_kb}KB, {len(zf.namelist())} files)")
print("\nContents:")
with zipfile.ZipFile(ZIP_OUT) as zf2:
    for info in zf2.infolist():
        print(f"  {info.filename:50s}  {info.file_size//1024:4d}KB")
