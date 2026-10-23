import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

export const API = 'http://localhost:8000';
const TOKEN_KEY = 'cerberus.token';
const USER_KEY = 'cerberus.user';

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
  get loggedIn(): boolean {
    return !!this.token;
  }

  async login(username: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<{ token: string; username: string }>(`${API}/auth/login`, { username, password }),
    );
    sessionStorage.setItem(TOKEN_KEY, res.token);
    sessionStorage.setItem(USER_KEY, res.username);
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
  }

  authHeaders(): Record<string, string> {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }
}
