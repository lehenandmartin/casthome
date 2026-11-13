// Promise-based replacements for window.prompt/confirm, rendered by Dialog.svelte.

export interface DialogRequest {
  kind: 'prompt' | 'confirm';
  title: string;
  message?: string;
  value?: string;
  placeholder?: string;
  confirmLabel: string;
  danger?: boolean;
  resolve: (value: string | boolean | null) => void;
}

class DialogStore {
  current = $state<DialogRequest | null>(null);

  prompt(options: { title: string; value?: string; placeholder?: string; confirmLabel: string }): Promise<string | null> {
    return new Promise((resolve) => {
      this.#open({ kind: 'prompt', ...options, resolve: (v) => resolve(typeof v === 'string' ? v : null) });
    });
  }

  confirm(options: { title: string; message?: string; confirmLabel: string; danger?: boolean }): Promise<boolean> {
    return new Promise((resolve) => {
      this.#open({ kind: 'confirm', ...options, resolve: (v) => resolve(v === true) });
    });
  }

  close(value: string | boolean | null): void {
    const request = this.current;
    this.current = null;
    request?.resolve(value);
  }

  #open(request: DialogRequest): void {
    this.current?.resolve(null); // only one dialog at a time
    this.current = request;
  }
}

export const dialogs = new DialogStore();
