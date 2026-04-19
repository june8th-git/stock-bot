name: Daily Portfolio Update

on:
  schedule:
    - cron: "30 21 * * 1-5"   # 4:30 PM ET (21:30 UTC), Mon–Fri
  workflow_dispatch:           # allow manual runs from GitHub UI

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

permissions:
  contents: write              # needed to push index.html to docs/

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run portfolio script
        env:
          TD_API_KEY:     ${{ secrets.TD_API_KEY }}
          EMAIL_SENDER:   ${{ secrets.EMAIL_SENDER }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
          EMAIL_RECEIVER: ${{ secrets.EMAIL_RECEIVER }}
        run: python portfolio.py

      - name: Commit & push HTML to docs/
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/index.html
          git diff --cached --quiet || git commit -m "chore: daily portfolio update $(date -u +'%Y-%m-%d')"
          git push
