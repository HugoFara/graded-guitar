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
    <li>
      <strong>Grade-disagreement votes</strong> — when you tell us a
      piece feels easier, right, or harder than the visible grade, we
      keep that vote, the timestamp, and a snapshot of the grade you
      were reacting to. The vote stays on this browser unless you
      send it yourself (see <em>Sharing signals</em> below).
    </li>
    <li>
      <strong>Practice takes</strong> — if you use the microphone
      feature, we keep a per-bar summary of the take: how many attempts
      each bar took, how your timing compared to the written tempo,
      where you paused, and where you started over. See
      <em>The microphone</em> below.
    </li>
  </ul>
  <p>
    That data is keyed under the prefix <code>gradedGuitar.</code> in
    your browser's storage. You can inspect or delete it yourself
    using your browser's developer tools.
  </p>

  <h3>The microphone</h3>
  <p>
    The practice feature listens through your microphone to work out
    where you are in the score. Specifically:
  </p>
  <ul>
    <li>
      <strong>It is off unless you turn it on.</strong> The microphone is
      only ever engaged when you click <em>Start listening</em> on a
      practice page, and your browser will ask permission the first
      time. Closing or leaving the page releases it.
    </li>
    <li>
      <strong>Your audio never leaves this browser.</strong> There is no
      server to send it to. All the analysis runs on your machine.
    </li>
    <li>
      <strong>The recording is not kept.</strong> Audio is converted, as
      it arrives, into twelve numbers per twentieth of a second
      describing which pitches are sounding. That summary is what the
      score follower reads, and the audio it came from is discarded
      immediately. Speech is not recoverable from it, and neither is
      the music.
    </li>
    <li>
      <strong>What is saved is the per-bar summary</strong> described
      above — timing, pauses and restarts — not the pitch stream and not
      the audio.
    </li>
  </ul>
  <p>
    Why we built this at all: the site's difficulty grades are still
    placeholders, and where a real player hesitates is a far better
    measure of how hard a piece is than anyone's guess. The output is a
    difficulty estimate <em>of the piece</em>. We are not scoring you,
    and we do not detect wrong notes — see
    <a href="https://github.com/HugoFara/graded-guitar/blob/main/decisions/0018-microphone-score-following.md" target="_blank" rel="noopener">ADR 0018</a>.
  </p>

  <h3>What we do NOT store</h3>
  <ul>
    <li>No emails, passwords, names, or any other PII.</li>
    <li>No IP addresses or device fingerprints (we don't run an analytics tool).</li>
    <li>No cookies for tracking or advertising.</li>
    <li>No data on any server we operate (today, there is no server).</li>
    <li>No audio recordings, and no raw microphone data of any kind.</li>
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

  <h3>Sharing signals</h3>
  <p>
    The <a href="#/profile">profiles page</a> has a
    <strong>Share signals…</strong> button. It downloads the same JSON
    backup you can already export, then opens a pre-filled email so
    you can attach it. Two things to know:
  </p>
  <ul>
    <li>
      It's strictly opt-in — nothing leaves your browser unless you
      click Send in your mail client.
    </li>
    <li>
      The file contains everything we store about you: display name,
      level, every status and grade-vote record, and any practice-take
      summaries. Read it before sending if you'd like to confirm what
      it contains.
    </li>
  </ul>
  <p>
    We use these shared signals only to improve grading accuracy
    during the closed-beta milestone (ADR 0013). They are not
    redistributed.
  </p>

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
    <a href="mailto:github@hugofara.net">github@hugofara.net</a>.
  </p>
  <p>
    Have classical-guitar MusicXML you've typeset and would be
    comfortable contributing to the corpus? The library is small and
    Renaissance/Baroque-heavy — modern repertoire, contemporary
    arrangements, and conservatory editions are all welcome. Same
    address.
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
