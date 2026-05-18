<script lang="ts">
  // M5 deliverable #5: public privacy statement covering what's stored
  // and why. See decisions/0012-m5-local-accounts.md.
</script>

<section class="privacy">
  <h2>Privacy</h2>

  <p class="lead">
    Short version: <strong>graded-guitar stores everything in your browser</strong>.
    Nothing is sent to a server we operate. There is no analytics, no
    tracking, and no account in the conventional sense.
  </p>

  <h3>What we store, and where</h3>
  <p>
    The site uses your browser's <code>localStorage</code> to remember:
  </p>
  <ul>
    <li>
      <strong>Profiles</strong> — a display name and a declared playing
      level. We do not collect email, password, or any other identifier.
    </li>
    <li>
      <strong>Per-piece status</strong> — which pieces you've marked as
      playing, completed, too hard, or not for you, with a timestamp.
    </li>
  </ul>
  <p>
    That data is keyed under the prefix <code>gradedGuitar.</code> in
    your browser's storage. You can inspect or delete it yourself
    using your browser's developer tools.
  </p>

  <h3>What we do NOT store</h3>
  <ul>
    <li>No emails, passwords, names, or any other PII.</li>
    <li>No IP addresses or device fingerprints (we don't run an analytics tool).</li>
    <li>No cookies for tracking or advertising.</li>
    <li>No data on any server we operate (today, there is no server).</li>
  </ul>

  <h3>Hosting</h3>
  <p>
    The site is served as a static bundle from
    <a href="https://docs.github.com/en/pages" target="_blank" rel="noopener">GitHub Pages</a>.
    GitHub may log requests for operational reasons; their privacy
    notice is at
    <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener">docs.github.com</a>.
  </p>

  <h3>Deleting your data</h3>
  <p>
    Two ways:
  </p>
  <ul>
    <li>
      Open <a href="#/profile">your profiles page</a> and click
      <em>Delete</em> on any profile. That wipes the profile and its
      library on this browser.
    </li>
    <li>
      Or, in your browser's site-settings panel for this site, clear
      site data. That removes every <code>gradedGuitar.</code> entry.
    </li>
  </ul>

  <h3>Future hosting</h3>
  <p>
    If the project gains enough traction to justify hosted
    infrastructure, we may offer real (server-backed) accounts so
    your library can sync across devices. That change would be opt-in
    and would come with a revised privacy notice — your existing
    local data would not be uploaded without your action. See
    <a href="https://github.com/HugoFara/graded-guitar/blob/main/decisions/0012-m5-local-accounts.md" target="_blank" rel="noopener">ADR 0012</a>
    for the architectural intent.
  </p>

  <h3>Contact</h3>
  <p>
    Questions or concerns:
    <a href="mailto:hugo.farajallah@unige.ch">hugo.farajallah@unige.ch</a>.
  </p>
</section>

<style>
  .privacy {
    max-width: 50rem;
    margin: 1rem auto;
    line-height: 1.5;
  }
  .lead {
    font-size: 1.05em;
    padding: 0.75rem;
    border-left: 3px solid var(--accent);
    background: var(--card-bg);
  }
  h3 {
    margin-top: 1.5em;
  }
  code {
    background: var(--card-bg);
    padding: 0.05em 0.3em;
    border-radius: 3px;
    font-size: 0.9em;
  }
</style>
