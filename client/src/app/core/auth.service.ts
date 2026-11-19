import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { apiBase } from './api-base';

export const API = apiBase(window.location);

export interface SessionInfo {
  id: string;
  created_at: string;
  expires_at: string;
  current: boolean;
}
const TOKEN_KEY = 'cerberus.token';
const USER_KEY = 'cerberus.user';
const ADMIN_KEY = 'cerberus.admin';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  get token(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  }
  get username(): string | null {
    return sessionStorage.getItem(USER_KEY);
  }
  get isAdmin(): boolean {
    return sessionStorage.getItem(ADMIN_KEY) === '1';
  }
  get loggedIn(): boolean {
    return !!this.token;
  }

  async login(username: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<{ token: string; username: string; is_admin: boolean }>(`${API}/auth/login`, { username, password }),
    );
    sessionStorage.setItem(TOKEN_KEY, res.token);
    sessionStorage.setItem(USER_KEY, res.username);
    sessionStorage.setItem(ADMIN_KEY, res.is_admin ? '1' : '0');
  }

  changePassword(currentPassword: string, newPassword: string): Promise<{ other_sessions_signed_out: number }> {
    return firstValueFrom(
      this.http.post<{ other_sessions_signed_out: number }>(
        `${API}/auth/change-password`,
        { current_password: currentPassword, new_password: newPassword },
        { headers: this.authHeaders() },
      ),
    );
  }

  sessions(): Promise<SessionInfo[]> {
    return firstValueFrom(this.http.get<SessionInfo[]>(`${API}/auth/sessions`, { headers: this.authHeaders() }));
  }

  revokeSession(id: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`${API}/auth/sessions/${id}`, { headers: this.authHeaders() }));
  }

  logoutOthers(): Promise<{ signed_out: number }> {
    return firstValueFrom(this.http.post<{ signed_out: number }>(`${API}/auth/logout-others`, {}, { headers: this.authHeaders() }));
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(this.http.post(`${API}/auth/logout`, {}, { headers: this.authHeaders() }));
    } catch {
      // Server already considers us logged out (or is unreachable); either way, clear locally.
    }
    this.clear();
    await this.router.navigate(['/login']);
  }

  clear(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(ADMIN_KEY);
  }

  authHeaders(): Record<string, string> {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }
}
