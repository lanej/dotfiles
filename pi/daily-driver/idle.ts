export interface IdleSnapshot {
  sessionId: string;
  branchId: string | null;
  historyId: string | null;
  settled: boolean;
  pendingInput: boolean;
  editorText: string;
  dialogs: number;
  children: number;
  percent: number | null;
}

export interface IdleHost {
  snapshot(): IdleSnapshot;
  compact(callbacks: { complete(): void; error(error: Error): void }): void;
  recordAttempt(historyId: string): void;
  notify(error: Error): void;
  schedule(callback: () => void, delay: number): () => void;
}

/** The runtime owns clocks and Pi effects; this controller owns idle eligibility. */
export class IdleCompactor {
  private cancelTimer?: () => void;
  private attempted: string | null = null;
  private busy = false;
  private generation = 0;
  private stopped = false;

  constructor(
    private readonly host: IdleHost,
    private readonly idleMs: number,
    private readonly minimumPercent: number,
  ) {}

  restore(historyId: string | null): void {
    this.attempted = historyId;
  }

  activity(): void {
    this.generation++;
    this.cancelTimer?.();
    this.cancelTimer = undefined;
  }

  settled(): void {
    this.activity();
    if (this.stopped || this.busy) return;
    const generation = this.generation;
    const before = this.host.snapshot();
    this.cancelTimer = this.host.schedule(() => {
      this.cancelTimer = undefined;
      const now = this.host.snapshot();
      if (
        this.stopped ||
        generation !== this.generation ||
        this.busy ||
        now.sessionId !== before.sessionId ||
        now.branchId !== before.branchId ||
        !now.historyId ||
        now.historyId !== before.historyId ||
        now.historyId === this.attempted ||
        !now.settled ||
        now.pendingInput ||
        now.editorText.length > 0 ||
        now.dialogs > 0 ||
        now.children > 0 ||
        now.percent === null ||
        !Number.isFinite(now.percent) ||
        now.percent < this.minimumPercent
      )
        return;
      // Record before the request: a failed or interrupted attempt must not become an idle retry loop.
      this.attempted = now.historyId;
      this.busy = true;
      const finish = () => {
        this.busy = false;
      };
      try {
        this.host.recordAttempt(now.historyId);
        this.host.compact({
          complete: finish,
          error: (error) => {
            finish();
            this.host.notify(error);
          },
        });
      } catch (error) {
        finish();
        this.host.notify(
          error instanceof Error ? error : new Error(String(error)),
        );
      }
    }, this.idleMs);
  }

  stop(): void {
    this.stopped = true;
    this.activity();
  }
}
