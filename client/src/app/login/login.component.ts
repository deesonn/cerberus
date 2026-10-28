import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <section class="card">
      <h1>Sign in</h1>
      <p class="sub">Your files are encrypted in your browser before they ever reach the server.</p>

      @if (notice) {
        <div class="banner-notice" id="session-notice">{{ notice }}</div>
      }
      @if (formError) {
        <div class="banner-error" id="form-error">{{ formError }}</div>
      }

      <form (ngSubmit)="submit()" novalidate>
        <div class="row">
          <label for="username">Username</label>
          <input id="username" name="username" type="text" autocomplete="username" [(ngModel)]="username" />
          @if (submitted && !username.trim()) {
            <div class="field-error" id="username-error">Username is required.</div>
          }
        </div>
        <div class="row">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" autocomplete="current-password" [(ngModel)]="password" />
          @if (submitted && !password) {
            <div class="field-error" id="password-error">Password is required.</div>
          }
        </div>
        <button class="primary" id="submit" type="submit" [disabled]="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
      </form>
    </section>
  `,
  styles: [`
    .card { max-width: 400px; margin: 48px auto 0; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 32px; }
    h1 { font-size: 26px; }
    .sub { color: var(--muted); font-size: 14px; margin: 8px 0 22px; }
    .row { margin: 16px 0; }
    form button { width: 100%; margin-top: 8px; }
    .banner-error { margin-bottom: 8px; }
    .banner-notice { margin-bottom: 12px; color: #ffcf5c; background: rgba(255,207,92,.08); border: 1px solid rgba(255,207,92,.35); padding: 10px 12px; border-radius: 8px; font-size: 14px; }
  `],
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  username = '';
  password = '';
  submitted = false;
  busy = false;
  formError = '';
  notice =
    this.route.snapshot.queryParamMap.get('reason') === 'expired'
      ? 'Your session expired. Please sign in again.'
      : this.route.snapshot.queryParamMap.get('reason') === 'signin'
        ? 'Please sign in to continue.'
        : '';

  async submit() {
    this.submitted = true;
    this.formError = '';
    if (!this.username.trim() || !this.password) return;
    this.busy = true;
    try {
      await this.auth.login(this.username.trim(), this.password);
      await this.router.navigate(['/']);
    } catch (err) {
      const e = err as HttpErrorResponse;
      if (e.status === 401) this.formError = 'Username or password is incorrect.';
      else if (e.status === 429) this.formError = 'Too many failed attempts. Please wait a minute and try again.';
      else this.formError = "Couldn't reach the server. Please try again.";
    } finally {
      this.busy = false;
    }
  }
}
