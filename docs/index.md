---
template: home.html
title: Overview
description: Agents write the code. Scorebook makes them prove it, with an open-source runner that checks every stage.
---

<section class="home-hero" aria-labelledby="home-title">
  <div class="home-hero-copy">
    <p class="home-kicker">OPEN SOURCE · MIT · CLAUDE CODE · CODEX · CURSOR</p>
    <h1 id="home-title">Agents write the code. Scorebook makes them prove it.</h1>
    <p class="home-lead">One confirmed plan becomes a staged run: tests that fail for the right reason, an implementation checked against real command output, an optional independent review, and a guarded draft PR. Every stage starts a fresh agent session. Every check that counts is one the runner ran itself.</p>
    <div class="home-actions">
      <a class="button button-primary" href="install/">Install <span aria-hidden="true">→</span></a>
      <a class="button button-secondary" href="https://github.com/MarkoArsov/agent-workflow">View on GitHub</a>
      <a class="text-link" href="#how-it-works">See how it works <span aria-hidden="true">→</span></a>
    </div>
    <div class="install-command" aria-label="Global installation command">
      <span>INSTALL</span>
      <pre><code>curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --global</code></pre>
      <p>Requires the matching published tag. Review the pinned script first if that is your policy.</p>
    </div>
    <p class="home-trust-strip">MIT · zero runtime dependencies · runs locally · no account · no telemetry</p>
  </div>
  <div class="run-panel" aria-label="Example Scorebook run">
    <div class="run-panel-top"><span class="run-dot" aria-hidden="true"></span><span>csv-export</span><span class="run-live">RUNNING</span></div>
    <div class="run-command"><span>$</span> scorebook status csv-export</div>
    <div class="run-status"><span>stage</span><strong>review</strong><span class="status-signal">green evidence bound to diff c0045111…</span></div>
    <ol class="run-stages">
      <li class="is-complete" data-run-stage><span>01</span><strong>Plan</strong><em>confirmed</em></li>
      <li class="is-complete" data-run-stage><span>02</span><strong>Tests</strong><em>red → frozen</em></li>
      <li class="is-complete" data-run-stage><span>03</span><strong>Implement</strong><em>green</em></li>
      <li class="is-current" data-run-stage><span>04</span><strong>Review</strong><em>fresh session</em></li>
      <li data-run-stage><span>05</span><strong>Deliver</strong><em>queued</em></li>
    </ol>
    <p class="run-note">Example run. Checks, attempts, and evidence stay on disk with the project.</p>
  </div>
</section>

<section class="home-problem" aria-labelledby="problem-title">
  <div class="section-intro">
    <p class="section-label">THE VERIFICATION GAP</p>
    <h2 id="problem-title">Passing tests is not a merge signal.</h2>
  </div>
  <div class="stat-grid">
    <div class="stat-tile"><p class="stat-figure">≈ 1 in 2</p><p class="stat-label">test-passing AI pull requests that the project's own maintainers would not merge</p><p class="stat-source"><a href="https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/">METR, March 2026</a>: 296 AI-generated PRs reviewed by maintainers of 3 SWE-bench Verified repositories</p></div>
    <div class="stat-tile"><p class="stat-figure">≈ 24 pts</p><p class="stat-label">average gap between the automated grader and the maintainers' merge decisions</p><p class="stat-source"><a href="https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/">METR, March 2026</a></p></div>
    <div class="stat-tile"><p class="stat-figure">46%</p><p class="stat-label">of agent-proposed fixes from Copilot, Devin, Cursor, and Claude rejected</p><p class="stat-source"><a href="https://arxiv.org/abs/2606.13468">AIDev study, 2026</a></p></div>
  </div>
  <p class="home-closing-line">Writing code stopped being the hard part. Proving a change is right is the new bottleneck, and Scorebook is built around it. <a class="text-link" href="why/">Read the research <span aria-hidden="true">→</span></a></p>
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
    <div class="workflow-step"><span>03 · always</span><h3>Implement</h3><p>Build, run every named check, fix, repeat. The runner then runs the checks itself.</p><p class="workflow-evidence">Parsed green output bound to the current diff fingerprint</p></div>
    <div class="workflow-step is-optional"><span>04 · optional</span><h3>Review</h3><p>A fresh session with the requirements and the actual diff. It never sees the implementation's reasoning.</p><p class="workflow-evidence">Findings, and checks re-run after any correction</p></div>
    <div class="workflow-step is-optional"><span>05 · optional</span><h3>Deliver</h3><p>Runner-owned commit, push, and draft PR. Refuses base branches; never force-pushes.</p><p class="workflow-evidence">A delivery record per repository</p></div>
  </div>
  <div class="manual-bypass"><span class="section-label">MANUAL LANE</span><p>Small change? Run <code>specify</code>, then <code>implement</code>, in one session: the same plan and named checks, no detached run.</p><a class="text-link" href="lanes/">Choose a lane <span aria-hidden="true">→</span></a></div>
</section>

<section class="home-stops" aria-labelledby="stops-title">
  <div class="section-intro">
    <p class="section-label">BOUNDED AUTONOMY</p>
    <h2 id="stops-title">Runs unattended. Stops only for what matters.</h2>
  </div>
  <div class="stop-grid">
    <div class="stop-col stop-col--flag">
      <p class="stop-col__title">Recorded, run continues</p>
      <ul>
        <li>Review findings, which are advisory</li>
        <li>Advisory rule findings</li>
        <li>One route for every stage</li>
        <li>Usage the provider didn't report, kept as unknown</li>
      </ul>
    </div>
    <div class="stop-col stop-col--stop">
      <p class="stop-col__title">Blocks completion</p>
      <ul>
        <li>Secret material or a blocking rule finding</li>
        <li>Edits outside the declared paths, or to a read-only repository</li>
        <li>A named check fails, or red or green evidence is missing</li>
        <li>A frozen test changed, or your pre-existing changes were touched</li>
        <li>Stale green evidence fails its re-run before delivery</li>
        <li>A delivery guard trips: base branch, unrelated staged changes, a moved HEAD</li>
        <li>Configured attempts or time limits run out</li>
      </ul>
    </div>
  </div>
  <p class="home-closing-line">Scope and guard violations stop the run at once. Failing checks go back to the agent as feedback first. Advisory findings never turn into babysitting, and a failed safety check never turns into a success summary.</p>
</section>

<section class="home-scorecard" aria-labelledby="scorecard-title">
  <div class="section-intro">
    <p class="section-label">THE SCORECARD</p>
    <h2 id="scorecard-title">Measured against <!-- scorecard: total --> checkpoints. Gaps included.</h2>
    <p>Most tools tell you they're safe. Scorebook publishes the scorecard: what the runner enforces, what's partial, what belongs to your organization, and what's still open.</p>
  </div>
<!-- scorecard: grid -->
  <p class="beyond-title">Beyond the rubric</p>
<!-- scorecard: beyond-chips -->
  <p><a class="text-link" href="scorecard/">Read the scorecard <span aria-hidden="true">→</span></a></p>
</section>

<section class="home-open" aria-labelledby="open-title">
  <div class="section-intro">
    <p class="section-label">OPEN SOURCE</p>
    <h2 id="open-title">Open source, all the way down.</h2>
    <p>A verification layer you can't inspect is just another claim to trust. Every line that decides whether your agents' work passes is in the public repository.</p>
  </div>
  <div class="tile-grid">
    <div class="tile"><h3>MIT-licensed</h3><p>Use it at work, change it, ship it.</p></div>
    <div class="tile"><h3>Read the runner</h3><p>Standard-library Python with zero runtime dependencies. The runner, parsers, and guards are ordinary code, not a hidden service.</p></div>
    <div class="tile"><h3>Runs on your machine</h3><p>Your agent CLIs, your logins, your repositories. No Scorebook account, server, or telemetry.</p></div>
    <div class="tile"><h3>Built in the open</h3><p>Public CI on Linux and macOS, public tests, public scorecard, gaps included.</p></div>
  </div>
  <div class="home-actions">
    <a class="button button-secondary" href="https://github.com/MarkoArsov/agent-workflow">Read the code</a>
    <a class="text-link" href="development/">How to contribute <span aria-hidden="true">→</span></a>
  </div>
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
    <div class="decision-card"><h3>Mechanical verification</h3><p class="decision-problem">A confident report can still be wrong.</p><p class="decision-result">An agent's response is a proposal, not a completion. The runner runs the checks.</p></div>
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
    <h2 id="review-title">Review is the new bottleneck. Scorebook treats it that way.</h2>
    <p>Agents produce diffs faster than anyone can responsibly merge them. Use AI to understand a change before you judge it, keep your own queue short, and spend the waits reviewing. A named human still approves.</p>
  </div>
  <div class="mono-chips"><code>understand</code><code>review-guide</code><code>peer-pr-review</code><code>address-pr-comments</code><code>pr-preflight</code></div>
  <p class="home-closing-line">One runner per project, and a short queue beats a pile of draft PRs. <a class="text-link" href="everyday/">Review and everyday use <span aria-hidden="true">→</span></a></p>
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
      <pre><code>scorebook skill copy review
scorebook skill new release-notes --description "Draft release notes from verified changes."
scorebook refresh</code></pre>
      <a href="customize/">Customize skills and stages <span aria-hidden="true">→</span></a>
    </div>
    <div class="tree-card">
      <p>KEEP EXTENSIONS WITH THE PROJECT</p>
      <pre aria-label="Project extension file tree"><code>.scorebook/
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
