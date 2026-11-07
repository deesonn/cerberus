import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { API, AuthService } from './auth.service';

export interface AdminUser {
  id: number;
  username: string;
  is_admin: boolean;
  file_count: number;
  total_bytes: number;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  list(): Promise<AdminUser[]> {
    return firstValueFrom(this.http.get<AdminUser[]>(`${API}/admin/users`, { headers: this.auth.authHeaders() }));
  }

  create(username: string, password: string, isAdmin: boolean): Promise<AdminUser> {
    return firstValueFrom(
      this.http.post<AdminUser>(`${API}/admin/users`, { username, password, is_admin: isAdmin }, { headers: this.auth.authHeaders() }),
    );
  }

  delete(id: number): Promise<{ username: string; files_removed: number }> {
    return firstValueFrom(
      this.http.delete<{ username: string; files_removed: number }>(`${API}/admin/users/${id}`, { headers: this.auth.authHeaders() }),
    );
  }
}
