import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../core/auth.service';

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
  `,
  styles: [`
    .card { max-width: 480px; margin: 0 auto; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 30px; }
    h2 { font-size: 22px; }
    .sub { color: var(--muted); font-size: 14px; margin: 8px 0 20px; }
    .row { margin: 14px 0; }
    form button { margin-top: 8px; }
    .banner-error, .banner-ok { margin-bottom: 14px; }
  `],
})
export class AccountComponent {
  private auth = inject(AuthService);

  current = '';
  next = '';
  confirm = '';
  busy = false;
  error = '';
  ok = '';

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
