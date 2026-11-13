<script lang="ts">
  import { api, ApiError } from '../lib/api';
  import { t, tCode } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  let password = $state('');
  let remember = $state(true);
  let busy = $state(false);
  let error = $state<string | null>(null);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    error = null;
    try {
      await api.login(password, remember);
      password = '';
      store.signedIn();
    } catch (err) {
      error = err instanceof ApiError ? tCode(err.code, err.params) : tCode('navidrome_unavailable');
    } finally {
      busy = false;
    }
  }
</script>

<main class="login">
  <form onsubmit={submit}>
    <h1>{t('app.name')}</h1>
    <p class="muted">{t('login.subtitleNoUser')}</p>
    <label>
      <span>{t('login.password')}</span>
      <!-- svelte-ignore a11y_autofocus -->
      <input type="password" bind:value={password} autocomplete="current-password" required autofocus />
    </label>
    <label class="check">
      <input type="checkbox" bind:checked={remember} />
      <span>{t('login.remember')}</span>
    </label>
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <button class="primary" type="submit" disabled={busy || !password}>
      {busy ? t('login.submitting') : t('login.submit')}
    </button>
  </form>
</main>

<style>
  .login {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 16px;
  }
  form {
    width: min(360px, 100%);
    display: grid;
    gap: 16px;
  }
  h1 {
    margin: 0;
  }
  label {
    display: grid;
    gap: 6px;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
</style>
