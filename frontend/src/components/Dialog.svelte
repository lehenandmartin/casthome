<script lang="ts">
  import { dialogs } from '../lib/dialog.svelte';
  import { t } from '../lib/i18n';

  let value = $state('');
  let input = $state<HTMLInputElement | null>(null);
  let confirmButton = $state<HTMLButtonElement | null>(null);

  $effect(() => {
    const request = dialogs.current;
    if (!request) return;
    value = request.value ?? '';
    // Focus once the dialog is rendered.
    queueMicrotask(() => (request.kind === 'prompt' ? input?.select() : confirmButton?.focus()));
  });

  function submit(event: SubmitEvent) {
    event.preventDefault();
    const request = dialogs.current;
    if (!request) return;
    if (request.kind === 'prompt') {
      const trimmed = value.trim();
      if (trimmed) dialogs.close(trimmed);
    } else {
      dialogs.close(true);
    }
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && dialogs.current && dialogs.close(null)} />

{#if dialogs.current}
  {@const request = dialogs.current}
  <div class="backdrop" role="presentation" onclick={() => dialogs.close(null)}></div>
  <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
    <form onsubmit={submit}>
      <h3 id="dialog-title">{request.title}</h3>
      {#if request.message}<p class="muted">{request.message}</p>{/if}
      {#if request.kind === 'prompt'}
        <input bind:this={input} type="text" bind:value placeholder={request.placeholder} aria-label={request.title} />
      {/if}
      <div class="actions">
        <button type="button" onclick={() => dialogs.close(null)}>{t('playlist.cancel')}</button>
        <button
          bind:this={confirmButton}
          type="submit"
          class={request.danger ? 'danger' : 'primary'}
          disabled={request.kind === 'prompt' && !value.trim()}>{request.confirmLabel}</button
        >
      </div>
    </form>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgb(0 0 0 / 0.45);
    z-index: 40;
  }
  .dialog {
    position: fixed;
    z-index: 41;
    left: 16px;
    right: 16px;
    top: 20dvh;
    max-width: 420px;
    margin: 0 auto;
    padding: 20px;
    border-radius: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: 0 12px 40px rgb(0 0 0 / 0.35);
  }
  form {
    display: grid;
    gap: 12px;
  }
  h3,
  p {
    margin: 0;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .danger {
    background: var(--danger);
    color: #fff;
    border-color: transparent;
    font-weight: 600;
  }
</style>
