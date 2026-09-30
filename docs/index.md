---
template: home.html
title: Overview
description: Agents write the code. The orchestrator makes them prove it, checking every stage in open-source code.
---

<section class="home-hero" aria-labelledby="home-title">
  <div class="home-hero-copy">
    <p class="home-kicker">Open Source · MIT · Claude Code · Codex · Cursor</p>
    <h1 id="home-title">Done means proven.</h1>
    <p class="home-lead">One confirmed plan becomes a staged run: failing tests first, checked implementation, optional review, guarded draft PR. Each stage runs in a fresh agent session, and only checks the runner ran itself count.</p>
    <div class="home-actions">
      <a class="button button-primary" href="install/">Install <span aria-hidden="true">→</span></a>
      <a class="button button-secondary" href="https://github.com/MarkoArsov/agent-workflow">View on GitHub</a>
    </div>
    <div class="install-command" aria-label="Global installation command">
      <span>install</span>
      <p class="install-os">macOS · Linux</p>
      <pre><code>curl -fsSL https://agentic.markoarsov.com/install.sh | sh</code></pre>
      <p class="install-os">Windows · PowerShell</p>
      <pre><code>irm https://agentic.markoarsov.com/install.ps1 | iex</code></pre>
      <p>Then run <code>/af-setup</code> in your agent. Needs Python 3.11+ and Git.</p>
    </div>
  </div>
  <div class="run-panel" aria-label="Example Agent Flow run">
    <div class="run-panel-top"><span class="run-dot" aria-hidden="true"></span><span>csv-export</span><span class="run-live">RUNNING</span></div>
    <div class="run-command"><span>$</span> agentflow status csv-export</div>
    <div class="run-status"><span>stage</span><strong>review</strong><span class="status-signal">green evidence bound to diff c0045111…</span></div>
    <ol class="run-stages">
      <li class="is-complete" data-run-stage><span>01</span><strong>Plan</strong><em>confirmed</em></li>
      <li class="is-complete" data-run-stage><span>02</span><strong>Tests</strong><em>red → frozen</em></li>
      <li class="is-complete" data-run-stage><span>03</span><strong>Implement</strong><em>green</em></li>
      <li class="is-current" data-run-stage><span>04</span><strong>Review<i class="stage-pulse" aria-hidden="true"></i></strong><em>fresh session</em></li>
      <li data-run-stage><span>05</span><strong>Deliver</strong><em>queued</em></li>
    </ol>
    <p class="run-note">Example run. Checks, attempts, and evidence stay on disk with the project.</p>
  </div>
</section>

<section class="home-problem" aria-labelledby="problem-title">
  <div class="section-intro">
    <p class="section-label">THE VERIFICATION GAP</p>
    <h2 id="problem-title">Green tests don't mean done.</h2>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><p class="stat-figure">1 in 2</p><p class="stat-label">AI pull requests that pass the tests would still be rejected by the project's maintainers.</p><p class="stat-source"><a href="https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/">METR, 2026</a></p></div>
    <div class="stat-tile"><p class="stat-figure">46%</p><p class="stat-label">of fixes proposed by coding agents in real open-source projects were rejected.</p><p class="stat-source"><a href="https://arxiv.org/abs/2606.13468">AIDev, 2026</a></p></div>
    <div class="stat-tile"><p class="stat-figure">3.7%</p><p class="stat-label">of engineering leaders say their processes are enough to keep quality and governance as agents take on more work.</p><p class="stat-source"><a href="https://www.qodo.ai/blog/state-of-ai-code-quality-report-2026/">Qodo, 2026</a></p></div>
  </div>
  <p class="home-closing-line">Writing code is no longer the hard part. Proving it's right is, so Agent Flow makes every stage prove it.</p>
  <p><a class="text-link" href="why/">Read the research <span aria-hidden="true">→</span></a></p>
</section>

<section class="how-it-works" id="how-it-works" aria-labelledby="how-it-works-title">
  <div class="section-intro">
    <p class="section-label">HOW IT WORKS</p>
    <h2 id="how-it-works-title">Five stages. Each one has to show its work.</h2>
    <p>Fresh horses at every stage: each stage starts a new session with only the plan, the project's rules, and the repository, so no chat history or bias carries over.</p>
  </div>
  <div class="workflow-diagram" aria-label="Specify through deliver">
    <svg class="workflow-arrows" viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true"><path d="M130 30H262M334 30H466M538 30H670M742 30H870"/><path d="M258 24l10 6-10 6M462 24l10 6-10 6M666 24l10 6-10 6M866 24l10 6-10 6"/></svg>
    <div class="workflow-step"><span>01 · specify</span><h3>Specify</h3><p>Research first, questions second. One complete plan in which every outcome maps to a named check.</p><p class="workflow-evidence">Four plan files plus a validated <code>pipeline.json</code></p></div>
    <div class="workflow-step is-optional"><span>02 · optional</span><h3>Tests</h3><p>Written before the code. They must fail on an assertion, not a setup error. Then they're frozen.</p><p class="workflow-evidence">Red proof and test-file hashes</p></div>
    <div class="workflow-step"><span>03 · always</span><h3>Implement</h3><p>Build, run every named check, fix, repeat. The orchestrator then runs the checks itself.</p><p class="workflow-evidence">Parsed green output bound to the current diff fingerprint</p></div>
    <div class="workflow-step is-optional"><span>04 · optional</span><h3>Review</h3><p>A fresh session with the requirements and the actual diff. It never sees the implementation's reasoning.</p><p class="workflow-evidence">Findings, and checks re-run after any correction</p></div>
    <div class="workflow-step is-optional"><span>05 · optional</span><h3>Deliver</h3><p>Orchestrator-owned commit, push, and draft PR. Refuses base branches; never force-pushes.</p><p class="workflow-evidence">A delivery record per repository</p></div>
  </div>
  <div class="manual-bypass"><span class="section-label">MANUAL LANE</span><p>Small change? Run <code>specify</code>, then <code>implement</code>, in one session: the same plan and named checks, no detached run.</p><a class="text-link" href="lanes/">Choose a lane <span aria-hidden="true">→</span></a></div>
</section>

<section class="home-scorecard" aria-labelledby="scorecard-title">
  <div class="section-intro">
    <p class="section-label">THE SCORECARD</p>
    <h2 id="scorecard-title">Measured against <!-- scorecard: total --> checkpoints. Gaps included.</h2>
    <p>Most tools tell you they're safe. Agent Flow publishes the scorecard: what the orchestrator enforces, what's partial, what belongs to your organization, and what's still open.</p>
  </div>
<!-- scorecard: grid -->
  <p><a class="text-link" href="scorecard/">Read the scorecard <span aria-hidden="true">→</span></a></p>
</section>

<section class="home-decisions" aria-labelledby="decisions-title">
  <div class="section-intro">
    <p class="section-label">DESIGN</p>
    <h2 id="decisions-title">Every decision answers a failure mode.</h2>
  </div>
  <div class="decision-grid">
    <div class="decision-card"><h3>Research before planning</h3><p class="decision-problem">Agents guess, or ask questions the repository can answer.</p><p class="decision-result"><code>specify</code> reads instructions and working examples first, then asks only what is missing.</p></div>
    <div class="decision-card"><h3>Tests first, red on an assertion</h3><p class="decision-problem">A test written after the code can prove the code instead of the requirement.</p><p class="decision-result">The red stage must fail on assertions, not setup errors. Then the tests are frozen.</p></div>
    <div class="decision-card"><h3>A fresh session per stage</h3><p class="decision-problem">Shared chat history biases later judgment.</p><p class="decision-result">Every stage and retry starts from the plan and the repository, not the previous conversation.</p></div>
    <div class="decision-card"><h3>Write it once</h3><p class="decision-problem">Asking a model to redo a mechanical step spends tokens and can give a different answer each time.</p><p class="decision-result">If a step can be a script, it is one: deterministic, free to run, and the same every time. Models are kept for judgement.</p></div>
    <div class="decision-card"><h3>Stop only on safety</h3><p class="decision-problem">Treating every finding as a stop turns automation into babysitting.</p><p class="decision-result">Scope, secrets, frozen tests, failed checks, and delivery guards block. Review notes don't.</p></div>
    <div class="decision-card"><h3>Open and local</h3><p class="decision-problem">A closed verification layer is one more claim to trust.</p><p class="decision-result">The whole verification layer is public code that runs on your machine.</p></div>
  </div>
  <p><a class="text-link" href="principles/">All design decisions <span aria-hidden="true">→</span></a></p>
</section>

<section class="home-split" aria-labelledby="models-title">
  <div class="section-intro">
    <p class="section-label">COST AND MODELS</p>
    <h2 id="models-title">Scripts own the process. Models own the judgement.</h2>
  </div>
  <ul class="point-list">
    <li><strong>Any harness.</strong> Claude Code, Codex, or Cursor. No vendor lock-in.</li>
    <li><strong>A route per stage.</strong> Explicit ordered fallbacks, never switched silently. An answer always resumes the session that asked.</li>
    <li><strong>Two sessions minimum.</strong> The cheapest complete path is <code>specify</code>, then <code>implement</code>.</li>
    <li><strong>No model calls where none are needed.</strong> Verification, status, watching, and delivery are local scripts.</li>
  </ul>
  <p><a class="text-link" href="models/">Cost and models <span aria-hidden="true">→</span></a></p>
</section>

<section class="home-split" aria-labelledby="review-title">
  <div class="section-intro">
    <p class="section-label">REVIEW</p>
    <h2 id="review-title">Review is the new bottleneck. Agent Flow treats it that way.</h2>
    <p>Agents produce diffs faster than anyone can responsibly merge them. Use AI to understand a change before you judge it, keep your own queue short, and spend the waits reviewing. A named human still approves.</p>
  </div>
  <div class="mono-chips"><code>understand</code><code>review-guide</code><code>peer-pr-review</code><code>address-pr-comments</code><code>pr-preflight</code></div>
  <p class="home-closing-line">One orchestrator per project, and a short queue beats a pile of draft PRs. <a class="text-link" href="everyday/">Review and everyday use <span aria-hidden="true">→</span></a></p>
</section>

<section class="ownership" aria-labelledby="ownership-title">
  <div class="section-intro">
    <p class="section-label">YOURS TO CHANGE</p>
    <h2 id="ownership-title">The workflow adapts to the repository, not the other way around.</h2>
    <p>Setup records commands, branches, agents, models, permissions, and delivery choices. Copy skills, capture rules, and add connectors and stages without touching installed defaults. Change it per project without forking, or fork the whole thing: it's MIT.</p>
  </div>
  <div class="ownership-grid">
    <div class="code-card">
      <p>CHANGE WHAT YOUR AGENTS KNOW</p>
      <pre><code>agentflow skill copy review
agentflow skill new release-notes --description "Draft release notes from verified changes."
agentflow refresh</code></pre>
      <a href="customize/">Customize skills and stages <span aria-hidden="true">→</span></a>
    </div>
    <div class="tree-card">
      <p>KEEP EXTENSIONS WITH THE PROJECT</p>
      <pre aria-label="Project extension file tree"><code>.agentflow/
├── skills/
├── rules/
├── references/
├── connectors/
└── stages.json</code></pre>
      <a href="projects/">See the project layout <span aria-hidden="true">→</span></a>
    </div>
  </div>
</section>

<section class="home-paths" aria-labelledby="paths-title">
  <div class="section-intro">
    <p class="section-label">PICK YOUR PATH</p>
    <h2 id="paths-title">Start where you are.</h2>
  </div>
  <div class="path-grid">
    <div class="path-card"><h3>First time here</h3><ol><li><a href="why/">The verification gap</a></li><li><a href="principles/">Design principles</a></li><li><a href="first-task/">Your first task</a></li></ol></div>
    <div class="path-card"><h3>Running tasks</h3><ol><li><a href="tasks/">Task lifecycle</a></li><li><a href="everyday/">Review and everyday use</a></li><li><a href="recovery/">When a task stops</a></li></ol></div>
    <div class="path-card"><h3>Adopting it for a team</h3><ol><li><a href="setup/">Set up your project</a></li><li><a href="customize/">Skills and stages</a></li><li><a href="scorecard/">Checkpoint scorecard</a></li><li><a href="security/">Security boundary</a></li></ol></div>
    <div class="path-card"><h3>Contributing</h3><ol><li><a href="open-source/">Open source</a></li><li><a href="code-map/">Code map</a></li><li><a href="development/">Contribute and develop</a></li></ol></div>
    <div class="path-card"><h3>Maintaining your setup</h3><ol><li><a href="maintaining/">Keep the workflow clear</a></li><li><a href="lifecycle/">Update and remove</a></li></ol></div>
  </div>
</section>

<section class="home-cta" aria-labelledby="cta-title">
  <p class="section-label">READY TO START</p>
  <h2 id="cta-title">Give your agents a route. Make every stage prove itself.</h2>
  <div class="home-actions home-actions--center">
    <a class="button button-primary" href="install/">Install <span aria-hidden="true">→</span></a>
    <a class="button button-secondary" href="first-task/">Your first task</a>
    <a class="button button-secondary" href="https://github.com/MarkoArsov/agent-workflow">Star on GitHub</a>
  </div>
  <p class="home-cta-note">Open source under the MIT license. Contributions welcome.</p>
</section>
