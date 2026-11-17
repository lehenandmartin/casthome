<script lang="ts">
  import { fadeOut, sheetOut } from '../lib/motion';
  // The app's single action menu (see lib/contextMenu.svelte.ts), and the
  // playlist picker its "Add to playlist…" entries open.
  import { tick } from 'svelte';
  import { contextMenu, type MenuAction } from '../lib/contextMenu.svelte';
  import Icon from './Icon.svelte';
  import PlaylistPicker from './PlaylistPicker.svelte';
  import RatingStars from './RatingStars.svelte';
  import { display } from '../lib/display.svelte';

  const open = $derived(contextMenu.current);
  const items = $derived((open?.spec.items ?? []).filter((item): item is MenuAction => Boolean(item)));
  let menuEl = $state<HTMLElement | null>(null);

  function close() {
    contextMenu.close();
  }

  // The backdrop appears under the finger of a long-press: ignore the tap that ends it.
  function backdropClick() {
    if (Date.now() - contextMenu.openedAt > 400) close();
  }

  function choose(item: MenuAction) {
    close();
    item.action?.();
  }

  // Highlight what was right-clicked while its menu is open.
  $effect(() => {
    const target = open?.target;
    if (!target) return;
    target.classList.add('context-target');
    return () => target.classList.remove('context-target');
  });

  // At the pointer: keep the menu inside the window, opening it up and/or to
  // the left near the edges. Focus the first entry for the keyboard.
  $effect(() => {
    if (!open?.at || !menuEl) return;
    const margin = 8;
    const { width, height } = menuEl.getBoundingClientRect();
    let { x, y } = open.at;
    if (x + width > window.innerWidth - margin) x = Math.max(margin, x - width);
    if (y + height > window.innerHeight - margin) y = Math.max(margin, window.innerHeight - margin - height);
    menuEl.style.left = `${x}px`;
    menuEl.style.top = `${y}px`;
    menuEl.querySelector<HTMLElement>('[role="menuitem"]')?.focus({ preventScroll: true });
  });

  // A right-click outside the open menu closes it and opens the one under the pointer.
  async function reopenUnder(event: MouseEvent) {
    event.preventDefault();
    const { clientX, clientY } = event;
    close();
    await tick();
    document
      .elementFromPoint(clientX, clientY)
      ?.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX, clientY }));
  }

  // Up/Down/Home/End move between the entries.
  function navigate(event: KeyboardEvent) {
    if (!menuEl || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const entries = [...menuEl.querySelectorAll<HTMLElement>('[role="menuitem"]')];
    const at = entries.indexOf(document.activeElement as HTMLElement);
    const next =
      event.key === 'Home' ? 0
      : event.key === 'End' ? entries.length - 1
      : event.key === 'ArrowDown' ? (at + 1) % entries.length
      : (at - 1 + entries.length) % entries.length;
    entries[next]?.focus();
  }

  // A menu at the pointer follows nothing: close it when the page moves.
  function onScroll(event: Event) {
    if (open?.at && !(event.target instanceof Node && menuEl?.contains(event.target))) close();
  }
</script>

<svelte:window
  onkeydown={(e) => {
    // Marked as handled so the view under the menu (Now Playing…) stays open.
    if (e.key === 'Escape' && open) {
      e.preventDefault();
      close();
    }
  }}
  onresize={() => open?.at && close()}
  onscrollcapture={onScroll}
/>

{#if open}
  <div class="sheet-backdrop" class:clear={open.at} role="presentation" onclick={backdropClick} oncontextmenu={reopenUnder} out:fadeOut></div>
  <div
    class="sheet"
    class:popover={open.at}
    out:sheetOut
    bind:this={menuEl}
    role="dialog"
    aria-modal="true"
    aria-label={open.spec.title}
    tabindex="-1"
    onkeydown={navigate}
  >
    <div class="sheet-head">
      <span class="text">
        <strong class="ellipsis">{open.spec.title}</strong>
        {#if open.spec.subtitle}<span class="muted ellipsis">{open.spec.subtitle}</span>{/if}
      </span>
      {#if open.spec.rating && display.ratings}
        {@const rating = open.spec.rating}
        <RatingStars
          id={rating.id}
          bind:rating={
            () => rating.value,
            (value) => {
              rating.value = value;
              rating.onchange(value);
            }
          }
        />
      {/if}
    </div>
    <div class="sheet-actions" role="menu">
      {#each items as item (item.label)}
        {#if item.href}
          <a role="menuitem" class:danger={item.danger} href={item.href} onclick={close}><Icon name={item.icon} size={20} />{item.label}</a>
        {:else}
          <button role="menuitem" class:danger={item.danger} onclick={() => choose(item)}><Icon name={item.icon} size={20} />{item.label}</button>
        {/if}
      {/each}
    </div>
  </div>
{/if}

{#if contextMenu.pickerFor}
  <PlaylistPicker songIds={contextMenu.pickerFor} onclose={() => (contextMenu.pickerFor = null)} />
{/if}

<style>
  .sheet-head {
    display: grid;
    gap: 8px;
    padding: 4px 4px 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
  }
  .text {
    display: grid;
    min-width: 0;
  }
  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sheet-actions {
    display: grid;
  }
  .sheet-actions > * {
    display: flex;
    align-items: center;
    gap: 12px;
    background: none;
    border: 0;
    border-radius: 10px;
    padding: 12px 8px;
    text-align: left;
    text-decoration: none;
    color: inherit;
    font-size: var(--text-md);
  }
  /* Mouse only: on touch screens the hover would stick to the entry under the
     finger that opened the menu with a long-press. */
  @media (hover: hover) {
    .sheet-actions > *:hover {
      background: var(--surface-2);
    }
  }
  .sheet-actions .danger {
    color: var(--danger);
  }

  /* Right-click: a compact menu at the pointer instead of a sheet. */
  .sheet-backdrop.clear {
    background: transparent;
    animation: none;
  }
  .sheet.popover {
    right: auto;
    bottom: auto;
    width: 260px;
    max-height: calc(100dvh - 16px);
    transform: none;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid var(--border);
    animation: fade-in 0.1s ease-out;
  }
  .sheet.popover::before {
    display: none;
  }
  .popover .sheet-head {
    gap: 6px;
    padding: 6px 8px 8px;
  }
  .popover .sheet-actions > * {
    gap: 8px;
    padding: 8px 8px;
    border-radius: 6px;
    font-size: var(--text-sm);
  }
  .popover .sheet-actions > :focus-visible {
    background: var(--surface-2);
    outline: none;
  }
</style>
