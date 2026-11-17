<script lang="ts">
  import { api } from '../lib/api';
  import { currentLanguage, t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { SessionInfo } from '../lib/types';
  import { describeUserAgent } from '../lib/useragent';

  // Inside Settings, which shows the section title.
  let { embedded = false }: { embedded?: boolean } = $props();
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
    await store.checkStatus();
  }

  const fmt = $derived(new Intl.DateTimeFormat(currentLanguage(), { dateStyle: 'medium', timeStyle: 'short' }));
  const others = $derived(sessions.filter((s) => !s.current).length);

  load();
</script>

<section>
  {#if !embedded}<h2>{t('sessions.title')}</h2>{/if}
  <p class="muted intro">{t('sessions.intro')}</p>

  <ul role="list">
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
          <!-- In Settings, this device signs out from the Account section above. -->
          {#if !embedded}<button onclick={signOut}>{t('nav.signOut')}</button>{/if}
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
    font-size: var(--text-xs);
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--accent-soft);
    color: var(--text);
    vertical-align: middle;
    display: inline-block;
    white-space: nowrap;
  }
  button {
    flex: none;
  }
  .danger {
    color: var(--danger);
  }
</style>
