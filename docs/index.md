---
template: home.html
description: A project-owned workflow that moves coding-agent tasks through checked stages.
---

<section class="home-hero" aria-labelledby="home-title">
  <div class="home-hero-copy">
    <p class="home-kicker">OPEN SOURCE · PROJECT OWNED · MIT</p>
    <h1 id="home-title">Your coding agents,<br>checked at every stage.</h1>
    <p class="home-lead">Stagecoach gives coding agents a project-owned path from a clear plan to checked code. Each runner stage starts fresh, then checks the actual files and command output before it advances.</p>
    <p class="rename-note">The CLI and package are still named <code>agent-workflow</code> while the rename is in progress.</p>
    <div class="home-actions">
      <a class="button button-primary" href="install/">Install Stagecoach <span aria-hidden="true">→</span></a>
      <a class="button button-secondary" href="#how-it-works">See how it works</a>
    </div>
    <div class="install-command" aria-label="Global installation command">
      <span>INSTALL</span>
      <pre><code>curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --global</code></pre>
      <p>Requires the matching published tag.</p>
    </div>
  </div>
  <div class="run-panel" aria-label="Example Stagecoach run">
    <div class="run-panel-top"><span class="run-dot" aria-hidden="true"></span><span>replace-navigation</span><span class="run-live">RUNNING</span></div>
    <div class="run-command"><span>$</span> agent-workflow status replace-navigation</div>
    <div class="run-status"><span>stage</span><strong>review</strong><span class="status-signal">evidence recorded</span></div>
    <ol class="run-stages">
      <li class="is-complete" data-run-stage><span>01</span><strong>Plan</strong><em>checked</em></li>
      <li class="is-complete" data-run-stage><span>02</span><strong>Tests</strong><em>checked</em></li>
      <li class="is-complete" data-run-stage><span>03</span><strong>Implement</strong><em>checked</em></li>
      <li class="is-current" data-run-stage><span>04</span><strong>Review</strong><em>current</em></li>
      <li data-run-stage><span>05</span><strong>Deliver</strong><em>queued</em></li>
    </ol>
    <p class="run-note">Named checks and current-diff evidence stay with the run.</p>
  </div>
</section>

<section class="home-trust" aria-label="Stagecoach qualities">
  <span>Clear plans</span><span>Fresh stages</span><span>Project-owned skills</span><span>Evidence in the open</span>
</section>

<section class="how-it-works" id="how-it-works" aria-labelledby="how-it-works-title">
  <div class="section-intro">
    <p class="section-label">THE RUNNER</p>
    <h2 id="how-it-works-title">Every task has a route you can inspect.</h2>
    <p>The full lane saves its plan and runs selected stages independently. The small manual lane keeps the same skills close when a pipeline is more ceremony than the change needs.</p>
  </div>
  <div class="workflow-diagram" aria-label="Plan through deliver workflow">
    <svg class="workflow-arrows" viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true"><path d="M130 30H262M334 30H466M538 30H670M742 30H870"/><path d="M258 24l10 6-10 6M462 24l10 6-10 6M666 24l10 6-10 6M866 24l10 6-10 6"/></svg>
    <div class="workflow-step"><span>01</span><h3>Plan</h3><p>Named acceptance checks map to each outcome.</p></div>
    <div class="workflow-step is-optional"><span>02 · optional</span><h3>Tests</h3><p>Expected failures remain visible as red evidence.</p></div>
    <div class="workflow-step"><span>03</span><h3>Implement</h3><p>Writable paths and repositories stay within scope.</p></div>
    <div class="workflow-step is-optional"><span>04 · optional</span><h3>Review</h3><p>The reviewer sees requirements and the actual diff.</p></div>
    <div class="workflow-step is-optional"><span>05 · optional</span><h3>Deliver</h3><p>Selected commits and draft PRs use guarded delivery.</p></div>
  </div>
  <p class="diagram-caption">Optional stages are chosen in each plan; no provider is required for every stage.</p>
</section>

<section class="manual-lane" aria-labelledby="manual-lane-title">
  <div>
    <p class="section-label">KEEP THE SMALL CHANGES SMALL</p>
    <h2 id="manual-lane-title">Use the manual lane when it fits.</h2>
    <p>Specify a concise plan, implement in the current agent session, and observe the checks. It is the same project-owned workflow without a full runner for contained work.</p>
  </div>
  <a class="text-link" href="tasks/#choose-a-lane">Choose a lane <span aria-hidden="true">→</span></a>
</section>

<section class="ownership" aria-labelledby="ownership-title">
  <div class="section-intro">
    <p class="section-label">YOUR PROJECT, YOUR RULES</p>
    <h2 id="ownership-title">The workflow adapts to the repository—not the other way around.</h2>
    <p>Setup records commands, branches, agents, models, permissions, and delivery choices. Copy skills, capture rules, and add connectors without forking the package.</p>
  </div>
  <div class="ownership-grid">
    <div class="code-card">
      <p>CHANGE WHAT YOUR AGENTS KNOW</p>
      <pre><code>agent-workflow skill copy review
agent-workflow skill new release-notes --description "Draft release notes from verified changes."
agent-workflow refresh</code></pre>
      <a href="customize/">Customize skills and stages <span aria-hidden="true">→</span></a>
    </div>
    <div class="tree-card">
      <p>KEEP EXTENSIONS WITH THE PROJECT</p>
      <pre aria-label="Project extension file tree"><code>.agent-workflow/
├── skills/
├── rules/
├── connectors/
└── stages.json</code></pre>
      <a href="projects/">See the project layout <span aria-hidden="true">→</span></a>
    </div>
  </div>
</section>

<section class="home-limits" aria-labelledby="limits-title">
  <h2 id="limits-title">Honest about what is checked.</h2>
  <p>Stagecoach records executable evidence, but host behavior and provider integrations still need the coverage stated for them. Read the limits before relying on an unattended path.</p>
  <p><a href="coverage/">Coverage and host checks</a><a href="verification/">Evidence and verification</a></p>
</section>

<section class="home-cta" aria-labelledby="cta-title">
  <p class="section-label">READY TO START</p>
  <h2 id="cta-title">Give the next task a route worth trusting.</h2>
  <p>Install Stagecoach, set up the project once, then keep the decisions and evidence close to the code.</p>
  <a class="button button-primary" href="install/">Install Stagecoach <span aria-hidden="true">→</span></a>
</section>
