#!/usr/bin/env bash
cd /home/jb/dev/hydra
for f in app/db.py app/main.py app/llm.py; do
    python3 -m py_compile "$f" && echo "SYNTAX_OK: $f" || echo "SYNTAX_ERROR: $f"
done
echo "---"
bash scripts/verify_sprint151.sh
