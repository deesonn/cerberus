import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService, SessionInfo } from '../core/auth.service';
import { signedInAgo, timeLeft } from '../core/session-list';

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [FormsModule],
  template: `
    <section class="card">
      <h2>Change your account password</h2>
      <p class="sub">This is the password you sign in with. It is <strong>not</strong> the password on your encrypted files —
        those keep the password you chose when you uploaded them, so nothing you've stored is affected.</p>

      @if (error) { <div class="banner-error" id="account-error">{{ error }}</div> }
      @if (ok) { <div class="banner-ok" id="account-ok">{{ ok }}</div> }

      <form (ngSubmit)="submit()" novalidate>
        <div class="row">
          <label for="current-password">Current password</label>
          <input id="current-password" name="current" type="password" autocomplete="current-password" [(ngModel)]="current" />
        </div>
        <div class="row">
          <label for="new-password">New password (at least 8 characters)</label>
          <input id="new-password" name="new" type="password" autocomplete="new-password" [(ngModel)]="next" />
        </div>
        <div class="row">
          <label for="confirm-password">Confirm new password</label>
          <input id="confirm-password" name="confirm" type="password" autocomplete="new-password" [(ngModel)]="confirm" />
        </div>
        <button class="primary" id="change-submit" type="submit" [disabled]="busy">{{ busy ? 'Changing…' : 'Change password' }}</button>
      </form>
    </section>

    <section class="card" id="sessions-card">
      <h2>Where you're signed in</h2>
      <p class="sub">Each row is a browser or device signed in to your account. If you don't recognize one, sign it out and change your password.</p>

      @if (sessionError) { <div class="banner-error" id="sessions-error">{{ sessionError }}</div> }
      @if (sessionOk) { <div class="banner-ok" id="sessions-ok">{{ sessionOk }}</div> }

      <ul class="sessions" id="session-list">
        @for (s of sessions; track s.id) {
          <li [class.current]="s.current">
            <div class="meta">
              <strong>{{ s.current ? 'This device' : 'Another device' }}
                @if (s.current) { <span class="badge" id="this-device">You are here</span> }
              </strong>
              <span>Signed in {{ ago(s) }} · {{ left(s) }}</span>
            </div>
            @if (!s.current) {
              <button class="revoke" (click)="revoke(s)" [disabled]="sessionBusy">Sign out</button>
            }
          </li>
        }
      </ul>
      <button id="logout-others" (click)="signOutOthers()" [disabled]="sessionBusy || others === 0">
        Sign out all other devices{{ others > 0 ? ' (' + others + ')' : '' }}
      </button>
    </section>
  `,
  styles: [`
    .sessions { list-style: none; padding: 0; margin: 0 0 16px; }
    .sessions li { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
    .sessions li:last-child { border-bottom: none; }
    .meta { display: flex; flex-direction: column; gap: 2px; }
    .meta span { color: var(--muted); font-size: 13px; }
    .badge { font-size: 11px; font-weight: 600; padding: 2px 8px; margin-left: 8px; border-radius: 10px; background: rgba(77, 171, 247, 0.16); color: #74c0fc; }
    .revoke { color: var(--danger); }
    .card { margin-bottom: 22px; }
    .card { max-width: 480px; margin: 0 auto; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 30px; }
    h2 { font-size: 22px; }
    .sub { color: var(--muted); font-size: 14px; margin: 8px 0 20px; }
    .row { margin: 14px 0; }
    form button { margin-top: 8px; }
    .banner-error, .banner-ok { margin-bottom: 14px; }
  `],
})
export class AccountComponent implements OnInit {
  private auth = inject(AuthService);

  current = '';
  next = '';
  confirm = '';
  busy = false;
  error = '';
  ok = '';

  sessions: SessionInfo[] = [];
  sessionBusy = false;
  sessionError = '';
  sessionOk = '';
  private now = new Date();

  get others(): number {
    return this.sessions.filter((s) => !s.current).length;
  }

  ago(s: SessionInfo): string { return signedInAgo(s.created_at, this.now); }
  left(s: SessionInfo): string { return timeLeft(s.expires_at, this.now); }

  async ngOnInit() {
    await this.loadSessions();
  }

  async loadSessions() {
    try {
      this.now = new Date();
      this.sessions = await this.auth.sessions();
    } catch {
      this.sessionError = "Couldn't load your signed-in devices. Please reload the page.";
    }
  }

  async revoke(s: SessionInfo) {
    this.sessionError = '';
    this.sessionOk = '';
    this.sessionBusy = true;
    try {
      await this.auth.revokeSession(s.id);
      this.sessionOk = 'That device was signed out.';
    } catch {
      this.sessionError = "Couldn't sign that device out. It may already be gone.";
    } finally {
      this.sessionBusy = false;
      await this.loadSessions();
    }
  }

  async signOutOthers() {
    this.sessionError = '';
    this.sessionOk = '';
    this.sessionBusy = true;
    try {
      const { signed_out } = await this.auth.logoutOthers();
      this.sessionOk = signed_out === 1 ? '1 other device was signed out.' : `${signed_out} other devices were signed out.`;
    } catch {
      this.sessionError = "Couldn't sign the other devices out. Please try again.";
    } finally {
      this.sessionBusy = false;
      await this.loadSessions();
    }
  }

  async submit() {
    this.error = '';
    this.ok = '';
    if (!this.current || !this.next || !this.confirm) { this.error = 'Fill in all three password fields.'; return; }
    if (this.next.length < 8) { this.error = 'The new password must be at least 8 characters.'; return; }
    if (this.next !== this.confirm) { this.error = "The new password and its confirmation don't match."; return; }
    if (this.next === this.current) { this.error = 'The new password must be different from the current one.'; return; }

    this.busy = true;
    try {
      const res = await this.auth.changePassword(this.current, this.next);
      const n = res.other_sessions_signed_out;
      this.ok = n > 0
        ? `Password changed. ${n} other signed-in ${n === 1 ? 'device was' : 'devices were'} signed out.`
        : 'Password changed. No other devices were signed in.';
      this.current = this.next = this.confirm = '';
      await this.loadSessions();   // the other devices are gone now, so the list should say so
    } catch (err) {
      const e = err as HttpErrorResponse;
      if (e.status === 403) this.error = 'Your current password is incorrect.';
      else if (e.status === 429) this.error = 'Too many failed attempts. Please wait a minute and try again.';
      else if (e.status === 422 && typeof e.error?.detail === 'string') this.error = e.error.detail;
      else this.error = "Couldn't change the password. Nothing was changed — please try again.";
    } finally {
      this.busy = false;
    }
  }
}
