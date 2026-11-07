import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="top">
      <div class="brand"><span class="mark">&#9670;</span> Cerberus</div>
      @if (auth.loggedIn) {
        <nav>
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" id="nav-files">Files</a>
          <a routerLink="/account" routerLinkActive="active" id="nav-account">Account</a>
          @if (auth.isAdmin) { <a routerLink="/admin" routerLinkActive="active" id="nav-admin">Admin</a> }
        </nav>
        <div class="who">
          <span>{{ auth.username }}</span>
          <button id="logout" (click)="auth.logout()">Log out</button>
        </div>
      }
    </header>
    <main><router-outlet /></main>
  `,
  styles: [`
    .top { display:flex; justify-content:space-between; align-items:center; padding:16px 28px; border-bottom:1px solid var(--border); background: var(--panel); }
    .brand { font-weight:700; font-size:18px; letter-spacing:.02em; }
    .mark { color: var(--accent); margin-right:6px; }
    nav { display:flex; gap:6px; margin-left:28px; margin-right:auto; }
    nav a { color: var(--muted); text-decoration:none; padding:6px 12px; border-radius:8px; font-size:14px; }
    nav a:hover { color: var(--text); }
    nav a.active { color: var(--text); background: var(--panel-2); }
    .who { display:flex; gap:14px; align-items:center; color: var(--muted); font-size:14px; }
    .who button { padding:6px 12px; font-size:13px; }
    main { max-width: 860px; margin: 0 auto; padding: 32px 20px 64px; }
  `],
})
export class AppComponent {
  auth = inject(AuthService);
}
