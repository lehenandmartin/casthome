<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { SessionInfo } from '../lib/types';
  import { describeUserAgent } from '../lib/useragent';

  let sessions = $state<SessionInfo[]>([]);

  async function load() {
    await store.run(async () => {
      sessions = await api.sessions();
    });
  }

  async function revoke(id: string) {
    await store.run(async () => {
      await api.revokeSession(id);
      await load();
    });
  }

  async function revokeOthers() {
    await store.run(async () => {
      await api.revokeOtherSessions();
      await load();
    });
  }

  async function signOut() {
    await store.run(api.logout);
    store.signedOut();
  }

  const fmt = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  const others = $derived(sessions.filter((s) => !s.current).length);

  load();
</script>

<section>
  <h2>{t('sessions.title')}</h2>
  <p class="muted">{t('sessions.intro')}</p>

  <ul>
    {#each sessions as session (session.id)}
      <li>
        <div class="text">
          <strong>
            {describeUserAgent(session.user_agent)}
            {#if session.current}<span class="badge">{t('sessions.current')}</span>{/if}
          </strong>
          <span class="muted">
            {t('sessions.lastSeen', { date: fmt.format(session.last_seen_at * 1000) })} · {session.ip || '—'}
          </span>
          <span class="muted">
            {session.persistent
              ? t('sessions.expiresSliding', { date: fmt.format(session.expires_at * 1000) })
              : t('sessions.browserSession')}
          </span>
        </div>
        {#if session.current}
          <button onclick={signOut}>{t('nav.signOut')}</button>
        {:else}
          <button class="danger" onclick={() => revoke(session.id)}>{t('sessions.revoke')}</button>
        {/if}
      </li>
    {/each}
  </ul>

  {#if others > 0}
    <button class="danger" onclick={revokeOthers}>{t('sessions.revokeOthers')}</button>
  {/if}
</section>

<style>
  ul {
    list-style: none;
    padding: 0;
    margin: 16px 0;
    display: grid;
    gap: 8px;
  }
  li {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .text {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .badge {
    margin-left: 6px;
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--accent);
    color: var(--on-accent);
    vertical-align: middle;
  }
  button {
    flex: none;
  }
  .danger {
    color: var(--danger);
  }
</style>
