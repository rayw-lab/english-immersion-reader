# Wave-2 Publish Candidate

state=wave2-shipped-candidate

## Human Gate

Do not run these commands before human review:

```bash
gh repo create rayw-lab/immersion-reader --public --source=. --remote=origin --push
gh repo edit rayw-lab/immersion-reader --enable-pages
git tag v0.1.0 && git push origin v0.1.0
```

## Repository Defaults

- Repository name: `immersion-reader`; `gh repo view rayw-lab/immersion-reader` returned not found on 2026-06-11.
- License: MIT.
- Chinese README filename: `README.zh.md`.
- Pages source after publish: `/docs`, demo path `/demo/`.
- Suggested topics: `claude-code`, `agent-skills`, `english-learning`, `edge-tts`, `language-learning`.
- Social preview source: `docs/assets/social-preview.png`.

## Publication Sequence After Review

1. Create the public GitHub repository and push `main`.
2. Enable GitHub Pages from `/docs`.
3. Confirm `https://rayw-lab.github.io/immersion-reader/demo/` loads.
4. Create tag `v0.1.0`.
5. Submit the low-barrier awesome-list PR draft in `docs/release/awesome-agent-skills-entry.md`.
6. Defer travisvn/awesome-claude-skills until the repo has roughly 10+ stars.
7. HN Show HN and V2EX are human-review channels; no default auto-post in wave-2.

## Rights Boundary

`lessons/` is ignored by git. User-captured transcripts, private articles, generated lessons, and generated audio stay local unless the publisher owns the rights.
