import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { API, AuthService } from './auth.service';

export interface FileMeta {
  hash: string;
  filename: string;
  size: number;
  uploaded_at: string;
}

export interface StorageInfo {
  used_bytes: number;
  quota_bytes: number;
  file_count: number;
  max_upload_bytes: number;
}

@Injectable({ providedIn: 'root' })
export class FilesService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  list(): Promise<FileMeta[]> {
    return firstValueFrom(this.http.get<FileMeta[]>(`${API}/files`, { headers: this.auth.authHeaders() }));
  }

  storage(): Promise<StorageInfo> {
    return firstValueFrom(this.http.get<StorageInfo>(`${API}/me/storage`, { headers: this.auth.authHeaders() }));
  }

  upload(ciphertext: Uint8Array, filename: string): Promise<FileMeta> {
    const form = new FormData();
    form.append('file', new Blob([ciphertext]), 'blob');
    form.append('filename', filename);
    return firstValueFrom(this.http.post<FileMeta>(`${API}/file/upload`, form, { headers: this.auth.authHeaders() }));
  }

  rename(hash: string, filename: string): Promise<{ hash: string; filename: string }> {
    return firstValueFrom(
      this.http.patch<{ hash: string; filename: string }>(`${API}/file/${hash}`, { filename }, { headers: this.auth.authHeaders() }),
    );
  }

  delete(hash: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`${API}/file/${hash}`, { headers: this.auth.authHeaders() }));
  }

  download(hash: string): Promise<ArrayBuffer> {
    return firstValueFrom(
      this.http.get(`${API}/file/${hash}`, { headers: this.auth.authHeaders(), responseType: 'arraybuffer' }),
    );
  }
}
