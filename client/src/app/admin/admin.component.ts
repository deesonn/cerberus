import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AdminService, AdminUser } from '../core/admin.service';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule],
  template: `
    <section class="card">
      <h2>Create an account</h2>
      <p class="sub">Accounts are only created by administrators. Share the starting password with the person privately.</p>
      @if (createError) { <div class="banner-error" id="admin-error">{{ createError }}</div> }
      @if (notice) { <div class="banner-ok" id="admin-ok">{{ notice }}</div> }
      <form (ngSubmit)="create()" novalidate class="create">
        <div>
          <label for="new-username">Username</label>
          <input id="new-username" name="u" type="text" autocomplete="off" [(ngModel)]="newUsername" />
        </div>
        <div>
          <label for="new-user-password">Starting password</label>
          <input id="new-user-password" name="p" type="password" autocomplete="new-password" [(ngModel)]="newPassword" />
        </div>
        <label class="check"><input id="new-user-admin" name="a" type="checkbox" [(ngModel)]="newIsAdmin" /> Make this person an administrator</label>
        <button class="primary" id="create-user" type="submit" [disabled]="busy">Create account</button>
      </form>
    </section>

    <section class="card">
      <h2>Accounts</h2>
      <p class="sub">Administrators see how many files each person has stored and how much space they use — never the files themselves.</p>
      @if (listError) { <div class="banner-error">{{ listError }}</div> }
      @if (loading) {
        <p class="sub">Loading…</p>
      } @else {
        <table id="user-table">
          <thead><tr><th>Username</th><th>Role</th><th class="num">Files</th><th class="num">Storage</th><th></th></tr></thead>
          <tbody>
            @for (u of users; track u.id) {
              <tr [attr.data-user]="u.username">
                <td><strong>{{ u.username }}</strong> @if (u.username === me) { <span class="you">you</span> }</td>
                <td><span class="pill" [class.admin]="u.is_admin">{{ u.is_admin ? 'Administrator' : 'User' }}</span></td>
                <td class="num">{{ u.file_count }}</td>
                <td class="num">{{ size(u.total_bytes) }}</td>
                <td class="act">
                  @if (confirming === u.id) {
                    <span class="warn">Delete {{ u.username }} and {{ u.file_count }} {{ u.file_count === 1 ? 'file' : 'files' }}?</span>
                    <button class="danger" id="del-yes" (click)="confirmDelete(u)" [disabled]="busy">Delete</button>
                    <button id="del-no" (click)="confirming = null">Cancel</button>
                  } @else if (u.username !== me) {
                    <button class="del" (click)="confirming = u.id; notice = ''">Delete</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </section>
  `,
  styles: [`
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 26px; margin-bottom: 22px; }
    h2 { font-size: 20px; }
    .sub { color: var(--muted); font-size: 14px; margin: 8px 0 18px; }
    .create { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 16px; align-items: end; }
    .create .check, .create button { grid-column: 1 / -1; }
    .check { display: flex; align-items: center; gap: 8px; color: var(--text); font-size: 14px; margin: 0; }
    .check input { width: auto; }
    .banner-error, .banner-ok { margin-bottom: 14px; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th { text-align: left; color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; padding: 0 8px 10px; }
    td { padding: 12px 8px; border-top: 1px solid var(--border); vertical-align: middle; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .act { text-align: right; white-space: nowrap; }
    .act button { padding: 6px 12px; font-size: 13px; margin-left: 6px; }
    .del { color: var(--danger); }
    .warn { color: var(--danger); font-size: 13px; }
    button.danger { background: var(--danger); color: #1a0505; border-color: var(--danger); font-weight: 600; }
    .pill { font-size: 12px; padding: 3px 9px; border-radius: 99px; background: var(--panel-2); color: var(--muted); }
    .pill.admin { background: rgba(62,166,255,.15); color: var(--accent); }
    .you { font-size: 11px; color: var(--muted); border: 1px solid var(--border); padding: 1px 6px; border-radius: 6px; margin-left: 6px; }
    @media (max-width: 640px) { .create { grid-template-columns: 1fr; } }
  `],
})
export class AdminComponent implements OnInit {
  private admin = inject(AdminService);
  private auth = inject(AuthService);

  me = this.auth.username;
  users: AdminUser[] = [];
  loading = true;
  busy = false;

  newUsername = '';
  newPassword = '';
  newIsAdmin = false;
  createError = '';
  listError = '';
  notice = '';
  confirming: number | null = null;

  async ngOnInit() {
    await this.refresh();
  }

  async refresh() {
    try {
      this.users = await this.admin.list();
      this.listError = '';
    } catch {
      this.listError = "Couldn't load the account list.";
    } finally {
      this.loading = false;
    }
  }

  size(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  async create() {
    this.createError = '';
    this.notice = '';
    if (!this.newUsername.trim() || !this.newPassword) { this.createError = 'Enter a username and a starting password.'; return; }
    this.busy = true;
    try {
      const made = await this.admin.create(this.newUsername.trim(), this.newPassword, this.newIsAdmin);
      this.notice = `Created ${made.is_admin ? 'administrator' : 'user'} "${made.username}".`;
      this.newUsername = this.newPassword = '';
      this.newIsAdmin = false;
      await this.refresh();
    } catch (err) {
      const e = err as HttpErrorResponse;
      this.createError = typeof e.error?.detail === 'string' ? e.error.detail : "Couldn't create the account. Please try again.";
    } finally {
      this.busy = false;
    }
  }

  async confirmDelete(u: AdminUser) {
    this.busy = true;
    try {
      const res = await this.admin.delete(u.id);
      this.notice = `Deleted "${res.username}" and ${res.files_removed} ${res.files_removed === 1 ? 'file' : 'files'}.`;
      this.confirming = null;
      await this.refresh();
    } catch (err) {
      const e = err as HttpErrorResponse;
      this.listError = typeof e.error?.detail === 'string' ? e.error.detail : "Couldn't delete that account.";
      this.confirming = null;
    } finally {
      this.busy = false;
    }
  }
}
