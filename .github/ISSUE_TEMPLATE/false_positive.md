---
name: False Positive Report
about: The scanner flagged something that came back N/A or is not a real vulnerability
title: "[FP] "
labels: false-positive
assignees: ''
---

## What was flagged?

<!-- Paste the scanner lead/candidate and the validation result. -->

```
candidate: XSS reflection at ...
```

## Why is it a false positive?

<!-- What made this come back N/A? CSP blocked it? Own data only? DNS-only SSRF? -->

## Program / Context

<!-- Bug bounty platform (H1, Bugcrowd, etc.) — no real target names needed -->

## Kill Signal

<!-- What observable signal should we add to the kill-signal table to prevent this in future? -->
