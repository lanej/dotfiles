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

export interface IdleSessionHost extends Omit<IdleHost, "snapshot"> {
  snapshot(): Omit<IdleSnapshot, "dialogs" | "children">;
}

/** Unknown child work outlives controller replacement during tree navigation and compaction. */
export class IdleSession {
  private controller: IdleCompactor | undefined;
  private settled = false;
  private dialogs = 0;
  private childWork = false;

  newSession(): void {
    this.stop();
    this.childWork = false;
  }

  initialize(
    host: IdleSessionHost,
    idleMs: number,
    minimumPercent: number,
    restoredHistory: string | null,
  ): void {
    this.stop();
    this.settled = host.snapshot().settled;
    this.dialogs = 0;
    this.controller = new IdleCompactor(
      {
        ...host,
        snapshot: () => {
          const snapshot = host.snapshot();
          return {
            ...snapshot,
            settled: this.settled && snapshot.settled,
            dialogs: this.dialogs,
            children: this.childWork ? 1 : 0,
          };
        },
      },
      idleMs,
      minimumPercent,
    );
    this.controller.restore(restoredHistory);
    if (this.settled) this.controller.settled();
  }

  activity(): void {
    this.controller?.activity();
  }

  terminalInput(): void {
    this.activity();
    if (this.settled) this.controller?.settled();
  }

  agentStart(): void {
    this.settled = false;
    this.activity();
  }

  agentSettled(): void {
    this.settled = true;
    this.controller?.settled();
  }

  promptStart(): void {
    this.dialogs++;
    this.activity();
  }

  promptEnd(): void {
    this.dialogs = Math.max(0, this.dialogs - 1);
    if (this.settled) this.controller?.settled();
  }

  toolStart(name: string): void {
    // Unknown third-party tools have no reliable completion signal. Only a new session clears this guard.
    if (/subagent|delegate|spawn_agent/.test(name)) this.childWork = true;
    this.activity();
  }

  stop(): void {
    this.controller?.stop();
    this.controller = undefined;
  }
}

/** The runtime owns clocks and Pi effects; this controller owns idle eligibility. */
export class IdleCompactor {
  private cancelTimer: (() => void) | undefined;
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
        now.historyId === null ||
        now.historyId.length === 0 ||
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
